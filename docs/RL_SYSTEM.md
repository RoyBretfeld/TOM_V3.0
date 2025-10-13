# TOM v3.0 - Reinforcement Learning System

## 🎯 Übersicht

Das RL-System für TOM v3.0 implementiert ein vollständiges **Reinforcement Learning Framework** zur kontinuierlichen Verbesserung des Realtime Voice Assistants durch **Feedback → Reward → Policy-Update**.

## 🏗️ Architektur

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Feedback      │    │   Reward        │    │   Policy        │
│   Collector     │───▶│   Calculator    │───▶│   Bandit        │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SQLite DB     │    │   Metrics        │    │   FSM Router    │
│   (Anonymized)  │    │   (Prometheus)   │    │   Integration   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 Komponenten

### 1. **Feedback Collector** (`apps/rl/feedback.py`)
- Sammelt und speichert Feedback-Events in SQLite
- Pydantic-Validierung gegen JSON-Schema
- PII-Anonymisierung vor Persistierung
- Statistiken und Cleanup-Funktionen

### 2. **Reward Calculator** (`apps/rl/reward_calc.py`)
- Berechnet normalisierten Reward `r ∈ [-1, +1]`
- Konfigurierbare Gewichtung verschiedener Signale
- Komponenten-Analyse für Debugging
- Clamping und Edge-Case-Behandlung

### 3. **Policy Bandit** (`apps/rl/policy_bandit.py`)
- Thompson Sampling für Policy-Auswahl
- Persistente Speicherung in JSON
- Statistiken und Konfidenz-Metriken
- Exploration-Rate-Schätzung

### 4. **Policy Router** (`apps/dispatcher/rt_fsm.py`)
- Integration in bestehende FSM-Logik
- Dynamische Policy-Auswahl basierend auf Kontext
- Session-Management mit Policy-Tracking
- Automatische Reward-Updates

### 5. **Prompt Variants** (`docs/policies/prompt_variants.yaml`)
- 12 verschiedene Policy-Kombinationen
- Slots: greeting, tone, length, inquiry_mode, barge_in_sensitivity
- Bandit-Konfiguration und Deployment-Regeln
- A/B-Testing-Parameter

### 6. **End-of-Call Feedback** (`apps/dispatcher/closing.py`)
- Automatische Feedback-Sammlung am Gesprächsende
- Robuste Parsing von Benutzerbewertungen (1-5)
- Policy-spezifische Feedback-Fragen
- Integration mit Feedback Collector

### 7. **Metrics Exporter** (`apps/monitor/metrics.py`)
- Prometheus-Metriken für RL-System
- Counter, Histogram, Gauge für verschiedene Metriken
- Registry-basierte Metriken-Sammlung
- Convenience-Funktionen für einfache Integration

### 8. **Deploy Guard** (`apps/rl/deploy_guard.py`)
- Shadow/A-B Deployment-Schutz
- Traffic-Split-Logik (10% neue, 5% unsichere Varianten)
- Automatische Blacklist bei schlechter Performance
- Deployment-Status und Gesundheitsmonitoring

### 9. **Offline Trainer** (`notebooks/rl_offline_train.md`)
- Markdown-Notebook mit Code-Blöcken
- Feature Engineering und Pairwise Preferences
- Optionales Reward Model Training
- Grid Search über Prompt-Slots
- Candidate Export für Deployment

## 🔄 Workflow

### 1. **Feedback-Sammlung**
```python
# Am Ende eines Gesprächs
from apps.dispatcher.closing import ask_feedback

session_context = {
    'policy_variant': 'v1a',
    'profile': 'kfz',
    'duration_sec': 120,
    'barge_in_count': 1,
    'repeats': 0
}

rating = await ask_feedback("call_123", session_context)
```

### 2. **Policy-Auswahl**
```python
# Bei neuen Gesprächen
from apps.dispatcher.rt_fsm import create_call_session

context = {'profile': 'kfz', 'time_of_day': 'morning'}
session = await create_call_session("call_456", "kfz")
# Policy wird automatisch über Bandit ausgewählt
```

