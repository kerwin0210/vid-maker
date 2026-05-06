# 贡献指南 — vid-maker

## 5 分钟快速上手

### 1. 环境准备

```bash
# 克隆并进入项目
cd ~/Desktop/workspace/vid-maker

# 安装依赖（需要 Node.js 22 + pnpm）
pnpm install

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API Keys

# 验证工程基线配置完整
bash scripts/check_baseline.sh
```

### 2. 启动开发环境

```bash
# 启动数据库（需要 Docker）
docker compose up -d postgres redis

# 运行数据库迁移
pnpm --filter @vid-maker/db drizzle-kit migrate

# 启动所有服务
pnpm dev           # 同时启动 api + web + worker
# 或单独启动：
pnpm --filter api dev       # API: http://localhost:3001
pnpm --filter web dev       # Web: http://localhost:3000
pnpm --filter worker dev    # Worker（后台进程）
```

### 3. 在 Cursor 中打开项目

**重要**：打开 `vid-maker/` 根目录，**不要只打开 src/**

```bash
cursor ~/Desktop/workspace/vid-maker
```

### 4. 第一次对话建议

打开 Cursor 后，在 Composer 中输入：

```
请帮我介绍一下 vid-maker 项目的架构，包括：
1. 技术栈和各模块职责
2. 视频生成的状态机流程
3. 我应该从哪里开始了解代码
```

---

## 5 条必读规则

> 详细内容在 `.cursor/rules/` 目录，以下是最重要的摘要：

### 1. 绝对不做（00-never-do.mdc）
- API Key 不能写进代码，必须用 `process.env.XXX`
- DB 查询必须带 `userId` 条件（防止越权访问）
- 积分扣减必须用 Redis Lua 原子脚本

### 2. 状态机不能跳步（AGENTS.md [Pipeline State Machine]）
```
draft → script_approved → storyboard_done → producing → done
```
不能直接 `draft → producing`，必须按顺序流转。

### 3. AI API 调用后必须记录成本（07-cost-aware.mdc）
```typescript
// 每次调用后必须写入 generation_jobs
await db.update(generationJobs).set({ aiCostCny: actualCost })
```

### 4. Worker 失败必须退积分（05-bullmq-worker.mdc）
```typescript
worker.on('failed', async (job) => {
  if (job.attemptsMade >= job.opts.attempts) {
    await refundCredits(job.data.userId, job.data.creditCost, ...)
  }
})
```

### 5. 开始前查记忆，完成后写记忆（08-memory-rag.mdc）
遇到外部 API 问题时先 `query_memory`，修复后 `ingest_memory`。

---

## project-memory-rag 使用

项目有内置的 AI 开发记忆系统，记录了架构决策和踩坑经验。

### 查询历史记忆

```
# 在 Cursor 中通过 MCP 调用（自动触发）
# 或手动在 Composer 中询问：
"@project-memory 查询 BullMQ 相关的历史踩坑"
```

### 查看已有记忆

```bash
python3 << 'EOF'
import sys, random
sys.path.insert(0, '/Users/kerwin/Desktop/workspace/AI自动化课件/课件资料/3 核心技术落地/toolkit/project-memory-rag/src')
from project_memory_rag import MemoryStore

def mock_embed(texts):
    return [[random.Random(sum(ord(c) for c in t[:50])).random() for _ in range(64)] for t in texts]

store = MemoryStore(path='.project-memory/vid-maker', embed_fn=mock_embed, vector_size=64)
results = store.retrieve('架构决策', top_n=5)
for r in results:
    print(f"[{r.entry.event_type.value}] {r.entry.content[:80]}")
EOF
```

---

## 常用命令

```bash
# 运行测试
pnpm test                          # 全部
pnpm --filter api test             # 仅 API 测试
pnpm --filter web test             # 仅前端测试

# 代码检查
pnpm lint                          # ESLint + Biome
pnpm typecheck                     # TypeScript 类型检查

# 数据库
pnpm --filter @vid-maker/db drizzle-kit generate   # 生成迁移
pnpm --filter @vid-maker/db drizzle-kit migrate    # 应用迁移

# 工程基线自检
bash scripts/check_baseline.sh
```

---

## 遇到问题？

1. 先查项目记忆：`query_memory("关键词")`
2. 看 `AGENTS.md` 对应 section
3. 查 `.cursor/rules/` 对应规则文件
4. 看 `docs/architecture.md` 架构说明
