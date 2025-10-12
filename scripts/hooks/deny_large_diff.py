#!/usr/bin/env python3
import subprocess, sys, os
MAX_FILES = int(os.getenv('CSB_MAX_FILES', '30'))
MAX_LINES = int(os.getenv('CSB_MAX_LINES', '600'))

def main():
    out = subprocess.check_output(['git','diff','--cached','--numstat']).decode()
    files = 0; lines = 0
    for line in out.splitlines():
        parts = line.split('\t')
        if len(parts) < 3: continue
        add, dele, path = parts
        if path.startswith('data/originals/'):
            print('ERROR: Änderungen in data/originals/ sind verboten')
            return 1
        files += 1
        try:
            lines += int(add) + int(dele)
        except ValueError:
            pass
    if files > MAX_FILES or lines > MAX_LINES:
        print(f'ERROR: Diff zu groß (files={files} lines={lines}) – bitte in kleinere Commits schneiden.')
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
