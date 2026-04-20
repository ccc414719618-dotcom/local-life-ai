#!/usr/bin/env bun
/**
 * Core Engine 测试脚本
 * 
 * 运行：bun run src/core/test.ts
 */

import { describe, test, expect } from 'bun:test'
import { SessionStateManager } from './session-state.js'
import { ProgressTracker, createProgressTracker } from './progress.js'
import { ConcurrencyController } from './concurrency.js'
import { ContextCacheManager, createContextCache } from './context-cache.js'

// ============================================================================
// Session State 测试
// ============================================================================

describe('SessionStateManager', () => {
  test('创建任务状态', async () => {
    const manager = new SessionStateManager()
    
    const state = await manager.create(
      'test_001',
      'image_generation',
      '生成测试图片',
      { total: 5 }
    )
    
    expect(state.taskId).toBe('test_001')
    expect(state.progress.total).toBe(5)
    expect(state.progress.status).toBe('pending')
  })
  
  test('更新进度', async () => {
    const manager = new SessionStateManager()
    
    await manager.create('test_002', 'test', '测试', { total: 10 })
    
    const updated = await manager.update({
      current: 3,
      status: 'running',
      details: '处理中...'
    })
    
    expect(updated.progress.current).toBe(3)
    expect(updated.progress.percentage).toBe(30)
    expect(updated.progress.status).toBe('running')
  })
  
  test('添加子任务', async () => {
    const manager = new SessionStateManager()
    
    await manager.create('test_003', 'test', '测试', { total: 3 })
    
    await manager.addSubTask({
      id: 'sub_1',
      name: '子任务 1',
      status: 'completed',
      result: { path: '/tmp/test.png' }
    })
    
    await manager.addSubTask({
      id: 'sub_2',
      name: '子任务 2',
      status: 'running'
    })
    
    const state = manager.getState()
    expect(state?.subTasks?.length).toBe(2)
    expect(state?.subTasks?.[0].status).toBe('completed')
  })
})

// ============================================================================
// Progress 测试
// ============================================================================

describe('ProgressTracker', () => {
  test('创建进度追踪器', () => {
    const progress = createProgressTracker({
      total: 5,
      type: 'image_generation'
    })
    
    const state = progress.getState()
    expect(state.total).toBe(5)
    expect(state.status).toBe('pending')
  })
  
  test('更新进度', async () => {
    const progress = createProgressTracker({
      total: 10,
      initialDetails: '开始任务'
    })
    
    progress.start('任务启动')
    
    await progress.update({ current: 5, status: 'running' })
    
    const state = progress.getState()
    expect(state.percentage).toBe(50)
    expect(state.status).toBe('running')
  })
  
  test('子任务追踪', async () => {
    const progress = createProgressTracker({
      total: 3,
      type: 'batch_process'
    })
    
    progress.start()
    
    await progress.startItem('task_1', '任务 1')
    await progress.completeItem('task_1', { result: 'ok' }, 1000)
    
    await progress.startItem('task_2', '任务 2')
    await progress.failItem('task_2', '超时错误')
    
    const state = progress.getState()
    expect(state.subItems?.length).toBe(2)
    expect(state.subItems?.[0].status).toBe('completed')
    expect(state.subItems?.[1].status).toBe('failed')
  })
  
  test('进度条渲染', () => {
    const progress = createProgressTracker({ total: 10 })
    progress.start()
    
    progress.update({ current: 5 })
    
    const bar = progress.toProgressBar({ width: 20 })
    expect(bar).toContain('[██████████░░░░░░░░░░]')
    expect(bar).toContain('50%')
  })
})

// ============================================================================
// Concurrency 测试
// ============================================================================

describe('ConcurrencyController', () => {
  test('并发执行读任务', async () => {
    const controller = new ConcurrencyController({
      maxConcurrency: 3
    })
    
    const results = await Promise.all([
      controller.execute('read', 'read1', async () => {
        await new Promise(r => setTimeout(r, 100))
        return 'result1'
      }),
      controller.execute('read', 'read2', async () => {
        await new Promise(r => setTimeout(r, 100))
        return 'result2'
      }),
      controller.execute('read', 'read3', async () => {
        await new Promise(r => setTimeout(r, 100))
        return 'result3'
      })
    ])
    
    expect(results).toEqual(['result1', 'result2', 'result3'])
    
    const status = controller.getStatus()
    expect(status.completed).toBe(3)
  })
  
  test('串行执行写任务', async () => {
    const controller = new ConcurrencyController({
      maxConcurrency: 5,
      maxWriteConcurrency: 1
    })
    
    const execTimes: number[] = []
    
    const start = Date.now()
    
    // 串行执行，所以用 await 依次执行
    const p1 = controller.execute('write', 'write1', async () => {
      execTimes.push(Date.now() - start)
      await new Promise(r => setTimeout(r, 30))
      return 'w1'
    })
    
    const p2 = controller.execute('write', 'write2', async () => {
      execTimes.push(Date.now() - start)
      await new Promise(r => setTimeout(r, 30))
      return 'w2'
    })
    
    const p3 = controller.execute('write', 'write3', async () => {
      execTimes.push(Date.now() - start)
      await new Promise(r => setTimeout(r, 30))
      return 'w3'
    })
    
    await Promise.all([p1, p2, p3])
    
    // 验证串行执行（每个任务间隔约 30ms）
    expect(execTimes[1] - execTimes[0]).toBeGreaterThanOrEqual(25)
    expect(execTimes[2] - execTimes[1]).toBeGreaterThanOrEqual(25)
  })
  
  test('超时控制', async () => {
    const controller = new ConcurrencyController({
      defaultTimeout: 100
    })
    
    try {
      await controller.execute('read', 'slow', async () => {
        await new Promise(r => setTimeout(r, 200))
        return 'timeout'
      })
      throw new Error('应该超时但未超时')
    } catch (error: any) {
      expect(error.message).toContain('Timeout')
    }
  })
  
  test('重试机制', async () => {
    const controller = new ConcurrencyController({
      defaultRetryCount: 2,
      defaultRetryDelay: 10
    })
    
    let attempts = 0
    
    const result = await controller.execute('read', 'retry_test', async () => {
      attempts++
      if (attempts < 3) {
        throw new Error('临时错误')
      }
      return 'success'
    })
    
    expect(attempts).toBe(3)
    expect(result).toBe('success')
  })
})

