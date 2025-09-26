import subprocess
import shutil
import os
import logging
from typing import List

LOG_PATH = "/tmp/ul_locator_debug.log"
logging.basicConfig(filename=LOG_PATH, level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")

class Locator:
    def __init__(self):
        self.locate_cmd = shutil.which("plocate") or shutil.which("locate")
        self.limit = None
        logging.debug("Locator started (hardware search via os.walk)")

    def set_limit(self, limit):
        self.limit = int(limit) if limit and limit.isdigit() else None

    def _discover_hardware_paths(self) -> List[str]:
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
        # Add /run/media/$USER/* explicitly
        try:
            user_dir = f"/run/media/{os.getlogin()}"
            if os.path.isdir(user_dir):
                for vol in os.listdir(user_dir):
                    p = os.path.join(user_dir, vol)
                    if os.path.isdir(p) and p not in paths:
                        paths.append(p)
        except Exception:
            pass
        # Dedupe
        return list(dict.fromkeys(paths))

    def _run_locate(self, tokens, raw_mode=False):
        if not self.locate_cmd:
            return []
        cmd = [self.locate_cmd] + (tokens if raw_mode else ["-i", " ".join(tokens)])
        try:
            out = subprocess.check_output(cmd, text=True, timeout=6, stderr=subprocess.DEVNULL)
            return [l for l in out.splitlines() if l.strip()]
        except Exception:
            return []

    def _run_find(self, pattern: str) -> List[str]:
        if not pattern.strip():
            return []
        results = []
        for path in self._discover_hardware_paths():
            try:
                want = pattern.lower()
                for root, _, files in os.walk(path):
                    for f in files:
                        if want in f.lower():
                            results.append(os.path.join(root, f))
            except Exception:
                pass
        return results

    def _unique_preserve_order(self, items):
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
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            return self._unique_preserve_order(self._run_find(" ".join(tokens[1:])))

        raw_mode = tokens[0].lower() == "r" and len(tokens) > 1
        locate_tokens = tokens[1:] if raw_mode else tokens

        locate_results = self._run_locate(locate_tokens, raw_mode)
        find_results = self._run_find(" ".join(locate_tokens))
        return self._unique_preserve_order(locate_results + find_results)

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:])
    if not q:
        print("Usage: python3 locator.py '<query>'")
        sys.exit(1)
    res = Locator().run(q)
    for r in res[:50]:
        print(r)
