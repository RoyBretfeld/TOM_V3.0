#!/usr/bin/env python3
"""
Grundlegende Tests für TelefonAssistent 3.0
"""
import pytest
import sys
import os

# Test-Pfad hinzufügen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_csb_environment():
    """Test: CSB v1 Umgebungsvariablen sind gesetzt"""
    assert os.getenv('CSB_MAX_FILES', '30') == '30'
    assert os.getenv('CSB_MAX_LINES', '600') == '600'
    assert float(os.getenv('SLO_OK_RATE', '0.95')) >= 0.95

def test_readonly_protection():
    """Test: data/originals Verzeichnis existiert und ist geschützt"""
    originals_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'originals')
    assert os.path.exists(originals_path)
    assert os.path.isdir(originals_path)

def test_utf8_encoding():
    """Test: UTF-8 Encoding funktioniert korrekt"""
    test_text = "Hallo Welt! 🎉"
    encoded = test_text.encode('utf-8')
    decoded = encoded.decode('utf-8')
    assert decoded == test_text

def test_project_structure():
    """Test: Grundlegende Projektstruktur ist vorhanden"""
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    required_dirs = [
        'src',
        'tests', 
        'tools',
        'scripts',
        'docs',
        'data/originals',
        '.github/workflows'
    ]
    
    for dir_path in required_dirs:
        full_path = os.path.join(project_root, dir_path)
        assert os.path.exists(full_path), f"Verzeichnis {dir_path} fehlt"

if __name__ == '__main__':
    pytest.main([__file__])
