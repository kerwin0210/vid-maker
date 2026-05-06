# vid-maker v2 系统架构设计

> 版本：v1.1 · 2026-05
> 定位：面向国内市场的 AI 视频制作 SaaS，积分+订阅混合计费，支持高并发扩展

---

## 一、技术选型

### 核心原则

1. **全栈 TypeScript**：前后端共享 Zod schema，类型安全从 DB 到 UI 贯通
2. **SaaS-Forward**：从 Day 1 就是多租户架构，不事后改造
3. **异步优先**：视频生成是长任务（5-15分钟），所有生成任务必须异步化
4. **效果优先**：每个环节选该类别全球最优模型，不以国内/国外为分类标准

### 基础设施选型

| 层级 | 选型 | 备选方案 | 选择理由 |
|------|------|---------|---------|
| API Server | **Hono.js + Node.js 22** | FastAPI（Python）| 全栈 TS 单语言；原生 SSE；可平迁 Cloudflare Workers |
| 任务队列 | **BullMQ + Redis** | FastAPI BackgroundTasks | Worker 独立进程可单独扩容；内置死信队列；优先级队列 |
| 数据库 | **PostgreSQL + Drizzle ORM** | DuckDB / MongoDB | ACID 事务保证积分一致性；Drizzle 类型安全迁移 |
| 前端 | **Next.js 15 + React 19** | Vite + React（SPA）| App Router 结构清晰；Server Actions |
| UI 组件 | **shadcn/ui + Tailwind** | MUI / Ant Design | 无包依赖，直接拥有源码 |
| 拖拽 | **dnd-kit** | react-beautiful-dnd | 活跃维护；支持无障碍；分镜网格排序 |
| 共享类型 | **Zod（packages/shared）** | 手写 TS interface | 运行时校验 + 类型推导合二为一 |
| 文件存储 | **阿里云 OSS** | 腾讯云 COS / AWS S3 | 国内 CDN 加速；S3 兼容 API |
| 认证 | **Better Auth** | NextAuth / Clerk | TypeScript 原生；手机号 OTP + 微信 OAuth |
| 支付 | **微信支付 + 支付宝** | Stripe | 国内市场唯一可行方案 |
| 内容审核 | **阿里云内容安全** | 腾讯云内容安全 | 图片+文本 API 成熟；与 OSS 同账号 |
| Monorepo | **pnpm workspaces** | Turborepo + npm | 磁盘占用小；workspace 依赖管理简洁 |
| FFmpeg | **child_process.execFile** | fluent-ffmpeg | 无额外依赖；维护风险低 |

### AI 模型选型（基于 2026 实测 Benchmark）

| 环节 | 主选 | 备选 | Benchmark 依据 |
|------|------|------|--------------|
| 脚本生成 | **Claude Sonnet 4.6** | Claude Haiku 4.5（批量降成本）| 生产 JSON 合规 98%+；GPT-5 同场景失败率 15-20% |
| 图片生成 | **FLUX 2 Pro（$0.03/张）** | Ideogram v3（文字入画）| 真实感领先；比 FLUX.1 Kontext Pro 便宜 25% |
| 视频生成 | **Kling 3.0（$0.075-0.112/秒）** | Runway Gen-4（广告级质感）| 原生 4K + 内置音频；Replicate/fal.ai 可调用 |
| TTS 配音 | **MiniMax Speech-02（$50/1M字符）** | ElevenLabs v3（多语言/声音克隆）| 全球 TTS Arena #1；中文 WER 2.252% vs ElevenLabs 16%；价格 1/4 |
| ASR 转写 | **Faster-Whisper large-v3（本地）** | OpenAI Whisper-1 API | WER 1.5%（优于 OpenAI API 的 2.8%）；Worker 本地运行零成本 |
| 视频理解 | **Claude 3.5 Sonnet Vision** | — | 共用 Anthropic Key；帧内容理解最强 |

---

