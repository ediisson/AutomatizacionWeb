"""
🚀 SCRIPT MAESTRO - Deploy completo del bot
Uso: python deploy.py [versión] ["mensaje del commit"]

Ejemplos:
    python deploy.py                          # Versión automática + commit default
    python deploy.py 1.0.1                    # Versión específica
    python deploy.py 1.0.1 "Fix login"       # Versión + mensaje
    python deploy.py --skip-compile           # Solo subir sin compilar
    python deploy.py --skip-github            # Solo compilar sin subir
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime

# ==========================================
# CONFIGURACIÓN
# ==========================================
NOMBRE_BOT = "BOT_AutomatismoWeb"
REPO_URL = "https://github.com/ediisson/AutomatizacionWeb.git"
RAMA = "main"
AUTOR = "EO"

# Rutas
RUTA_SCRIPT = os.path.join("GLOBAL", f"{NOMBRE_BOT}.py")
RUTA_ICONO = os.path.join("assets", "icons", "logoBOT.ico")
RUTA_LOGO = os.path.join("assets", "images", "logoBOT.png")
RUTA_VERSION = "version.json"
RUTA_INFO = "info_bot.json"
RUTA_BACKUP = "backup"

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def imprimir_titulo(texto):
    """Imprime un título formateado"""
    print(f"\n{'='*60}")
    print(f"  {texto}")
    print(f"{'='*60}")

def imprimir_paso(texto):
    """Imprime un paso"""
    print(f"\n  📌 {texto}")

def imprimir_ok(texto):
    """Imprime éxito"""
    print(f"  ✅ {texto}")

def imprimir_error(texto):
    """Imprime error"""
    print(f"  ❌ {texto}")

def imprimir_info(texto):
    """Imprime info"""
    print(f"  ℹ️  {texto}")

def ejecutar_comando(comando, descripcion=""):
    """Ejecuta un comando y muestra el resultado"""
    if descripcion:
        imprimir_paso(descripcion)
    
    resultado = subprocess.run(comando, capture_output=True, text=True, shell=True)
    
    if resultado.returncode == 0:
        return True
    else:
        if resultado.stderr:
            imprimir_error(resultado.stderr[:200])
        return False

def obtener_version_actual():
    """Lee la versión actual desde version.json"""
    try:
        if os.path.exists(RUTA_VERSION):
            with open(RUTA_VERSION, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "1.0.0")
    except:
        pass
    return "1.0.0"

def incrementar_version(version_actual):
    """Incrementa la versión automáticamente"""
    partes = version_actual.split(".")
    if len(partes) == 3:
        mayor, menor, parche = int(partes[0]), int(partes[1]), int(partes[2])
        parche += 1
        return f"{mayor}.{menor}.{parche}"
    return "1.0.0"

def actualizar_version_json(version, mensaje_commit):
    """Actualiza version.json"""
    imprimir_paso(f"Actualizando version.json a v{version}")
    
    version_info = {
        "version": version,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url_descarga": f"{REPO_URL.replace('.git', '')}/releases/download/v{version}/{NOMBRE_BOT}_v{version}.exe",
        "notas": mensaje_commit,
        "autor": AUTOR
    }
    
    with open(RUTA_VERSION, "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=4, ensure_ascii=False)
    
    imprimir_ok(f"version.json actualizado: v{version}")

def actualizar_info_bot(version, mensaje_commit):
    """Actualiza info_bot.json con las mejoras"""
    imprimir_paso("Actualizando info_bot.json")
    
    info = {
        "version": version,
        "como_funciona": [
            "1. Configura tus credenciales en la pestaña Configuración",
            "2. Carga o crea flujos en la pestaña Flujos",
            "3. Prueba los pasos en la pestaña Pruebas",
            "4. Ejecuta la automatización con el botón Ejecutar",
            "5. El bot lee el Excel y procesa cada OT",
            "6. Actualiza el Excel con los resultados"
        ],
        "mejoras": [],
        "proximas_mejoras": [
            "Sistema de actualización automática",
            "Soporte para más navegadores",
            "Reportes en PDF",
            "Programación de tareas"
        ]
    }
    
    # Cargar mejoras existentes
    if os.path.exists(RUTA_INFO):
        try:
            with open(RUTA_INFO, "r", encoding="utf-8") as f:
                info_existente = json.load(f)
                info["mejoras"] = info_existente.get("mejoras", [])
        except:
            pass
    
    # Agregar nueva mejora
    nueva_mejora = {
        "version": version,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "cambios": [mensaje_commit]
    }
    info["mejoras"].insert(0, nueva_mejora)
    
    with open(RUTA_INFO, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=4, ensure_ascii=False)
    
    imprimir_ok("info_bot.json actualizado")

def actualizar_version_en_bot(version):
    """Actualiza la versión en el archivo del bot"""
    imprimir_paso(f"Actualizando versión en {NOMBRE_BOT}.py")
    
    if not os.path.exists(RUTA_SCRIPT):
        imprimir_error(f"No se encontró: {RUTA_SCRIPT}")
        return
    
    with open(RUTA_SCRIPT, "r", encoding="utf-8") as f:
        contenido = f.read()
    
    # Buscar y reemplazar versión
    import re
    patron = r'self\.version\s*=\s*"[^"]*"'
    reemplazo = f'self.version = "{version}"'
    contenido = re.sub(patron, reemplazo, contenido)
    
    with open(RUTA_SCRIPT, "w", encoding="utf-8") as f:
        f.write(contenido)
    
    imprimir_ok(f"Versión actualizada en el bot: v{version}")

def hacer_backup(version):
    """Hace backup del código actual"""
    imprimir_paso("Haciendo backup")
    
    os.makedirs(RUTA_BACKUP, exist_ok=True)
    
    backup_nombre = f"{RUTA_BACKUP}/{NOMBRE_BOT}_v{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    
    if os.path.exists(RUTA_SCRIPT):
        shutil.copy2(RUTA_SCRIPT, backup_nombre)
        imprimir_ok(f"Backup creado: {backup_nombre}")
    else:
        imprimir_error(f"No se encontró: {RUTA_SCRIPT}")

def compilar_bot(version):
    """Compila el bot a .exe"""
    imprimir_paso(f"Compilando {NOMBRE_BOT} v{version}")
    
    if not os.path.exists(RUTA_SCRIPT):
        imprimir_error(f"No se encontró: {RUTA_SCRIPT}")
        return False
    
    # Verificar icono
    comando_icono = []
    if os.path.exists(RUTA_ICONO):
        comando_icono = ["--icon", RUTA_ICONO]
        imprimir_ok("Icono encontrado")
    else:
        imprimir_info("Icono no encontrado, compilando sin icono")
    
    # Verificar logo
    comando_logo = []
    if os.path.exists(RUTA_LOGO):
        comando_logo = ["--add-data", f"{RUTA_LOGO};assets/images"]
    
    # Comando de compilación
    comando = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", f"{NOMBRE_BOT}_v{version}",
    ] + comando_icono + comando_logo + [
        "--add-data", "GLOBAL/configuraciones.json;." if os.path.exists("GLOBAL/configuraciones.json") else "",
        "--add-data", "GLOBAL/flujos.json;." if os.path.exists("GLOBAL/flujos.json") else "",
        RUTA_SCRIPT
    ]
    
    # Limpiar comando de elementos vacíos
    comando = [c for c in comando if c]
    
    imprimir_info("Compilando...")
    if not ejecutar_comando(comando, ""):
        imprimir_error("Error en la compilación")
        return False
    
    imprimir_ok(f"Ejecutable creado: dist/{NOMBRE_BOT}_v{version}.exe")
    return True

def limpiar_temporales():
    """Limpia archivos temporales"""
    imprimir_paso("Limpiando archivos temporales")
    
    carpetas_limpiar = ["build", "temp", "__pycache__"]
    
    for carpeta in carpetas_limpiar:
        if os.path.exists(carpeta):
            shutil.rmtree(carpeta)
            imprimir_ok(f"Eliminada: {carpeta}/")
    
    # Eliminar archivos temporales
    archivos_temporales = [
        f"{NOMBRE_BOT}.spec",
        f"{NOMBRE_BOT}_nuevo.exe",
        "actualizar.bat",
    ]
    
    for archivo in archivos_temporales:
        if os.path.exists(archivo):
            os.remove(archivo)
            imprimir_ok(f"Eliminado: {archivo}")

def subir_github(version, mensaje_commit):
    """Sube todo a GitHub"""
    imprimir_paso("Subiendo a GitHub")
    
    # Verificar git
    if not ejecutar_comando(["git", "--version"], ""):
        imprimir_error("Git no está instalado")
        return False
    
    # Inicializar repo si no existe
    if not os.path.exists(".git"):
        ejecutar_comando(["git", "init"], "Inicializando repo")
    
    # Agregar remote
    resultado = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
    if resultado.returncode != 0:
        ejecutar_comando(["git", "remote", "add", "origin", REPO_URL], "Agregando remote")
    
    # Crear README si no existe
    if not os.path.exists("README.md"):
        crear_readme(version)
    
    # Agregar archivos
    archivos = [
        RUTA_SCRIPT,
        RUTA_VERSION,
        RUTA_INFO,
        "README.md",
        "deploy.py",
    ]
    
    archivos_existentes = [a for a in archivos if os.path.exists(a)]
    ejecutar_comando(["git", "add"] + archivos_existentes, f"Agregando {len(archivos_existentes)} archivos")
    
    # Commit
    ejecutar_comando(["git", "commit", "-m", f"v{version} - {mensaje_commit}"], "Haciendo commit")
    
    # Push
    if not ejecutar_comando(["git", "push", "-u", "origin", RAMA], "Subiendo a GitHub"):
        ejecutar_comando(["git", "push", "--force", "origin", RAMA], "Reintentando con --force")
    
    imprimir_ok("Bot subido a GitHub")

def crear_readme(version):
    """Crea README.md"""
    imprimir_paso("Creando README.md")
    
    readme_content = f"""# 🤖 {NOMBRE_BOT}

