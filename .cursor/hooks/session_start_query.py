#!/usr/bin/env python3
"""
session_start_query.py — vid-maker Cursor SessionStart Hook

打开新 Cursor 会话时自动运行。
查询最近 5 条 project-memory-rag 记忆，以 additional_context 形式
注入到会话上下文，帮助 Agent 快速了解项目历史踩坑和架构决策。

failClosed: false 保证记忆查询失败时不影响 Cursor 正常工作。
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent.parent
PMR_PATH = str(PROJECT_ROOT / ".project-memory" / "vid-maker")
PMR_DIM = int(os.getenv("PMR_DIM", "64"))
TOP_N = 5


# ── Mock embed ────────────────────────────────────────────────────────────────

def _mock_embed(texts: list[str]) -> list[list[float]]:
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


# ── 主逻辑 ───────────────────────────────────────────────────────────────────

def main() -> int:
    try:
        # 优先使用环境变量指定的路径，其次尝试 pip 安装版本
        pmr_src_env = os.getenv("PMR_SRC_PATH", "")
        if pmr_src_env:
            pmr_src = Path(pmr_src_env)
            if pmr_src.exists():
                sys.path.insert(0, str(pmr_src))

        try:
            from project_memory_rag import MemoryStore  # type: ignore[import]
        except ImportError:
            return 0

        if not Path(PMR_PATH).exists():
            return 0

        embed_fn, vector_size = _get_embed_fn()
        store = MemoryStore(path=PMR_PATH, embed_fn=embed_fn, vector_size=vector_size)

        # 查询最近记忆（用通用查询词）
        results = store.retrieve("项目开发经验踩坑架构决策", top_n=TOP_N)

        if not results:
            return 0

        lines = ["## vid-maker 项目记忆（最近 5 条）\n"]
        for i, r in enumerate(results, 1):
            entry = r.entry
            lines.append(f"**{i}. [{entry.event_type.value}]** {entry.content[:100]}...")
            if hasattr(entry, 'solution') and entry.solution:
                lines.append(f"   → {entry.solution[:80]}")
            lines.append("")

        context = "\n".join(lines)

        # 输出 Cursor Hook 期望的格式
        output = {
            "additional_context": context
        }
        print(json.dumps(output, ensure_ascii=False))
        return 0

    except Exception:  # noqa: BLE001
        return 0


if __name__ == "__main__":
    sys.exit(main())
