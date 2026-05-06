---
name: bullmq-job-gen
version: "1.0"
description: 生成 BullMQ Job 定义、Worker 处理器骨架、死信队列配置和退积分逻辑。
allowed-tools:
  - Read
  - Write
  - Glob
---

# bullmq-job-gen

为 vid-maker 生成符合规范的 BullMQ 异步任务。

## 触发条件

- 用户说"新增一个异步任务"
- 需要将耗时操作移到 Worker 处理
- 新增 AI API 调用任务

## 生成步骤

### Step 1：在 packages/queue 定义 Job 类型

```typescript
// packages/queue/src/jobs/[job-name].job.ts
export const XxxJobSchema = z.object({
  projectId:  z.string().uuid(),
  userId:     z.string().uuid(),
  creditCost: z.number().int().positive(),  // ← 必须，用于失败退积分
  // 业务字段...
})
export type XxxJobData = z.infer<typeof XxxJobSchema>

// 在 packages/queue/src/queues.ts 注册 Queue
export const xxxQueue = new Queue('xxx', {
  connection: redis,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: 'exponential', delay: 5000 },
    removeOnComplete: { count: 100 },
    removeOnFail: false,
  }
})
```

### Step 2：生成 Worker 处理器

```typescript
// apps/worker/src/jobs/xxx.worker.ts
import { Worker, Job } from 'bullmq'
import { XxxJobData } from '@vid-maker/queue'

async function processXxx(job: Job<XxxJobData>) {
  // 1. 写入 generation_jobs 记录开始
  const jobRecord = await createJobRecord(job.data.projectId, 'xxx')

  try {
    // 2. 执行实际工作
    const result = await doWork(job.data)

    // 3. 写入实际成本（必须！）
    await updateJobCost(jobRecord.id, result.costCny)

    return result
  } catch (err) {
    await markJobFailed(jobRecord.id)
    throw err  // 让 BullMQ 处理重试逻辑
  }
}

export const xxxWorker = new Worker('xxx', processXxx, {
  connection: redis,
  concurrency: 5,  // 根据外部 API 限制设置
})

// 必须配置 failed 事件退积分
xxxWorker.on('failed', async (job, err) => {
  if (job && job.attemptsMade >= (job.opts.attempts ?? 1)) {
    await refundCredits(job.data.userId, job.data.creditCost, job.data.projectId)
    await updateProjectStatus(job.data.projectId, 'failed')
  }
})
```

## 关键约束

- ✅ Job data 必须包含 creditCost（用于失败退积分）
- ✅ 必须配置 failed 事件处理器
- ✅ 每次 AI API 调用后立即写入 generation_jobs 成本
- ✅ 处理器必须幂等（同一 Job 重试不会产生副作用）
- ❌ 禁止在 Worker 中直接操作积分（统一走 refundCredits 函数）
