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
        self.find_timeout = 10  # seconds per drive
        self.max_find_results = 1000  # prevent hanging on very large drives

        logging.debug("Locator init; locate_cmd=%s find_cmd=%s", self.locate_cmd, self.find_cmd)

    def set_limit(self, limit):
        try:
            self.limit = int(limit)
            logging.debug("set_limit -> %s", self.limit)
        except Exception:
            logging.exception("set_limit: invalid value: %s", limit)
            self.limit = None

    def _parse_pattern(self, pattern: str) -> tuple:
        """
        Returns: (mode, search_term, raw_mode)
        modes: 'hardware', 'raw', 'combined'
        """
        pattern = pattern.strip()
        if not pattern:
            return 'combined', '', False
        
        # Hardware-only mode
        if pattern.lower().startswith('hw '):
            return 'hardware', pattern[3:].strip(), False
        
        # Raw locate mode
        if pattern.lower().startswith('r '):
            return 'raw', pattern[2:].strip(), True
        
        return 'combined', pattern, False

    def _should_skip_path(self, path: str) -> bool:
        """Skip certain paths even if they match hardware_bases pattern."""
        skip_patterns = [
            '/media/cdrom', '/media/cdrecorder',  # CD/DVD drives
            '/mnt/system', '/mnt/secure',         # System mounts
        ]
        return any(path.startswith(pattern) for pattern in skip_patterns)

    def _is_mounted(self, path: str) -> bool:
        """Check if a path is actually mounted (not just a directory)."""
        try:
            # Use findmnt to check if the path is a mount point
            result = subprocess.run(
                ['findmnt', '-n', '-o', 'TARGET', path],
                capture_output=True, text=True, timeout=2
            )
            return result.returncode == 0 and path in result.stdout
        except Exception:
            # Fallback: check if it's a mount point by comparing device IDs
            try:
                path_stat = os.stat(path)
                parent_stat = os.stat(os.path.dirname(path))
                return path_stat.st_dev != parent_stat.st_dev
            except Exception:
                return True  # Assume mounted if we can't determine

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
                            if os.path.isdir(p) and not self._should_skip_path(p):
                                paths.append(p)

            # /media/* and /mnt/*
            for base in ["/media", "/mnt"]:
                if os.path.isdir(base):
                    for p in glob.glob(os.path.join(base, "*")):
                        if os.path.isdir(p) and not self._should_skip_path(p):
                            paths.append(p)
        except Exception:
            logging.exception("Error discovering hardware paths")

        # Filter out non-mounted paths and dedupe
        seen = set()
        out = []
        for p in paths:
            if p not in seen and self._is_mounted(p):
                seen.add(p)
                out.append(p)
        logging.debug("Discovered hardware paths: %s", out)
        return out

    def _run_locate(self, pattern: str, raw_mode: bool = False) -> List[str]:
        """Run plocate/locate and return lines (or empty list if not available)."""
        if not self.locate_cmd:
            logging.debug("No locate/plocate command available")
            return []

        if raw_mode:
            # Split pattern for raw mode to handle multiple args
            import shlex
            try:
                args = shlex.split(pattern)
                cmd = [self.locate_cmd] + args
            except Exception:
                cmd = [self.locate_cmd, pattern]
        else:
            # case-insensitive search of the pattern
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
        except subprocess.TimeoutExpired:
            logging.warning("locate timed out")
            return []
        except Exception as e:
            logging.exception("locate run failed: %s", e)
            return []

    def _run_find_on_path(self, path: str, pattern: str, timeout: int = None) -> List[str]:
        """Run 'find path -iname *pattern*' and return matches. Uses subprocess find when available."""
        if not os.path.isdir(path) or not os.access(path, os.R_OK):
            logging.debug("Path not readable or not a directory: %s", path)
            return []

        if timeout is None:
            timeout = self.find_timeout

        if self.find_cmd:
            # Use timeout command to prevent hanging on large drives
            cmd = ['timeout', str(timeout), self.find_cmd, path, "-iname", f"*{pattern}*"]
            logging.debug("Running find: %s", cmd)
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
                out = proc.stdout or ""
                if proc.stderr:
                    # Filter out common benign errors
                    stderr = proc.stderr.strip()
                    if "Permission denied" not in stderr:  # Skip common permission errors
                        logging.debug("find stderr (path=%s): %s", path, stderr)
                lines = [l for l in out.splitlines() if l.strip()]
                # Limit results to prevent overwhelming the system
                if len(lines) > self.max_find_results:
                    lines = lines[:self.max_find_results]
                    logging.debug("Limited find results to %d on path %s", self.max_find_results, path)
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
                            if len(matches) >= self.max_find_results:
                                logging.debug("Reached max results limit (%d) on %s", self.max_find_results, path)
                                break
                    if len(matches) >= self.max_find_results:
                        break
                logging.debug("os.walk found %d files in %s", len(matches), path)
            except Exception:
                logging.exception("os.walk failed on %s", path)
            return matches

    def _run_find(self, pattern: str) -> List[str]:
        """Run find across all discovered hardware paths and return combined results."""
        if not pattern.strip():
            return []

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

        mode, search_term, raw_mode = self._parse_pattern(pattern)
        
        if mode == 'hardware':
            if not search_term:
                return []
            logging.debug("Hardware-only search for: %s", search_term)
            find_results = self._run_find(search_term)
            return self._unique_preserve_order(find_results)

        if mode == 'raw':
            if not search_term:
                return []
            logging.debug("Raw locate search for: %s", search_term)
            return self._run_locate(search_term, raw_mode=True)

        # Combined mode
        if not search_term:
            return []

        locate_results = self._run_locate(search_term, raw_mode=False)
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
        print("Usage: python3 locator.py <query>")
        print("Examples:")
        print("  python3 locator.py project.docx          # Normal search")
        print("  python3 locator.py hw project.docx       # Hardware drives only")
        print("  python3 locator.py r -i .png            # Raw locate with regex")
        print(f"\nDebug log: {LOG_PATH}")
        sys.exit(0)
    res = loc.run(q)
    print(f"Found {len(res)} results (showing up to 200):")
    for i, r in enumerate(res[:200], 1):
        print(f"{i:03d}: {r}")
    if len(res) > 200:
        print(f"... and {len(res) - 200} more results")
    print(f"\nDebug log: {LOG_PATH}")
