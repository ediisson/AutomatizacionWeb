import os
import shutil
import subprocess
import json
from datetime import datetime

VERSION = "1.0.0"
NOMBRE_BOT = "BOT_AutomatismoWeb"

def compilar_bot():
    """Compila el bot a .exe"""
    
    # Hacer backup
    backup_dir = "backup"
    os.makedirs(backup_dir, exist_ok=True)
    backup_nombre = f"{backup_dir}/{NOMBRE_BOT}_v{VERSION}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    shutil.copy2(f"{NOMBRE_BOT}.py", backup_nombre)
    print(f"✅ Backup: {backup_nombre}")
    
    # Compilar
    comando = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name', f'{NOMBRE_BOT}_v{VERSION}',
        '--add-data', 'configuraciones.json;.',
        '--add-data', 'flujos.json;.',
        f'{NOMBRE_BOT}.py'
    ]
    
    print(f"🔄 Compilando {NOMBRE_BOT} v{VERSION}...")
    subprocess.run(comando)
    
    print(f"✅ Compilación completada")
    print(f"📁 Ejecutable: dist/{NOMBRE_BOT}_v{VERSION}.exe")

if __name__ == "__main__":
    compilar_bot()