## 二、整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户端（浏览器）                       │
│  Next.js 15 Web App（:3000）                                 │
│  ├── Step 1-5 向导 UI（4种输入：提示词/文案/大纲/视频导入）  │
│  ├── SSE 接收（分镜进度）                                     │
│  ├── 分镜多版本对比选优                                       │
│  └── 积分/订阅/支付/导出页面                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────────┐
│                    Hono API Server（:3001）                   │
│  ├── 路由：projects / billing / auth / sse / export          │
│  ├── 中间件：authMiddleware / rateLimiter / contentModerate  │
│  └── 积分扣减：Redis Lua 原子脚本                             │
└──────┬───────────────────┬──────────────────────────────────┘
       │ BullMQ enqueue    │ DB 读写
┌──────▼──────┐    ┌───────▼────────────────────────────────┐
│   Redis     │    │  PostgreSQL（:5432）                    │
│  ├── 队列   │    │  ├── users / subscriptions              │
│  ├── 积分   │    │  ├── credit_transactions                │
│  └── SSE    │    │  ├── projects / scenes / scene_assets   │
└──────┬──────┘    │  └── generation_jobs                    │
       │ BullMQ    └────────────────────────────────────────┘
┌──────▼──────────────────────────────────────────────────────┐
│              BullMQ Worker（独立进程，可多实例）               │
│  ├── analyze.job.ts  → Whisper ASR + Claude Vision → scenes │
│  ├── storyboard.job.ts → FLUX 2 Pro 并行出图 → SSE push     │
│  ├── produce.job.ts  → MiniMax TTS + Kling 3.0 + FFmpeg     │
│  ├── subtitle.job.ts → Whisper forced alignment → SRT       │
│  └── failed 事件 → 自动退积分 + 更新项目状态为 failed        │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP API 调用（via Provider 抽象层）
┌─────────────────────▼───────────────────────────────────────┐
│                    外部 AI API                               │
│  Claude Sonnet 4.6（脚本生成）+ Claude 3.5 Vision（帧分析）  │
│  FLUX 2 Pro via Replicate（分镜图，主）                      │
│  Ideogram v3（文字入画场景，备）                             │
│  MiniMax Speech-02（TTS 配音，主）                           │
│  ElevenLabs v3（多语言/克隆，备）                            │
│  Kling 3.0 via fal.ai/Replicate（视频生成，主）              │
│  Runway Gen-4（广告级质感，备）                              │
│  Faster-Whisper large-v3（本地 ASR，主）                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、目录结构

```
vid-maker/
├── apps/
│   ├── api/                    # Hono API Server（Node.js 22）
│   │   ├── src/
│   │   │   ├── routes/         # projects.ts / billing.ts / auth.ts / sse.ts / export.ts
│   │   │   ├── middleware/     # auth.ts / rate-limit.ts / content-moderate.ts
│   │   │   ├── services/       # credit.service.ts / project.service.ts
│   │   │   └── index.ts
│   │   └── package.json
│   │
│   ├── worker/                 # BullMQ Worker（独立进程）
│   │   ├── src/
│   │   │   ├── jobs/           # analyze.job.ts / storyboard.job.ts / produce.job.ts / subtitle.job.ts
│   │   │   ├── providers/      # AI Provider 抽象层（见第九节）
│   │   │   │   ├── image/      # image.provider.ts / flux2pro.ts / ideogram.ts
│   │   │   │   ├── video/      # video.provider.ts / kling.ts / runway.ts
│   │   │   │   └── tts/        # tts.provider.ts / minimax.ts / elevenlabs.ts
│   │   │   └── index.ts
│   │   └── package.json
│   │
│   ├── web/                    # Next.js 15 前端（用户端）
│   │   ├── src/app/
│   │   │   ├── page.tsx
│   │   │   ├── projects/[id]/  # Step 1-5 页面路由
│   │   │   ├── billing/
│   │   │   └── settings/
│   │   └── package.json
│   │
│   └── admin/                  # Next.js 15 运营后台
│       └── package.json
│
├── packages/
│   ├── shared/                 # Zod schemas + 共享类型
│   ├── db/                     # Drizzle ORM schema + 迁移
│   └── queue/                  # BullMQ Job 定义（api + worker 共用）
│
├── docs/
│   ├── architecture.md
│   ├── dev-prompts.md
│   ├── setup-guide.md
│   └── marketplace-plugins.md
│
└── scripts/
    └── check_baseline.sh
```

