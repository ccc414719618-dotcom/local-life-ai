/**
 * Progress Feedback System - 进度反馈系统
 * 
 * 核心能力：
 * 1. 统一进度接口
 * 2. 流式进度回调
 * 3. 多进度类型支持
 * 4. UI 渲染辅助
 * 
 * 使用方式：
 * ```typescript
 * const progress = createProgressTracker({
 *   total: 5,
 *   type: 'image_generation',
 *   onProgress: (p) => console.log(`${p.percentage}% - ${p.details}`)
 * })
 * 
 * await progress.step('生成图 1', async () => {
 *   // 执行任务
 *   await progress.update({ current: 1, status: 'completed' })
 * })
 * ```
 */

// ============================================================================
// 类型定义
// ============================================================================

export type ProgressStatus = 
  | 'pending'    // 等待中
  | 'running'    // 进行中
  | 'completed'  // 已完成
  | 'failed'     // 失败
  | 'skipped'    // 跳过

export type ProgressType =
  | 'image_generation'  // 图片生成
  | 'file_upload'       // 文件上传
  | 'card_send'         // 卡片发送
  | 'batch_process'     // 批量处理
  | 'api_call'          // API 调用
  | 'custom'            // 自定义

export interface ProgressItem {
  id: string
  name: string
  status: ProgressStatus
  startTime?: number
  endTime?: number
  duration?: number
  error?: string
  result?: any
}

export interface ProgressState {
  // 总体进度
  total: number
  current: number
  percentage: number
  status: ProgressStatus
  
  // 类型信息
  type: ProgressType
  
  // 详情
  details?: string
  subItems?: ProgressItem[]
  
  // 时间追踪
  startTime: number
  lastUpdateTime: number
  estimatedRemaining?: number  // 预估剩余时间 (ms)
  
  // 回调
  onProgress?: (state: ProgressState) => void
}

// ============================================================================
// 进度追踪器类
// ============================================================================

export class ProgressTracker {
  private state: ProgressState
  private items: Map<string, ProgressItem> = new Map()
  
  constructor(options: {
    total: number
    type?: ProgressType
    onProgress?: (state: ProgressState) => void
    initialDetails?: string
  }) {
    const now = Date.now()
    
    this.state = {
      total: options.total,
      current: 0,
      percentage: 0,
      status: 'pending',
      type: options.type || 'custom',
      details: options.initialDetails || '准备中...',
      subItems: [],
      startTime: now,
      lastUpdateTime: now,
      onProgress: options.onProgress
    }
  }
  
  /**
   * 开始任务
   */
  start(details?: string): ProgressState {
    this.state.status = 'running'
    this.state.details = details || '任务进行中...'
    this.state.startTime = Date.now()
    this.state.lastUpdateTime = Date.now()
    this.notify()
    return this.state
  }
  
  /**
   * 更新进度
   */
  async update(updates: Partial<ProgressState>): Promise<ProgressState> {
    // 合并更新
    if (updates.current !== undefined) {
      this.state.current = updates.current
      this.state.percentage = Math.round((this.state.current / this.state.total) * 100)
    }
    
    if (updates.status) {
      this.state.status = updates.status
    }
    
    if (updates.details) {
      this.state.details = updates.details
    }
    
    if (updates.estimatedRemaining !== undefined) {
      this.state.estimatedRemaining = updates.estimatedRemaining
    }
    
    this.state.lastUpdateTime = Date.now()
    this.notify()
    
    return this.state
  }
  
  /**
   * 完成一个子项
   */
  async completeItem(
    itemId: string,
    result?: any,
    duration?: number
  ): Promise<ProgressItem> {
    const item = this.items.get(itemId)
    
    if (item) {
      item.status = 'completed'
      item.endTime = Date.now()
      item.duration = duration || (item.endTime - (item.startTime || Date.now()))
      item.result = result
    } else {
      // 自动创建
      const newItem: ProgressItem = {
        id: itemId,
        name: itemId,
        status: 'completed',
        startTime: Date.now(),
        endTime: Date.now(),
        duration: duration || 0,
        result
      }
      this.items.set(itemId, newItem)
    }
    
    // 更新总进度
    const completedCount = Array.from(this.items.values())
      .filter(i => i.status === 'completed').length
    
    await this.update({
      current: completedCount,
      details: `已完成 ${completedCount}/${this.state.total}`
    })
    
    return this.items.get(itemId)!
  }
  
  /**
   * 添加子项
   */
  addItem(item: Omit<ProgressItem, 'status'> & { status?: ProgressStatus }): ProgressItem {
    const progressItem: ProgressItem = {
      ...item,
      status: item.status || 'pending'
    }
    
    this.items.set(item.id, progressItem)
    this.updateSubItems()
    
    return progressItem
  }
  
  /**
   * 更新子项状态
   */
  updateItem(itemId: string, updates: Partial<ProgressItem>): ProgressItem | null {
    const item = this.items.get(itemId)
    
    if (!item) {
      return null
    }
    
    Object.assign(item, updates)
    this.updateSubItems()
    
    return item
  }
  
  /**
   * 标记子项进行中
   */
  async startItem(itemId: string, name?: string): Promise<ProgressItem> {
    let item = this.items.get(itemId)
    
    if (!item) {
      item = {
        id: itemId,
        name: name || itemId,
        status: 'pending'
      }
      this.items.set(itemId, item)
    }
    
    item.status = 'running'
    item.startTime = Date.now()
    item.name = name || item.name
    
    this.updateSubItems()
    
    await this.update({
      details: `正在进行：${item.name}`
    })
    
    return item
  }
  
