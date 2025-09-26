import subprocess
import shutil
import os
import logging
import threading
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
        self.limit = None
        logging.debug("Locator initialized. locate_cmd: %s", self.locate_cmd)

    def set_limit(self, limit):
        try:
            self.limit = int(limit)
        except:
            self.limit = None

    def _get_mount_points(self) -> List[str]:
        paths = []
        bases = ["/run/media", "/media", "/mnt"]
        for base in bases:
            if not os.path.isdir(base):
                continue
            try:
                for entry in os.listdir(base):
                    full = os.path.join(base, entry)
                    if os.path.isdir(full):
                        paths.append(full)
            except Exception as e:
                logging.debug("Skip base %s: %s", base, e)
        return paths

    def _walk_with_timeout(self, path: str, pattern: str, timeout: int = 8) -> List[str]:
        result = []
        exception = None

        def target():
            nonlocal exception
            try:
                pattern_lower = pattern.lower()
                for root, _, files in os.walk(path):
                    for f in files:
                        if pattern_lower in f.lower():
                            result.append(os.path.join(root, f))
            except Exception as e:
                exception = e

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            logging.warning("Timeout scanning %s (>%d sec)", path, timeout)
            return []
        if exception:
            logging.debug("Walk failed on %s: %s", path, exception)
            return []
        return result

    def _search_mounts(self, pattern: str) -> List[str]:
        if not pattern.strip():
            return []
        all_results = []
        for path in self._get_mount_points():
            logging.debug("Scanning hardware path: %s", path)
            results = self._walk_with_timeout(path, pattern, timeout=6)
            all_results.extend(results)
        logging.debug("Hardware search total results: %d", len(all_results))
        return all_results

    def _run_locate(self, query: str) -> List[str]:
        if not self.locate_cmd:
            return []
        try:
            out = subprocess.check_output(
                [self.locate_cmd, "-i", query],
                text=True,
                timeout=5,
                stderr=subprocess.DEVNULL
            )
            return [line.strip() for line in out.splitlines() if line.strip()]
        except Exception as e:
            logging.debug("Locate failed: %s", e)
            return []

    def run(self, pattern: str) -> List[str]:
        if not pattern or not pattern.strip():
            return []

        tokens = pattern.strip().split()

        if tokens[0].lower() == "hw" and len(tokens) > 1:
            return self._search_mounts(" ".join(tokens[1:]))

        if tokens[0].lower() == "r" and len(tokens) > 1:
            try:
                out = subprocess.check_output(
                    [self.locate_cmd] + tokens[1:],
                    text=True,
                    timeout=5,
                    stderr=subprocess.DEVNULL
                )
                return [line.strip() for line in out.splitlines() if line.strip()]
            except:
                return []

        query = " ".join(tokens)
        locate_results = self._run_locate(query)
        hardware_results = self._search_mounts(query)

        seen = set()
        combined = []
        for item in locate_results + hardware_results:
            if item not in seen:
                seen.add(item)
                combined.append(item)
        return combined