---

## 四、核心数据库 Schema（Drizzle）

### users 表

```typescript
export const users = pgTable('users', {
  id:            uuid('id').primaryKey().defaultRandom(),
  phone:         varchar('phone', { length: 11 }).unique(),
  wechatOpenid:  varchar('wechat_openid', { length: 64 }).unique(),
  creditBalance: integer('credit_balance').notNull().default(0),
  planId:        varchar('plan_id', { length: 32 }).notNull().default('free'),
  createdAt:     timestamp('created_at').notNull().defaultNow(),
})
```

### subscriptions 表

```typescript
export const subscriptions = pgTable('subscriptions', {
  id:             uuid('id').primaryKey().defaultRandom(),
  userId:         uuid('user_id').notNull().references(() => users.id),
  plan:           varchar('plan', { length: 32 }).notNull(),
  monthlyCredits: integer('monthly_credits').notNull(),
  expiresAt:      timestamp('expires_at').notNull(),
  createdAt:      timestamp('created_at').notNull().defaultNow(),
})
```

### credit_transactions 表

```typescript
export const creditTransactionTypeEnum = pgEnum('credit_tx_type', [
  'recharge', 'subscribe', 'consume', 'refund', 'expire',
])

export const creditTransactions = pgTable('credit_transactions', {
  id:        uuid('id').primaryKey().defaultRandom(),
  userId:    uuid('user_id').notNull().references(() => users.id),
  delta:     integer('delta').notNull(),
  type:      creditTransactionTypeEnum('type').notNull(),
  refId:     varchar('ref_id', { length: 64 }),
  createdAt: timestamp('created_at').notNull().defaultNow(),
})
```

### projects 表

```typescript
export const projectStatusEnum = pgEnum('project_status', [
  'draft', 'script_approved', 'storyboard_done', 'producing', 'done', 'failed'
])

// input_mode 新增 'video'（视频导入分析模式）
export const inputModeEnum = pgEnum('input_mode', [
  'prompt', 'article', 'outline', 'video'
])

export const projects = pgTable('projects', {
  id:               uuid('id').primaryKey().defaultRandom(),
  userId:           uuid('user_id').notNull().references(() => users.id),
  status:           projectStatusEnum('status').notNull().default('draft'),
  inputMode:        inputModeEnum('input_mode').notNull(),
  rawInput:         text('raw_input').notNull(),
  specJson:         text('spec_json').notNull(),
  sourceVideoUrl:   text('source_video_url'),   // 视频导入模式：原始视频 URL
  estimatedCostCny: integer('estimated_cost_cny').notNull().default(0),
  totalCostCny:     integer('total_cost_cny').notNull().default(0),
  finalVideoUrl:    text('final_video_url'),
  subtitleUrl:      text('subtitle_url'),       // SRT 字幕文件 URL
  parentProjectId:  uuid('parent_project_id'),
  createdAt:        timestamp('created_at').notNull().defaultNow(),
  updatedAt:        timestamp('updated_at').notNull().defaultNow(),
})
```

### scenes 表（新增专业摄影参数）

