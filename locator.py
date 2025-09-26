class Locator:
    def __init__(self):
        self.cmd = 'plocate' if self.__check_has_plocate() else 'locate'
        self.find_cmd = shutil.which("find")
        self.limit = 5
        self.hardware_bases = ["/run/media", "/media", "/mnt"]
        # New: customizable prefixes
        self.hardware_prefix = "hw"
        self.raw_prefix = "r"
        print(f"Initialized Locator: cmd={self.cmd}, find_cmd={self.find_cmd}, hw_prefix={self.hardware_prefix}, raw_prefix={self.raw_prefix}")

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

    # New setters
    def set_hardware_prefix(self, prefix: str):
        if prefix and prefix.strip():
            self.hardware_prefix = prefix.strip()
        print(f"Set hardware prefix to '{self.hardware_prefix}'")

    def set_raw_prefix(self, prefix: str):
        if prefix and prefix.strip():
            self.raw_prefix = prefix.strip()
        print(f"Set raw prefix to '{self.raw_prefix}'")

    def run(self, pattern):
        if not self.cmd:
            raise RuntimeError('Neither plocate nor locate commands found')
        if not pattern or not pattern.strip():
            raise RuntimeError('No search pattern provided')
        
        tokens = pattern.strip().split()
        print(f"Search pattern: '{pattern}', tokens: {tokens}")
        
        # Hardware-only mode
        if tokens[0].lower() == self.hardware_prefix.lower() and len(tokens) > 1:
            search_pattern = ' '.join(tokens[1:])
            print(f"Hardware-only search for: '{search_pattern}'")
            return self._run_find(search_pattern)
        
        # Raw mode
        if tokens[0].lower() == self.raw_prefix.lower() and len(tokens) > 1:
            raw_args = tokens[1:]
            cmd = [self.cmd] + raw_args
            print(f'Executing raw command: {" ".join(cmd)}')
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
        except subprocess.TimeoutExpired:
            print("Locate command timed out")

        hardware_results = []
        if search_pattern.strip():
            hardware_results = self._run_find(search_pattern)
            print(f"Hardware search found {len(hardware_results)} results")

        combined_results = locate_results.copy()
        for result in hardware_results:
            if result not in combined_results and len(combined_results) < self.limit:
                combined_results.append(result)

        print(f"Total combined results: {len(combined_results)}")
        return combined_results[:self.limit]
