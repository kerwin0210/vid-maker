# vid-maker 开发提示词手册

> 按阶段顺序使用，每条提示词可直接复制到 Cursor Composer。
> 发送前建议先 @ 引用对应文件，等 `code-reviewer` background agent 跑完再进入下一步。

---

## 阶段总览

```
Phase 0  基础设施   Step 0.1 Monorepo 骨架 → Step 0.2 Docker 本地服务
Phase 1  数据层     Step 1.1 Drizzle Schema → Step 1.2 Zod Schemas → Step 1.3 BullMQ Queue
Phase 2  API 核心   Step 2.1 Hono 骨架 → Step 2.2 积分 API → Step 2.3 状态机 API → Step 2.4 SSE
Phase 3  Worker     Step 3.1 分镜生成 → Step 3.2 视频生产
Phase 4  前端       Step 4.1 Next.js 初始化 → Step 4.2 Step1-3 → Step 4.3 Step4-5+积分
Phase 5  联调       Step 5.1 E2E 冒烟测试
```

---

## Phase 0：基础设施

### Step 0.1 — Monorepo 骨架

> 发送前打开：`AGENTS.md` + `docs/architecture.md`

```
我需要搭建 vid-maker 的 pnpm monorepo 骨架。

请参考 AGENTS.md [Project] 里的目录结构和 docs/architecture.md 第三节，创建以下文件（只创建配置文件和空目录，严禁写业务逻辑）：

根目录：
- pnpm-workspace.yaml（声明 apps/* 和 packages/*）
- package.json（name: "vid-maker", private: true, engines: { node: ">=22" }）
- tsconfig.base.json（strict: true, noUncheckedIndexedAccess: true, exactOptionalPropertyTypes: true）
- .npmrc（shamefully-hoist=false）

apps/api/package.json：
- name: "@vid-maker/api"
- dependencies: hono @hono/zod-validator bullmq ioredis drizzle-orm pg zod better-auth structlog @anthropic-ai/sdk replicate @elevenlabs/elevenlabs-js
- devDependencies: @types/node tsx vitest @types/pg

apps/worker/package.json：
- name: "@vid-maker/worker"
- dependencies: bullmq ioredis drizzle-orm pg zod @vid-maker/db @vid-maker/queue @vid-maker/shared

apps/web/package.json：
- name: "@vid-maker/web"
- dependencies: next@15 react@19 react-dom@19 @vid-maker/shared swr
- devDependencies: typescript @types/react @types/node

apps/admin/package.json：
- name: "@vid-maker/admin"
- dependencies: next@15 react@19 react-dom@19 @vid-maker/shared @vid-maker/db

packages/shared/package.json：
- name: "@vid-maker/shared"
- dependencies: zod

packages/db/package.json：
- name: "@vid-maker/db"
- dependencies: drizzle-orm pg
- devDependencies: drizzle-kit @types/pg

packages/queue/package.json：
- name: "@vid-maker/queue"
- dependencies: bullmq ioredis @vid-maker/shared

完成后执行：
1. pnpm install（验证 workspace 解析正常）
2. 输出根目录树（不含 node_modules）
```

---

### Step 0.2 — Docker 本地服务

> 发送前打开：`.env.example`

```
为 vid-maker 创建本地开发用的 docker-compose.yml。

包含以下服务：

1. postgres
   - image: postgres:16-alpine
   - ports: 5432:5432
   - environment: POSTGRES_DB=vidmaker_dev, POSTGRES_USER=postgres, POSTGRES_PASSWORD=postgres
   - volumes: postgres_data:/var/lib/postgresql/data
   - healthcheck: pg_isready -U postgres

2. redis
   - image: redis:7-alpine
   - ports: 6379:6379
   - command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
   - healthcheck: redis-cli ping

同时创建 .env（复制自 .env.example）并填入以下本地开发值：
- DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vidmaker_dev
- REDIS_URL=redis://localhost:6379
- NODE_ENV=development
- PMR_SRC_PATH=/Users/kerwin/Desktop/workspace/AI自动化课件/课件资料/3 核心技术落地/toolkit/project-memory-rag/src

执行 docker compose up -d，验证两个服务健康后输出 docker compose ps。
```

---

## Phase 1：数据层

