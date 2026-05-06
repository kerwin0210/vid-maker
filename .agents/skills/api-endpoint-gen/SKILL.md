---
name: api-endpoint-gen
version: "1.0"
description: 生成 Hono API 路由，含 Zod schema 定义、auth 中间件、用户隔离、统一错误处理和 vitest 单元测试。
allowed-tools:
  - Read
  - Write
  - Glob
---

# api-endpoint-gen

为 vid-maker API Server 生成符合规范的 Hono 路由端点。

## 触发条件

- 用户说"新增 XX 接口"
- 用户描述了 API 功能需求
- 需要修改现有路由

## 生成步骤

### Step 1：在 packages/shared 定义 Zod Schema

```typescript
// packages/shared/src/schemas/[feature].schema.ts
export const CreateXxxSchema = z.object({
  // 定义请求体字段
})
export type CreateXxxInput = z.infer<typeof CreateXxxSchema>

export const XxxResponseSchema = z.object({
  // 定义响应字段
})
export type XxxResponse = z.infer<typeof XxxResponseSchema>
```

### Step 2：生成 Hono 路由

```typescript
// apps/api/src/routes/[feature].ts
import { Hono } from 'hono'
import { zValidator } from '@hono/zod-validator'
import { authMiddleware } from '../middleware/auth'
import { CreateXxxSchema } from '@vid-maker/shared'

const router = new Hono()
router.use('*', authMiddleware)

router.post('/', zValidator('json', CreateXxxSchema), async (c) => {
  const input = c.req.valid('json')
  const userId = c.get('userId')

  // 业务逻辑
  const result = await xxxService.create(userId, input)

  return c.json(result, 201)
})

export { router as xxxRouter }
```

### Step 3：生成 vitest 测试

```typescript
// apps/api/src/routes/[feature].test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { testClient } from 'hono/testing'
import { app } from '../app'

describe('POST /xxx', () => {
  it('成功创建，返回 201', async () => { ... })
  it('未认证时返回 401', async () => { ... })
  it('请求体不合法时返回 400', async () => { ... })
  it('访问他人资源时返回 404', async () => { ... })
})
```

## 关键约束

- ✅ 所有路由必须经过 authMiddleware
- ✅ 请求体必须用 zValidator 校验（不手写验证逻辑）
- ✅ 所有 DB 查询必须带 userId 条件
- ✅ 错误统一抛出 AppError，不直接 return 错误 JSON
- ❌ 禁止在路由层写业务逻辑（抽到 service 层）
