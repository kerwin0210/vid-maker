# vid-maker v2 系统架构设计

> 版本：v1.0 · 2026-05
> 定位：面向国内市场的 AI 视频制作 SaaS，积分+订阅混合计费，支持高并发扩展

---

## 一、技术选型

### 核心原则

1. **全栈 TypeScript**：前后端共享 Zod schema，类型安全从 DB 到 UI 贯通
2. **SaaS-Forward**：从 Day 1 就是多租户架构，不事后改造
3. **异步优先**：视频生成是长任务（5-15分钟），所有生成任务必须异步化

### 选型矩阵

| 层级 | 选型 | 备选方案 | 选择理由 |
|------|------|---------|---------|
| API Server | **Hono.js + Node.js 22** | FastAPI（Python）| 全栈 TS 单语言；原生 SSE；可平迁 Cloudflare Workers |
| 任务队列 | **BullMQ + Redis** | FastAPI BackgroundTasks | Worker 独立进程可单独扩容；内置死信队列；优先级队列 |
| 数据库 | **PostgreSQL + Drizzle ORM** | DuckDB / MongoDB | ACID 事务保证积分一致性；Drizzle 类型安全迁移 |
| 前端 | **Next.js 15 + React 19** | Vite + React（SPA）| 无 SEO 需求但 App Router 结构清晰；Server Actions |
| UI 组件 | **shadcn/ui + Tailwind** | MUI / Ant Design | 无包依赖，直接拥有源码；配合 shadcn / frontend-design Marketplace plugin |
| 拖拽 | **dnd-kit** | react-beautiful-dnd | 活跃维护；支持无障碍；适合分镜网格排序 |
| 共享类型 | **Zod（packages/shared）** | 手写 TS interface | 运行时校验 + 类型推导合二为一 |
| 文件存储 | **阿里云 OSS** | 腾讯云 COS / AWS S3 | 国内 CDN 加速；S3 兼容 API |
| 认证 | **Better Auth** | NextAuth / Clerk | TypeScript 原生；支持手机号 OTP + 微信 OAuth |
| 支付 | **微信支付 + 支付宝** | Stripe | 国内市场唯一可行方案 |
| 内容审核 | **阿里云内容安全** | 腾讯云内容安全 | 图片+文本 API 成熟；与 OSS 同账号 |
| Monorepo | **pnpm workspaces** | Turborepo + npm | 磁盘占用小；workspace 依赖管理简洁 |
| FFmpeg | **child_process.execFile** | fluent-ffmpeg | 无额外依赖；维护风险低；vid-maker 用法简单 |

---

## 二、整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户端（浏览器）                       │
│  Next.js 15 Web App（:3000）                                 │
│  ├── Step 1-5 向导 UI                                        │
│  ├── SSE 接收（分镜进度）                                     │
│  └── 积分/订阅/支付页面                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────────┐
│                    Hono API Server（:3001）                   │
│  ├── 路由：projects / billing / auth / sse                   │
│  ├── 中间件：authMiddleware / rateLimiter / contentModerate  │
│  └── 积分扣减：Redis Lua 原子脚本                             │
└──────┬───────────────────┬──────────────────────────────────┘
       │ BullMQ enqueue    │ DB 读写
┌──────▼──────┐    ┌───────▼────────────────────────────────┐
│   Redis     │    │  PostgreSQL（:5432）                    │
│  ├── 队列   │    │  ├── users / subscriptions              │
│  ├── 积分   │    │  ├── credit_transactions                │
│  └── SSE    │    │  ├── projects / scenes                  │
└──────┬──────┘    │  └── generation_jobs                    │
       │ BullMQ    └────────────────────────────────────────┘
┌──────▼──────────────────────────────────────────────────────┐
│              BullMQ Worker（独立进程，可多实例）               │
│  ├── storyboard.job.ts → FLUX.1 并行出图 → SSE push         │
│  ├── produce.job.ts → ElevenLabs TTS + Kling 视频 + FFmpeg  │
│  └── failed 事件 → 自动退积分 + 更新项目状态为 failed         │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP API 调用
┌─────────────────────▼───────────────────────────────────────┐
│                    外部 AI API                               │
│  Claude Sonnet 4.6（脚本生成）                               │
│  FLUX.1 Kontext Pro via Replicate（分镜图）                  │
│  ElevenLabs v2（TTS 旁白）                                   │
│  Kling v2.6-pro（视频生成）                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、目录结构