Bot para automatizar la asignación de OTs en Consensus.

## 📦 Versión
v{version}

## 🚀 Instalación
1. Descarga el .exe desde [Releases]({REPO_URL.replace('.git', '')}/releases)
2. Ejecuta {NOMBRE_BOT}_v{version}.exe
3. Configura tus credenciales

## 📋 Características
- ✅ Sistema de flujos personalizados
- ✅ Pruebas en tiempo real
- ✅ Lectura automática de Excel
- ✅ Variables dinámicas
- ✅ Copiar/pegar flujos
- ✅ Editor visual de flujos

## 👨‍💻 Desarrollado por
{AUTOR} con ❤️
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    imprimir_ok("README.md creado")

def crear_release(version, mensaje_commit):
    """Crea un release en GitHub"""
    imprimir_paso(f"Creando release v{version}")
    
    exe_path = os.path.join("dist", f"{NOMBRE_BOT}_v{version}.exe")
    
    if not os.path.exists(exe_path):
        imprimir_error(f"No se encontró: {exe_path}")
        return False
    
    comando = [
        "gh", "release", "create", f"v{version}",
        exe_path,
        "--title", f"v{version}",
        "--notes", mensaje_commit
    ]
    
    if ejecutar_comando(comando, "Creando release"):
        imprimir_ok(f"Release v{version} creado")
        return True
    else:
        imprimir_info("GitHub CLI no disponible, crea el release manualmente")
        return False