```typescript
export const scenes = pgTable('scenes', {
  id:            uuid('id').primaryKey().defaultRandom(),
  projectId:     uuid('project_id').notNull().references(() => projects.id, { onDelete: 'cascade' }),
  sceneOrder:    integer('scene_order').notNull(),
  narration:     text('narration').notNull(),
  visualPrompt:  text('visual_prompt').notNull(),
  cameraMotion:  varchar('camera_motion', { length: 128 }).notNull().default('static shot'),
  durationSec:   integer('duration_sec').notNull(),
  // 专业摄影参数（来自 Storyboard Studio）
  shotType:      varchar('shot_type', { length: 32 }),      // close_up|medium|full|long|extreme_long
  composition:   varchar('composition', { length: 32 }),    // rule_of_thirds|symmetry|golden_ratio|center
  lighting:      varchar('lighting', { length: 32 }),       // natural|soft|backlight|sidelight|toplight
  colorTone:     varchar('color_tone', { length: 32 }),     // warm|cool|high_contrast|desaturated
  // 选定的主版本资产（关联 scene_assets）
  selectedImageId: uuid('selected_image_id'),   // 用户挑选的主图
  selectedVideoId: uuid('selected_video_id'),   // 用户挑选的主视频
  audioPath:     text('audio_path'),
})
```

### scene_assets 表（新增，多版本资产）

```typescript
// 单场景多次生成保留历史，用户显式挑选最佳（来自 Storyboard Studio）
export const sceneAssets = pgTable('scene_assets', {
  id:          uuid('id').primaryKey().defaultRandom(),
  sceneId:     uuid('scene_id').notNull().references(() => scenes.id, { onDelete: 'cascade' }),
  type:        varchar('type', { length: 16 }).notNull(),     // 'image'|'video'
  url:         text('url').notNull(),
  provider:    varchar('provider', { length: 32 }).notNull(), // 'flux2pro'|'ideogram'|'kling'|'runway'
  costCny:     integer('cost_cny').notNull().default(0),
  isSelected:  boolean('is_selected').notNull().default(false),
  createdAt:   timestamp('created_at').notNull().defaultNow(),
})
```

### generation_jobs 表（新增 analyze / subtitle 类型）

```typescript
export const generationJobTypeEnum = pgEnum('generation_job_type', [
  'analyze',    // 视频导入分析（ASR + Vision）
  'script',
  'storyboard',
  'tts',
  'video',
  'subtitle',   // 字幕生成（Whisper forced alignment）
  'assemble',
])

export const generationJobs = pgTable('generation_jobs', {
  id:          uuid('id').primaryKey().defaultRandom(),
  projectId:   uuid('project_id').notNull().references(() => projects.id),
  type:        generationJobTypeEnum('type').notNull(),
  status:      varchar('status', { length: 16 }).notNull().default('pending'),
  provider:    varchar('provider', { length: 32 }),  // 记录使用了哪个 Provider
  aiCostCny:   integer('ai_cost_cny').notNull().default(0),
  startedAt:   timestamp('started_at'),
  finishedAt:  timestamp('finished_at'),
  errorMsg:    text('error_msg'),
})
```

---

## 五、视频生成状态机

```
[输入模式 prompt/article/outline] → Claude 生成脚本 → status: draft
[输入模式 video] → 上传视频 → analyze Job（Whisper+Vision）→ status: draft

     status: draft（脚本/分析结果已出，等待用户审核）
           ↓ POST /projects/:id/approve-script
     status: script_approved
（自动触发 storyboard BullMQ Job，FLUX 2 Pro 并行出图）
（SSE 推送每张图完成事件）
     status: storyboard_done（等待用户审核分镜，可多版本选优）
           ↓ POST /projects/:id/approve-storyboard
     status: producing
（MiniMax TTS + Kling 3.0 + FFmpeg + Whisper subtitle）
           ↓ 全部完成
     status: done

任意步骤失败 → status: failed（自动退积分）
```

合法转换表（代码必须 assertValidTransition）：

```typescript
export const VALID_TRANSITIONS: Record<ProjectStatus, ProjectStatus[]> = {
  draft:            ['script_approved', 'failed'],
  script_approved:  ['storyboard_done', 'failed'],
  storyboard_done:  ['producing', 'failed'],
  producing:        ['done', 'failed'],
  done:             [],
  failed:           [],
}
```

---

## 六、积分与计费设计