```
vid-maker/
├── apps/
│   ├── api/                    # Hono API Server（Node.js 22）
│   │   ├── src/
│   │   │   ├── routes/         # projects.ts / billing.ts / auth.ts / sse.ts
│   │   │   ├── middleware/     # auth.ts / rate-limit.ts / content-moderate.ts
│   │   │   ├── services/       # credit.service.ts / project.service.ts
│   │   │   └── index.ts        # 入口
│   │   └── package.json
│   │
│   ├── worker/                 # BullMQ Worker（独立进程）
│   │   ├── src/
│   │   │   ├── jobs/           # storyboard.job.ts / produce.job.ts
│   │   │   ├── providers/      # flux1.ts / kling.ts / elevenlabs.ts
│   │   │   └── index.ts        # 入口（注册所有 Worker）
│   │   └── package.json
│   │
│   ├── web/                    # Next.js 15 前端（用户端）
│   │   ├── src/app/
│   │   │   ├── page.tsx        # 落地页
│   │   │   ├── projects/[id]/  # Step 1-5 页面路由
│   │   │   ├── billing/        # 充值/订阅页面
│   │   │   └── settings/       # 账号设置
│   │   └── package.json
│   │
│   └── admin/                  # Next.js 15 运营后台
│       ├── src/app/
│       │   ├── users/          # 用户管理
│       │   ├── costs/          # 成本监控
│       │   └── content/        # 内容审核队列
│       └── package.json
│
├── packages/
│   ├── shared/                 # 前后端共用 Zod schemas
│   │   └── src/
│   │       ├── schemas/        # project.schema.ts / billing.schema.ts
│   │       └── types/          # 枚举类型
│   │
│   ├── db/                     # Drizzle ORM
│   │   ├── src/schema/         # users.ts / projects.ts / billing.ts
│   │   ├── migrations/         # 迁移文件（由 drizzle-kit 生成）
│   │   └── drizzle.config.ts
│   │
│   └── queue/                  # BullMQ 队列定义（api + worker 共用）
│       └── src/
│           ├── queues.ts       # Queue 实例定义
│           └── jobs/           # Job schema 定义
│
├── docs/
│   ├── architecture.md         # 本文件
│   └── marketplace-plugins.md  # Cursor Marketplace plugin 安装说明
│
└── scripts/
    └── check_baseline.sh       # 工程基线自检
```

---

## 四、核心数据库 Schema（Drizzle）

### users 表

```typescript
export const users = pgTable('users', {
  id:            uuid('id').primaryKey().defaultRandom(),
  phone:         varchar('phone', { length: 11 }).unique(),
  wechatOpenid:  varchar('wechat_openid', { length: 64 }).unique(),
  creditBalance: integer('credit_balance').notNull().default(0),  // 单位：积分
  planId:        varchar('plan_id', { length: 32 }).notNull().default('free'),
  createdAt:     timestamp('created_at').notNull().defaultNow(),
})
```

### subscriptions 表

```typescript
export const subscriptions = pgTable('subscriptions', {
  id:             uuid('id').primaryKey().defaultRandom(),
  userId:         uuid('user_id').notNull().references(() => users.id),
  plan:           varchar('plan', { length: 32 }).notNull(),      // 'free'|'basic'|'pro'
  monthlyCredits: integer('monthly_credits').notNull(),
  expiresAt:      timestamp('expires_at').notNull(),
  createdAt:      timestamp('created_at').notNull().defaultNow(),
})
```

### credit_transactions 表（积分流水）

```typescript
export const creditTransactionTypeEnum = pgEnum('credit_tx_type', [
  'recharge',    // 用户充值
  'subscribe',   // 订阅赠送
  'consume',     // 生成消耗
  'refund',      // 生成失败退还
  'expire',      // 过期清零
])

export const creditTransactions = pgTable('credit_transactions', {
  id:        uuid('id').primaryKey().defaultRandom(),
  userId:    uuid('user_id').notNull().references(() => users.id),
  delta:     integer('delta').notNull(),                          // 正数=增加，负数=消耗
  type:      creditTransactionTypeEnum('type').notNull(),
  refId:     varchar('ref_id', { length: 64 }),                  // 关联的 projectId 或 orderId
  createdAt: timestamp('created_at').notNull().defaultNow(),
})
```

### projects 表

