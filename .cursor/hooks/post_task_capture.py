#!/usr/bin/env python3
"""
post_task_capture.py — vid-maker Cursor Stop Hook

Agent 每次完成回合（stop 事件）后自动运行。
分析 Agent 响应内容，判断是否值得写入 project-memory-rag。

触发写入的条件：
- 含错误/报错/exception/修复/fixed → capture_error
- 含迁移/重构/migration/refactor   → capture_task_end
- 含选择了/决定/ADR               → capture_adr
- 含完成了/已完成/successfully 且长度 > 300 字 → capture_task_end

failClosed: false 保证记忆写入失败时不影响 Cursor 正常工作。
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent.parent  # vid-maker/
PMR_PATH = str(PROJECT_ROOT / ".project-memory" / "vid-maker")
PMR_PROJECT = "vid-maker"
PMR_DIM = int(os.getenv("PMR_DIM", "64"))  # 测试模式用 64，生产模式用 1024


# ── Mock embed（无 bge-m3 时降级使用）────────────────────────────────────────

def _mock_embed(texts: list[str]) -> list[list[float]]:
    """确定性 mock embed，仅用于开发环境（无 bge-m3 时）。"""
    result = []
    for text in texts:
        seed = sum(ord(c) for c in text[:50])
        rng = random.Random(seed)
        result.append([rng.random() for _ in range(PMR_DIM)])
    return result


def _get_embed_fn():
    try:
        from FlagEmbedding import BGEM3FlagModel  # type: ignore[import]
        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
        return lambda texts: model.encode(texts)["dense_vecs"].tolist(), 1024
    except ImportError:
        return _mock_embed, PMR_DIM


# ── 关键词判断 ────────────────────────────────────────────────────────────────

ERROR_KEYWORDS = ["错误", "报错", "exception", "修复", "fixed", "fix:", "bug"]
REFACTOR_KEYWORDS = ["迁移", "重构", "migration", "refactor", "重写", "重新设计"]
ADR_KEYWORDS = ["选择了", "决定", "选型", "adr", "因为", "原因是", "为什么选"]
DONE_KEYWORDS = ["完成了", "已完成", "successfully", "done", "实现了", "上线了"]


def classify_response(text: str) -> str | None:
    """判断响应类型，返回 event_type 或 None（不需要记录）。"""
    lower = text.lower()
    if any(kw in lower for kw in ERROR_KEYWORDS):
        return "error"
    if any(kw in lower for kw in ADR_KEYWORDS):
        return "adr"
    if any(kw in lower for kw in REFACTOR_KEYWORDS):
        return "task_end"
    if any(kw in lower for kw in DONE_KEYWORDS) and len(text) > 300:
        return "task_end"
    return None


# ── 主逻辑 ───────────────────────────────────────────────────────────────────

def main() -> int:
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            return 0

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"final_response": raw}

        response_text = data.get("final_response", "")
        if not response_text:
            return 0

        event_type = classify_response(response_text)
        if event_type is None:
            return 0

        # 动态加载 project-memory-rag
        # 优先使用环境变量指定的路径，其次尝试 pip 安装版本
        pmr_src_env = os.getenv("PMR_SRC_PATH", "")
        if pmr_src_env:
            pmr_src = Path(pmr_src_env)
            if pmr_src.exists():
                sys.path.insert(0, str(pmr_src))

        try:
            from project_memory_rag import MemoryCapture, MemoryStore  # type: ignore[import]
        except ImportError:
            return 0  # 未安装时静默跳过

        embed_fn, vector_size = _get_embed_fn()
        store = MemoryStore(path=PMR_PATH, embed_fn=embed_fn, vector_size=vector_size)
        cap = MemoryCapture(store, project=PMR_PROJECT)

        summary = response_text[:200].strip()

        if event_type == "error":
            cap.capture_error(
                error_msg=f"[Auto-captured] {summary}",
                solution=response_text[:500],
                tags=["auto-capture", "error-fix"],
            )
        elif event_type == "adr":
            cap.capture_adr(
                title=f"[Auto-captured ADR] {summary[:80]}",
                decision=summary,
                rationale=response_text[:500],
                tags=["auto-capture", "adr"],
            )
        else:
            cap.capture_task_end(
                task_desc=f"[Auto-captured] {summary[:80]}",
                outcome=response_text[:500],
                tags=["auto-capture", "task-complete"],
            )

        return 0

    except Exception:  # noqa: BLE001
        # failClosed: false — 任何异常都静默处理，不影响 Cursor
        return 0


if __name__ == "__main__":
    sys.exit(main())