### 积分定价矩阵（基于实际 API 成本，汇率 $1=¥7.2）

| 规格 | FLUX 2 Pro | Kling 3.0 | MiniMax TTS | Claude | AI 成本 | 建议积分 | 毛利率 |
|------|-----------|----------|------------|--------|---------|---------|------|
| 30s（5场景）| ¥1.08 | ¥10.3 | ¥0.05 | ¥0.1 | **≈¥12** | 20积分 | ~40% |
| 1min（10场景）| ¥2.16 | ¥20.6 | ¥0.09 | ¥0.2 | **≈¥23** | 38积分 | ~39% |
| 2min（20场景）| ¥4.32 | ¥41 | ¥0.18 | ¥0.3 | **≈¥46** | 75积分 | ~39% |
| 5min（40场景）| ¥8.64 | ¥83 | ¥0.36 | ¥0.5 | **≈¥93** | 150积分 | ~38% |

> Kling 3.0：$0.112/秒 × 5秒/场景 × 7.2；FLUX 2 Pro：$0.03/张 × 7.2；MiniMax：$50/1M字符

### 订阅套餐

| 套餐 | 月费 | 每月赠积分 | 主要权益 |
|------|------|---------|---------|
| 免费版 | ¥0 | 10 | 2个30s视频/月 |
| 基础版 | ¥99 | 60 | 全规格，优先队列 |
| 专业版 | ¥299 | 200 | 最高优先级，专属客服 |

### 充值包

| 充值包 | 价格 | 积分 |
|--------|------|------|
| 基础包 | ¥49 | 50 |
| 标准包 | ¥129 | 150 |
| 专业包 | ¥299 | 400 |

---

## 七、BullMQ 任务队列设计

### 队列优先级

```typescript
await storyboardQueue.add('generate', jobData, {
  priority: user.planId === 'pro' ? 10 : 1,
  attempts: 3,
  backoff: { type: 'exponential', delay: 5000 },
})
```

### Worker 并发控制

```typescript
// 并发数受 Kling API 速率限制约束
const produceWorker = new Worker('produce', processProduceJob, {
  connection: redis,
  concurrency: 5,
})
```

### 失败自动退积分

```typescript
produceWorker.on('failed', async (job, err) => {
  if (job && job.attemptsMade >= (job.opts.attempts ?? 1)) {
    await Promise.all([
      refundCredits(job.data.userId, job.data.creditCost, job.data.projectId),
      updateProjectStatus(job.data.projectId, 'failed'),
    ])
  }
})
```

---

## 八、SSE 实时进度推送

```
Worker 完成一张分镜图（FLUX 2 Pro）
    ↓
Redis PUBLISH storyboard:{projectId} {sceneId, imageUrl, assetId}
    ↓
Hono SSE 端点 → EventSource 推送给浏览器
    ↓
前端 useStoryboardProgress Hook 更新 UI（骨架屏 → 渐入动效）
用户可在场景卡片点"生成更多"触发同场景再生成（保留历史版本）
```

---

## 九、AI Provider 抽象层

Worker 中所有 AI 调用通过统一 Provider 接口，便于切换和降级：

```typescript
// apps/worker/src/providers/image/image.provider.ts
export interface ImageProvider {
  name: string
  generate(prompt: string, spec: VideoSpec): Promise<{ url: string; costCny: number }>
}

// apps/worker/src/providers/image/flux2pro.ts
export class Flux2ProProvider implements ImageProvider {
  name = 'flux2pro'
  async generate(prompt: string, spec: VideoSpec) {
    const output = await replicate.run('black-forest-labs/flux-2-pro', {
      input: { prompt, aspect_ratio: spec.aspectRatio }
    })
    return { url: String(output), costCny: Math.round(0.03 * 7.2 * 100) }
  }
}

// 同理：VideoProvider（kling.ts / runway.ts）、TtsProvider（minimax.ts / elevenlabs.ts）
```

**Provider 选择逻辑**：

