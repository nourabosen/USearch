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
        self.locate_cmd = self._find_locate_cmd()
        self.find_cmd = shutil.which("find")
        self.limit = None  # main.py handles pagination
        logging.debug("Locator init: locate=%s, find=%s", self.locate_cmd, self.find_cmd)

    def _find_locate_cmd(self):
        return shutil.which("plocate") or shutil.which("locate")

    def set_limit(self, limit):
        # This is called by main.py, but we don't use it for truncation
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
                except Exception as e:
                    logging.debug("Skip %s: %s", base, e)
        return paths

    def _escape_find_pattern(self, pattern: str) -> str:
        for char in r'[]?*{}!':
            pattern = pattern.replace(char, '\\' + char)
        return pattern

    def _run_find_on_path(self, path: str, pattern: str, timeout: int = 10) -> List[str]:
        if not pattern.strip() or not os.path.isdir(path):
            return []
        safe_pattern = self._escape_find_pattern(pattern)
        if self.find_cmd:
            cmd = [self.find_cmd, path, "-iname", f"*{safe_pattern}*"]
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                # find returns 1 when no matches → not an error
                if result.returncode > 1:
                    logging.debug("find failed on %s: rc=%d, stderr=%s", path, result.returncode, result.stderr.strip())
                    return []
                return [line.strip() for line in result.stdout.splitlines() if line.strip()]
            except subprocess.TimeoutExpired:
                logging.warning("find timed out on %s", path)
                return []
            except Exception as e:
                logging.exception("find exception on %s: %s", path, e)
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
            except Exception as e:
                logging.exception("os.walk failed on %s: %s", path, e)
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
            cmd = [self.locate_cmd, "-i"] + (tokens if tokens else [""])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            if result.returncode not in (0, 1):
                logging.debug("locate failed: rc=%d, stderr=%s", result.returncode, result.stderr.strip())
                return []
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except Exception as e:
            logging.exception("locate exception: %s", e)
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
        logging.debug("Run called with pattern: %r", pattern)
        if not pattern or not pattern.strip():
            return []

        tokens = pattern.strip().split()

        # Hardware-only mode
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            search_term = " ".join(tokens[1:])
            find_results = self._run_find(search_term)
            return self._unique_preserve_order(find_results)

        # Raw locate mode
        raw_mode = tokens[0].lower() == "r" and len(tokens) > 1
        if raw_mode:
            locate_tokens = tokens[1:]
        else:
            locate_tokens = tokens

        # Run locate
        locate_results = self._run_locate(locate_tokens, raw_mode=raw_mode)

        # Run find on hardware mounts
        search_term = " ".join(locate_tokens)
        find_results = self._run_find(search_term) if search_term.strip() else []

        # Merge: locate first, then find
        combined = locate_results + find_results
        return self._unique_preserve_order(combined)
