import subprocess
import os

class Locator:
    def __init__(self):
        self.cmd = 'plocate' if self.__check_has_plocate() else 'locate'
        self.limit = 8

    def set_limit(self, limit):
        try:
            new_limit = int(limit)
            if new_limit > 0:
                self.limit = new_limit
        except Exception:
            self.limit = 8

    def __check_has_plocate(self):
        try:
            subprocess.check_call(['which', 'plocate'],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def run(self, pattern):
        """
        Normal search: plocate/locate
        Special case: if pattern starts with 'hw ', run find on /run/media
        """
        if not pattern or not pattern.strip():
            raise RuntimeError("No search pattern provided")

        args = pattern.strip().split()

        # Hardware search mode
        if args[0].lower() == 'hw' and len(args) > 1:
            search_term = " ".join(args[1:])
            try:
                cmd = ['find', '/run/media', '-iname', f'*{search_term}*']
                output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
                return [line for line in output.splitlines() if line.strip()]
            except subprocess.CalledProcessError:
                return []
        
        # Default: use plocate/locate
        cmd = [self.cmd, '-i']
        if args[0].lower() == 'r' and len(args) > 1:
            cmd.extend(args[1:])
        else:
            cmd.append(pattern)

        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            return [line for line in output.splitlines() if line.strip()]
        except subprocess.CalledProcessError as e:
            out = getattr(e, 'output', '')
            if out:
                return [line for line in out.splitlines() if line.strip()]
            raise RuntimeError(f"Command failed with exit status {e.returncode}: {out}")
