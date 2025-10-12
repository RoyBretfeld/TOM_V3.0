# TelefonAssistent 3.0

Ein intelligenter Telefonassistent mit professioneller Entwicklungsinfrastruktur.

## 🚀 Schnellstart

```bash
# Repository klonen
git clone <repository-url>
cd TelefonAssistent_3.0

# Entwicklungsumgebung einrichten
pip install pre-commit
pre-commit install

# Umgebungsvariablen setzen
cp .env.example .env

# Dependencies installieren (falls vorhanden)
pip install -r requirements.txt
```

## 📁 Projektstruktur

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
├── scripts/               # Automatisierungsskripte
└── docs/                  # Dokumentation
```

## 🛡️ CSB v1 - Cursor-Safety Baseline

Dieses Projekt folgt der CSB v1 (Cursor-Safety Baseline) für sichere Entwicklung:

- **UTF-8 Encoding**: Alle Schreiboperationen mit `encoding="utf-8"`
- **Read-Only Schutz**: `./data/originals/**` ist unantastbar
- **Diff-Limits**: Max 30 Dateien oder 600 Zeilen pro Commit
- **SLOs**: Accuracy ≥ 95%, Mojibake = 0, Fail-Rate < 2%
- **Tests**: Mindestens 1 Test pro Änderung

## 🔧 Entwicklung

### Pre-commit Hooks
```bash
pre-commit run --all-files
```

### Tests ausführen
```bash
pytest
```

### CSB-Checks
```bash
python tools/ci_slo_check.py
```

## 📋 Akzeptanzkriterien

- [ ] Alle Tests bestehen
- [ ] Pre-commit Hooks erfolgreich
- [ ] UTF-8 Encoding korrekt gesetzt
- [ ] Keine Schreibzugriffe auf `./data/originals/**`
- [ ] SLOs eingehalten

## 🤝 Contributing

Bitte folge den CSB v1 Leitplanken und verwende das Prompt-Template aus `system/CBS-STARD.md`.
