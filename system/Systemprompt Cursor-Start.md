# CSB v1 – Cursor‑Safety Baseline (orgweit)

**Systemprompt + Starterpaket** für alle Cursor‑gestützten Projekte. Entscheidungen:

* **Org‑weit** via `.github`‑Default‑Repo
* **CI:** GitHub Actions
* **Technologie:** **Polyglott** (Python + JS/TS)
* **Read‑Only Eingangsverzeichnis:** `./data/originals/**`
* **Grenzen:** Diff ≤ **30 Dateien** oder **600 Zeilen**; SLOs übernehmen (Accuracy ≥ 95 %, Mojibake = 0, Fail‑Rate < 2 %)

---

## 1) System‑Prompt (immer oben einfügen)

```
[SYSTEM • CSB v1 — Cursor‑Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF‑8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ‑ONLY INPUTS: Alles unter ./data/originals/** ist unantastbar (keine Schreib/Move/Rename‑Operationen).
2) ENCODING: Alle Schreib/Export/Log‑Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt **namentlich** genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF‑LIMIT: Max 30 Dateien **oder** 600 geänderte Zeilen. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + knappe Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake‑Marker = 0, Original‑Integrität OK. Bei Verstoß: Änderung abbrechen.
7) LOGGING: Ruhig, UTF‑8‑safe; keine Debug‑Flut.
8) SECURITY: Keine Secrets im Repo. Pre‑commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre‑commit ok · ci_slo_check ok (falls vorhanden) · tests ok · **no writes** to ./data/originals/**
[END SYSTEM]
```

---

## 2) Org‑weites `.github`‑Default‑Repo (Standard für alle Repos)

### 2.1 CODEOWNERS

`/.github/CODEOWNERS`

```txt
# Reviewer‑Pflicht für sensible Pfade
/data/originals/**    @maintainers
ingest/reader.py      @maintainers
tools/orig_integrity.py @maintainers
repositories/**       @maintainers
routes/**             @maintainers
```

> `@maintainers` auf eure Teams/Accounts anpassen.

### 2.2 Pull‑Request‑Template

`/.github/PULL_REQUEST_TEMPLATE.md`

```md
## Was wurde geändert?
- …

## Checks (CSB v1)
- [ ] ./data/originals/** unangetastet (read‑only)
- [ ] Alle Writes/Exports UTF‑8 (encoding="utf-8")
- [ ] Tests hinzugefügt/aktualisiert + Akzeptanzkriterien notiert
- [ ] (falls vorhanden) tools/ci_slo_check.py grün
- [ ] SLOs eingehalten (Accuracy ≥ 95 %, Mojibake = 0, Fail‑Rate < 2 %)

## Scope (Dateiliste)
- Erlaubte Dateien in diesem PR: …
```

### 2.3 Issue‑Template (optional)

`/.github/ISSUE_TEMPLATE/guardrails.md`

```md
---
name: Guardrails Request
about: Änderung an Leitplanken (CSB v1)
---
**Was soll geändert werden?**
**Begründung / Risikoabwägung**
**Betroffene Repos**
```

---

## 3) GitHub Actions – Workflows (polyglott)

### 3.1 Security‑Baseline (Warnstufe, später auf „blocking“ schaltbar)

`/.github/workflows/security.yml`

```yaml
name: security-baseline
on: [push, pull_request]
jobs:
  sec:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: Install Python tooling
        run: pip install -q pre-commit bandit pip-audit || true
      - name: pre-commit (quick)
        run: pre-commit run --all-files || true
      - name: bandit (py security)
        run: bandit -q -r . || true
      - name: pip-audit (deps CVE)
        run: pip-audit -f json || true
      - name: Node available?
        id: node
        run: echo "has_node=$([ -f package.json ] && echo true || echo false)" >> $GITHUB_OUTPUT
      - if: steps.node.outputs.has_node == 'true'
        name: Setup Node
        uses: actions/setup-node@v4
        with: { node-version: '20' }
      - if: steps.node.outputs.has_node == 'true'
        name: npm audit (prod)
        run: npm audit --omit=dev || true
```

> „|| true“ = Warnungen. Für „blocking“ einfach entfernen.

### 3.2 CI – Tests & SLOs

