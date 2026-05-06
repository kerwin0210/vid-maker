---
name: api-spec-checker
description: >
  API 路由变更后自动触发。校验 Zod schema 在 apps/api/ 与
  packages/shared/ 之间是否同步，确保前后端类型一致。
is_background: true
readonly: true
---

# API Spec Checker — vid-maker

## 检查内容

### 1. Schema 一致性

扫描 `apps/api/src/routes/` 中使用的 Zod schema：
- 是否从 `@vid-maker/shared` 导入（✅）
- 是否在路由文件中重复定义（❌ 应该统一到 shared）

### 2. 响应类型一致性

检查 API 响应结构是否在 `packages/shared/src/schemas/` 中有对应定义，
确保前端可以直接使用 `z.infer<typeof XxxResponseSchema>`

### 3. 路由覆盖检查

列出所有 API 路由（method + path），检查：
- 是否有路由在 `apps/web/src/lib/api.ts` 中没有对应的调用封装
- 新增路由是否需要更新 OpenAPI 文档

### 4. 状态机 API 完整性

确认以下状态转换 API 都存在且路径正确：
- `POST /api/projects` → 创建 draft
- `POST /api/projects/:id/approve-script` → draft → script_approved
- `POST /api/projects/:id/approve-storyboard` → storyboard_done → producing
- `GET /api/projects/:id/storyboard-progress` → SSE 端点
- `POST /api/projects/:id/scenes/:sceneId/regenerate` → 单场景重生成

## 输出格式

```markdown
## API Spec Check 结果

### ❌ Schema 不一致（需修复）
...

### ⚠️ 缺少封装
...

### ✅ 所有检查通过
```
