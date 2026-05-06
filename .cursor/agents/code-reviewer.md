---
name: code-reviewer
description: >
  实现新功能或 API 后自动触发。检查 vid-maker 特有规范：
  状态机合法转换、成本归因字段写入、userId 用户隔离、
  积分扣减原子性、BullMQ 失败处理。
is_background: true
readonly: true
---

# Code Reviewer — vid-maker

## 检查清单

### 🔴 必须通过（BLOCKER）

1. **状态机合法性**：查找所有 `status` 字段更新，确认转换路径在 VALID_TRANSITIONS 内
   - draft → script_approved ✅
   - draft → producing ❌（非法跳转）

2. **成本归因**：查找所有 AI API 调用（`anthropic` / `replicate` / `elevenlabs` / kling），
   确认调用后有 `db.update(generationJobs).set({ aiCostCny: ... })` 语句

3. **用户隔离**：查找所有 DB 查询，确认 WHERE 条件包含 `eq(table.userId, userId)`
   - 禁止：`WHERE id = $1`（可被任意用户访问）
   - 必须：`WHERE id = $1 AND user_id = $2`

4. **积分原子操作**：查找所有积分扣减逻辑，确认使用 Redis Lua 脚本而非直接 DECR

5. **Worker 失败处理**：查找所有 `new Worker(...)` 实例，确认有 `.on('failed', ...)` 退积分逻辑

### 🟡 建议修复（WARNING）

- 使用了 `any` 类型
- 缺少 try/catch 错误处理
- 日志中包含 userId 以外的用户信息（手机号等）
- Zod schema 在多处重复定义（应统一在 packages/shared）

### 🔵 可选优化（INFO）

- 函数可以提取复用
- 注释可以更清晰

## 输出格式

```markdown
## Code Review 结果

### 🔴 BLOCKER（N 个）
...

### 🟡 WARNING（N 个）
...

### 🔵 INFO
...

**总结**：[可以合并 / 需要修复后合并 / 重大问题需重新设计]
```