### Step 1.1 — Drizzle Schema（packages/db）

> 发送前打开：`docs/architecture.md`（第四节"核心数据库 Schema"）

```
为 vid-maker 创建 packages/db 的完整 Drizzle ORM schema。

参考 docs/architecture.md 第四节，在 packages/db/src/schema/ 下创建以下文件：

1. users.ts
   字段：id(uuid PK) / phone(varchar 11, unique) / wechat_openid(varchar 64, unique) /
         credit_balance(integer, default 0) / plan_id(varchar 32, default 'free') / created_at

2. billing.ts
   - creditTransactionTypeEnum：recharge / subscribe / consume / refund / expire
   - subscriptions 表：id / user_id(FK) / plan / monthly_credits / expires_at / created_at
   - creditTransactions 表：id / user_id(FK) / delta(integer) / type(enum) / ref_id(varchar 64) / created_at

3. projects.ts
   - projectStatusEnum：draft / script_approved / storyboard_done / producing / done / failed
   - inputModeEnum：prompt / article / outline
   - projects 表：id / user_id(FK) / status(enum, default draft) / input_mode / raw_input(text) /
                  spec_json(text) / estimated_cost_cny(integer) / total_cost_cny(integer) /
                  final_video_url(text) / parent_project_id(uuid) / created_at / updated_at
   - scenes 表：id / project_id(FK cascade) / scene_order(integer) / narration(text) /
               visual_prompt(text) / camera_motion(varchar 128) / duration_sec(integer) /
               image_url(text) / audio_path(text) / video_path(text)

4. jobs.ts
   - generationJobTypeEnum：script / storyboard / tts / video / assemble
   - generationJobs 表：id / project_id(FK) / type(enum) / status(varchar 16, default pending) /
                        ai_cost_cny(integer, default 0) / started_at / finished_at / error_msg(text)

5. index.ts：统一导出所有 schema 和 enum

6. drizzle.config.ts：
   schema: './src/schema/*', out: './migrations', driver: 'pg'
   dbCredentials: { connectionString: process.env.DATABASE_URL! }

执行：
1. pnpm --filter @vid-maker/db drizzle-kit generate
2. pnpm --filter @vid-maker/db drizzle-kit migrate
3. psql $DATABASE_URL -c "\dt" 验证所有表已创建
```

---

### Step 1.2 — Zod Schemas（packages/shared）

> 发送前打开：`packages/db/src/schema/projects.ts` + `AGENTS.md`（[Pipeline State Machine] 节）

```
为 vid-maker 创建 packages/shared 的完整 Zod schemas。

在 packages/shared/src/schemas/ 下创建：

1. project.schema.ts：
   - ProjectStatusSchema = z.enum(['draft','script_approved','storyboard_done','producing','done','failed'])
   - InputModeSchema = z.enum(['prompt','article','outline'])
   - AspectRatioSchema = z.enum(['16:9','9:16','1:1'])
   - DurationPresetSchema = z.enum(['30s','1min','2min','5min'])
   - VideoSpecSchema（duration_preset / aspect_ratio / visual_style / voice_id）
   - SceneSchema（id / narration / visual_prompt / camera_motion / duration_sec /
                 image_url? / audio_path? / video_path?）
   - CreateProjectSchema（input_mode / raw_input(min 1, max 2000) /
                         duration_preset / aspect_ratio / visual_style / voice_id /
                         parent_project_id?）
   - ScenePatchSchema（narration? / visual_prompt? / camera_motion? / duration_sec?）
   - VALID_TRANSITIONS: Record<ProjectStatus, ProjectStatus[]>（完整映射）
   - assertValidTransition(from, to)：非法时抛 Error
   - SCENE_COUNT_MAP: { '30s':5, '1min':10, '2min':20, '5min':40 }
   - DURATION_SEC_MAP: { '30s':30, '1min':60, '2min':120, '5min':300 }
   - estimateCreditCost(spec: VideoSpec): number（按 architecture.md 第六节定价矩阵）

2. billing.schema.ts：
   - CreditTxTypeSchema = z.enum([...])
   - DeductCreditsSchema（user_id / amount / project_id）
   - EstimateCostSchema（duration_preset / aspect_ratio）

3. index.ts：统一导出所有 schemas 和类型

要求：
- 所有 TypeScript 类型通过 z.infer<typeof XxxSchema> 推导，不手写 interface
- estimateCreditCost 返回值单位为"积分"（1积分≈¥1）
```

