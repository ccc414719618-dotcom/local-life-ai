/**
 * Session State Manager - 会话状态持久化
 * 
 * 核心能力：
 * 1. 任务进度实时写入（WAL 协议）
 * 2. 掉线自动恢复
 * 3. 断点续传支持
 * 
 * 使用方式：
 * ```typescript
 * const state = await sessionState.create('task_001', {
 *   type: 'image_generation',
 *   total: 5,
 *   current: 0
 * })
 * 
 * await state.update({ current: 1, status: 'completed' })
 * await state.complete()
 * ```
 */

import { readFile, writeFile, access } from 'fs/promises'
import { join } from 'path'

// ============================================================================
// 类型定义
// ============================================================================

export type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed'

export type TaskType = 
  | 'image_generation'
  | 'feishu_card'
  | 'batch_generate'
  | 'content_review'
  | 'data_analysis'
  | string  // 支持自定义

export interface TaskProgress {
  current: number
  total: number
  percentage: number
  status: TaskStatus
  details?: string
}

export interface SessionStateData {
  // 任务基本信息
  taskId: string
  taskType: TaskType
  taskName: string
  
  // 进度追踪
  progress: TaskProgress
  subTasks?: Array<{
    id: string
    name: string
    status: TaskStatus
    result?: any
    error?: string
  }>
  
  // 时间追踪
  startTime: string
  lastUpdateTime: string
  estimatedEndTime?: string
  
  // 上下文缓存（用于断点续传）
  context?: {
    systemPromptHash?: string
    lastCacheSafeParams?: any
    generatedFiles?: string[]
    uploadedFiles?: string[]
  }
  
  // 错误处理
  error?: {
    message: string
    stack?: string
    retryCount: number
    lastRetryTime?: string
  }
  
  // 元数据
  metadata?: Record<string, any>
}

// ============================================================================
// 状态文件路径
// ============================================================================

const STATE_FILE = join(process.cwd(), 'SESSION-STATE.md')

// ============================================================================
// 核心类
// ============================================================================

export class SessionStateManager {
  private state: SessionStateData | null = null
  private writeQueue: Promise<void> = Promise.resolve()
  
  /**
   * 创建新任务状态
   */
  async create(taskId: string, taskType: TaskType, taskName: string, options?: {
    total?: number
    context?: SessionStateData['context']
    metadata?: Record<string, any>
  }): Promise<SessionStateData> {
    const now = new Date().toISOString()
    
    this.state = {
      taskId,
      taskType,
      taskName,
      progress: {
        current: 0,
        total: options?.total || 1,
        percentage: 0,
        status: 'pending',
        details: '任务已创建，等待启动'
      },
      subTasks: [],
      startTime: now,
      lastUpdateTime: now,
      context: options?.context,
      metadata: options?.metadata
    }
    
    await this.persist()
    return this.state
  }
  
  /**
   * 从文件恢复状态（掉线恢复用）
   */
  async restore(): Promise<SessionStateData | null> {
    try {
      await access(STATE_FILE)
      const content = await readFile(STATE_FILE, 'utf-8')
      
      // 解析 Markdown 格式的 state 文件
      const stateJson = this.parseMarkdownState(content)
      if (stateJson) {
        this.state = stateJson
        return this.state
      }
    } catch (error) {
      // 文件不存在或解析失败，返回 null
      console.log('[SessionState] 无已保存的状态，创建新任务')
    }
    
    return null
  }
  
  /**
   * 更新任务进度
   */
  async update(progress: Partial<TaskProgress>): Promise<SessionStateData> {
    if (!this.state) {
      throw new Error('Session state not initialized. Call create() first.')
    }
    
    // 合并进度
    this.state.progress = {
      ...this.state.progress,
      ...progress,
      percentage: progress.current !== undefined 
        ? Math.round((progress.current / this.state.progress.total) * 100)
        : this.state.progress.percentage
    }
    
    this.state.lastUpdateTime = new Date().toISOString()
    
    // 更新状态
    if (progress.status) {
      this.state.progress.status = progress.status
    }
    
    await this.persist()
    return this.state
  }
  
  /**
   * 添加子任务
   */
  async addSubTask(subTask: {
    id: string
    name: string
    status: TaskStatus
    result?: any
    error?: string
  }): Promise<void> {
    if (!this.state) {
      throw new Error('Session state not initialized')
    }
    
    if (!this.state.subTasks) {
      this.state.subTasks = []
    }
    
    // 检查是否已存在
    const existingIndex = this.state.subTasks.findIndex(t => t.id === subTask.id)
    
    if (existingIndex >= 0) {
      // 更新现有子任务
      this.state.subTasks[existingIndex] = {
        ...this.state.subTasks[existingIndex],
        ...subTask
      }
    } else {
      // 添加新子任务
      this.state.subTasks.push(subTask)
    }
    
    this.state.lastUpdateTime = new Date().toISOString()
    await this.persist()
  }
  
  /**
   * 更新子任务状态
   */
  async updateSubTask(taskId: string, updates: Partial<typeof this.state.subTasks>[number]): Promise<void> {
    if (!this.state?.subTasks) {
      throw new Error('Session state not initialized or no subTasks')
    }
    
    const index = this.state.subTasks.findIndex(t => t.id === taskId)
    if (index === -1) {
      throw new Error(`SubTask not found: ${taskId}`)
    }
    
    this.state.subTasks[index] = {
      ...this.state.subTasks[index],
      ...updates
    }
    
    this.state.lastUpdateTime = new Date().toISOString()
    await this.persist()
  }
  
  /**
   * 标记任务完成
   */
  async complete(result?: any): Promise<SessionStateData> {
    return this.update({
      status: 'completed',
      details: result ? `完成：${JSON.stringify(result)}` : '任务已完成'
    })
  }
  
