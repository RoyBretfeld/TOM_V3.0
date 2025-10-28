# TOM v3.0 – Sync Ordner

**Zweck:** Dieser Ordner enthält alle Dateien, die für die Synchronisation zwischen E: (lokal), G: (Cloud) und Arbeit benötigt werden.

---

## Was gehört hier rein?

### ✅ DOHIN (wird gesynct)
- Konfigurationsdateien (`*.yaml`, `*.json`)
- Scripts für Automatisierung
- Batch-Dateien für Robocopy
- Import/Export-Tools
- Backup-Skripte

### ❌ NICHT DOHIN (wird NICHT gesynct)
- Große Dateien (> 10 MB)
- Audio-Dateien
- Modelle (WhisperX, Piper)
- Logs
- Cache-Dateien

---

## Dateien

### `sync_to_cloud.bat`
Windows-Batch-Script für Robocopy von E: → G:

### `sync_from_cloud.bat`
Windows-Batch-Script für Robocopy von G: → E:

### `setup_new_location.sh`
Setup-Script für neue Standorte (Linux/Mac)

### `check_git_status.ps1`
PowerShell-Script um Git-Status auf allen Standorten zu prüfen

---

## Verwendung

### Von E: nach G: synct
```powershell
cd sync
.\sync_to_cloud.bat
```

### Von G: nach E: synct
```powershell
cd sync
.\sync_from_cloud.bat
```

### Git-Status prüfen
```powershell
cd sync
.\check_git_status.ps1
```

---

## Best Practices

1. **Keine großen Dateien** – Nur Scripts und Konfigurationen
2. **KEINE Secrets** – API-Keys, Passwörter bleiben in `.env` (nicht in Git)
3. **Beschreibende Namen** – z.B. `setup_arbeit.sh`, `backup_db.sql`
4. **Kommentare** – In Scripts beschreiben was sie tun

---

## Wo liegt was?

- **E: (Privat):** Entwicklungs-Ort, große Dateien
- **G: (Cloud):** Backup, automatischer Sync
- **Arbeit:** Git-Clone oder Import

Siehe `DEPLOYMENT_GUIDE.md` für Details.

