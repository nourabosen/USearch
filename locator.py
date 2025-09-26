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
        print(f"=== LOCATOR INITIALIZED ===")
        print(f"Locate command: {self.cmd}")
        print(f"Find command: {self.find_cmd}")
        print(f"Limit: {self.limit}")

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

    def _run_find(self, pattern: str, search_folders: bool = False) -> List[str]:
        """Run find on hardware-mounted drives."""
        paths = self._discover_hardware_paths()
        if not paths:
            print("No hardware paths found")
            return []
            
        if not self.find_cmd:
            print("No find command available")
            return []

        all_results = []
        print(f"=== FIND SEARCH ===")
        print(f"Pattern: '{pattern}'")
        print(f"Search folders: {search_folders}")
        
        for path in paths:
            try:
                print(f"Searching in: {path}")
                
                # Build find command
                cmd = [self.find_cmd, path, "-maxdepth", "3"]
                
                if search_folders:
                    cmd.extend(["-type", "d", "-iname", f"*{pattern}*"])
                    print(f"Folder search command: {' '.join(cmd)}")
                else:
                    cmd.extend(["-type", "f", "-iname", f"*{pattern}*"])
                    print(f"File search command: {' '.join(cmd)}")
                
                # Run find command
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                print(f"Find return code: {result.returncode}")
                
                if result.returncode == 0:
                    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                    print(f"Found {len(lines)} results in {path}")
                    
                    for line in lines[:3]:  # Show first 3 results for debugging
                        print(f"  Result: {line}")
                    if len(lines) > 3:
                        print(f"  ... and {len(lines) - 3} more")
                        
                    all_results.extend(lines)
                    
                    if len(all_results) >= self.limit:
                        all_results = all_results[:self.limit]
                        break
                else:
                    print(f"Find stderr: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print(f"Find timed out in {path}")
            except Exception as e:
                print(f"Error searching {path}: {e}")

        print(f"Total hardware results: {len(all_results)}")
        return all_results

    def _run_locate(self, pattern: str, search_folders: bool = False) -> List[str]:
        """Run locate command."""
        cmd = [self.cmd, '-i', '-l', '50', pattern]  # Get more results for filtering
        
        print(f"=== LOCATE SEARCH ===")
        print(f"Command: {' '.join(cmd)}")
        print(f"Search folders: {search_folders}")
        
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=5)
            results = [line for line in output.splitlines() if line.strip()]
            print(f"Locate found {len(results)} raw results")
            
            if search_folders:
                # Filter to only include directories
                folder_results = []
                for result in results:
                    if os.path.isdir(result):
                        folder_results.append(result)
                        print(f"  Found folder: {result}")
                    if len(folder_results) >= self.limit:
                        break
                print(f"Filtered to {len(folder_results)} folders")
                return folder_results[:self.limit]
            else:
                print(f"Returning {min(len(results), self.limit)} files")
                return results[:self.limit]
                
        except subprocess.CalledProcessError as e:
            print(f"Locate command failed: {e.output}")
            return []
        except subprocess.TimeoutExpired:
            print("Locate command timed out")
            return []

    def run(self, pattern):
        if not self.cmd:
            raise RuntimeError('Neither plocate nor locate commands found')
        if not pattern or not pattern.strip():
            raise RuntimeError('No search pattern provided')
        
        print(f"\n{'='*50}")
        print(f"STARTING SEARCH: '{pattern}'")
        print(f"{'='*50}")
        
        # Parse search mode
        original_pattern = pattern
        search_folders = False
        hardware_only = False
        raw_mode = False
        
        tokens = pattern.strip().split()
        
        # Check for raw mode first
        if tokens and tokens[0].lower() == 'r':
            raw_mode = True
            pattern = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            print(f"RAW MODE: {pattern}")
        
        # Check for hardware folder mode
        elif len(tokens) >= 2 and tokens[0].lower() == 'hw' and tokens[1].lower() == 'folder':
            hardware_only = True
            search_folders = True
            pattern = ' '.join(tokens[2:]) if len(tokens) > 2 else ""
            print(f"HARDWARE FOLDER MODE: {pattern}")
        
        # Check for hardware mode
        elif tokens and tokens[0].lower() == 'hw':
            hardware_only = True
            pattern = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            print(f"HARDWARE MODE: {pattern}")
        
        # Check for folder mode
        elif tokens and tokens[0].lower() == 'folder':
            search_folders = True
            pattern = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            print(f"FOLDER MODE: {pattern}")
        
        else:
            print(f"STANDARD MODE: {pattern}")
        
        if not pattern.strip():
            raise RuntimeError('No search pattern provided after mode prefix')
        
        # Raw mode
        if raw_mode:
            cmd = [self.cmd] + pattern.split()
            print(f"Executing raw command: {' '.join(cmd)}")
            try:
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
                results = [line for line in output.splitlines() if line.strip()]
                print(f"Raw search returned {len(results)} results")
                return results
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Command failed with exit status {e.returncode}: {e.output}")
        
        # Hardware-only search
        elif hardware_only:
            results = self._run_find(pattern, search_folders)
            print(f"Hardware search returned {len(results)} results")
            return results
        
        # Combined search (locate + hardware)
        else:
            locate_results = self._run_locate(pattern, search_folders)
            hardware_results = self._run_find(pattern, search_folders)
            
            # Combine results - remove duplicates
            combined_results = locate_results.copy()
            for result in hardware_results:
                if result not in combined_results and len(combined_results) < self.limit:
                    combined_results.append(result)
            
            print(f"Combined search returned {len(combined_results)} results")
            return combined_results[:self.limit]
