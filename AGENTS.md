# AGENTS.md — vid-maker v2
> 版本：v1.1 · 2026-05 · vid-maker SaaS 项目

---

## [Project]

**一句话描述**：vid-maker 是面向国内市场的 AI 视频制作 SaaS，用户通过 5 步交互流程生成电商/产品引流视频，支持积分+订阅混合计费。

**核心端口**：
- API Server（Hono）：`http://localhost:3001`
- Web 前端（Next.js）：`http://localhost:3000`
- Admin 后台：`http://localhost:3002`
- PostgreSQL：`localhost:5432`
- Redis：`localhost:6379`

**Monorepo 结构**：
```
vid-maker/
├── apps/
│   ├── api/        # Hono API Server（Node.js 22）
│   ├── worker/     # BullMQ Worker（独立进程）
│   ├── web/        # Next.js 15 前端（用户端）
│   └── admin/      # Next.js 15 后台（运营端）
├── packages/
│   ├── shared/     # Zod schemas + 共享类型
│   ├── db/         # Drizzle ORM schema + 迁移文件
│   └── queue/      # BullMQ Job 定义（api 和 worker 共用）
├── docs/           # 架构文档
└── scripts/        # 运维脚本
```

---

## [Tech Stack]

### 基础设施

| 层级 | 选型 | 说明 |
|------|------|------|
| API Server | Hono.js + Node.js 22 | 轻量 TypeScript-first，原生 SSE |
| 任务队列 | BullMQ + Redis | Worker 独立扩容，死信队列，优先级 |
| 数据库 | PostgreSQL + Drizzle ORM | 多租户就绪，类型安全迁移 |
| 前端 | Next.js 15 + React 19 | App Router，shadcn/ui + dnd-kit |
| 共享类型 | Zod（packages/shared）| 前后端共用，运行时校验 |
| 文件存储 | 阿里云 OSS | S3 兼容，CDN 分发 |
| 认证 | Better Auth | 手机号 OTP + 微信 OAuth |
| 支付 | 微信支付 + 支付宝 | 国内主流 |
| 内容审核 | 阿里云内容安全 | 生成前前置过滤 |
| RAG 记忆 | project-memory-rag v1.0 | MCP Server，自动捕获开发经验 |

### AI 模型（效果优先，基于 2026 Benchmark）

| 环节 | 主选 | 备选 | 关键指标 |
|------|------|------|---------|
| 脚本生成 | Claude Sonnet 4.6 | Claude Haiku 4.5 | JSON 合规 98%+，最佳结构化输出 |
| 图片生成 | FLUX 2 Pro（Replicate）| Ideogram v3 | $0.03/张，真实感领先，6s 生成 |
| 视频生成 | Kling 3.0（fal.ai）| Runway Gen-4 | 原生 4K + 内置音频，$0.112/秒 |
| TTS 配音 | MiniMax Speech-02 | ElevenLabs v3 | 全球 TTS Arena #1，中文 WER 2.252% |
| ASR 转写 | Faster-Whisper large-v3（本地）| OpenAI Whisper-1 API | WER 1.5%，零 API 成本 |
| 视频理解 | Claude 3.5 Sonnet Vision | — | 共用 Anthropic Key |

---

## [Key Modules]

| 路径 | 职责 | 关键文件 |
|------|------|---------|
| `apps/api/src/routes/` | HTTP 路由，状态机转换触发点 | `projects.ts` / `sse.ts` / `billing.ts` / `export.ts` |
| `apps/worker/src/jobs/` | 异步任务执行 | `analyze.job.ts` / `storyboard.job.ts` / `produce.job.ts` / `subtitle.job.ts` |
| `apps/worker/src/providers/` | AI Provider 抽象层（可插拔）| `image/flux2pro.ts` / `video/kling.ts` / `tts/minimax.ts` |
| `apps/web/src/app/projects/` | 5 步向导前端页面 | `step1/` ~ `step5/` |
| `packages/db/src/schema/` | Drizzle 表定义 | `users.ts` / `projects.ts` / `billing.ts` / `scene-assets.ts` |
| `packages/shared/src/` | 跨包 Zod schemas | `project.schema.ts` / `billing.schema.ts` |
| `packages/queue/src/` | BullMQ Job 类型定义 | `jobs.ts` / `queues.ts` |

---

## [Pipeline State Machine]

视频生成流水线的 6 个状态，**只能按以下路径转换，禁止跳状态**：

```
draft
  ↓ POST /projects/:id/approve-script（用户确认脚本）
script_approved
  ↓ 自动触发 storyboard BullMQ Job
storyboard_done
  ↓ POST /projects/:id/approve-storyboard（用户确认分镜）
producing
  ↓ 自动完成（TTS + Kling + FFmpeg）
done

任意状态 → failed（外部 API 报错 or 超时）
```

