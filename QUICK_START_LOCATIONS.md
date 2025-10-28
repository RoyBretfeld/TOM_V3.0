# TOM v3.0 – Quick Start nach Standort

Schnellübersicht: Was muss ich wo tun?

---

## 🏠 Privat (E:\ Laufwerk)

**Zweck:** Hauptentwicklung, große Modelle, GPU-Tests

### Erste Schritte
```powershell
cd E:\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0
.venv\Scripts\Activate.ps1
```

### Täglicher Workflow
```powershell
# Änderungen von anderen Standorten holen
git pull origin master

# Entwickeln...

# Committen und pushen
git add .
git commit -m "Beschreibung"
git push origin master
```

### Was hier liegt
- Kompletter Code + `.venv/`
- Große Modelle (`data/models/whisperx/`)
- Audio-Aufnahmen (`data/audio/`)
- Logs

---

## ☁️ Cloud (G:\ Google Drive)

**Zweck:** Automatisches Backup, Zugriff von überall

### Erste Schritte
```powershell
cd "G:\Meine Ablage\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0"

# Virtual Environment erstellen (falls noch nicht vorhanden)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Was hier liegt
- Kompletter Code (automatisch gesynct von E:)
- Git Repository
- Dokumentation
- KEINE großen Dateien (.venv, node_modules, Modelle)

### Wichtig
- Nicht direkt entwickeln (langsamer Sync)
- Nur für Backup und Zugriff von anderen Geräten
- Bei Änderungen: Auf E: entwickeln, dann automatisch gesynct

---

## 💼 Arbeit (C:\ oder Netzlaufwerk)

**Zweck:** Entwicklung im Büro

### Erste Schritte (einmalig)
Siehe **`WORK_SETUP.md`** für vollständige Anleitung

```powershell
# Option A: Git Clone
git clone https://github.com/YOUR_USERNAME/TelefonAssistent_3.0.git
cd TelefonAssistent_3.0

# Option B: Von G: kopieren
robocopy "G:\Meine Ablage\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0" ^
         "C:\Projekte\TelefonAssistent_3.0" ^
         /E /XD .venv node_modules __pycache__ data\audio data\models\whisperx

# Virtual Environment erstellen
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Environment-Datei erstellen
copy env.work.example .env
# .env mit Editor öffnen und anpassen
```

### Täglicher Workflow
```powershell
# Morgens: Neueste Änderungen holen
git pull origin master

# Entwickeln...

# Abends: Hochladen
git add .
git commit -m "Beschreibung"
git push origin master
```

### Was hier liegt
- Code (Git-Clone)
- Eigene `.venv/`
- Standortspezifische `.env`
- Optional: Lokale Modelle (falls GPU vorhanden)

---

## 🔄 Sync-Strategie

### E: ↔ G: (automatisch)
- Google Drive Desktop App synct automatisch
- Keine manuelle Aktion nötig
- Ausnahmen: `.venv`, `node_modules`, große Dateien (bereits in `.gitignore`)

### E: ↔ Arbeit (via Git)
```powershell
# Auf E:
git push origin master

# Auf Arbeit
git pull origin master
```

### G: ↔ Arbeit (via Git)
```powershell
# Auf G: (falls direkt entwickelt)
git push origin master

# Auf Arbeit
git pull origin master
```

---

## 📋 Checkliste: Standort-Wechsel

### Von E: zu G:
- [ ] Auf E: committen und pushen
- [ ] Warten bis Cloud-Sync abgeschlossen (Google Drive Icon)
- [ ] Auf G: öffnen (automatisch aktuell)

### Von E: zu Arbeit:
- [ ] Auf E: committen und pushen (`git push origin master`)
- [ ] Auf Arbeit: `git pull origin master`
- [ ] Auf Arbeit: `.venv\Scripts\Activate.ps1`
- [ ] Optional: `pip install -r requirements.txt` (falls neue Dependencies)

### Von Arbeit zu E:
- [ ] Auf Arbeit: committen und pushen
- [ ] Auf E: `git pull origin master`
- [ ] Optional: `pip install -r requirements.txt` (falls neue Dependencies)

---

## 🆘 Probleme?

### "Module not found" nach git pull
```powershell
pip install -r requirements.txt --upgrade
```

### Git-Konflikte
```powershell
git status
git stash
git pull origin master
git stash pop
```

### Cloud-Sync zu langsam
- Google Drive Desktop App: Selektives Sync aktivieren
- Nur `___TelefonAssistent_3.0/` syncen
- Große Ordner ausschließen

### Tests schlagen fehl auf Arbeit
```powershell
# Nur Unit-Tests (ohne GPU/Dienste)
pytest tests/unit -v
```

---

## 📚 Weitere Dokumentation

- **`DEPLOYMENT_GUIDE.md`** – Vollständige Übersicht
- **`WORK_SETUP.md`** – Detaillierte Arbeits-PC Anleitung
- **`SETUP_AFTER_CLOUD_SYNC.md`** – Setup nach Cloud-Kopie
- **`README.md`** – Projekt-Übersicht

