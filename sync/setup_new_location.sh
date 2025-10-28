#!/bin/bash
# TOM v3.0 - Setup Script für neue Standorte (Linux/Mac)
# Setzt Virtual Environment auf und installiert Dependencies

set -e

echo "===== TOM v3.0 Setup ====="
echo ""

# Prüfe ob wir im Projekt-Verzeichnis sind
if [ ! -f "requirements.txt" ]; then
    echo "FEHLER: requirements.txt nicht gefunden!"
    echo "Bitte im Projekt-Root-Verzeichnis ausführen."
    exit 1
fi

# Prüfe Python
if ! command -v python3 &> /dev/null; then
    echo "FEHLER: python3 nicht gefunden!"
    echo "Bitte Python 3.10+ installieren."
    exit 1
fi

echo "Python: $(python3 --version)"
echo ""

# Virtual Environment erstellen
if [ -d ".venv" ]; then
    echo "Virtual Environment existiert bereits (.venv/)"
    echo "Loeschen und neu erstellen? (j/N)"
    read -r response
    if [[ "$response" == "j" || "$response" == "J" ]]; then
        rm -rf .venv
        echo "Virtual Environment entfernt."
    fi
fi

if [ ! -d ".venv" ]; then
    echo "Erstelle Virtual Environment..."
    python3 -m venv .venv
    echo "✓ Virtual Environment erstellt"
fi

# Aktivieren
echo ""
echo "Aktiviere Virtual Environment..."
source .venv/bin/activate

# Dependencies installieren
echo ""
echo "Installiere Dependencies..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo ""
echo "✓ Dependencies installiert"
echo ""

# Environment-Datei prüfen
if [ ! -f ".env" ]; then
    if [ -f "env.work.example" ]; then
        cp env.work.example .env
        echo "✓ .env erstellt von env.work.example"
        echo "  Bitte .env anpassen (Editor: nano .env)"
    else
        echo "WARNUNG: Keine .env Datei gefunden!"
        echo "Bitte manuell erstellen."
    fi
fi

# Tests
echo ""
echo "Fuehre Unit-Tests aus..."
if pytest tests/unit -v --tb=short; then
    echo ""
    echo "✓ Tests erfolgreich"
else
    echo ""
    echo "WARNUNG: Einige Tests sind fehlgeschlagen"
fi

echo ""
echo "===== SETUP ABGESCHLOSSEN ====="
echo ""
echo "Naechste Schritte:"
echo "  1. .env anpassen: nano .env"
echo "  2. Tests ausfuehren: pytest tests/unit -v"
echo "  3. Git Remote prüfen: git remote -v"
echo ""