```typescript
export const projectStatusEnum = pgEnum('project_status', [
  'draft', 'script_approved', 'storyboard_done', 'producing', 'done', 'failed'
])

export const projects = pgTable('projects', {
  id:               uuid('id').primaryKey().defaultRandom(),
  userId:           uuid('user_id').notNull().references(() => users.id),
  status:           projectStatusEnum('status').notNull().default('draft'),
  inputMode:        varchar('input_mode', { length: 16 }).notNull(),  // 'prompt'|'article'|'outline'
  rawInput:         text('raw_input').notNull(),
  specJson:         text('spec_json').notNull(),                       // VideoSpec JSON
  estimatedCostCny: integer('estimated_cost_cny').notNull().default(0), // 单位：分
  totalCostCny:     integer('total_cost_cny').notNull().default(0),
  finalVideoUrl:    text('final_video_url'),
  parentProjectId:  uuid('parent_project_id'),                        // 变体关联
  createdAt:        timestamp('created_at').notNull().defaultNow(),
  updatedAt:        timestamp('updated_at').notNull().defaultNow(),
})
```

### scenes 表

```typescript
export const scenes = pgTable('scenes', {
  id:            uuid('id').primaryKey().defaultRandom(),
  projectId:     uuid('project_id').notNull().references(() => projects.id, { onDelete: 'cascade' }),
  sceneOrder:    integer('scene_order').notNull(),
  narration:     text('narration').notNull(),
  visualPrompt:  text('visual_prompt').notNull(),
  cameraMotion:  varchar('camera_motion', { length: 128 }).notNull().default('static shot'),
  durationSec:   integer('duration_sec').notNull(),
  imageUrl:      text('image_url'),
  audioPath:     text('audio_path'),
  videoPath:     text('video_path'),
})
```

### generation_jobs 表（成本追踪）

```typescript
export const generationJobTypeEnum = pgEnum('generation_job_type', [
  'script', 'storyboard', 'tts', 'video', 'assemble'
])

export const generationJobs = pgTable('generation_jobs', {
  id:          uuid('id').primaryKey().defaultRandom(),
  projectId:   uuid('project_id').notNull().references(() => projects.id),
  type:        generationJobTypeEnum('type').notNull(),
  status:      varchar('status', { length: 16 }).notNull().default('pending'),
  aiCostCny:   integer('ai_cost_cny').notNull().default(0),  // 单位：分
  startedAt:   timestamp('started_at'),
  finishedAt:  timestamp('finished_at'),
  errorMsg:    text('error_msg'),
})
```

---

## 五、视频生成状态机

```
[用户] POST /projects（输入内容+规格配置）
           ↓
     status: draft
（脚本已生成，等待用户审核）
           ↓ 用户点"确认脚本"
     POST /projects/:id/approve-script
           ↓
     status: script_approved
（自动触发 storyboard BullMQ Job）
           ↓ FLUX.1 并行生成图片
（SSE 推送每张图完成事件）
     status: storyboard_done
（等待用户审核分镜）
           ↓ 用户点"确认画面"
     POST /projects/:id/approve-storyboard
           ↓
     status: producing
（TTS + Kling + FFmpeg 全自动）
           ↓ 完成
     status: done ←──────── 任意步骤失败
                              ↓
                         status: failed
                    （自动触发退积分）
```

### 合法状态转换（代码必须校验）

```typescript
// packages/shared/src/schemas/project.schema.ts
export const VALID_TRANSITIONS: Record<ProjectStatus, ProjectStatus[]> = {
  draft:            ['script_approved', 'failed'],
  script_approved:  ['storyboard_done', 'failed'],
  storyboard_done:  ['producing', 'failed'],
  producing:        ['done', 'failed'],
  done:             [],
  failed:           [],
}

export function assertValidTransition(from: ProjectStatus, to: ProjectStatus): void {
  if (!VALID_TRANSITIONS[from].includes(to)) {
    throw new Error(`非法状态转换：${from} → ${to}`)
  }
}
```

---

## 六、积分与计费设计

### 积分定价矩阵

| 视频规格 | 场景数 | AI API 成本 | 建议积分定价 | 毛利率 |
|---------|--------|------------|------------|-------|
| 30s     | 5      | ~¥11       | 20积分     | ~45% |
| 1min    | 10     | ~¥22       | 38积分     | ~42% |
| 2min    | 20     | ~¥43       | 70积分     | ~39% |
| 5min    | 40     | ~¥87       | 130积分    | ~33% |

> 1积分 ≈ ¥1，成本估算汇率 $1 = ¥7.2

### 订阅套餐

| 套餐 | 月费 | 每月赠积分 | 主要权益 |
|------|------|---------|---------|
| 免费版 | ¥0 | 10 | 每月 2 个 30s 视频，标准队列 |
| 基础版 | ¥99 | 60 | 全规格视频，优先队列 |
| 专业版 | ¥299 | 200 | 全规格视频，最高优先级，专属客服 |

