import os
import subprocess
import logging
import sys

class Locator:
    def __init__(self):
        self.cmd = 'plocate' if self.__check_has_plocate() else 'locate'
        self.limit = 5

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

    def run(self, pattern):
        if not self.cmd:
            raise RuntimeError('Neither plocate nor locate commands found')
        if not pattern or not pattern.strip():
            raise RuntimeError('No search pattern provided')
        
        try:
            cmd = [self.cmd, '-i', '-l', str(self.limit)]
            args = pattern.split(' ')
            if args[0].lower() == 'r' and len(args) > 1:
                cmd.extend(args[1:])
            else:
                cmd.append(pattern)
            print(f'Executing command: {" ".join(cmd)}')
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            return [line for line in output.splitlines() if line.strip()]
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed with exit status {e.returncode}: {e.output}")
