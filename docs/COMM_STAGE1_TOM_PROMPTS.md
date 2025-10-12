# TOM v3.0 – Cursor Prompts für Stage 1 Entwicklung

## 🎯 Übersicht

Dieses Dokument enthält alle Cursor-Prompts für die erste Entwicklungsphase von TOM v3.0. Die Prompts sind in der richtigen Reihenfolge angeordnet und sollten nacheinander abgearbeitet werden.

---

## 📋 Prompt 1: Docker-Compose Setup

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Docker-Compose Setup für TOM v3.0 Realtime-Architektur

**Scope (Dateiliste, nur diese Pfade ändern):**
- infra/docker-compose.realtime.yml
- infra/.env.example
- infra/nginx.conf

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] Docker-Compose definiert alle Container: Redis, Telephony Bridge, STT/LLM/TTS Worker, Monitor
- [ ] Alle Services sind über interne Netzwerke verbunden
- [ ] Environment-Variablen sind korrekt gesetzt (UTF-8)
- [ ] Nginx-Konfiguration für Load-Balancing vorhanden

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_docker_compose.py: Prüft Docker-Compose Syntax und Service-Definitionen

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer Docker.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤3 Dateien ODER ≤200 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 📋 Prompt 2: Telephony Bridge

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Telephony Bridge WebSocket-Implementation

**Scope (Dateiliste, nur diese Pfade ändern):**
- apps/telephony_bridge/ws.py
- apps/telephony_bridge/__init__.py
- tests/unit/test_telephony_bridge.py

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] WebSocket-Server läuft auf konfigurierbarem Port
- [ ] Audio-Streams werden korrekt zwischen Telefonie und Realtime-Pipeline weitergeleitet
- [ ] Verbindungsmanagement für mehrere gleichzeitige Anrufe
- [ ] UTF-8 sichere Logging-Ausgaben

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_telephony_bridge.py: WebSocket-Verbindungen, Audio-Stream-Handling, Multi-Client-Support

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer websockets, asyncio.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤3 Dateien ODER ≤300 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 📋 Prompt 3: Realtime STT Stream

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Realtime STT Stream-Verarbeitung

**Scope (Dateiliste, nur diese Pfade ändern):**
- apps/realtime/stt_stream.py
- apps/realtime/__init__.py
- tests/unit/test_stt_stream.py

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] Audio-Stream wird kontinuierlich zu Text transkribiert
- [ ] Latenz < 200ms für lokale STT-Verarbeitung
- [ ] UTF-8 sichere Text-Ausgabe
- [ ] Redis-Integration für Stream-Weiterleitung

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_stt_stream.py: Audio-zu-Text-Konvertierung, Latenzmessung, Redis-Integration

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer speech_recognition, redis.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤3 Dateien ODER ≤250 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 📋 Prompt 4: Realtime LLM Stream

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Realtime LLM Stream-Verarbeitung

**Scope (Dateiliste, nur diese Pfade ändern):**
- apps/realtime/llm_stream.py
- apps/realtime/__init__.py
- tests/unit/test_llm_stream.py

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] Text-Stream wird kontinuierlich zu LLM-Response verarbeitet
- [ ] Latenz < 500ms für Provider-basierte LLM-Verarbeitung
- [ ] UTF-8 sichere Text-Ein- und Ausgabe
- [ ] Redis-Integration für Stream-Weiterleitung

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_llm_stream.py: Text-zu-Response-Konvertierung, Latenzmessung, Provider-Integration

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer openai, redis.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤3 Dateien ODER ≤300 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 📋 Prompt 5: Realtime TTS Stream

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Realtime TTS Stream-Verarbeitung

**Scope (Dateiliste, nur diese Pfade ändern):**
- apps/realtime/tts_stream.py
- apps/realtime/__init__.py
- tests/unit/test_tts_stream.py

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] Text-Stream wird kontinuierlich zu Audio synthetisiert
- [ ] Latenz < 300ms für lokale TTS-Verarbeitung
- [ ] UTF-8 sichere Text-Eingabe
- [ ] Redis-Integration für Stream-Weiterleitung

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_tts_stream.py: Text-zu-Audio-Konvertierung, Latenzmessung, Audio-Qualität

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer pyttsx3, redis.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤3 Dateien ODER ≤250 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 📋 Prompt 6: Realtime Bus

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Realtime Bus für Stream-Koordination

**Scope (Dateiliste, nur diese Pfade ändern):**
- apps/realtime/realtime_bus.py
- apps/realtime/__init__.py
- tests/unit/test_realtime_bus.py

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] Redis-basierte Stream-Koordination zwischen STT/LLM/TTS
- [ ] Message-Routing zwischen allen Realtime-Komponenten
- [ ] Fehlerbehandlung und Retry-Logik
- [ ] UTF-8 sichere Message-Serialisierung

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_realtime_bus.py: Stream-Koordination, Message-Routing, Fehlerbehandlung

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer redis, asyncio.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤3 Dateien ODER ≤350 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 📋 Prompt 7: Dispatcher FSM

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Dispatcher FSM für Anrufsteuerung

