# Core Engine - 核心引擎

所有机器人都能受益的基础设施层。

---

## 📦 模块概览

```
src/core/
├── index.ts              # 统一导出 + 组合函数
├── session-state.ts      # 会话状态持久化
├── progress.ts           # 进度反馈系统
├── concurrency.ts        # 并发控制器
└── context-cache.ts      # 上下文缓存管理
```

---

## 🚀 快速开始

### 1. 完整任务环境（推荐）

```typescript
import { createTaskEnvironment } from './core/index.js'

// 创建任务环境
const env = await createTaskEnvironment('image_generation', '生成治愈系插画', {
  total: 5,
  progressType: 'image_generation',
  concurrency: {
    maxConcurrency: 5,
    maxWriteConcurrency: 1
  }
})

try {
  // 启动进度
  env.progress.start('开始生成图片...')
  
  // 并发执行读任务
  const templates = await env.concurrency.execute(
    'read',
    '加载提示词模板',
    async () => loadTemplates()
  )
  
  // 串行执行写任务
  for (let i = 1; i <= 5; i++) {
    await env.progress.startItem(`image_${i}`, `生成图 ${i}`)
    
    const image = await env.concurrency.execute(
      'write',
      `保存图片 ${i}`,
      async () => generateAndSave(i)
    )
    
    await env.progress.completeItem(`image_${i}`, image)
  }
  
  // 完成任务
  await env.complete({ success: true, count: 5 })
  
} catch (error) {
  await env.fail(error as Error)
  throw error
} finally {
  await env.cleanup()
}
```

---

### 2. 掉线恢复

```typescript
import { restoreTaskEnvironment } from './core/index.js'

// 尝试恢复之前的任务
const restored = await restoreTaskEnvironment()

if (restored) {
  console.log(`恢复任务：${restored.state.taskName}`)
  console.log(`进度：${restored.state.progress.percentage}%`)
  
  // 从断点继续
  await restored.resume()
  
  // 从未完成的子任务继续
  const pendingTasks = restored.state.subTasks?.filter(t => t.status !== 'completed') || []
  
  for (const task of pendingTasks) {
    console.log(`继续执行：${task.name}`)
    // ... 继续执行
  }
} else {
  console.log('无已保存的任务，创建新任务')
  // 创建新任务
}
```

---

### 3. 单独使用进度追踪

```typescript
import { createProgressTracker, trackProgress } from './core/progress.js'

const progress = createProgressTracker({
  total: 5,
  type: 'image_generation',
  onProgress: (state) => {
    console.log(`${state.percentage}% - ${state.details}`)
  }
})

progress.start('开始任务...')

// 方式 1：手动更新
await progress.update({ current: 1, details: '完成第 1 张' })

// 方式 2：使用钩子包装
const result = await trackProgress(
  progress,
  'task_1',
  '生成图 1',
  async () => {
    // 执行任务
    return { path: '/tmp/image1.png' }
  }
)

// 方式 3：批量追踪
import { trackBatch } from './core/progress.js'

const results = await trackBatch(
  progress,
  [
    { id: '1', name: '图 1', fn: () => generate(1) },
    { id: '2', name: '图 2', fn: () => generate(2) },
  ],
  { concurrent: 3 }  // 并发 3 个
)

await progress.complete('所有图片生成完成')
```

---

### 4. 并发控制

```typescript
import { ConcurrencyController } from './core/concurrency.js'

const controller = new ConcurrencyController({
  maxConcurrency: 10,
  maxWriteConcurrency: 1,  // 写操作串行
  defaultTimeout: 60000,
  defaultRetryCount: 2
})

// 只读任务（并发执行）
const [data1, data2, data3] = await Promise.all([
  controller.execute('read', '读取文件 1', () => readFile('file1')),
  controller.execute('read', '读取文件 2', () => readFile('file2')),
  controller.execute('read', '读取文件 3', () => readFile('file3'))
])

// 写任务（串行执行）
await controller.execute('write', '保存文件 1', () => writeFile('file1', data1))
await controller.execute('write', '保存文件 2', () => writeFile('file2', data2))

// 批量执行
const results = await controller.executeBatch([
  { type: 'read', name: '读取 A', fn: () => readA() },
  { type: 'read', name: '读取 B', fn: () => readB() },
  { type: 'write', name: '保存结果', fn: () => save(results) }
])

// 查看状态
console.log(controller.getStatus())
// {
//   readQueue: 0,
//   writeQueue: 0,
//   runningRead: 0,
//   runningWrite: 1,
//   completed: 5
// }
```

---

### 5. 上下文缓存

