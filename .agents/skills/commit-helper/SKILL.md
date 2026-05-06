---
name: commit-helper
version: "1.0"
description: 根据变更内容生成 Conventional Commits 格式的提交信息。
allowed-tools:
  - Bash
---

# commit-helper

生成符合 Conventional Commits 规范的提交信息。

## 触发条件

- 用户说"帮我写 commit message"
- 用户说"生成提交信息"

## 步骤

### Step 1：分析变更

```bash
git diff --staged --stat     # 变更文件摘要
git diff --staged            # 详细 diff
```

### Step 2：生成提交信息

格式：`<type>(<scope>): <description>`

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `refactor` | 重构（不影响功能）|
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `docs` | 文档更新 |
| `chore` | 构建/工具链更新 |
| `ci` | CI/CD 相关 |

scope 示例（vid-maker 特有）：
- `worker` / `api` / `web` / `admin` / `db` / `queue` / `shared`
- `billing` / `storyboard` / `auth` / `sse`

### Step 3：输出示例

```
feat(worker): add storyboard job with SSE progress push

- Implement FLUX.1 parallel image generation with BullMQ
- Add SSE pub/sub for real-time progress updates
- Configure dead-letter queue with automatic credit refund on failure

Closes #42
```

## 关键约束

- ✅ description 用英文小写动词开头（add / fix / implement / update）
- ✅ 超过一行时用 body 解释 why，不解释 what
- ❌ 禁止 "update code" / "fix bug" 等无意义描述