### 充值包

| 充值包 | 价格 | 积分 | 折扣 |
|--------|------|------|------|
| 基础包 | ¥49  | 50   | —    |
| 标准包 | ¥129 | 150  | 8.6折 |
| 专业包 | ¥279 | 350  | 8折  |

### 积分原子扣减（Redis Lua）

```lua
-- 原子操作：余额足够时才扣减
local balance = tonumber(redis.call('GET', KEYS[1]))
if balance == nil or balance < tonumber(ARGV[1]) then
  return 0  -- 余额不足，不扣减
end
redis.call('DECRBY', KEYS[1], ARGV[1])
redis.call('PUBLISH', 'credit:changed:' .. KEYS[2], ARGV[1])
return 1  -- 扣减成功
```

---

## 七、BullMQ 任务队列设计

### 队列优先级

```typescript
// Pro 用户 priority=10，免费用户 priority=1
// BullMQ 数字越大优先级越高
await storyboardQueue.add('generate', jobData, {
  priority: user.planId === 'pro' ? 10 : 1,
  attempts: 3,
  backoff: { type: 'exponential', delay: 5000 },
})
```

### Worker 并发控制

```typescript
// 并发数 = Kling API 允许的最大并发数
// 多实例部署时：总并发 = 实例数 × concurrency
const produceWorker = new Worker('produce', processProduceJob, {
  connection: redis,
  concurrency: 5,  // 单实例 5 个并发，2 台实例 = 10 并发
})
```

### 失败自动退积分

```typescript
produceWorker.on('failed', async (job, err) => {
  logger.error('produce.job.failed', { jobId: job?.id, error: err.message })
  if (job && job.attemptsMade >= (job.opts.attempts ?? 1)) {
    await Promise.all([
      refundCredits(job.data.userId, job.data.creditCost, job.data.projectId),
      updateProjectStatus(job.data.projectId, 'failed'),
      notifyUser(job.data.userId, '视频生成失败，积分已全额退还'),
    ])
  }
})
```

---

## 八、SSE 实时进度推送

```
Worker 完成一张分镜图
    ↓
Redis PUBLISH storyboard:{projectId} {sceneId, imageUrl}
    ↓
Hono SSE 端点订阅 Redis Channel
    ↓
EventSource 推送给浏览器
    ↓
前端 useStoryboardProgress Hook 更新 UI（骨架屏→实图）
```

```typescript
// Hono SSE 端点
app.get('/projects/:id/storyboard-progress', authMiddleware, async (c) => {
  const projectId = c.req.param('id')
  return streamSSE(c, async (stream) => {
    const sub = redis.subscribe(`storyboard:${projectId}`, async (msg) => {
      await stream.writeSSE({ data: msg, event: 'scene-done' })
    })
    c.req.raw.signal.addEventListener('abort', () => sub.unsubscribe())
  })
})
```

---

## 九、部署架构（三阶段）

### Phase 1：MVP（月费 ~¥800）

```
单台 ECS（4核8G）
├── API Server（pm2）
├── BullMQ Worker（pm2）
└── Next.js Web（pm2）

阿里云 RDS PostgreSQL（1核2G）
阿里云 Redis（1G）
阿里云 OSS（按量）
```

### Phase 2：内测付费（月费 ~¥4000）

```
SLB 负载均衡
├── 2-3台 API Server ECS
└── 5-10台 Worker ECS（根据队列深度手动调整）

阿里云 RDS PostgreSQL（2核4G + 只读实例）
阿里云 Redis 集群（3节点）
阿里云 OSS + CDN
```

### Phase 3：公测（K8s 自动扩缩）

```
ACK（阿里云 Kubernetes）
├── API Deployment（HPA 按 CPU 扩缩）
├── Worker Deployment（KEDA 按 BullMQ 队列深度扩缩）
└── Web Deployment（静态，CDN 优先）

RDS PostgreSQL（4核8G + PolarDB 读写分离）
Redis 企业版
```

---

## 十、国内 SaaS 合规要点

| 要求 | 方案 |
|------|------|
| ICP 备案 | 使用国内 ECS + 域名备案 |
| 内容审核 | 所有 AI 生成前过阿里云内容安全 |
| 数据留存 | 用户数据存国内 RDS，不出境 |
| 隐私政策 | 上线前必须有隐私政策页面 |
| 支付合规 | 微信/支付宝商户号 + 营业执照 |
| 软著 | 建议申请软件著作权（客户端保护）|