```typescript
import { createContextCache, contextCache } from './core/context-cache.js'

const cache = createContextCache()

// 设置缓存安全参数
const cacheKey = cache.setSafeParams({
  systemPrompt: '你是一个小红书运营专家...',
  tools: [{ name: 'Read' }, { name: 'Write' }],
  model: 'claude-sonnet-4'
})

// 检查是否可以共享父任务缓存
const canShare = cache.canShare(
  {
    systemPrompt: '你是一个小红书运营专家...',
    model: 'claude-sonnet-4'
  },
  parentCacheKey
)

if (canShare) {
  console.log('✅ 可以共享缓存，节省 token')
}

// 获取统计
const stats = cache.getStats()
console.log(`缓存命中率：${(stats.hitRate * 100).toFixed(2)}%`)
```

---

## 📊 SESSION-STATE.md 示例

任务运行时会自动生成 `SESSION-STATE.md`：

```markdown
# 📋 会话状态 - 生成治愈系插画

**任务 ID:** task_1712234567890_abc123
**任务类型:** image_generation
**状态:** ✅ completed

## 📊 进度

**总进度:** 100% (5/5)
**详情:** 任务已完成

## ⏰ 时间

**开始时间:** 2026-04-04 17:00:00
**最后更新:** 2026-04-04 17:07:30

## ✅ 子任务

- ✅ 图 1：分类图 (img_1) → {"path": "/tmp/img_1.png"}
- ✅ 图 2：步骤 1 (img_2) → {"path": "/tmp/img_2.png"}
- ✅ 图 3：步骤 2 (img_3) → {"path": "/tmp/img_3.png"}
- ✅ 图 4：步骤 3 (img_4) → {"path": "/tmp/img_4.png"}
- ✅ 图 5：总结图 (img_5) → {"path": "/tmp/img_5.png"}

## 🧠 上下文

**生成文件:** /tmp/img_1.png, /tmp/img_2.png, /tmp/img_3.png, /tmp/img_4.png, /tmp/img_5.png
**上传文件:** img_key_1, img_key_2, img_key_3, img_key_4, img_key_5
```

---

## 🎯 最佳实践

### 1. 长任务必须用 Session State

```typescript
// ✅ 正确：长任务持久化
await withSessionTask('image_generation', '生成 5 张图', { total: 5 }, async (state) => {
  for (let i = 1; i <= 5; i++) {
    await generateImage(i)
    await state.update({ current: i })
  }
})

// ❌ 错误：无持久化，掉线后丢失进度
for (let i = 1; i <= 5; i++) {
  await generateImage(i)  // 掉线后不知道执行到哪了
}
```

### 2. 读写分离并发

```typescript
// ✅ 正确：读并发，写串行
await controller.execute('read', '读取模板', () => loadTemplate())
await controller.execute('write', '保存图片', () => saveImage())  // 自动串行

// ❌ 错误：所有任务都用相同并发
await Promise.all([
  saveImage1(),  // 可能冲突
  saveImage2(),  // 可能冲突
  saveImage3()   // 可能冲突
])
```

### 3. 进度实时反馈

```typescript
// ✅ 正确：每步更新进度
await progress.startItem('img_1', '生成图 1')
const result = await generate()
await progress.completeItem('img_1', result)

// ❌ 错误：只在最后更新
await generateAll()
await progress.update({ current: 5 })  // 用户不知道中间进度
```

---

## 🔧 配置选项

### ConcurrencyController

| 选项 | 默认值 | 说明 |
|------|--------|------|
| maxConcurrency | 10 | 最大并发数 |
| maxWriteConcurrency | 1 | 写操作最大并发 |
| maxReadConcurrency | maxConcurrency | 读操作最大并发 |
| defaultTimeout | 60000 | 默认超时 (ms) |
| defaultRetryCount | 0 | 默认重试次数 |
| defaultRetryDelay | 1000 | 默认重试间隔 (ms) |

### ContextCacheManager

| 选项 | 默认值 | 说明 |
|------|--------|------|
| maxEntries | 100 | 最大缓存条目数 |

---

## 📝 注意事项

1. **SESSION-STATE.md 位置**: 工作区根目录
2. **任务完成后清理**: 调用 `cleanup()` 避免状态文件累积
3. **并发控制器缓存**: 定期调用 `clearCompleted()` 清理已完成任务
4. **缓存命中率**: 使用 `getStats()` 监控缓存效果

---

## 🚧 待扩展

- [ ] 支持分布式锁（多实例场景）
- [ ] 支持任务优先级队列
- [ ] 支持任务依赖图
- [ ] 支持进度持久化到数据库
- [ ] 支持缓存持久化到磁盘

---

_最后更新：2026-04-04_
