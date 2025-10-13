"""
TOM v3.0 - End-of-Call Feedback Collection
Sammelt Benutzerbewertungen am Ende von Gesprächen für RL-Training
"""

import asyncio
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime

from apps.rl.feedback import store_feedback
from apps.rl.models import create_feedback_event

logger = logging.getLogger(__name__)

class FeedbackCollector:
    """Sammelt Feedback am Ende von Gesprächen"""
    
    def __init__(self):
        self.feedback_patterns = {
            # Bewertung 1-5 erkennen
            'rating': re.compile(r'(?:bewertung|rating|note|sterne|punkte|zahlen?)\s*:?\s*([1-5])', re.IGNORECASE),
            'direct_number': re.compile(r'\b([1-5])\b'),
            'words': {
                '1': ['schrecklich', 'unzufrieden', 'enttäuscht', 'gar nicht', 'überhaupt nicht'],
                '2': ['nicht gut', 'schlecht', 'unzufrieden', 'enttäuscht'],
                '3': ['okay', 'ok', 'mittelmäßig', 'durchschnittlich', 'normal'],
                '4': ['gut', 'zufrieden', 'hilfreich', 'nett'],
                '5': ['sehr gut', 'exzellent', 'perfekt', 'toll', 'super', 'ausgezeichnet']
            }
        }
        
    async def ask_feedback(self, call_id: str, session_context: Dict[str, Any]) -> Optional[int]:
        """
        Fragt den Benutzer nach einer Bewertung 1-5
        Returns: Bewertung (1-5) oder None bei Fehlern
        """
        try:
            # Policy-Variante aus Session-Kontext holen
            policy_variant = session_context.get('policy_variant', 'v1a')
            profile = session_context.get('profile', 'general')
            
            # Feedback-Frage stellen
            feedback_prompt = self._get_feedback_prompt(policy_variant)
            logger.info(f"Stelle Feedback-Frage für Call {call_id}: {feedback_prompt}")
            
            # Hier würde normalerweise TTS/STT stattfinden
            # Für Tests simulieren wir eine Antwort
            user_response = await self._simulate_user_response()
            
            # Bewertung parsen
            rating = self._parse_rating(user_response)
            
            if rating is not None:
                # Feedback-Event erstellen und speichern
                feedback_event = create_feedback_event(
                    call_id=call_id,
                    agent="TOM",
                    profile=profile,
                    policy_variant=policy_variant,
                    user_rating=rating,
                    resolution=True,  # Annahme: Gespräch erfolgreich beendet
                    duration_sec=session_context.get('duration_sec', 0),
                    barge_in_count=session_context.get('barge_in_count', 0),
                    repeats=session_context.get('repeats', 0),
                    handover=False
                )
                
                store_feedback(feedback_event)
                logger.info(f"Feedback gespeichert: Call {call_id}, Rating {rating}")
                return rating
            else:
                logger.warning(f"Konnte Bewertung nicht parsen: {user_response}")
                return None
                
        except Exception as e:
            logger.error(f"Fehler beim Feedback-Sammeln: {e}")
            return None
    
    def _get_feedback_prompt(self, policy_variant: str) -> str:
        """Generiert Feedback-Frage basierend auf Policy-Variante"""
        prompts = {
            'v1a': "Wie würden Sie unsere Unterhaltung bewerten? Geben Sie eine Zahl von 1 bis 5 an.",
            'v1b': "Hat Ihnen unser Gespräch gefallen? Bewerten Sie mich bitte von 1 bis 5.",
            'v2a': "Bewertung 1-5 für die Servicequalität.",
            'v2b': "Wie zufrieden sind Sie mit meiner Hilfe? Bewerten Sie von 1 bis 5.",
            'v3a': "War das hilfreich? Geben Sie mir eine Note von 1 bis 5!",
            'v3b': "Wie war unser Gespräch für Sie? Bewerten Sie bitte von 1 bis 5.",
            'v4a': "Technische Bewertung: 1-5.",
            'v4b': "War alles verständlich? Bewerten Sie von 1 bis 5.",
            'v5a': "Wie war's? 😊 Bewertung 1-5!",
            'v5b': "Bewerten Sie meine Leistung von 1 bis 5.",
            'v6a': "Wie war die Anpassung? Bewertung 1-5.",
            'v6b': "Wie zufrieden sind Sie mit dem Service? Bewertung 1-5."
        }
        return prompts.get(policy_variant, prompts['v1a'])
    
    async def _simulate_user_response(self) -> str:
        """Simuliert Benutzerantwort für Tests"""
        import random
        responses = [
            "Das war sehr gut, 5 Sterne!",
            "Bewertung 4",
            "Okay, 3",
            "Schlecht, nur 2",
            "Gar nicht zufrieden, 1",
            "Super hilfreich!",
            "Mittelmäßig",
            "Exzellent!"
        ]
        return random.choice(responses)
    
    def _parse_rating(self, response: str) -> Optional[int]:
        """
        Parst Bewertung aus Benutzerantwort
        Returns: 1-5 oder None
        """
        if not response:
            return None
            
        response_lower = response.lower().strip()
        
        # Direkte Zahlen suchen
        direct_match = self.feedback_patterns['direct_number'].search(response)
        if direct_match:
            rating = int(direct_match.group(1))
            if 1 <= rating <= 5:
                return rating
        
        # Bewertungsmuster suchen
        rating_match = self.feedback_patterns['rating'].search(response)
        if rating_match:
            rating = int(rating_match.group(1))
            if 1 <= rating <= 5:
                return rating
        
        # Wörter suchen (von höchster zu niedrigster Bewertung)
        for rating_num in ['5', '4', '3', '2', '1']:
            words = self.feedback_patterns['words'][rating_num]
            for word in words:
                if word in response_lower:
                    return int(rating_num)
        
        return None

# Convenience-Funktionen
_feedback_collector: Optional[FeedbackCollector] = None

def _get_feedback_collector() -> FeedbackCollector:
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector

async def ask_feedback(call_id: str, session_context: Dict[str, Any]) -> Optional[int]:
    """Fragt nach Feedback und speichert es"""
    return await _get_feedback_collector().ask_feedback(call_id, session_context)

def parse_rating(response: str) -> Optional[int]:
    """Parst Bewertung aus Text"""
    return _get_feedback_collector()._parse_rating(response)
