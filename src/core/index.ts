/**
 * Core Engine - 核心引擎
 * 
 * 所有机器人都能受益的基础设施：
 * - Session State: 会话状态持久化（掉线恢复）
 * - Progress: 进度反馈系统（实时展示）
 * - Concurrency: 并发控制器（智能调度）
 * - Context Cache: 上下文缓存管理（性能优化）
 * 
 * @module core
 */

// ============================================================================
// 导出：会话状态管理
// ============================================================================
export {
  sessionState,
  SessionStateManager,
  withSessionTask,
  type SessionStateData,
  type TaskProgress,
  type TaskStatus,
  type TaskType
} from './session-state.js'

// ============================================================================
// 导出：进度反馈系统
// ============================================================================
export {
  createProgressTracker,
  trackProgress,
  trackBatch,
  ProgressTracker,
  type ProgressState,
  type ProgressItem,
  type ProgressStatus,
  type ProgressType
} from './progress.js'

// ============================================================================
// 导出：并发控制器
// ============================================================================
export {
  ConcurrencyController,
  createImageGeneratorController,
  createFileOperationController,
  createApiCallController,
  getDefaultController,
  type ConcurrencyConfig,
  type Task,
  type TaskOptions,
  type OperationType
} from './concurrency.js'

// ============================================================================
// 导出：上下文缓存
// ============================================================================
export {
  contextCache,
  createContextCache,
  ContextCacheManager,
  compareSystemPrompts,
  extractPromptSignature,
  type CacheSafeParams,
  type CacheEntry,
  type CacheStats
} from './context-cache.js'

// ============================================================================
// 便捷组合函数
// ============================================================================

import { sessionState } from './session-state.js'
import { createProgressTracker, type ProgressType } from './progress.js'
import { ConcurrencyController, type ConcurrencyConfig } from './concurrency.js'
import { createContextCache } from './context-cache.js'

/**
 * 创建任务执行环境（组合所有核心能力）
 */
export async function createTaskEnvironment(
  taskType: string,
  taskName: string,
  options: {
    total?: number
    progressType?: ProgressType
    concurrency?: ConcurrencyConfig
    context?: any
  } = {}
) {
  const taskId = `task_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  
  // 1. 创建会话状态
  await sessionState.create(taskId, taskType as any, taskName, {
    total: options.total,
    context: options.context
  })
  
  // 2. 创建进度追踪器
  const progress = createProgressTracker({
    total: options.total || 1,
    type: options.progressType,
    onProgress: (state) => {
      // 自动同步到会话状态
      sessionState.update({
        current: state.current,
        status: state.status as any,
        details: state.details
      })
    }
  })
  
  // 3. 创建并发控制器
  const concurrency = new ConcurrencyController(
    options.concurrency || {
      maxConcurrency: 10,
      maxWriteConcurrency: 1
    }
  )
  
  // 4. 创建上下文缓存
  const cache = createContextCache()
  
  return {
    taskId,
    progress,
    concurrency,
    cache,
    
    /**
     * 完成任务
     */
    async complete(result?: any) {
      await progress.complete(undefined, result)
      await sessionState.complete(result)
    },
    
    /**
     * 任务失败
     */
    async fail(error: Error) {
      await progress.fail(error.message)
      await sessionState.fail({
        message: error.message,
        stack: error.stack
      })
    },
    
    /**
     * 清除状态
     */
    async cleanup() {
      await sessionState.clear()
      concurrency.clearCompleted()
    }
  }
}

/**
 * 恢复任务环境（掉线恢复用）
 */
export async function restoreTaskEnvironment() {
  const state = await sessionState.restore()
  
  if (!state) {
    return null
  }
  
  // 恢复进度追踪器
  const progress = createProgressTracker({
    total: state.progress.total,
    initialDetails: state.progress.details
  })
  
  // 恢复并发控制器
  const concurrency = new ConcurrencyController({
    maxConcurrency: 10,
    maxWriteConcurrency: 1
  })
  
  // 恢复上下文缓存
  const cache = createContextCache()
  
  return {
    taskId: state.taskId,
    state,
    progress,
    concurrency,
    cache,
    
    /**
     * 从断点继续
     */
    async resume() {
      // 恢复进度
      await progress.update({
        current: state.progress.current,
        status: state.progress.status as any,
        details: state.progress.details
      })
      
      // 恢复子任务状态
      if (state.subTasks) {
        for (const task of state.subTasks) {
          progress.addItem({
            id: task.id,
            name: task.name,
            status: task.status as any,
            result: task.result,
            error: task.error
          })
        }
      }
      
      return state
    }
  }
}