### 3. **Reward-Berechnung**
```python
# Automatisch bei Gesprächsende
from apps.rl.reward_calc import calc_reward

signals = {
    'resolution': True,
    'user_rating': 4,
    'barge_in_count': 1,
    'duration_sec': 120
}

reward = calc_reward(signals)  # z.B. 0.7
```

### 4. **Bandit-Update**
```python
# Automatisch nach Reward-Berechnung
from apps.rl.policy_bandit import update_policy_reward

update_policy_reward('v1a', 0.7)
```

### 5. **Deployment-Guard**
```python
# Für sichere Policy-Deployment
from apps.rl.deploy_guard import select_variant_for_deployment

variant = select_variant_for_deployment({'profile': 'kfz'})
# Berücksichtigt Traffic-Split und Blacklist
```

## 📊 Metriken

### Prometheus-Metriken
- `rl_feedback_total`: Anzahl Feedback-Events
- `rl_reward_distribution`: Reward-Verteilung
- `rl_user_rating_distribution`: Benutzerbewertungen
- `rl_policy_pulls_total`: Policy-Auswahlen
- `rl_policy_success_rate`: Erfolgsrate pro Variante
- `rl_bandit_exploration_rate`: Exploration-Rate
- `rl_active_variants_total`: Aktive Varianten
- `rl_blacklisted_variants_total`: Blacklisted Varianten

### Beispiel-Abfragen
```promql
# Durchschnittlicher Reward pro Variante
avg(rl_reward_distribution) by (policy_variant)

# Erfolgsrate der letzten 24h
rate(rl_policy_success_rate[24h])

# Exploration vs. Exploitation
rl_bandit_exploration_rate
```

## 🛡️ Sicherheit

### PII-Schutz
- Automatische Anonymisierung von Call-IDs
- Zeitstempel-Aggregation (Stunden-Granularität)
- Keine Speicherung von Audio-Inhalten
- GDPR-konforme Datenverarbeitung

### Deployment-Sicherheit
- Traffic-Split-Limits (max. 10% neue Varianten)
- Automatische Blacklist bei schlechter Performance
- Rollback-Mechanismen
- Sandbox-Learning-Umgebung

## 🚀 Deployment

### 1. **Initialisierung**
```bash
# Datenverzeichnisse erstellen
mkdir -p data/rl
mkdir -p docs/policies

# Policy-Varianten laden
python -c "
from apps.rl.policy_bandit import PolicyBandit
from apps.rl.deploy_guard import DeployGuard
import yaml

# Varianten aus YAML laden
with open('docs/policies/prompt_variants.yaml') as f:
    data = yaml.safe_load(f)

bandit = PolicyBandit()
for variant_id, variant_data in data['variants'].items():
    bandit.add_variant(PolicyVariant(
        id=variant_id,
        name=variant_data['name'],
        parameters=variant_data['parameters']
    ))

# DeployGuard initialisieren
guard = DeployGuard()
for variant_id in data['variants'].keys():
    guard.add_variant_to_deployment(variant_id)
"
```

### 2. **Monitoring einrichten**
```bash
# Prometheus-Metriken aktivieren
curl http://localhost:8080/metrics

# Grafana-Dashboard erstellen
# Importiere RL-Metriken-Dashboard
```

### 3. **Offline-Training planen**
```bash
# Wöchentliches Training
crontab -e
# 0 2 * * 1 /path/to/python /path/to/notebooks/rl_offline_train.md
```

## 📈 Performance-Optimierung

### Bandit-Konvergenz
- **Thompson Sampling**: Balanciert Exploration/Exploitation
- **Optimistische Initialisierung**: Alpha=1, Beta=1
- **Konfidenz-Schwellwerte**: Min. 10 Pulls für Konfidenz

### Reward-Formel
```python
reward = 0.6 * resolution +           # Problemlösung
         0.2 * ((rating-3)/2) +         # Benutzerbewertung (skaliert)
         -0.1 * min(barge_ins, 3)/3 +   # Barge-Ins (penalisiert)
         -0.1 * min(repeats, 3)/3 +     # Wiederholungen (penalisiert)
         -0.1 * handover +              # Übergabe (penalisiert)
         clamp((180-duration)/180, -0.2, +0.2)  # Dauer-Bonus/Malus
```

