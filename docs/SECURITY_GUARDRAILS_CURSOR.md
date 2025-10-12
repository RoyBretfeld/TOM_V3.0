# TOM v3.0 – Sicherheitsleitplanken für Cursor

## 🛡️ CSB v1 Compliance

Dieses Dokument definiert die Sicherheitsleitplanken für die Entwicklung von TOM v3.0 mit Cursor.

### Grundprinzipien

1. **Read-Only Schutz**: Alle Dateien in `docs/` sind schreibgeschützt
2. **UTF-8 Encoding**: Alle Ausgaben mit `encoding="utf-8"`
3. **Modulare Entwicklung**: Nur explizit genannte Module ändern
4. **Diff-Limits**: Max 30 Dateien oder 600 Zeilen pro Commit
5. **Test-Pflicht**: Mindestens 1 Test pro Änderung

### Verbotene Operationen

- **Keine Änderungen** an Dateien in `docs/`
- **Keine Schreibzugriffe** auf `data/runtime/` (außer für Laufzeitdaten)
- **Keine Refactorings** ohne explizite Genehmigung
- **Keine neuen Dependencies** ohne Begründung

### Erlaubte Bereiche

- **Apps-Module**: `apps/telephony_bridge/`, `apps/realtime/`, `apps/dispatcher/`, `apps/monitor/`
- **Web-Frontend**: `web/dashboard/`
- **Infrastruktur**: `infra/` (außer `.env` Dateien)
- **Tests**: `tests/unit/`, `tests/e2e/`
- **Scripts**: `scripts/` (außer `init_project.py`)

### SLO-Anforderungen

- **Accuracy**: ≥ 95% für alle Verarbeitungsschritte
- **Mojibake**: = 0 (keine Encoding-Fehler)
- **Fail-Rate**: < 2% für alle Komponenten
- **Latenz**: < 1000ms End-to-End für Realtime-Pipeline

### Entwicklungsrichtlinien

1. **Prompt-Template**: Immer `docs/CBS-STARD.md` verwenden
2. **Scope-Definition**: Konkrete Dateien/Pfade angeben
3. **Akzeptanzkriterien**: Messbare Ziele definieren
4. **Test-Coverage**: Mindestens 80% für neue Module

### Sicherheitschecks

- **Pre-commit Hooks**: Automatische Qualitätsprüfungen
- **CI/CD Pipeline**: Automatische Tests und Security-Scans
- **Code Review**: Alle Änderungen müssen reviewed werden
- **Dependency Audit**: Regelmäßige Sicherheitsprüfungen

### Verstöße

Bei Verstößen gegen diese Leitplanken:
1. **Sofortiger Stopp** der Entwicklung
2. **Rückgängigmachung** der Änderungen
3. **Analyse** der Ursache
4. **Anpassung** der Leitplanken falls nötig

### Kontakt

Bei Fragen zu diesen Leitplanken siehe `docs/CBS-STARD.md` oder erstelle ein Issue mit dem Template `docs/.github/ISSUE_TEMPLATE/guardrails.md`.
