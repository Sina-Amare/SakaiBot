"""Atomic .env writer.

Preserves existing lines/comments/order, writes atomically (temp + os.replace),
backs up to .env.bak before the first change, and never logs secret values.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)

ENV_PATH = Path(".env")


class EnvWriter:
    def __init__(self, path: Path = ENV_PATH) -> None:
        self.path = Path(path)

    def read(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        if not self.path.exists():
            return out
        for line in self.path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
        return out

    def set_many(self, updates: Dict[str, Optional[str]]) -> None:
        """Set/replace keys. A value of None or '' removes that key.

        Atomic and comment-preserving. Keys not in ``updates`` are untouched.
        """
        existing_lines = []
        if self.path.exists():
            existing_lines = self.path.read_text(encoding="utf-8").splitlines()

        remaining = dict(updates)
        out_lines = []
        for line in existing_lines:
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                key = line.split("=", 1)[0].strip()
                if key in remaining:
                    val = remaining.pop(key)
                    if val is None or val == "":
                        continue  # drop this key
                    out_lines.append(f"{key}={val}")
                    continue
            out_lines.append(line)
        for key, val in remaining.items():
            if val is None or val == "":
                continue
            out_lines.append(f"{key}={val}")

        content = "\n".join(out_lines).rstrip("\n") + "\n"
        target_dir = self.path.resolve().parent
        target_dir.mkdir(parents=True, exist_ok=True)

        # Backup before mutating.
        try:
            if self.path.exists():
                bak = self.path.with_name(self.path.name + ".bak")
                bak.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass

        fd, tmp = tempfile.mkstemp(dir=str(target_dir), prefix=".env.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

        logger.info("Updated .env keys: %s", ", ".join(sorted(updates.keys())))