---

### Step 1.3 — BullMQ Queue 定义（packages/queue）

> 发送前打开：`.cursor/rules/05-bullmq-worker.mdc`

```
为 vid-maker 创建 packages/queue 的 BullMQ 队列和 Job 类型定义。

在 packages/queue/src/ 下创建：

1. connection.ts：
   - 导出 redis（IORedis 实例，读 process.env.REDIS_URL，lazyConnect: true）
   - 导出 redisConnection（BullMQ 用的精简连接配置对象，不含 lazyConnect）

2. jobs/storyboard.job.ts：
   - StoryboardJobSchema = z.object({ project_id, user_id, credit_cost, scenes, spec })
   - 导出 StoryboardJobData = z.infer<typeof StoryboardJobSchema>

3. jobs/produce.job.ts：
   - ProduceJobSchema = z.object({ project_id, user_id, credit_cost, scenes, spec, storyboard_urls })
   - 导出 ProduceJobData = z.infer<typeof ProduceJobSchema>

4. queues.ts：
   - storyboardQueue = new Queue('storyboard', { connection, defaultJobOptions: {
       attempts: 3,
       backoff: { type: 'exponential', delay: 5000 },
       removeOnComplete: { count: 100 },
       removeOnFail: false
     }})
   - produceQueue = new Queue('produce', { connection, defaultJobOptions: {
       attempts: 2,
       backoff: { type: 'fixed', delay: 10000 },
       removeOnComplete: { count: 100 },
       removeOnFail: false
     }})

5. index.ts：统一导出

要求：
- Job schema 必须包含 credit_cost 字段（用于失败时退积分）
- 不在此包写任何 Worker 处理逻辑
- 所有 Queue 名称与 Worker 侧保持字符串一致
```

---

## Phase 2：API 核心

### Step 2.1 — Hono 应用骨架 + 中间件

> 发送前打开：`.cursor/rules/02-hono-api.mdc` + `.cursor/rules/06-security.mdc`

```
为 vid-maker 创建 apps/api 的 Hono 应用骨架和核心中间件。

在 apps/api/src/ 下创建：

1. lib/errors.ts：
   - AppError class（code: string / message: string / status: number / details?: unknown）
   - errorHandler：Hono onError handler，统一返回 { error: { code, message, requestId } }

2. lib/logger.ts：
   - structlog 风格 JSON logger（level / timestamp / message / ...fields）
   - getLogger(module: string) 工厂函数

3. lib/db.ts：
   - drizzle(pg) 实例，读 DATABASE_URL
   - 连接池配置（max: 10）

4. lib/redis.ts：
   - IORedis 实例，读 REDIS_URL

5. middleware/request-id.ts：
   - 每个请求注入 x-request-id（UUID），存入 c.set('requestId', ...)

6. middleware/auth.ts：
   - authMiddleware：读取 Better Auth session，注入 c.set('userId', ...)
   - dev 环境无 session 时注入 mock userId（不报错，方便本地调试）

7. middleware/rate-limit.ts：
   - rateLimiter({ free: number, pro: number, window: string })
   - 基于 Redis 滑动窗口，超限返回 429

8. middleware/content-moderate.ts：
   - moderateText(text)：调用阿里云内容安全 @alicloud/green20220302
   - 无 ALIYUN_ACCESS_KEY_ID 时 dev 环境直接返回（不拦截）
   - 违规时抛 AppError('CONTENT_MODERATION_REJECTED', ..., { status: 400 })

9. index.ts：
   - 注册 requestId → logger → cors → routes
   - 注册 onError(errorHandler)
   - 监听 3001 端口

执行 tsx apps/api/src/index.ts，访问 localhost:3001/health 返回 { status:'ok' } 验证启动正常。
```

---

### Step 2.2 — 积分系统 API

> 发送前打开：`docs/architecture.md`（第六节"积分与计费设计"）+ `packages/shared/src/schemas/billing.schema.ts`

