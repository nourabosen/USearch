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
        print(f"Initialized Locator: cmd={self.cmd}, find_cmd={self.find_cmd}")

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
            # Check each base path
            for base in self.hardware_bases:
                if os.path.isdir(base):
                    print(f"Checking {base}")
                    try:
                        items = os.listdir(base)
                        for item in items:
                            full_path = os.path.join(base, item)
                            if os.path.isdir(full_path):
                                print(f"Found hardware path: {full_path}")
                                paths.append(full_path)
                    except PermissionError:
                        print(f"Permission denied accessing {base}")
                    except Exception as e:
                        print(f"Error reading {base}: {e}")
        except Exception as e:
            print(f"Error discovering hardware paths: {e}")

        # Also check /run/media/user/* structure
        try:
            run_media_base = "/run/media"
            if os.path.isdir(run_media_base):
                for user in os.listdir(run_media_base):
                    user_dir = os.path.join(run_media_base, user)
                    if os.path.isdir(user_dir):
                        for volume in os.listdir(user_dir):
                            volume_path = os.path.join(user_dir, volume)
                            if os.path.isdir(volume_path) and volume_path not in paths:
                                print(f"Found user-mounted path: {volume_path}")
                                paths.append(volume_path)
        except Exception as e:
            print(f"Error checking /run/media structure: {e}")

        print(f"Discovered {len(paths)} total hardware paths")
        return paths

    def _run_find(self, pattern: str) -> List[str]:
        """Run find on hardware-mounted drives - FIXED version."""
        paths = self._discover_hardware_paths()
        if not paths:
            print("No hardware paths found to search")
            return []
            
        if not self.find_cmd:
            print("No find command available")
            return []

        all_results = []
        print(f"Searching for pattern: '{pattern}' in {len(paths)} hardware paths")
        
        for path in paths:
            try:
                print(f"Searching in: {path}")
                
                # Test if we can actually read the directory
                if not os.access(path, os.R_OK):
                    print(f"Cannot read directory: {path}")
                    continue
                
                # Use simpler find command without -quit to get all matches
                # Use proper shell escaping for the pattern
                cmd = [self.find_cmd, path, "-type", "f", "-iname", f"*{pattern}*"]
                
                print(f"Running command: {' '.join(cmd)}")
                
                # Run with timeout to prevent hanging
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                    print(f"Found {len(lines)} results in {path}")
                    all_results.extend(lines)
                    
                    # Stop if we have enough results
                    if len(all_results) >= self.limit:
                        all_results = all_results[:self.limit]
                        print(f"Reached result limit of {self.limit}")
                        break
                else:
                    print(f"Find command failed in {path} (return code: {result.returncode})")
                    if result.stderr:
                        print(f"Error: {result.stderr.strip()}")
                    
            except subprocess.TimeoutExpired:
                print(f"Find timed out in {path}")
            except Exception as e:
                print(f"Error searching {path}: {e}")

        print(f"Total hardware results found: {len(all_results)}")
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
        print(f'Normal search for: "{search_pattern}"')
        
        locate_results = []
        hardware_results = []
        
        # Run locate search
        try:
            locate_cmd = [self.cmd, '-i', '-l', str(self.limit), search_pattern]
            print(f'Executing locate command: {" ".join(locate_cmd)}')
            
            locate_output = subprocess.check_output(locate_cmd, stderr=subprocess.STDOUT, text=True, timeout=5)
            locate_results = [line for line in locate_output.splitlines() if line.strip()]
            print(f"Locate found {len(locate_results)} results")
        except subprocess.CalledProcessError as e:
            print(f"Locate command failed: {e}")
        except subprocess.TimeoutExpired:
            print("Locate command timed out")
        except Exception as e:
            print(f"Locate error: {e}")

        # Run hardware search if we have a pattern and need more results
        if search_pattern.strip() and len(locate_results) < self.limit:
            hardware_results = self._run_find(search_pattern)
            print(f"Hardware search found {len(hardware_results)} results")
        else:
            print("Skipping hardware search - enough locate results or empty pattern")

        # Combine results - remove duplicates
        combined_results = locate_results.copy()
        for result in hardware_results:
            if result not in combined_results and len(combined_results) < self.limit:
                combined_results.append(result)

        print(f"Total combined results: {len(combined_results)}")
        return combined_results[:self.limit]


# Test function
def test_hardware_search():
    """Test hardware search directly"""
    print("=== Testing Hardware Search ===")
    locator = Locator()
    
    # Test path discovery
    paths = locator._discover_hardware_paths()
    print(f"Discovered paths: {paths}")
    
    # Test find command
    if paths:
        test_pattern = "test"  # Change this to a file you know exists on your drives
        results = locator._run_find(test_pattern)
        print(f"Test results for '{test_pattern}': {results}")
    else:
        print("No hardware paths found to test")

if __name__ == "__main__":
    # If run with "test" argument, run hardware search test
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_hardware_search()
    else:
        # Normal operation
        q = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
        loc = Locator()
        if not q:
            print("Usage: python3 locator.py <query>")
            print("       python3 locator.py test  (to test hardware search)")
            sys.exit(0)
        res = loc.run(q)
        print(f"Found {len(res)} results:")
        for i, r in enumerate(res, 1):
            print(f"{i:03d}: {r}")
