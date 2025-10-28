# Setup nach Cloud-Sync (G: Laufwerk)

Nachdem du das Projekt auf das Cloud-Laufwerk kopiert hast, führe diese Schritte aus:

## 1. Virtuelle Umgebung neu erstellen

```powershell
# Zum Projekt-Verzeichnis wechseln
cd "G:\Meine Ablage\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0"

# Virtual Environment erstellen
python -m venv .venv

# Aktivieren
.venv\Scripts\Activate.ps1

# Dependencies installieren
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 2. Node Modules neu installieren (falls Dashboard verwendet wird)

```powershell
cd web\dashboard
npm install
npm run build
cd ..\..
```

## 3. Git Status prüfen

```powershell
git status
git log --oneline -5  # Zeigt letzte 5 Commits
```

## 4. Models herunterladen (falls nötig)

```powershell
# Piper Models (schon vorhanden in data/models/piper)
# Ollama Models (wenn nicht vorhanden)
ollama pull llama3:instruct

# WhisperX Models werden beim ersten Start automatisch geladen
```

## 5. Environment-Variablen anpassen

Die `.env.example` bzw. `.env.sample` Datei auf dem neuen Laufwerk anpassen:

```bash
# Pfade anpassen für G: Laufwerk
RECORD_PATH=G:\Meine Ablage\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0\data\audio
```

## 6. Testen

```powershell
# Unit Tests
pytest tests/unit -v

# Component Tests (benötigt GPU/Ollama)
pytest tests/component -v
```

## 7. Im Hinterkopf behalten

**Cloud-Sync bei Entwicklung:**
- Git Commits werden automatisch gesynct (wenn .git kopiert wurde)
- `.venv` und `node_modules` werden in der Cloud ignoriert (bereits in .gitignore)
- Bei jedem Wechsel zwischen E: und G: die Virtual Environment neu aktivieren

---

## Empfehlung

**Option A: Nur auf G: arbeiten**
- Einmal Setup auf G: durchführen
- Für alle Änderungen G: verwenden
- Cloud-Sync erledigt automatisch die Sicherung

**Option B: Beide Orte verwenden**
- E: für lokale Entwicklung
- G: für Cloud-Backup
- Regelmäßig: `git push` von E:, dann `git pull` auf G:

