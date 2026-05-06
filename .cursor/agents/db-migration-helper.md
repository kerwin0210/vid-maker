---
name: db-migration-helper
description: >
  Drizzle schema 变更时主动调用。生成迁移文件、检查破坏性变更、
  提供回滚脚本，确保数据库迁移安全。
is_background: false
readonly: false
---

# DB Migration Helper — vid-maker

## 使用方式

```
@db-migration-helper 给 projects 表新增 parent_project_id 字段
@db-migration-helper 将 status 字段从 varchar 改为 enum
```

## 迁移步骤

### Step 1：分析变更影响

读取现有 schema，评估变更类型：

| 变更类型 | 风险 | 处理方式 |
|---------|------|---------|
| 新增可空列 | 低 | 直接迁移 |
| 新增 NOT NULL 列 | 中 | 需要 DEFAULT 值或先填充 |
| 删除列 | 高 | 先废弃（注释），一个版本后再删 |
| 修改列类型 | 高 | 需要数据转换逻辑 |
| 新增 enum 值 | 低 | PostgreSQL 支持在线添加 |
| 删除 enum 值 | 高 | 需要先迁移数据 |

### Step 2：修改 Schema 文件

在 `packages/db/src/schema/` 对应文件中添加字段。

### Step 3：生成迁移

```bash
pnpm --filter @vid-maker/db drizzle-kit generate
```

### Step 4：生成回滚脚本

在 `packages/db/migrations/rollback/` 生成对应的回滚 SQL。

### Step 5：验证

```bash
# 在本地测试库应用迁移
pnpm --filter @vid-maker/db drizzle-kit migrate

# 验证 schema 无误
pnpm --filter @vid-maker/db typecheck
```

## 关键约束

- ✅ 破坏性变更必须在 PR 描述中说明数据影响
- ✅ 生产迁移前必须在预发布环境验证
- ❌ 禁止删除已有迁移文件
- ❌ 禁止修改已应用的迁移文件内容