# ==========================================
# FUNCIÓN PRINCIPAL
# ==========================================

def main():
    """Función principal del deploy"""
    
    imprimir_titulo("🚀 DEPLOY AUTOMÁTICO DEL BOT")
    
    # ==========================================
    # OBTENER PARÁMETROS
    # ==========================================
    skip_compile = "--skip-compile" in sys.argv
    skip_github = "--skip-github" in sys.argv
    
    # Obtener versión
    version_actual = obtener_version_actual()
    version_nueva = None
    
    for arg in sys.argv[1:]:
        if arg[0].isdigit():
            version_nueva = arg
            break
    
    if not version_nueva:
        version_nueva = incrementar_version(version_actual)
    
    # Obtener mensaje del commit
    mensaje_commit = ""
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.startswith('"') or (not arg.startswith("--") and not arg[0].isdigit()):
            mensaje_commit = arg.replace('"', '')
            break
    
    if not mensaje_commit:
        mensaje_commit = input("📝 Mensaje del commit (Enter para default): ").strip()
        if not mensaje_commit:
            mensaje_commit = f"Actualización automática {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # ==========================================
    # MOSTRAR RESUMEN
    # ==========================================
    imprimir_titulo("📋 RESUMEN DEL DEPLOY")
    print(f"  📦 Versión anterior: v{version_actual}")
    print(f"  📦 Nueva versión:    v{version_nueva}")
    print(f"  📝 Commit:           {mensaje_commit}")
    print(f"  🔧 Compilar:         {'Sí' if not skip_compile else 'No'}")
    print(f"  📤 Subir a GitHub:   {'Sí' if not skip_github else 'No'}")
    
    confirmar = input("\n  ¿Continuar? (s/n): ").strip().lower()
    if confirmar != "s" and confirmar != "si":
        imprimir_error("Operación cancelada")
        return
    
    # ==========================================
    # 1. HACER BACKUP
    # ==========================================
    hacer_backup(version_nueva)
    
    # ==========================================
    # 2. ACTUALIZAR VERSIÓN
    # ==========================================
    actualizar_version_json(version_nueva, mensaje_commit)
    actualizar_info_bot(version_nueva, mensaje_commit)
    actualizar_version_en_bot(version_nueva)
    
    # ==========================================
    # 3. COMPILAR
    # ==========================================
    if not skip_compile:
        compilar_bot(version_nueva)
    
    # ==========================================
    # 4. LIMPIAR
    # ==========================================
    limpiar_temporales()
    
    # ==========================================
    # 5. SUBIR A GITHUB
    # ==========================================
    if not skip_github:
        subir_github(version_nueva, mensaje_commit)
        crear_release(version_nueva, mensaje_commit)
    
    # ==========================================
    # 6. RESUMEN FINAL
    # ==========================================
    imprimir_titulo("✅ DEPLOY COMPLETADO")
    print(f"  📦 Versión: v{version_nueva}")
    print(f"  📝 Commit: {mensaje_commit}")
    print(f"  🔗 Repo: {REPO_URL}")
    print(f"  📁 Ejecutable: dist/{NOMBRE_BOT}_v{version_nueva}.exe")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()