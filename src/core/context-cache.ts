/**
 * Context Cache Manager - 上下文缓存管理
 * 
 * 核心能力：
 * 1. Prompt 缓存键管理
 * 2. 父子任务缓存共享
 * 3. 缓存命中率追踪
 * 4. 自动失效策略
 * 
 * 使用方式：
 * ```typescript
 * const cache = createContextCache()
 * 
 * // 设置缓存安全参数
 * const cacheKey = cache.setSafeParams({
 *   systemPrompt: '...',
 *   tools: [...],
 *   model: 'claude-sonnet'
 * })
 * 
 * // 检查是否可共享缓存
 * if (cache.canShare(parentCacheKey)) {
 *   // 共享父任务缓存
 * }
 * ```
 */

import { createHash } from 'crypto'

// ============================================================================
// 类型定义
// ============================================================================

export interface CacheSafeParams {
  systemPrompt: string
  tools?: any[]
  model: string
  thinkingConfig?: any
}

export interface CacheEntry {
  key: string
  params: CacheSafeParams
  createdAt: number
  hits: number
  lastHitAt?: number
  parentId?: string
  metadata?: Record<string, any>
}

export interface CacheStats {
  totalEntries: number
  totalHits: number
  hitRate: number
  oldestEntry?: number
  newestEntry?: number
}

// ============================================================================
// 缓存管理类
// ============================================================================

export class ContextCacheManager {
  private entries: Map<string, CacheEntry> = new Map()
  private currentKey: string | null = null
  private maxEntries: number
  
  constructor(options?: { maxEntries?: number }) {
    this.maxEntries = options?.maxEntries || 100
  }
  
  /**
   * 计算缓存键
   */
  computeKey(params: CacheSafeParams): string {
    const content = JSON.stringify({
      systemPrompt: params.systemPrompt,
      tools: params.tools?.map(t => t.name || t),
      model: params.model,
      thinkingConfig: params.thinkingConfig
    })
    
    return `cache_${createHash('sha256').update(content).digest('hex').slice(0, 16)}`
  }
  
  /**
   * 设置缓存安全参数
   */
  setSafeParams(params: CacheSafeParams, options?: {
    parentId?: string
    metadata?: Record<string, any>
  }): string {
    const key = this.computeKey(params)
    
    const existing = this.entries.get(key)
    
    if (existing) {
      // 命中现有缓存
      existing.hits++
      existing.lastHitAt = Date.now()
      this.currentKey = key
      return key
    }
    
    // 创建新缓存条目
    const entry: CacheEntry = {
      key,
      params,
      createdAt: Date.now(),
      hits: 1,
      parentId: options?.parentId,
      metadata: options?.metadata
    }
    
    this.entries.set(key, entry)
    this.currentKey = key
    
    // 清理过期条目
    this.prune()
    
    return key
  }
  
  /**
   * 获取缓存条目
   */
  getEntry(key: string): CacheEntry | undefined {
    const entry = this.entries.get(key)
    
    if (entry) {
      entry.hits++
      entry.lastHitAt = Date.now()
    }
    
    return entry
  }
  
  /**
   * 检查是否可以共享缓存
   */
  canShare(childParams: CacheSafeParams, parentKey: string): boolean {
    const parentEntry = this.entries.get(parentKey)
    
    if (!parentEntry) {
      return false
    }
    
    // 检查关键参数是否一致
    const childKey = this.computeKey(childParams)
    
    // 如果键相同，直接共享
    if (childKey === parentKey) {
      return true
    }
    
    // 检查是否只有非关键参数不同
    const criticalMatch = 
      childParams.systemPrompt === parentEntry.params.systemPrompt &&
      childParams.model === parentEntry.params.model &&
      JSON.stringify(childParams.tools?.map(t => t.name || t)) ===
        JSON.stringify(parentEntry.params.tools?.map(t => t.name || t))
    
    return criticalMatch
  }
  
  /**
   * 获取当前缓存键
   */
  getCurrentKey(): string | null {
    return this.currentKey
  }
  
  /**
   * 获取缓存统计
   */
  getStats(): CacheStats {
    const entries = Array.from(this.entries.values())
    const totalHits = entries.reduce((sum, e) => sum + e.hits, 0)
    
    return {
      totalEntries: entries.length,
      totalHits,
      hitRate: entries.length > 0 ? (totalHits - entries.length) / totalHits : 0,
      oldestEntry: entries.length > 0 ? Math.min(...entries.map(e => e.createdAt)) : undefined,
      newestEntry: entries.length > 0 ? Math.max(...entries.map(e => e.createdAt)) : undefined
    }
  }
  
  /**
   * 获取所有条目（用于调试）
   */
  getEntries(): CacheEntry[] {
    return Array.from(this.entries.values())
  }
  
  /**
   * 清除缓存
   */
  clear(): void {
    this.entries.clear()
    this.currentKey = null
  }
  
  /**
   * 清除指定条目
   */
  delete(key: string): boolean {
    const result = this.entries.delete(key)
    
    if (this.currentKey === key) {
      this.currentKey = null
    }
    
    return result
  }
  
  /**
   * 修剪缓存（移除最旧的条目）
   */
  private prune(): void {
    if (this.entries.size <= this.maxEntries) {
      return
    }
    
    const entries = Array.from(this.entries.entries())
      .sort((a, b) => a[1].createdAt - b[1].createdAt)
    
    // 移除最旧的 20%
    const toRemove = Math.ceil(this.entries.size * 0.2)
    
    for (let i = 0; i < toRemove; i++) {
      this.entries.delete(entries[i][0])
    }
  }
  
  /**
   * 导出缓存（用于持久化）
   */
  export(): object {
    return {
      entries: Array.from(this.entries.values()),
      currentKey: this.currentKey,
      exportedAt: new Date().toISOString()
    }
  }
  
  /**
   * 导入缓存（用于恢复）
   */
  import(data: any): void {
    if (!data?.entries) return
    
    for (const entry of data.entries) {
      this.entries.set(entry.key, entry)
    }
    
    if (data.currentKey) {
      this.currentKey = data.currentKey
    }
  }
}

// ============================================================================
// 工厂函数
// ============================================================================

export function createContextCache(options?: { maxEntries?: number }): ContextCacheManager {
  return new ContextCacheManager(options)
}

// ============================================================================
// 便捷工具
// ============================================================================

/**
 * 快速比较两个系统提示词是否等价
 */
export function compareSystemPrompts(a: string, b: string): boolean {
  // 忽略空白字符差异
  const normalize = (s: string) => s.replace(/\s+/g, ' ').trim()
  return normalize(a) === normalize(b)
}

/**
 * 提取系统提示词的关键部分（用于快速比较）
 */
export function extractPromptSignature(prompt: string): string {
  // 提取前 100 个字符作为签名
  return prompt.slice(0, 100).replace(/\s+/g, ' ')
}

// ============================================================================
// 单例导出
// ============================================================================

export const contextCache = new ContextCacheManager()
