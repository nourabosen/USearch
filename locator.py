import subprocess


class Locator:
    def __init__(self):
        self.cmd = 'locate' if self.__check_has_locate() else None
        self.limit = 10   # total results (split between locate + find)
        self.opt = ''

    def set_limit(self, limit):
        print('set limit to ' + str(limit))
        self.limit = int(limit)

    def set_locate_opt(self, opt):
        print('set locate opt to ' + opt)
        self.opt = opt

    def __check_has_locate(self):
        try:
            subprocess.check_call(['which', 'locate'],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            return True
        except:
            return False

    def __run_locate(self, pattern):
        if not self.cmd:
            return []
        cmd = [self.cmd, '-l', str(self.limit)]
        args = pattern.split(' ')
        if args[0] == 'r':
            cmd.extend(args[1:])
        else:
            cmd.append(self.opt)
            cmd.extend(args)
        print('[Locator] Running locate:', cmd)
        try:
            output = subprocess.check_output(cmd)
            return output.decode().splitlines()
        except subprocess.CalledProcessError:
            return []

    def __run_find(self, pattern):
        # Search hardware-mounted drives
        search_dirs = ["/run/media", "/mnt"]
        cmd = ["find"] + search_dirs + ["-iname", f"*{pattern}*"]
        print('[Locator] Running find:', cmd)
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            return output.decode().splitlines()
        except subprocess.CalledProcessError:
            return []

    def run(self, pattern):
        if not pattern:
            return []

        # Run both searches
        locate_results = self.__run_locate(pattern)
        find_results = self.__run_find(pattern)

        # Merge & respect global limit
        combined = locate_results + find_results
        return combined[:self.limit]
