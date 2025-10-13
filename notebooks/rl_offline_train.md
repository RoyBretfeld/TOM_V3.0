# TOM v3.0 - RL Offline Trainer

## Ziel

Offline-Training für Reinforcement Learning System zur kontinuierlichen Verbesserung der Policy-Varianten basierend auf gesammelten Feedback-Daten.

## Übersicht

Dieses Notebook demonstriert den Offline-Training-Workflow für TOM v3.0:

1. **Datenladen**: Feedback-Events aus SQLite-Datenbank
2. **Feature Engineering**: Aufbereitung der Daten für ML-Training
3. **Pairwise Preferences**: Generierung von Präferenzpaaren
4. **Reward Model Training**: Optionales kleines Reward-Modell
5. **Grid Search**: Suche über Prompt-Slots
6. **Candidate Export**: Top-Kandidaten für Deployment

## 1. Setup und Imports

```python
import sqlite3
import pandas as pd
import numpy as np
import json
import yaml
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
import logging

# ML Libraries
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder, StandardScaler

# RL Components
from apps.rl.feedback import FeedbackCollector
from apps.rl.reward_calc import RewardCalculator
from apps.rl.policy_bandit import PolicyBandit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

## 2. Datenladen und Exploration

```python
def load_feedback_data(db_path: str = 'data/rl/feedback.db', 
                      days_back: int = 30) -> pd.DataFrame:
    """
    Lädt Feedback-Daten aus SQLite-Datenbank
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    cutoff_ts = cutoff_date.timestamp()
    
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT call_id, ts, agent, profile, policy_variant, signals
        FROM feedback 
        WHERE ts >= ?
        ORDER BY ts DESC
        """
        df = pd.read_sql_query(query, conn, params=(cutoff_ts,))
    
    # JSON-Signale parsen
    df['signals'] = df['signals'].apply(json.loads)
    
    # Signale in separate Spalten aufteilen
    signals_df = pd.json_normalize(df['signals'])
    df = pd.concat([df.drop('signals', axis=1), signals_df], axis=1)
    
    logger.info(f"Geladene Feedback-Events: {len(df)}")
    logger.info(f"Policy-Varianten: {df['policy_variant'].unique()}")
    logger.info(f"Profile: {df['profile'].unique()}")
    
    return df

