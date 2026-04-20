/**
 * Concurrency Controller - 并发控制器
 * 
 * 核心能力：
 * 1. 智能并发调度（读/写分离）
 * 2. 资源槽位管理
 * 3. 优先级队列
 * 4. 超时控制
 * 
 * 使用方式：
 * ```typescript
 * const controller = new ConcurrencyController({
 *   maxConcurrency: 5,
 *   maxWriteConcurrency: 1  // 写操作串行
 * })
 * 
 * // 只读任务可并发
 * await controller.execute('read', 'file1', async () => {
 *   return readFile('file1')
 * })
 * 
 * // 写任务串行
 * await controller.execute('write', 'file2', async () => {
 *   return writeFile('file2', content)
 * })
 * ```
 */

// ============================================================================
// 类型定义
// ============================================================================

export type OperationType = 'read' | 'write' | 'custom'

export interface TaskOptions {
  type: OperationType
  priority?: number  // 数字越小优先级越高
  timeout?: number   // 超时时间 (ms)
  retryCount?: number // 重试次数
  retryDelay?: number // 重试间隔 (ms)
}

export interface Task<T = any> {
  id: string
  name: string
  options: TaskOptions
  fn: () => Promise<T>
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  createdAt: number
  startedAt?: number
  completedAt?: number
  result?: T
  error?: Error
  retryAttempt?: number
}

export interface ConcurrencyConfig {
  maxConcurrency: number        // 最大并发数
  maxWriteConcurrency?: number  // 写操作最大并发（默认 1，串行）
  maxReadConcurrency?: number   // 读操作最大并发（默认等于 maxConcurrency）
  defaultTimeout?: number       // 默认超时 (ms)
  defaultRetryCount?: number    // 默认重试次数
  defaultRetryDelay?: number    // 默认重试间隔 (ms)
}

// ============================================================================
// 并发控制器类
// ============================================================================

export class ConcurrencyController {
  private config: Required<ConcurrencyConfig>
  
  // 任务队列
  private readQueue: Task[] = []
  private writeQueue: Task[] = []
  
  // 运行中的任务
  private runningRead = new Map<string, Task>()
  private runningWrite = new Map<string, Task>()
  
  // 已完成的任务（缓存）
  private completed = new Map<string, Task>()
  
  // 信号量
  private readSemaphore: number
  private writeSemaphore: number
  
  // 调度器
  private schedulerRunning = false
  
  constructor(config: ConcurrencyConfig) {
    this.config = {
      maxConcurrency: config.maxConcurrency || 10,
      maxWriteConcurrency: config.maxWriteConcurrency || 1,
      maxReadConcurrency: config.maxReadConcurrency || config.maxConcurrency || 10,
      defaultTimeout: config.defaultTimeout || 60000,
      defaultRetryCount: config.defaultRetryCount || 0,
      defaultRetryDelay: config.defaultRetryDelay || 1000
    }
    
    this.readSemaphore = this.config.maxReadConcurrency
    this.writeSemaphore = this.config.maxWriteConcurrency
  }
  
  /**
   * 执行任务
   */
  async execute<T>(
    type: OperationType,
    name: string,
    fn: () => Promise<T>,
    options?: Partial<TaskOptions>
  ): Promise<T> {
    const task: Task<T> = {
      id: this.generateId(),
      name,
      options: {
        type,
        priority: 0,
        timeout: this.config.defaultTimeout,
        retryCount: this.config.defaultRetryCount,
        retryDelay: this.config.defaultRetryDelay,
        ...options
      },
      fn,
      status: 'pending',
      createdAt: Date.now()
    }
    
    // 添加到对应队列
    if (type === 'write') {
      this.writeQueue.push(task as Task)
    } else {
      this.readQueue.push(task as Task)
    }
    
    // 启动调度器
    this.startScheduler()
    
    // 等待任务完成
    return new Promise((resolve, reject) => {
      const checkComplete = () => {
        const completedTask = this.completed.get(task.id)
        
        if (completedTask) {
          if (completedTask.status === 'completed') {
            resolve(completedTask.result as T)
          } else if (completedTask.status === 'failed') {
            reject(completedTask.error)
          } else if (completedTask.status === 'cancelled') {
            reject(new Error(`Task cancelled: ${name}`))
          }
          return
        }
        
        setTimeout(checkComplete, 10)
      }
      
      checkComplete()
    })
  }
  
  /**
   * 批量执行任务
   */
  async executeBatch<T>(
    tasks: Array<{
      type: OperationType
      name: string
      fn: () => Promise<T>
      priority?: number
    }>
  ): Promise<T[]> {
    const promises = tasks.map(task =>
      this.execute(task.type, task.name, task.fn, { priority: task.priority })
    )
    
    return Promise.all(promises)
  }
  
  /**
   * 取消任务
   */
  cancel(taskId: string): boolean {
    // 从队列中移除
    const readIndex = this.readQueue.findIndex(t => t.id === taskId)
    if (readIndex >= 0) {
      this.readQueue.splice(readIndex, 1)
      return true
    }
    
    const writeIndex = this.writeQueue.findIndex(t => t.id === taskId)
    if (writeIndex >= 0) {
      this.writeQueue.splice(writeIndex, 1)
      return true
    }
    
    // 取消运行中的任务（无法真正取消，只能标记）
    const runningTask = this.runningRead.get(taskId) || this.runningWrite.get(taskId)
    if (runningTask) {
      runningTask.status = 'cancelled'
      return true
    }
    
    return false
  }
  
