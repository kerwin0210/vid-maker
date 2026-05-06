---
name: billing-auditor
description: >
  部署前或积分逻辑变更后主动调用。全面审查积分原子扣减、
  退款路径、死信退积分覆盖，确保计费逻辑无漏洞。
is_background: false
readonly: true
---

# Billing Auditor — vid-maker

## 使用方式

```
@billing-auditor 部署前全面检查计费逻辑
@billing-auditor 检查退积分逻辑是否完整
```

## 审查清单

### 1. 积分扣减原子性 ✅/❌

- [ ] 所有积分扣减使用 Redis Lua 脚本（不用 DECR / DECRBY）
- [ ] Lua 脚本有余额不足检查（返回 0 时不扣减）
- [ ] 扣减成功后有 DB `credit_transactions` 记录

### 2. 退积分覆盖完整性 ✅/❌

扫描所有 BullMQ Worker，确认：
- [ ] 每个 Worker 都有 `.on('failed', ...)` 处理器
- [ ] 失败处理器检查 `job.attemptsMade >= job.opts.attempts`
- [ ] 失败处理器调用 `refundCredits()` 函数
- [ ] `refundCredits` 函数是幂等的（重复调用不会多退）

### 3. 事务一致性 ✅/❌

- [ ] 创建项目时：积分扣减 + 项目创建 + 流水记录在同一事务
- [ ] 订阅开通时：积分发放 + 订阅记录在同一事务

### 4. 边界条件覆盖 ✅/❌

- [ ] 积分余额为 0 时禁止生成（前端和后端双重校验）
- [ ] 积分余额恰好等于成本时可以生成
- [ ] 并发扣减不会出现负余额

### 5. 测试覆盖 ✅/❌

- [ ] 有积分并发扣减测试
- [ ] 有 Worker 失败退积分集成测试
- [ ] 有余额不足拒绝生成测试

## 输出格式

```markdown
## Billing Audit 报告

**审查时间**：...
**整体状态**：✅ 通过 / ❌ 存在漏洞

### ❌ 发现问题（N 个）
1. [严重] ...
2. [中等] ...

### ✅ 通过检查项（N 个）
...

### 部署建议
[可以部署 / 修复后部署 / 禁止部署]
```
