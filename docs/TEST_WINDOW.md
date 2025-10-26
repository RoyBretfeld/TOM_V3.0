# TOM v3.0 - Test-Window für Realtime-API mit Fallback

**Wichtig**: Diese Anleitung beschreibt den Test-Prozess für die **Realtime-API mit Provider-First und Local-Fallback**. Nach dem Test-Window **muss ALLOW_EGRESS=false gesetzt werden**.

---

## 🎯 Ziel

**Provider-Realtime-API primär** produktiv testen (voller Duplex-Pfad, <500ms E2E), lokale Pipeline nur als **Fallback**. Kosten werden **mitgeloggt**, aber entscheiden nicht den Test.

---

## 1️⃣ Preflight-Checks

### Environment-Variablen prüfen:

```bash
# Muss gesetzt sein für Test-Window
export REALTIME_BACKEND=provider
export ALLOW_EGRESS=true                      # NUR für Testfenster!
export FALLBACK_POLICY=provider_then_local
export FALLBACK_TRIGGER_MS=800
export FALLBACK_ERROR_BURST=3

# Provider-Konfiguration
export REALTIME_WS_URL=wss://api.openai.com/v1/realtime
export REALTIME_API_KEY=sk-XXX

# Fallback-Konfiguration
export PIPER_VOICE=de-DE-thorsten-high
export PHONE_HASH_SALT=CHANGE_ME_SALT
```

### Preflight-Checks:

```bash
# 1. TLS/Firewall prüfen
curl -I https://api.openai.com/v1/realtime

# 2. Keys validieren
echo $REALTIME_API_KEY | wc -c  # Sollte > 20 sein

# 3. Local-Backend verfügbar
python -c "from apps.realtime.local_realtime import LocalRealtimeSession; print('Local OK')"

# 4. Monitoring aktiv
docker ps | grep prometheus

# 5. Log-Verzeichnis existiert
mkdir -p data/cost_logs data/test_results
```

---

## 2️⃣ Smoke-Tests

### 2.1 Realtime-Probe

```bash
# E2E-Latenztest
python scripts/realtime_probe.py

# Erwartete Exit-Codes:
# 0: E2E < 500ms ✓
# 1: 500ms <= E2E < 800ms ⚠
# 2: E2E >= 800ms ✗
```

### 2.2 Latenz-Ziele

- **First Token**: < 300ms
- **First Audio**: < 500ms
- **E2E**: < 500ms (optimal), < 800ms (akzeptabel)

### 2.3 Backend-Verifikation

```bash
# Prüfe ob Provider aktiv ist
curl http://localhost:8085/metrics | grep tom_realtime_backend

# Sollte zeigen:
# tom_realtime_backend{backend="provider"} 1
# tom_realtime_backend{backend="local"} 0
```

---

## 3️⃣ Live-Call-Tests

### 3.1 Test-Setup

1. **FreeSWITCH DID konfigurieren**:
   ```xml
   <!-- Dialplan: infra/freeswitch/dialplan_audio_fork.xml -->
   ```

2. **Gateway starten**:
   ```bash
   python apps/telephony_bridge/ws_realtime.py
   ```

3. **Monitoring starten**:
   ```bash
   docker-compose -f infra/docker-compose.monitoring.yml up -d
   ```

### 3.2 Test-Ablauf

1. **Live-Call**: Handy → FreeSWITCH DID → TOM antwortet
2. **Hörbarkeit prüfen**: TOM spricht deutlich hörbar
3. **Barge-In testen**: Unterbreche TOM, prüfe < 120ms Abbruch
4. **Duplex-Dialog**: Wechselnde Gesprächspartner, flüssiger Dialog

### 3.3 Erwartete Verhalten

- **Provider aktiv**: Dialog funktioniert, < 500ms E2E
- **Barge-In**: < 120ms Unterbrechung
- **Backpressure**: Metriken in Grafana beobachten
- **Cost-Log**: `data/cost_logs/costs_*.jsonl` wird gefüllt

---

## 4️⃣ Soak-Tests (10 Minuten)

### 4.1 Parallele Sessions

```bash
# 2 parallele Sessions starten
for i in {1..2}; do
  python scripts/realtime_probe.py &
done
wait
```

### 4.2 Metriken beobachten

**Grafana Dashboard**: `http://localhost:3000`

**Wichtige Metriken**:
- `tom_realtime_e2e_ms{backend="provider"}` → p95 < 800ms
- `tom_realtime_backend` → provider=1, local=0
- `tom_pipeline_backpressure_total` → sollte 0 bleiben
- `tom_provider_failover_total` → sollte 0 bleiben

### 4.3 Failover-Szenario

```bash
# Provider absichtlich trennen (Firewall-Regel)
sudo iptables -A OUTPUT -d api.openai.com -j DROP

# Warte 30s → sollte auf Local failen
sleep 30

# Prüfe Metriken
curl http://localhost:8085/metrics | grep tom_provider_failover_total
# Sollte zeigen: tom_provider_failover_total 1

# Prüfe Backend-Wechsel
curl http://localhost:8085/metrics | grep tom_realtime_backend
# Sollte zeigen: backend="local"} 1

# Provider wieder aktivieren
sudo iptables -D OUTPUT -d api.openai.com -j DROP
```

