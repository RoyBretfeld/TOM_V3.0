#!/usr/bin/env python3
import sys, subprocess
RO = 'data/originals/'
paths = subprocess.check_output(['git','diff','--cached','--name-only']).decode().splitlines()
viol = [p for p in paths if p.startswith(RO)]
if viol:
    print('ERROR: Schreibzugriffe auf read-only Pfad erkannt:', *viol, sep='\n - ')
    sys.exit(1)
sys.exit(0)
