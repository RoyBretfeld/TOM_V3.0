# CSB v1 – Start-Prompt (zum Anpinnen)

So nutzt du dieses Dokument bei JEDEM neuen Cursor-Task:
1) **Block A** (System-Header) komplett kopieren → ganz oben in deinen Prompt einfügen.  
2) **Block B** (Prompt-Gerüst) darunter ausfüllen (Scope/AC/Tests).  
3) Prompt in Cursor senden. Fertig.

---

## 🔒 Block A – CSB System-Header (immer ganz oben einfügen)

[SYSTEM • CSB v1 — Cursor-Safety Baseline]

Ziele:
- Originaldaten bleiben unverändert.
- Einheitliches Encoding (UTF-8) in allen Schreibpfaden.
- Kleine, überprüfbare Diffs mit Tests + Akzeptanzkriterien.
- Messbare SLOs (Accuracy, Mojibake=0, Integrität OK).

Leitplanken:
1) READ-ONLY INPUTS: Alles unter **./data/originals/** ist unantastbar (keine Schreib/Move/Rename-Operationen).
2) ENCODING: Alle Schreib/Export/Log-Operationen mit `encoding="utf-8"`. Keine cp1252/cp850 in Writes.
3) SCOPE: Nur die im Prompt **namentlich** genannten Dateien ändern. Keine Refactorings, keine neuen Dependencies.
4) DIFF-LIMIT: Max **30 Dateien** ODER **600 Zeilen** geändert. Bei Überschreitung **abbrechen**.
5) TESTS: Für jede Änderung mind. **1** passender Test + **klare Akzeptanzkriterien**.
6) SLOs: Erkennungsquote ≥ **95 %**, Mojibake-Marker **= 0**, Original-Integrität **OK**. Bei Verstoß **abbrechen**.
7) LOGGING: Ruhig, UTF-8-safe; keine Debug-Flut.
8) SECURITY: Keine Secrets ins Repo. Pre-commit/CI müssen grün sein.

Verpflichtende Checks je Task:
- **pre-commit ok** · **tests ok** · (falls vorhanden) **ci_slo_check ok** · **no writes** to `./data/originals/**`
[END SYSTEM]

---

## 🧭 Block B – Prompt-Gerüst (ausfüllen)

# Prompt – <Kurzbeschreibung des Tasks>
**Scope (Dateiliste, nur diese Pfade ändern):**  
- <pfad/zu/datei1>  
- <pfad/zu/datei2>  
*(nichts außerhalb dieser Liste anfassen)*

**Ziele / Akzeptanzkriterien (messbar):**  
- [ ] <konkret, z. B. „Match-Endpoint zeigt `has_geo` korrekt für Aliasse“>  
- [ ] <„/api/... liefert Filter q/action + Paginierung“>  
- [ ] <„Kein Mojibake in Response; UTF-8-Schreibpfade gesetzt“>

**Tests (mindestens einer, kurz beschreiben):**  
- `tests/<name>.py`: <was wird geprüft, happy & edge case>  
- (optional) Smoke: <ein GET/POST mit Beispiel-Payload>

**Nicht tun (Guard):**  
- Kein Refactoring/Rewrite.  
- Keine neuen Dependencies.  
- Keine Änderungen unter `./data/originals/**`.  
- Keine Debug-Logs über INFO hinaus.

**Diff-Budget:** ≤30 Dateien ODER ≤600 Zeilen.

**SLO-Bezug:**  
- Accuracy ≥95 % · Mojibake=0 · Original-Integrität OK.  
- Bei SLO-Verstoß: **Task abbrechen** und Befund berichten.

**Output (erwartet):**  
- Unified-Diff + kurze Markdown-Zusammenfassung (Was/Warum/Wie testen).  
- Hinweise auf neue/angepasste ENV-Flags (falls relevant).

---

## ✅ Block C – Mini-Checkliste vor dem Senden

- [ ] **CSB-Header** oben eingefügt  
- [ ] **Scope** ist eng (konkrete Dateien/Pfade)  
- [ ] **AC** sind messbar (ja/nein prüfbar)  
- [ ] **Mind. 1 Test** vorgesehen  
- [ ] **Diff-Budget** notiert (≤30 Files/≤600 Zeilen)  
- [ ] **SLOs** genannt (95 %/0/MOI OK)  
- [ ] Keine Schreibpfade Richtung **`./data/originals/**`**

---

## ℹ️ Hinweise

- **UTF-8**: Jede Schreib-Operation in Code-Beispielen explizit mit `encoding="utf-8"` anfordern.  
- **Originale**: Alles, was aus CSV/Tourplänen kommt, gilt als **read-only** und wird **niemals** überschrieben.  
- **Fehlschlag erwünscht**: Wenn Leitplanken reißen (SLO, Diff-Limit, RO-Pfad) → der Assistent soll abbrechen und den Grund melden (kein „Heldencode“).