```typescript
// 运行时从环境变量读取，便于 A/B 测试和降级
const imageProvider = process.env.IMAGE_PROVIDER === 'ideogram'
  ? new IdeogramProvider()
  : new Flux2ProProvider()  // 默认主选
```

---

## 十、扩展功能（来自 Storyboard Studio + Cliptolution）

### 10.1 视频导入分析模式（第 4 种输入）

```
用户上传视频文件 → OSS 存储 → analyze.job.ts
    ↓
FFmpeg 均匀抽帧（每 scene_count/duration 秒一帧）
    ↓
Faster-Whisper large-v3（本地）→ 旁白文本 ASR
    ↓
Claude 3.5 Sonnet Vision 分析各帧画面特征
    ↓
合并生成 scenes 数组（narration + visual_prompt + professional params）
→ status: draft，进入标准 Step 2 审核流程
```

### 10.2 专业摄影参数

scenes 表新增 4 个可选字段，Claude 生成脚本时附带结构化摄影建议：

```
镜头类型（shot_type）：特写 / 中景 / 全景 / 远景 / 大远景
构图方式（composition）：三分法 / 对称 / 黄金分割 / 中心
光线设置（lighting）：自然光 / 柔光 / 逆光 / 侧光 / 顶光
色调风格（color_tone）：暖色调 / 冷色调 / 高对比度 / 低饱和度
```

这些参数融入 FLUX 2 Pro 的 prompt 中，提升生成一致性。

### 10.3 单场景多版本资产

Step 3 分镜审核页：
- 每个场景展示已生成图片
- 悬浮出现"生成更多"按钮 → 再调 FLUX 2 Pro 生成一张（保留历史）
- 底部展示该场景所有版本，用户点选 → 标记 is_selected=true
- 确认画面时只用 selected 版本进入生产流程

### 10.4 自动字幕生成

produce.job.ts 完成 TTS 后，触发 subtitle.job.ts：

```
MiniMax TTS → audio.mp3
    ↓
Faster-Whisper forced alignment（本地）→ 精确时间轴 SRT
    ↓
FFmpeg 可选：burn-in 字幕版 MP4
OSS 存储 SRT 文件，更新 projects.subtitle_url
```

### 10.5 剪映草稿导出

Step 5 新增导出选项：

```
GET /api/projects/:id/export/jianying → 返回剪映 draft JSON
GET /api/projects/:id/export/srt     → 返回 SRT 字幕文件
GET /api/projects/:id/export/json    → 返回结构化分镜 JSON
```

剪映 draft 格式参考 Storyboard Studio 实现，映射字段：
- scenes → 剪映 segments
- narration → 语音文本
- image/video URLs → 素材路径
- duration_sec → 片段时长

---

## 十一、部署架构（三阶段）

### Phase 1：MVP（月费 ~¥900）

```
单台 ECS（4核8G）
├── API Server（pm2）
├── BullMQ Worker（pm2，含 Faster-Whisper 本地模型）
└── Next.js Web（pm2）

阿里云 RDS PostgreSQL + Redis + OSS
```

### Phase 2：内测付费（月费 ~¥5000）

```
SLB 负载均衡
├── 2-3台 API Server
└── 5-10台 Worker（GPU 实例，Faster-Whisper 加速）

RDS 主从 + Redis 集群 + OSS CDN
```

### Phase 3：公测（K8s 自动扩缩）

```
ACK + KEDA（基于 BullMQ 队列深度自动扩缩 Worker）
GPU 节点池（Faster-Whisper / 未来本地模型）
```

---

## 十二、国内 SaaS 合规要点

| 要求 | 方案 |
|------|------|
| ICP 备案 | 国内 ECS + 域名备案 |
| 内容审核 | AI 生成前过阿里云内容安全 |
| 数据留存 | 用户数据存国内 RDS，不出境 |
| 隐私政策 | 上线前必须有隐私政策页面 |
| 支付合规 | 微信/支付宝商户号 + 营业执照 |