**合法转换表**（代码中必须 assert）：

```typescript
const VALID_TRANSITIONS: Record<ProjectStatus, ProjectStatus[]> = {
  draft:            ['script_approved', 'failed'],
  script_approved:  ['storyboard_done', 'failed'],
  storyboard_done:  ['producing', 'failed'],
  producing:        ['done', 'failed'],
  done:             [],
  failed:           [],
}
```

---

## [SaaS Rules]

### 积分原子扣减（必须用 Redis Lua 脚本）

```typescript
// 禁止直接 DECR，必须用原子脚本防超扣
const deductScript = `
  local balance = tonumber(redis.call('GET', KEYS[1]))
  if balance == nil or balance < tonumber(ARGV[1]) then return 0 end
  redis.call('DECRBY', KEYS[1], ARGV[1])
  return 1
`
```

### 任务失败必须退积分

```typescript
worker.on('failed', async (job, err) => {
  if (job && job.attemptsMade >= (job.opts.attempts ?? 1)) {
    await refundCredits(job.data.userId, job.data.creditCost, job.data.projectId)
  }
})
```

### 内容审核前置

所有用户输入（提示词/文案/大纲）在调用 Claude/FLUX.1 之前必须先过阿里云内容安全 API，审核不通过直接拒绝并返回 400。

---

## [Sub-agents]

### Cursor Sub-agents（.cursor/agents/）

**Background 自动触发（is_background: true）**：

| Agent | 触发时机 | 核心检查项 |
|-------|---------|-----------|
| `code-reviewer` | 实现新功能/API 后 | 状态机合法性、成本归因字段、userId 隔离 |
| `test-writer` | 新增函数/路由后 | vitest 单元测试 + playwright E2E |
| `security-auditor` | 新增 API 端点或处理用户输入时 | SQL 注入、缺失 auth 中间件、PII 泄露 |
| `api-spec-checker` | API 路由变更后 | Zod schema 在 api/ 与 packages/shared/ 同步 |

**主动调用（显式 @agent-name）**：

| Agent | 使用时机 |
|-------|---------|
| `worker-debugger` | BullMQ 任务失败时 |
| `cost-investigator` | 查 AI 成本/毛利时 |
| `db-migration-helper` | Drizzle schema 变更时 |
| `billing-auditor` | 部署前/积分逻辑变更后 |

---

## [MCP Services]

| MCP | 用途 | 权限 |
|-----|------|------|
| `filesystem` | 项目文件读写 | 限 vid-maker/ 目录 |
| `postgres` | PostgreSQL 查询（开发库）| 读写 |
| `redis` | 积分余额/队列状态查看 | 只读 |
| `playwright` | 前端 E2E 自动化测试 | — |
| `aliyun-oss` | 查看 OSS 存储文件 | 只读 |
| `cost-watcher` | AI API 费用查询 | 只读 |
| `project-memory` | RAG 记忆读写 | 读写 |

> Git 操作使用 SSH（`git@github.com:`），项目已配置 URL 重写规则，无需额外 Token。

---

## [Cost Attribution]

每次调用 AI API（Claude / FLUX.1 / ElevenLabs / Kling）后，**必须**将实际成本写入 `generation_jobs` 表：

```typescript
await db.update(generationJobs)
  .set({
    aiCostCny: actualCost,
    status: 'done',
    finishedAt: new Date(),
  })
  .where(eq(generationJobs.id, jobId))
```

**禁止** 只在内存中累计成本而不持久化。`projects.totalCostCny` 由所有 `generation_jobs.aiCostCny` 汇总计算。

---

## [Memory]

### 使用 project-memory-rag（通过 MCP project-memory）

**必须调用 `query_memory` 的场景（任务开始前）**：
- 遇到外部 API 对接问题（Kling / FLUX.1 / ElevenLabs）
- 遇到 BullMQ 队列/并发问题
- 遇到 PostgreSQL / Drizzle 迁移问题
- 遇到积分扣减逻辑 bug

**必须调用 `ingest_memory` 的场景（任务完成后）**：
- 修复了外部 API 报错（capture_error）
- 做了架构决策（capture_adr）
- 完成了重大功能模块（capture_task_end）
- PR 合并了重要变更（capture_pr）

**不需要写入的场景**：
- 日常 CRUD 接口开发
- 样式/UI 调整
- 文档更新

### 查询示例

```
query_memory("Kling API 超时处理")
query_memory("BullMQ 死信队列配置")
query_memory("积分扣减并发安全")
```

# 版本：v1.0 · 2026-05 · vid-maker SaaS 项目
