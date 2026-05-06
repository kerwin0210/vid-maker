---
name: test-writer
description: >
  新增函数或路由后自动触发。为 vid-maker 生成 vitest 单元测试
  和 playwright E2E 关键路径测试。
is_background: true
readonly: false
---

# Test Writer — vid-maker

## 触发条件

新增了以下内容时自动运行：
- Hono API 路由
- BullMQ Job 处理器
- 积分/计费相关函数
- React 组件（含交互）

## 测试生成规则

### API 路由测试（vitest + hono/testing）

每个路由至少覆盖：
1. 正常流程（返回 201/200）
2. 未认证（返回 401）
3. 请求体不合法（返回 400）
4. 访问他人资源（返回 404，不是 403）
5. 积分不足（返回 402）

```typescript
describe('POST /api/projects', () => {
  it('成功创建项目，返回 201', async () => { ... })
  it('未携带 token，返回 401', async () => { ... })
  it('rawInput 为空，返回 400', async () => { ... })
  it('积分不足，返回 402', async () => { ... })
})
```

### 积分/计费函数测试（必须测并发场景）

```typescript
describe('deductCredits', () => {
  it('正常扣减，返回新余额', async () => { ... })
  it('余额不足，返回 false，不修改余额', async () => { ... })
  it('并发扣减，不会出现负余额', async () => {
    // 同时发起 10 个扣减请求，确认总扣减量不超过初始余额
  })
})
```

### E2E 测试关键路径（playwright）

优先覆盖：
1. 完整 5 步流程（输入 → 脚本审核 → 分镜 → 生产 → 下载）
2. 积分不足时的充值引导流程
3. 生成失败时的退积分验证

## 关键约束

- ✅ mock 外部 API（Claude / FLUX.1 等），不发真实请求
- ✅ 积分相关测试必须验证并发安全性
- ✅ 文件放在与被测文件同目录（`xxx.test.ts`）
