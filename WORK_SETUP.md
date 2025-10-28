# TOM v3.0 – Setup auf Arbeits-PC

**Ziel:** Projekt auf dem Arbeits-PC lauffähig machen, unabhängig von Privat-Setup.

---

## Voraussetzungen prüfen

### 1. Software-Anforderungen

**Minimal (nur Code-Entwicklung):**
- [ ] Python 3.10+ (`python --version`)
- [ ] Git (`git --version`)
- [ ] Visual Studio Code oder Cursor
- [ ] PowerShell 7+ (Windows) oder Bash (Linux)

**Optional (für Tests mit ML-Komponenten):**
- [ ] NVIDIA GPU mit CUDA 11.8+ (`nvidia-smi`)
- [ ] Node.js 18+ (für Dashboard) (`node --version`)
- [ ] Docker Desktop (für Container-Tests)
- [ ] Ollama (für LLM-Tests) (`ollama --version`)

### 2. Hardware-Check

```powershell
# Hardware-Inventar erstellen
python tools/host_inventory.py

# Ausgabe prüfen:
# - CPU: Kerne, Modell
# - RAM: Mindestens 16 GB empfohlen
# - GPU: Modell, VRAM (12+ GB für Realtime)
```

**Empfehlung:**
- **Nur Code-Entwicklung:** 8 GB RAM, CPU reicht
- **Mit Tests (ohne GPU):** 16 GB RAM, CPU
- **Mit ML-Tests:** 16 GB RAM, GPU mit 12+ GB VRAM

---

## Setup-Optionen

### Option A: Git Clone (Empfohlen)

**Voraussetzung:** GitHub/GitLab Repository ist eingerichtet

```powershell
# 1. Repository clonen
cd C:\Projekte  # oder anderer Pfad
git clone https://github.com/YOUR_USERNAME/TelefonAssistent_3.0.git
cd TelefonAssistent_3.0

# 2. Branch prüfen
git branch -a
git checkout master  # oder dev

# 3. Virtual Environment erstellen
python -m venv .venv
.venv\Scripts\Activate.ps1

# 4. Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Environment-Datei erstellen
copy env.work.example .env
# .env mit Editor öffnen und anpassen
```

### Option B: Import von G: (Cloud)

**Voraussetzung:** Zugriff auf Google Drive mit Projekt

```powershell
# 1. Von G: kopieren (ohne .venv, node_modules)
robocopy "G:\Meine Ablage\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0" ^
         "C:\Projekte\TelefonAssistent_3.0" ^
         /E /XD .venv node_modules __pycache__ .pytest_cache data\audio data\models\whisperx logs zip

# 2. Zum Projekt wechseln
cd C:\Projekte\TelefonAssistent_3.0

# 3. Virtual Environment erstellen
python -m venv .venv
.venv\Scripts\Activate.ps1

# 4. Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Git Remote einrichten (falls noch nicht vorhanden)
git remote -v
# Falls leer:
git remote add origin https://github.com/YOUR_USERNAME/TelefonAssistent_3.0.git
git fetch origin
git branch --set-upstream-to=origin/master master
```

### Option C: ZIP-Import (Offline)

**Voraussetzung:** ZIP-Archiv von G: oder E:

```powershell
# 1. ZIP entpacken
Expand-Archive -Path "TOM_v3.0_Complete.zip" -DestinationPath "C:\Projekte\TelefonAssistent_3.0"

# 2. Zum Projekt wechseln
cd C:\Projekte\TelefonAssistent_3.0

# 3. Virtual Environment erstellen
python -m venv .venv
.venv\Scripts\Activate.ps1

# 4. Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Git initialisieren (falls .git fehlt)
git init
git remote add origin https://github.com/YOUR_USERNAME/TelefonAssistent_3.0.git
git fetch origin
git reset --hard origin/master
```

---

## Konfiguration anpassen

### 1. Environment-Variablen (`.env`)

```bash
# Kopiere Template
cp env.work.example .env

# Öffne .env und passe an:
# - RECORD_PATH: Pfad für Audio-Aufnahmen (z.B. C:\Temp\tom_audio)
# - OLLAMA_URL: Falls Ollama läuft (http://localhost:11434)
# - CHROMA_URL: Falls ChromaDB läuft (http://localhost:8000)
# - ALLOW_EGRESS: false (keine externen API-Calls auf Arbeit)
```

**Wichtig:** `.env` enthält keine Secrets in Git. Jeder Standort hat eigene `.env`.

### 2. Pfade prüfen

```powershell
# Prüfe ob Pfade existieren
Test-Path "C:\Temp\tom_audio"  # Falls nicht: mkdir "C:\Temp\tom_audio"
```

---

## Tests durchführen

### Basis-Tests (ohne GPU/Dienste)

```powershell
# Unit-Tests (reine Logik)
pytest tests/unit -v

# Sollte grün sein, auch ohne GPU/Ollama
```

### Component-Tests (benötigen Hardware/Dienste)

