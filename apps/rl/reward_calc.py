"""
TOM v3.0 - RL Reward Calculator
Berechnet normalisierte Rewards aus Feedback-Signalen für RL-Training
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import math


@dataclass
class RewardConfig:
    """Konfiguration für Reward-Berechnung"""
    
    # Gewichtungen für verschiedene Signale
    resolution_weight: float = 0.6
    rating_weight: float = 0.2
    barge_in_weight: float = -0.1
    repeats_weight: float = -0.1
    handover_weight: float = -0.1
    
    # Duration-Bonus (optimal bei 180 Sekunden)
    optimal_duration_sec: float = 180.0
    duration_bonus_max: float = 0.2
    
    # Clamp-Werte
    min_reward: float = -1.0
    max_reward: float = 1.0


class RewardCalculator:
    """Berechnet Rewards aus Feedback-Signalen"""
    
    def __init__(self, config: Optional[RewardConfig] = None):
        """
        Initialisiert den Reward Calculator
        
        Args:
            config: Reward-Konfiguration (optional)
        """
        self.config = config or RewardConfig()
        self.logger = logging.getLogger(f"{__name__}.RewardCalculator")
    
    def calc_reward(self, signals: Dict[str, Any]) -> float:
        """
        Berechnet den Reward aus Feedback-Signalen
        
        Args:
            signals: Dictionary mit Feedback-Signalen
            
        Returns:
            Normalisierter Reward zwischen -1 und +1
        """
        try:
            # Basis-Reward
            reward = 0.0
            
            # 1. Resolution Success (0.6 Gewichtung)
            resolution = signals.get('resolution', False)
            if resolution:
                reward += self.config.resolution_weight
            
            # 2. User Rating (0.2 Gewichtung, 1-5 → -1 bis +1)
            user_rating = signals.get('user_rating')
            if user_rating is not None:
                rating_reward = (user_rating - 3) / 2  # 1→-1, 3→0, 5→+1
                reward += self.config.rating_weight * rating_reward
            
            # 3. Barge-In Penalty (-0.1 Gewichtung, max 3 Barge-Ins)
            barge_in_count = signals.get('barge_in_count', 0)
            barge_in_penalty = min(barge_in_count, 3) / 3
            reward += self.config.barge_in_weight * barge_in_penalty
            
            # 4. Repeats Penalty (-0.1 Gewichtung, max 3 Repeats)
            repeats = signals.get('repeats', 0)
            repeats_penalty = min(repeats, 3) / 3
            reward += self.config.repeats_weight * repeats_penalty
            
            # 5. Handover Penalty (-0.1 Gewichtung)
            handover = signals.get('handover', False)
            if handover:
                reward += self.config.handover_weight
            
            # 6. Duration Bonus (optimal bei 180 Sekunden)
            duration_sec = signals.get('duration_sec', 0.0)
            duration_bonus = self._calc_duration_bonus(duration_sec)
            reward += duration_bonus
            
            # 7. Clamp auf [-1, +1]
            reward = max(self.config.min_reward, min(self.config.max_reward, reward))
            
            self.logger.debug(f"Reward berechnet: {reward:.3f} aus Signalen: {signals}")
            return reward
            
        except Exception as e:
            self.logger.error(f"Fehler bei Reward-Berechnung: {e}")
            return 0.0  # Neutraler Reward bei Fehlern
    
    def _calc_duration_bonus(self, duration_sec: float) -> float:
        """
        Berechnet Duration-Bonus basierend auf optimaler Gesprächsdauer
        
        Args:
            duration_sec: Gesprächsdauer in Sekunden
            
        Returns:
            Duration-Bonus zwischen -0.2 und +0.2
        """
        if duration_sec <= 0:
            return 0.0
        
        # Optimal bei 180 Sekunden (3 Minuten)
        optimal = self.config.optimal_duration_sec
        max_bonus = self.config.duration_bonus_max
        
        # Berechne Abweichung von optimaler Dauer
        deviation = abs(duration_sec - optimal)
        
        # Bonus nimmt linear ab mit der Abweichung
        # Bei 0 Sekunden Abweichung: +0.2
        # Bei 180 Sekunden Abweichung: 0
        # Bei 360+ Sekunden Abweichung: -0.2
        bonus = max_bonus * (1 - deviation / optimal)
        
        # Clamp auf [-0.2, +0.2]
        return max(-max_bonus, min(max_bonus, bonus))
    
    def calc_reward_components(self, signals: Dict[str, Any]) -> Dict[str, float]:
        """
        Berechnet Reward-Komponenten für Debugging/Analyse
        
        Args:
            signals: Dictionary mit Feedback-Signalen
            
        Returns:
            Dictionary mit einzelnen Reward-Komponenten
        """
        components = {}
        
        # Resolution Component
        resolution = signals.get('resolution', False)
        components['resolution'] = self.config.resolution_weight if resolution else 0.0
        
        # Rating Component
        user_rating = signals.get('user_rating')
        if user_rating is not None:
            rating_reward = (user_rating - 3) / 2
            components['rating'] = self.config.rating_weight * rating_reward
        else:
            components['rating'] = 0.0
        
        # Barge-In Component
        barge_in_count = signals.get('barge_in_count', 0)
        barge_in_penalty = min(barge_in_count, 3) / 3
        components['barge_in'] = self.config.barge_in_weight * barge_in_penalty
        
        # Repeats Component
        repeats = signals.get('repeats', 0)
        repeats_penalty = min(repeats, 3) / 3
        components['repeats'] = self.config.repeats_weight * repeats_penalty
        
        # Handover Component
        handover = signals.get('handover', False)
        components['handover'] = self.config.handover_weight if handover else 0.0
        
        # Duration Component
        duration_sec = signals.get('duration_sec', 0.0)
        components['duration'] = self._calc_duration_bonus(duration_sec)
        
        # Total Reward
        total_reward = sum(components.values())
        components['total'] = max(self.config.min_reward, min(self.config.max_reward, total_reward))
        
        return components
    
    def get_reward_stats(self, rewards: list[float]) -> Dict[str, float]:
        """
        Berechnet Statistiken für eine Liste von Rewards
        
        Args:
            rewards: Liste von Reward-Werten
            
        Returns:
            Dictionary mit Statistiken
        """
        if not rewards:
            return {
                'count': 0,
                'mean': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'p25': 0.0,
                'p50': 0.0,
                'p75': 0.0
            }
        
        sorted_rewards = sorted(rewards)
        n = len(rewards)
        
        return {
            'count': n,
            'mean': sum(rewards) / n,
            'std': math.sqrt(sum((r - sum(rewards) / n) ** 2 for r in rewards) / n),
            'min': min(rewards),
            'max': max(rewards),
            'p25': sorted_rewards[int(0.25 * n)] if n > 0 else 0.0,
            'p50': sorted_rewards[int(0.5 * n)] if n > 0 else 0.0,
            'p75': sorted_rewards[int(0.75 * n)] if n > 0 else 0.0
        }


# Globale Instanz für einfachen Zugriff
reward_calculator = RewardCalculator()


def calc_reward(signals: Dict[str, Any]) -> float:
    """
    Convenience-Funktion zum Berechnen von Rewards
    
    Args:
        signals: Dictionary mit Feedback-Signalen
        
    Returns:
        Normalisierter Reward zwischen -1 und +1
    """
    return reward_calculator.calc_reward(signals)


def calc_reward_components(signals: Dict[str, Any]) -> Dict[str, float]:
    """
    Convenience-Funktion für Reward-Komponenten
    
    Args:
        signals: Dictionary mit Feedback-Signalen
        
    Returns:
        Dictionary mit einzelnen Reward-Komponenten
    """
    return reward_calculator.calc_reward_components(signals)