  /**
   * 标记任务失败
   */
  async fail(error: { message: string; stack?: string }): Promise<SessionStateData> {
    if (!this.state) {
      throw new Error('Session state not initialized')
    }
    
    this.state.error = {
      message: error.message,
      stack: error.stack,
      retryCount: this.state.error?.retryCount || 0
    }
    
    return this.update({
      status: 'failed',
      details: `失败：${error.message}`
    })
  }
  
  /**
   * 获取当前状态
   */
  getState(): SessionStateData | null {
    return this.state
  }
  
  /**
   * 清除状态文件（任务完成后）
   */
  async clear(): Promise<void> {
    this.state = null
    try {
      await writeFile(STATE_FILE, '', 'utf-8')
    } catch (error) {
      console.error('[SessionState] 清除状态失败:', error)
    }
  }
  
  /**
   * 持久化状态到文件（WAL 协议）
   */
  private async persist(): Promise<void> {
    if (!this.state) return
    
    // 队列化写入，避免并发冲突
    this.writeQueue = this.writeQueue.then(async () => {
      try {
        const markdown = this.toMarkdown(this.state)
        await writeFile(STATE_FILE, markdown, 'utf-8')
      } catch (error) {
        console.error('[SessionState] 持久化失败:', error)
      }
    })
    
    await this.writeQueue
  }
  
  /**
   * 将状态转换为 Markdown 格式
   */
  private toMarkdown(state: SessionStateData): string {
    const lines: string[] = [
      `# 📋 会话状态 - ${state.taskName}`,
      '',
      `**任务 ID:** ${state.taskId}`,
      `**任务类型:** ${state.taskType}`,
      `**状态:** ${this.statusEmoji(state.progress.status)} ${state.progress.status}`,
      '',
      '## 📊 进度',
      '',
      `**总进度:** ${state.progress.percentage}% (${state.progress.current}/${state.progress.total})`,
      state.progress.details ? `**详情:** ${state.progress.details}` : '',
      '',
      '## ⏰ 时间',
      '',
      `**开始时间:** ${this.formatTime(state.startTime)}`,
      `**最后更新:** ${this.formatTime(state.lastUpdateTime)}`,
      state.estimatedEndTime ? `**预计完成:** ${this.formatTime(state.estimatedEndTime)}` : '',
    ]
    
    // 子任务列表
    if (state.subTasks && state.subTasks.length > 0) {
      lines.push('', '## ✅ 子任务', '')
      for (const task of state.subTasks) {
        const emoji = this.statusEmoji(task.status)
        const result = task.result ? ` → ${JSON.stringify(task.result)}` : ''
        const error = task.error ? ` ❌ ${task.error}` : ''
        lines.push(`- ${emoji} **${task.name}** (${task.id})${result}${error}`)
      }
    }
    
    // 上下文信息
    if (state.context) {
      lines.push('', '## 🧠 上下文', '')
      if (state.context.generatedFiles?.length) {
        lines.push(`**生成文件:** ${state.context.generatedFiles.join(', ')}`)
      }
      if (state.context.uploadedFiles?.length) {
        lines.push(`**上传文件:** ${state.context.uploadedFiles.join(', ')}`)
      }
    }
    
    // 错误信息
    if (state.error) {
      lines.push(
        '',
        '## ❌ 错误',
        '',
        `**消息:** ${state.error.message}`,
        `**重试次数:** ${state.error.retryCount}`,
        state.error.lastRetryTime ? `**最后重试:** ${this.formatTime(state.error.lastRetryTime)}` : ''
      )
    }
    
    // 元数据
    if (state.metadata && Object.keys(state.metadata).length > 0) {
      lines.push('', '## 📝 元数据', '')
      for (const [key, value] of Object.entries(state.metadata)) {
        lines.push(`- **${key}:** ${value}`)
      }
    }
    
    lines.push('', '---', '', `_最后更新：${new Date().toISOString()}_`)
    
    return lines.join('\n')
  }
  
  /**
   * 从 Markdown 解析状态
   */
  private parseMarkdownState(markdown: string): SessionStateData | null {
    try {
      // 简单实现：查找 JSON 块
      const jsonMatch = markdown.match(/```json\n([\s\S]*?)\n```/)
      if (jsonMatch) {
        return JSON.parse(jsonMatch[1])
      }
      
      // 或者尝试从文本中提取关键信息
      // TODO: 实现更完善的解析
      return null
    } catch (error) {
      console.error('[SessionState] 解析 Markdown 失败:', error)
      return null
    }
  }
  
  /**
   * 状态转 Emoji
   */
  private statusEmoji(status: TaskStatus): string {
    const map: Record<TaskStatus, string> = {
      pending: '⏸️',
      running: '🔄',
      paused: '⏸️',
      completed: '✅',
      failed: '❌'
    }
    return map[status] || '❓'
  }
  
  /**
   * 格式化时间
   */
  private formatTime(isoString: string): string {
    return new Date(isoString).toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour12: false
    })
  }
}

// ============================================================================
// 单例导出
// ============================================================================

export const sessionState = new SessionStateManager()

// ============================================================================
// 便捷函数
// ============================================================================

/**
 * 快速创建并启动任务
 */
export async function withSessionTask<T>(
  taskType: TaskType,
  taskName: string,
  options: {
    total?: number
    context?: SessionStateData['context']
  },
  fn: (state: SessionStateManager) => Promise<T>
): Promise<T> {
  const taskId = `task_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  
  try {
    await sessionState.create(taskId, taskType, taskName, options)
    const result = await fn(sessionState)
    await sessionState.complete(result)
    return result
  } catch (error) {
    await sessionState.fail({
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined
    })
    throw error
  }
}