  /**
   * 标记子项失败
   */
  async failItem(itemId: string, error: string): Promise<ProgressItem> {
    const item = this.items.get(itemId)
    
    if (item) {
      item.status = 'failed'
      item.endTime = Date.now()
      item.error = error
      this.updateSubItems()
    }
    
    return item!
  }
  
  /**
   * 完成任务
   */
  async complete(finalDetails?: string, result?: any): Promise<ProgressState> {
    this.state.status = 'completed'
    this.state.current = this.state.total
    this.state.percentage = 100
    this.state.details = finalDetails || '任务已完成'
    this.state.lastUpdateTime = Date.now()
    
    this.notify()
    return this.state
  }
  
  /**
   * 任务失败
   */
  async fail(error: string, details?: string): Promise<ProgressState> {
    this.state.status = 'failed'
    this.state.details = details || `失败：${error}`
    this.state.lastUpdateTime = Date.now()
    
    this.notify()
    return this.state
  }
  
  /**
   * 获取当前状态
   */
  getState(): ProgressState {
    return { ...this.state, subItems: Array.from(this.items.values()) }
  }
  
  /**
   * 获取预估剩余时间
   */
  estimateRemaining(): number | undefined {
    const completed = Array.from(this.items.values())
      .filter(i => i.status === 'completed' && i.duration)
    
    if (completed.length === 0) {
      return undefined
    }
    
    const avgDuration = completed.reduce((sum, i) => sum + (i.duration || 0), 0) / completed.length
    const remaining = this.state.total - this.state.current
    
    return avgDuration * remaining
  }
  
  /**
   * 格式化为文本（用于日志/显示）
   */
  toString(): string {
    const emoji = this.statusEmoji(this.state.status)
    const lines = [
      `${emoji} ${this.state.details || '任务进行中'}`,
      `进度：${this.state.percentage}% (${this.state.current}/${this.state.total})`
    ]
    
    // 添加子项状态
    const items = Array.from(this.items.values())
    if (items.length > 0) {
      lines.push('')
      for (const item of items) {
        const itemEmoji = this.statusEmoji(item.status)
        const duration = item.duration ? ` (${(item.duration / 1000).toFixed(1)}s)` : ''
        const error = item.error ? ` ❌ ${item.error}` : ''
        lines.push(`  ${itemEmoji} ${item.name}${duration}${error}`)
      }
    }
    
    return lines.join('\n')
  }
  
  /**
   * 格式化为进度条
   */
  toProgressBar(options?: { width?: number; showPercentage?: boolean }): string {
    const width = options?.width || 30
    const showPercentage = options?.showPercentage ?? true
    
    const percentage = Math.min(100, Math.max(0, this.state.percentage))
    const filled = Math.round((percentage / 100) * width)
    const empty = Math.max(0, width - filled)
    
    const bar = '█'.repeat(filled) + '░'.repeat(empty)
    const pctText = showPercentage ? ` ${percentage}%` : ''
    
    return `[${bar}]${pctText}`
  }
  
  private updateSubItems(): void {
    this.state.subItems = Array.from(this.items.values())
    this.notify()
  }
  
  private notify(): void {
    if (this.state.onProgress) {
      this.state.onProgress(this.getState())
    }
  }
  
  private statusEmoji(status: ProgressStatus): string {
    const map: Record<ProgressStatus, string> = {
      pending: '⏸️',
      running: '🔄',
      completed: '✅',
      failed: '❌',
      skipped: '⏭️'
    }
    return map[status] || '❓'
  }
}

// ============================================================================
// 工厂函数
// ============================================================================

export function createProgressTracker(options: {
  total: number
  type?: ProgressType
  onProgress?: (state: ProgressState) => void
  initialDetails?: string
}): ProgressTracker {
  return new ProgressTracker(options)
}

// ============================================================================
// 便捷钩子
// ============================================================================

/**
 * 包装一个异步函数，自动追踪进度
 */
export async function trackProgress<T>(
  tracker: ProgressTracker,
  itemId: string,
  itemName: string,
  fn: () => Promise<T>
): Promise<T> {
  await tracker.startItem(itemId, itemName)
  
  const startTime = Date.now()
  
  try {
    const result = await fn()
    const duration = Date.now() - startTime
    
    await tracker.completeItem(itemId, result, duration)
    
    return result
  } catch (error) {
    await tracker.failItem(itemId, error instanceof Error ? error.message : String(error))
    throw error
  }
}

/**
 * 批量追踪多个任务
 */
export async function trackBatch<T>(
  tracker: ProgressTracker,
  items: Array<{ id: string; name: string; fn: () => Promise<T> }>,
  options?: { concurrent?: number }
): Promise<T[]> {
  const concurrent = options?.concurrent || 1
  const results: T[] = []
  
  if (concurrent === 1) {
    // 串行执行
    for (const item of items) {
      const result = await trackProgress(tracker, item.id, item.name, item.fn)
      results.push(result)
    }
  } else {
    // 并发执行
    const queue = [...items]
    const running = new Set<Promise<void>>()
    
    while (queue.length > 0 || running.size > 0) {
      // 填充并发槽位
      while (running.size < concurrent && queue.length > 0) {
        const item = queue.shift()!
        const promise = trackProgress(tracker, item.id, item.name, item.fn)
          .then(result => {
            results.push(result)
            running.delete(promise)
          })
          .catch(() => {
            running.delete(promise)
          })
        
        running.add(promise)
      }
      
      // 等待至少一个完成
      if (running.size > 0) {
        await Promise.race(running)
      }
    }
  }
  
  await tracker.complete()
  return results
}
