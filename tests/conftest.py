"""
TOM v3.0 - Pytest Configuration (Real-Only, No Mocks)
Skip-Tests wenn echte Dependencies fehlen
"""

import os
import shutil
import socket
import pytest
from typing import Callable, Dict


# Availability-Checks für echte Dependencies
REQUIREMENTS: Dict[str, Callable[[], bool]] = {
    'GPU': lambda: shutil.which('nvidia-smi') is not None,
    'OLLAMA': lambda: _check_port_open('localhost', 11434),
    'PIPER': lambda: shutil.which('piper') is not None,
    'FS_WSS': lambda: _check_fs_wss_url(),
    'REDIS': lambda: _check_port_open('localhost', 6379),
    'CHROMADB': lambda: _check_port_open('localhost', 8000),
    'PROMETHEUS': lambda: _check_port_open('localhost', 9090),
}


def _check_port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    """Prüft ob Port offen ist"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except Exception:
        return False


def _check_fs_wss_url() -> bool:
    """Prüft ob FreeSWITCH WSS URL gesetzt ist"""
    url = os.getenv('FS_WSS_URL', '')
    return url.startswith('wss://')


@pytest.fixture(scope='session')
def ensure_real_env(request):
    """Prüft ob echte Dependencies verfügbar sind, skipt sonst"""
    # Marker auslesen
    markers = [m.name for m in request.node.iter_markers()]
    
    # Required Dependencies basierend auf Marker bestimmen
    required = []
    if 'component' in markers:
        required = ['GPU', 'OLLAMA', 'PIPER']
    elif 'integration' in markers:
        required = ['REDIS', 'PROMETHEUS']
    elif 'e2e' in markers:
        required = ['GPU', 'FS_WSS', 'OLLAMA', 'PIPER']
    
    # Verfügbarkeits-Checks
    missing = []
    for dep in required:
        if not REQUIREMENTS.get(dep, lambda: False)():
            missing.append(dep)
    
    # Skip wenn Dependencies fehlen
    if missing:
        pytest.skip(
            f"Real-Only Test: Übersprungen, fehlt: {', '.join(missing)}. "
            f"Um diesen Test auszuführen, benötigst du: {', '.join(required)}"
        )
    
    yield


@pytest.fixture(scope='session')
def cuda_available():
    """Prüft ob CUDA verfügbar ist"""
    try:
        import torch
        if not torch.cuda.is_available():
            pytest.skip("CUDA nicht verfügbar")
        yield torch.cuda.is_available()
    except ImportError:
        pytest.skip("PyTorch nicht installiert")


@pytest.fixture(scope # Ollama-Client verfügbar
def pytest_configure(config):
    """Konfiguriert Pytest für Real-Only Tests"""
    # Warnt wenn Mocks gefunden werden
    if config.getoption('--real-only-check'):
        _warn_about_mocks()


def _warn_about_mocks():
    """Warnung wenn Mocks in echten Tests gefunden werden"""
    import warnings
    warnings.warn(
        "Mock imports in tests/(component|integration|e2e)/ sind verboten! "
        "Verwende pytest skip() statt Mocks."
    )


# Convenience-Fixture für Ollama
@pytest.fixture(scope='session')
def ollama_client(ensure_real_env):
    """Ollama-Client Fixture"""
    try:
        import ollama
        return ollama.Client()
    except ImportError:
        pytest.skip("Ollama nicht installiert")


# Convenience-Fixture für FreeSWITCH
@pytest.fixture(scope='session')
def freeswitch_available(ensure_real_env):
    """Prüft ob FreeSWITCH verfügbar ist"""
    fs_url = os.getenv('FS_WSS_URL', '')
    if not fs_url.startswith('wss://'):
        pytest.skip("FreeSWITCH WSS URL nicht konfiguriert")
    return fs_url