## 🔧 Konfiguration

### Umgebungsvariablen
```bash
# RL-System aktivieren
RL_ENABLED=true
RL_FEEDBACK_DB_PATH=data/rl/feedback.db
RL_BANDIT_STATE_PATH=data/rl/bandit_state.json

# Deployment-Guard
RL_TRAFFIC_SPLIT_NEW=0.1
RL_TRAFFIC_SPLIT_UNCERTAIN=0.05
RL_BLACKLIST_THRESHOLD=-0.2
RL_MIN_PULLS_FOR_BLACKLIST=20

# Metriken
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
```

### YAML-Konfiguration
```yaml
# docs/policies/prompt_variants.yaml
bandit_config:
  initial_alpha: 1.0
  initial_beta: 1.0
  exploration_rate: 0.1
  min_pulls_for_confidence: 10

deployment:
  traffic_split:
    new_variants: 0.1
    uncertain_variants: 0.05
    base_variant: "v1a"
  blacklist_threshold:
    reward_mean: -0.2
    min_pulls: 20
```

## 🧪 Testing

### Unit Tests
```bash
# Alle RL-Tests ausführen
python -m pytest tests/rl/ -v

# Spezifische Komponenten testen
python -m pytest tests/rl/test_feedback.py -v
python -m pytest tests/rl/test_reward_calc.py -v
python -m pytest tests/rl/test_policy_bandit.py -v
python -m pytest tests/unit/test_dispatcher_fsm.py -v
python -m pytest tests/unit/test_closing.py -v
python -m pytest tests/unit/test_metrics.py -v
```

### Integration Tests
```bash
# End-to-End RL-Workflow testen
python -c "
import asyncio
from apps.dispatcher.rt_fsm import create_call_session, handle_call_event, CallEvent
from apps.dispatcher.closing import ask_feedback

async def test_rl_workflow():
    # Session erstellen
    session = await create_call_session('test_call', 'kfz')
    print(f'Policy ausgewählt: {session.policy_variant}')
    
    # Gespräch simulieren
    await handle_call_event('test_call', CallEvent.INCOMING_CALL)
    await handle_call_event('test_call', CallEvent.CALL_ANSWERED)
    await handle_call_event('test_call', CallEvent.CALL_ENDED)
    
    # Feedback sammeln
    rating = await ask_feedback('test_call', {
        'policy_variant': session.policy_variant,
        'profile': 'kfz',
        'duration_sec': 120
    })
    print(f'Feedback erhalten: {rating}')

asyncio.run(test_rl_workflow())
"
```

## 📚 Weiterführende Dokumentation

- [Feedback Schema](docs/schemas/feedback_event.json)
- [Policy Variants](docs/policies/prompt_variants.yaml)
- [Offline Training](notebooks/rl_offline_train.md)
- [FSM Integration](apps/dispatcher/rt_fsm.py)
- [Metrics API](apps/monitor/metrics.py)

## 🤝 Contributing

### Code-Standards
- **Pydantic V2**: Verwende `@field_validator` statt `@validator`
- **Type Hints**: Vollständige Typisierung aller Funktionen
- **Docstrings**: Google-Style für alle öffentlichen Funktionen
- **Tests**: Mindestens 80% Code-Coverage

### Pull Request Checklist
- [ ] Alle Tests bestehen
- [ ] Type Hints korrekt
- [ ] Docstrings aktualisiert
- [ ] Metriken integriert
- [ ] Sicherheitsprüfungen bestanden

## 📞 Support

Bei Fragen zum RL-System:
- **Issues**: GitHub Issues mit `rl` Label
- **Dokumentation**: Siehe `docs/` Verzeichnis
- **Beispiele**: Siehe `notebooks/` Verzeichnis
- **Tests**: Siehe `tests/rl/` Verzeichnis
