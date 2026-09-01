import os
import shutil
import json
from datetime import datetime

def organizar_carpeta():
    """Organiza la carpeta del proyecto"""
    
    # Carpetas a crear
    carpetas = [
        'dist',
        'build',
        'backup',
        'docs',
        'assets/icons',
        'assets/images',
        'logs',
        'temp',
        'tests',
    ]
    
    # Crear carpetas
    for carpeta in carpetas:
        os.makedirs(carpeta, exist_ok=True)
        print(f"✅ Carpeta creada: {carpeta}/")
    
    # Crear .gitignore
    with open('.gitignore', 'w', encoding='utf-8') as f:
        f.write("""# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
env/

# PyInstaller
build/
dist/
*.spec

# Archivos temporales
temp/
*.tmp
*.log

# Configuraciones personales
configuraciones.json
flujos.json

# Backup
backup/

# IDE
.vscode/
.idea/
*.swp
""")
    print("✅ .gitignore creado")
    
    # Crear requirements.txt
    with open('requirements.txt', 'w', encoding='utf-8') as f:
        f.write("""selenium>=4.0.0
pandas>=2.0.0
openpyxl>=3.0.0
psutil>=5.9.0
pyinstaller>=6.0.0
""")
    print("✅ requirements.txt creado")
    
    # Crear version.json
    version = {
        "version": "1.0.0",
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "descripcion": "automatización de WEB",
        "autor": "EO"
    }
    with open('version.json', 'w', encoding='utf-8') as f:
        json.dump(version, f, indent=4, ensure_ascii=False)
    print("✅ version.json creado")
    
    # Hacer backup del bot actual
    if os.path.exists('BOT_AutomatismoWeb.py'):
        backup_nombre = f'backup/BOT_AutomatismoWeb_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
        shutil.copy2('BOT_AutomatismoWeb.py', backup_nombre)
        print(f"✅ Backup creado: {backup_nombre}")
    
    print("\n🎉 ¡Carpeta organizada correctamente!")

if __name__ == "__main__":
    organizar_carpeta()