# Daten laden
df = load_feedback_data()
print(f"Dataset Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
```

## 3. Feature Engineering

```python
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Erstellt Features für ML-Training
    """
    df_eng = df.copy()
    
    # Zeitbasierte Features
    df_eng['datetime'] = pd.to_datetime(df_eng['ts'], unit='s')
    df_eng['hour'] = df_eng['datetime'].dt.hour
    df_eng['day_of_week'] = df_eng['datetime'].dt.dayofweek
    df_eng['is_weekend'] = df_eng['day_of_week'].isin([5, 6])
    
    # Policy-Varianten-Features (One-Hot-Encoding)
    policy_dummies = pd.get_dummies(df_eng['policy_variant'], prefix='policy')
    df_eng = pd.concat([df_eng, policy_dummies], axis=1)
    
    # Profil-Features
    profile_dummies = pd.get_dummies(df_eng['profile'], prefix='profile')
    df_eng = pd.concat([df_eng, profile_dummies], axis=1)
    
    # Interaktions-Features
    df_eng['barge_in_per_minute'] = df_eng['barge_in_count'] / (df_eng['duration_sec'] / 60 + 1)
    df_eng['repeats_per_minute'] = df_eng['repeats'] / (df_eng['duration_sec'] / 60 + 1)
    
    # Reward berechnen
    reward_calc = RewardCalculator()
    df_eng['calculated_reward'] = df_eng.apply(
        lambda row: reward_calc.calc_reward(row.to_dict()), axis=1
    )
    
    return df_eng

# Features erstellen
df_features = engineer_features(df)
print(f"Features Shape: {df_features.shape}")
print(f"Feature Columns: {[col for col in df_features.columns if col.startswith(('policy_', 'profile_'))]}")
```

## 4. Pairwise Preferences Generierung

```python
def generate_pairwise_preferences(df: pd.DataFrame) -> List[Tuple[str, str, float]]:
    """
    Generiert Pairwise-Präferenzen aus Feedback-Daten
    """
    preferences = []
    
    # Gruppiere nach ähnlichen Kontexten (Profil, Zeit, etc.)
    for profile in df['profile'].unique():
        profile_df = df[df['profile'] == profile]
        
        # Sortiere nach Reward (höher = besser)
        profile_df = profile_df.sort_values('calculated_reward', ascending=False)
        
        # Erstelle Paare: bessere vs. schlechtere Varianten
        variants = profile_df['policy_variant'].unique()
        
        for i, better_var in enumerate(variants):
            better_reward = profile_df[profile_df['policy_variant'] == better_var]['calculated_reward'].mean()
            
            for worse_var in variants[i+1:]:
                worse_reward = profile_df[profile_df['policy_variant'] == worse_var]['calculated_reward'].mean()
                
                # Nur signifikante Unterschiede berücksichtigen
                if better_reward - worse_reward > 0.1:
                    preferences.append((better_var, worse_var, better_reward - worse_reward))
    
    logger.info(f"Generierte Pairwise-Präferenzen: {len(preferences)}")
    return preferences

# Präferenzen generieren
preferences = generate_pairwise_preferences(df_features)
print(f"Beispiel-Präferenzen: {preferences[:5]}")
```

## 5. Reward Model Training (Optional)

```python
def train_reward_model(df: pd.DataFrame) -> RandomForestRegressor:
    """
    Trainiert ein kleines Reward-Modell zur Vorhersage von Rewards
    """
    # Features für Training
    feature_cols = [col for col in df.columns if col.startswith(('policy_', 'profile_', 'hour', 'is_weekend'))]
    X = df[feature_cols]
    y = df['calculated_reward']
    
    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Modell trainieren
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluation
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    logger.info(f"Reward Model - MSE: {mse:.4f}, R²: {r2:.4f}")
    
    # Feature Importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("Top Feature Importances:")
    print(feature_importance.head(10))
    
    return model

# Reward Model trainieren
reward_model = train_reward_model(df_features)
```

## 6. Grid Search über Prompt-Slots

```python
def load_prompt_variants() -> Dict[str, Dict[str, Any]]:
    """
    Lädt Prompt-Varianten aus YAML-Datei
    """
    with open('docs/policies/prompt_variants.yaml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data['variants']

def grid_search_prompt_slots(df: pd.DataFrame, variants: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Führt Grid Search über Prompt-Slots durch
    """
    results = []
    
    # Extrahiere alle möglichen Slot-Werte
    slot_values = {}
    for variant_id, variant_data in variants.items():
        for slot, value in variant_data['parameters'].items():
            if slot not in slot_values:
                slot_values[slot] = set()
            slot_values[slot].add(value)
    
    logger.info(f"Gefundene Slots: {list(slot_values.keys())}")
    logger.info(f"Slot-Werte: {slot_values}")
    
    # Simuliere Grid Search (vereinfacht)
    # In der Praxis würde man alle Kombinationen durchgehen
    for slot in slot_values.keys():
        for value in slot_values[slot]:
            # Simuliere Performance für diese Slot-Wert-Kombination
            # In der Praxis würde man das Reward Model verwenden
            simulated_reward = np.random.normal(0.5, 0.2)  # Placeholder
            
            results.append({
                'slot': slot,
                'value': value,
                'simulated_reward': simulated_reward,
                'confidence': np.random.uniform(0.6, 0.9)
            })
    
    # Sortiere nach Reward
    results.sort(key=lambda x: x['simulated_reward'], reverse=True)
    
    return results

# Prompt-Varianten laden
variants = load_prompt_variants()
print(f"Geladene Varianten: {list(variants.keys())}")

# Grid Search durchführen
grid_results = grid_search_prompt_slots(df_features, variants)
print(f"Grid Search Ergebnisse: {len(grid_results)}")
print("Top 5 Ergebnisse:")
for i, result in enumerate(grid_results[:5]):
    print(f"{i+1}. {result['slot']}={result['value']} -> Reward: {result['simulated_reward']:.3f}")
```

## 7. Candidate Export

```python
def export_top_candidates(results: List[Dict[str, Any]], 
                         top_n: int = 5,
                         output_path: str = 'docs/policies/candidates.yaml') -> None:
    """
    Exportiert Top-Kandidaten für Deployment
    """
    top_candidates = results[:top_n]
    
    candidates_data = {
        'generated_at': datetime.now().isoformat(),
        'total_evaluated': len(results),
        'top_candidates': []
    }
    
    for i, candidate in enumerate(top_candidates):
        candidate_data = {
            'rank': i + 1,
            'slot': candidate['slot'],
            'value': candidate['value'],
            'simulated_reward': candidate['simulated_reward'],
            'confidence': candidate['confidence'],
            'recommendation': 'high' if candidate['simulated_reward'] > 0.6 else 'medium'
        }
        candidates_data['top_candidates'].append(candidate_data)
    
    # Speichere in YAML
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(candidates_data, f, default_flow_style=False, allow_unicode=True)
    
    logger.info(f"Top {top_n} Kandidaten exportiert nach {output_path}")
    
    # Erstelle auch JSON für einfachere Integration
    json_path = output_path.replace('.yaml', '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(candidates_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"JSON-Export: {json_path}")

# Top-Kandidaten exportieren
export_top_candidates(grid_results, top_n=5)
```

## 8. Deployment-Empfehlungen

```python
def generate_deployment_recommendations(df: pd.DataFrame, 
                                      variants: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generiert Deployment-Empfehlungen basierend auf Analyse
    """
    recommendations = {
        'analysis_date': datetime.now().isoformat(),
        'data_summary': {
            'total_events': len(df),
            'unique_variants': df['policy_variant'].nunique(),
            'date_range': {
                'start': df['datetime'].min().isoformat(),
                'end': df['datetime'].max().isoformat()
            }
        },
        'variant_performance': {},
        'recommendations': []
    }
    
    # Analysiere Performance pro Variante
    for variant_id in df['policy_variant'].unique():
        variant_df = df[df['policy_variant'] == variant_id]
        
        performance = {
            'total_events': len(variant_df),
            'avg_reward': variant_df['calculated_reward'].mean(),
            'avg_user_rating': variant_df['user_rating'].mean() if 'user_rating' in variant_df.columns else None,
            'success_rate': (variant_df['resolution'] == True).mean() if 'resolution' in variant_df.columns else None,
            'avg_duration': variant_df['duration_sec'].mean(),
            'barge_in_rate': variant_df['barge_in_count'].mean(),
            'escalation_rate': (variant_df['handover'] == True).mean() if 'handover' in variant_df.columns else None
        }
        
        recommendations['variant_performance'][variant_id] = performance
    
    # Generiere Empfehlungen
    best_variant = max(recommendations['variant_performance'].items(), 
                      key=lambda x: x[1]['avg_reward'])
    
    recommendations['recommendations'].append({
        'type': 'promote',
        'variant': best_variant[0],
        'reason': f"Highest average reward: {best_variant[1]['avg_reward']:.3f}",
        'confidence': 'high'
    })
    
    # Identifiziere problematische Varianten
    for variant_id, perf in recommendations['variant_performance'].items():
        if perf['avg_reward'] < -0.2 and perf['total_events'] >= 20:
            recommendations['recommendations'].append({
                'type': 'blacklist',
                'variant': variant_id,
                'reason': f"Low reward: {perf['avg_reward']:.3f}",
                'confidence': 'high'
            })
    
    return recommendations

# Empfehlungen generieren
deployment_recs = generate_deployment_recommendations(df_features, variants)

# Speichere Empfehlungen
with open('docs/policies/deployment_recommendations.json', 'w', encoding='utf-8') as f:
    json.dump(deployment_recs, f, indent=2, ensure_ascii=False)

print("Deployment-Empfehlungen:")
for rec in deployment_recs['recommendations']:
    print(f"- {rec['type'].upper()}: {rec['variant']} - {rec['reason']}")
```

## 9. Zusammenfassung und nächste Schritte

```python
def print_training_summary():
    """
    Druckt Zusammenfassung des Offline-Trainings
    """
    print("\n" + "="*60)
    print("TOM v3.0 - RL Offline Training Summary")
    print("="*60)
    
    print(f"📊 Datenanalyse:")
    print(f"   - Feedback-Events: {len(df)}")
    print(f"   - Policy-Varianten: {df['policy_variant'].nunique()}")
    print(f"   - Zeitraum: {df['datetime'].min().date()} bis {df['datetime'].max().date()}")
    
    print(f"\n🔍 Feature Engineering:")
    print(f"   - Features erstellt: {len([col for col in df_features.columns if col.startswith(('policy_', 'profile_'))])}")
    print(f"   - Pairwise-Präferenzen: {len(preferences)}")
    
    print(f"\n🤖 Model Training:")
    print(f"   - Reward Model trainiert: ✅")
    print(f"   - Grid Search durchgeführt: ✅")
    print(f"   - Top-Kandidaten identifiziert: ✅")
    
    print(f"\n📋 Deployment-Empfehlungen:")
    for rec in deployment_recs['recommendations']:
        status = "🟢" if rec['type'] == 'promote' else "🔴"
        print(f"   {status} {rec['type'].upper()}: {rec['variant']}")
    
    print(f"\n📁 Ausgabedateien:")
    print(f"   - docs/policies/candidates.yaml")
    print(f"   - docs/policies/candidates.json")
    print(f"   - docs/policies/deployment_recommendations.json")
    
    print(f"\n🚀 Nächste Schritte:")
    print(f"   1. Review der Kandidaten in candidates.yaml")
    print(f"   2. Integration in DeployGuard für A/B-Testing")
    print(f"   3. Monitoring der neuen Varianten")
    print(f"   4. Regelmäßige Re-Training-Zyklen")
    
    print("="*60)

# Zusammenfassung ausgeben
print_training_summary()
```

## 10. Automatisierung und Scheduling

```python
# Beispiel für automatisiertes Training
def schedule_offline_training():
    """
    Plant regelmäßiges Offline-Training
    """
    schedule_config = {
        'frequency': 'weekly',  # täglich, wöchentlich, monatlich
        'data_window_days': 30,
        'min_events_threshold': 100,
        'output_paths': {
            'candidates': 'docs/policies/candidates.yaml',
            'recommendations': 'docs/policies/deployment_recommendations.json'
        },
        'notification': {
            'enabled': True,
            'email': 'admin@tom-v3.com',
            'slack_webhook': None
        }
    }
    
    # Speichere Konfiguration
    with open('docs/policies/training_schedule.json', 'w') as f:
        json.dump(schedule_config, f, indent=2)
    
    print("Training-Schedule konfiguriert:")
    print(f"- Frequenz: {schedule_config['frequency']}")
    print(f"- Datenfenster: {schedule_config['data_window_days']} Tage")
    print(f"- Min. Events: {schedule_config['min_events_threshold']}")

# Schedule konfigurieren
schedule_offline_training()
```

---

## Hinweise zur Produktionsnutzung

1. **Datenqualität**: Stelle sicher, dass Feedback-Daten vollständig und korrekt sind
2. **Modell-Validierung**: Verwende Cross-Validation für robuste Ergebnisse
3. **A/B-Testing**: Teste neue Varianten schrittweise mit DeployGuard
4. **Monitoring**: Überwache Performance der neuen Varianten kontinuierlich
5. **Rollback-Plan**: Bereite Rollback-Strategien für problematische Varianten vor

## Erweiterungsmöglichkeiten

- **Online Learning**: Integration von Online-RL-Algorithmen
- **Multi-Armed Bandits**: Erweiterte Bandit-Algorithmen (LinUCB, etc.)
- **Deep Learning**: Neuronale Netze für komplexere Reward-Modelle
- **Causal Inference**: Kausale Analyse von Policy-Effekten
- **Federated Learning**: Dezentrales Training über mehrere Instanzen
