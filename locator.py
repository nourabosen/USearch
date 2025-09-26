import os
import subprocess
import sys
import shutil

class Locator:
    def __init__(self, hardware_prefix="hw", raw_prefix="r"):
        self.cmd = 'plocate' if self.__check_has_plocate() else 'locate'
        self.find_cmd = shutil.which("find")
        self.limit = 5
        self.hardware_prefix = hardware_prefix
        self.raw_prefix = raw_prefix
        print(f"Initialized Locator: cmd={self.cmd}, find_cmd={self.find_cmd}")

    def set_prefixes(self, hardware_prefix, raw_prefix):
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

    def _get_mounted_drives(self):
        """Get mounted drives using mount command"""
        drives = []
        try:
            # Use mount command to find mounted filesystems
            result = subprocess.run(['mount'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                if '/dev/' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        mount_point = parts[2]
                        # Check if it's a hardware drive mount point
                        if any(mount_point.startswith(path) for path in ['/run/media/', '/media/', '/mnt/']):
                            if os.path.isdir(mount_point) and mount_point not in drives:
                                drives.append(mount_point)
                                print(f"Found mounted drive: {mount_point}")
        except Exception as e:
            print(f"Error getting mounted drives: {e}")
        
        # Also check the standard directories
        standard_paths = ['/run/media', '/media', '/mnt']
        for path in standard_paths:
            if os.path.isdir(path):
                try:
                    for item in os.listdir(path):
                        full_path = os.path.join(path, item)
                        if os.path.isdir(full_path) and full_path not in drives:
                            drives.append(full_path)
                            print(f"Found standard path: {full_path}")
                except Exception as e:
                    print(f"Error reading {path}: {e}")
        
        print(f"Total drives to search: {drives}")
        return drives

    def _search_with_find(self, pattern, search_path):
        """Search using find command in a specific path"""
        try:
            # Simple find command: find /path -name "*pattern*" (case insensitive)
            cmd = [self.find_cmd, search_path, '-name', f'*{pattern}*', '-type', 'f']
            print(f"Running find: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                print(f"Found {len(files)} files in {search_path}")
                return files
            else:
                print(f"Find failed: {result.stderr}")
                return []
        except subprocess.TimeoutExpired:
            print(f"Find timed out for {search_path}")
            return []
        except Exception as e:
            print(f"Error with find in {search_path}: {e}")
            return []

    def _search_hardware_drives(self, pattern):
        """Search all hardware drives for the pattern"""
        if not self.find_cmd:
            print("No find command available")
            return []
            
        drives = self._get_mounted_drives()
        if not drives:
            print("No hardware drives found")
            return []
        
        all_results = []
        for drive in drives:
            print(f"Searching drive: {drive}")
            results = self._search_with_find(pattern, drive)
            all_results.extend(results)
            
            # Stop if we have enough results
            if len(all_results) >= self.limit:
                all_results = all_results[:self.limit]
                break
        
        print(f"Hardware search found {len(all_results)} results")
        return all_results

    def run(self, pattern):
        if not self.cmd:
            raise RuntimeError('Neither plocate nor locate commands found')
        if not pattern or not pattern.strip():
            raise RuntimeError('No search pattern provided')
        
        tokens = pattern.strip().split()
        print(f"Search pattern: '{pattern}'")
        
        # Hardware-only mode
        if tokens and tokens[0].lower() == self.hardware_prefix.lower() and len(tokens) > 1:
            search_pattern = ' '.join(tokens[1:])
            print(f"HARDWARE-ONLY SEARCH: '{search_pattern}'")
            return self._search_hardware_drives(search_pattern)
        
        # Raw mode
        if tokens and tokens[0].lower() == self.raw_prefix.lower() and len(tokens) > 1:
            raw_args = tokens[1:]
            cmd = [self.cmd] + raw_args
            print(f'RAW SEARCH: {" ".join(cmd)}')
            try:
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
                return [line for line in output.splitlines() if line.strip()]
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Command failed: {e.output}")
        
        # Normal mode - locate only (for now, to test)
        search_pattern = pattern
        print(f'NORMAL SEARCH: "{search_pattern}"')
        
        try:
            cmd = [self.cmd, '-i', '-l', str(self.limit), search_pattern]
            print(f'Locate command: {" ".join(cmd)}')
            
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=5)
            results = [line for line in output.splitlines() if line.strip()]
            print(f"Locate found {len(results)} results")
            return results
        except subprocess.CalledProcessError as e:
            print(f"Locate failed: {e}")
            return []
        except Exception as e:
            print(f"Search error: {e}")
            return []


# Test the hardware search
if __name__ == "__main__":
    # Test hardware search specifically
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("=== TESTING HARDWARE SEARCH ===")
        locator = Locator()
        
        # Test 1: List mounted drives
        print("\n1. Listing mounted drives:")
        drives = locator._get_mounted_drives()
        print(f"Found {len(drives)} drives: {drives}")
        
        # Test 2: Search for a test pattern
        if drives:
            test_pattern = "test" if len(sys.argv) <= 2 else sys.argv[2]
            print(f"\n2. Searching for '{test_pattern}':")
            results = locator._search_hardware_drives(test_pattern)
            print(f"Found {len(results)} results: {results}")
        else:
            print("No drives found to test with")
            
    else:
        # Normal operation
        q = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
        loc = Locator()
        if not q:
            print("Usage: python3 locator.py <query>")
            print("       python3 locator.py test [pattern]  (test hardware search)")
            sys.exit(0)
        res = loc.run(q)
        print(f"Found {len(res)} results:")
        for i, r in enumerate(res, 1):
            print(f"{i}: {r}")
