#!/usr/bin/env python3
"""
TOM v3.0 - Init Project Script

Automatische Projektinitialisierung für TOM v3.0:
- Erstellt alle fehlenden Verzeichnisse
- Generiert __init__.py Dateien für Python-Module
- Validiert die Projektstruktur

CSB v1 Compliance:
- UTF-8 Encoding für alle Dateierstellungen
- Read-Only Schutz für docs/ Verzeichnis
- Validierung der Projektstruktur
"""
import os
import sys
from pathlib import Path

# UTF-8 Encoding sicherstellen
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class ProjectInitializer:
    """
    Projektinitialisierer für TOM v3.0
    """
    
    def __init__(self, project_root: str = None):
        """
        Initialisiert den Projektinitialisierer
        
        Args:
            project_root: Projekt-Root-Verzeichnis
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.created_dirs = []
        self.created_files = []
        
    def create_directory_structure(self):
        """Erstellt die komplette Verzeichnisstruktur"""
        print("📁 Erstelle Verzeichnisstruktur...")
        
        # Definiere alle erforderlichen Verzeichnisse
        directories = [
            # Apps-Verzeichnisse
            'apps/telephony_bridge',
            'apps/realtime',
            'apps/dispatcher',
            'apps/monitor',
            
            # Web-Verzeichnisse
            'web/dashboard',
            
            # Infra-Verzeichnisse
            'infra',
            
            # Test-Verzeichnisse
            'tests/unit',
            'tests/e2e',
            
            # Scripts-Verzeichnisse
            'scripts',
            
            # Data-Verzeichnisse
            'data/runtime',
            
            # Docs-Verzeichnisse (bereits vorhanden)
            'docs',
            
            # Models-Verzeichnisse
            'models/stt',
            'models/tts',
            'models/llm',
            
            # Logs-Verzeichnisse
            'logs',
            
            # Config-Verzeichnisse
            'config'
        ]
        
        for dir_path in directories:
            full_path = self.project_root / dir_path
            
            # Überspringe docs/ (schreibgeschützt)
            if 'docs' in str(full_path) and full_path.exists():
                print(f"   ⚠️ Überspringe schreibgeschütztes Verzeichnis: {dir_path}")
                continue
            
            if not full_path.exists():
                try:
                    full_path.mkdir(parents=True, exist_ok=True)
                    self.created_dirs.append(str(full_path))
                    print(f"   ✅ Erstellt: {dir_path}")
                except Exception as e:
                    print(f"   ❌ Fehler bei {dir_path}: {e}")
            else:
                print(f"   ℹ️ Bereits vorhanden: {dir_path}")
    
    def create_init_files(self):
        """Erstellt __init__.py Dateien für alle Python-Module"""
        print("\n🐍 Erstelle __init__.py Dateien...")
        
        # Python-Module-Verzeichnisse
        python_modules = [
            'apps',
            'apps/telephony_bridge',
            'apps/realtime',
            'apps/dispatcher',
            'apps/monitor',
            'tests',
            'tests/unit',
            'tests/e2e',
            'scripts'
        ]
        
        for module_path in python_modules:
            full_path = self.project_root / module_path
            init_file = full_path / '__init__.py'
            
            if full_path.exists() and not init_file.exists():
                try:
                    # Erstelle __init__.py mit UTF-8 Encoding
                    with open(init_file, 'w', encoding='utf-8') as f:
                        f.write(f'"""TOM v3.0 - {module_path} Module"""\n')
                        f.write(f'# Automatisch generiert von init_project.py\n')
                        f.write(f'# CSB v1 Compliance: UTF-8 Encoding\n\n')
                        f.write(f'__version__ = "3.0.0"\n')
                        f.write(f'__author__ = "TOM v3.0 Team"\n')
                    
                    self.created_files.append(str(init_file))
                    print(f"   ✅ Erstellt: {module_path}/__init__.py")
                    
                except Exception as e:
                    print(f"   ❌ Fehler bei {module_path}/__init__.py: {e}")
            else:
                print(f"   ℹ️ Bereits vorhanden: {module_path}/__init__.py")
    
    def create_basic_files(self):
        """Erstellt grundlegende Projektdateien"""
        print("\n📄 Erstelle grundlegende Projektdateien...")
        
        # requirements.txt für Python-Dependencies
        requirements_file = self.project_root / 'requirements.txt'
        if not requirements_file.exists():
            try:
                with open(requirements_file, 'w', encoding='utf-8') as f:
                    f.write('# TOM v3.0 - Python Dependencies\n')
                    f.write('# CSB v1 Compliance: UTF-8 Encoding\n\n')
                    f.write('# Core Dependencies\n')
                    f.write('pytest>=7.0.0\n')
                    f.write('pytest-cov>=4.0.0\n')
                    f.write('websockets>=11.0.0\n')
                    f.write('redis>=4.5.0\n')
                    f.write('asyncio-mqtt>=0.13.0\n')
                    f.write('prometheus-client>=0.16.0\n')
                    f.write('speech-recognition>=3.10.0\n')
                    f.write('pyttsx3>=2.90\n')
                    f.write('openai>=1.0.0\n')
                    f.write('uvloop>=0.17.0\n')
                    f.write('aiofiles>=23.0.0\n')
                
                self.created_files.append(str(requirements_file))
                print("   ✅ Erstellt: requirements.txt")
                
            except Exception as e:
                print(f"   ❌ Fehler bei requirements.txt: {e}")
        
        # .gitignore
        gitignore_file = self.project_root / '.gitignore'
        if not gitignore_file.exists():
            try:
                with open(gitignore_file, 'w', encoding='utf-8') as f:
                    f.write('# TOM v3.0 - Git Ignore\n')
                    f.write('# CSB v1 Compliance: UTF-8 Encoding\n\n')
                    f.write('# Python\n')
                    f.write('__pycache__/\n')
                    f.write('*.py[cod]\n')
                    f.write('*.so\n')
                    f.write('.Python\n')
                    f.write('env/\n')
                    f.write('venv/\n')
                    f.write('.env\n')
                    f.write('\n# Models\n')
                    f.write('models/*/\n')
                    f.write('!models/*/.gitkeep\n')
                    f.write('\n# Logs\n')
                    f.write('logs/*\n')
                    f.write('*.log\n')
                    f.write('\n# Runtime Data\n')
                    f.write('data/runtime/*\n')
                    f.write('!data/runtime/.gitkeep\n')
                    f.write('\n# IDE\n')
                    f.write('.vscode/\n')
                    f.write('.idea/\n')
                    f.write('*.swp\n')
                    f.write('*.swo\n')
                
                self.created_files.append(str(gitignore_file))
                print("   ✅ Erstellt: .gitignore")
                
            except Exception as e:
                print(f"   ❌ Fehler bei .gitignore: {e}")
    
    def create_gitkeep_files(self):
        """Erstellt .gitkeep Dateien für leere Verzeichnisse"""
        print("\n📌 Erstelle .gitkeep Dateien...")
        
        gitkeep_dirs = [
            'data/runtime',
            'models/stt',
            'models/tts',
            'models/llm',
            'logs',
            'config'
        ]
        
        for dir_path in gitkeep_dirs:
            full_path = self.project_root / dir_path
            gitkeep_file = full_path / '.gitkeep'
            
            if full_path.exists() and not gitkeep_file.exists():
                try:
                    with open(gitkeep_file, 'w', encoding='utf-8') as f:
                        f.write('# TOM v3.0 - Git Keep\n')
                        f.write('# CSB v1 Compliance: UTF-8 Encoding\n')
                        f.write('# Dieses Verzeichnis wird von Git verwaltet\n')
                    
                    self.created_files.append(str(gitkeep_file))
                    print(f"   ✅ Erstellt: {dir_path}/.gitkeep")
                    
                except Exception as e:
                    print(f"   ❌ Fehler bei {dir_path}/.gitkeep: {e}")
    
    def validate_structure(self):
        """Validiert die Projektstruktur"""
        print("\n🔍 Validiere Projektstruktur...")
        
        required_dirs = [
            'apps/telephony_bridge',
            'apps/realtime',
            'apps/dispatcher',
            'apps/monitor',
            'web/dashboard',
            'infra',
            'tests/unit',
            'tests/e2e',
            'scripts',
            'docs',
            'data/runtime'
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            print("   ❌ Fehlende Verzeichnisse:")
            for missing in missing_dirs:
                print(f"      - {missing}")
            return False
        else:
            print("   ✅ Alle erforderlichen Verzeichnisse vorhanden")
            return True
    
    def print_summary(self):
        """Druckt Zusammenfassung der Initialisierung"""
        print("\n📊 Initialisierung abgeschlossen:")
        print(f"   📁 Verzeichnisse erstellt: {len(self.created_dirs)}")
        print(f"   📄 Dateien erstellt: {len(self.created_files)}")
        
        if self.created_dirs:
            print("\n   Erstellte Verzeichnisse:")
            for dir_path in self.created_dirs:
                print(f"      - {dir_path}")
        
        if self.created_files:
            print("\n   Erstellte Dateien:")
            for file_path in self.created_files:
                print(f"      - {file_path}")

def main():
    """Hauptfunktion"""
    print("🚀 TOM v3.0 Projektinitialisierung gestartet")
    
    # Projektinitialisierer erstellen
    initializer = ProjectInitializer()
    
    try:
        # Verzeichnisstruktur erstellen
        initializer.create_directory_structure()
        
        # __init__.py Dateien erstellen
        initializer.create_init_files()
        
        # Grundlegende Dateien erstellen
        initializer.create_basic_files()
        
        # .gitkeep Dateien erstellen
        initializer.create_gitkeep_files()
        
        # Struktur validieren
        structure_valid = initializer.validate_structure()
        
        # Zusammenfassung drucken
        initializer.print_summary()
        
        if structure_valid:
            print("\n🎉 Projektinitialisierung erfolgreich abgeschlossen!")
            print("\n📋 Nächste Schritte:")
            print("   1. Docker-Compose Setup: docker-compose -f infra/docker-compose.realtime.yml up -d")
            print("   2. Dependencies installieren: pip install -r requirements.txt")
            print("   3. Tests ausführen: python -m pytest tests/")
            print("   4. Realtime-Probe: python scripts/realtime_probe.py")
            return 0
        else:
            print("\n⚠️ Projektinitialisierung mit Warnungen abgeschlossen!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Fehler bei der Initialisierung: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
