---
name: drizzle-migration
version: "1.0"
description: 生成 Drizzle ORM 迁移文件，检查破坏性变更，提供回滚脚本。
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# drizzle-migration

为 vid-maker 数据库 schema 变更生成安全的迁移文件。

## 触发条件

- 用户说"给 XX 表加字段"
- 用户说"修改 schema"
- Drizzle schema 文件发生变更

## 生成步骤

### Step 1：检查现有 Schema

```bash
# 读取当前 schema 文件
cat packages/db/src/schema/*.ts
# 查看已有迁移
ls packages/db/migrations/
```

### Step 2：修改 Schema 文件

```typescript
// packages/db/src/schema/projects.ts
// 添加新字段示例
export const projects = pgTable('projects', {
  // ... 现有字段
  parentProjectId: uuid('parent_project_id').references(() => projects.id), // 新增
})
```

### Step 3：生成迁移文件

```bash
pnpm --filter @vid-maker/db drizzle-kit generate
# 生成文件：packages/db/migrations/XXXX_add_parent_project_id.sql
```

### Step 4：审查生成的 SQL

检查以下破坏性变更：
- `DROP COLUMN`：会丢失数据，需要先备份
- `ALTER COLUMN ... NOT NULL`：需要先填充现有 NULL 值
- `DROP TABLE`：需要二次确认
- 修改 enum 类型：PostgreSQL 限制，需要特殊处理

### Step 5：生成回滚脚本

```sql
-- packages/db/migrations/rollback/XXXX_rollback.sql
ALTER TABLE projects DROP COLUMN IF EXISTS parent_project_id;
```

### Step 6：应用迁移

```bash
pnpm --filter @vid-maker/db drizzle-kit migrate
```

## 关键约束

- ❌ 禁止手动修改已应用的迁移文件
- ❌ 禁止在生产环境 drizzle-kit push（必须走迁移文件）
- ✅ 每次 schema 变更必须同步更新 packages/shared 中对应的 Zod schema
- ✅ 破坏性变更需要先在本地验证，再提 PR 审查
