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

    def _get_hardware_paths(self) -> List[str]:
        paths = []
        # 1. Your exact drive (most important)
        your_drive = "/run/media/nour/01DBF71DDDEF4780"
        if os.path.isdir(your_drive):
            paths.append(your_drive)
            logging.debug("Added your drive: %s", your_drive)
        
        # 2. Generic fallbacks (if accessible)
        candidates = [
            "/run/media",
            "/media",
            "/mnt"
        ]
        for base in candidates:
            if os.path.isdir(base):
                try:
                    for item in os.listdir(base):
                        full = os.path.join(base, item)
                        if os.path.isdir(full) and full not in paths:
                            paths.append(full)
                except Exception as e:
                    logging.debug("Skip %s: %s", base, e)
        return paths

    def _search_hardware(self, pattern: str) -> List[str]:
        if not pattern.strip():
            return []
        pattern_lower = pattern.lower()
        results = []
        for path in self._get_hardware_paths():
            try:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if pattern_lower in f.lower():
                            full_path = os.path.join(root, f)
                            results.append(full_path)
            except Exception as e:
                logging.debug("Skip walk on %s: %s", path, e)
        logging.debug("Hardware search found %d results", len(results))
        return results

    def _run_locate(self, query: str) -> List[str]:
        if not self.locate_cmd:
            return []
        try:
            cmd = [self.locate_cmd, "-i", query]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return lines
        except Exception as e:
            logging.debug("Locate failed: %s", e)
            return []

    def run(self, pattern: str) -> List[str]:
        logging.debug("Search triggered with: %r", pattern)
        if not pattern or not pattern.strip():
            return []

        tokens = pattern.strip().split()
        
        # Hardware-only mode: "hw <term>"
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            term = " ".join(tokens[1:])
            return self._search_hardware(term)

        # Raw locate mode: "r <args>"
        if tokens[0].lower() == "r" and len(tokens) > 1:
            try:
                cmd = [self.locate_cmd] + tokens[1:]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                return [line.strip() for line in result.stdout.splitlines() if line.strip()]
            except:
                return []

        # Default: locate + hardware
        locate_results = self._run_locate(" ".join(tokens))
        hardware_results = self._search_hardware(" ".join(tokens))
        
        # Deduplicate (locate first)
        seen = set()
        combined = []
        for item in locate_results + hardware_results:
            if item not in seen:
                seen.add(item)
                combined.append(item)
        return combined
