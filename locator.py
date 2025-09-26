import subprocess
import shutil
import os
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
                    full_path = os.path.join(base, entry)
                    if os.path.isdir(full_path):
                        paths.append(full_path)
            except Exception as e:
                logging.debug("Skip base %s: %s", base, e)
        return paths

    def _search_mounts(self, pattern: str) -> List[str]:
        if not pattern.strip():
            return []
        pattern_lower = pattern.lower()
        results = []
        for path in self._get_mount_points():
            try:
                for root, _, files in os.walk(path):
                    for f in files:
                        if pattern_lower in f.lower():
                            results.append(os.path.join(root, f))
            except Exception as e:
                logging.debug("Skip walk on %s: %s", path, e)
        logging.debug("Hardware search found %d results", len(results))
        return results

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

        # Hardware-only: "hw <term>"
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            return self._search_mounts(" ".join(tokens[1:]))

        # Raw locate: "r <args>"
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

        # Default: locate + hardware
        query = " ".join(tokens)
        locate_results = self._run_locate(query)
        hardware_results = self._search_mounts(query)

        # Deduplicate (preserve order)
        seen = set()
        combined = []
        for item in locate_results + hardware_results:
            if item not in seen:
                seen.add(item)
                combined.append(item)
        return combined
