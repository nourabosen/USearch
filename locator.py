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
        # Prefer plocate, fall back to locate
        self.locate_cmd = shutil.which("plocate") or shutil.which("locate")
        self.find_cmd = shutil.which("find")
        self.limit = None  # Pagination handled by main.py

        logging.debug("Locator init; locate_cmd=%s find_cmd=%s", self.locate_cmd, self.find_cmd)

    def set_limit(self, limit):
        try:
            self.limit = int(limit)
            logging.debug("set_limit -> %s", self.limit)
        except Exception:
            logging.exception("set_limit: invalid value: %s", limit)
            self.limit = None

    def _escape_glob_for_find(self, pattern: str) -> str:
        """Escape glob metacharacters so pattern is treated literally in -iname."""
        for char in r'[]?*{}!':
            pattern = pattern.replace(char, '\\' + char)
        return pattern

    def _discover_hardware_paths(self) -> List[str]:
        """Discover active mount points under /run/media, /media, and /mnt."""
        paths = []
        try:
            # Handle /run/media/<user>/<volume>
            run_media = "/run/media"
            if os.path.isdir(run_media):
                for user in os.listdir(run_media):
                    user_path = os.path.join(run_media, user)
                    if os.path.isdir(user_path):
                        try:
                            for vol in os.listdir(user_path):
                                full_path = os.path.join(user_path, vol)
                                if os.path.isdir(full_path):
                                    paths.append(full_path)
                        except (PermissionError, OSError):
                            logging.warning("Permission or access error: %s", user_path)

            # Handle /media/* and /mnt/*
            for base in ["/media", "/mnt"]:
                if os.path.isdir(base):
                    try:
                        for entry in os.listdir(base):
                            full_path = os.path.join(base, entry)
                            if os.path.isdir(full_path):
                                paths.append(full_path)
                    except (PermissionError, OSError):
                        logging.warning("Permission or access error: %s", base)

            # Explicit fallback for current user (e.g., /run/media/nour)
            try:
                current_user = os.getlogin()
                explicit_path = f"/run/media/{current_user}"
                if os.path.isdir(explicit_path):
                    for vol in os.listdir(explicit_path):
                        p = os.path.join(explicit_path, vol)
                        if os.path.isdir(p) and p not in paths:
                            paths.append(p)
            except Exception:
                pass  # os.getlogin() may fail in some environments

        except Exception:
            logging.exception("Error during hardware path discovery")

        # Deduplicate while preserving order
        seen = set()
        out = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                out.append(p)
        logging.debug("Final discovered hardware paths: %s", out)
        return out

    def _run_locate(self, tokens: List[str], raw_mode: bool = False) -> List[str]:
        if not self.locate_cmd:
            logging.debug("No locate/plocate command available")
            return []

        if raw_mode:
            cmd = [self.locate_cmd] + tokens
        else:
            pattern = " ".join(tokens)
            cmd = [self.locate_cmd, "-i", pattern]

        logging.debug("Running locate: %s", cmd)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            out = proc.stdout or ""
            if proc.stderr:
                logging.debug("locate stderr: %s", proc.stderr.strip())
            lines = [l for l in out.splitlines() if l.strip()]
            logging.debug("locate returned %d lines", len(lines))
            return lines
        except Exception as e:
            logging.exception("locate run failed: %s", e)
            return []

    def _run_find_on_path(self, path: str, pattern: str, timeout: int = 20) -> List[str]:
        if not os.path.isdir(path) or not pattern.strip():
            return []

        # Escape glob characters to avoid syntax errors in -iname
        safe_pattern = pattern
        for char in r'[]?*{}!':
            safe_pattern = safe_pattern.replace(char, '\\' + char)

        if self.find_cmd:
            cmd = [self.find_cmd, path, "-iname", f"*{safe_pattern}*"]
            logging.debug("Running find: %s", cmd)
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                # find returns:
                #   0 = OK (matches or not)
                #   1 = No matches → NOT an error!
                #   >1 = Real error
                if proc.returncode > 1:
                    logging.error("find failed (code %d) on %s: %s", proc.returncode, path, proc.stderr.strip())
                    return []
                out = proc.stdout or ""
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                logging.debug("find(%s) returned %d results", path, len(lines))
                return lines
            except subprocess.TimeoutExpired:
                logging.warning("find timed out on %s", path)
                return []
            except Exception as e:
                logging.exception("Unexpected error in find on %s: %s", path, e)
                return []
        else:
            # Fallback to os.walk
            logging.debug("Using os.walk fallback on %s", path)
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
        if not pattern or not pattern.strip():
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
        logging.debug("run called with pattern: %r", pattern)
        if not pattern or not pattern.strip():
            logging.debug("Empty pattern -> returning []")
            return []

        tokens = pattern.strip().split()

        # Hardware-only mode
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            search_term = " ".join(tokens[1:])
            logging.debug("Hardware-only search for: %s", search_term)
            find_results = self._run_find(search_term)
            return self._unique_preserve_order(find_results)

        # Raw locate mode
        raw_mode = (tokens[0].lower() == "r" and len(tokens) > 1)
        if raw_mode:
            locate_tokens = tokens[1:]
        else:
            locate_tokens = tokens

        # Run locate
        locate_results = self._run_locate(locate_tokens, raw_mode=raw_mode)

        # Run find on hardware mounts
        search_term = " ".join(locate_tokens)
        find_results = self._run_find(search_term) if search_term.strip() else []

        # Merge and deduplicate (locate first, then find)
        combined = locate_results + find_results
        combined = self._unique_preserve_order(combined)
        logging.debug("Combined result count: %d", len(combined))
        return combined


# Quick manual test
if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
    loc = Locator()
    if not q:
        print("Usage: python3 locator.py <query>")
        print("Examples:")
        print("  python3 locator.py 'project.docx'        # hybrid search")
        print("  python3 locator.py 'hw summer.jpg'       # hardware only")
        print("  python3 locator.py 'r -S .png'           # raw locate")
        print(f"Debug log: {LOG_PATH}")
        sys.exit(0)
    res = loc.run(q)
    print(f"Found {len(res)} results (showing up to 200):")
    for i, r in enumerate(res[:200], 1):
        print(f"{i:03d}: {r}")
    print(f"\nDebug log: {LOG_PATH}")