```
为 vid-maker 创建积分核心服务和 billing 路由。

1. apps/api/src/services/credit.service.ts：

   deductCredits(userId: string, amount: number, projectId: string): Promise<boolean>
   - 使用 Redis Lua 原子脚本（必须完整包含以下逻辑）：
     local balance = tonumber(redis.call('GET', KEYS[1]))
     if balance == nil or balance < tonumber(ARGV[1]) then return 0 end
     redis.call('DECRBY', KEYS[1], ARGV[1])
     return 1
   - 返回 false 时抛 AppError('CREDIT_INSUFFICIENT', '积分不足', { status: 402 })
   - 扣减成功后异步写 DB credit_transactions（type: 'consume'）

   refundCredits(userId, amount, projectId): Promise<void>
   - 幂等：先查 credit_transactions 是否已有 type='refund' AND ref_id=projectId
   - 未退过：Redis INCRBY + DB insert credit_transactions(type:'refund')

   getBalance(userId): Promise<number>
   - 从 Redis 读取（key: credit:{userId}）
   - Redis 不存在时从 DB 读 users.credit_balance 并同步到 Redis

2. apps/api/src/routes/billing.ts（全部需要 authMiddleware）：
   - GET  /api/billing/balance → { balance: number, plan: string }
   - POST /api/billing/estimate（body: EstimateCostSchema）→ { credits: number, cny_estimate: number }
   - GET  /api/billing/transactions?page=1&limit=20 → 积分流水列表（分页）

要求：
- Lua 脚本必须原子执行，禁止用 GET + SET 分两步
- refundCredits 的幂等检查必须在 DB 事务内
```

---

### Step 2.3 — 项目状态机 API

> 发送前打开：`AGENTS.md`（[Pipeline State Machine] 节）+ `packages/shared/src/schemas/project.schema.ts`

```
为 vid-maker 创建 projects 状态机 API 路由。

apps/api/src/routes/projects.ts（全部需要 authMiddleware）：

POST /api/projects（接受 CreateProjectSchema）：
1. moderateText(rawInput)（内容安全审核）
2. 估算积分消耗：estimateCreditCost(spec)
3. deductCredits(userId, cost, newProjectId)
4. 调用 Claude Sonnet 4.6 生成脚本（system prompt 见 AGENTS.md 中脚本生成要求）
5. 写入 projects（status:'draft'）和 scenes 表
6. 写入 generation_jobs（type:'script'，记录 Claude 实际 token 成本）
7. 返回 { project_id, status, scenes, estimated_cost_cny }

GET /api/projects → 用户项目列表（分页，最新在前）
GET /api/projects/:id → 项目详情（含 scenes）

PATCH /api/projects/:id/script（body: { scenes: ScenePatch[] }）：
- 批量更新 scenes 内容
- 验证 project.userId === userId，否则 404

POST /api/projects/:id/approve-script：
- assertValidTransition(project.status, 'script_approved')
- 更新 status → 'script_approved'
- storyboardQueue.add('generate', { project_id, user_id, credit_cost, scenes, spec }, { priority: isPro ? 10 : 1 })

POST /api/projects/:id/approve-storyboard：
- assertValidTransition(project.status, 'producing')
- 更新 status → 'producing'
- produceQueue.add('produce', { ... })

POST /api/projects/:id/scenes/:sceneId/regenerate：
- 单场景重新生成图片（调用 FLUX.1，更新 scenes.image_url）

要求：
- 所有 DB 查询 WHERE 必须包含 AND user_id = userId
- 状态转换错误返回 409 Conflict（不是 400）
- Claude 成本：(inputTokens * 0.000003 + outputTokens * 0.000015) * 7.2，单位转为"分"写入 DB
```

---

### Step 2.4 — SSE 分镜进度端点

> 发送前打开：`.agents/skills/sse-progress-ui/SKILL.md`

