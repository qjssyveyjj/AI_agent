"""
管理员批量入库脚本：遍历目录，将支持的文档逐个入库。

用法（在 backend 目录下）：
    python -m scripts.ingest_dir /path/to/docs

纯内网环境同样适用，只要 DATABASE_URL 与 EMBED_* 配置正确。
"""

import asyncio
import sys
from pathlib import Path

from app.kb.db import close_kb, init_kb
from app.kb.parser import UnsupportedFileType
from app.kb.service import ingest_document

SUPPORTED = {".pdf", ".docx", ".xlsx", ".txt", ".md", ".csv", ".json", ".log"}


async def main(target: str) -> None:
    root = Path(target)
    if not root.exists():
        print(f"路径不存在：{target}")
        return

    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED]
    if not files:
        print("未找到可入库的文档")
        return

    await init_kb()
    ok, fail = 0, 0
    for p in files:
        try:
            info = await ingest_document(p.name, p.read_bytes(), source="batch")
            print(f"[OK] {p.name} -> {info['chunk_count']} 片段")
            ok += 1
        except (UnsupportedFileType, ValueError) as e:
            print(f"[SKIP] {p.name}: {e}")
            fail += 1
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {p.name}: {type(e).__name__}: {e}")
            fail += 1
    await close_kb()
    print(f"\n完成：成功 {ok}，失败/跳过 {fail}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python -m scripts.ingest_dir <目录路径>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
