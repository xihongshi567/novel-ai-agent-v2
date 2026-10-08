"""M4 修复回归：atomic_write 行为不变量。

M1/M4 之前所有 save() 都是 naive open(..., "w") + write，崩溃/断电时会留下
半新半旧的 JSON。本测试验证 atomic_write_text / atomic_write_json 的三条
核心不变量，避免后续回退到非原子写入。

运行：py -m unittest tests.test_atomic_write 或 py -m unittest discover tests
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from novel_agent.core._atomic import atomic_write_json, atomic_write_text  # noqa: E402


class AtomicWriteTests(unittest.TestCase):
    def test_write_text_normal(self):
        p = ROOT / "projects" / "_test_atomic_text.txt"
        try:
            atomic_write_text(p, "hello 世界")
            self.assertEqual(p.read_text(encoding="utf-8"), "hello 世界")
        finally:
            if p.exists():
                p.unlink()

    def test_write_json_normal(self):
        p = ROOT / "projects" / "_test_atomic.json"
        try:
            atomic_write_json(p, {"k": "中文", "n": 42}, ensure_ascii=False, indent=2)
            loaded = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(loaded, {"k": "中文", "n": 42})
        finally:
            if p.exists():
                p.unlink()

    def test_write_overwrites_existing(self):
        p = ROOT / "projects" / "_test_atomic_overwrite.json"
        try:
            atomic_write_text(p, "first")
            atomic_write_text(p, "second")
            self.assertEqual(p.read_text(encoding="utf-8"), "second")
        finally:
            if p.exists():
                p.unlink()

    def test_crash_mid_write_leaves_original_intact(self):
        """模拟写入中途抛异常：原文件不被破坏，临时文件被清理。"""
        p = ROOT / "projects" / "_test_atomic_crash.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        original = "ORIGINAL_DATA_不可丢失"
        p.write_text(original, encoding="utf-8")
        try:
            with mock.patch("os.fsync", side_effect=RuntimeError("模拟崩溃")):
                with self.assertRaises(RuntimeError):
                    atomic_write_text(p, "BAD_NEW_DATA_应该不出现")
            # 原文件保持原样
            self.assertEqual(p.read_text(encoding="utf-8"), original)
        finally:
            if p.exists():
                p.unlink()

    def test_no_temp_file_leftover(self):
        """成功后同目录不应残留 .tmp 临时文件。"""
        p = ROOT / "projects" / "_test_atomic_no_tmp.txt"
        try:
            atomic_write_text(p, "content")
            tmp_files = list(p.parent.glob(f".{p.name}.*.tmp"))
            self.assertEqual(tmp_files, [], f"残留临时文件: {tmp_files}")
        finally:
            if p.exists():
                p.unlink()

    def test_creates_parent_dir(self):
        p = ROOT / "projects" / "_test_atomic_subdir" / "deep" / "file.txt"
        try:
            atomic_write_text(p, "ok")
            self.assertTrue(p.exists())
            self.assertEqual(p.read_text(encoding="utf-8"), "ok")
        finally:
            if p.exists():
                p.unlink()
            # 清理空目录
            for d in [p.parent, p.parent.parent, p.parent.parent.parent]:
                if d.exists() and not any(d.iterdir()):
                    d.rmdir()


if __name__ == "__main__":
    unittest.main()
