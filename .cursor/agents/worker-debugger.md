---
name: worker-debugger
description: >
  BullMQ 任务失败时主动调用。分析死信队列、Job 日志，
  确认退积分是否触发，给出修复建议。
is_background: false
readonly: true
---

# Worker Debugger — vid-maker

## 使用方式

```
@worker-debugger 分析 storyboard Job 失败，projectId: xxx-xxx
```

## 调试步骤

### Step 1：查看失败 Job

```bash
# 通过 Redis CLI 查看死信队列
redis-cli
> LRANGE bull:storyboard:failed 0 10
> HGETALL bull:storyboard:1234
```

### Step 2：分析失败原因

常见失败原因分类：

| 错误类型 | 典型错误信息 | 处理建议 |
|---------|------------|---------|
| Kling API 超时 | `Request timeout after 30000ms` | 增加 timeout，改为轮询 |
| Kling API 限流 | `429 Too Many Requests` | 降低 Worker 并发数，加 backoff |
| FLUX.1 内容违规 | `Content policy violation` | 检查内容审核是否漏判 |
| 积分余额不足 | `Insufficient credits` | 检查扣减时机，是否在创建 Job 前已扣 |
| DB 连接超时 | `Connection timeout` | 检查连接池配置 |

### Step 3：确认退积分是否触发

```bash
# 查看 credit_transactions 表中是否有对应 refund 记录
psql $DATABASE_URL -c "
  SELECT * FROM credit_transactions
  WHERE ref_id = 'PROJECT_ID' AND type = 'refund'
  ORDER BY created_at DESC LIMIT 5;
"
```

如果没有 refund 记录，说明退积分未触发，需要检查：
1. Worker `failed` 事件是否注册
2. `job.attemptsMade >= job.opts.attempts` 条件是否满足
3. `refundCredits` 函数是否抛出了异常

### Step 4：手动触发退积分（紧急修复）

```typescript
// 通过 REPL 手动退积分
await refundCredits(userId, creditCost, projectId)
await updateProjectStatus(projectId, 'failed')
```

## 输出格式

```markdown
## Worker Debug 报告

**Job ID**：xxx
**Queue**：storyboard
**失败次数**：3/3
**失败原因**：...

**退积分状态**：✅ 已退还 / ❌ 未退还（需手动处理）

**根因分析**：...

**修复建议**：...
```
