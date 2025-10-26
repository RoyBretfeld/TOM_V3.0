"""
TOM v3.0 - PCM Audio Utilities
PCMU/G.711 <-> PCM16 Konvertierung & Resampling
"""

import logging
import struct
from typing import Tuple
import numpy as np

logger = logging.getLogger(__name__)


def pcmu_to_pcm16(pcmu_bytes: bytes) -> bytes:
    """Konvertiert PCMU (G.711 μ-law) zu PCM16 (Linear)"""
    pcmu_array = np.frombuffer(pcmu_bytes, dtype=np.uint8)
    pcmu_ulaw = pcmu_array.astype(np.int16) - 0x80
    
    # μ-law Dekodierung
    sign = (pcmu_ulaw & 0x80) != 0
    exponent = (pcmu_ulaw >> 4) & 0x07
    mantissa = pcmu_ulaw & 0x0F
    
    pcm16_samples = np.zeros_like(pcmu_ulaw, dtype=np.int16)
    
    pcm16_samples = (
        ((mantissa << (exponent + 3)) + (8 << exponent) + 4) >> 1
    )
    pcm16_samples = np.where(sign, -pcm16_samples, pcm16_samples)
    pcm16_samples = pcm16_samples.astype(np.int16)
    
    return pcm16_samples.tobytes()


def resample_8k_to_16k(audio_8k: bytes) -> bytes:
    """Resamplet PCM16 8kHz -> 16kHz (Linear Interpolation)"""
    audio_array = np.frombuffer(audio_8k, dtype=np.int16)
    
    # Linear Interpolation
    indices = np.arange(0, len(audio_array), 0.5)
    resampled = np.interp(indices, np.arange(len(audio_array)), audio_array)
    
    return resampled.astype(np.int16).tobytes()


def create_20ms_frame(audio_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Erstellt 20ms Audio-Frame (320 Samples @ 16kHz)"""
    samples_per_frame = int(sample_rate * 0.02)  # 20ms
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    
    # Frame auf volle Länge bringen
    if len(audio_array) < samples_per_frame:
        # Padding mit Silence
        padding = np.zeros(samples_per_frame - len(audio_array), dtype=np.int16)
        frame = np.concatenate([audio_array, padding])
    else:
        frame = audio_array[:samples_per_frame]
    
    return frame.tobytes()


class JitterBuffer:
    """Jitter Buffer für Audio-Frames (20ms)"""
    
    def __init__(self, max_delay_ms: int = 100):
        self.max_delay_ms = max_delay_ms
        self.frame_size_ms = 20
        self.buffer = []
        self.last_timestamp = 0
        
    def add_frame(self, audio_data: bytes, timestamp: float) -> None:
        """Frame hinzufügen"""
        self.buffer.append({
            'audio': audio_data,
            'timestamp': timestamp
        })
        
    def get_frame(self) -> Tuple[bytes, float]:
        """Frame abrufen (mit Jitter-Kompensation)"""
        if not self.buffer:
            return None, 0.0
            
        frame = self.buffer.pop(0)
        return frame['audio'], frame['timestamp']
    
    def flush(self) -> None:
        """Buffer leeren"""
        self.buffer = []

