# 🚀 Core Engine 快速指南

> 所有机器人都能受益的基础设施层  
> **版本：** 1.0 | **日期：** 2026-04-04

---

## 📦 安装/使用

无需安装，直接使用：

```typescript
import { 
  createTaskEnvironment,
  restoreTaskEnvironment,
  sessionState,
  createProgressTracker,
  ConcurrencyController
} from './src/core/index.js'
```

---

## 🎯 场景 1：长任务防掉线

**问题：** 生图任务 7 分钟，OpenClaw 10 分钟超时，掉线后进度丢失

**解决：**

```typescript
import { createTaskEnvironment } from './src/core/index.js'

const env = await createTaskEnvironment('image_generation', '生成 5 张治愈系插画', {
  total: 5
})

try {
  env.progress.start('开始生成图片...')
  
  for (let i = 1; i <= 5; i++) {
    await env.progress.startItem(`img_${i}`, `生成图 ${i}`)
    
    // 生图逻辑（60 秒）
    const image = await generateImage(i)
    
    await env.progress.completeItem(`img_${i}`, image)
    // ✅ 每步自动写入 SESSION-STATE.md
  }
  
  await env.complete({ success: true })
  
} catch (error) {
  await env.fail(error as Error)
  throw error
}
```

**掉线恢复：**

```typescript
import { restoreTaskEnvironment } from './src/core/index.js'

// 尝试恢复之前的任务
const restored = await restoreTaskEnvironment()

if (restored) {
  console.log(`恢复任务：${restored.state.taskName}`)
  console.log(`进度：${restored.state.progress.percentage}%`)
  
  await restored.resume()
  
  // 从未完成的子任务继续
  const pendingTasks = restored.state.subTasks?.filter(
    t => t.status !== 'completed'
  ) || []
  
  for (const task of pendingTasks) {
    console.log(`继续执行：${task.name}`)
    // ... 继续
  }
}
```

---

## 🎯 场景 2：并发控制（读/写分离）

**问题：** 同时保存多个图片导致磁盘竞争

**解决：**

```typescript
import { ConcurrencyController } from './src/core/index.js'

const controller = new ConcurrencyController({
  maxConcurrency: 5,     // 读操作并发 5
  maxWriteConcurrency: 1 // 写操作串行
})

// 读取提示词模板（并发）
const templates = await Promise.all([
  controller.execute('read', '读取模板 1', () => loadTemplate(1)),
  controller.execute('read', '读取模板 2', () => loadTemplate(2)),
  controller.execute('read', '读取模板 3', () => loadTemplate(3))
])

// 保存图片（串行，避免磁盘竞争）
for (let i = 1; i <= 5; i++) {
  await controller.execute('write', `保存图片${i}`, () => saveImage(i))
}
```

**预配置控制器：**

```typescript
import { 
  createImageGeneratorController,
  createFileOperationController,
  createApiCallController
} from './src/core/index.js'

// 生图专用（读 5 并发，写 1 串行，2 分钟超时）
const imgController = createImageGeneratorController()

// 文件操作专用（读 10 并发，写 2 并发）
const fileController = createFileOperationController()

// API 调用专用（5 并发，30 秒超时，重试 3 次）
const apiController = createApiCallController()
```

---

## 🎯 场景 3：进度实时反馈

**问题：** 用户不知道任务执行到哪了

**解决：**

```typescript
import { createProgressTracker } from './src/core/index.js'

const progress = createProgressTracker({
  total: 5,
  type: 'image_generation',
  onProgress: (state) => {
    // 实时反馈给用户
    console.log(`${state.percentage}% - ${state.details}`)
    // 或者发送到飞书/微信
  }
})

progress.start('开始生成治愈系插画...')

// 方式 1：手动更新
await progress.update({ current: 1, status: 'running' })

// 方式 2：使用钩子包装
import { trackProgress } from './src/core/index.js'

const result = await trackProgress(
  progress,
  'img_1',
  '生成图 1',
  async () => generateImage(1)
)

// 方式 3：批量追踪（支持并发）
import { trackBatch } from './src/core/index.js'

const results = await trackBatch(
  progress,
  [
    { id: '1', name: '图 1', fn: () => generate(1) },
    { id: '2', name: '图 2', fn: () => generate(2) },
    { id: '3', name: '图 3', fn: () => generate(3) }
  ],
  { concurrent: 3 }  // 并发 3 个
)

await progress.complete('所有图片生成完成！')
```

**进度条渲染：**

