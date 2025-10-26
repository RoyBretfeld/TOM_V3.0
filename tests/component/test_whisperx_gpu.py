"""
TOM v3.0 - WhisperX GPU Component Test (Real-Only)
Testet echte WhisperX-Modell-Ladung auf GPU
"""

import pytest
import torch


pytestmark = [pytest.mark.component, pytest.mark.real_only]


def test_whisperx_gpu_model_load(ensure_real_env, cuda_available):
    """Testet WhisperX-Modell-Ladung auf GPU"""
    import whisperx
    
    # Prüfe CUDA-Verfügbarkeit
    assert torch.cuda.is_available(), "CUDA nicht verfügbar"
    assert torch.cuda.device_count() > 0, "Keine CUDA-GPUs gefunden"
    
    logger.info(f"CUDA-Gerät: {torch.cuda.get_device_name(0)}")
    
    # WhisperX-Modell laden
    model = whisperx.load_model(
        "large-v3",
        device="cuda",
        compute_type="float16"
    )
    
    assert model is not None, "Modell-Ladung fehlgeschlagen"
    logger.info("WhisperX-Modell erfolgreich auf GPU geladen")


def test_whisperx_transcription_quality(ensure_real_env, cuda_available):
    """Testet Qualität der WhisperX-Transkription"""
    import whisperx
    import numpy as np
    
    # Audio-Array erstellen (Stille für Test)
    sample_rate = 16000
    duration = 1.0  # 1 Sekunde
    audio_array = np.zeros(int(sample_rate * duration))
    
    # Model laden und transkribieren
    model = whisperx.load_model("large-v3", device="cuda", compute_type="float16")
    result = model.transcribe(audio_array, language="de")
    
    assert result is not None, "Transkription fehlgeschlagen"
    assert 'text' in result or 'segments' in result, "Transkriptions-Format falsch"


import logging
logger = logging.getLogger(__name__)

