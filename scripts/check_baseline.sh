#!/usr/bin/env bash
# check_baseline.sh — vid-maker 工程基线自检脚本
# 用法：bash scripts/check_baseline.sh
# 全部通过退出 0，有任何失败退出 1

set -euo pipefail

PASS=0
FAIL=0
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

green() { echo -e "\033[32m✅ $1\033[0m"; }
red()   { echo -e "\033[31m❌ $1\033[0m"; }

check() {
  local desc="$1"
  local condition="$2"
  if eval "$condition" > /dev/null 2>&1; then
    green "$desc"
    PASS=$((PASS + 1))
  else
    red "失败：$desc"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  vid-maker 工程基线自检"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── Block 1.1 AGENTS.md ──────────────────────────────────────────────────────
echo "[ AGENTS.md ]"
check "AGENTS.md 存在" "test -f '$ROOT/AGENTS.md'"
check "AGENTS.md 包含 [Memory] section" "grep -q '\[Memory\]' '$ROOT/AGENTS.md'"
check "AGENTS.md 包含 [Pipeline State Machine] section" "grep -q '\[Pipeline State Machine\]' '$ROOT/AGENTS.md'"
check "AGENTS.md 包含 [Sub-agents] section" "grep -q '\[Sub-agents\]' '$ROOT/AGENTS.md'"
check "AGENTS.md 包含 [Cost Attribution] section" "grep -q '\[Cost Attribution\]' '$ROOT/AGENTS.md'"
check "CLAUDE.md 是软链接指向 AGENTS.md" "test -L '$ROOT/CLAUDE.md'"
echo ""

# ── Block 1.2 Rules ──────────────────────────────────────────────────────────
echo "[ .cursor/rules/ ]"
check ".cursor/rules/ 目录存在" "test -d '$ROOT/.cursor/rules'"
check "规则文件数量 ≥ 9" "[ \$(ls '$ROOT/.cursor/rules/'*.mdc 2>/dev/null | wc -l) -ge 9 ]"
check "00-never-do.mdc 存在" "test -f '$ROOT/.cursor/rules/00-never-do.mdc'"
check "05-bullmq-worker.mdc 存在" "test -f '$ROOT/.cursor/rules/05-bullmq-worker.mdc'"
check "08-memory-rag.mdc 存在" "test -f '$ROOT/.cursor/rules/08-memory-rag.mdc'"
echo ""

# ── Block 1.3 Sub-agents ─────────────────────────────────────────────────────
echo "[ Sub-agents ]"
check ".cursor/agents/ 存在且有 ≥ 8 个文件" "[ \$(ls '$ROOT/.cursor/agents/'*.md 2>/dev/null | wc -l) -ge 8 ]"
check "code-reviewer.md 存在" "test -f '$ROOT/.cursor/agents/code-reviewer.md'"
check "billing-auditor.md 存在" "test -f '$ROOT/.cursor/agents/billing-auditor.md'"
echo ""

# ── Block 1.4 Skills ─────────────────────────────────────────────────────────
echo "[ Skills ]"
check ".agents/skills/ 目录存在" "test -d '$ROOT/.agents/skills'"
check "自定义 skills 数量 ≥ 8" "[ \$(ls '$ROOT/.agents/skills/' 2>/dev/null | wc -l) -ge 8 ]"
check "sse-progress-ui SKILL.md 存在" "test -f '$ROOT/.agents/skills/sse-progress-ui/SKILL.md'"
check "saas-billing-ui SKILL.md 存在" "test -f '$ROOT/.agents/skills/saas-billing-ui/SKILL.md'"
check "Marketplace plugins 说明文件存在" "test -f '$ROOT/docs/marketplace-plugins.md'"
echo ""

# ── Block 1.5 MCP ────────────────────────────────────────────────────────────
echo "[ .mcp.json ]"
check ".mcp.json 存在" "test -f '$ROOT/.mcp.json'"
check ".mcp.json JSON 格式正确" "python3 -m json.tool '$ROOT/.mcp.json'"
check ".mcp.json 包含 project-memory" "grep -q 'project-memory' '$ROOT/.mcp.json'"
check ".mcp.json 包含 postgres" "grep -q '\"postgres\"' '$ROOT/.mcp.json'"
check ".mcp.json 包含 7 个 MCP 服务（github 已移除，走 SSH）" "[ \$(python3 -c \"import json; d=json.load(open('$ROOT/.mcp.json')); print(len(d.get('mcpServers',{})))\") -eq 7 ]"
check "git SSH 重写规则已配置" "git -C '$ROOT' config 'url.git@github.com:.insteadof' 2>/dev/null | grep -q 'https'"
echo ""

# ── Block 1.6 project-memory-rag ─────────────────────────────────────────────
echo "[ project-memory-rag ]"
check ".project-memory/vid-maker/ 目录存在" "test -d '$ROOT/.project-memory/vid-maker'"
check ".project-memory/vid-maker/meta.json 存在" "test -f '$ROOT/.project-memory/vid-maker/meta.json'"
echo ""

# ── Block 1.7 Cursor Hooks ───────────────────────────────────────────────────
echo "[ Cursor Hooks ]"
check ".cursor/hooks.json 存在" "test -f '$ROOT/.cursor/hooks.json'"
check "hooks.json JSON 格式正确" "python3 -m json.tool '$ROOT/.cursor/hooks.json'"
check "hooks.json 包含 stop Hook" "grep -q '\"stop\"' '$ROOT/.cursor/hooks.json'"
check "hooks.json 包含 sessionStart Hook" "grep -q '\"sessionStart\"' '$ROOT/.cursor/hooks.json'"
check "post_task_capture.py 存在" "test -f '$ROOT/.cursor/hooks/post_task_capture.py'"
check "session_start_query.py 存在" "test -f '$ROOT/.cursor/hooks/session_start_query.py'"
check "post_task_capture.py 可执行" "test -x '$ROOT/.cursor/hooks/post_task_capture.py'"
echo ""

# ── Block 1.8 辅助文件 ───────────────────────────────────────────────────────
echo "[ 辅助文件 ]"
check ".env.example 存在" "test -f '$ROOT/.env.example'"
check "CONTRIBUTING.md 存在" "test -f '$ROOT/CONTRIBUTING.md'"
check ".gitignore 存在" "test -f '$ROOT/.gitignore'"
echo ""

# ── 汇总 ─────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════"
echo "  自检结果：${PASS} 项通过，${FAIL} 项失败"
echo "═══════════════════════════════════════════════════════"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo -e "\033[32m🎉 工程基线配置完整，可以开始开发！\033[0m"
  exit 0
else
  echo -e "\033[31m⚠️  有 ${FAIL} 项配置不完整，请根据上方提示修复后重新运行。\033[0m"
  exit 1
fi