```typescript
// 文本进度条
console.log(progress.toProgressBar({ width: 30 }))
// 输出：[███████████████░░░░░░░░░░] 50%

// 详细状态
console.log(progress.toString())
/* 输出：
🔄 正在进行：生成图 2
进度：40% (2/5)

  ✅ 图 1 (1.2s)
  🔄 图 2
  ⏸️ 图 3
  ⏸️ 图 4
  ⏸️ 图 5
*/
```

---

## 🎯 场景 4：上下文缓存优化

**问题：** 父子任务重复消耗 token

**解决：**

```typescript
import { createContextCache } from './src/core/index.js'

const cache = createContextCache()

// 父任务设置缓存
const parentKey = cache.setSafeParams({
  systemPrompt: '你是一个小红书运营专家...',
  tools: [{ name: 'Read' }, { name: 'Write' }],
  model: 'claude-sonnet-4'
})

// 子任务检查是否可共享缓存
const canShare = cache.canShare(
  {
    systemPrompt: '你是一个小红书运营专家...',
    model: 'claude-sonnet-4'
  },
  parentKey
)

if (canShare) {
  console.log('✅ 可以共享缓存，节省 token')
}

// 监控缓存命中率
const stats = cache.getStats()
console.log(`缓存命中率：${(stats.hitRate * 100).toFixed(2)}%`)
```

---

## 📊 SESSION-STATE.md 示例

任务运行时自动生成：

```markdown
# 📋 会话状态 - 生成治愈系插画

**任务 ID:** task_1712234567890_abc123
**任务类型:** image_generation
**状态:** 🔄 running

## 📊 进度

**总进度:** 40% (2/5)
**详情:** 正在进行：生成图 2

## ⏰ 时间

**开始时间:** 2026-04-04 17:00:00
**最后更新:** 2026-04-04 17:02:30

## ✅ 子任务

- ✅ 图 1：分类图 (img_1) → {"path": "/tmp/img_1.png"}
- 🔄 图 2：步骤 1 (img_2)
- ⏸️ 图 3：步骤 2 (img_3)
- ⏸️ 图 4：步骤 3 (img_4)
- ⏸️ 图 5：总结图 (img_5)
```

---

## 🧪 测试

运行完整测试套件：

```bash
cd /Volumes/1TB/openclaw/xiaohongshu-bot
bun test ./src/core/test.ts
```

**测试结果：**

```
bun test v1.3.10

src/core/test.ts:
(pass) SessionStateManager > 创建任务状态
(pass) SessionStateManager > 更新进度
(pass) ProgressTracker > 创建进度追踪器
(pass) ConcurrencyController > 并发执行读任务
(pass) ConcurrencyController > 串行执行写任务
...

16 pass
0 fail
```

---

## 📚 API 参考

### createTaskEnvironment

创建完整任务环境（推荐）

```typescript
const env = await createTaskEnvironment(
  taskType: string,
  taskName: string,
  options?: {
    total?: number
    progressType?: ProgressType
    concurrency?: ConcurrencyConfig
    context?: any
  }
)
```

### restoreTaskEnvironment

恢复之前的任务（掉线恢复）

```typescript
const restored = await restoreTaskEnvironment()
if (restored) {
  await restored.resume()
}
```

### createProgressTracker

创建进度追踪器

```typescript
const progress = createProgressTracker({
  total: number,
  type?: ProgressType,
  onProgress?: (state: ProgressState) => void,
  initialDetails?: string
})
```

### ConcurrencyController

并发控制器

```typescript
const controller = new ConcurrencyController({
  maxConcurrency: 10,
  maxWriteConcurrency: 1,
  defaultTimeout: 60000,
  defaultRetryCount: 0,
  defaultRetryDelay: 1000
})
```

---

## ⚠️ 注意事项

1. **任务完成后清理**
   ```typescript
   await env.cleanup()  // 清除 SESSION-STATE.md
   ```

2. **并发控制器缓存清理**
   ```typescript
   controller.clearCompleted()  // 定期清理
   ```

3. **写操作串行**
   - 默认 `maxWriteConcurrency: 1`
   - 避免磁盘/网络竞争

4. **超时设置**
   - 生图任务：120 秒
   - API 调用：30 秒
   - 文件操作：60 秒

---

## 🚧 待扩展

- [ ] 支持分布式锁（多实例）
- [ ] 支持任务依赖图
- [ ] 支持进度持久化到数据库
- [ ] 支持缓存持久化到磁盘

---

**文档维护者：** xiaohongshu-bot  
**最后更新：** 2026-04-04
