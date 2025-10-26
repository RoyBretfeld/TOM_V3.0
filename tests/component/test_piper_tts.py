"""
TOM v3.0 - Piper TTS Component Test (Real-Only)
Testet echte Piper TTS - keine Mocks!
"""

import pytest
import subprocess
import tempfile
import os


pytestmark = [pytest.mark.component, pytest.mark.real_only]


def test_piper_tts_executable_available(ensure_real_env):
    """Testet ob Piper ausführbar ist"""
    result = subprocess.run(
        ['piper', '--version'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, "Piper ist nicht ausführbar"
    logger.info(f"Piper Version: {result.stdout.strip()}")


def test_piper_tts_generates_audio(ensure_real_env, tmp_path):
    """Testet ob Piper echte PCM16-Audio-Dateien generiert"""
    # Test-Text
    test_text = "Hallo, dies ist ein Test mit Piper TTS."
    
    # Modell-Pfad (relativ zu data/models/piper)
    model_dir = os.getenv('PIPER_MODEL_DIR', './data/models/piper')
    model_name = os.getenv('PIPER_VOICE', 'de-DE-thorsten-medium')
    
    # Output-Datei
    output_file = tmp_path / "test_output.wav"
    
    # Piper-Aufruf
    cmd = [
        'piper',
        '--model', f'{model_dir}/{model_name}.onnx',
        '--config-file', f'{model_dir}/{model_name}.onnx.json',
        '--output_file', str(output_file)
    ]
    
    # Text als Input
    result = subprocess.run(
        cmd,
        input=test_text.encode('utf-8'),
        capture_output=True,
        text=True,
        timeout=30
    )
    
    assert result.returncode == 0, f"Piper-Fehler: {result.stderr}"
    assert output_file.exists(), "Ausgabedatei wurde nicht erstellt"
    assert output_file.stat().st_size > 1000, "Ausgabedatei zu klein (< 1KB)"
    
    logger.info(f"Piper generierte {output_file.stat().st_size} Bytes Audio")


def test_piper_tts_pcm16_format(ensure_real_env, tmp_path):
    """Testet ob Piper PCM16-Audio generiert"""
    import wave
    
    test_text = "Test"
    model_dir = os.getenv('PIPER_MODEL_DIR', './data/models/piper')
    model_name = os.getenv('PIPER_VOICE', 'de-DE-thorsten-medium')
    output_file = tmp_path / "test_pcm16.wav"
    
    cmd = [
        'piper',
        '--model', f'{model_dir}/{model_name}.onnx',
        '--config-file', f'{model_dir}/{model_name}.onnx.json',
        '--output_file', str(output_file)
    ]
    
    result = subprocess.run(
        cmd,
        input=test_text.encode('utf-8'),
        capture_output=True,
        timeout=30
    )
    
    assert result.returncode == 0, "Piper-Fehler"
    assert output_file.exists(), "Keine Output-Datei"
    
    # WAV-Format prüfen
    with wave.open(str(output_file), 'rb') as wav:
        assert wav.getnchannels() == 1, "Mono erforderlich"
        assert wav.getsampwidth() == 2, "16-bit erforderlich"
        assert wav.getframerate() in [16000, 22050, 44100], "Sample-Rate ungültig"
    
    logger.info("Piper PCM16-Format korrekt")


import logging
logger = logging.getLogger(__name__)