---

## 5️⃣ Kosten-Tracking (informativ)

### 5.1 Cost-Logs

```bash
# Log-Dateien anzeigen
ls -lh data/cost_logs/costs_*.jsonl

# Beispiel-Eintrag:
cat data/cost_logs/costs_20250101.jsonl | jq .
```

**Beispiel**:
```json
{
  "call_id": "call_12345",
  "backend": "provider",
  "start_time": "2025-01-01T10:00:00",
  "end_time": "2025-01-01T10:02:30",
  "stt_duration_s": 150,
  "llm_duration_s": 120,
  "tts_duration_s": 100,
  "stt_cost_eur": 0.0750,
  "llm_cost_eur": 0.0800,
  "tts_cost_eur": 0.0167,
  "total_cost_eur": 0.1717
}
```

### 5.2 Kosten-Zusammenfassung

```bash
# Kosten pro Tag berechnen
cat data/cost_logs/costs_*.jsonl | jq -s 'map(.total_cost_eur) | add'
```

---

## 6️⃣ Fallback-Verhalten

### 6.1 Automatischer Failover

**Trigger**:
- **Latenz**: p95 E2E > `FALLBACK_TRIGGER_MS` (800ms) für 10 Minuten
- **Fehler-Burst**: `FALLBACK_ERROR_BURST` (3) Fehler in `FALLBACK_ERROR_WINDOW` (60s)

**Verhalten**:
1. Provider-Session wird geschlossen
2. Local-Session wird erstellt
3. Backend-Typ wechselt von "provider" → "local"
4. Metrik `tom_provider_failover_total` wird inkrementiert
5. Cooldown für 10 Minuten

### 6.2 Monitoring

```bash
# Failover-Erkennung
curl http://localhost:8085/metrics | grep tom_provider_failover_total

# Backend-Status
watch -n 1 "curl -s http://localhost:8085/metrics | grep tom_realtime_backend"
```

---

## 7️⃣ Rückbau (WICHTIG)

### 7.1 Test-Window beenden

**Nach Testfenster**:

```bash
# ALLOW_EGRESS zurücksetzen
export ALLOW_EGRESS=false

# Config neu laden
source .env.realtime.test

# Services neu starten
docker-compose restart
```

### 7.2 Verification

```bash
# Prüfe ob Provider deaktiviert ist
curl http://localhost:8085/metrics | grep tom_realtime_backend

# Sollte zeigen:
# tom_realtime_backend{backend="provider"} 0
# tom_realtime_backend{backend="local"} 1
```

### 7.3 Alert-Check

```bash
# Prüfe Alert-Status
curl -X POST http://localhost:9090/api/v1/alerts

# Alert-Regel: backend==provider UND ALLOW_EGRESS=false → Hard Alert
```

---

## 8️⃣ Definition of Done

✅ **Provider aktiv**: Hörbarer Duplex-Dialog mit < 500-800ms E2E  
✅ **Barge-In funktioniert**: < 120ms Abbruch  
✅ **Fallback funktioniert**: Bei Fehler/Latenz → Local übernimmt  
✅ **Metriken sichtbar**: Backend-Gauge, Failover-Counter, E2E-Latenz  
✅ **Cost-Log erzeugt**: JSONL mit Kosten-Tracking (informativ)  
✅ **Rückbau erfolgt**: `ALLOW_EGRESS=false` nach Test-Window  

---

## 9️⃣ Troubleshooting

### Problem: Provider-Connection failed

```bash
# Prüfe Network
curl -I https://api.openai.com/v1/realtime

# Prüfe Keys
echo $REALTIME_API_KEY | cut -c1-7

# Prüfe Logs
tail -f logs/tom.log | grep "Provider"
```

### Problem: High Latency (> 800ms)

```bash
# Provider-Latenz messen
curl -w "@curl-format.txt" https://api.openai.com/v1/realtime

# Fallback aktivieren
export FALLBACK_TRIGGER_MS=600
docker-compose restart
```

### Problem: Failover nicht aktiviert

```bash
# Prüfe Policy
echo $FALLBACK_POLICY

# Sollte sein: provider_then_local

# Prüfe Logs
grep "failover" logs/tom.log
```

---

## 🔟 Nächste Schritte

Nach erfolgreichem Test-Window:

1. **Cost-Analyse**: Kosten-Logs analysieren
2. **Provider-Performance**: E2E-Latenz vs. Kosten bewerten
3. **Fallback-Rate**: Wie oft wurde gefailovert?
4. **User-Feedback**: Dialog-Qualität bewerten
5. **Entscheidung**: Provider primär oder nur Fallback?

---

**Test-Window erfolgreich abgeschlossen!** ✅

