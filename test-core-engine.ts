#!/usr/bin/env bun
/**
 * 核心引擎实战测试
 * 
 * 模拟场景：生成 5 张治愈系插画教程图片
 * - 每张图片生成模拟耗时 2 秒
 * - 上传图片模拟耗时 1 秒
 * - 总耗时约 15 秒
 * 
 * 运行：bun run test-core-engine.ts
 */

import { 
  createTaskEnvironment,
  restoreTaskEnvironment,
  ConcurrencyController,
  trackBatch
} from './src/core/index.js'
import { writeFile, readFile } from 'fs/promises'
import { join } from 'path'

// ============================================================================
// 模拟服务：Gemini 生图
// ============================================================================

async function mockGeminiGenerate(prompt: string, index: number): Promise<{ path: string; size: number }> {
  // 模拟生图耗时（1.5-3 秒随机）
  const delay = 1500 + Math.random() * 1500
  await new Promise(r => setTimeout(r, delay))
  
  const outputPath = join(process.cwd(), 'tmp', `test_img_${index}.png`)
  
  // 模拟生成图片文件
  await writeFile(outputPath, `MOCK_IMAGE_DATA_${index}\nPrompt: ${prompt}`)
  
  const stat = await readFile(outputPath)
  
  return {
    path: outputPath,
    size: stat.length
  }
}

// ============================================================================
// 模拟服务：飞书上传
// ============================================================================