```
为 vid-maker 创建 SSE 分镜进度推送端点。

apps/api/src/routes/sse.ts：

GET /api/projects/:id/storyboard-progress（需要 authMiddleware）

逻辑：
1. 查询项目，验证 userId，404 找不到
2. 若 status 已是 storyboard_done / producing / done：
   - 读取所有 scenes 的 image_url，逐条推送 scene-done 事件
   - 最后推送 complete 事件，关闭连接
3. 否则：
   - 用 streamSSE 创建 SSE 流
   - 订阅 Redis channel：storyboard:{projectId}
   - 收到消息 → await stream.writeSSE({ event: 'scene-done', data: JSON.stringify(msg) })
   - 收到 complete 消息 → 推送 complete 事件后关闭
4. 客户端断开（c.req.raw.signal abort）→ 取消 Redis 订阅
5. 每 30s 发一条 event: keepalive（防代理超时断连）

SSE 消息格式（data 字段为 JSON 字符串）：
- event: scene-done, data: { sceneId, imageUrl, totalDone, totalScenes }
- event: complete, data: { projectId }
- event: error, data: { code, message }
- event: keepalive, data: {}

要求：
- Redis 订阅必须在请求结束时清理（用 try/finally）
- 不要用 setInterval keepalive（用 BullMQ 事件驱动）
```

---

## Phase 3：Worker

### Step 3.1 — 分镜生成 Worker

> 发送前打开：`.cursor/rules/05-bullmq-worker.mdc` + `.cursor/rules/07-cost-aware.mdc`

```
为 vid-maker 创建 storyboard 分镜图生成 Worker。

apps/worker/src/jobs/storyboard.worker.ts：

processStoryboardJob(job: Job<StoryboardJobData>)：

1. 在 DB 创建 generation_job 记录（type:'storyboard', status:'running'）
2. 分批并行调用 Replicate FLUX.1 Kontext Pro（每批 10 张）：
   - model: "black-forest-labs/flux-kontext-pro"
   - input: { prompt: scene.visual_prompt, aspect_ratio: spec.aspect_ratio, output_format: "webp", output_quality: 90 }
   - 加 tenacity 重试（3次，指数退避 2s-15s）
3. 每张图完成后（不等全部完成）：
   a. 更新 DB：scenes.image_url = imageUrl
   b. 计算成本：0.04 美元 × 7.2 = 0.288 元 = 288 分
   c. 更新 DB：generation_jobs.ai_cost_cny += 288
   d. Redis PUBLISH storyboard:{projectId} { sceneId, imageUrl, totalDone, totalScenes }
4. 全部完成：
   a. Redis PUBLISH storyboard:{projectId} { type:'complete' }
   b. DB 更新 projects.status = 'storyboard_done'

Worker 配置：
const storyboardWorker = new Worker('storyboard', processStoryboardJob, {
  connection: redisConnection,
  concurrency: 10
})

storyboardWorker.on('failed', async (job, err) => {
  logger.error('storyboard.job.failed', { jobId: job?.id, error: err.message })
  if (job && job.attemptsMade >= (job.opts.attempts ?? 1)) {
    await refundCredits(job.data.user_id, job.data.credit_cost, job.data.project_id)
    await updateProjectStatus(job.data.project_id, 'failed')
  }
})

无 REPLICATE_API_TOKEN 时（dev 环境）：返回固定 placeholder 图片 URL，不调用真实 API。

要求：
- 每张图成本写入独立的 generation_job 行（不合并到一条）
- 退积分必须幂等（refundCredits 函数已有此保证）
```

---

### Step 3.2 — 生产 Worker（TTS + Kling + FFmpeg）

> 发送前打开：`.cursor/rules/07-cost-aware.mdc` + `docs/architecture.md`（第七节 BullMQ 设计）

