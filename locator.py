"""
locator.py — concurrent hybrid locator for Ulauncher fork

- Runs plocate/locate (fast, indexed) and find on hardware mounts concurrently.
- Detects mounts via /proc/mounts (looks for mountpoints under /run/media, /media, /mnt).
- Modes:
    * "hw <term>" : hardware-only find
    * "r <args...>" : raw locate args passed to locate/plocate
    * otherwise : run locate AND find, merge results
- Writes debug to /tmp/ul_locator_debug.log
- Returns combined list (no slicing). main.py should paginate.
"""
from __future__ import annotations
import shutil
import subprocess
import os
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

LOG_PATH = "/tmp/ul_locator_debug.log"
logging.basicConfig(filename=LOG_PATH,
                    level=logging.DEBUG,
                    format="%(asctime)s %(levelname)s: %(message)s")


class Locator:
    def __init__(self):
        self.locate_cmd = shutil.which("plocate") or shutil.which("locate")
        self.find_cmd = shutil.which("find")
        self.limit = None  # do not enforce here
        self.locate_timeout = 4    # seconds for locate
        self.find_timeout = 20     # per mount find timeout
        # recognized mount prefixes
        self._mount_prefixes = ("/run/media", "/media", "/mnt")
        logging.debug("Locator initialized; locate_cmd=%s find_cmd=%s", self.locate_cmd, self.find_cmd)

    def set_limit(self, limit):
        try:
            self.limit = int(limit)
            logging.debug("set_limit -> %s", self.limit)
        except Exception:
            logging.exception("invalid limit: %s", limit)
            self.limit = None

    def set_locate_opt(self, opt):
        # kept for backward compatibility; not used by default flow
        self._locate_opt = opt
        logging.debug("set_locate_opt -> %s", opt)

    def _discover_hardware_mounts(self) -> List[str]:
        mounts = []
        try:
            with open("/proc/mounts", "r") as fh:
                for line in fh:
                    parts = line.split()
                    if len(parts) >= 2:
                        mpoint = parts[1]
                        # include mountpoints under the prefixes
                        if any(mpoint.startswith(pref + "/") or mpoint == pref for pref in self._mount_prefixes):
                            if os.path.isdir(mpoint):
                                mounts.append(mpoint)
        except Exception:
            logging.exception("failed reading /proc/mounts, falling back to globbing")

        # fallback: check common dirs if none found
        if not mounts:
            for pref in self._mount_prefixes:
                if os.path.isdir(pref):
                    for entry in os.listdir(pref):
                        p = os.path.join(pref, entry)
                        if os.path.isdir(p):
                            mounts.append(p)

        # dedupe preserve order
        seen = set()
        out = []
        for p in mounts:
            if p not in seen:
                seen.add(p)
                out.append(p)
        logging.debug("Discovered hardware mounts: %s", out)
        return out

    def _run_locate(self, tokens: List[str], raw_mode: bool = False) -> List[str]:
        if not self.locate_cmd:
            logging.debug("No locate/plocate found on PATH")
            return []

        if raw_mode:
            cmd = [self.locate_cmd] + tokens
        else:
            pattern = " ".join(tokens)
            cmd = [self.locate_cmd, "-i", pattern]

        logging.debug("Running locate command: %s", cmd)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.locate_timeout)
            out = proc.stdout or ""
            if proc.stderr:
                logging.debug("locate stderr: %s", proc.stderr.strip())
            lines = [l for l in out.splitlines() if l.strip()]
            logging.debug("locate found %d results", len(lines))
            return lines
        except subprocess.TimeoutExpired:
            logging.warning("locate timed out for cmd: %s", cmd)
            return []
        except Exception:
            logging.exception("locate failed for cmd: %s", cmd)
            return []

    def _run_find_on_mount(self, mount: str, pattern: str) -> List[str]:
        if not os.path.isdir(mount):
            return []
        if not self.find_cmd:
            logging.debug("find command not found; skipping find on %s", mount)
            return []

        # Use -iname for case-insensitive substring search
        cmd = [self.find_cmd, mount, "-iname", f"*{pattern}*"]
        logging.debug("Running find: %s", cmd)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.find_timeout)
            out = proc.stdout or ""
            if proc.stderr:
                logging.debug("find stderr for %s: %s", mount, proc.stderr.strip())
            lines = [l for l in out.splitlines() if l.strip()]
            logging.debug("find on %s returned %d", mount, len(lines))
            return lines
        except subprocess.TimeoutExpired:
            logging.warning("find timed out on %s", mount)
            return []
        except Exception:
            logging.exception("find failed on %s", mount)
            return []

    def _run_find_all_mounts(self, pattern: str) -> List[str]:
        mounts = self._discover_hardware_mounts()
        if not mounts:
            logging.debug("No hardware mounts found to search")
            return []

        results = []
        # run finds concurrently for speed
        with ThreadPoolExecutor(max_workers=min(6, max(1, len(mounts)))) as ex:
            futures = {ex.submit(self._run_find_on_mount, m, pattern): m for m in mounts}
            for fut in as_completed(futures):
                mount = futures[fut]
                try:
                    res = fut.result()
                    if res:
                        results.extend(res)
                except Exception:
                    logging.exception("Error for mount %s", mount)
        logging.debug("Total find results across mounts: %d", len(results))
        return results

    @staticmethod
    def _unique_preserve_order(items: List[str]) -> List[str]:
        seen = set()
        out = []
        for it in items:
            if it not in seen:
                seen.add(it)
                out.append(it)
        return out

    def run(self, pattern: str) -> List[str]:
        logging.debug("run called with pattern: %r", pattern)
        if not pattern or not pattern.strip():
            return []

        tokens = pattern.strip().split()
        # hardware-only mode
        if tokens[0].lower() == "hw" and len(tokens) > 1:
            search_term = " ".join(tokens[1:])
            logging.debug("Performing hardware-only search for: %s", search_term)
            find_results = self._run_find_all_mounts(search_term)
            return self._unique_preserve_order(find_results)

        # raw locate mode 'r <args...>'
        raw_mode = tokens[0].lower() == "r" and len(tokens) > 1
        locate_tokens = tokens[1:] if raw_mode else tokens
        search_term = " ".join(locate_tokens).strip()

        # run both locate and find concurrently
        with ThreadPoolExecutor(max_workers=2) as ex:
            future_locate = ex.submit(self._run_locate, locate_tokens, raw_mode)
            future_find = ex.submit(self._run_find_all_mounts, search_term) if search_term else None

            locate_results = future_locate.result()
            find_results = future_find.result() if future_find else []

        combined = self._unique_preserve_order(locate_results + find_results)
        logging.debug("Combined results count: %d", len(combined))
        return combined


# CLI test helper
if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]).strip()
    print("Debug log:", LOG_PATH)
    loc = Locator()
    print("locate_cmd:", loc.locate_cmd, "find_cmd:", loc.find_cmd)
    print("discovered mounts:", loc._discover_hardware_mounts())
    if not q:
        print("Usage: python3 locator.py <query>")
        print("Examples:")
        print("  python3 locator.py myfile")
        print("  python3 locator.py 'hw myfile'   # hardware only")
        print("  python3 locator.py 'r -S .png'   # raw locate args")
        sys.exit(0)
    res = loc.run(q)
    print(f"Found {len(res)} results (showing up to 500):")
    for i, r in enumerate(res[:500], 1):
        print(f"{i:03d}: {r}")
    print("\nTail debug log for details:")
    print("  tail -n 200 /tmp/ul_locator_debug.log")
