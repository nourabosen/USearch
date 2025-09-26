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
        self.limit = None  # Not used for truncation

    def set_limit(self, limit):
        # Keep for compatibility; main.py uses it for pagination
        try:
            self.limit = int(limit)
        except:
            self.limit = None

    def _discover_mounts(self) -> List[str]:
        paths = []
        for base in ["/run/media", "/media", "/mnt"]:
            if os.path.isdir(base):
                try:
                    for entry in os.listdir(base):
                        full = os.path.join(base, entry)
                        if os.path.isdir(full):
                            paths.append(full)
                except:
                    pass
        return paths

    def _escape_pattern(self, pat: str) -> str:
        for c in r'[]?*{}!':
            pat = pat.replace(c, '\\' + c)
        return pat

    def _search_hardware(self, pattern: str) -> List[str]:
        if not pattern.strip():
            return []
        results = []
        safe_pat = self._escape_pattern(pattern)
        for path in self._discover_mounts():
            if self.find_cmd:
                try:
                    cmd = [self.find_cmd, path, "-iname", f"*{safe_pat}*"]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
                    if res.returncode <= 1:  # 0=ok, 1=no matches
                        results.extend(line.strip() for line in res.stdout.splitlines() if line.strip())
                except:
                    pass
            else:
                # Fallback to os.walk
                try:
                    for root, _, files in os.walk(path):
                        for f in files:
                            if pattern.lower() in f.lower():
                                results.append(os.path.join(root, f))
                except:
                    pass
        return results

    def _run_locate(self, tokens: List[str], raw: bool = False) -> List[str]:
        if not self.locate_cmd:
            return []
        try:
            if raw:
                cmd = [self.locate_cmd] + tokens
            else:
                cmd = [self.locate_cmd, "-i", " ".join(tokens)] if tokens else [self.locate_cmd, "-i", ""]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            if res.returncode in (0, 1):
                return [line.strip() for line in res.stdout.splitlines() if line.strip()]
        except:
            pass
        return []

    def _dedupe(self, items: List[str]) -> List[str]:
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
            return self._dedupe(self._search_hardware(" ".join(tokens[1:])))

        # Raw mode
        raw = tokens[0].lower() == "r" and len(tokens) > 1
        locate_tokens = tokens[1:] if raw else tokens

        locate_results = self._run_locate(locate_tokens, raw_mode=raw)
        hardware_results = [] if raw else self._search_hardware(" ".join(locate_tokens))

        return self._dedupe(locate_results + hardware_results)