```
为 vid-maker 创建视频生产 Worker。

apps/worker/src/jobs/produce.worker.ts：

processProduceJob(job: Job<ProduceJobData>)：

阶段一：TTS（ElevenLabs）
- 逐场景调用 ElevenLabs v2（voice_id 来自 spec）
- SDK: @elevenlabs/elevenlabs-js，接口: textToSpeech.convert
- 保存音频到 /tmp/vid-{projectId}/audio/scene-{id}.mp3
- 成本：narration.length × 0.00018 × 7.2，写入 generation_jobs(type:'tts')

阶段二：视频生成（Kling）
- 调用 Kling v2.6-pro API（POST https://api.klingai.com/v1/videos/image2video）
- 参数：image_url=scene.image_url, camera_control=scene.camera_motion, duration=5
- 轮询任务状态（GET /v1/videos/{taskId}）：间隔 10s，最大 10 分钟
- 成本：5秒 × $0.05 × 7.2 = 1.8 元 = 180 分，写入 generation_jobs(type:'video')

阶段三：FFmpeg 合成
- 生成 concat.txt（ffmpeg 拼接列表文件）
- child_process.execFile('ffmpeg', [
    '-f', 'concat', '-safe', '0', '-i', 'concat.txt',
    '-c:v', 'copy', '-c:a', 'aac', '-movflags', '+faststart',
    'output.mp4'
  ], { cwd: tmpDir })
- 写入 generation_jobs(type:'assemble'，cost:0)

阶段四：上传 OSS + 收尾
- 上传 output.mp4 到阿里云 OSS（使用 ali-oss SDK）
- key: videos/{projectId}/final.mp4
- 更新 projects.final_video_url = CDN_URL + key
- 更新 projects.status = 'done'
- 累加 projects.total_cost_cny（所有 generation_jobs 之和）
- 删除 /tmp/vid-{projectId}/ 临时文件

Worker 配置：concurrency: 5，failed 事件退积分 + status='failed'

无真实 API Key 时（dev mock）：
- TTS → 复制一段静音 mp3
- Kling → 用 FFmpeg 将分镜图转成 5s 静止视频
- OSS → 复制到本地 public/ 目录，返回 localhost URL
```

---

## Phase 4：前端

### Step 4.1 — Next.js 骨架 + shadcn 初始化

> 发送前打开：`.cursor/rules/03-nextjs-patterns.mdc`

```
为 vid-maker 初始化 apps/web 的 Next.js 15 前端完整骨架。

1. Next.js 配置（apps/web/next.config.ts）：
   - 配置 rewrites：/api/* → http://localhost:3001/api/*（开发代理到 Hono）
   - 配置 images.remotePatterns：Replicate CDN + 阿里云 OSS CDN 域名

2. 初始化 shadcn/ui：
   style: default，baseColor: slate，CSS variables: yes，路径 @/components/ui
   安装组件：button input textarea label select tabs dialog progress badge card skeleton toast separator

3. 安装额外依赖：
   pnpm --filter @vid-maker/web add @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities swr clsx tailwind-merge

4. apps/web/src/lib/utils.ts：cn() 工具函数（使用 clsx + tailwind-merge）

5. apps/web/src/lib/api.ts：
   封装所有 API 调用，每个函数返回类型化结果：
   - createProject(input: CreateProjectInput): Promise<{ project_id, status, scenes, estimated_cost_cny }>
   - getProject(id: string): Promise<Project>
   - patchScript(id, scenes): Promise<void>
   - approveScript(id): Promise<void>
   - approveStoryboard(id): Promise<void>
   - getBalance(): Promise<{ balance: number, plan: string }>

6. apps/web/src/hooks/useStoryboardProgress.ts：
   完全按照 .agents/skills/sse-progress-ui/SKILL.md 实现：
   - 返回 { completedScenes: Map<number, string>, isComplete, progress, error }
   - 组件卸载时关闭 EventSource

7. apps/web/src/app/layout.tsx（根布局）：
   - 顶部导航：Logo + CreditBalance 组件（占位，下步实现）+ 用户菜单
   - Toaster（shadcn 全局 toast）
   - 字体：Inter（Next.js 字体优化）

8. apps/web/src/app/page.tsx（首页）：
   - 简洁 Hero：标题 + 副标题 + "开始制作" 按钮 → /projects/new

验证：pnpm --filter @vid-maker/web dev 启动，localhost:3000 显示首页布局。
```

---

### Step 4.2 — Step 1-3：5 步向导核心页面

> 发送前打开：`.agents/skills/sse-progress-ui/SKILL.md` + `.agents/skills/saas-billing-ui/SKILL.md`

