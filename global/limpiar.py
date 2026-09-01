import os
import shutil

def limpiar_proyecto():
    """Limpia archivos temporales"""
    
    # Carpetas a limpiar
    carpetas_limpiar = [
        'build',
        'temp',
        '__pycache__',
    ]
    
    for carpeta in carpetas_limpiar:
        if os.path.exists(carpeta):
            shutil.rmtree(carpeta)
            print(f"🗑️ Eliminada: {carpeta}/")
    
    # Archivos a eliminar
    archivos_eliminar = [
        '*.spec',
        '*.pyc',
    ]
    
    print("\n✅ Proyecto limpiado")

if __name__ == "__main__":
    limpiar_proyecto()