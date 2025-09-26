import subprocess
import glob
import os


class Locator:
    def __init__(self):
        self.cmd = 'locate' if self.__check_has_locate() else None
        self.limit = 10
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
        # Dynamically detect mounted hardware paths under /run/media and /mnt
        search_dirs = []
        search_dirs.extend(glob.glob("/run/media/*/*"))  # e.g. /run/media/nour/UUID
        search_dirs.extend(glob.glob("/mnt/*"))

        results = []
        for path in search_dirs:
            if os.path.isdir(path):
                cmd = ["find", path, "-iname", f"*{pattern}*"]
                print('[Locator] Running find:', cmd)
                try:
                    output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
                    results.extend(output.decode().splitlines())
                except subprocess.CalledProcessError:
                    continue
        return results

    def run(self, pattern):
        if not pattern:
            return []

        locate_results = self.__run_locate(pattern)
        find_results = self.__run_find(pattern)

        combined = locate_results + find_results
        return combined[:self.limit]