// ============================================================================
// Context Cache 测试
// ============================================================================

describe('ContextCacheManager', () => {
  test('计算缓存键', () => {
    const cache = new ContextCacheManager()
    
    const key1 = cache.computeKey({
      systemPrompt: 'test prompt',
      model: 'claude-sonnet'
    })
    
    const key2 = cache.computeKey({
      systemPrompt: 'test prompt',
      model: 'claude-sonnet'
    })
    
    expect(key1).toBe(key2)
  })
  
  test('缓存共享检测', () => {
    const cache = new ContextCacheManager()
    
    const parentKey = cache.setSafeParams({
      systemPrompt: 'system prompt',
      tools: [{ name: 'Read' }],
      model: 'claude-sonnet'
    })
    
    const canShare = cache.canShare(
      {
        systemPrompt: 'system prompt',
        tools: [{ name: 'Read' }],
        model: 'claude-sonnet'
      },
      parentKey
    )
    
    expect(canShare).toBe(true)
  })
  
  test('缓存统计', () => {
    const cache = new ContextCacheManager()
    
    cache.setSafeParams({ systemPrompt: 'prompt1', model: 'm1' })
    cache.setSafeParams({ systemPrompt: 'prompt2', model: 'm2' })
    cache.setSafeParams({ systemPrompt: 'prompt1', model: 'm1' })  // 命中
    
    const stats = cache.getStats()
    
    expect(stats.totalEntries).toBe(2)
    expect(stats.totalHits).toBe(3)
    expect(stats.hitRate).toBeGreaterThan(0)
  })
  
  test('缓存修剪', () => {
    const cache = new ContextCacheManager({ maxEntries: 5 })
    
    // 添加 10 个条目
    for (let i = 0; i < 10; i++) {
      cache.setSafeParams({
        systemPrompt: `prompt_${i}`,
        model: 'test'
      })
    }
    
    const entries = cache.getEntries()
    expect(entries.length).toBeLessThanOrEqual(5)
  })
})

// ============================================================================
// 集成测试
// ============================================================================

describe('Core Engine Integration', () => {
  test('完整任务流程', async () => {
    // 1. 创建会话状态
    const session = new SessionStateManager()
    await session.create('integration_001', 'test', '集成测试', { total: 3 })
    
    // 2. 创建进度追踪（手动同步到 session）
    const progress = createProgressTracker({
      total: 3,
      onProgress: (state) => {
        session.update({ current: state.current, status: state.status as any })
      }
    })
    progress.start()
    
    // 3. 执行任务（并发执行）
    const results = await Promise.all([
      (async () => {
        await progress.startItem('t1', '任务 1')
        await new Promise(r => setTimeout(r, 30))
        await progress.completeItem('t1', 'r1')
        return 'r1'
      })(),
      (async () => {
        await progress.startItem('t2', '任务 2')
        await new Promise(r => setTimeout(r, 30))
        await progress.completeItem('t2', 'r2')
        return 'r2'
      })(),
      (async () => {
        await progress.startItem('t3', '任务 3')
        await new Promise(r => setTimeout(r, 30))
        await progress.completeItem('t3', 'r3')
        return 'r3'
      })()
    ])
    
    await progress.complete()
    await session.complete(results)
    
    // 等待异步更新完成
    await new Promise(r => setTimeout(r, 50))
    
    // 5. 验证结果
    const finalState = session.getState()
    expect(finalState?.progress.status).toBe('completed')
    expect(finalState?.progress.current).toBe(3)
    expect(results).toEqual(['r1', 'r2', 'r3'])
    
    // 6. 清理
    await session.clear()
  })
})

console.log('\n✅ 所有测试用例已加载\n')