```
为 vid-maker 实现 5 步向导的前三步页面和关键组件。

apps/web/src/components/CostConfirmDialog/CostConfirmDialog.tsx：
- 完全按照 saas-billing-ui SKILL.md 中"生成前成本确认弹窗"实现
- COST_WARN_THRESHOLD = 50 积分
- 积分不足时禁用确认按钮 + 显示充值引导

apps/web/src/app/projects/new/page.tsx（Step 1 - 输入）：
- shadcn Tabs 切换：提示词 / 文案 / 大纲
  · 提示词：Textarea（1句话描述视频）
  · 文案：Textarea（完整文案，max 2000字）
  · 大纲：Textarea（每行一个场景要点）
- 规格选择（shadcn RadioGroup 或 Button Group）：
  · 时长：30s / 1min / 2min / 5min
  · 比例：16:9 / 9:16 / 1:1
  · 风格：电影感 / 动漫 / 纪录片 / 科技感
- 底部：预估积分消耗（实时计算，使用 estimateCreditCost）+ "生成脚本"按钮
- 点击按钮逻辑：
  1. 积分不足 → 弹 CostConfirmDialog
  2. 成本 > 50积分 → 弹 CostConfirmDialog
  3. 确认 → 调用 createProject → 跳转 /projects/{id}/step2

apps/web/src/app/projects/[id]/layout.tsx：
- 5步进度条（Step 1-5），根据 project.status 高亮当前步
- Server Component，suspense 边界保护

apps/web/src/app/projects/[id]/step2/page.tsx（Step 2 - 脚本审核）：
- Client Component
- 场景列表：每个场景卡片包含：
  · 场景编号 badge
  · 旁白文本（点击 → textarea，失焦 PATCH 保存，加 debounce 500ms）
  · 画面描述（同上）
  · ↺ 单场景重新生成 + × 删除 按钮（右上角）
- 顶部：整体调整 Textarea（发给 AI 批量修改所有场景风格）
- 底部操作：[← 返回修改输入] [确认脚本 → 开始生成画面]

apps/web/src/app/projects/[id]/step3/page.tsx（Step 3 - 分镜审核）：
- 使用 useStoryboardProgress hook 驱动
- 网格布局：grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4
- SceneSlot 组件（完全按 sse-progress-ui SKILL.md 实现）：
  · undefined imageUrl → 骨架屏（bg-muted animate-pulse）
  · 有 imageUrl → 渐入动效（animate-in fade-in duration-500）
  · hover 显示：↺ 重新生成 + ⬆ 上传替换
- 顶部：Progress 进度条 + "X/Y 已完成"
- dnd-kit SortableContext：拖拽排序（排序后 PATCH 保存）
- 底部：[← 返回修改脚本] [确认画面 → 开始生产]（可在生成完成前提前点击）

所有页面移动端适配，min-h-screen flex flex-col。
```

---

### Step 4.3 — Step 4-5 + 积分充值页面

> 发送前打开：`.agents/skills/saas-billing-ui/SKILL.md`

```
为 vid-maker 实现向导第 4-5 步和积分充值页面。

apps/web/src/components/CreditBalance/CreditBalance.tsx：
- 完全按照 saas-billing-ui SKILL.md "积分余额展示（导航栏）"实现
- SWR 轮询 /api/billing/balance（refreshInterval: 30000）
- 余额 < 20 积分：橙色警告 + "充值"链接

apps/web/src/app/projects/[id]/step4/page.tsx（Step 4 - 生产进度）：
- 轮询 GET /api/projects/:id（每 5s，使用 SWR refreshInterval）
- 进度展示：
  · TTS 旁白录制中... / ✅ 完成
  · Kling 视频生成中... / ✅ 完成
  · 视频合成中... / ✅ 完成
- status = 'done' → 自动跳转 step5
- status = 'failed' → 显示错误 + "积分已退还" + 重试按钮
- Notification API：页面可见时不推通知；用户离开时 Notification.requestPermission + new Notification('视频生成完成')

apps/web/src/app/projects/[id]/step5/page.tsx（Step 5 - 下载）：
- HTML5 video 预览（controls，src=final_video_url）
- 下载按钮（a href download）
- 本次生成成本：来自 project.total_cost_cny
- 操作按钮：
  · "再做一个" → /projects/new
  · "基于此创建变体" → /projects/new?parent={id}

apps/web/src/app/billing/page.tsx（积分充值）：
按 saas-billing-ui SKILL.md 实现三个部分：

1. 当前余额卡片（余额 + 当前套餐 + 到期时间）

2. 积分充值包（3档，推荐标记标准包）：
   - ¥49 → 50积分（基础包）
   - ¥129 → 150积分（标准包，"最划算" badge）
   - ¥279 → 350积分（专业包）
   - 点击"立即购买"→ Toast "支付功能即将上线，请联系客服"（MVP 阶段）

3. 订阅套餐对比卡片（3列）：
   - 免费版：¥0 / 10积分/月 / 仅30s视频
   - 基础版：¥99 / 60积分/月 / 全规格 / 优先队列
   - 专业版：¥299 / 200积分/月 / 最高优先级 / 专属客服
   - 当前套餐高亮，其他显示"升级"按钮（同上 Toast）
```

