import os
import subprocess
import shutil
from typing import List

class Locator:
    def __init__(self):
        self.locate_cmd = shutil.which("plocate") or shutil.which("locate")
        self.limit = None  # main.py handles display limit

    def set_limit(self, limit):
        # Keep for compatibility; not used for truncation
        pass

    def _get_mounts(self) -> List[str]:
        mounts = []
        for base in ["/run/media", "/media", "/mnt"]:
            if os.path.isdir(base):
                try:
                    for item in os.listdir(base):
                        full = os.path.join(base, item)
                        if os.path.isdir(full):
                            mounts.append(full)
                except:
                    pass
        return mounts

    def _search_hardware(self, pattern: str) -> List[str]:
        if not pattern.strip():
            return []
        results = []
        pattern_l = pattern.lower()
        for path in self._get_mounts():
            try:
                for root, _, files in os.walk(path, topdown=True):
                    for f in files:
                        if pattern_l in f.lower():
                            results.append(os.path.join(root, f))
            except:
                pass  # skip inaccessible paths
        return results

    def _run_locate(self, query: str) -> List[str]:
        if not self.locate_cmd:
            return []
        try:
            cmd = [self.locate_cmd, "-i", query]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=5)
            return [line.strip() for line in out.splitlines() if line.strip()]
        except:
            return []

    def run(self, pattern: str) -> List[str]:
        if not pattern or not pattern.strip():
            return []

        tokens = pattern.strip().split()

        # Hardware-only mode
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            return self._search_hardware(" ".join(tokens[1:]))

        # Raw mode
        if tokens[0].lower() == "r" and len(tokens) > 1:
            try:
                cmd = [self.locate_cmd] + tokens[1:]
                out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=5)
                return [line.strip() for line in out.splitlines() if line.strip()]
            except:
                return []

        # Default: locate + hardware
        query = " ".join(tokens)
        locate_results = self._run_locate(query)
        hardware_results = self._search_hardware(query)

        # Deduplicate (locate first)
        seen = set()
        combined = []
        for item in locate_results + hardware_results:
            if item not in seen:
                seen.add(item)
                combined.append(item)
        return combined
