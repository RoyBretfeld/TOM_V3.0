"""
TOM v3.0 - Realtime-Konfiguration mit Feature-Flags
Dynamische Aktivierung von STT/LLM/TTS-Komponenten
"""

import os
from typing import Literal, Optional
from enum import Enum


class RealtimeMode(Enum):
    """Verfügbare Realtime-Modi"""
    OFF = "off"
    MOCK = "mock"
    PROVIDER = "provider"
    LOCAL = "local"


class RealtimeConfig:
    """Konfiguration für Realtime-Komponenten"""
    
    # STT-Konfiguration
    REALTIME_STT: RealtimeMode = RealtimeMode(
        os.getenv('REALTIME_STT', 'local')
    )
    
    # LLM-Konfiguration  
    REALTIME_LLM: RealtimeMode = RealtimeMode(
        os.getenv('REALTIME_LLM', 'local')
    )
    
    # TTS-Konfiguration
    REALTIME_TTS: RealtimeMode = RealtimeMode(
        os.getenv('REALTIME_TTS', 'local')
    )
    
    # Provider-spezifische Konfiguration
    LLM_PROVIDER_URL: Optional[str] = os.getenv('LLM_PROVIDER_URL')
    LLM_PROVIDER_KEY: Optional[str] = os.getenv('LLM_PROVIDER_KEY')
    LLM_MODEL: str = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
    
    # Azure Speech Services
    AZURE_SPEECH_KEY: Optional[str] = os.getenv('AZURE_SPEECH_KEY')
    AZURE_SPEECH_REGION: Optional[str] = os.getenv('AZURE_SPEECH_REGION')
    AZURE_SPEECH_LANGUAGE: str = os.getenv('AZURE_SPEECH_LANGUAGE', 'de-DE')
    
    # Azure TTS
    AZURE_TTS_KEY: Optional[str] = os.getenv('AZURE_TTS_KEY')
    AZURE_TTS_REGION: Optional[str] = os.getenv('AZURE_TTS_REGION')
    AZURE_TTS_VOICE: str = os.getenv('AZURE_TTS_VOICE', 'de-DE-KatjaNeural')
    
    # TTS-spezifische Konfiguration
    TTS_PIPER_PATH: str = os.getenv('TTS_PIPER_PATH', '/usr/local/bin/piper')
    TTS_VOICE: str = os.getenv('TTS_VOICE', 'de_DE-thorsten-medium')
    
    # Performance-Konfiguration
    MAX_CONCURRENT_STREAMS: int = int(os.getenv('MAX_CONCURRENT_STREAMS', '10'))
    STREAM_TIMEOUT: int = int(os.getenv('STREAM_TIMEOUT', '30'))
    
    # DEV-Flags
    DEV_ALLOW_NO_JWT: bool = os.getenv('DEV_ALLOW_NO_JWT', 'true').lower() == 'true'
    DEV_MOCK_DELAYS: bool = os.getenv('DEV_MOCK_DELAYS', 'true').lower() == 'true'
    DEV_MOCK_DELAY_MS: int = int(os.getenv('DEV_MOCK_DELAY_MS', '50'))


def is_stt_enabled() -> bool:
    """Prüft ob STT aktiviert ist"""
    return RealtimeConfig.REALTIME_STT != RealtimeMode.OFF


def is_llm_enabled() -> bool:
    """Prüft ob LLM aktiviert ist"""
    return RealtimeConfig.REALTIME_LLM != RealtimeMode.OFF


def is_tts_enabled() -> bool:
    """Prüft ob TTS aktiviert ist"""
    return RealtimeConfig.REALTIME_TTS != RealtimeMode.OFF


def is_mock_mode(component: str) -> bool:
    """Prüft ob Komponente im Mock-Modus läuft"""
    if component == 'stt':
        return RealtimeConfig.REALTIME_STT == RealtimeMode.MOCK
    elif component == 'llm':
        return RealtimeConfig.REALTIME_LLM == RealtimeMode.MOCK
    elif component == 'tts':
        return RealtimeConfig.REALTIME_TTS == RealtimeMode.MOCK
    return False