**Scope (Dateiliste, nur diese Pfade ändern):**
- apps/dispatcher/rt_fsm.py
- apps/dispatcher/__init__.py
- tests/unit/test_dispatcher_fsm.py

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] FSM-basierte Anrufsteuerung mit Zuständen: IDLE, RINGING, CONNECTED, PROCESSING, ENDED
- [ ] State-Transitions basierend auf Audio-Events und User-Input
- [ ] Fehlerbehandlung für unerwartete Zustände
- [ ] UTF-8 sichere State-Logging

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_dispatcher_fsm.py: State-Transitions, Event-Handling, Fehlerbehandlung

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer asyncio, enum.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤3 Dateien ODER ≤400 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 📋 Prompt 8: Monitor Metriken

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Monitor Metriken und Health-Checks

**Scope (Dateiliste, nur diese Pfade ändern):**
- apps/monitor/metrics.py
- apps/monitor/health.py
- apps/monitor/__init__.py
- tests/unit/test_monitor.py

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] Prometheus-Metriken für alle Realtime-Komponenten
- [ ] Health-Checks für alle Services (Redis, WebSocket, STT/LLM/TTS)
- [ ] Latenz-Monitoring für End-to-End-Performance
- [ ] UTF-8 sichere Metriken-Ausgabe

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_monitor.py: Metriken-Sammlung, Health-Checks, Prometheus-Integration

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer prometheus_client, redis.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤4 Dateien ODER ≤300 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 📋 Prompt 9: Realtime Probe Script

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Realtime Probe Script für Latenzmessung

**Scope (Dateiliste, nur diese Pfade ändern):**
- scripts/realtime_probe.py
- tests/unit/test_realtime_probe.py

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] Latenzmessung für komplette Realtime-Pipeline (STT → LLM → TTS)
- [ ] Performance-Benchmarks für verschiedene Audio-Längen
- [ ] CSV-Export der Messergebnisse mit UTF-8 Encoding
- [ ] Automatische SLO-Verifikation (< 1000ms End-to-End)

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_realtime_probe.py: Latenzmessung, Benchmark-Funktionalität, CSV-Export

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer asyncio, csv, time.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤2 Dateien ODER ≤200 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 📋 Prompt 10: Init Project Script

**Prompt:**
```
[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter ./docs/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit encoding="utf-8". Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt namentlich genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max 30 Dateien ODER 600 Zeilen geändert. Bei Überschreitung abbrechen.
5) TESTS: Für jede Änderung mind. 1 passender Test + klare Akzeptanzkriterien.
6) SLOs: Erkennungsquote ≥ 95 %, Mojibake-Marker = 0, Original-Integrität OK. Bei Verstoß abbrechen.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- pre-commit ok · tests ok · (falls vorhanden) ci_slo_check ok · no writes to ./docs/**
[END SYSTEM]

# Prompt – Init Project Script für automatische Projektinitialisierung

**Scope (Dateiliste, nur diese Pfade ändern):**
- scripts/init_project.py
- tests/unit/test_init_project.py

**Ziele / Akzeptanzkriterien (messbar):**
- [ ] Automatische Erstellung aller fehlenden Verzeichnisse
- [ ] Generierung von __init__.py Dateien für alle Python-Module
- [ ] UTF-8 sichere Dateierstellung
- [ ] Validierung der Projektstruktur

**Tests (mindestens einer, kurz beschreiben):**
- tests/unit/test_init_project.py: Verzeichnis-Erstellung, __init__.py-Generierung, Struktur-Validierung

**Nicht tun (Guard):**
- Kein Refactoring/Rewrite.
- Keine neuen Dependencies außer os, pathlib.
- Keine Änderungen unter ./docs/**.
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤2 Dateien ODER ≤150 Zeilen.

**SLO-Bezug:**
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.
- Bei SLO-Verstoß: Task abbrechen und Befund berichten.

**Output (erwartet):**
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).
```

---

## 🎯 Verwendung

1. **Reihenfolge einhalten**: Prompts 1-10 nacheinander abarbeiten
2. **CSB-Header**: Immer den kompletten CSB-Header verwenden
3. **Scope beachten**: Nur die genannten Dateien ändern
4. **Tests schreiben**: Für jede Änderung mindestens 1 Test
5. **SLOs prüfen**: Accuracy ≥ 95%, Mojibake = 0, Fail-Rate < 2%

## ✅ Erfolgskriterien

Nach Abarbeitung aller Prompts:
- [ ] Alle Docker-Container laufen
- [ ] Realtime-Pipeline funktioniert
- [ ] Latenzziele erreicht (< 1000ms)
- [ ] Alle Tests bestehen
- [ ] CSB v1 Compliance eingehalten