`/.github/workflows/ci.yml`

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      CSB_MAX_FILES: 30
      CSB_MAX_LINES: 600
      SLO_OK_RATE: 0.95
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: Setup Node (optional)
        uses: actions/setup-node@v4
        with: { node-version: '20' }
      - name: Install Python deps (if exists)
        run: |
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install pytest
      - name: Install JS deps (if exists)
        run: |
          if [ -f package.json ]; then npm ci; fi
      - name: Pre-commit (blocking)
        run: |
          pip install pre-commit
          pre-commit run --all-files
      - name: PatchGuard (optional)
        run: |
          if [ -f tools/patch_guard.py ]; then python tools/patch_guard.py; fi
      - name: SLO-Check (optional)
        run: |
          if [ -f tools/ci_slo_check.py ]; then python tools/ci_slo_check.py; fi
      - name: Python Tests (if tests present)
        run: |
          if compgen -G "tests/**/*.py" > /dev/null; then pytest -q; else echo "No Python tests"; fi
      - name: ESLint (if configured)
        run: |
          if [ -f package.json ] && npx --yes eslint -v >/dev/null 2>&1; then npx --yes eslint .; else echo "No ESLint"; fi
```

---

## 4) Pre‑commit – Hooks & Diff‑Limits (polyglott‑freundlich)

`/.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: check-merge-conflict
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: detect-private-key
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: |
          (?x)^(
            node_modules/|
            dist/|
            build/
          )
  - repo: local
    hooks:
      - id: block-orig-writes
        name: Block writes in ./data/originals
        entry: python scripts/hooks/block_orig_writes.py
        language: system
        stages: [commit]
      - id: scan-forbidden-write-patterns
        name: Scan for forbidden write patterns to ./data/originals
        entry: python scripts/hooks/scan_forbidden_patterns.py
        language: system
        stages: [commit]
      - id: deny-large-diff
        name: Deny large diff
        entry: python scripts/hooks/deny_large_diff.py
        language: system
        stages: [commit]
```

> Optional weitere Formatter (black/isort/eslint) können projektspezifisch ergänzt werden.

`.secrets.baseline` kann initial leer committet werden und später via `detect-secrets scan` aktualisiert werden.

---

## 5) Hook‑Skripte (repo‑lokal)

`scripts/hooks/deny_large_diff.py`

```python
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
```

`scripts/hooks/block_orig_writes.py`

```python
#!/usr/bin/env python3
import sys, subprocess
RO = 'data/originals/'
paths = subprocess.check_output(['git','diff','--cached','--name-only']).decode().splitlines()
viol = [p for p in paths if p.startswith(RO)]
if viol:
    print('ERROR: Schreibzugriffe auf read-only Pfad erkannt:', *viol, sep='\n - ')
    sys.exit(1)
sys.exit(0)
```

`scripts/hooks/scan_forbidden_patterns.py`

```python
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
```

`tools/patch_guard.py`

```python
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
```

---

## 6) UTF‑8 Runtime Defaults

`.env.example`

```env
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
```

---

## 7) Mini‑README (Roll‑out in 3 Schritten)

`README.CSB.md`

```md
# CSB v1 – Roll-out
1) Org‑weites `.github`‑Repo anlegen/aktualisieren – Dateien aus CSB v1 übernehmen.
2) In jedem Projekt:
   - `pip install pre-commit && pre-commit install`
   - `.env` aus `.env.example` ableiten (UTF‑8)
   - Optional: `tools/patch_guard.py` nutzen (CI‑Step), z. B. `ALLOWED_GLOBS="routes/**,repositories/**" python tools/patch_guard.py`
3) In PR‑Reviews auf CSB‑Checkliste bestehen (Template).
```

---

## 8) Akzeptanzkriterien

* **System‑Prompt** vorhanden und in Prompts referenzierbar.
* **Org‑weites .github** mit CODEOWNERS + PR‑Template + Workflows aktiv.
* **Pre‑commit** mit RO‑Schutz und Diff‑Limit verhindert Wildwuchs.
* **CI** führt Security‑Baseline, pre‑commit, SLO‑Check (falls vorhanden) und Tests aus.
* **UTF‑8** Defaults gesetzt.
* **Polyglott**: Python + JS/TS werden berücksichtigt.

## Output

* Dieses Dokument ist die Blaupause. Inhalte 1:1 in eure Repos kopieren bzw. ins `.github`‑Org‑Repo übernehmen.
