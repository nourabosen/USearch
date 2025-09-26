import os
import subprocess
import logging
import sys
import shutil
import glob
from typing import List

class Locator:
    def __init__(self, hardware_prefix="hw", raw_prefix="r"):
        self.cmd = 'plocate' if self.__check_has_plocate() else 'locate'
        self.find_cmd = shutil.which("find")
        self.limit = 5
        self.hardware_bases = ["/run/media", "/media", "/mnt"]
        self.hardware_prefix = hardware_prefix
        self.raw_prefix = raw_prefix
        print(f"Initialized Locator: cmd={self.cmd}, find_cmd={self.find_cmd}, hardware_prefix='{hardware_prefix}', raw_prefix='{raw_prefix}'")

    def set_prefixes(self, hardware_prefix, raw_prefix):
        """Update search prefixes from preferences"""
        self.hardware_prefix = hardware_prefix
        self.raw_prefix = raw_prefix
        print(f"Updated prefixes: hardware='{hardware_prefix}', raw='{raw_prefix}'")

    def set_limit(self, limit):
        try:
            new_limit = int(limit)
            if new_limit > 0:
                self.limit = new_limit
            else:
                self.limit = 5
            print(f'set limit to {self.limit}')
        except ValueError:
            self.limit = 5
            print(f'Invalid limit value, setting to default: {self.limit}')

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
                print(f"Checking {base}")
                for user in os.listdir(base):
                    userdir = os.path.join(base, user)
                    if os.path.isdir(userdir):
                        for vol in os.listdir(userdir):
                            p = os.path.join(userdir, vol)
                            if os.path.isdir(p):
                                print(f"Found hardware path: {p}")
                                paths.append(p)

            # /media/* and /mnt/*
            for base in ["/media", "/mnt"]:
                if os.path.isdir(base):
                    print(f"Checking {base}")
                    for item in os.listdir(base):
                        p = os.path.join(base, item)
                        if os.path.isdir(p):
                            print(f"Found hardware path: {p}")
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
        print(f"Discovered {len(out)} hardware paths: {out}")
        return out

    def _run_find(self, pattern: str) -> List[str]:
        """Run find on hardware-mounted drives - optimized version."""
        paths = self._discover_hardware_paths()
        if not paths:
            print("No hardware paths found")
            return []
            
        if not self.find_cmd:
            print("No find command available")
            return []

        all_results = []
        print(f"Searching for pattern: '{pattern}' in hardware paths")
        
        for path in paths:
            try:
                print(f"Searching in: {path}")
                # Use -maxdepth 3 to avoid deep recursion and speed up search
                # Use -type f to only search files, not directories
                cmd = [self.find_cmd, path, "-maxdepth", "3", "-type", "f", "-iname", f"*{pattern}*"]
                
                # Run with timeout to prevent hanging
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                    print(f"Found {len(lines)} results in {path}")
                    all_results.extend(lines)
                    
                    # Stop if we have enough results
                    if len(all_results) >= self.limit:
                        all_results = all_results[:self.limit]
                        break
                else:
                    print(f"Find failed in {path}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print(f"Find timed out in {path}")
            except Exception as e:
                print(f"Error searching {path}: {e}")

        print(f"Total hardware results: {len(all_results)}")
        return all_results

    def run(self, pattern):
        if not self.cmd:
            raise RuntimeError('Neither plocate nor locate commands found')
        if not pattern or not pattern.strip():
            raise RuntimeError('No search pattern provided')
        
        tokens = pattern.strip().split()
        print(f"Search pattern: '{pattern}', tokens: {tokens}")
        
        # Hardware-only mode: "<hardware_prefix> <pattern>"
        if tokens and tokens[0].lower() == self.hardware_prefix.lower() and len(tokens) > 1:
            search_pattern = ' '.join(tokens[1:])
            print(f"Hardware-only search for: '{search_pattern}' (prefix: '{self.hardware_prefix}')")
            return self._run_find(search_pattern)
        
        # Raw mode: "<raw_prefix> <args>"
        if tokens and tokens[0].lower() == self.raw_prefix.lower() and len(tokens) > 1:
            raw_args = tokens[1:]
            cmd = [self.cmd] + raw_args
            print(f'Executing raw command: {" ".join(cmd)} (prefix: "{self.raw_prefix}")')
            try:
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
                return [line for line in output.splitlines() if line.strip()]
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Command failed with exit status {e.returncode}: {e.output}")
        
        # Normal mode: combined search
        search_pattern = pattern
        locate_cmd = [self.cmd, '-i', '-l', str(self.limit), search_pattern]
        print(f'Executing locate command: {" ".join(locate_cmd)}')
        
        locate_results = []
        try:
            locate_output = subprocess.check_output(locate_cmd, stderr=subprocess.STDOUT, text=True, timeout=5)
            locate_results = [line for line in locate_output.splitlines() if line.strip()]
            print(f"Locate found {len(locate_results)} results")
        except subprocess.CalledProcessError as e:
            print(f"Locate command failed: {e}")
            locate_results = []
        except subprocess.TimeoutExpired:
            print("Locate command timed out")
            locate_results = []

        # Always run hardware search but only if we have a pattern
        hardware_results = []
        if search_pattern.strip():
            hardware_results = self._run_find(search_pattern)
            print(f"Hardware search found {len(hardware_results)} results")

        # Combine results - remove duplicates
        combined_results = locate_results.copy()
        for result in hardware_results:
            if result not in combined_results and len(combined_results) < self.limit:
                combined_results.append(result)

        print(f"Total combined results: {len(combined_results)}")
        return combined_results[:self.limit]
