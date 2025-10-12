#!/usr/bin/env python3
"""Verifiziert, dass nur erlaubte Pfade geändert werden.
Nutzung: ALLOWED_GLOBS="routes/**,repositories/**,docs/**" python tools/patch_guard.py
"""
import os, sys, subprocess, fnmatch
allowed = [g.strip() for g in os.getenv('ALLOWED_GLOBS','').split(',') if g.strip()]
if not allowed:
    print('WARN: keine ALLOWED_GLOBS gesetzt – PatchGuard übersprungen'); sys.exit(0)
changed = subprocess.check_output(['git','diff','--name-only','--cached']).decode().splitlines()
viol = [p for p in changed if not any(fnmatch.fnmatch(p, g) for g in allowed)]
if viol:
    print('ERROR: Nicht erlaubte Änderungen:', *viol, sep='\n - ')
    sys.exit(1)
print('PatchGuard OK'); sys.exit(0)
