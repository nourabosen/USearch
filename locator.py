"""
Hybrid locator for the Ulauncher extension:
- Uses plocate/locate for fast indexed search.
- Also runs a live `find` on typical mounted media (/run/media) to include external drives.
- Merges results, de-duplicates while preserving order (plocate results first).
"""

import subprocess
import shutil
import os

class Locator:
    def __init__(self):
        # prefer plocate when available
        self.cmd = 'plocate' if shutil.which('plocate') else ('locate' if shutil.which('locate') else None)
        self.limit = 8  # per-page limit used by extension UI (not a hard limit of returned results)
        # mount roots to search live (can extend later)
        self.hardware_paths = ['/run/media', '/media', '/mnt']

    def set_limit(self, limit):
        try:
            new_limit = int(limit)
            if new_limit > 0:
                self.limit = new_limit
        except Exception:
            self.limit = 8

    def _run_plocate(self, pattern_tokens, raw_mode=False):
        """
        Run plocate/locate and return list of lines.
        If raw_mode is True, pattern_tokens is a list of tokens treated as raw arguments.
        Otherwise, join tokens back to a single pattern argument.
        """
        if not self.cmd:
            return []

        if raw_mode:
            # pass tokens as-is (useful when user typed r <opts> ...)
            cmd = [self.cmd] + pattern_tokens
        else:
            # normal: case-insensitive search for the whole pattern
            cmd = [self.cmd, '-i', ' '.join(pattern_tokens)]

        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            return [line for line in output.splitlines() if line.strip()]
        except subprocess.CalledProcessError as e:
            # if command returned non-zero but has output, still return it
            out = getattr(e, 'output', '') or ''
            return [line for line in out.splitlines() if line.strip()]

    def _run_find_on_paths(self, search_term, search_paths):
        """
        Run find on provided paths and return matches.
        We use -iname '*term*' for case-insensitive substring match.
        If the search_term contains shell metacharacters we still treat it as literal substring search.
        """
        matches = []
        if not search_term:
            return matches

        # Build find command for each path separately to avoid permission issues halting everything
        for root in search_paths:
            if not os.path.exists(root):
                continue
            # Run find: files and directories; use -iname for case-insensitive and wrap with wildcards
            # Limit follow symlinks? We won't follow by default.
            try:
                cmd = ['find', root, '-iname', f'*{search_term}*']
                # hide stderr (permission denied messages) to keep output clean
                output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
                for line in output.splitlines():
                    if line.strip():
                        matches.append(line.strip())
            except subprocess.CalledProcessError:
                # find returned non-zero (likely no matches) => ignore
                continue
            except Exception:
                # ignore unexpected find errors for robustness
                continue
        return matches

    def _unique_preserve_order(self, items):
        seen = set()
        out = []
        for it in items:
            if it not in seen:
                seen.add(it)
                out.append(it)
        return out

    def run(self, pattern):
        """
        Main API:
        - Accepts a pattern string the user typed (e.g. 'myfile.txt' or 'r -S foo' or 'hw foo')
        - Returns a list of absolute paths (strings). No truncation is applied here.
        Behavior:
        - If the pattern starts with 'hw ' (case-insensitive), run only a live find on hardware paths.
        - Else:
            * Run plocate/locate (fast indexed) for the pattern (supports 'r' raw prefix for passing args).
            * Also run find on hardware paths to discover items not in the locate DB.
            * Merge results (plocate results first), de-duplicate.
        """
        if not pattern or not pattern.strip():
            raise RuntimeError('No search pattern provided')

        tokens = pattern.strip().split()
        if not tokens:
            raise RuntimeError('No search pattern provided')

        # hardware-only mode: "hw <pattern...>"
        if tokens[0].lower() == 'hw' and len(tokens) > 1:
            search_term = ' '.join(tokens[1:])
            find_results = self._run_find_on_paths(search_term, self.hardware_paths)
            return self._unique_preserve_order(find_results)

        # determine raw mode for plocate: e.g., "r <opts...>"
        raw_mode = (tokens[0].lower() == 'r' and len(tokens) > 1)
        plocate_tokens = tokens[1:] if raw_mode else tokens

        # run plocate/locate for fast results
        plocate_results = self._run_plocate(plocate_tokens, raw_mode=raw_mode)

        # run find on hardware paths to include external drives (slower)
        # pick a reasonable search term: join tokens if not raw mode.
        find_term = ' '.join(plocate_tokens) if plocate_tokens else ''
        find_results = []
        # only attempt find when there are hardware paths
        if find_term:
            find_results = self._run_find_on_paths(find_term, self.hardware_paths)

        # merge preserving plocate results first, then appended hardware ones, de-duplicate
        combined = plocate_results + find_results
        combined = self._unique_preserve_order(combined)

        return combined
