#!/usr/bin/env python3
import re, sys, subprocess
PATTERNS = [r'open\(\s*[\"\']data/originals/', r'write_text\(.*data/originals/', r'to_csv\(.*data/originals']
text = subprocess.check_output(['git','diff','--cached']).decode(errors='ignore')
viol = [p for p in PATTERNS if re.search(p, text)]
if viol:
    print('ERROR: Verdächtige Schreibmuster Richtung data/originals gefunden:')
    for v in viol: print(' -', v)
    sys.exit(1)
sys.exit(0)
