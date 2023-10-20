from collections import namedtuple
import datetime
import os
from pwd import getpwuid
import re
import subprocess
import string
import tempfile
import stat

MAX_FILE_SIZE = 1024 * 1024 * 64 # 64 MB
PREVIEW_SIZE = 400
SwapContent = namedtuple('SwapContent', ['filename', 'size', 'owner', 'last_modify', 'preview'])

class VimSwapFileFinder:
    def __init__(self):
        self.last_check = datetime.datetime.now() - datetime.timedelta(hours=1)

    def update_time(self):
        self.last_check = datetime.datetime.now()

    def recover_swap_file(self, filename: string):
        """
        Recover a swap file specified by `filename` and return full file contents.
        It should be guranteed the file size is not too big to recover.
        """
        if not re.match(r'^[~\ +\-\_A-Za-z0-9\/\.]*$', filename):
            print("Bad file name")
            return None

        try:
            scriptfile = tempfile.NamedTemporaryFile(mode='w+')
            capturefile = tempfile.NamedTemporaryFile(mode='w+')
            scriptfile.write(f":w! {capturefile.name}\n:q!\n")
            scriptfile.flush()

        except:
            print(f"Cannot capture swap file {filename}: tempfile cannot be created", flush=True)

        finally:
            try:
                vim = subprocess.Popen([f'vim', '-r', filename, '-s', scriptfile.name])
                vim.wait(10)

                if vim.returncode == 0:
                    content = capturefile.read()
                    print(f"vim recovered. Swap file {filename}", flush=True)
                else:
                    print(f"vim recover failed. Maybe the file is not valid or the script is not working. Swap file {filename}", flush=True)
                    content = None

            except subprocess.TimeoutExpired:
                print(f"vim session timeout. Maybe the file is too large or the script is not working. Swap file {filename}", flush=True)
                content = None

            scriptfile.close()
            capturefile.close()

        return content
    
    def scan_directory(self, dir: string):
        """
        Scan a given dir for newly created swap file.
        `dir` should not end with '/'.
        Return a list of SwapContent.
        """
        recovered_list = []
        with os.scandir(dir) as dir_entries:
            for entry in dir_entries:
                if not entry.stat().st_mode & (1 << 5):
                    continue
                
                # detect only file
                if not entry.is_file():
                    continue
                
                # detect valid file name
                filename = entry.name
                if not re.match(r"^.*\.sw.$", filename):
                    continue

                # detect size <= MAX_FILE_SIZE
                if entry.stat().st_size > MAX_FILE_SIZE:
                    print(f"File {filename} is too big, skipping.")

                last_modify = datetime.datetime.fromtimestamp(entry.stat().st_mtime)
                if last_modify < self.last_check:
                    continue

                # recover swap file
                fullname = dir + '/' + filename
                owner = getpwuid(entry.stat().st_uid).pw_name
                content = self.recover_swap_file(fullname)
                if content != None:
                    recovered_list.append(SwapContent(filename=fullname, size=entry.stat().st_size, owner=owner, last_modify=last_modify, preview=content[:PREVIEW_SIZE]))

        return recovered_list

if __name__ == '__main__':
    sf = VimSwapFileFinder()
    input()
    print(sf.scan_directory('/tmp'))