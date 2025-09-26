import os
import subprocess
import logging
import sys
import shutil
import glob
from typing import List

class Locator:
    def __init__(self):
        self.cmd = 'plocate' if self.__check_has_plocate() else 'locate'
        self.find_cmd = shutil.which("find")
        self.limit = 5
        self.hardware_bases = ["/run/media", "/media", "/mnt"]

    def set_limit(self, limit):
        try:
            new_limit = int(limit)
            if new_limit > 0:
                self.limit = new_limit
            else:
                self.limit = 5  # Default to 5 if invalid
            print(('set limit to ' + str(self.limit)))
        except ValueError:
            self.limit = 5  # Default to 5 if not a number
            print(('Invalid limit value, setting to default: ' + str(self.limit)))

    def __check_has_plocate(self):
        try:
            subprocess.check_call(['which', 'plocate'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

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
        except Exception as e:
            print(f"Error discovering hardware paths: {e}")

        # dedupe preserve order
        seen = set()
        out = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                out.append(p)
        print(f"Discovered hardware paths: {out}")
        return out

    def _run_find(self, pattern: str) -> List[str]:
        """Run find on hardware-mounted drives."""
        paths = self._discover_hardware_paths()
        if not paths or not self.find_cmd:
            return []

        all_results = []
        for path in paths:
            try:
                cmd = [self.find_cmd, path, "-iname", f"*{pattern}*", "-print", "-quit"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.stdout:
                    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                    all_results.extend(lines)
            except Exception as e:
                print(f"Find failed on {path}: {e}")

        return all_results[:self.limit]  # Apply limit

    def run(self, pattern):
        if not self.cmd:
            raise RuntimeError('Neither plocate nor locate commands found')
        if not pattern or not pattern.strip():
            raise RuntimeError('No search pattern provided')
        
        tokens = pattern.strip().split()
        
        # Hardware-only mode: "hw <pattern>"
        if tokens[0].lower() == 'hw' and len(tokens) > 1:
            search_pattern = ' '.join(tokens[1:])
            print(f"Hardware-only search for: {search_pattern}")
            return self._run_find(search_pattern)
        
        # Raw mode: "r <args>"
        if tokens[0].lower() == 'r' and len(tokens) > 1:
            raw_args = tokens[1:]
            cmd = [self.cmd] + raw_args
            print(f'Executing raw command: {" ".join(cmd)}')
        else:
            # Normal mode: combined search
            search_pattern = pattern
            cmd = [self.cmd, '-i', '-l', str(self.limit), search_pattern]
            print(f'Executing command: {" ".join(cmd)}')
            
            # Run locate first
            try:
                locate_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
                locate_results = [line for line in locate_output.splitlines() if line.strip()]
            except subprocess.CalledProcessError as e:
                locate_results = []
                print(f"Locate command failed: {e}")

            # If we have fewer than limit results, try hardware search
            if len(locate_results) < self.limit:
                hardware_results = self._run_find(search_pattern)
                # Combine and deduplicate
                combined = locate_results + [r for r in hardware_results if r not in locate_results]
                return combined[:self.limit]  # Ensure we don't exceed limit
            else:
                return locate_results

        # For raw mode or fallback
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            return [line for line in output.splitlines() if line.strip()]
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed with exit status {e.returncode}: {e.output}")
