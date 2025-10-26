"""
TOM v3.0 - Cost Logger
Kosten-Tracking für Realtime-Calls (informativ)
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Preise (Platzhalter - nur für Tests)
PRICE_STT_PER_SEC = float(os.getenv('PRICE_STT_PER_MIN', '0.030')) / 60
PRICE_TTS_PER_SEC = float(os.getenv('PRICE_TTS_PER_MIN', '0.010')) / 60
PRICE_LLM_PER_SEC = float(os.getenv('PRICE_LLM_PER_MIN', '0.040')) / 60

# Log-Verzeichnis
COST_LOG_DIR = Path("data/cost_logs")
COST_LOG_DIR.mkdir(parents=True, exist_ok=True)


class CostLogger:
    """Kosten-Logger für einzelne Calls"""
    
    def __init__(self):
        self.current_call = None
        
    def start_call(self, call_id: str, backend: str):
        """Startet Kosten-Tracking für Call"""
        self.current_call = {
            'call_id': call_id,
            'backend': backend,
            'start_time': datetime.now().isoformat(),
            'stt_duration_s': 0,
            'llm_duration_s': 0,
            'tts_duration_s': 0
        }
        logger.info(f"Cost tracking started for call {call_id} (backend: {backend})")
        
    def update_stt_duration(self, duration_s: float):
        """Aktualisiert STT-Dauer"""
        if self.current_call:
            self.current_call['stt_duration_s'] += duration_s
            
    def update_llm_duration(self, duration_s: float):
        """Aktualisiert LLM-Dauer"""
        if self.current_call:
            self.current_call['llm_duration_s'] += duration_s
            
    def update_tts_duration(self, duration_s: float):
        """Aktualisiert TTS-Dauer"""
        if self.current_call:
            self.current_call['tts_duration_s'] += duration_s
            
    def end_call(self):
        """Beendet Kosten-Tracking und loggt"""
        if not self.current_call:
            return
            
        # Kosten berechnen
        stt_cost = self.current_call['stt_duration_s'] * PRICE_STT_PER_SEC
        llm_cost = self.current_call['llm_duration_s'] * PRICE_LLM_PER_SEC
        tts_cost = self.current_call['tts_duration_s'] * PRICE_TTS_PER_SEC
        total_cost = stt_cost + llm_cost + tts_cost
        
        self.current_call['end_time'] = datetime.now().isoformat()
        self.current_call['stt_cost_eur'] = stt_cost
        self.current_call['llm_cost_eur'] = llm_cost
        self.current_call['tts_cost_eur'] = tts_cost
        self.current_call['total_cost_eur'] = total_cost
        
        # JSONL-Log
        self._log_to_jsonl(self.current_call)
        
        logger.info(
            f"Call {self.current_call['call_id']} ended: "
            f"cost={total_cost:.4f}€ (STT: {stt_cost:.4f}, LLM: {llm_cost:.4f}, TTS: {tts_cost:.4f})"
        )
        
        # Reset
        call_id = self.current_call['call_id']
        self.current_call = None
        return call_id
    
    def _log_to_jsonl(self, record: dict):
        """Loggt Eintrag in JSONL-Datei"""
        log_file = COST_LOG_DIR / f"costs_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(record) + '\n')


# Globale Instanz
cost_logger = CostLogger()


def start_call(call_id: str, backend: str):
    """Startet Kosten-Tracking"""
    cost_logger.start_call(call_id, backend)


def update_stt_duration(duration_s: float):
    """Aktualisiert STT-Dauer"""
    cost_logger.update_stt_duration(duration_s)


def update_llm_duration(duration_s: float):
    """Aktualisiert LLM-Dauer"""
    cost_logger.update_llm_duration(duration_s)


def update_tts_duration(duration_s: float):
    """Aktualisiert TTS-Dauer"""
    cost_logger.update_tts_duration(duration_s)


def end_call() -> Optional[str]:
    """Beendet Kosten-Tracking"""
    return cost_logger.end_call()

