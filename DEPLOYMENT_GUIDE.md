# TOM v3.0 – Multi-Standort Deployment Guide

## Übersicht: Wo liegt was?

### G:\ (Google Drive Cloud) – **Haupt-Repository & Backup**
**Zweck:** Zentrale Versionsverwaltung, automatisches Backup, Zugriff von überall

**Was MUSS hier sein:**
- Kompletter Source Code (`apps/`, `scripts/`, `tests/`, `web/`, `src/`)
- Git Repository (`.git/`)
- Dokumentation (`docs/`, `*.md`)
- Konfigurationen (`*.yaml`, `*.json`, `.env.example`, `env.sample`)
- Requirements (`requirements.txt`, `requirements-dev.txt`)
- Infra-Definitionen (`infra/`, `Dockerfile.*`, `docker-compose.*`)

**Was NICHT hier sein sollte:**
- `.venv/` – Virtual Environment (standortspezifisch)
- `infra/venv/` – Build-Umgebung für Container (lokal regenerierbar)
- `node_modules/`, `web/dashboard/node_modules/` – Node Dependencies (standortspezifisch)
- `data/audio/` – Audio-Aufnahmen (zu groß, lokal)
- `data/models/` – ML-Modelle (WhisperX, Piper, Ollama etc.)
- `__pycache__/`, `.pytest_cache/`, `tests/__pycache__/` – Cache (temporär)
- `logs/` – Log-Dateien (lokal)
- `MagicMock/` – Debug-/Spielwiese, nicht für Cloud nötig
- `zip/` – Archive (temporär, lokal erzeugen)

---

### E:\ (Lokales Laufwerk Privat) – **Entwicklung & Performance**
**Zweck:** Schnelle Entwicklung, große Dateien, GPU-Tests

**Was hier liegen sollte:**
- Komplette Entwicklungsumgebung (Kopie von G:)
- `.venv/` – Virtual Environment mit allen Dependencies
- `infra/venv/` – Container-Build-Umgebung (falls lokal gebaut wird)
- `data/models/whisperx/`, `data/models/piper/`, `data/models/ollama/` – Modelle
- `data/audio/` – Test-Audioaufnahmen
- `logs/` – Entwicklungs-Logs
- `node_modules/` – Wenn Dashboard entwickelt wird

**Sync-Strategie:**
- Code-Änderungen: `git commit` + `git push` → automatisch auf G: via Cloud-Sync
- Große Dateien: Bleiben auf E:, werden nicht gesynct
- Bei Bedarf: Manuelles Kopieren von E: → G: für Backup

---

### Arbeits-PC – **Produktive Entwicklung**
**Zweck:** Entwicklung im Büro, möglicherweise andere Hardware

**Setup:** Siehe `WORK_SETUP.md`

**Was hier liegt:**
- Git-Clone von GitHub/GitLab (oder Import von G:)
- Eigene `.venv/` mit Dependencies
- Standortspezifische `.env` Konfiguration
- Optional: Lokale Modelle (falls GPU vorhanden)

---

## Sync-Workflow zwischen Standorten

### Szenario 1: Privat (E:) → Cloud (G:) → Arbeit

```bash
# Auf E: (Privat)
git add .
git commit -m "Feature XYZ implementiert"
git push origin master

# Cloud-Sync (automatisch)
# G: erhält automatisch die Änderungen via Google Drive Sync

# Auf Arbeit
git pull origin master
```

### Szenario 2: Arbeit → Cloud (G:) → Privat (E:)

```bash
# Auf Arbeit
git add .
git commit -m "Bugfix ABC"
git push origin master

# Auf E: (Privat) oder G: (Cloud)
git pull origin master
```

### Szenario 3: Nur Dokumentation (ohne Git)

```bash
# Auf G: (Cloud) - Datei bearbeiten
# Automatischer Sync zu allen verbundenen Geräten
# Auf E: oder Arbeit: Einfach neu öffnen
```

---

## Best Practices

### 1. Git als Single Source of Truth
- Alle Code-Änderungen über Git committen
- Niemals direkt Dateien zwischen E: und G: kopieren (außer bei Setup)
- Branch-Strategie: `master` für stabile Version, `dev` für Entwicklung

### 2. Standortspezifische Konfiguration
- Jeder Standort hat eigene `.env` Datei (nicht in Git)
- Templates: `.env.example`, `env.sample`, `env.work.example`
- Pfade in `.env` anpassen (z.B. `RECORD_PATH`)

### 3. Große Dateien
- Modelle: Lokal herunterladen, nicht über Git/Cloud
- Audio: Nur auf E: speichern, auf Arbeit Mock-Daten verwenden
- Logs: Lokal, nicht committen

### 4. Virtual Environments
- Jeder Standort hat eigene `.venv/`
- Nach `git pull`: Immer `pip install -r requirements.txt` prüfen
- Bei neuen Dependencies: `requirements.txt` updaten und committen

### 5. Node Modules (Dashboard)
- Nur installieren, wenn Dashboard entwickelt wird
- Nach `git pull`: `npm install` im `web/dashboard/` Ordner
- Nicht committen (bereits in `.gitignore`)

---

## Troubleshooting

### Problem: "Module not found" nach git pull
**Lösung:**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Problem: Tests schlagen fehl auf Arbeit (keine GPU)
**Lösung:**
```bash
# Nur Unit-Tests laufen lassen
pytest tests/unit -v

# Component-Tests überspringen (benötigen GPU)
pytest tests/unit tests/integration -v
```

### Problem: Konflikte zwischen E: und G:
**Lösung:**
```bash
# Auf E: (oder G:)
git status
git stash  # Lokale Änderungen sichern
git pull origin master
git stash pop  # Änderungen wieder anwenden
```

### Problem: Cloud-Sync dauert zu lange
**Lösung:**
- Google Drive Desktop App: Selektives Sync aktivieren
- Nur `___TelefonAssistent_3.0/` syncen
- Große Ordner (`data/models/`) vom Sync ausschließen

---

## Checkliste: Neuer Standort Setup

- [ ] Git Repository clonen oder von G: kopieren
- [ ] Virtual Environment erstellen (`python -m venv .venv`)
- [ ] Dependencies installieren (`pip install -r requirements.txt`)
- [ ] `.env` Datei erstellen (von `.env.example` kopieren)
- [ ] Pfade in `.env` anpassen
- [ ] Git Remote prüfen (`git remote -v`)
- [ ] Test: `pytest tests/unit -v`
- [ ] Optional: Modelle herunterladen (Ollama, Piper, WhisperX)
- [ ] Optional: Node Modules installieren (`cd web/dashboard && npm install`)

---

## Weitere Dokumentation

- **`WORK_SETUP.md`** – Detaillierte Anleitung für Arbeits-PC Setup
- **`SETUP_AFTER_CLOUD_SYNC.md`** – Setup nach Kopieren auf G:
- **`README.md`** – Projekt-Übersicht
- **`docs/PROJECT_SETUP.md`** – Technische Setup-Details

