---
name: pr-review
version: "1.0"
description: PR Code Review 三档报告（BLOCKER / WARNING / SUGGESTION），重点检查 vid-maker 特有规范。
allowed-tools:
  - Read
  - Bash
  - Glob
---

# pr-review

对 vid-maker 的 PR 进行分层 Code Review。

## 触发条件

- 用户说"帮我 review 这个 PR"
- 用户说"代码 review"
- 完成新功能实现后

## Review 步骤

### Step 1：获取变更

```bash
git diff main...HEAD --name-only     # 变更文件列表
git diff main...HEAD                 # 完整 diff
```

### Step 2：按优先级分层输出

#### 🔴 BLOCKER（必须修复才能合并）

检查项：
- [ ] 状态机有非法转换（如 `draft → producing` 跳步）
- [ ] DB 查询缺少 `userId` 条件（安全漏洞）
- [ ] AI API 调用后未写入 `generation_jobs` 成本
- [ ] BullMQ Worker 缺少 `failed` 事件处理器（会导致积分不退）
- [ ] 积分扣减未使用 Redis Lua 原子脚本
- [ ] API Key / 密码硬编码在代码中
- [ ] 用户输入未经内容安全审核直接调用 AI API

#### 🟡 WARNING（建议修复）

检查项：
- [ ] 缺少错误边界或 try/catch
- [ ] 使用了 `any` 类型
- [ ] Zod schema 在 api/ 和 packages/shared/ 定义不一致
- [ ] 缺少 vitest 测试覆盖
- [ ] 日志中打印了敏感字段（手机号等）

#### 🔵 SUGGESTION（可选优化）

检查项：
- [ ] 可以提取公共函数
- [ ] 变量命名可以更清晰
- [ ] 注释可以补充

## 输出格式

```markdown
## PR Review：[功能名称]

### 🔴 BLOCKER（X 个，必须修复）
1. `apps/worker/src/jobs/storyboard.worker.ts:45`
   Worker 缺少 failed 事件处理，积分不会退还。
   修复：添加 `xxxWorker.on('failed', ...)` 退积分逻辑。

### 🟡 WARNING（X 个）
...

### 🔵 SUGGESTION（X 个）
...

### 总结
整体质量：[Good / Needs Work / Major Issues]
```