def is_provider_mode(component: str) -> bool:
    """Prüft ob Komponente im Provider-Modus läuft"""
    if component == 'stt':
        return RealtimeConfig.REALTIME_STT == RealtimeMode.PROVIDER
    elif component == 'llm':
        return RealtimeConfig.REALTIME_LLM == RealtimeMode.PROVIDER
    elif component == 'tts':
        return RealtimeConfig.REALTIME_TTS == RealtimeMode.PROVIDER
    return False


def is_local_mode(component: str) -> bool:
    """Prüft ob Komponente im Local-Modus läuft"""
    if component == 'stt':
        return RealtimeConfig.REALTIME_STT == RealtimeMode.LOCAL
    elif component == 'llm':
        return RealtimeConfig.REALTIME_LLM == RealtimeMode.LOCAL
    elif component == 'tts':
        return RealtimeConfig.REALTIME_TTS == RealtimeMode.LOCAL
    return False


def get_config_summary() -> dict:
    """Gibt eine Zusammenfassung der aktuellen Konfiguration zurück"""
    return {
        'stt': {
            'enabled': is_stt_enabled(),
            'mode': RealtimeConfig.REALTIME_STT.value,
            'mock': is_mock_mode('stt'),
            'provider': is_provider_mode('stt'),
            'local': is_local_mode('stt')
        },
        'llm': {
            'enabled': is_llm_enabled(),
            'mode': RealtimeConfig.REALTIME_LLM.value,
            'mock': is_mock_mode('llm'),
            'provider': is_provider_mode('llm'),
            'local': is_local_mode('llm'),
            'provider_url': RealtimeConfig.LLM_PROVIDER_URL,
            'model': RealtimeConfig.LLM_MODEL
        },
        'tts': {
            'enabled': is_tts_enabled(),
            'mode': RealtimeConfig.REALTIME_TTS.value,
            'mock': is_mock_mode('tts'),
            'provider': is_provider_mode('tts'),
            'local': is_local_mode('tts'),
            'piper_path': RealtimeConfig.TTS_PIPER_PATH,
            'voice': RealtimeConfig.TTS_VOICE
        },
        'dev': {
            'allow_no_jwt': RealtimeConfig.DEV_ALLOW_NO_JWT,
            'mock_delays': RealtimeConfig.DEV_MOCK_DELAYS,
            'mock_delay_ms': RealtimeConfig.DEV_MOCK_DELAY_MS
        },
        'performance': {
            'max_concurrent_streams': RealtimeConfig.MAX_CONCURRENT_STREAMS,
            'stream_timeout': RealtimeConfig.STREAM_TIMEOUT
        }
    }


def validate_config() -> list[str]:
    """Validiert die Konfiguration und gibt Warnungen zurück"""
    warnings = []
    
    # Provider-Modus ohne URL/Key
    if is_provider_mode('llm') and not RealtimeConfig.LLM_PROVIDER_URL:
        warnings.append("LLM Provider-Modus aktiviert, aber LLM_PROVIDER_URL nicht gesetzt")
    
    if is_provider_mode('llm') and not RealtimeConfig.LLM_PROVIDER_KEY:
        warnings.append("LLM Provider-Modus aktiviert, aber LLM_PROVIDER_KEY nicht gesetzt")
    
    # Local-Modus ohne Pfad
    if is_local_mode('tts') and not os.path.exists(RealtimeConfig.TTS_PIPER_PATH):
        warnings.append(f"TTS Local-Modus aktiviert, aber Piper nicht gefunden: {RealtimeConfig.TTS_PIPER_PATH}")
    
    # DEV-Flags in Produktion
    if RealtimeConfig.DEV_ALLOW_NO_JWT:
        warnings.append("DEV_ALLOW_NO_JWT ist aktiviert - nur für Entwicklung verwenden!")
    
    return warnings


# Globale Instanz für einfachen Zugriff
config = RealtimeConfig()