async function mockFeishuUpload(imagePath: string): Promise<{ img_key: string }> {
  // 模拟上传耗时（0.5-1.5 秒随机）
  const delay = 500 + Math.random() * 1000
  await new Promise(r => setTimeout(r, delay))
  
  return {
    img_key: `img_key_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  }
}

// ============================================================================
// 测试 1：完整任务流程（带进度追踪 + 并发控制）
// ============================================================================

async function test1_fullWorkflow() {
  console.log('\n' + '='.repeat(60))
  console.log('🧪 测试 1：完整任务流程（带进度追踪 + 并发控制）')
  console.log('='.repeat(60) + '\n')
  
  const env = await createTaskEnvironment(
    'image_generation',
    '生成 5 张治愈系插画教程',
    {
      total: 5,
      progressType: 'image_generation',
      concurrency: {
        maxConcurrency: 3,  // 最多 3 个并发
        maxWriteConcurrency: 1  // 写操作串行
      }
    }
  )
  
  try {
    env.progress.start('🎨 开始生成治愈系插画教程...')
    
    // 显示进度条
    const showProgress = setInterval(() => {
      const state = env.progress.getState()
      const bar = env.progress.toProgressBar({ width: 40 })
      process.stdout.write(`\r${bar} ${state.details || ''}          `)
    }, 500)
    
    // 定义 5 个图片生成任务
    const prompts = [
      '治愈系插画 - 分类总览图',
      '治愈系插画 - 步骤 1：准备材料',
      '治愈系插画 - 步骤 2：基础绘制',
      '治愈系插画 - 步骤 3：细节完善',
      '治愈系插画 - 步骤 4：最终效果'
    ]
    
    // 使用并发控制器执行
    const controller = env.concurrency
    
    for (let i = 0; i < prompts.length; i++) {
      const prompt = prompts[i]
      const index = i + 1
      
      await env.progress.startItem(`gen_${index}`, `生成图 ${index}`)
      
      // 生图（读操作，可并发）
      const image = await controller.execute(
        'read',
        `生图${index}`,
        async () => mockGeminiGenerate(prompt, index)
      )
      
      await env.progress.completeItem(`gen_${index}`, image)
      
      // 上传（写操作，串行）
      await env.progress.startItem(`upload_${index}`, `上传图 ${index}`)
      
      const uploadResult = await controller.execute(
        'write',
        `上传${index}`,
        async () => mockFeishuUpload(image.path)
      )
      
      await env.progress.completeItem(`upload_${index}`, uploadResult)
      
      // 更新会话状态
      await env.cache.setSafeParams({
        systemPrompt: `生成第${index}张图`,
        model: 'gemini-2.5-pro'
      })
    }
    
    clearInterval(showProgress)
    
    // 完成
    console.log('\n')
    await env.complete({
      success: true,
      totalImages: 5,
      cacheStats: env.cache.getStats()
    })
    
    // 显示最终状态
    const finalState = env.progress.getState()
    console.log('\n✅ 任务完成！')
    console.log(`   总进度：${finalState.percentage}%`)
    console.log(`   总耗时：${((finalState.lastUpdateTime - finalState.startTime) / 1000).toFixed(2)}秒`)
    console.log(`   缓存命中：${finalState.subItems?.length || 0} 个子任务`)
    
    // 显示 SESSION-STATE.md 内容
    console.log('\n📄 SESSION-STATE.md 内容预览：')
    console.log('-'.repeat(60))
    const stateContent = await readFile('SESSION-STATE.md', 'utf-8')
    const lines = stateContent.split('\n').slice(0, 20)
    console.log(lines.join('\n'))
    console.log('...')
    console.log('-'.repeat(60))
    
    await env.cleanup()
    
    return true
    
  } catch (error) {
    clearInterval(showProgress)
    await env.fail(error as Error)
    throw error
  }
}

// ============================================================================
// 测试 2：掉线恢复模拟
// ============================================================================

async function test2_recovery() {
  console.log('\n' + '='.repeat(60))
  console.log('🧪 测试 2：掉线恢复模拟')
  console.log('='.repeat(60) + '\n')
  
  // 先创建一个任务，模拟执行到一半"掉线"
  const env = await createTaskEnvironment(
    'image_generation',
    '测试恢复任务',
    { total: 5 }
  )
  
  env.progress.start('开始任务...')
  
  // 模拟执行了 2 个子任务
  await env.progress.startItem('task_1', '任务 1')
  await env.progress.completeItem('task_1', { result: '完成' }, 100)
  
  await env.progress.startItem('task_2', '任务 2')
  await env.progress.completeItem('task_2', { result: '完成' }, 100)
  
  // 模拟执行到第 3 个任务时"掉线"
  await env.progress.startItem('task_3', '任务 3')
  await env.progress.update({ current: 2, status: 'running', details: '掉线前状态已保存' })
  
  console.log('💥 模拟掉线！状态已保存到 SESSION-STATE.md')
  console.log('   掉线前进度：2/5 (40%)')
  
  // 不清理，让状态文件保留
  
  // 模拟"重启"后恢复
  console.log('\n🔄 尝试恢复任务...')
  
  const restored = await restoreTaskEnvironment()
  
  if (restored) {
    console.log(`✅ 恢复成功！`)
    console.log(`   任务名：${restored.state.taskName}`)
    console.log(`   掉线前进度：${restored.state.progress.percentage}%`)
    console.log(`   已完成子任务：${restored.state.subTasks?.filter(t => t.status === 'completed').length || 0}/${restored.state.progress.total}`)
    
    // 显示未完成的子任务
    const pending = restored.state.subTasks?.filter(t => t.status !== 'completed') || []
    console.log(`   待继续任务：${pending.length} 个`)
    
    for (const task of pending) {
      console.log(`      - ${task.name} (${task.id})`)
    }
    
    await restored.cleanup()
    await env.cleanup()
  } else {
    console.log('❌ 恢复失败')
    await env.cleanup()
  }
}

// ============================================================================
// 测试 3：并发控制效果对比
// ============================================================================

async function test3_concurrency() {
  console.log('\n' + '='.repeat(60))
  console.log('🧪 测试 3：并发控制效果对比')
  console.log('='.repeat(60) + '\n')
  
  // 测试 1：无限制并发（模拟问题场景）
  console.log('📊 场景 A：无限制并发（所有任务同时执行）')
  const startA = Date.now()
  
  const promisesA = []
  for (let i = 1; i <= 5; i++) {
    promisesA.push(
      (async () => {
        await new Promise(r => setTimeout(r, 500))
        console.log(`   [${Date.now() - startA}ms] 任务${i}完成（无限制）`)
      })()
    )
  }
  
  await Promise.all(promisesA)
  const timeA = Date.now() - startA
  console.log(`   总耗时：${timeA}ms\n`)
  
  // 测试 2：串行执行（写操作）
  console.log('📊 场景 B：串行执行（写操作串行）')
  const startB = Date.now()
  
  for (let i = 1; i <= 5; i++) {
    await new Promise(r => setTimeout(r, 500))
    console.log(`   [${Date.now() - startB}ms] 任务${i}完成（串行）`)
  }
  
  const timeB = Date.now() - startB
  console.log(`   总耗时：${timeB}ms\n`)
  
  // 测试 3：智能并发（读并发，写串行）
  console.log('📊 场景 C：智能并发（读并发 3，写串行 1）')
  const controller = new ConcurrencyController({
    maxConcurrency: 3,
    maxWriteConcurrency: 1
  })
  
  const startC = Date.now()
  
  // 读任务并发
  const readPromises = []
  for (let i = 1; i <= 3; i++) {
    readPromises.push(
      controller.execute('read', `读${i}`, async () => {
        await new Promise(r => setTimeout(r, 500))
        console.log(`   [${Date.now() - startC}ms] 读任务${i}完成（并发）`)
        return `read_${i}`
      })
    )
  }
  
  const readResults = await Promise.all(readPromises)
  
  // 写任务串行
  for (let i = 1; i <= 2; i++) {
    await controller.execute('write', `写${i}`, async () => {
      await new Promise(r => setTimeout(r, 500))
      console.log(`   [${Date.now() - startC}ms] 写任务${i}完成（串行）`)
      return `write_${i}`
    })
  }
  
  const timeC = Date.now() - startC
  console.log(`   总耗时：${timeC}ms`)
  console.log(`   状态：${JSON.stringify(controller.getStatus())}\n`)
  
  // 对比分析
  console.log('📈 对比分析：')
  console.log(`   - 无限制并发：${timeA}ms（最快，但可能资源竞争）`)
  console.log(`   - 完全串行：${timeB}ms（最慢，但最安全）`)
  console.log(`   - 智能并发：${timeC}ms（平衡性能和安全性）✅`)
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
  console.log('\n')
  console.log('╔══════════════════════════════════════════════════════════╗')
  console.log('║     Core Engine 实战测试 - 小芙基础设施验证              ║')
  console.log('║     测试时间：' + new Date().toLocaleString('zh-CN') + '                  ║')
  console.log('╚══════════════════════════════════════════════════════════╝')
  
  try {
    // 创建 tmp 目录
    await writeFile(join(process.cwd(), 'tmp', '.gitkeep'), '')
    
    // 运行测试
    await test1_fullWorkflow()
    await test2_recovery()
    await test3_concurrency()
    
    // 清理
    console.log('\n' + '='.repeat(60))
    console.log('✅ 所有测试完成！')
    console.log('='.repeat(60) + '\n')
    
  } catch (error) {
    console.error('\n❌ 测试失败:', error)
    process.exit(1)
  }
}

// 运行
main()
