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

    def set_limit(self, limit):
        self.limit = int(limit) if limit and limit.isdigit() else None

    def _get_mounts(self):
        # Only scan paths we know work
        candidates = [
            "/run/media/nour/01DBF71DDDEF4780",  # YOUR EXACT PATH
        ]
        # Add generic ones too
        try:
            for user in os.listdir("/run/media"):
                for vol in os.listdir(f"/run/media/{user}"):
                    candidates.append(f"/run/media/{user}/{vol}")
        except:
            pass
        for base in ["/media", "/mnt"]:
            try:
                for item in os.listdir(base):
                    candidates.append(f"{base}/{item}")
            except:
                pass
        # Keep only existing directories
        return [p for p in candidates if os.path.isdir(p)]

    def _search_mounts(self, pattern: str) -> List[str]:
        if not pattern.strip():
            return []
        results = []
        for path in self._get_mounts():
            try:
                for root, _, files in os.walk(path):
                    for f in files:
                        if pattern.lower() in f.lower():
                            results.append(os.path.join(root, f))
            except Exception as e:
                logging.error("Skip %s: %s", path, e)
        return results

    def _run_locate(self, query: str) -> List[str]:
        if not self.locate_cmd:
            return []
        try:
            out = subprocess.check_output([self.locate_cmd, "-i", query], text=True, timeout=5, stderr=subprocess.DEVNULL)
            return [line for line in out.splitlines() if line.strip()]
        except:
            return []

    def run(self, pattern: str) -> List[str]:
        if not pattern or not pattern.strip():
            return []

        tokens = pattern.strip().split()
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            return self._search_mounts(" ".join(tokens[1:]))

        raw = tokens[0].lower() == "r" and len(tokens) > 1
        locate_tokens = tokens[1:] if raw else tokens
        locate_query = " ".join(locate_tokens)

        locate_results = self._run_locate(locate_query) if not raw else []
        if raw:
            return locate_results

        find_results = self._search_mounts(locate_query)
        # Dedupe
        seen = set()
        combined = []
        for item in locate_results + find_results:
            if item not in seen:
                seen.add(item)
                combined.append(item)
        return combined
