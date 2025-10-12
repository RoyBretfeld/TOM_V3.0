# TelefonAssistent 3.0 - Grundlegende Projektstruktur

## 📁 Verzeichnisstruktur

```
TelefonAssistent_3.0/
├── system/                 # System-Dokumentation
│   ├── CBS-STARD.md       # CSB Prompt-Template
│   └── Systemprompt Cursor-Start.md
├── data/
│   └── originals/         # Read-Only Originaldaten
├── src/                   # Hauptquellcode
├── tests/                 # Test-Suite
├── tools/                 # Hilfstools
│   ├── patch_guard.py     # Patch-Schutz
│   └── ci_slo_check.py    # SLO-Checks
├── scripts/
│   └── hooks/             # Pre-commit Hooks
│       ├── block_orig_writes.py
│       ├── deny_large_diff.py
│       └── scan_forbidden_patterns.py
├── .github/
│   ├── CODEOWNERS         # Reviewer-Pflichten
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/
│   └── workflows/         # CI/CD
│       ├── security.yml
│       └── ci.yml
└── docs/                  # Dokumentation
```

## 🛡️ CSB v1 Implementierung

### Sicherheitsfeatures:
- **Read-Only Schutz**: `./data/originals/**` ist unantastbar
- **Diff-Limits**: Max 30 Dateien oder 600 Zeilen pro Commit
- **UTF-8 Encoding**: Alle Schreiboperationen mit korrektem Encoding
- **Pre-commit Hooks**: Automatische Qualitätsprüfungen
- **SLO-Monitoring**: Accuracy ≥ 95%, Mojibake = 0, Fail-Rate < 2%

### Entwicklungsworkflow:
1. **Prompt-Template**: Verwende `system/CBS-STARD.md` für alle Cursor-Tasks
2. **Scope-Definition**: Nur explizit genannte Dateien ändern
3. **Test-Pflicht**: Mindestens 1 Test pro Änderung
4. **Akzeptanzkriterien**: Messbare Ziele definieren

## 🚀 Nächste Schritte

1. **Pre-commit installieren**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

2. **Umgebungsvariablen setzen**:
   ```bash
   cp env.example .env
   ```

3. **Erste Tests erstellen**:
   ```bash
   # Beispiel-Test in tests/test_basic.py
   ```

4. **Projekt-spezifische Konfiguration**:
   - `requirements.txt` für Python-Dependencies
   - `package.json` für Node.js-Dependencies (falls benötigt)
   - Spezifische Tests für TelefonAssistent-Funktionalität

## 📋 Checkliste für neue Features

- [ ] CSB-Header in Prompt eingefügt
- [ ] Scope eng definiert (konkrete Dateien/Pfade)
- [ ] Akzeptanzkriterien messbar formuliert
- [ ] Mindestens 1 Test vorgesehen
- [ ] Diff-Budget eingehalten (≤30 Files/≤600 Zeilen)
- [ ] SLOs genannt (95%/0/MOI OK)
- [ ] Keine Schreibpfade zu `./data/originals/**`
