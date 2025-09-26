import os
import subprocess
import shutil
import logging
from typing import List

LOG_PATH = "/tmp/ul_locator_debug.log"
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s"
)

class Locator:
    def __init__(self):
        self.locate_cmd = shutil.which("plocate") or shutil.which("locate")
        self.find_cmd = shutil.which("find")
        self.limit = None  # main.py handles pagination

    def set_limit(self, limit):
        # Keep for compatibility, but not used for truncation
        try:
            self.limit = int(limit)
        except (ValueError, TypeError):
            self.limit = None

    def _discover_mounts(self) -> List[str]:
        paths = []
        bases = ["/run/media", "/media", "/mnt"]
        for base in bases:
            if os.path.isdir(base):
                try:
                    for entry in os.listdir(base):
                        full = os.path.join(base, entry)
                        if os.path.isdir(full):
                            paths.append(full)
                except Exception:
                    pass
        return paths

    def _escape_find_pattern(self, pattern: str) -> str:
        for char in r'[]?*{}!':
            pattern = pattern.replace(char, '\\' + char)
        return pattern

    def _run_find_on_path(self, path: str, pattern: str, timeout: int = 8) -> List[str]:
        if not pattern.strip() or not os.path.isdir(path):
            return []
        safe_pattern = self._escape_find_pattern(pattern)
        if self.find_cmd:
            cmd = [self.find_cmd, path, "-iname", f"*{safe_pattern}*"]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                if result.returncode > 1:
                    return []
                return [line.strip() for line in result.stdout.splitlines() if line.strip()]
            except:
                return []
        else:
            # Fallback to os.walk
            matches = []
            want = pattern.lower()
            try:
                for root, _, files in os.walk(path):
                    for f in files:
                        if want in f.lower():
                            matches.append(os.path.join(root, f))
            except:
                pass
            return matches

    def _run_find(self, pattern: str) -> List[str]:
        if not pattern.strip():
            return []
        results = []
        for path in self._discover_mounts():
            results.extend(self._run_find_on_path(path, pattern))
        return results

    def _run_locate(self, tokens: List[str], raw_mode: bool = False) -> List[str]:
        if not self.locate_cmd:
            return []
        if raw_mode:
            cmd = [self.locate_cmd] + tokens
        else:
            cmd = [self.locate_cmd, "-i", " ".join(tokens)] if tokens else [self.locate_cmd, "-i", ""]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            if result.returncode not in (0, 1):
                return []
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except:
            return []

    def _unique_preserve_order(self, items: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in items:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def run(self, pattern: str) -> List[str]:
        if not pattern or not pattern.strip():
            return []

        tokens = pattern.strip().split()

        # Hardware-only mode
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            search_term = " ".join(tokens[1:])
            return self._unique_preserve_order(self._run_find(search_term))

        # Raw locate mode
        raw_mode = tokens[0].lower() == "r" and len(tokens) > 1
        locate_tokens = tokens[1:] if raw_mode else tokens

        locate_results = self._run_locate(locate_tokens, raw_mode=raw_mode)
        find_results = self._run_find(" ".join(locate_tokens)) if not raw_mode else []

        return self._unique_preserve_order(locate_results + find_results)
