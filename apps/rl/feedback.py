"""
TOM v3.0 - RL Feedback Collector
Sichere Speicherung und Validierung von Feedback-Events für RL-Training
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib

from .models import FeedbackEvent, FeedbackSignals, anonymize_feedback_event


class FeedbackCollector:
    """Sammelt und speichert Feedback-Events für RL-Training"""
    
    def __init__(self, db_path: str = "data/rl/feedback.db"):
        """
        Initialisiert den Feedback Collector
        
        Args:
            db_path: Pfad zur SQLite-Datenbank
        """
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(f"{__name__}.FeedbackCollector")
        
        # Datenbank-Verzeichnis erstellen
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Datenbank initialisieren
        self._init_database()
    
    def _init_database(self):
        """Initialisiert die SQLite-Datenbank mit Feedback-Tabelle"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Feedback-Tabelle erstellen
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        call_id TEXT NOT NULL,
                        ts REAL NOT NULL,
                        agent TEXT NOT NULL,
                        profile TEXT NOT NULL,
                        policy_variant TEXT NOT NULL,
                        signals TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        anonymized BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Indizes für bessere Performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_call_id 
                    ON feedback(call_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_policy_variant 
                    ON feedback(policy_variant)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_ts 
                    ON feedback(ts)
                """)
                
                conn.commit()
                self.logger.info(f"Feedback-Datenbank initialisiert: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"Fehler bei Datenbank-Initialisierung: {e}")
            raise
    
    def store_feedback(self, event: Dict[str, Any]) -> bool:
        """
        Speichert ein Feedback-Event in der Datenbank
        
        Args:
            event: Feedback-Event Dictionary
            
        Returns:
            True wenn erfolgreich gespeichert, False bei Fehler
        """
        try:
            # Event validieren
            feedback_event = FeedbackEvent(**event)
            
            # Event anonymisieren für sichere Speicherung
            anonymized_event = anonymize_feedback_event(feedback_event)
            
            # In Datenbank speichern
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO feedback (
                        call_id, ts, agent, profile, policy_variant, 
                        signals, anonymized
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    anonymized_event['call_id'],
                    anonymized_event['ts'],
                    anonymized_event['agent'],
                    anonymized_event['profile'],
                    anonymized_event['policy_variant'],
                    json.dumps(anonymized_event['signals']),
                    True
                ))
                
                conn.commit()
                
                self.logger.info(f"Feedback gespeichert: {anonymized_event['call_id']}")
                return True
                
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern des Feedback-Events: {e}")
            return False
    
    def get_feedback_by_policy(self, policy_variant: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Holt Feedback-Events für eine bestimmte Policy-Variante
        
        Args:
            policy_variant: Policy-Variante (z.B. 'v1a')
            limit: Maximale Anzahl Events
            
        Returns:
            Liste von Feedback-Events
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT call_id, ts, agent, profile, policy_variant, signals
                    FROM feedback 
                    WHERE policy_variant = ? 
                    ORDER BY ts DESC 
                    LIMIT ?
                """, (policy_variant, limit))
                
                events = []
                for row in cursor.fetchall():
                    event = dict(row)
                    event['signals'] = json.loads(event['signals'])
                    events.append(event)
                
                return events
                
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der Feedback-Events: {e}")
            return []
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Gibt Statistiken über gespeicherte Feedback-Events zurück
        
        Returns:
            Dictionary mit Statistiken
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Gesamtanzahl Events
                cursor.execute("SELECT COUNT(*) FROM feedback")
                total_events = cursor.fetchone()[0]
                
                # Events pro Policy-Variante
                cursor.execute("""
                    SELECT policy_variant, COUNT(*) 
                    FROM feedback 
                    GROUP BY policy_variant
                """)
                policy_stats = dict(cursor.fetchall())
                
                # Events pro Profil
                cursor.execute("""
                    SELECT profile, COUNT(*) 
                    FROM feedback 
                    GROUP BY profile
                """)
                profile_stats = dict(cursor.fetchall())
                
                # Neueste Events
                cursor.execute("""
                    SELECT MAX(ts) FROM feedback
                """)
                latest_ts = cursor.fetchone()[0]
                
                return {
                    'total_events': total_events,
                    'policy_stats': policy_stats,
                    'profile_stats': profile_stats,
                    'latest_event_ts': latest_ts,
                    'db_path': str(self.db_path)
                }
                
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der Statistiken: {e}")
            return {}
    
    def cleanup_old_events(self, days: int = 90):
        """
        Löscht alte Feedback-Events (Datenschutz)
        
        Args:
            days: Events älter als X Tage werden gelöscht
        """
        try:
            cutoff_ts = datetime.now().timestamp() - (days * 24 * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM feedback WHERE ts < ?", (cutoff_ts,))
                deleted_count = cursor.rowcount
                
                conn.commit()
                
                self.logger.info(f"Alte Events gelöscht: {deleted_count} (älter als {days} Tage)")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Fehler beim Löschen alter Events: {e}")
            return 0


# Globale Instanz für einfachen Zugriff
feedback_collector = FeedbackCollector()


def store_feedback(event: Dict[str, Any]) -> bool:
    """
    Convenience-Funktion zum Speichern von Feedback-Events
    
    Args:
        event: Feedback-Event Dictionary
        
    Returns:
        True wenn erfolgreich gespeichert
    """
    return feedback_collector.store_feedback(event)


def get_feedback_stats() -> Dict[str, Any]:
    """
    Convenience-Funktion für Feedback-Statistiken
    
    Returns:
        Dictionary mit Statistiken
    """
    return feedback_collector.get_feedback_stats()