---

## Phase 5：联调验证

### Step 5.1 — E2E 冒烟测试 + 关键单元测试

> 发送前打开：`AGENTS.md` + `CONTRIBUTING.md`

```
为 vid-maker 创建联调验证脚本和关键单元测试。

1. scripts/smoke-test.ts（tsx 可直接运行）：

const BASE_URL = process.env.API_URL ?? 'http://localhost:3001'
const MOCK = process.env.SMOKE_MOCK === 'true'

步骤：
a. 健康检查：GET /health → { status:'ok' }
b. 创建项目：POST /api/projects（mock userId 模式）
   body: { input_mode:'prompt', raw_input:'给一款测试产品做30s引流视频', duration_preset:'30s', aspect_ratio:'16:9', visual_style:'cinematic', voice_id:'test' }
   预期：status=201, project_id, scenes.length=5
c. 审核脚本：POST /api/projects/{id}/approve-script → status=202
d. SSE 进度：连接 /api/projects/{id}/storyboard-progress，等待 complete 事件（超时 3 分钟）
e. 验证 scenes 全部有 image_url
f. 审核分镜：POST /api/projects/{id}/approve-storyboard → status=202
g. 轮询状态直到 done 或 failed（超时 15 分钟，每 10s 一次）
h. 断言 final_video_url 可访问（HEAD 请求 200）
i. 验证积分流水：GET /api/billing/transactions → 有 consume 记录

SMOKE_MOCK=true 时跳过真实 API 调用，只验证流程骨架。

运行：tsx scripts/smoke-test.ts

2. vitest 关键单元测试：

packages/shared/src/__tests__/state-machine.test.ts：
- 测试所有合法转换通过（6条）
- 测试所有非法转换抛 Error（如 draft→producing）

apps/api/src/__tests__/credit.service.test.ts：
- 正常扣减：balance=100，扣10 → balance=90，返回true
- 余额不足：balance=5，扣10 → balance不变，抛 CREDIT_INSUFFICIENT
- 并发扣减：初始100积分，10个并发各扣20，最终 balance=0（不为负）
- refundCredits 幂等：同 projectId 调用3次，只退一次

运行 pnpm test 并确认全部通过，输出测试报告。
```

---

## 附：常用调试提示词

### 调试：BullMQ 任务失败

```
@worker-debugger

storyboard 队列有失败任务，projectId: {填入实际ID}

请帮我：
1. 查看 Redis 死信队列中该 Job 的详情
2. 分析失败原因
3. 确认 credit_transactions 表是否有 type='refund' 的退积分记录
4. 给出修复建议
```

---

### 调试：积分成本分析

```
@cost-investigator

请分析 generation_jobs 表过去 7 天的数据：
1. 按视频规格（spec_json.duration_preset）分组的平均成本
2. 找出实际成本超过估算成本 1.5 倍的项目
3. 计算各规格的真实毛利率（定价积分 - AI成本）
4. 给出是否需要调整定价的建议
```

---

### 调试：DB Schema 变更

```
@db-migration-helper

需要给 projects 表新增 {填入字段描述} 字段。

请：
1. 分析这个变更的破坏性风险
2. 修改对应的 Drizzle schema 文件
3. 生成迁移文件（pnpm --filter @vid-maker/db drizzle-kit generate）
4. 提供回滚 SQL
5. 更新 packages/shared 中对应的 Zod schema
```

---

### 审计：部署前安全检查

```
@billing-auditor

准备部署到生产环境，请全面审查：
1. 积分扣减原子性（Redis Lua 脚本是否覆盖所有场景）
2. 退积分路径完整性（所有 Worker 的 failed 事件是否都有退积分）
3. 并发安全性（是否有可能出现负积分）
4. 给出"可以部署 / 需要修复后部署"的结论
```

---

> **提示**：每次发完提示词后等 `code-reviewer` background agent 完成检查，如有 BLOCKER 先修复再继续下一步。