  /**
   * 获取状态
   */
  getStatus(): {
    readQueue: number
    writeQueue: number
    runningRead: number
    runningWrite: number
    completed: number
    readSemaphore: number
    writeSemaphore: number
  } {
    return {
      readQueue: this.readQueue.length,
      writeQueue: this.writeQueue.length,
      runningRead: this.runningRead.size,
      runningWrite: this.runningWrite.size,
      completed: this.completed.size,
      readSemaphore: this.readSemaphore,
      writeSemaphore: this.writeSemaphore
    }
  }
  
  /**
   * 清空已完成任务缓存
   */
  clearCompleted(): void {
    this.completed.clear()
  }
  
  /**
   * 生成任务 ID
   */
  private generateId(): string {
    return `task_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  }
  
  /**
   * 启动调度器
   */
  private startScheduler(): void {
    if (this.schedulerRunning) return
    
    this.schedulerRunning = true
    
    setImmediate(() => {
      this.runScheduler()
      this.schedulerRunning = false
    })
  }
  
  /**
   * 运行调度器
   */
  private async runScheduler(): Promise<void> {
    let hasWork = false
    
    // 调度读任务
    while (this.readSemaphore > 0 && this.readQueue.length > 0) {
      hasWork = true
      
      // 按优先级排序
      this.readQueue.sort((a, b) => (a.options.priority || 0) - (b.options.priority || 0))
      
      const task = this.readQueue.shift()!
      this.readSemaphore--
      this.runningRead.set(task.id, task)
      
      // 异步执行，不阻塞调度
      this.runTask(task, 'read').finally(() => {
        this.readSemaphore++
        this.runningRead.delete(task.id)
        this.startScheduler()  // 触发下一轮调度
      })
    }
    
    // 调度写任务
    while (this.writeSemaphore > 0 && this.writeQueue.length > 0) {
      hasWork = true
      
      // 按优先级排序
      this.writeQueue.sort((a, b) => (a.options.priority || 0) - (b.options.priority || 0))
      
      const task = this.writeQueue.shift()!
      this.writeSemaphore--
      this.runningWrite.set(task.id, task)
      
      // 异步执行
      this.runTask(task, 'write').finally(() => {
        this.writeSemaphore++
        this.runningWrite.delete(task.id)
        this.startScheduler()
      })
    }
    
    // 如果没有更多工作，退出
    if (!hasWork && this.readQueue.length === 0 && this.writeQueue.length === 0) {
      return
    }
    
    // 继续调度
    if (hasWork) {
      this.startScheduler()
    }
  }
  
  /**
   * 运行单个任务
   */
  private async runTask(task: Task, type: 'read' | 'write'): Promise<void> {
    task.status = 'running'
    task.startedAt = Date.now()
    
    try {
      // 设置超时
      const timeout = task.options.timeout || this.config.defaultTimeout
      const result = await this.withTimeout(task.fn, timeout)
      
      task.status = 'completed'
      task.result = result
      task.completedAt = Date.now()
      
    } catch (error) {
      // 重试逻辑
      const retryCount = task.retryAttempt || 0
      const maxRetries = task.options.retryCount || 0
      
      if (retryCount < maxRetries) {
        task.retryAttempt = retryCount + 1
        task.status = 'pending'
        
        // 延迟后重新加入队列
        const delay = task.options.retryDelay || this.config.defaultRetryDelay
        await new Promise(resolve => setTimeout(resolve, delay * (retryCount + 1)))
        
        if (type === 'read') {
          this.readQueue.push(task)
        } else {
          this.writeQueue.push(task)
        }
        return
      }
      
      // 失败
      task.status = 'failed'
      task.error = error instanceof Error ? error : new Error(String(error))
      task.completedAt = Date.now()
    }
    
    // 缓存结果
    this.completed.set(task.id, task)
  }
  
  /**
   * 超时包装
   */
  private async withTimeout<T>(fn: () => Promise<T>, timeout: number): Promise<T> {
    return Promise.race([
      fn(),
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout after ${timeout}ms`)), timeout)
      )
    ])
  }
}

// ============================================================================
// 预配置控制器
// ============================================================================

/**
 * 创建适合图片生成的并发控制器
 * - 读操作：并发 5（读取提示词模板等）
 * - 写操作：并发 1（保存图片，避免磁盘竞争）
 */
export function createImageGeneratorController(): ConcurrencyController {
  return new ConcurrencyController({
    maxConcurrency: 5,
    maxWriteConcurrency: 1,
    defaultTimeout: 120000,  // 2 分钟超时（生图可能较慢）
    defaultRetryCount: 2
  })
}

/**
 * 创建适合文件操作的并发控制器
 */
export function createFileOperationController(): ConcurrencyController {
  return new ConcurrencyController({
    maxConcurrency: 10,
    maxWriteConcurrency: 2,
    defaultTimeout: 60000
  })
}

/**
 * 创建适合 API 调用的并发控制器
 */
export function createApiCallController(): ConcurrencyController {
  return new ConcurrencyController({
    maxConcurrency: 5,
    maxWriteConcurrency: 3,  // API 写操作可适度并发
    defaultTimeout: 30000,
    defaultRetryCount: 3,
    defaultRetryDelay: 500
  })
}

// ============================================================================
// 单例导出（可选）
// ============================================================================

// 全局默认控制器
let defaultController: ConcurrencyController | null = null

export function getDefaultController(): ConcurrencyController {
  if (!defaultController) {
    defaultController = new ConcurrencyController({
      maxConcurrency: 10,
      maxWriteConcurrency: 1
    })
  }
  return defaultController
}
