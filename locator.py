import subprocess
import shutil
import os
import glob
import logging
from typing import List

LOG_PATH = "/tmp/ul_locator_debug.log"
logging.basicConfig(filename=LOG_PATH,
                    level=logging.DEBUG,
                    format="%(asctime)s %(levelname)s: %(message)s")


class Locator:
    def __init__(self):
        # prefer plocate
        self.locate_cmd = shutil.which("plocate") or shutil.which("locate")
        self.find_cmd = shutil.which("find")
        self.limit = None  # do not truncate here; let main.py paginate
        self.hardware_bases = ["/run/media", "/media", "/mnt"]

        logging.debug("Locator init; locate_cmd=%s find_cmd=%s", self.locate_cmd, self.find_cmd)

    def set_limit(self, limit):
        try:
            self.limit = int(limit)
            logging.debug("set_limit -> %s", self.limit)
        except Exception:
            logging.exception("set_limit: invalid value: %s", limit)
            self.limit = None

    def _discover_hardware_paths(self) -> List[str]:
        """Return a list of existing directories to search on external/media mounts."""
        paths = []
        try:
            # /run/media/<user>/<volume>
            base = "/run/media"
            if os.path.isdir(base):
                for user in os.listdir(base):
                    userdir = os.path.join(base, user)
                    if os.path.isdir(userdir):
                        for vol in os.listdir(userdir):
                            p = os.path.join(userdir, vol)
                            if os.path.isdir(p):
                                paths.append(p)

            # /media/* and /mnt/*
            for base in ["/media", "/mnt"]:
                if os.path.isdir(base):
                    for p in glob.glob(os.path.join(base, "*")):
                        if os.path.isdir(p):
                            paths.append(p)
        except Exception:
            logging.exception("Error discovering hardware paths")

        # dedupe preserve order
        seen = set()
        out = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                out.append(p)
        logging.debug("Discovered hardware paths: %s", out)
        return out

    def _run_locate(self, tokens: List[str], raw_mode: bool = False) -> List[str]:
        """Run plocate/locate and return lines (or empty list if not available)."""
        if not self.locate_cmd:
            logging.debug("No locate/plocate command available")
            return []

        if raw_mode:
            cmd = [self.locate_cmd] + tokens
        else:
            # case-insensitive search of the joined pattern
            pattern = " ".join(tokens)
            cmd = [self.locate_cmd, "-i", pattern]

        logging.debug("Running locate: %s", cmd)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            out = proc.stdout or ""
            # if locate produced no stdout but stderr contains info, log it
            if proc.stderr:
                logging.debug("locate stderr: %s", proc.stderr.strip())
            lines = [l for l in out.splitlines() if l.strip()]
            logging.debug("locate returned %d lines", len(lines))
            return lines
        except Exception as e:
            logging.exception("locate run failed: %s", e)
            return []

    def _run_find_on_path(self, path: str, pattern: str, timeout: int = 20) -> List[str]:
        """Run 'find path -iname *pattern*' and return matches. Uses subprocess find when available."""
        if not os.path.isdir(path):
            return []

        if self.find_cmd:
            cmd = [self.find_cmd, path, "-iname", f"*{pattern}*"]
            logging.debug("Running find: %s", cmd)
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                out = proc.stdout or ""
                if proc.stderr:
                    logging.debug("find stderr (path=%s): %s", path, proc.stderr.strip())
                lines = [l for l in out.splitlines() if l.strip()]
                logging.debug("find(%s) returned %d lines", path, len(lines))
                return lines
            except subprocess.TimeoutExpired:
                logging.warning("find timed out on %s", path)
                return []
            except Exception:
                logging.exception("find failed on %s", path)
                return []
        else:
            # fallback to Python os.walk (may be slower)
            logging.debug("find command not found; using os.walk fallback on %s", path)
            matches = []
            want = pattern.lower()
            try:
                for dirpath, dirnames, filenames in os.walk(path):
                    for fn in filenames:
                        if want in fn.lower():
                            matches.append(os.path.join(dirpath, fn))
                logging.debug("os.walk found %d files in %s", len(matches), path)
            except Exception:
                logging.exception("os.walk failed on %s", path)
            return matches

    def _run_find(self, pattern: str) -> List[str]:
        """Run find across all discovered hardware paths and return combined results."""
        paths = self._discover_hardware_paths()
        if not paths:
            logging.debug("No hardware paths discovered")
            return []

        results = []
        for p in paths:
            try:
                results.extend(self._run_find_on_path(p, pattern))
            except Exception:
                logging.exception("Error searching path %s", p)
        logging.debug("Total find results across hardware: %d", len(results))
        return results

    @staticmethod
    def _unique_preserve_order(items: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in items:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def run(self, pattern: str) -> List[str]:
        """
        pattern: full string typed after the keyword (e.g. "foo", "r -S .png", "hw summer")
        Behavior:
         - "hw <pattern>" -> only hardware find on detected mount points
         - "r <args...>" -> raw locate mode (tokens passed to locate)
         - otherwise -> run locate (fast) AND run find on hardware mounts; merge results
        Returns combined list (no limit applied).
        """
        logging.debug("run called with pattern: %r", pattern)
        if not pattern or not pattern.strip():
            logging.debug("Empty pattern -> returning []")
            return []

        tokens = pattern.strip().split()
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            search_term = " ".join(tokens[1:])
            logging.debug("Hardware-only search for: %s", search_term)
            find_results = self._run_find(search_term)
            return self._unique_preserve_order(find_results)

        # raw locate prefix: 'r <args...>'
        raw_mode = (tokens[0].lower() == "r" and len(tokens) > 1)
        if raw_mode:
            locate_tokens = tokens[1:]
        else:
            locate_tokens = tokens

        # run locate (fast)
        locate_results = self._run_locate(locate_tokens, raw_mode=raw_mode)

        # also run hardware find (non-empty pattern needed)
        search_term = " ".join(locate_tokens)
        find_results = []
        if search_term.strip():
            find_results = self._run_find(search_term)

        combined = locate_results + find_results
        combined = self._unique_preserve_order(combined)
        logging.debug("Combined result count: %d", len(combined))
        return combined


# quick manual test when executed directly
if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
    loc = Locator()
    if not q:
        print("Usage: python3 locator.py <query>   (try 'hw <term>' to search mounted drives only)")
        print(f"Debug log: {LOG_PATH}")
        sys.exit(0)
    res = loc.run(q)
    print(f"Found {len(res)} results (showing up to 200):")
    for i, r in enumerate(res[:200], 1):
        print(f"{i:03d}: {r}")
    print(f"\nDebug log: {LOG_PATH}")