```powershell
# Prüfe welche Dienste verfügbar sind
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
curl http://localhost:11434/api/tags  # Ollama

# Component-Tests (nur wenn Dienste laufen)
pytest tests/component -v

# Falls Dienste fehlen: Tests werden übersprungen (kein Fehler)
```

### Integration-Tests

```powershell
# Benötigt: Gateway, Redis, ChromaDB
pytest tests/integration -v
```

---

## Optionale Komponenten installieren

### Ollama (LLM lokal)

```powershell
# Download: https://ollama.ai/download
# Installation: ollama-windows-amd64.exe

# Modell herunterladen
ollama pull llama3:instruct

# Test
ollama run llama3:instruct "Hallo, wie geht es dir?"
```

### Piper TTS (lokal)

```powershell
# Download: https://github.com/rhasspy/piper/releases
# Entpacken nach: C:\Tools\piper\

# Modell herunterladen (bereits in Repo unter data/models/piper/)
# Test
C:\Tools\piper\piper.exe --model data/models/piper/de_DE-thorsten-medium.onnx --output_file test.wav
echo "Hallo Test" | C:\Tools\piper\piper.exe --model data/models/piper/de_DE-thorsten-medium.onnx --output_file test.wav
```

### WhisperX (GPU-beschleunigtes STT)

**Voraussetzung:** NVIDIA GPU mit CUDA

```powershell
# CUDA Toolkit installieren (falls nicht vorhanden)
# Download: https://developer.nvidia.com/cuda-downloads

# WhisperX installieren
pip install git+https://github.com/m-bain/whisperx.git

# Test
python -c "import whisperx; print('WhisperX OK')"
```

### Dashboard (React/Vite)

```powershell
# Node.js installieren (falls nicht vorhanden)
# Download: https://nodejs.org/

cd web/dashboard
npm install
npm run dev

# Browser: http://localhost:5173
```

---

## Git-Workflow auf Arbeit

### Täglicher Workflow

```powershell
# Morgens: Neueste Änderungen holen
git pull origin master

# Entwickeln...
# Dateien bearbeiten

# Änderungen committen
git add .
git commit -m "Beschreibung der Änderung"

# Abends: Hochladen
git push origin master
```

### Branch-Strategie (optional)

```powershell
# Feature-Branch erstellen
git checkout -b feature/neue-funktion

# Entwickeln und committen
git add .
git commit -m "Feature XYZ implementiert"

# Pushen
git push origin feature/neue-funktion

# Auf Privat-PC: Branch mergen
git checkout master
git merge feature/neue-funktion
git push origin master
```

---

## Troubleshooting

### Problem: Python nicht gefunden
**Lösung:**
```powershell
# Python PATH prüfen
$env:PATH -split ';' | Select-String python

# Falls leer: Python neu installieren und "Add to PATH" aktivieren
```

### Problem: CUDA nicht gefunden (GPU-Tests)
**Lösung:**
```powershell
# CUDA-Version prüfen
nvidia-smi

# CUDA Toolkit installieren (passend zur GPU-Driver-Version)
# Download: https://developer.nvidia.com/cuda-downloads
```

### Problem: Git Authentication fehlgeschlagen
**Lösung:**
```powershell
# Personal Access Token erstellen (GitHub)
# Settings -> Developer settings -> Personal access tokens

# Token verwenden statt Passwort
git config --global credential.helper store
git push origin master
# Username: YOUR_GITHUB_USERNAME
# Password: YOUR_PERSONAL_ACCESS_TOKEN
```

### Problem: Tests schlagen fehl
**Lösung:**
```powershell
# Nur Unit-Tests (ohne Hardware-Abhängigkeiten)
pytest tests/unit -v

# Detaillierte Ausgabe
pytest tests/unit -vv --tb=short

# Einzelnen Test
pytest tests/unit/test_dispatcher_fsm.py::test_state_transitions -v
```

### Problem: Import-Fehler nach git pull
**Lösung:**
```powershell
# Dependencies aktualisieren
pip install -r requirements.txt --upgrade
```

---

## Checkliste: Arbeit Setup abgeschlossen

- [ ] Python 3.10+ installiert
- [ ] Git installiert und konfiguriert
- [ ] Repository geclont oder importiert
- [ ] Virtual Environment erstellt (`.venv/`)
- [ ] Dependencies installiert (`requirements.txt`)
- [ ] `.env` Datei erstellt und angepasst
- [ ] Unit-Tests laufen grün (`pytest tests/unit -v`)
- [ ] Git Remote konfiguriert (`git remote -v`)
- [ ] Optional: Ollama installiert und Modell geladen
- [ ] Optional: Dashboard läuft (`npm run dev`)

---

## Nächste Schritte

1. **Code-Entwicklung:** Änderungen in `apps/`, `scripts/`, `tests/`
2. **Committen:** `git add . && git commit -m "..."`
3. **Pushen:** `git push origin master`
4. **Auf Privat-PC:** `git pull origin master`

Bei Fragen: Siehe `DEPLOYMENT_GUIDE.md` oder `README.md`

