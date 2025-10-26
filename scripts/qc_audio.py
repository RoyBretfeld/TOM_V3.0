#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Audio Qualitätsprüfung (QC)
Objektive Analyse von Mikrofonaufnahmen
"""

import sys
import json
import wave
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def analyze_audio_quality(wav_path: str) -> dict:
    """
    Audio-Qualität analysieren
    
    Args:
        wav_path: Pfad zur WAV-Datei
        
    Returns:
        dict: Qualitätsmetriken und Empfehlungen
    """
    try:
        # WAV-Datei öffnen und validieren
        with wave.open(wav_path, "rb") as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            n_frames = wf.getnframes()
            
            # Validierung
            if sample_rate != 16000:
                raise ValueError(f"Unerwartete Sample-Rate: {sample_rate} (erwartet: 16000)")
            if channels != 1:
                raise ValueError(f"Unerwartete Kanalanzahl: {channels} (erwartet: 1)")
            if sample_width != 2:
                raise ValueError(f"Unerwartete Sample-Breite: {sample_width} (erwartet: 2)")
            
            # Audio-Daten lesen
            frames = wf.readframes(n_frames)
        
        # Zu numpy-Array konvertieren
        audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
        
        if len(audio_data) == 0:
            return {
                "error": "Leere Audio-Datei",
                "advice": ["Datei ist leer oder korrupt"]
            }
        
        # Basis-Metriken berechnen
        rms = float(np.sqrt(np.mean(audio_data**2)))
        peak = float(np.max(np.abs(audio_data)))
        dc_offset = float(np.mean(audio_data))
        
        # Clipping-Analyse
        clip_threshold = 32760  # 99.9% von 32767
        clipped_samples = np.sum(np.abs(audio_data) >= clip_threshold)
        clip_ratio = float(clipped_samples / len(audio_data))
        
        # SNR-Schätzung (High-Pass-Filter für Rauschschätzung)
        # Einfacher High-Pass-Filter (401-Tap Moving Average)
        hp_filter = np.ones(401) / 401
        filtered_audio = audio_data - np.convolve(audio_data, hp_filter, mode='same')
        
        # Rauschschätzung
        noise_level = float(np.sqrt(np.mean(filtered_audio**2)) + 1e-6)
        signal_level = rms + 1e-6
        snr_db = float(20 * np.log10(signal_level / noise_level))
        
        # Dynamik-Analyse
        dynamic_range = float(20 * np.log10(peak / (rms + 1e-6)))
        
        # Empfehlungen generieren
        advice = []
        
        # Clipping-Check
        if clip_ratio > 0.001:
            advice.append(f"⚠️ Clipping erkannt: {clip_ratio:.4f} ({clipped_samples} Samples)")
        else:
            advice.append("✅ Kein Clipping")
        
        # Level-Check
        if rms < 300:
            advice.append("⚠️ Mikrofon zu leise - näher sprechen oder Gain erhöhen")
        elif rms > 9000:
            advice.append("⚠️ Mikrofon zu laut - weiter weg oder Gain reduzieren")
        else:
            advice.append("✅ Mikrofon-Level optimal")
        
        # DC-Offset-Check
        if abs(dc_offset) > 200:
            advice.append(f"⚠️ DC-Offset hoch: {dc_offset:.1f}")
        else:
            advice.append("✅ DC-Offset OK")
        
        # SNR-Check
        if snr_db > 20:
            advice.append("✅ Signal-Rausch-Verhältnis gut")
        elif snr_db > 10:
            advice.append("⚠️ SNR schwach - Umgebung zu laut")
        else:
            advice.append("❌ SNR sehr schlecht - sehr laute Umgebung")
        
        # Dynamik-Check
        if dynamic_range > 20:
            advice.append("✅ Gute Dynamik")
        else:
            advice.append("⚠️ Niedrige Dynamik - möglicherweise Kompression")
        
        # Gesamtbewertung
        quality_score = 100
        if clip_ratio > 0.001:
            quality_score -= 30
        if rms < 300 or rms > 9000:
            quality_score -= 20
        if abs(dc_offset) > 200:
            quality_score -= 15
        if snr_db < 20:
            quality_score -= 25
        if dynamic_range < 20:
            quality_score -= 10
        
        quality_score = max(0, quality_score)
        
        if quality_score >= 80:
            overall_quality = "Sehr gut"
        elif quality_score >= 60:
            overall_quality = "Gut"
        elif quality_score >= 40:
            overall_quality = "Befriedigend"
        else:
            overall_quality = "Schlecht"
        
        return {
            "file_info": {
                "path": wav_path,
                "duration_sec": len(audio_data) / 16000,
                "samples": len(audio_data),
                "sample_rate": sample_rate,
                "channels": channels,
                "bit_depth": sample_width * 8
            },
            "metrics": {
                "rms": round(rms, 1),
                "peak": round(peak, 1),
                "dc_offset": round(dc_offset, 1),
                "clip_ratio": round(clip_ratio, 6),
                "clipped_samples": int(clipped_samples),
                "snr_db_est": round(snr_db, 1),
                "dynamic_range_db": round(dynamic_range, 1),
                "noise_level": round(noise_level, 1)
            },
            "quality": {
                "score": quality_score,
                "rating": overall_quality
            },
            "advice": advice,
            "targets": {
                "rms_min": 300,
                "rms_max": 9000,
                "clip_threshold": 0.001,
                "dc_threshold": 200,
                "snr_min": 20,
                "dynamic_range_min": 20
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "advice": [f"Fehler bei der Analyse: {e}"]
        }


def main():
    """CLI-Hauptfunktion"""
    if len(sys.argv) != 2:
        print("Verwendung: python qc_audio.py <wav_file>")
        print("Beispiel: python qc_audio.py data/recordings/call-001/call-001.wav")
        sys.exit(1)
    
    wav_path = sys.argv[1]
    
    if not Path(wav_path).exists():
        print(f"Fehler: Datei nicht gefunden: {wav_path}")
        sys.exit(1)
    
    # Analyse durchführen
    result = analyze_audio_quality(wav_path)
    
    # JSON-Output
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
