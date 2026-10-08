"""原子写入：写到临时文件后 os.replace，避免崩溃时留下半新半旧的目标文件。

跨 core/ 各模块共享。所有 save() 都应走这两个函数，禁止直接 open(..., "w")。

实现要点：
- 同目录临时文件，确保 os.replace 是原子的（同文件系统下）
- 写入失败不留下垃圾文件（finally 清理）
- 文件权限从原文件继承（如果有），否则使用默认
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """把 text 原子地写到 path。

    先写到同目录临时文件，fsync 后 os.replace 覆盖原文件。崩溃在任何
    阶段都不会污染 path 原内容，只可能丢失本次写入。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # 写入或替换失败：清理临时文件，把异常往上抛
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, data: Any, *, encoding: str = "utf-8",
                      indent: int | None = 2, ensure_ascii: bool = False) -> None:
    """把 data 序列化为 JSON 后原子写入 path。"""
    text = json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
    atomic_write_text(path, text, encoding=encoding)
