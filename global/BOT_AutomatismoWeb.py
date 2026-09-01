import time
import psutil
import subprocess
import pandas as pd
from openpyxl import load_workbook
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import json
import os
from datetime import datetime
import threading
import re
from enum import Enum
from typing import List, Dict, Any, Optional
import urllib.request

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# OBTENER RUTA DE LA CARPETA DEL SCRIPT
# ==========================================
import sys

if getattr(sys, 'frozen', False):
    # Si es un .exe compilado
    RUTA_BASE = os.path.dirname(sys.executable)
else:
    # Si es un script .py
    RUTA_BASE = os.path.dirname(os.path.abspath(__file__))

# Cambiar al directorio del script
os.chdir(RUTA_BASE)

# Rutas de archivos
RUTA_CONFIGURACIONES = os.path.join(RUTA_BASE, "configuraciones.json")
RUTA_FLUJOS = os.path.join(RUTA_BASE, "flujos.json")
RUTA_INFO_BOT = os.path.join(RUTA_BASE, "info_bot.json")

# ==========================================
# RUTAS DE LOGOS E ICONOS
# ==========================================
# Subir un nivel desde GLOBAL para llegar a AutomatismoWEB
RUTA_PROYECTO = os.path.dirname(RUTA_BASE)

RUTA_ICONO = os.path.join(RUTA_PROYECTO, "assets", "icons", "logoBOT.ico")
RUTA_LOGO = os.path.join(RUTA_PROYECTO, "assets", "images", "logoBOT.png")


# ==========================================
# SISTEMA DE ACTUALIZACIÓN
# ==========================================
VERSION_ACTUAL = "1.0.0"
URL_VERSION = "https://raw.githubusercontent.com/ediisson/AutomatizacionWeb/main/version.json"



def verificar_actualizacion():
    """Verifica si hay una nueva versión en GitHub"""
    try:
        with urllib.request.urlopen(URL_VERSION, timeout=5) as response:
            data = json.loads(response.read().decode())
        
        version_remota = data.get("version", "")
        url_descarga = data.get("url_descarga", "")
        notas = data.get("notas", "")
        
        if version_remota > VERSION_ACTUAL:
            return True, version_remota, url_descarga, notas
        return False, VERSION_ACTUAL, None, None
    except:
        return False, VERSION_ACTUAL, None, None

# ==========================================
#  VARIABLE GLOBAL PARA CONTROLAR DETENCIÓN
# ==========================================
DETENER_EJECUCION = False
DRIVER_ACTUAL = None

# ==========================================
#  CLASES PARA EL SISTEMA DE FLUJOS
# ==========================================


class TipoAccion(Enum):
    CLICK = "click"
    ESCRIBIR = "escribir"
    SELECCIONAR = "seleccionar"
    ESPERAR = "esperar"
    JAVASCRIPT = "javascript"
    VALIDAR = "validar"
    SCROLL = "scroll"
    OBTENER_TEXTO = "obtener_texto"
    SI_EXISTE = "si_existe"
    REPETIR = "repetir"


class SelectorTipo(Enum):
    XPATH = "xpath"
    CSS = "css"
    ID = "id"
    CLASS = "class"
    NAME = "name"
    TAG = "tag"


class Paso:
    def __init__(
        self,
        tipo: TipoAccion,
        selector: str = None,
        selector_tipo: SelectorTipo = SelectorTipo.XPATH,
        valor: str = None,
        segundos: int = 1,
        javascript: str = None,
        descripcion: str = "",
        variable_guardar: str = None,
        condicion: str = None,
        repeticiones: int = 1,
        pasos_condicionales: List["Paso"] = None,
    ):
        self.tipo = tipo
        self.selector = selector
        self.selector_tipo = selector_tipo
        self.valor = valor
        self.segundos = segundos
        self.javascript = javascript
        self.descripcion = descripcion
        self.variable_guardar = variable_guardar
        self.condicion = condicion
        self.repeticiones = repeticiones
        self.pasos_condicionales = pasos_condicionales or []

    def to_dict(self):
        return {
            "tipo": self.tipo.value,
            "selector": self.selector,
            "selector_tipo": self.selector_tipo.value if self.selector_tipo else None,
            "valor": self.valor,
            "segundos": self.segundos,
            "javascript": self.javascript,
            "descripcion": self.descripcion,
            "variable_guardar": self.variable_guardar,
            "condicion": self.condicion,
            "repeticiones": self.repeticiones,
            "pasos_condicionales": [p.to_dict() for p in self.pasos_condicionales],
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            tipo=TipoAccion(data["tipo"]),
            selector=data.get("selector"),
            selector_tipo=(
                SelectorTipo(data["selector_tipo"])
                if data.get("selector_tipo")
                else None
            ),
            valor=data.get("valor"),
            segundos=data.get("segundos", 1),
            javascript=data.get("javascript"),
            descripcion=data.get("descripcion", ""),
            variable_guardar=data.get("variable_guardar"),
            condicion=data.get("condicion"),
            repeticiones=data.get("repeticiones", 1),
            pasos_condicionales=[
                Paso.from_dict(p) for p in data.get("pasos_condicionales", [])
            ],
        )

    def get_by(self):
        mapping = {
            SelectorTipo.XPATH: By.XPATH,
            SelectorTipo.CSS: By.CSS_SELECTOR,
            SelectorTipo.ID: By.ID,
            SelectorTipo.CLASS: By.CLASS_NAME,
            SelectorTipo.NAME: By.NAME,
            SelectorTipo.TAG: By.TAG_NAME,
        }
        return mapping.get(self.selector_tipo, By.XPATH)


# ==========================================
#  FLUJO MANAGER
# ==========================================


class FlujoManager:
    def __init__(self, archivo_flujos=None):
        # Usar ruta absoluta si no se proporciona una
        if archivo_flujos is None:
            self.archivo_flujos = RUTA_FLUJOS  # Ruta global definida arriba
        else:
            self.archivo_flujos = archivo_flujos
        self.flujos = self.cargar_flujos()

    def cargar_flujos(self):
        if os.path.exists(self.archivo_flujos):
            try:
                with open(self.archivo_flujos, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not isinstance(data, dict):
                    print(
                        f"Error: El archivo {self.archivo_flujos} no contiene un diccionario válido"
                    )
                    return {}

                flujos_cargados = {}
                for nombre, flujo_data in data.items():
                    if isinstance(flujo_data, dict):
                        try:
                            flujos_cargados[nombre] = self._parse_flujo(flujo_data)
                        except Exception as e:
                            print(f"Error parseando flujo '{nombre}': {e}")
                    else:
                        print(
                            f"Advertencia: El flujo '{nombre}' no tiene un formato válido"
                        )

                return flujos_cargados

            except json.JSONDecodeError as e:
                print(f"Error decodificando JSON: {e}")
                return {}
            except Exception as e:
                print(f"Error cargando flujos: {e}")
                return {}
        return {}

    def _parse_flujo(self, data):
        if not isinstance(data, dict):
            raise ValueError("El flujo debe ser un diccionario")

        return {
            "nombre": data.get("nombre", ""),
            "descripcion": data.get("descripcion", ""),
            "pasos": [Paso.from_dict(p) for p in data.get("pasos", [])],
            "variables": data.get("variables", {}),
        }

    def guardar_flujo(
        self, nombre: str, descripcion: str, pasos: List[Paso], variables: Dict = None
    ):
        if nombre in self.flujos:
            return False, f"Ya existe un flujo con el nombre '{nombre}'"

        self.flujos[nombre] = {
            "nombre": nombre,
            "descripcion": descripcion,
            "pasos": pasos,
            "variables": variables or {},
        }
        self._guardar_archivo()
        return True, "Flujo guardado exitosamente"

    def actualizar_flujo(
        self, nombre: str, descripcion: str, pasos: List[Paso], variables: Dict = None
    ):
        if nombre not in self.flujos:
            return False, f"No existe el flujo '{nombre}'"

        self.flujos[nombre] = {
            "nombre": nombre,
            "descripcion": descripcion,
            "pasos": pasos,
            "variables": variables or {},
        }
        self._guardar_archivo()
        return True, "Flujo actualizado exitosamente"

    def eliminar_flujo(self, nombre: str):
        if nombre in self.flujos:
            del self.flujos[nombre]
            self._guardar_archivo()
            return True
        return False

    def obtener_flujo(self, nombre: str):
        return self.flujos.get(nombre)

    def listar_flujos(self):
        return list(self.flujos.keys())

    def _guardar_archivo(self):
        try:
            data = {}
            for nombre, flujo in self.flujos.items():
                data[nombre] = {
                    "nombre": flujo["nombre"],
                    "descripcion": flujo["descripcion"],
                    "pasos": [p.to_dict() for p in flujo["pasos"]],
                    "variables": flujo["variables"],
                }

            os.makedirs(
                os.path.dirname(os.path.abspath(self.archivo_flujos)), exist_ok=True
            )
            with open(self.archivo_flujos, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error guardando flujos: {e}")
            return False

    def copiar_flujo(self, nombre_original, nuevo_nombre):
        """Copia un flujo existente con un nuevo nombre"""
        if nombre_original not in self.flujos:
            return False, f"No existe el flujo '{nombre_original}'"

        if nuevo_nombre in self.flujos:
            return False, f"Ya existe un flujo con el nombre '{nuevo_nombre}'"

        # Obtener el flujo original
        flujo_original = self.flujos[nombre_original]

        # Crear copia con nuevo nombre
        self.flujos[nuevo_nombre] = {
            "nombre": nuevo_nombre,
            "descripcion": flujo_original["descripcion"],
            "pasos": [
                Paso.from_dict(p.to_dict()) for p in flujo_original["pasos"]
            ],  # Copia profunda
            "variables": (
                flujo_original["variables"].copy()
                if flujo_original.get("variables")
                else {}
            ),
        }

        self._guardar_archivo()
        return True, f"Flujo copiado como '{nuevo_nombre}'"


# ==========================================
#  MOTOR DE FLUJOS
# ==========================================


class MotorFlujos:
    def __init__(self, driver=None, ui=None, variables_globales=None):
        self.driver = driver
        self.ui = ui
        self.variables = variables_globales or {}
        self.detener = False
        self.wait = None
        self.pasos_ejecutados = 0
        self.pasos_fallidos = 0

        if driver:
            self.wait = WebDriverWait(driver, 20)

    def set_driver(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    def log(self, mensaje, tipo="info"):
        if self.ui:
            self.ui.log(mensaje, tipo)
        else:
            print(f"[{tipo.upper()}] {mensaje}")

    def ejecutar_flujo(self, flujo: Dict, variables_iniciales: Dict = None):
        self.variables.update(variables_iniciales or {})
        self.detener = False
        self.pasos_ejecutados = 0
        self.pasos_fallidos = 0

        if "variables" in flujo:
            self.variables.update(flujo["variables"])

        nombre_flujo = flujo.get("nombre", "Sin nombre")
        self.log(f"🚀 Ejecutando flujo: {nombre_flujo}", "info")

        pasos = flujo.get("pasos", [])
        total = len(pasos)

        if total == 0:
            self.log("⚠️ El flujo no tiene pasos, no hay nada que ejecutar", "warning")
            return True

        for idx, paso in enumerate(pasos, 1):
            if self.detener or DETENER_EJECUCION:
                self.log("🛑 Flujo detenido por el usuario", "stop")
                return False

            desc = paso.descripcion or paso.tipo.value
            self.log(f"📌 Paso {idx}/{total}: {desc}", "info")

            try:
                if self._ejecutar_paso(paso):
                    self.pasos_ejecutados += 1
                else:
                    self.log(f"❌ Falló el paso {idx}: {desc}", "error")
                    self.pasos_fallidos += 1
                    return False
            except Exception as e:
                self.log(f"❌ Error en paso {idx}: {str(e)}", "error")
                self.pasos_fallidos += 1
                return False

        self.log(
            f"✅ Flujo ejecutado exitosamente ({self.pasos_ejecutados} pasos)",
            "success",
        )
        return True

    def _ejecutar_paso(self, paso: Paso) -> bool:
        if paso.tipo in [
            TipoAccion.CLICK,
            TipoAccion.ESCRIBIR,
            TipoAccion.SELECCIONAR,
            TipoAccion.VALIDAR,
            TipoAccion.SCROLL,
            TipoAccion.OBTENER_TEXTO,
            TipoAccion.SI_EXISTE,
        ]:
            if not self.driver:
                self.log("❌ No hay driver disponible para ejecutar este paso", "error")
                return False

        valor = self._reemplazar_variables(paso.valor) if paso.valor else None
        selector = self._reemplazar_variables(paso.selector) if paso.selector else None

        if paso.tipo == TipoAccion.CLICK:
            return self._ejecutar_click(selector, paso.selector_tipo)
        elif paso.tipo == TipoAccion.ESCRIBIR:
            return self._ejecutar_escribir(selector, paso.selector_tipo, valor)
        elif paso.tipo == TipoAccion.SELECCIONAR:
            return self._ejecutar_seleccionar(selector, paso.selector_tipo, valor)
        elif paso.tipo == TipoAccion.ESPERAR:
            for i in range(paso.segundos):
                if self.detener or DETENER_EJECUCION:
                    self.log("🛑 Espera interrumpida por detención", "stop")
                    return False
                time.sleep(1)
            return True
        elif paso.tipo == TipoAccion.JAVASCRIPT:
            return self._ejecutar_javascript(paso.javascript)
        elif paso.tipo == TipoAccion.VALIDAR:
            return self._ejecutar_validar(selector, paso.selector_tipo)
        elif paso.tipo == TipoAccion.SCROLL:
            return self._ejecutar_scroll(selector, paso.selector_tipo)
        elif paso.tipo == TipoAccion.OBTENER_TEXTO:
            return self._ejecutar_obtener_texto(
                selector, paso.selector_tipo, paso.variable_guardar
            )
        elif paso.tipo == TipoAccion.SI_EXISTE:
            return self._ejecutar_si_existe(
                selector, paso.selector_tipo, paso.pasos_condicionales
            )
        elif paso.tipo == TipoAccion.REPETIR:
            for _ in range(paso.repeticiones):
                if self.detener or DETENER_EJECUCION:
                    return False
                for sub_paso in paso.pasos_condicionales:
                    if not self._ejecutar_paso(sub_paso):
                        return False
            return True
        return False

    def _get_by(self, selector_tipo):
        mapping = {
            SelectorTipo.XPATH: By.XPATH,
            SelectorTipo.CSS: By.CSS_SELECTOR,
            SelectorTipo.ID: By.ID,
            SelectorTipo.CLASS: By.CLASS_NAME,
            SelectorTipo.NAME: By.NAME,
            SelectorTipo.TAG: By.TAG_NAME,
        }
        return mapping.get(selector_tipo, By.XPATH)

    def _reemplazar_variables(self, texto):
        if not texto:
            return texto
        for key, value in self.variables.items():
            if value is not None:
                texto = texto.replace(f"{{{key}}}", str(value))
        return texto

    def _ejecutar_click(self, selector, selector_tipo):
        try:
            if not self.driver or not self.wait:
                return False

            by = self._get_by(selector_tipo)
            try:
                elemento = self.wait.until(EC.element_to_be_clickable((by, selector)))
            except:
                elemento = self.wait.until(
                    EC.presence_of_element_located((by, selector))
                )

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", elemento
            )
            time.sleep(0.5)

            try:
                elemento.click()
            except:
                self.driver.execute_script("arguments[0].click();", elemento)

            self.log(f"✅ Click en: {selector[:80]}", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error en click: {str(e)[:100]}", "error")
            return False

    def _ejecutar_escribir(self, selector, selector_tipo, valor):
        try:
            if not self.driver or not self.wait:
                return False

            by = self._get_by(selector_tipo)
            elemento = self.wait.until(EC.presence_of_element_located((by, selector)))
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", elemento
            )
            time.sleep(0.5)
            elemento.clear()
            elemento.send_keys(str(valor) if valor else "")
            self.log(f"✅ Escrito: {str(valor)[:50]}", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error al escribir: {str(e)[:100]}", "error")
            return False

    def _ejecutar_seleccionar(self, selector, selector_tipo, valor):
        try:
            if not self.driver or not self.wait:
                return False

            by = self._get_by(selector_tipo)
            elemento = self.wait.until(EC.presence_of_element_located((by, selector)))
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", elemento
            )
            time.sleep(0.5)
            select = Select(elemento)
            select.select_by_visible_text(str(valor) if valor else "")
            self.log(f"✅ Seleccionado: {str(valor)[:50]}", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error al seleccionar: {str(e)[:100]}", "error")
            return False

    def _ejecutar_javascript(self, javascript):
        try:
            if not self.driver:
                return False

            js = self._reemplazar_variables(javascript)
            self.driver.execute_script(js)
            self.log(f"✅ JavaScript ejecutado", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error en JavaScript: {str(e)[:100]}", "error")
            return False

    def _ejecutar_validar(self, selector, selector_tipo):
        try:
            if not self.driver or not self.wait:
                return False

            by = self._get_by(selector_tipo)
            self.wait.until(EC.presence_of_element_located((by, selector)))
            self.log(f"✅ Elemento validado: {selector[:80]}", "success")
            return True
        except Exception as e:
            self.log(f"❌ Elemento no encontrado: {str(e)[:100]}", "error")
            return False

    def _ejecutar_scroll(self, selector, selector_tipo):
        try:
            if not self.driver or not self.wait:
                return False

            by = self._get_by(selector_tipo)
            elemento = self.wait.until(EC.presence_of_element_located((by, selector)))
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", elemento
            )
            self.log(f"✅ Scroll a: {selector[:80]}", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error en scroll: {str(e)[:100]}", "error")
            return False

    def _ejecutar_obtener_texto(self, selector, selector_tipo, variable_guardar):
        try:
            if not self.driver or not self.wait:
                return False

            by = self._get_by(selector_tipo)
            elemento = self.wait.until(EC.presence_of_element_located((by, selector)))
            texto = elemento.text
            if variable_guardar:
                self.variables[variable_guardar] = texto
            self.log(f"✅ Texto obtenido: {texto[:50]}...", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error al obtener texto: {str(e)[:100]}", "error")
            return False

    def _ejecutar_si_existe(self, selector, selector_tipo, pasos_condicionales):
        try:
            if not self.driver or not self.wait:
                return False

            by = self._get_by(selector_tipo)
            self.wait.until(EC.presence_of_element_located((by, selector)))
            self.log(
                f"✅ Elemento encontrado, ejecutando pasos condicionales", "success"
            )
            for paso in pasos_condicionales:
                if not self._ejecutar_paso(paso):
                    return False
            return True
        except:
            self.log(f"ℹ️ Elemento no encontrado, saltando pasos condicionales", "info")
            return True


# ==========================================
#  CLASE CONFIG MANAGER
# ==========================================


class ConfigManager:
    def __init__(self, config_file=None):
        # Usar ruta absoluta si no se proporciona una
        if config_file is None:
            self.config_file = RUTA_CONFIGURACIONES  # Ruta global
        else:
            self.config_file = config_file
        self.configuraciones = self.cargar_configuraciones()

    def cargar_configuraciones(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error cargando configuraciones: {e}")
                return {}
        return {}

    def guardar_configuraciones(self):
        try:
            os.makedirs(
                os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True
            )
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.configuraciones, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error guardando configuraciones: {e}")
            return False

    def agregar_configuracion(self, nombre, valores):
        if nombre in self.configuraciones:
            return False, "Ya existe una configuración con este nombre"

        campos_requeridos = [
            "USUARIO",
            "PASSWORD",
            "URL_LOGIN",
            "EXCEL_OTPS",
            "BRAVE_PATH",
            "CHROMEDRIVER_PATH",
        ]

        for campo in campos_requeridos:
            if campo not in valores:
                return False, f"Falta el campo: {campo}"

        self.configuraciones[nombre] = valores
        if self.guardar_configuraciones():
            return True, "Configuración guardada exitosamente"
        else:
            return False, "Error al guardar la configuración"

    def eliminar_configuracion(self, nombre):
        if nombre in self.configuraciones:
            del self.configuraciones[nombre]
            self.guardar_configuraciones()
            return True
        return False

    def obtener_configuracion(self, nombre):
        return self.configuraciones.get(nombre, None)

    def listar_configuraciones(self):
        return list(self.configuraciones.keys())


# DialogoPaso (DEBE IR ANTES DE EditorFlujosUI)
class DialogoPaso:
    def __init__(self, parent, editor, paso=None):
        self.editor = editor
        self.resultado = None

        self.ventana = tk.Toplevel(parent)
        self.ventana.title("✏️ Editar Paso")
        self.ventana.geometry("650x600")
        self.ventana.configure(bg="#f0f2f5")
        self.ventana.transient(parent)

        self.tipo_var = tk.StringVar(value=paso.tipo.value if paso else "click")
        self.selector_var = tk.StringVar(value=paso.selector if paso else "")
        self.selector_tipo_var = tk.StringVar(
            value=paso.selector_tipo.value if paso and paso.selector_tipo else "xpath"
        )
        self.valor_var = tk.StringVar(value=paso.valor if paso else "")
        self.segundos_var = tk.StringVar(value=str(paso.segundos) if paso else "1")
        self.javascript_var = tk.StringVar(value=paso.javascript if paso else "")
        self.descripcion_var = tk.StringVar(value=paso.descripcion if paso else "")
        self.variable_guardar_var = tk.StringVar(
            value=paso.variable_guardar if paso else ""
        )

        self._crear_widgets()

        self.ventana.update_idletasks()
        width = self.ventana.winfo_width()
        height = self.ventana.winfo_height()
        x = (self.ventana.winfo_screenwidth() // 2) - (width // 2)
        y = (self.ventana.winfo_screenheight() // 2) - (height // 2)
        self.ventana.geometry(f"{width}x{height}+{x}+{y}")

        parent.wait_window(self.ventana)

    def _crear_widgets(self):
        main_frame = ttk.Frame(self.ventana, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="✏️ Configurar Paso", style="Title.TLabel").pack(
            pady=(0, 15)
        )

        # Tipo de acción
        frame_tipo = ttk.Frame(main_frame)
        frame_tipo.pack(fill=tk.X, pady=5)
        ttk.Label(frame_tipo, text="Tipo de Acción:").pack(side=tk.LEFT, padx=(0, 10))
        self.combo_tipo = ttk.Combobox(
            frame_tipo,
            textvariable=self.tipo_var,
            state="readonly",
            values=[t.value for t in TipoAccion],
            width=25,
        )
        self.combo_tipo.pack(side=tk.LEFT)
        self.combo_tipo.bind("<<ComboboxSelected>>", self._actualizar_campos)

        # Descripción
        frame_desc = ttk.Frame(main_frame)
        frame_desc.pack(fill=tk.X, pady=5)
        ttk.Label(frame_desc, text="Descripción:").pack(side=tk.LEFT, padx=(0, 10))
        self.entry_desc = ttk.Entry(
            frame_desc, textvariable=self.descripcion_var, width=40
        )
        self.entry_desc.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Selector
        frame_selector = ttk.Frame(main_frame)
        frame_selector.pack(fill=tk.X, pady=5)
        ttk.Label(frame_selector, text="Selector:").pack(side=tk.LEFT, padx=(0, 10))
        self.entry_selector = ttk.Entry(
            frame_selector, textvariable=self.selector_var, width=40
        )
        self.entry_selector.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Tipo de selector
        frame_selector_tipo = ttk.Frame(main_frame)
        frame_selector_tipo.pack(fill=tk.X, pady=5)
        ttk.Label(frame_selector_tipo, text="Tipo Selector:").pack(
            side=tk.LEFT, padx=(0, 10)
        )
        self.combo_selector_tipo = ttk.Combobox(
            frame_selector_tipo,
            textvariable=self.selector_tipo_var,
            state="readonly",
            values=[s.value for s in SelectorTipo],
            width=15,
        )
        self.combo_selector_tipo.pack(side=tk.LEFT)

        # Valor
        frame_valor = ttk.Frame(main_frame)
        frame_valor.pack(fill=tk.X, pady=5)
        ttk.Label(frame_valor, text="Valor:").pack(side=tk.LEFT, padx=(0, 10))
        self.entry_valor = ttk.Entry(frame_valor, textvariable=self.valor_var, width=30)
        self.entry_valor.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(frame_valor, text="(usa {OT}, {CAJA}, etc)", foreground="gray").pack(
            side=tk.LEFT, padx=(10, 0)
        )

        # Segundos
        frame_segundos = ttk.Frame(main_frame)
        frame_segundos.pack(fill=tk.X, pady=5)
        ttk.Label(frame_segundos, text="Segundos:").pack(side=tk.LEFT, padx=(0, 10))
        self.entry_segundos = ttk.Entry(
            frame_segundos, textvariable=self.segundos_var, width=10
        )
        self.entry_segundos.pack(side=tk.LEFT)

        # JavaScript
        frame_js = ttk.Frame(main_frame)
        frame_js.pack(fill=tk.X, pady=5)
        ttk.Label(frame_js, text="JavaScript:").pack(side=tk.LEFT, padx=(0, 10))
        self.entry_js = ttk.Entry(frame_js, textvariable=self.javascript_var, width=40)
        self.entry_js.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Variable guardar
        frame_var = ttk.Frame(main_frame)
        frame_var.pack(fill=tk.X, pady=5)
        ttk.Label(frame_var, text="Guardar en:").pack(side=tk.LEFT, padx=(0, 10))
        self.entry_var = ttk.Entry(
            frame_var, textvariable=self.variable_guardar_var, width=20
        )
        self.entry_var.pack(side=tk.LEFT)

        ttk.Separator(main_frame, orient="horizontal").pack(fill=tk.X, pady=15)

        # Botones
        frame_botones = ttk.Frame(main_frame)
        frame_botones.pack(fill=tk.X)

        tk.Button(
            frame_botones,
            text="❌ Cancelar",
            command=self._cancelar,
            bg="#e74c3c",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=5)

        tk.Button(
            frame_botones,
            text="✅ Guardar Paso",
            command=self._aceptar,
            bg="#27ae60",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=5)

        self.ventana.after(100, self._actualizar_campos)

    def _actualizar_campos(self, event=None):
        tipo = self.tipo_var.get()

        estado_selector = "normal"
        estado_valor = "normal"

        if tipo == "click":
            estado_valor = "disabled"
        elif tipo == "esperar":
            estado_selector = "disabled"
        elif tipo == "javascript":
            estado_selector = "disabled"

        try:
            self.entry_selector.config(state=estado_selector)
            self.entry_valor.config(state=estado_valor)
        except:
            pass

    def _aceptar(self):
        try:
            tipo = TipoAccion(self.tipo_var.get())
            selector = self.selector_var.get().strip() or None
            selector_tipo = (
                SelectorTipo(self.selector_tipo_var.get())
                if self.selector_tipo_var.get()
                else SelectorTipo.XPATH
            )
            valor = self.valor_var.get().strip() or None
            segundos = int(self.segundos_var.get().strip() or 1)
            javascript = self.javascript_var.get().strip() or None
            descripcion = self.descripcion_var.get().strip() or ""
            variable_guardar = self.variable_guardar_var.get().strip() or None

            self.resultado = Paso(
                tipo=tipo,
                selector=selector,
                selector_tipo=selector_tipo,
                valor=valor,
                segundos=segundos,
                javascript=javascript,
                descripcion=descripcion,
                variable_guardar=variable_guardar,
            )
            self.ventana.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error", f"Error al crear el paso: {e}", parent=self.ventana
            )

    def _cancelar(self):
        self.resultado = None
        self.ventana.destroy()


# ==========================================
#  CLASE para editar flujos
# ==========================================


class EditorFlujosUI:
    def __init__(self, parent, flujo_manager):
        self.parent = parent
        self.flujo_manager = flujo_manager
        self.pasos = []
        self.nombre_flujo = tk.StringVar()
        self.descripcion_flujo = tk.StringVar()
        self.paso_seleccionado = None

        self.ventana = tk.Toplevel(parent)
        self.ventana.title("✏️ Editor de Flujos")
        self.ventana.geometry("900x700")
        self.ventana.configure(bg="#f0f2f5")

        self.ventana.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._crear_widgets()
        self.actualizar_lista_flujos()

    def _on_closing(self):
        self.ventana.destroy()

    def _crear_widgets(self):
        main_frame = ttk.Frame(self.ventana, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="✏️ EDITOR DE FLUJOS", style="Title.TLabel").pack(
            pady=(0, 15)
        )

        # Panel de selección
        panel_seleccion = ttk.LabelFrame(
            main_frame, text="📁 Seleccionar Flujo", padding="10"
        )
        panel_seleccion.pack(fill=tk.X, pady=(0, 12))

        frame_selector = ttk.Frame(panel_seleccion)
        frame_selector.pack(fill=tk.X)

        ttk.Label(frame_selector, text="Flujo:").pack(side=tk.LEFT, padx=(0, 8))

        self.combo_flujos = ttk.Combobox(frame_selector, state="readonly", width=35)
        self.combo_flujos.pack(side=tk.LEFT, padx=(0, 10))
        self.combo_flujos.bind("<<ComboboxSelected>>", self._cargar_flujo)

        ttk.Button(frame_selector, text="📂 Cargar", command=self._cargar_flujo).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(
            frame_selector, text="🗑️ Eliminar", command=self._eliminar_flujo
        ).pack(side=tk.LEFT)

        # Panel de información
        panel_info = ttk.LabelFrame(
            main_frame, text="📋 Información del Flujo", padding="10"
        )
        panel_info.pack(fill=tk.X, pady=(0, 12))

        frame_nombre = ttk.Frame(panel_info)
        frame_nombre.pack(fill=tk.X, pady=2)
        ttk.Label(frame_nombre, text="Nombre:").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(frame_nombre, textvariable=self.nombre_flujo, width=40).pack(
            side=tk.LEFT
        )

        frame_desc = ttk.Frame(panel_info)
        frame_desc.pack(fill=tk.X, pady=2)
        ttk.Label(frame_desc, text="Descripción:").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(frame_desc, textvariable=self.descripcion_flujo, width=40).pack(
            side=tk.LEFT
        )

        # Panel de pasos
        panel_pasos = ttk.LabelFrame(
            main_frame, text="📝 Pasos del Flujo", padding="10"
        )
        panel_pasos.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        frame_lista = ttk.Frame(panel_pasos)
        frame_lista.pack(fill=tk.BOTH, expand=True)

        scroll_pasos = ttk.Scrollbar(frame_lista)
        scroll_pasos.pack(side=tk.RIGHT, fill=tk.Y)

        self.lista_pasos = tk.Listbox(
            frame_lista, yscrollcommand=scroll_pasos.set, font=("Consolas", 9), height=8
        )
        self.lista_pasos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_pasos.config(command=self.lista_pasos.yview)
        self.lista_pasos.bind("<<ListboxSelect>>", self._seleccionar_paso)

        # Botones de pasos
        frame_botones_pasos = ttk.Frame(panel_pasos)
        frame_botones_pasos.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(
            frame_botones_pasos, text="➕ Agregar Paso", command=self._agregar_paso
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            frame_botones_pasos, text="✏️ Editar Paso", command=self._editar_paso
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_botones_pasos, text="⬆️ Subir", command=self._subir_paso).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(frame_botones_pasos, text="⬇️ Bajar", command=self._bajar_paso).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(
            frame_botones_pasos, text="🗑️ Eliminar Paso", command=self._eliminar_paso
        ).pack(side=tk.LEFT, padx=2)

        # Botones de acción
        panel_acciones = ttk.Frame(main_frame)
        panel_acciones.pack(fill=tk.X, pady=(0, 12))

        ttk.Button(
            panel_acciones, text="💾 Guardar Flujo", command=self._guardar_flujo
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            panel_acciones, text="🔄 Nuevo Flujo", command=self._nuevo_flujo
        ).pack(side=tk.LEFT, padx=5)

    def actualizar_lista_flujos(self):
        """Actualiza SOLO el combobox del editor"""
        flujos = self.flujo_manager.listar_flujos()
        self.combo_flujos["values"] = flujos
        if flujos:
            self.combo_flujos.set(flujos[0])

    def _cargar_flujo(self, event=None):
        nombre = self.combo_flujos.get()
        if not nombre:
            return

        flujo = self.flujo_manager.obtener_flujo(nombre)
        if not flujo:
            return

        self.nombre_flujo.set(flujo["nombre"])
        self.descripcion_flujo.set(flujo.get("descripcion", ""))
        self.pasos = flujo["pasos"].copy()
        self._actualizar_lista_pasos()

    def _actualizar_lista_pasos(self):
        self.lista_pasos.delete(0, tk.END)
        for i, paso in enumerate(self.pasos, 1):
            desc = paso.descripcion or paso.tipo.value
            selector = paso.selector or ""
            self.lista_pasos.insert(tk.END, f"{i}. {desc} - {selector[:50]}")

    def _seleccionar_paso(self, event):
        selection = self.lista_pasos.curselection()
        if selection:
            self.paso_seleccionado = selection[0]

    def _agregar_paso(self):
        dialog = DialogoPaso(self.ventana, self)
        if dialog.resultado:
            self.pasos.append(dialog.resultado)
            self._actualizar_lista_pasos()

    def _editar_paso(self):
        if self.paso_seleccionado is None:
            messagebox.showwarning("Advertencia", "Seleccione un paso para editar")
            return

        paso = self.pasos[self.paso_seleccionado]
        dialog = DialogoPaso(self.ventana, self, paso)
        if dialog.resultado:
            self.pasos[self.paso_seleccionado] = dialog.resultado
            self._actualizar_lista_pasos()

    def _subir_paso(self):
        if self.paso_seleccionado is None or self.paso_seleccionado == 0:
            return
        self.pasos[self.paso_seleccionado], self.pasos[self.paso_seleccionado - 1] = (
            self.pasos[self.paso_seleccionado - 1],
            self.pasos[self.paso_seleccionado],
        )
        self.paso_seleccionado -= 1
        self._actualizar_lista_pasos()
        self.lista_pasos.selection_set(self.paso_seleccionado)

    def _bajar_paso(self):
        if (
            self.paso_seleccionado is None
            or self.paso_seleccionado == len(self.pasos) - 1
        ):
            return
        self.pasos[self.paso_seleccionado], self.pasos[self.paso_seleccionado + 1] = (
            self.pasos[self.paso_seleccionado + 1],
            self.pasos[self.paso_seleccionado],
        )
        self.paso_seleccionado += 1
        self._actualizar_lista_pasos()
        self.lista_pasos.selection_set(self.paso_seleccionado)

    def _eliminar_paso(self):
        if self.paso_seleccionado is None:
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar este paso?"):
            del self.pasos[self.paso_seleccionado]
            self.paso_seleccionado = None
            self._actualizar_lista_pasos()

    def _guardar_flujo(self):
        nombre = self.nombre_flujo.get().strip()
        if not nombre:
            messagebox.showerror("Error", "El nombre del flujo es obligatorio")
            return

        if not self.pasos:
            messagebox.showerror("Error", "El flujo debe tener al menos un paso")
            return

        descripcion = self.descripcion_flujo.get().strip()

        if nombre in self.flujo_manager.flujos:
            if not messagebox.askyesno(
                "Confirmar", f"¿Actualizar el flujo '{nombre}'?"
            ):
                return
            exito, mensaje = self.flujo_manager.actualizar_flujo(
                nombre, descripcion, self.pasos
            )
        else:
            exito, mensaje = self.flujo_manager.guardar_flujo(
                nombre, descripcion, self.pasos
            )

        if exito:
            messagebox.showinfo("Éxito", mensaje)
            self.actualizar_lista_flujos()
        else:
            messagebox.showerror("Error", mensaje)

    def _nuevo_flujo(self):
        self.nombre_flujo.set("")
        self.descripcion_flujo.set("")
        self.pasos = []
        self.paso_seleccionado = None
        self._actualizar_lista_pasos()
        self.combo_flujos.set("")

    def _eliminar_flujo(self):
        nombre = self.combo_flujos.get()
        if not nombre:
            return

        if messagebox.askyesno("Confirmar", f"¿Eliminar el flujo '{nombre}'?"):
            if self.flujo_manager.eliminar_flujo(nombre):
                messagebox.showinfo("Éxito", f"Flujo '{nombre}' eliminado")
                self._nuevo_flujo()
                self.actualizar_lista_flujos()
            else:
                messagebox.showerror("Error", "No se pudo eliminar el flujo")


# ==========================================
#  CLASE PRINCIPAL - BOT COMPLETO
# ==========================================


class ConfiguracionUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 BOT AutomatismoWeb - Sistema de Flujos")
        self.root.configure(bg="#f0f2f5")
        self.root.geometry("1200x850")

        # ==========================================
        # ESTABLECER ICONO DE LA VENTANA
        # ==========================================
        try:
            if os.path.exists(RUTA_ICONO):
                self.root.iconbitmap(RUTA_ICONO)
            else:
                print(f"⚠️ Icono no encontrado: {RUTA_ICONO}")
        except Exception as e:
            print(f"❌ Error cargando icono: {e}")

        self.setup_styles()
        self.config_manager = ConfigManager()
        self.flujo_manager = FlujoManager()

        self.config_vars = {}
        self.config_seleccionada = tk.StringVar()
        self.flujo_seleccionado_var = tk.StringVar()
        self.flujo_login_var = tk.StringVar()

        self.test_tipo_var = tk.StringVar(value="click")
        self.test_selector_var = tk.StringVar()
        self.test_selector_tipo_var = tk.StringVar(value="xpath")
        self.test_valor_var = tk.StringVar()
        self.historial_pruebas = []

        # Nuevos atributos para edición
        self.flujo_prueba_actual = None
        self.paso_prueba_actual = None
        self.modo_edicion_paso = False

        self.crear_widgets()
        self.actualizar_lista_configuraciones()
        self.actualizar_lista_flujos()

        self.ejecutando = False
        self.hilo_ejecucion = None
        self.driver_actual = None
        self.driver_pid = None

        # Datos de versión
        self.version = self._obtener_version()
        self.desarrollador = "EO"
        self.año = "2026"

        # Portapapeles interno
        self.portapapeles_flujo = None
        self.portapapeles_nombre = None

        # Crear barra de menú
        self._crear_menu_bar()

        # Crear barra de estado (pie de página)
        self._crear_status_bar()

        self.root.update_idletasks()
        self.ajustar_ventana()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Verificar actualización al iniciar (después de 3 segundos)
        self.root.after(3000, self._verificar_actualizacion_inicio)

    def _obtener_version(self):
        """Lee la versión desde version.json"""
        try:
            if os.path.exists(os.path.join(RUTA_BASE, "version.json")):
                with open(os.path.join(RUTA_BASE, "version.json"), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("version", "1.0.0")
        except:
            pass
        return "1.0.0"

    def _cargar_info_bot(self):
        """Carga la información del bot desde info_bot.json"""
        info = {
            "version": self.version,
            "como_funciona": [],
            "mejoras": [],
            "proximas_mejoras": []
        }
        
        try:
            if os.path.exists(RUTA_INFO_BOT):
                with open(RUTA_INFO_BOT, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    info.update(data)
        except Exception as e:
            print(f"Error cargando info_bot.json: {e}")
        
        return info

    def _verificar_actualizacion_inicio(self):
        """Verifica actualización al iniciar sin molestar mucho"""
        try:
            hay_actualizacion, version, url, notas = verificar_actualizacion()
            
            if hay_actualizacion:
                respuesta = messagebox.askyesno(
                    "🔄 Actualización Disponible",
                    f"Hay una nueva versión: v{version}\n\n"
                    f"Versión actual: v{VERSION_ACTUAL}\n\n"
                    f"Notas: {notas}\n\n"
                    "¿Descargar e instalar?"
                )
                if respuesta:
                    self._descargar_actualizacion(url, version)
        except:
            pass

    def _on_closing(self):
        if self.ejecutando:
            if messagebox.askyesno(
                "Confirmar", "¿Hay una ejecución en progreso. ¿Desea detenerla y salir?"
            ):
                self.detener_ejecucion()
                self.root.after(100, self.root.destroy)
        else:
            self.root.destroy()

    def _crear_menu_bar(self):
        """Crea la barra de menú superior estilo Windows"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ==========================================
        # MENÚ ARCHIVO
        # ==========================================
        menu_archivo = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 Archivo", menu=menu_archivo)

        menu_archivo.add_command(
            label="💾 Guardar Configuración", command=self.guardar_configuracion
        )
        menu_archivo.add_command(
            label="📂 Abrir Configuración",
            command=self.cargar_configuracion_seleccionada,
        )
        menu_archivo.add_separator()
        menu_archivo.add_command(label="🔄 Limpiar Campos", command=self.limpiar_campos)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="❌ Salir", command=self._on_closing)

        # ==========================================
        # MENÚ FLUJOS
        # ==========================================
        menu_flujos = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📋 Flujos", menu=menu_flujos)

        menu_flujos.add_command(
            label="✏️ Abrir Editor", command=self._abrir_editor_flujos
        )
        menu_flujos.add_command(
            label="📂 Cargar Flujo para Probar", command=self._cargar_flujo_para_pruebas
        )
        menu_flujos.add_separator()
        menu_flujos.add_command(
            label="🔄 Actualizar Lista", command=self.actualizar_lista_flujos
        )

        # ==========================================
        # MENÚ PRUEBAS
        # ==========================================
        menu_pruebas = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🧪 Pruebas", menu=menu_pruebas)

        menu_pruebas.add_command(
            label="▶️ Ejecutar Prueba", command=self._ejecutar_prueba
        )
        menu_pruebas.add_command(
            label="💾 Guardar en Flujo", command=self._guardar_prueba_en_flujo
        )
        menu_pruebas.add_command(
            label="📦 Guardar Todas", command=self._guardar_historial_completo
        )
        menu_pruebas.add_separator()
        menu_pruebas.add_command(
            label="🌐 Abrir Navegador", command=self._abrir_navegador_prueba
        )
        menu_pruebas.add_command(
            label="❌ Cerrar Navegador", command=self._cerrar_navegador_prueba
        )

        # ==========================================
        # MENÚ AYUDA
        # ==========================================
        menu_ayuda = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Ayuda", menu=menu_ayuda)

        menu_ayuda.add_command(label="📖 Acerca de...", command=self._mostrar_acerca_de)
        menu_ayuda.add_command(
            label="🔄 Buscar Actualizaciones",
            command=self._verificar_actualizacion_manual,
        )
        menu_ayuda.add_separator()
        menu_ayuda.add_command(
            label="📋 Ver Logs", command=lambda: self.notebook.select(self.tab_logs)
        )

    def _crear_status_bar(self):
        """Crea la barra de estado inferior"""
        self.status_bar = tk.Frame(self.root, bg="#2c3e50", height=30)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        # Frame izquierdo (estado)
        frame_izquierdo = tk.Frame(self.status_bar, bg="#2c3e50")
        frame_izquierdo.pack(side=tk.LEFT, padx=10)

        self.label_estado = tk.Label(
            frame_izquierdo,
            text="✅ Listo",
            bg="#2c3e50",
            fg="white",
            font=("Segoe UI", 8),
        )
        self.label_estado.pack(side=tk.LEFT)

        # Frame derecho (versión y desarrollador)
        frame_derecho = tk.Frame(self.status_bar, bg="#2c3e50")
        frame_derecho.pack(side=tk.RIGHT, padx=10)

        label_version = tk.Label(
            frame_derecho,
            text=f"v{self.version}",
            bg="#2c3e50",
            fg="#bdc3c7",
            font=("Segoe UI", 8),
        )
        label_version.pack(side=tk.LEFT, padx=(0, 10))

        label_dev = tk.Label(
            frame_derecho,
            text=f"Desarrollado por {self.desarrollador} con ❤️",
            bg="#2c3e50",
            fg="#e74c3c",
            font=("Segoe UI", 8, "bold"),
        )
        label_dev.pack(side=tk.LEFT)

    def _mostrar_acerca_de(self):
        """Muestra ventana de información completa"""
        ventana = tk.Toplevel(self.root)
        ventana.title("Acerca de")
        ventana.geometry("650x750")
        ventana.configure(bg="#f0f2f5")
        ventana.transient(self.root)
        ventana.resizable(False, False)
        
        # Establecer icono de la ventana
        try:
            if os.path.exists(RUTA_ICONO):
                ventana.iconbitmap(RUTA_ICONO)
        except:
            pass
        
        # Centrar ventana
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (650 // 2)
        y = (ventana.winfo_screenheight() // 2) - (750 // 2)
        ventana.geometry(f"650x750+{x}+{y}")
        
        # ==========================================
        # FRAME PRINCIPAL
        # ==========================================
        main_frame = ttk.Frame(ventana)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # ==========================================
        # CANVAS CON SCROLL
        # ==========================================
        canvas = tk.Canvas(main_frame, bg="#f0f2f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        
        # Frame interno del scroll
        contenido = ttk.Frame(canvas)
        
        # Vincular el tamaño del frame al canvas
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        contenido.bind("<Configure>", _on_frame_configure)
        
        # Crear ventana en el canvas
        canvas_window = canvas.create_window((0, 0), window=contenido, anchor="nw")
        
        # Ajustar ancho del frame al ancho del canvas
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ==========================================
        # CONTENIDO
        # ==========================================
        
        # Logo (usar imagen personalizada o emoji)
        try:
            from PIL import Image, ImageTk
            
            if os.path.exists(RUTA_LOGO):
                # Cargar y redimensionar imagen
                img = Image.open(RUTA_LOGO)
                img = img.resize((100, 100), Image.LANCZOS)
                logo = ImageTk.PhotoImage(img)
                
                label_logo = tk.Label(contenido, image=logo, bg="#f0f2f5")
                label_logo.image = logo  # Mantener referencia
                label_logo.pack(pady=(10, 5))
            else:
                tk.Label(
                    contenido,
                    text="🤖",
                    font=("Segoe UI", 48),
                    bg="#f0f2f5",
                ).pack(pady=(10, 5))
        except ImportError:
            tk.Label(
                contenido,
                text="🤖",
                font=("Segoe UI", 48),
                bg="#f0f2f5",
            ).pack(pady=(10, 5))
        
        # Título
        tk.Label(
            contenido,
            text="BOT AutomatismoWeb",
            font=("Segoe UI", 16, "bold"),
            fg="#2c3e50",
            bg="#f0f2f5",
        ).pack()
        
        # Versión
        tk.Label(
            contenido,
            text=f"Versión {self.version}",
            font=("Segoe UI", 10),
            fg="#7f8c8d",
            bg="#f0f2f5",
        ).pack(pady=(0, 10))
        
        # Separador
        ttk.Separator(contenido, orient="horizontal").pack(fill=tk.X, pady=5)
        
        # ==========================================
        # CÓMO FUNCIONA
        # ==========================================
        frame_como = ttk.LabelFrame(contenido, text="📖 Cómo Funciona", padding="10")
        frame_como.pack(fill=tk.X, pady=10)
        
        info = self._cargar_info_bot()
        
        for paso in info.get("como_funciona", []):
            tk.Label(
                frame_como,
                text=paso,
                bg="#f0f2f5",
                fg="#2c3e50",
                font=("Segoe UI", 9),
                anchor="w",
                justify=tk.LEFT,
            ).pack(fill=tk.X, pady=2)
        
        # ==========================================
        # MEJORAS
        # ==========================================
        frame_mejoras = ttk.LabelFrame(contenido, text="🔄 Mejoras", padding="10")
        frame_mejoras.pack(fill=tk.X, pady=10)
        
        for mejora in info.get("mejoras", []):
            version_mejora = mejora.get("version", "")
            fecha_mejora = mejora.get("fecha", "")
            cambios = mejora.get("cambios", [])
            
            tk.Label(
                frame_mejoras,
                text=f"v{version_mejora} - {fecha_mejora}",
                bg="#f0f2f5",
                fg="#3498db",
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).pack(fill=tk.X, pady=(5, 2))
            
            for cambio in cambios:
                tk.Label(
                    frame_mejoras,
                    text=f"  • {cambio}",
                    bg="#f0f2f5",
                    fg="#2c3e50",
                    font=("Segoe UI", 9),
                    anchor="w",
                    justify=tk.LEFT,
                ).pack(fill=tk.X, pady=1)
        
        # ==========================================
        # PRÓXIMAS MEJORAS
        # ==========================================
        frame_proximas = ttk.LabelFrame(contenido, text="🚀 Próximas Mejoras", padding="10")
        frame_proximas.pack(fill=tk.X, pady=10)
        
        for mejora in info.get("proximas_mejoras", []):
            tk.Label(
                frame_proximas,
                text=f"  • {mejora}",
                bg="#f0f2f5",
                fg="#7f8c8d",
                font=("Segoe UI", 9),
                anchor="w",
                justify=tk.LEFT,
            ).pack(fill=tk.X, pady=1)
        
        # Separador
        ttk.Separator(contenido, orient="horizontal").pack(fill=tk.X, pady=10)
        
        # ==========================================
        # DESARROLLADOR
        # ==========================================
        tk.Label(
            contenido,
            text=f"Desarrollado por {self.desarrollador} con ❤️",
            font=("Segoe UI", 10, "bold"),
            fg="#e74c3c",
            bg="#f0f2f5",
        ).pack(pady=(10, 0))
        
        tk.Label(
            contenido,
            text=f"© {self.año} Todos los derechos reservados",
            font=("Segoe UI", 8),
            fg="#95a5a6",
            bg="#f0f2f5",
        ).pack(pady=(5, 10))
        
        # ==========================================
        # BOTÓN CERRAR (fijo abajo)
        # ==========================================
        frame_boton = ttk.Frame(ventana)
        frame_boton.pack(fill=tk.X, pady=10)
        
        tk.Button(
            frame_boton,
            text="Cerrar",
            command=ventana.destroy,
            bg="#3498db",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack()

    
    def _verificar_actualizacion_manual(self):
        """Verifica actualizaciones manualmente"""
        self.log("🔄 Buscando actualizaciones...", "info")
        
        try:
            hay_actualizacion, version, url, notas = verificar_actualizacion()
            
            if hay_actualizacion:
                self.log(f"🔄 Nueva versión disponible: v{version}", "warning")
                respuesta = messagebox.askyesno(
                    "🔄 Actualización Disponible",
                    f"Versión actual: v{VERSION_ACTUAL}\n"
                    f"Nueva versión: v{version}\n\n"
                    f"Notas: {notas}\n\n"
                    "¿Descargar e instalar?"
                )
                if respuesta:
                    self._descargar_actualizacion(url, version)
            else:
                messagebox.showinfo(
                    "Sin Actualizaciones", 
                    f"Ya tienes la última versión (v{VERSION_ACTUAL})"
                )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo verificar: {e}")

    def _descargar_actualizacion(self, url, version):
        """Descarga e instala la actualización"""
        import urllib.request
        import subprocess
        
        def descargar():
            try:
                self.log(f"📥 Descargando v{version}...", "info")
                
                # Ruta del archivo temporal
                archivo_temp = os.path.join(RUTA_BASE, "BOT_AutomatismoWeb_v1.0.0.exe")
                
                # Descargar
                urllib.request.urlretrieve(url, archivo_temp)
                self.log("✅ Descarga completada", "success")
                
                # Hacer backup del actual
                backup_dir = os.path.join(RUTA_BASE, "backup")
                os.makedirs(backup_dir, exist_ok=True)
                backup_nombre = os.path.join(backup_dir, f"BOT_v{VERSION_ACTUAL}.exe")
                
                if os.path.exists(sys.executable):
                    import shutil
                    shutil.copy2(sys.executable, backup_nombre)
                    self.log("✅ Backup creado", "success")
                
                # Crear script batch para reemplazar
                batch_content = f"""@echo off
    timeout /t 2 /nobreak >nul
    del "{sys.executable}"
    move /y "{archivo_temp}" "{sys.executable}"
    start "" "{sys.executable}"
    del "%~f0"
    exit
    """
                batch_path = os.path.join(RUTA_BASE, "actualizar.bat")
                with open(batch_path, "w", encoding="utf-8") as f:
                    f.write(batch_content)
                
                # Ejecutar script batch
                subprocess.Popen(batch_path, shell=True)
                
                # Cerrar el bot
                self.root.after(500, self.root.destroy)
                
            except Exception as e:
                self.log(f"❌ Error descargando: {e}", "error")
        
        threading.Thread(target=descargar, daemon=True).start()

    def ajustar_ventana(self):
        self.root.update_idletasks()
        width = max(1200, self.root.winfo_reqwidth() + 30)
        height = max(850, self.root.winfo_reqheight() + 30)
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 14, "bold"),
            foreground="#2c3e50",
            background="#f0f2f5",
        )
        style.configure("TLabel", font=("Segoe UI", 9), background="#f0f2f5")
        style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=6)
        style.configure(
            "TLabelframe",
            font=("Segoe UI", 9, "bold"),
            background="#f0f2f5",
            foreground="#2c3e50",
        )
        style.configure(
            "TLabelframe.Label", font=("Segoe UI", 9, "bold"), foreground="#2c3e50"
        )
        style.configure("TEntry", fieldbackground="white", borderwidth=1)
        style.configure("TCombobox", fieldbackground="white", borderwidth=1)

    def crear_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_config = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_config, text="⚙️ Configuración")
        self._crear_tab_configuracion()

        self.tab_flujos = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_flujos, text="📋 Flujos")
        self._crear_tab_flujos()

        # ==========================================
        # NUEVA PESTAÑA EDITOR - AQUÍ FALTA
        # ==========================================
        self.tab_editor = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_editor, text="✏️ Editor")
        self._crear_tab_editor()  # <- Este método también falta

        self.tab_pruebas = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_pruebas, text="🧪 Pruebas")
        self._crear_tab_pruebas()

        self.tab_logs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_logs, text="📋 Logs")
        self._crear_tab_logs()

    def _crear_tab_configuracion(self):
        canvas = tk.Canvas(self.tab_config, bg="#f0f2f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self.tab_config, orient="vertical", command=canvas.yview
        )

        main_frame = ttk.Frame(canvas, padding="15")

        main_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)

        # Selector de configuración
        panel_seleccion = ttk.LabelFrame(
            main_frame, text="📁 Seleccionar Configuración", padding="10"
        )
        panel_seleccion.pack(fill=tk.X, pady=(0, 12))

        frame_selector = ttk.Frame(panel_seleccion)
        frame_selector.pack(fill=tk.X)

        ttk.Label(frame_selector, text="Configuración:").pack(side=tk.LEFT, padx=(0, 8))

        self.combo_config = ttk.Combobox(
            frame_selector,
            textvariable=self.config_seleccionada,
            state="readonly",
            width=35,
        )
        self.combo_config.pack(side=tk.LEFT, padx=(0, 10))
        self.combo_config.bind(
            "<<ComboboxSelected>>", self.cargar_configuracion_seleccionada
        )

        ttk.Button(
            frame_selector,
            text="📂 Cargar",
            command=self.cargar_configuracion_seleccionada,
            width=10,
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            frame_selector,
            text="🗑️ Eliminar",
            command=self.eliminar_configuracion,
            width=10,
        ).pack(side=tk.LEFT)

        # Campos de configuración
        panel_config = ttk.LabelFrame(
            main_frame, text="⚙️ Variables Configurables", padding="12"
        )
        panel_config.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        self._crear_campos_configuracion(panel_config)

        # Selector de flujo de LOGIN (se ejecuta una vez)
        panel_flujo_login = ttk.LabelFrame(
            main_frame, text="🔐 Flujo de LOGIN (se ejecuta una sola vez)", padding="10"
        )
        panel_flujo_login.pack(fill=tk.X, pady=(0, 12))

        frame_flujo_login = ttk.Frame(panel_flujo_login)
        frame_flujo_login.pack(fill=tk.X)

        ttk.Label(frame_flujo_login, text="Flujo Login:").pack(
            side=tk.LEFT, padx=(0, 10)
        )
        self.combo_flujo_login = ttk.Combobox(
            frame_flujo_login,
            textvariable=self.flujo_login_var,
            state="readonly",
            width=40,
        )
        self.combo_flujo_login.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Selector de flujo de ASIGNACIÓN (por OT)
        panel_flujo = ttk.LabelFrame(
            main_frame, text="📋 Flujo secundario (por OT)", padding="10"
        )
        panel_flujo.pack(fill=tk.X, pady=(0, 12))

        frame_flujo = ttk.Frame(panel_flujo)
        frame_flujo.pack(fill=tk.X)

        ttk.Label(frame_flujo, text="Flujo Secundario:").pack(
            side=tk.LEFT, padx=(0, 10)
        )
        self.combo_flujos = ttk.Combobox(
            frame_flujo,
            textvariable=self.flujo_seleccionado_var,
            state="readonly",
            width=40,
        )
        self.combo_flujos.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.combo_flujos.bind("<<ComboboxSelected>>", self._mostrar_info_flujo)

        self.label_info_flujo = ttk.Label(frame_flujo, text="")
        self.label_info_flujo.pack(side=tk.LEFT, padx=(10, 0))

        # Estado del navegador
        panel_navegador = ttk.LabelFrame(main_frame, text="🌐 Navegador", padding="10")
        panel_navegador.pack(fill=tk.X, pady=(0, 12))

        self.label_estado_navegador = ttk.Label(
            panel_navegador, text="⚠️ Navegador cerrado", foreground="red"
        )
        self.label_estado_navegador.pack()

        # Botones de acción
        panel_acciones = ttk.LabelFrame(main_frame, text="🚀 Acciones", padding="10")
        panel_acciones.pack(fill=tk.X, pady=(0, 12))

        frame_botones = ttk.Frame(panel_acciones)
        frame_botones.pack()

        btn_guardar = tk.Button(
            frame_botones,
            text="💾 Guardar Configuración",
            command=self.guardar_configuracion,
            bg="#3498db",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=15,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_guardar.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_ejecutar = tk.Button(
            frame_botones,
            text="▶️ Ejecutar Automatización",
            command=self.ejecutar_automatizacion,
            bg="#27ae60",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=15,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
        )
        self.btn_ejecutar.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_detener = tk.Button(
            frame_botones,
            text="⏹️ Detener",
            command=self.detener_ejecucion,
            bg="#dc3545",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=15,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
            state="disabled",
        )
        self.btn_detener.pack(side=tk.LEFT, padx=(0, 8))

        btn_limpiar = tk.Button(
            frame_botones,
            text="🔄 Limpiar Campos",
            command=self.limpiar_campos,
            bg="#95a5a6",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=15,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_limpiar.pack(side=tk.LEFT)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _crear_campos_configuracion(self, parent):
        campos = [
            ("👤 USUARIO", "usuario"),
            ("🔒 PASSWORD", "password"),
            ("🌐 URL_LOGIN", "url_login"),
            ("📊 EXCEL_OTPS", "excel_otps"),
            ("🌍 BRAVE_PATH", "brave_path"),
            ("💻 CHROMEDRIVER_PATH", "chromedriver_path"),
        ]

        grid_frame = ttk.Frame(parent)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        grid_frame.columnconfigure(1, weight=1)

        row_colors = ["#f8f9fa", "white"]

        for i, (label, key) in enumerate(campos):
            row_frame = tk.Frame(grid_frame, bg=row_colors[i % 2])
            row_frame.grid(row=i, column=0, columnspan=2, sticky="ew", pady=1)
            row_frame.columnconfigure(1, weight=1)

            label_widget = ttk.Label(row_frame, text=label, width=18, anchor="e")
            label_widget.grid(row=0, column=0, padx=(5, 8), pady=4, sticky="e")

            if key == "password":
                entry = ttk.Entry(row_frame, show="•", width=40)
                entry.grid(row=0, column=1, padx=(0, 5), pady=4, sticky="ew")
            elif "path" in key or "excel" in key:
                frame_entry = ttk.Frame(row_frame)
                frame_entry.grid(row=0, column=1, padx=(0, 5), pady=4, sticky="ew")
                frame_entry.columnconfigure(0, weight=1)

                entry = ttk.Entry(frame_entry, width=35)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

                btn_explorar = tk.Button(
                    frame_entry,
                    text="📁",
                    width=3,
                    command=lambda e=entry: self.explorar_archivo(e),
                    bg="#e0e0e0",
                    relief=tk.FLAT,
                    cursor="hand2",
                    font=("Segoe UI", 9),
                )
                btn_explorar.pack(side=tk.LEFT, padx=(3, 0))
            else:
                entry = ttk.Entry(row_frame, width=40)
                entry.grid(row=0, column=1, padx=(0, 5), pady=4, sticky="ew")

            self.config_vars[key] = entry

    def _crear_tab_flujos(self):
        main_frame = ttk.Frame(self.tab_flujos, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="📋 Flujos Disponibles", style="Title.TLabel").pack(
            pady=(0, 15)
        )

        # ==========================================
        # CANVAS PARA LISTA DE FLUJOS CON SCROLL
        # ==========================================
        frame_lista_container = ttk.Frame(main_frame)
        frame_lista_container.pack(fill=tk.BOTH, expand=True)

        canvas_lista = tk.Canvas(
            frame_lista_container, bg="#f0f2f5", highlightthickness=0
        )
        scrollbar_lista = ttk.Scrollbar(
            frame_lista_container, orient="vertical", command=canvas_lista.yview
        )

        self.frame_flujos = ttk.Frame(canvas_lista)
        self.frame_flujos.bind(
            "<Configure>",
            lambda e: canvas_lista.configure(scrollregion=canvas_lista.bbox("all")),
        )

        # ==========================================
        # CORRECCIÓN: Guardar referencia a la ventana del canvas
        # ==========================================
        self.canvas_window_flujos = canvas_lista.create_window(
            (0, 0), window=self.frame_flujos, anchor="nw"
        )
        canvas_lista.configure(yscrollcommand=scrollbar_lista.set)

        canvas_lista.pack(side="left", fill="both", expand=True)
        scrollbar_lista.pack(side="right", fill="y")

        def _on_canvas_configure(event):
            # Corregido: usar la referencia guardada
            canvas_lista.itemconfig(self.canvas_window_flujos, width=event.width)

        canvas_lista.bind("<Configure>", _on_canvas_configure)

        # Botones inferiores
        frame_botones = ttk.Frame(main_frame)
        frame_botones.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            frame_botones, text="🔄 Actualizar", command=self.actualizar_lista_flujos
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            frame_botones, text="✏️ Editor", command=self._abrir_editor_flujos
        ).pack(side=tk.LEFT, padx=5)

        self.actualizar_lista_flujos()

    def _crear_tab_pruebas(self):
        canvas = tk.Canvas(self.tab_pruebas, bg="#f0f2f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self.tab_pruebas, orient="vertical", command=canvas.yview
        )

        main_frame = ttk.Frame(canvas, padding="15")

        main_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)

        ttk.Label(
            main_frame, text="🧪 PRUEBAS EN TIEMPO REAL", style="Title.TLabel"
        ).pack(pady=(0, 15))

        # ==========================================
        # PANEL DE CONFIGURACIÓN DE PRUEBA
        # ==========================================
        panel_test = ttk.LabelFrame(
            main_frame, text="🎯 Configurar Prueba", padding="10"
        )
        panel_test.pack(fill=tk.X, pady=(0, 12))

        # Campos
        frame_tipo = ttk.Frame(panel_test)
        frame_tipo.pack(fill=tk.X, pady=3)
        ttk.Label(frame_tipo, text="Tipo:").pack(side=tk.LEFT, padx=(0, 10))
        combo_tipo = ttk.Combobox(
            frame_tipo,
            textvariable=self.test_tipo_var,
            state="readonly",
            values=[t.value for t in TipoAccion],
            width=15,
        )
        combo_tipo.pack(side=tk.LEFT)
        combo_tipo.bind("<<ComboboxSelected>>", self._actualizar_campos_prueba)

        frame_selector = ttk.Frame(panel_test)
        frame_selector.pack(fill=tk.X, pady=3)
        ttk.Label(frame_selector, text="Selector:").pack(side=tk.LEFT, padx=(0, 10))
        self.entry_test_selector = ttk.Entry(
            frame_selector, textvariable=self.test_selector_var, width=40
        )
        self.entry_test_selector.pack(side=tk.LEFT, fill=tk.X, expand=True)

        frame_selector_tipo = ttk.Frame(panel_test)
        frame_selector_tipo.pack(fill=tk.X, pady=3)
        ttk.Label(frame_selector_tipo, text="Tipo Selector:").pack(
            side=tk.LEFT, padx=(0, 10)
        )
        combo_selector_tipo = ttk.Combobox(
            frame_selector_tipo,
            textvariable=self.test_selector_tipo_var,
            state="readonly",
            values=[s.value for s in SelectorTipo],
            width=15,
        )
        combo_selector_tipo.pack(side=tk.LEFT)

        frame_valor = ttk.Frame(panel_test)
        frame_valor.pack(fill=tk.X, pady=3)
        ttk.Label(frame_valor, text="Valor:").pack(side=tk.LEFT, padx=(0, 10))
        self.entry_test_valor = ttk.Entry(
            frame_valor, textvariable=self.test_valor_var, width=30
        )
        self.entry_test_valor.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Botones de prueba
        frame_botones1 = ttk.Frame(panel_test)
        frame_botones1.pack(fill=tk.X, pady=(10, 3))

        btn_ejecutar = tk.Button(
            frame_botones1,
            text="▶️ Ejecutar",
            command=self._ejecutar_prueba,
            bg="#27ae60",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_ejecutar.pack(side=tk.LEFT, padx=2)

        btn_guardar = tk.Button(
            frame_botones1,
            text="💾 Guardar",
            command=self._guardar_prueba_en_flujo,
            bg="#3498db",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_guardar.pack(side=tk.LEFT, padx=2)

        btn_guardar_todas = tk.Button(
            frame_botones1,
            text="📦 Guardar Todas",
            command=self._guardar_historial_completo,
            bg="#9b59b6",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_guardar_todas.pack(side=tk.LEFT, padx=2)

        btn_cargar = tk.Button(
            frame_botones1,
            text="📂 Cargar Flujo",
            command=self._cargar_flujo_para_pruebas,
            bg="#00bcd4",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_cargar.pack(side=tk.LEFT, padx=2)

        btn_recargar = tk.Button(
            frame_botones1,
            text="🔄 Variables",
            command=self._recargar_variables_excel,
            bg="#8bc34a",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_recargar.pack(side=tk.LEFT, padx=2)

        # Botones navegador
        frame_botones2 = ttk.Frame(panel_test)
        frame_botones2.pack(fill=tk.X, pady=3)

        btn_abrir = tk.Button(
            frame_botones2,
            text="🌐 Abrir Nav",
            command=self._abrir_navegador_prueba,
            bg="#f39c12",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_abrir.pack(side=tk.LEFT, padx=2)

        btn_cerrar = tk.Button(
            frame_botones2,
            text="❌ Cerrar Nav",
            command=self._cerrar_navegador_prueba,
            bg="#e74c3c",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_cerrar.pack(side=tk.LEFT, padx=2)

        btn_cambios = tk.Button(
            frame_botones2,
            text="💾 Cambios",
            command=self._guardar_cambios_paso,
            bg="#ff9800",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_cambios.pack(side=tk.LEFT, padx=2)

        btn_siguiente = tk.Button(
            frame_botones2,
            text="⏭️ Siguiente",
            command=self._probar_siguiente_paso,
            bg="#607d8b",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_siguiente.pack(side=tk.LEFT, padx=2)

        # ==========================================
        # PANEL DE FLUJO CARGADO (SIEMPRE VISIBLE)
        # ==========================================
        self.panel_flujo_cargado = ttk.LabelFrame(
            main_frame, text="📂 Flujo Cargado", padding="10"
        )
        self.panel_flujo_cargado.pack(fill=tk.X, pady=(0, 12))

        # Frame para mostrar información del flujo
        self.frame_info_flujo = ttk.Frame(self.panel_flujo_cargado)
        self.frame_info_flujo.pack(fill=tk.X, pady=(0, 5))

        self.label_flujo_nombre = ttk.Label(
            self.frame_info_flujo,
            text="No hay flujo cargado",
            font=("Segoe UI", 10, "bold"),
        )
        self.label_flujo_nombre.pack(side=tk.LEFT)

        # Botones de acción del flujo
        frame_acciones_flujo = ttk.Frame(self.frame_info_flujo)
        frame_acciones_flujo.pack(side=tk.RIGHT)

        btn_ejecutar_todo = tk.Button(
            frame_acciones_flujo,
            text="▶️ Ejecutar Todo",
            command=self._ejecutar_flujo_completo_pruebas,
            bg="#4caf50",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_ejecutar_todo.pack(side=tk.LEFT, padx=2)

        btn_cerrar_flujo = tk.Button(
            frame_acciones_flujo,
            text="❌",
            command=self._cerrar_flujo_cargado,
            bg="#e74c3c",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=5,
            pady=2,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_cerrar_flujo.pack(side=tk.LEFT, padx=2)

        # ==========================================
        # CANVAS CON SCROLL HORIZONTAL Y VERTICAL
        # ==========================================
        frame_scroll_container = ttk.Frame(self.panel_flujo_cargado)
        frame_scroll_container.pack(fill=tk.BOTH, expand=True)

        canvas_flujo = tk.Canvas(
            frame_scroll_container, height=150, bg="#f8f9fa", highlightthickness=0
        )
        scrollbar_vertical = ttk.Scrollbar(
            frame_scroll_container, orient="vertical", command=canvas_flujo.yview
        )
        scrollbar_horizontal = ttk.Scrollbar(
            frame_scroll_container, orient="horizontal", command=canvas_flujo.xview
        )

        self.frame_pasos_flujo = ttk.Frame(canvas_flujo)
        self.frame_pasos_flujo.bind(
            "<Configure>",
            lambda e: canvas_flujo.configure(scrollregion=canvas_flujo.bbox("all")),
        )

        canvas_flujo.create_window((0, 0), window=self.frame_pasos_flujo, anchor="nw")
        canvas_flujo.configure(
            yscrollcommand=scrollbar_vertical.set,
            xscrollcommand=scrollbar_horizontal.set,
        )

        # Empaquetar con grid
        canvas_flujo.grid(row=0, column=0, sticky="nsew")
        scrollbar_vertical.grid(row=0, column=1, sticky="ns")
        scrollbar_horizontal.grid(row=1, column=0, sticky="ew")

        frame_scroll_container.grid_rowconfigure(0, weight=1)
        frame_scroll_container.grid_columnconfigure(0, weight=1)

        # Panel de resultados
        panel_resultados = ttk.LabelFrame(
            main_frame, text="📊 Resultados", padding="10"
        )
        panel_resultados.pack(fill=tk.BOTH, expand=True)

        self.test_result_text = scrolledtext.ScrolledText(
            panel_resultados,
            height=8,
            font=("Consolas", 9),
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#d4d4d4",
        )
        self.test_result_text.pack(fill=tk.BOTH, expand=True)

        self._actualizar_campos_prueba()

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _crear_tab_logs(self):
        main_frame = ttk.Frame(self.tab_logs, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="📋 Log de Ejecución", style="Title.TLabel").pack(
            pady=(0, 15)
        )

        self.log_text = scrolledtext.ScrolledText(
            main_frame,
            height=20,
            font=("Consolas", 9),
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_config("info", foreground="#4fc3f7")
        self.log_text.tag_config("success", foreground="#81c784")
        self.log_text.tag_config("error", foreground="#ef5350")
        self.log_text.tag_config("warning", foreground="#ffb74d")
        self.log_text.tag_config("time", foreground="#78909c")
        self.log_text.tag_config("stop", foreground="#ff6b6b")

        frame_botones = ttk.Frame(main_frame)
        frame_botones.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            frame_botones, text="🗑️ Limpiar Log", command=self._limpiar_log
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            frame_botones, text="💾 Exportar Log", command=self._exportar_log
        ).pack(side=tk.LEFT, padx=5)

        self.status_frame = ttk.Frame(main_frame)
        self.status_frame.pack(fill=tk.X, pady=(5, 0))
        self.status_label = ttk.Label(
            self.status_frame, text="✅ Listo", font=("Segoe UI", 8)
        )
        self.status_label.pack(side=tk.LEFT)

    # ==========================================
    #  MÉTODOS DE CONFIGURACIÓN
    # ==========================================

    def explorar_archivo(self, entry):
        filename = filedialog.askopenfilename(title="Seleccionar archivo")
        if filename:
            entry.delete(0, tk.END)
            entry.insert(0, filename)
            self.status_label.config(text="📁 Archivo seleccionado")

    def actualizar_lista_configuraciones(self):
        configs = self.config_manager.listar_configuraciones()
        self.combo_config["values"] = configs
        if configs:
            self.combo_config.set(configs[0])

    def cargar_configuracion_seleccionada(self, event=None):
        nombre = self.config_seleccionada.get()
        if not nombre:
            return
        config = self.config_manager.obtener_configuracion(nombre)
        if not config:
            return
        for key, entry in self.config_vars.items():
            key_upper = key.upper()
            if key_upper in config:
                entry.delete(0, tk.END)
                entry.insert(0, str(config[key_upper]))
        self.log(f"✅ Configuración '{nombre}' cargada exitosamente", "success")
        self.status_label.config(text=f"✅ Configuración '{nombre}' cargada")

    def guardar_configuracion(self):
        nombre = simpledialog.askstring(
            "💾 Guardar Configuración",
            "Ingrese un nombre para la configuración:",
            parent=self.root,
        )
        if not nombre:
            return
        if nombre.strip() == "":
            messagebox.showerror("Error", "El nombre no puede estar vacío")
            return
        valores = {}
        for key, entry in self.config_vars.items():
            key_upper = key.upper()
            valores[key_upper] = entry.get()
        campos_vacios = [k for k, v in valores.items() if not v.strip()]
        if campos_vacios:
            messagebox.showerror(
                "Error",
                f"Los siguientes campos están vacíos:\n{', '.join(campos_vacios)}",
            )
            return
        if nombre in self.config_manager.configuraciones:
            if not messagebox.askyesno(
                "Confirmar",
                f"Ya existe una configuración con el nombre '{nombre}'. ¿Desea sobrescribirla?",
            ):
                return
        exito, mensaje = self.config_manager.agregar_configuracion(nombre, valores)
        if exito:
            messagebox.showinfo("Éxito", mensaje)
            self.actualizar_lista_configuraciones()
            self.combo_config.set(nombre)
            self.log(f"✅ Configuración '{nombre}' guardada exitosamente", "success")
            self.status_label.config(text=f"✅ Configuración '{nombre}' guardada")
        else:
            messagebox.showerror("Error", mensaje)
            self.log(f"❌ {mensaje}", "error")

    def eliminar_configuracion(self):
        nombre = self.config_seleccionada.get()
        if not nombre:
            return
        if messagebox.askyesno(
            "Confirmar", f"¿Está seguro de eliminar la configuración '{nombre}'?"
        ):
            if self.config_manager.eliminar_configuracion(nombre):
                messagebox.showinfo("Éxito", f"Configuración '{nombre}' eliminada")
                self.actualizar_lista_configuraciones()
                self.limpiar_campos()
                self.log(f"🗑️ Configuración '{nombre}' eliminada", "warning")
                self.status_label.config(text=f"🗑️ Configuración '{nombre}' eliminada")
            else:
                messagebox.showerror("Error", "No se pudo eliminar la configuración")

    def limpiar_campos(self):
        for key, entry in self.config_vars.items():
            entry.delete(0, tk.END)
        self.config_seleccionada.set("")
        self.log("🔄 Campos limpiados", "info")
        self.status_label.config(text="🔄 Campos limpiados")

    # ==========================================
    #  MÉTODOS DE FLUJOS
    # ==========================================

    def actualizar_lista_flujos(self):
        """Actualiza la lista de flujos visual y los selectores"""
        flujos = self.flujo_manager.listar_flujos()

        # ==========================================
        # 1. Actualizar selectores de login y asignación
        # ==========================================
        flujos_login = []
        flujos_asignacion = []

        for flujo in flujos:
            nombre_lower = flujo.lower()
            if "login" in nombre_lower:
                flujos_login.append(flujo)
            else:
                flujos_asignacion.append(flujo)

        # Selector de LOGIN
        if hasattr(self, "combo_flujo_login"):
            self.combo_flujo_login["values"] = flujos_login
            if flujos_login:
                self.combo_flujo_login.set(flujos_login[0])
            else:
                self.combo_flujo_login.set("")

        # Selector de ASIGNACIÓN
        if hasattr(self, "combo_flujos"):
            self.combo_flujos["values"] = flujos_asignacion
            if flujos_asignacion:
                self.combo_flujos.set(flujos_asignacion[0])
            else:
                self.combo_flujos.set("")

        # ==========================================
        # 2. Actualizar lista visual en la pestaña Flujos
        # ==========================================
        if hasattr(self, "frame_flujos"):
            # Limpiar frame
            for widget in self.frame_flujos.winfo_children():
                widget.destroy()

            if not flujos:
                # Mostrar mensaje si no hay flujos
                ttk.Label(
                    self.frame_flujos,
                    text="No hay flujos creados",
                    font=("Segoe UI", 10),
                ).pack(pady=20)
            else:
                # Mostrar cada flujo con botones
                for flujo_nombre in flujos:
                    flujo = self.flujo_manager.obtener_flujo(flujo_nombre)
                    if not flujo:
                        continue

                    # Frame para cada flujo
                    frame_flujo = tk.Frame(
                        self.frame_flujos, bg="white", relief=tk.RIDGE, bd=1
                    )
                    frame_flujo.pack(fill=tk.X, pady=3, padx=5)

                    # Información del flujo
                    desc = flujo.get("descripcion", "")
                    pasos = len(flujo.get("pasos", []))

                    info_texto = f"📁 {flujo_nombre}"
                    if desc:
                        info_texto += f" - {desc}"
                    info_texto += f" ({pasos} pasos)"

                    label_info = tk.Label(
                        frame_flujo,
                        text=info_texto,
                        bg="white",
                        fg="#2c3e50",
                        font=("Segoe UI", 9, "bold"),
                        anchor="w",
                    )
                    label_info.pack(
                        side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8
                    )

                    # Frame para botones
                    frame_btns = tk.Frame(frame_flujo, bg="white")
                    frame_btns.pack(side=tk.RIGHT, padx=5)

                    # Botón Copiar
                    btn_copiar = tk.Button(
                        frame_btns,
                        text="📋 Copiar",
                        command=lambda nombre=flujo_nombre: self._copiar_flujo_rapido(
                            nombre
                        ),
                        bg="#3498db",
                        fg="white",
                        font=("Segoe UI", 8, "bold"),
                        padx=8,
                        pady=3,
                        relief=tk.FLAT,
                        cursor="hand2",
                    )
                    btn_copiar.pack(side=tk.LEFT, padx=2)

                    # Botón Pegar
                    btn_pegar = tk.Button(
                        frame_btns,
                        text="📑 Pegar",
                        command=self._pegar_flujo_rapido,
                        bg="#00bcd4",
                        fg="white",
                        font=("Segoe UI", 8, "bold"),
                        padx=8,
                        pady=3,
                        relief=tk.FLAT,
                        cursor="hand2",
                    )
                    btn_pegar.pack(side=tk.LEFT, padx=2)

                    # Botón Cargar
                    btn_cargar = tk.Button(
                        frame_btns,
                        text="📂 Cargar",
                        command=lambda nombre=flujo_nombre: self._cargar_flujo_rapido(
                            nombre
                        ),
                        bg="#27ae60",
                        fg="white",
                        font=("Segoe UI", 8, "bold"),
                        padx=8,
                        pady=3,
                        relief=tk.FLAT,
                        cursor="hand2",
                    )
                    btn_cargar.pack(side=tk.LEFT, padx=2)

                    # Botón Eliminar
                    btn_eliminar = tk.Button(
                        frame_btns,
                        text="🗑️",
                        command=lambda nombre=flujo_nombre: self._eliminar_flujo_rapido(
                            nombre
                        ),
                        bg="#e74c3c",
                        fg="white",
                        font=("Segoe UI", 8, "bold"),
                        padx=5,
                        pady=3,
                        relief=tk.FLAT,
                        cursor="hand2",
                    )
                    btn_eliminar.pack(side=tk.LEFT, padx=2)

        # ==========================================
        # 3. Actualizar lista antigua si existe
        # ==========================================
        if hasattr(self, "lista_flujos"):
            self.lista_flujos.delete(0, tk.END)
            for flujo in flujos:
                self.lista_flujos.insert(tk.END, flujo)

    def _mostrar_info_flujo(self, event=None):
        nombre = self.flujo_seleccionado_var.get()
        if not nombre:
            return
        flujo = self.flujo_manager.obtener_flujo(nombre)
        if flujo:
            desc = flujo.get("descripcion", "")
            pasos = len(flujo.get("pasos", []))
            self.label_info_flujo.config(text=f"📝 {desc} | {pasos} pasos")
        else:
            self.label_info_flujo.config(text="")

    def _cargar_flujo_seleccionado(self):
        selection = self.lista_flujos.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un flujo")
            return
        nombre = self.lista_flujos.get(selection[0])
        self.combo_flujos.set(nombre)
        self._mostrar_info_flujo()
        messagebox.showinfo("Flujo cargado", f"Flujo '{nombre}' cargado para ejecución")

    def _eliminar_flujo_seleccionado(self):
        selection = self.lista_flujos.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un flujo")
            return
        nombre = self.lista_flujos.get(selection[0])
        if messagebox.askyesno("Confirmar", f"¿Eliminar el flujo '{nombre}'?"):
            if self.flujo_manager.eliminar_flujo(nombre):
                messagebox.showinfo("Éxito", f"Flujo '{nombre}' eliminado")
                self.actualizar_lista_flujos()
            else:
                messagebox.showerror("Error", "No se pudo eliminar el flujo")

    def _ver_pasos_flujo(self):
        selection = self.lista_flujos.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un flujo")
            return
        nombre = self.lista_flujos.get(selection[0])
        flujo = self.flujo_manager.obtener_flujo(nombre)
        if not flujo:
            return
        ventana = tk.Toplevel(self.root)
        ventana.title(f"📋 Pasos del Flujo: {nombre}")
        ventana.geometry("700x500")
        ventana.configure(bg="#f0f2f5")
        text = scrolledtext.ScrolledText(ventana, font=("Consolas", 9), wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, f"📋 FLUJO: {nombre}\n")
        text.insert(tk.END, f"📝 Descripción: {flujo.get('descripcion', '')}\n")
        text.insert(tk.END, f"{'='*60}\n\n")
        for i, paso in enumerate(flujo.get("pasos", []), 1):
            text.insert(tk.END, f"Paso {i}: {paso.descripcion or paso.tipo.value}\n")
            text.insert(tk.END, f"  Tipo: {paso.tipo.value}\n")
            if paso.selector:
                text.insert(tk.END, f"  Selector: {paso.selector}\n")
            if paso.valor:
                text.insert(tk.END, f"  Valor: {paso.valor}\n")
            text.insert(tk.END, f"  {'-'*40}\n")
        text.config(state=tk.DISABLED)

    # ==========================================
    #  MÉTODOS DE LOG
    # ==========================================

    def log(self, mensaje, tipo="info"):
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda: self._log_ui(mensaje, tipo))
        else:
            self._log_ui(mensaje, tipo)

    def _log_ui(self, mensaje, tipo="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] ", "time")
        self.log_text.insert(tk.END, f"{mensaje}\n", tipo)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

        # Actualizar barra de estado con el último mensaje
        if hasattr(self, "label_estado"):
            colores = {
                "info": "#3498db",
                "success": "#27ae60",
                "error": "#e74c3c",
                "warning": "#f39c12",
                "stop": "#e74c3c",
            }
            color = colores.get(tipo, "#2c3e50")
            self.label_estado.config(text=mensaje[:50], fg=color)

    def _limpiar_log(self):
        self.log_text.delete(1.0, tk.END)

    def _exportar_log(self):
        filename = filedialog.asksaveasfilename(
            title="Exportar Log",
            defaultextension=".txt",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("Éxito", f"Log exportado a {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al exportar: {e}")

    # ==========================================
    #  MÉTODOS DE PRUEBAS
    # ==========================================

    def _actualizar_campos_prueba(self, event=None):
        tipo = self.test_tipo_var.get()

        estado_selector = "normal"
        estado_valor = "normal"

        if tipo in [
            "click",
            "esperar",
            "javascript",
            "scroll",
            "validar",
            "obtener_texto",
            "si_existe",
        ]:
            if tipo != "escribir" and tipo != "seleccionar":
                estado_valor = "disabled"

        try:
            self.entry_test_selector.config(state=estado_selector)
            self.entry_test_valor.config(state=estado_valor)
        except:
            pass

    def _ejecutar_prueba(self):
        global DRIVER_ACTUAL

        if not DRIVER_ACTUAL:
            messagebox.showwarning(
                "Advertencia", "Primero abre el navegador con 'Abrir Navegador'"
            )
            return

        tipo = TipoAccion(self.test_tipo_var.get())
        selector = self.test_selector_var.get().strip() or None
        selector_tipo = SelectorTipo(self.test_selector_tipo_var.get())
        valor = self.test_valor_var.get().strip() or None

        # ==========================================
        # NUEVO: Construir variables disponibles
        # ==========================================
        variables_prueba = self._obtener_variables_prueba()

        # Reemplazar variables en selector y valor
        if selector:
            selector = self._reemplazar_variables_texto(selector, variables_prueba)
        if valor:
            valor = self._reemplazar_variables_texto(valor, variables_prueba)

        # Mostrar en resultados
        self.test_result_text.delete(1.0, tk.END)
        self.test_result_text.insert(tk.END, f"🧪 Probando: {tipo.value}\n")
        self.test_result_text.insert(
            tk.END, f"Selector original: {self.test_selector_var.get()}\n"
        )
        self.test_result_text.insert(tk.END, f"Selector real: {selector or 'N/A'}\n")
        self.test_result_text.insert(
            tk.END, f"Valor original: {self.test_valor_var.get()}\n"
        )
        self.test_result_text.insert(tk.END, f"Valor real: {valor or 'N/A'}\n")
        self.test_result_text.insert(tk.END, f"{'='*50}\n\n")

        paso = Paso(
            tipo=tipo,
            selector=selector,
            selector_tipo=selector_tipo,
            valor=valor,
            segundos=1,
            descripcion=f"Prueba de {tipo.value}",
        )

        motor = MotorFlujos(DRIVER_ACTUAL, self, variables_prueba)

        def ejecutar():
            try:
                if selector:
                    try:
                        by = paso.get_by()
                        elemento = WebDriverWait(DRIVER_ACTUAL, 5).until(
                            EC.presence_of_element_located((by, selector))
                        )
                        self.root.after(
                            0,
                            lambda: self.test_result_text.insert(
                                tk.END, f"✅ Elemento encontrado: {selector}\n\n"
                            ),
                        )
                    except Exception as e:
                        self.root.after(
                            0,
                            lambda: self.test_result_text.insert(
                                tk.END,
                                f"❌ Elemento NO encontrado: {selector}\n"
                                f"Error: {str(e)[:200]}\n\n",
                            ),
                        )
                        return

                resultado = motor._ejecutar_paso(paso)

                def actualizar_resultado():
                    if resultado:
                        self.test_result_text.insert(tk.END, "✅ PRUEBA EXITOSA\n")

                        paso_guardado = Paso(
                            tipo=tipo,
                            selector=self.test_selector_var.get().strip()
                            or None,  # Guardar con variables originales
                            selector_tipo=selector_tipo,
                            valor=self.test_valor_var.get().strip()
                            or None,  # Guardar con variables originales
                            segundos=1,
                            descripcion=f"Prueba de {tipo.value}",
                            variable_guardar=None,
                            condicion=None,
                            repeticiones=1,
                            pasos_condicionales=[],
                        )
                        self.historial_pruebas.append(paso_guardado)
                        self.test_result_text.insert(
                            tk.END, "\n💾 Prueba agregada al historial\n"
                        )
                        self.test_result_text.insert(
                            tk.END, f"📝 Total pasos: {len(self.historial_pruebas)}\n"
                        )
                    else:
                        self.test_result_text.insert(tk.END, "❌ PRUEBA FALLIDA\n")

                self.root.after(0, actualizar_resultado)

            except Exception as e:

                def actualizar_error():
                    self.test_result_text.insert(tk.END, f"❌ ERROR: {str(e)}\n")

                self.root.after(0, actualizar_error)

        threading.Thread(target=ejecutar, daemon=True).start()

    def _obtener_variables_prueba(self):
        """Obtiene todas las variables disponibles para pruebas"""
        variables = {}

        # ==========================================
        # 1. Variables de CONFIGURACIÓN
        # ==========================================
        for key, entry in self.config_vars.items():
            key_upper = key.upper()
            valor = entry.get().strip()
            if valor:
                variables[key_upper] = valor
            else:
                variables[key_upper] = ""

        # ==========================================
        # 2. Variables del EXCEL (primera fila)
        # ==========================================
        excel_path = self.config_vars.get("excel_otps", None)

        if excel_path and excel_path.get().strip():
            try:
                df = pd.read_excel(excel_path.get().strip(), dtype=str)
                df = df.fillna("")

                if len(df) > 0:
                    primera_fila = df.iloc[0]

                    for columna in df.columns:
                        nombre_var = self._normalizar_nombre_variable(columna)
                        valor = str(primera_fila[columna])
                        if valor == "nan":
                            valor = ""

                        # Agregar con nombre normalizado
                        variables[nombre_var] = valor

                        # Agregar con nombre original
                        variables[columna] = valor

                        # Agregar alias comunes
                        if nombre_var == "OT":
                            variables["OT"] = valor
                        elif "CONTROLLER" in nombre_var:
                            variables["CONTROLLER"] = valor
                        elif nombre_var == "CAJA":
                            variables["CAJA"] = valor

            except Exception as e:
                self.log(f"⚠️ No se pudo leer Excel para variables: {e}", "warning")

        # ==========================================
        # 3. Variables estándar
        # ==========================================
        variables["USUARIO"] = (
            self.config_vars.get("usuario", tk.StringVar(value="")).get().strip()
        )
        variables["PASSWORD"] = (
            self.config_vars.get("password", tk.StringVar(value="")).get().strip()
        )
        variables["URL_LOGIN"] = (
            self.config_vars.get("url_login", tk.StringVar(value="")).get().strip()
        )
        variables["EXCEL_OTPS"] = (
            self.config_vars.get("excel_otps", tk.StringVar(value="")).get().strip()
        )

        return variables

    def _reemplazar_variables_texto(self, texto, variables):
        """Reemplaza {VARIABLE} con su valor real"""
        if not texto:
            return texto

        for key, value in variables.items():
            texto = texto.replace(f"{{{key}}}", str(value))

        return texto

    def _recargar_variables_excel(self):
        """Fuerza la recarga de variables del Excel y las muestra"""
        variables = self._obtener_variables_prueba()

        # Mostrar resumen en el panel de resultados
        self.test_result_text.delete(1.0, tk.END)
        self.test_result_text.insert(tk.END, "🔄 VARIABLES CARGADAS\n")
        self.test_result_text.insert(tk.END, f"{'='*50}\n\n")

        # Mostrar variables de configuración
        self.test_result_text.insert(tk.END, "⚙️ CONFIGURACIÓN:\n")
        for key, value in variables.items():
            if key in [
                "USUARIO",
                "PASSWORD",
                "URL_LOGIN",
                "EXCEL_OTPS",
                "BRAVE_PATH",
                "CHROMEDRIVER_PATH",
            ]:
                self.test_result_text.insert(tk.END, f"  {{{key}}} = {value}\n")

        # Mostrar variables del Excel
        self.test_result_text.insert(tk.END, "\n📊 EXCEL:\n")
        for key, value in variables.items():
            if key not in [
                "USUARIO",
                "PASSWORD",
                "URL_LOGIN",
                "EXCEL_OTPS",
                "BRAVE_PATH",
                "CHROMEDRIVER_PATH",
            ]:
                if value:
                    self.test_result_text.insert(tk.END, f"  {{{key}}} = {value}\n")

        self.test_result_text.insert(tk.END, f"\n{'='*50}\n")
        self.test_result_text.insert(
            tk.END, f"✅ {len(variables)} variables disponibles\n"
        )
        self.test_result_text.insert(
            tk.END, "📌 Ya puedes usar {VARIABLE} en tus pruebas\n"
        )

        # Actualizar barra de estado
        self.log(f"🔄 Variables recargadas: {len(variables)} disponibles", "success")

    def _abrir_navegador_prueba(self):
        global DRIVER_ACTUAL

        valores = {}
        for key, entry in self.config_vars.items():
            key_upper = key.upper()
            valores[key_upper] = entry.get().strip()

        if not valores.get("URL_LOGIN"):
            messagebox.showerror("Error", "Configura la URL_LOGIN primero")
            return

        if DRIVER_ACTUAL:
            messagebox.showinfo("Info", "El navegador ya está abierto")
            return

        self.log("🌐 Abriendo navegador para pruebas...", "info")

        def abrir():
            driver = self._abrir_navegador_y_url(valores)
            if driver:
                self.root.after(
                    0, lambda: self.log("✅ Navegador abierto para pruebas", "success")
                )
            else:
                self.root.after(
                    0, lambda: self.log("❌ Error al abrir navegador", "error")
                )

        threading.Thread(target=abrir, daemon=True).start()

    def _cerrar_navegador_prueba(self):
        global DRIVER_ACTUAL

        if DRIVER_ACTUAL:
            try:
                DRIVER_ACTUAL.quit()
                self.log("✅ Navegador de pruebas cerrado", "success")
            except:
                pass
            finally:
                DRIVER_ACTUAL = None
                self.driver_actual = None
                self.label_estado_navegador.config(
                    text="⚠️ Navegador cerrado", foreground="red"
                )
        else:
            messagebox.showinfo("Info", "No hay navegador abierto")

    # ==========================================
    #  MÉTODOS DE EJECUCIÓN
    # ==========================================

    def _obtener_pid_driver(self, driver):
        try:
            if hasattr(driver, "service") and hasattr(driver.service, "process"):
                chromedriver_pid = driver.service.process.pid

                try:
                    chromedriver_proc = psutil.Process(chromedriver_pid)
                    hijos = chromedriver_proc.children(recursive=True)
                    for hijo in hijos:
                        if (
                            "chrome" in hijo.name().lower()
                            or "brave" in hijo.name().lower()
                        ):
                            return hijo.pid
                except:
                    pass

                return chromedriver_pid
        except Exception as e:
            self.log(f"⚠️ Error obteniendo PID: {e}", "warning")
        return None

    def _matar_proceso_especifico(self, pid):
        if not pid:
            return

        try:
            proceso = psutil.Process(pid)

            for hijo in proceso.children(recursive=True):
                try:
                    hijo.kill()
                except:
                    pass

            proceso.kill()

        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            self.log(f"⚠️ Error al matar proceso {pid}: {e}", "warning")

    def detener_ejecucion(self):
        global DETENER_EJECUCION, DRIVER_ACTUAL

        self.log("🛑 ⚠️ DETENIENDO EJECUCIÓN...", "stop")
        self.status_label.config(text="🛑 Deteniendo...")

        # Actualizar barra de estado
        if hasattr(self, "label_estado"):
            self.label_estado.config(text="⏹ Detenido", fg="#e74c3c")

        DETENER_EJECUCION = True

        if DRIVER_ACTUAL:
            try:
                if not self.driver_pid:
                    self.driver_pid = self._obtener_pid_driver(DRIVER_ACTUAL)

                DRIVER_ACTUAL.quit()
                self.log("✅ Driver cerrado correctamente", "success")
            except Exception as e:
                self.log(f"⚠️ Error al cerrar driver: {e}", "warning")
            finally:
                DRIVER_ACTUAL = None

        if self.driver_pid:
            self._matar_proceso_especifico(self.driver_pid)
            self.driver_pid = None

        self.btn_detener.config(state="disabled")
        self.btn_ejecutar.config(state=tk.NORMAL, text="▶️ Ejecutar Automatización")
        self.ejecutando = False
        self.driver_actual = None
        self.label_estado_navegador.config(
            text="⚠️ Navegador cerrado", foreground="red"
        )
        self.status_label.config(text="✅ Detenido")

    def _abrir_navegador_y_url(self, config):
        global DRIVER_ACTUAL

        BRAVE_PATH = config.get("BRAVE_PATH", "")
        URL_LOGIN = config.get("URL_LOGIN", "")
        CHROMEDRIVER_PATH = config.get("CHROMEDRIVER_PATH", "")

        if not BRAVE_PATH:
            self.log("❌ BRAVE_PATH no configurado", "error")
            return None

        if not URL_LOGIN:
            self.log("❌ URL_LOGIN no configurada", "error")
            return None

        try:
            self.log(f"🌐 Abriendo navegador en {URL_LOGIN}...", "info")

            options = Options()
            options.binary_location = BRAVE_PATH
            options.add_argument("--start-maximized")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-extensions")
            options.add_argument("--remote-allow-origins=*")

            service = Service(CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)

            self.driver_pid = self._obtener_pid_driver(driver)

            driver.get(URL_LOGIN)
            time.sleep(2)

            self.log(f"✅ Navegador abierto en {URL_LOGIN}", "success")
            self.label_estado_navegador.config(
                text="✅ Navegador abierto", foreground="green"
            )

            DRIVER_ACTUAL = driver
            self.driver_actual = driver

            return driver

        except Exception as e:
            self.log(f"❌ Error al abrir navegador: {e}", "error")
            return None

    def ejecutar_automatizacion(self):
        global DETENER_EJECUCION

        if self.ejecutando:
            messagebox.showwarning("Advertencia", "⚠️ Ya hay una ejecución en progreso")
            return

        for key, entry in self.config_vars.items():
            if not entry.get().strip():
                messagebox.showerror("Error", f"El campo {key} está vacío")
                return

        valores = {}
        for key, entry in self.config_vars.items():
            key_upper = key.upper()
            valores[key_upper] = entry.get().strip()

        DETENER_EJECUCION = False

        self.ejecutando = True
        self.btn_ejecutar.config(state="disabled", text="⏳ Ejecutando...")
        self.btn_detener.config(state="normal")
        self.status_label.config(text="🔄 Ejecutando...")

        flujo_login_nombre = self.flujo_login_var.get()  # LOGIN
        flujo_asignacion_nombre = self.flujo_seleccionado_var.get()  # ASIGNACIÓN

        if not flujo_asignacion_nombre:
            self.log("📋 No hay flujo de asignación seleccionado", "error")
            self._finalizar_ejecucion()
            return

        flujo_asignacion = self.flujo_manager.obtener_flujo(flujo_asignacion_nombre)
        if not flujo_asignacion:
            messagebox.showerror(
                "Error", f"No se encontró el flujo '{flujo_asignacion_nombre}'"
            )
            self._finalizar_ejecucion()
            return

        flujo_login = None
        if flujo_login_nombre and flujo_login_nombre != flujo_asignacion_nombre:
            flujo_login = self.flujo_manager.obtener_flujo(flujo_login_nombre)

        self.log(
            f"🔐 Flujo Login: {flujo_login_nombre if flujo_login else 'No seleccionado'}",
            "info",
        )
        self.log(f"📋 Flujo Asignación: {flujo_asignacion_nombre}", "info")
        self.root.update_idletasks()

        self.hilo_ejecucion = threading.Thread(
            target=self._ejecutar_automatizacion_hilo,
            args=(valores, flujo_asignacion, flujo_login),
            daemon=True,
        )
        self.hilo_ejecucion.start()

    def _ejecutar_automatizacion_hilo(self, config, flujo_asignacion, flujo_login=None):
        global DETENER_EJECUCION, DRIVER_ACTUAL

        try:
            self._ejecutar_flujo_con_logs(config, flujo_asignacion, flujo_login)
        except Exception as e:
            self.root.after(
                0, lambda: self.log(f"❌ Error en la ejecución: {str(e)}", "error")
            )
            self.root.after(
                0, lambda: self.status_label.config(text="❌ Error en la ejecución")
            )
        finally:
            self.root.after(0, self._finalizar_ejecucion)

    def _finalizar_ejecucion(self):
        global DETENER_EJECUCION, DRIVER_ACTUAL

        self.ejecutando = False
        DETENER_EJECUCION = False

        self.btn_ejecutar.config(state=tk.NORMAL, text="▶️ Ejecutar Automatización")
        self.btn_detener.config(state="disabled")

        if DRIVER_ACTUAL:
            self.label_estado_navegador.config(
                text="✅ Navegador abierto", foreground="green"
            )
        else:
            self.label_estado_navegador.config(
                text="⚠️ Navegador cerrado", foreground="red"
            )

        self.driver_actual = None
        DRIVER_ACTUAL = None
        self.driver_pid = None

        self.log("✅ Automatización finalizada", "success")
        self.status_label.config(text="✅ Automatización finalizada")
        # Actualizar barra de estado
        if hasattr(self, "label_estado"):
            self.label_estado.config(text="✅ Listo", fg="white")

    def _normalizar_nombre_variable(self, nombre_columna):
        """Convierte el nombre de una columna en un nombre de variable válido"""
        nombre = str(nombre_columna).upper()

        reemplazos = {
            "Á": "A",
            "É": "E",
            "Í": "I",
            "Ó": "O",
            "Ú": "U",
            "Ñ": "N",
            "Ü": "U",
            " ": "_",
            "-": "_",
            ".": "_",
            "/": "_",
            "\\": "_",
            "(": "",
            ")": "",
            "[": "",
            "]": "",
            "{": "",
            "}": "",
            ":": "_",
            ";": "_",
            ",": "_",
            "+": "_",
            "*": "_",
            "?": "",
            "!": "",
            "¿": "",
            "¡": "",
            '"': "",
            "'": "",
            "`": "",
            "^": "",
            "~": "",
            "|": "_",
            "&": "_",
            "%": "_",
            "$": "_",
            "#": "_",
            "@": "_",
            "<": "_",
            ">": "_",
            "=": "_",
        }

        for char_especial, reemplazo in reemplazos.items():
            nombre = nombre.replace(char_especial, reemplazo)

        nombre = re.sub(r"_+", "_", nombre)
        nombre = nombre.strip("_")

        return nombre

    def _ejecutar_flujo_con_logs(self, config, flujo_asignacion, flujo_login=None):
        global DETENER_EJECUCION, DRIVER_ACTUAL

        USUARIO = config.get("USUARIO", "")
        PASSWORD = config.get("PASSWORD", "")
        URL_LOGIN = config.get("URL_LOGIN", "")
        EXCEL_OTPS = config.get("EXCEL_OTPS", "")
        BRAVE_PATH = config.get("BRAVE_PATH", "")
        CHROMEDRIVER_PATH = config.get("CHROMEDRIVER_PATH", "")

        driver = None
        start_time = time.time()

        try:
            if DETENER_EJECUCION:
                return

            # Leer Excel
            self.root.after(0, lambda: self.log("📊 Leyendo Excel...", "info"))

            df = None
            try:
                df = pd.read_excel(EXCEL_OTPS, dtype=str)
                df = df.fillna("")
                self.root.after(
                    0,
                    lambda: self.log(
                        f"✅ Excel cargado: {len(df)} registros", "success"
                    ),
                )
            except Exception as e:
                self.root.after(
                    0, lambda: self.log(f"❌ Error leyendo Excel: {e}", "error")
                )
                return

            # Abrir navegador
            self.root.after(0, lambda: self.log("🌐 Abriendo navegador...", "info"))
            driver = self._abrir_navegador_y_url(config)

            if not driver:
                return

            # ==========================================
            # EJECUTAR LOGIN PRIMERO (UNA SOLA VEZ)
            # ==========================================
            if flujo_login:
                self.root.after(
                    0,
                    lambda: self.log(
                        f"🔐 Ejecutando login: {flujo_login['nombre']}...", "info"
                    ),
                )
                variables_login = {
                    "USUARIO": USUARIO,
                    "PASSWORD": PASSWORD,
                    "URL_LOGIN": URL_LOGIN,
                    "BRAVE_PATH": BRAVE_PATH,
                    "CHROMEDRIVER_PATH": CHROMEDRIVER_PATH,
                }
                motor_login = MotorFlujos(driver, self, variables_login)
                login_exitoso = motor_login.ejecutar_flujo(flujo_login)

                if not login_exitoso:
                    self.root.after(
                        0, lambda: self.log("❌ Error en login, abortando", "error")
                    )
                    return

                self.root.after(0, lambda: self.log("✅ Login exitoso", "success"))

            # ==========================================
            # PROCESAR CADA OT DEL EXCEL
            # ==========================================
            total_filas = len(df)
            filas_exitosas = 0
            filas_fallidas = 0

            for idx, fila in df.iterrows():
                if DETENER_EJECUCION:
                    break

                self.root.after(
                    0, lambda i=idx + 1, t=total_filas: self.log(f"\n{'='*60}", "info")
                )
                self.root.after(
                    0,
                    lambda i=idx + 1, t=total_filas: self.log(
                        f"👉 Procesando OT {i}/{t}", "info"
                    ),
                )
                self.root.after(0, lambda: self.log(f"{'='*60}", "info"))

                # Variables base
                variables_base = {
                    "USUARIO": USUARIO,
                    "PASSWORD": PASSWORD,
                    "URL_LOGIN": URL_LOGIN,
                    "EXCEL_OTPS": EXCEL_OTPS,
                    "BRAVE_PATH": BRAVE_PATH,
                    "CHROMEDRIVER_PATH": CHROMEDRIVER_PATH,
                }

                # Leer todas las columnas automáticamente
                for columna in df.columns:
                    valor = str(fila.get(columna, "")).strip()
                    nombre_var = self._normalizar_nombre_variable(columna)

                    if valor and valor != "nan":
                        variables_base[nombre_var] = valor
                    else:
                        variables_base[nombre_var] = ""

                    variables_base[columna] = valor

                # Variables estándar
                if "OT" in df.columns:
                    variables_base["OT"] = str(fila.get("OT", "")).strip()
                if "Controller Responsable" in df.columns:
                    variables_base["CONTROLLER"] = str(
                        fila.get("Controller Responsable", "")
                    ).strip()
                if "Caja" in df.columns:
                    variables_base["CAJA"] = (
                        str(fila.get("Caja", "")).strip() or "PUESTA EN MARCHA"
                    )

                # Ejecutar flujo de asignación
                motor = MotorFlujos(driver, self, variables_base)
                exito = motor.ejecutar_flujo(flujo_asignacion)

                if exito:
                    filas_exitosas += 1
                    for col in ["Estado BOT", "Estado", "ESTADO"]:
                        if col in df.columns:
                            df.at[idx, col] = "ASIGNACION CORRECTA EN CONSENSUS"
                            break
                else:
                    filas_fallidas += 1
                    for col in ["Estado BOT", "Estado", "ESTADO"]:
                        if col in df.columns:
                            df.at[idx, col] = "ERROR"
                            break

                time.sleep(2)

            # Guardar Excel
            try:
                df.to_excel(EXCEL_OTPS, index=False, engine="openpyxl")
                self.root.after(0, lambda: self.log("✅ Excel actualizado", "success"))
            except:
                pass

            # Resumen
            tiempo = int(time.time() - start_time)
            self.root.after(0, lambda: self.log(f"\n{'='*60}", "info"))
            self.root.after(
                0, lambda: self.log(f"✅ Exitosas: {filas_exitosas}", "success")
            )
            self.root.after(
                0, lambda: self.log(f"❌ Fallidas: {filas_fallidas}", "error")
            )
            self.root.after(
                0,
                lambda: self.log(f"⏱️ Tiempo: {tiempo // 60}m {tiempo % 60}s", "info"),
            )

        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Error crítico: {str(e)}", "error"))
            raise
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            DRIVER_ACTUAL = None
            self.driver_actual = None

    def _crear_tab_editor(self):
        """Crea la pestaña del editor de flujos"""
        self.editor_frame = ttk.Frame(self.tab_editor)
        self.editor_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            self.editor_frame, text="📝 Editor de Flujos", style="Title.TLabel"
        ).pack(pady=20)
        ttk.Label(self.editor_frame, text="Crea y modifica flujos visualmente").pack()

        btn_abrir_editor = tk.Button(
            self.editor_frame,
            text="✏️ Abrir Editor de Flujos",
            command=self._abrir_editor_flujos,
            bg="#3498db",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            padx=30,
            pady=15,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn_abrir_editor.pack(pady=30)

    def _abrir_editor_flujos(self):
        """Abre la ventana del editor de flujos"""
        EditorFlujosUI(self.root, self.flujo_manager)
        self.actualizar_lista_flujos()

    def _guardar_prueba_en_flujo(self):
        """Guarda la prueba actual como paso en un flujo existente o nuevo"""
        global DRIVER_ACTUAL

        # Obtener los valores de la prueba
        tipo = self.test_tipo_var.get()
        selector = self.test_selector_var.get().strip()
        selector_tipo = self.test_selector_tipo_var.get()
        valor = self.test_valor_var.get().strip()

        if not selector and tipo not in ["esperar", "javascript"]:
            messagebox.showwarning(
                "Advertencia", "El selector es obligatorio para esta acción"
            )
            return

        # Crear el paso
        paso = Paso(
            tipo=TipoAccion(tipo),
            selector=selector if selector else None,
            selector_tipo=SelectorTipo(selector_tipo),
            valor=valor if valor else None,
            segundos=1,
            descripcion=f"Prueba de {tipo}",
            variable_guardar=None,
            condicion=None,
            repeticiones=1,
            pasos_condicionales=[],
        )

        # Preguntar si quiere guardar en flujo existente o crear nuevo
        opcion = messagebox.askyesnocancel(
            "Guardar Paso",
            "¿Desea guardar este paso en un flujo?\n\n"
            "SÍ = Guardar en flujo existente\n"
            "NO = Crear nuevo flujo\n"
            "Cancelar = No guardar",
        )

        if opcion is None:  # Cancelar
            return

        if opcion:  # SÍ = flujo existente
            self._guardar_en_flujo_existente(paso)
        else:  # NO = crear nuevo flujo
            self._guardar_en_flujo_nuevo(paso)

    def _guardar_en_flujo_existente(self, paso):
        """Guarda el paso en un flujo existente"""
        flujos = self.flujo_manager.listar_flujos()

        if not flujos:
            messagebox.showinfo("Info", "No hay flujos creados. Se creará uno nuevo.")
            self._guardar_en_flujo_nuevo(paso)
            return

        # Crear ventana de selección
        ventana = tk.Toplevel(self.root)
        ventana.title("📂 Seleccionar Flujo")
        ventana.geometry("400x300")
        ventana.configure(bg="#f0f2f5")
        ventana.transient(self.root)

        tk.Label(
            ventana,
            text="Seleccione el flujo donde guardar:",
            bg="#f0f2f5",
            font=("Segoe UI", 10),
        ).pack(pady=10)

        combo = ttk.Combobox(ventana, values=flujos, state="readonly", width=30)
        combo.pack(pady=10)
        if flujos:
            combo.set(flujos[0])

        def guardar():
            nombre_flujo = combo.get()
            if not nombre_flujo:
                messagebox.showwarning(
                    "Advertencia", "Seleccione un flujo", parent=ventana
                )
                return

            flujo = self.flujo_manager.obtener_flujo(nombre_flujo)
            if not flujo:
                messagebox.showerror("Error", "No se encontró el flujo", parent=ventana)
                return

            # Agregar el paso al flujo
            pasos = flujo["pasos"].copy()
            pasos.append(paso)

            exito, mensaje = self.flujo_manager.actualizar_flujo(
                nombre_flujo, flujo["descripcion"], pasos
            )

            if exito:
                messagebox.showinfo(
                    "Éxito", f"Paso guardado en flujo '{nombre_flujo}'", parent=ventana
                )
                self.log(f"✅ Paso guardado en flujo '{nombre_flujo}'", "success")
                self.actualizar_lista_flujos()
                ventana.destroy()
            else:
                messagebox.showerror("Error", mensaje, parent=ventana)

        tk.Button(
            ventana,
            text="💾 Guardar",
            command=guardar,
            bg="#27ae60",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(pady=10)

    def _guardar_en_flujo_nuevo(self, paso):
        """Crea un flujo nuevo con el paso"""
        # Pedir nombre del flujo
        nombre = simpledialog.askstring(
            "Nuevo Flujo", "Ingrese el nombre del nuevo flujo:", parent=self.root
        )

        if not nombre or nombre.strip() == "":
            return

        nombre = nombre.strip()

        # Preguntar si es flujo de login o de asignación
        tipo_flujo = messagebox.askyesno(
            "Tipo de Flujo",
            f"¿El flujo '{nombre}' es un flujo de LOGIN?\n\n"
            "SÍ = Login (se ejecuta una sola vez)\n"
            "NO = Asignación (se ejecuta para cada OT)",
        )

        descripcion = ""
        if tipo_flujo:
            descripcion = "Flujo de Login"
        else:
            descripcion = "Flujo de Asignación"

        # Guardar el flujo
        exito, mensaje = self.flujo_manager.guardar_flujo(nombre, descripcion, [paso])

        if exito:
            messagebox.showinfo("Éxito", f"Flujo '{nombre}' creado con el paso")
            self.log(f"✅ Flujo '{nombre}' creado exitosamente", "success")
            self.actualizar_lista_flujos()
        else:
            messagebox.showerror("Error", mensaje)

    def _guardar_historial_completo(self):
        """Guarda todas las pruebas del historial como un flujo completo"""
        if not self.historial_pruebas:
            messagebox.showwarning("Advertencia", "No hay pruebas en el historial")
            return

        nombre = simpledialog.askstring(
            "Guardar Flujo Completo",
            "Ingrese el nombre del flujo con todas las pruebas:",
            parent=self.root,
        )

        if not nombre or nombre.strip() == "":
            return

        nombre = nombre.strip()

        # Preguntar si es flujo de login o de asignación
        tipo_flujo = messagebox.askyesno(
            "Tipo de Flujo",
            f"¿El flujo '{nombre}' es un flujo de LOGIN?\n\n"
            "SÍ = Login (se ejecuta una sola vez)\n"
            "NO = Asignación (se ejecuta para cada OT)",
        )

        descripcion = "Flujo de Login" if tipo_flujo else "Flujo de Asignación"

        exito, mensaje = self.flujo_manager.guardar_flujo(
            nombre, descripcion, self.historial_pruebas.copy()
        )

        if exito:
            messagebox.showinfo(
                "Éxito",
                f"Flujo '{nombre}' creado con {len(self.historial_pruebas)} pasos",
            )
            self.log(
                f"✅ Flujo '{nombre}' creado con {len(self.historial_pruebas)} pasos",
                "success",
            )
            self.actualizar_lista_flujos()
            self.historial_pruebas.clear()
            self.log("🔄 Historial de pruebas limpiado", "info")
        else:
            messagebox.showerror("Error", mensaje)

    def _guardar_todas_las_pruebas(self):
        """Guarda todas las pruebas realizadas como pasos en un flujo"""
        # Esta función guarda el historial de pruebas
        pass

    def _cargar_flujo_para_pruebas(self):
        """Carga un flujo en el panel usando un select"""
        flujos = self.flujo_manager.listar_flujos()

        if not flujos:
            messagebox.showwarning("Advertencia", "No hay flujos creados")
            return

        # Crear ventana pequeña con select
        ventana = tk.Toplevel(self.root)
        ventana.title("📂 Cargar Flujo")
        ventana.geometry("350x150")
        ventana.configure(bg="#f0f2f5")
        ventana.transient(self.root)
        ventana.resizable(False, False)

        # Centrar
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (350 // 2)
        y = (ventana.winfo_screenheight() // 2) - (150 // 2)
        ventana.geometry(f"350x150+{x}+{y}")

        # Contenido
        tk.Label(
            ventana,
            text="Seleccione el flujo:",
            bg="#f0f2f5",
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(15, 5))

        combo = ttk.Combobox(ventana, values=flujos, state="readonly", width=30)
        combo.pack(pady=5)
        if flujos:
            combo.set(flujos[0])

        def cargar():
            nombre = combo.get()
            if not nombre:
                return

            flujo = self.flujo_manager.obtener_flujo(nombre)
            if not flujo:
                return

            # Guardar referencia
            self.flujo_prueba_actual = nombre
            self.paso_prueba_actual = 0

            # Actualizar panel
            self._actualizar_panel_flujo(flujo)

            self.log(
                f"📂 Flujo '{nombre}' cargado con {len(flujo['pasos'])} pasos",
                "success",
            )
            ventana.destroy()

        tk.Button(
            ventana,
            text="📂 Cargar",
            command=cargar,
            bg="#00bcd4",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(pady=10)

    def _actualizar_panel_flujo(self, flujo):
        """Actualiza el panel de flujo cargado con los pasos"""
        # Limpiar frame
        for widget in self.frame_pasos_flujo.winfo_children():
            widget.destroy()

        # Actualizar etiqueta
        self.label_flujo_nombre.config(text=f"📂 {flujo['nombre']}")

        # Mostrar cada paso
        for i, paso in enumerate(flujo["pasos"], 1):
            # Frame para cada paso (fondo blanco con borde)
            frame_paso = tk.Frame(
                self.frame_pasos_flujo, bg="white", relief=tk.RIDGE, bd=1
            )
            frame_paso.pack(fill=tk.X, pady=2, padx=3)

            # Información del paso
            desc = paso.descripcion or paso.tipo.value
            selector = paso.selector or ""
            valor = paso.valor or ""

            # Texto completo sin truncar
            info = f"Paso {i}: [{paso.tipo.value}] {desc}"
            if selector:
                info += f"  |  🔍 {selector}"
            if valor:
                info += f"  |  💬 {valor}"

            # Label con información (se expande horizontalmente)
            label = tk.Label(
                frame_paso,
                text=info,
                bg="white",
                fg="#2c3e50",
                font=("Consolas", 8),
                anchor="w",
                justify=tk.LEFT,
            )
            label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=3)

            # Frame para botones
            frame_btns = tk.Frame(frame_paso, bg="white")
            frame_btns.pack(side=tk.RIGHT, padx=3)

            # Botón Ejecutar paso
            btn_ejecutar = tk.Button(
                frame_btns,
                text="▶️",
                command=lambda idx=i - 1: self._ejecutar_paso_flujo(idx),
                bg="#27ae60",
                fg="white",
                font=("Segoe UI", 8, "bold"),
                padx=4,
                pady=1,
                relief=tk.FLAT,
                cursor="hand2",
                width=2,
            )
            btn_ejecutar.pack(side=tk.LEFT, padx=1)

            # Botón Editar paso
            btn_editar = tk.Button(
                frame_btns,
                text="✏️",
                command=lambda idx=i - 1: self._editar_paso_flujo(idx),
                bg="#f39c12",
                fg="white",
                font=("Segoe UI", 8, "bold"),
                padx=4,
                pady=1,
                relief=tk.FLAT,
                cursor="hand2",
                width=2,
            )
            btn_editar.pack(side=tk.LEFT, padx=1)

        # Actualizar scroll del canvas
        self.panel_flujo_cargado.update_idletasks()

    def _ejecutar_paso_flujo(self, indice):
        """Ejecuta un paso específico del flujo cargado"""
        global DRIVER_ACTUAL

        if not DRIVER_ACTUAL:
            messagebox.showwarning("Advertencia", "Primero abre el navegador")
            return

        flujo = self.flujo_manager.obtener_flujo(self.flujo_prueba_actual)
        if not flujo:
            return

        paso = flujo["pasos"][indice]

        # Cargar en campos de prueba
        self.test_tipo_var.set(paso.tipo.value)
        self.test_selector_var.set(paso.selector or "")
        self.test_selector_tipo_var.set(
            paso.selector_tipo.value if paso.selector_tipo else "xpath"
        )
        self.test_valor_var.set(paso.valor or "")
        self._actualizar_campos_prueba()
        self.paso_prueba_actual = indice

        # Ejecutar
        self._ejecutar_prueba()

    def _editar_paso_flujo(self, indice):
        """Carga un paso para editar"""
        flujo = self.flujo_manager.obtener_flujo(self.flujo_prueba_actual)
        if not flujo:
            return

        paso = flujo["pasos"][indice]

        self.test_tipo_var.set(paso.tipo.value)
        self.test_selector_var.set(paso.selector or "")
        self.test_selector_tipo_var.set(
            paso.selector_tipo.value if paso.selector_tipo else "xpath"
        )
        self.test_valor_var.set(paso.valor or "")
        self._actualizar_campos_prueba()
        self.paso_prueba_actual = indice
        self.modo_edicion_paso = True

        self.log(f"✏️ Editando paso {indice + 1}", "warning")

    def _guardar_cambios_paso(self):
        """Guarda los cambios realizados al paso en el flujo"""
        if not hasattr(self, "flujo_prueba_actual") or not hasattr(
            self, "paso_prueba_actual"
        ):
            messagebox.showwarning("Advertencia", "No hay un paso en modo edición")
            return

        flujo = self.flujo_manager.obtener_flujo(self.flujo_prueba_actual)
        if not flujo:
            messagebox.showerror("Error", "No se encontró el flujo")
            return

        # Obtener valores actuales de la prueba
        tipo = TipoAccion(self.test_tipo_var.get())
        selector = self.test_selector_var.get().strip() or None
        selector_tipo = SelectorTipo(self.test_selector_tipo_var.get())
        valor = self.test_valor_var.get().strip() or None

        # Crear el paso actualizado
        paso_actualizado = Paso(
            tipo=tipo,
            selector=selector,
            selector_tipo=selector_tipo,
            valor=valor,
            segundos=1,
            descripcion=f"Paso {self.paso_prueba_actual + 1} - {tipo.value}",
            variable_guardar=None,
            condicion=None,
            repeticiones=1,
            pasos_condicionales=[],
        )

        # Actualizar el paso en el flujo
        pasos = flujo["pasos"].copy()
        pasos[self.paso_prueba_actual] = paso_actualizado

        exito, mensaje = self.flujo_manager.actualizar_flujo(
            self.flujo_prueba_actual, flujo["descripcion"], pasos
        )

        if exito:
            messagebox.showinfo(
                "Éxito",
                f"Paso {self.paso_prueba_actual + 1} actualizado en flujo '{self.flujo_prueba_actual}'",
            )
            self.log(
                f"✅ Paso {self.paso_prueba_actual + 1} actualizado en flujo '{self.flujo_prueba_actual}'",
                "success",
            )
            self.actualizar_lista_flujos()

            # Limpiar modo edición
            delattr(self, "flujo_prueba_actual")
            delattr(self, "paso_prueba_actual")
            if hasattr(self, "modo_edicion_paso"):
                delattr(self, "modo_edicion_paso")
        else:
            messagebox.showerror("Error", mensaje)

    def _probar_siguiente_paso(self):
        """Carga el siguiente paso del flujo en pruebas"""
        if not hasattr(self, "flujo_prueba_actual") or not hasattr(
            self, "paso_prueba_actual"
        ):
            messagebox.showwarning("Advertencia", "No hay un flujo cargado en pruebas")
            return

        flujo = self.flujo_manager.obtener_flujo(self.flujo_prueba_actual)
        if not flujo:
            return

        siguiente = self.paso_prueba_actual + 1
        if siguiente >= len(flujo["pasos"]):
            messagebox.showinfo("Fin", "No hay más pasos en este flujo")
            return

        paso = flujo["pasos"][siguiente]

        # Cargar el siguiente paso
        self.test_tipo_var.set(paso.tipo.value)
        self.test_selector_var.set(paso.selector or "")
        self.test_selector_tipo_var.set(
            paso.selector_tipo.value if paso.selector_tipo else "xpath"
        )
        self.test_valor_var.set(paso.valor or "")
        self._actualizar_campos_prueba()

        self.paso_prueba_actual = siguiente

        self.log(
            f"📂 Paso {siguiente + 1} cargado: {paso.descripcion or paso.tipo.value}",
            "info",
        )

    def _ejecutar_flujo_completo_pruebas(self):
        """Ejecuta el flujo completo cargado en pruebas"""
        global DRIVER_ACTUAL

        if not DRIVER_ACTUAL:
            messagebox.showwarning("Advertencia", "Primero abre el navegador")
            return

        if not hasattr(self, "flujo_prueba_actual"):
            messagebox.showwarning(
                "Advertencia", "Primero carga un flujo con '📂 Cargar Flujo'"
            )
            return

        flujo = self.flujo_manager.obtener_flujo(self.flujo_prueba_actual)
        if not flujo:
            messagebox.showerror("Error", "No se encontró el flujo")
            return

        pasos = flujo["pasos"]
        if not pasos:
            messagebox.showwarning("Advertencia", "El flujo no tiene pasos")
            return

        # Confirmar
        if not messagebox.askyesno(
            "Confirmar",
            f"¿Ejecutar flujo completo '{self.flujo_prueba_actual}'?\n\n"
            f"Pasos: {len(pasos)}\n"
            "Se ejecutarán todos los pasos en orden.",
        ):
            return

        # Obtener variables
        variables_prueba = self._obtener_variables_prueba()

        # Limpiar resultados
        self.test_result_text.delete(1.0, tk.END)
        self.test_result_text.insert(
            tk.END, f"🚀 Ejecutando flujo completo: {self.flujo_prueba_actual}\n"
        )
        self.test_result_text.insert(tk.END, f"📋 Pasos: {len(pasos)}\n")
        self.test_result_text.insert(tk.END, f"{'='*50}\n\n")

        def ejecutar():
            motor = MotorFlujos(DRIVER_ACTUAL, self, variables_prueba)
            exitosos = 0
            fallidos = 0

            for i, paso in enumerate(pasos, 1):
                if DETENER_EJECUCION:
                    break

                self.root.after(
                    0,
                    lambda i=i: self.test_result_text.insert(
                        tk.END,
                        f"\n📌 Paso {i}/{len(pasos)}: {paso.descripcion or paso.tipo.value}\n",
                    ),
                )

                # Reemplazar variables en el paso
                paso_real = Paso(
                    tipo=paso.tipo,
                    selector=(
                        self._reemplazar_variables_texto(
                            paso.selector, variables_prueba
                        )
                        if paso.selector
                        else None
                    ),
                    selector_tipo=paso.selector_tipo,
                    valor=(
                        self._reemplazar_variables_texto(paso.valor, variables_prueba)
                        if paso.valor
                        else None
                    ),
                    segundos=paso.segundos,
                    javascript=paso.javascript,
                    descripcion=paso.descripcion,
                    variable_guardar=paso.variable_guardar,
                    condicion=paso.condicion,
                    repeticiones=paso.repeticiones,
                    pasos_condicionales=paso.pasos_condicionales,
                )

                resultado = motor._ejecutar_paso(paso_real)

                if resultado:
                    exitosos += 1
                    self.root.after(
                        0,
                        lambda i=i: self.test_result_text.insert(
                            tk.END, f"✅ Paso {i} exitoso\n"
                        ),
                    )
                else:
                    fallidos += 1
                    self.root.after(
                        0,
                        lambda i=i: self.test_result_text.insert(
                            tk.END, f"❌ Paso {i} falló\n"
                        ),
                    )

                    # Preguntar si continuar
                    continuar = messagebox.askyesno(
                        "Error en paso",
                        f"El paso {i} falló.\n\n"
                        "¿Desea continuar con el siguiente paso?",
                    )
                    if not continuar:
                        break

                time.sleep(1)

            # Resumen
            self.root.after(
                0,
                lambda: self.test_result_text.insert(
                    tk.END,
                    f"\n{'='*50}\n"
                    f"📊 RESUMEN: ✅ {exitosos} exitosos | ❌ {fallidos} fallidos | 📋 {len(pasos)} totales\n",
                ),
            )

            self.log(
                f"✅ Flujo completo: {exitosos} exitosos, {fallidos} fallidos",
                "success" if fallidos == 0 else "warning",
            )

        threading.Thread(target=ejecutar, daemon=True).start()

    def _cerrar_flujo_cargado(self):
        """Cierra el flujo cargado del panel"""
        self.flujo_prueba_actual = None
        self.paso_prueba_actual = None

        # Limpiar panel
        for widget in self.frame_pasos_flujo.winfo_children():
            widget.destroy()

        self.label_flujo_nombre.config(text="No hay flujo cargado")
        self.log("🔄 Flujo cerrado del panel", "info")

    def _ejecutar_desde_paso_actual(self):
        """Ejecuta el flujo desde el paso actual cargado"""
        global DRIVER_ACTUAL

        if not DRIVER_ACTUAL:
            messagebox.showwarning("Advertencia", "Primero abre el navegador")
            return

        if not hasattr(self, "flujo_prueba_actual") or not hasattr(
            self, "paso_prueba_actual"
        ):
            messagebox.showwarning("Advertencia", "Primero carga un paso del flujo")
            return

        flujo = self.flujo_manager.obtener_flujo(self.flujo_prueba_actual)
        if not flujo:
            return

        pasos = flujo["pasos"]
        paso_inicial = self.paso_prueba_actual

        if paso_inicial >= len(pasos):
            messagebox.showwarning("Advertencia", "No hay más pasos")
            return

        pasos_restantes = pasos[paso_inicial:]

        if not messagebox.askyesno(
            "Confirmar",
            f"¿Ejecutar desde el paso {paso_inicial + 1}?\n\n"
            f"Pasos restantes: {len(pasos_restantes)}",
        ):
            return

        variables_prueba = self._obtener_variables_prueba()

        self.test_result_text.delete(1.0, tk.END)
        self.test_result_text.insert(
            tk.END, f"🚀 Ejecutando desde paso {paso_inicial + 1}\n"
        )
        self.test_result_text.insert(tk.END, f"{'='*50}\n\n")

        def ejecutar():
            motor = MotorFlujos(DRIVER_ACTUAL, self, variables_prueba)
            exitosos = 0
            fallidos = 0

            for i, paso in enumerate(pasos_restantes, paso_inicial + 1):
                if DETENER_EJECUCION:
                    break

                self.root.after(
                    0,
                    lambda i=i: self.test_result_text.insert(
                        tk.END,
                        f"\n📌 Paso {i}/{len(pasos)}: {paso.descripcion or paso.tipo.value}\n",
                    ),
                )

                paso_real = Paso(
                    tipo=paso.tipo,
                    selector=(
                        self._reemplazar_variables_texto(
                            paso.selector, variables_prueba
                        )
                        if paso.selector
                        else None
                    ),
                    selector_tipo=paso.selector_tipo,
                    valor=(
                        self._reemplazar_variables_texto(paso.valor, variables_prueba)
                        if paso.valor
                        else None
                    ),
                    segundos=paso.segundos,
                    javascript=paso.javascript,
                    descripcion=paso.descripcion,
                    variable_guardar=paso.variable_guardar,
                    condicion=paso.condicion,
                    repeticiones=paso.repeticiones,
                    pasos_condicionales=paso.pasos_condicionales,
                )

                resultado = motor._ejecutar_paso(paso_real)

                if resultado:
                    exitosos += 1
                    self.root.after(
                        0,
                        lambda i=i: self.test_result_text.insert(
                            tk.END, f"✅ Paso {i} exitoso\n"
                        ),
                    )
                else:
                    fallidos += 1
                    self.root.after(
                        0,
                        lambda i=i: self.test_result_text.insert(
                            tk.END, f"❌ Paso {i} falló\n"
                        ),
                    )
                    continuar = messagebox.askyesno(
                        "Error", f"Paso {i} falló. ¿Continuar?"
                    )
                    if not continuar:
                        break

                time.sleep(1)

            self.root.after(
                0,
                lambda: self.test_result_text.insert(
                    tk.END,
                    f"\n{'='*50}\n"
                    f"📊 RESUMEN: ✅ {exitosos} | ❌ {fallidos} | 📋 {len(pasos_restantes)} restantes\n",
                ),
            )

        threading.Thread(target=ejecutar, daemon=True).start()

    def _ejecutar_solo_paso_actual(self):
        """Ejecuta solo el paso actual cargado en pruebas"""
        self._ejecutar_prueba()

    def _copiar_flujo(self):
        """Copia un flujo existente con nuevo nombre"""
        flujos = self.flujo_manager.listar_flujos()

        if not flujos:
            messagebox.showwarning("Advertencia", "No hay flujos para copiar")
            return

        # Crear ventana para copiar flujo
        ventana = tk.Toplevel(self.root)
        ventana.title("📋 Copiar Flujo")
        ventana.geometry("400x250")
        ventana.configure(bg="#f0f2f5")
        ventana.transient(self.root)
        ventana.resizable(False, False)

        # Centrar
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (400 // 2)
        y = (ventana.winfo_screenheight() // 2) - (250 // 2)
        ventana.geometry(f"400x250+{x}+{y}")

        # Selector de flujo original
        tk.Label(
            ventana, text="Flujo a copiar:", bg="#f0f2f5", font=("Segoe UI", 10, "bold")
        ).pack(pady=(15, 5))

        combo = ttk.Combobox(ventana, values=flujos, state="readonly", width=30)
        combo.pack(pady=5)
        if flujos:
            combo.set(flujos[0])

        # Campo para nuevo nombre
        tk.Label(
            ventana, text="Nuevo nombre:", bg="#f0f2f5", font=("Segoe UI", 10, "bold")
        ).pack(pady=(10, 5))

        entry_nuevo = ttk.Entry(ventana, width=30)
        entry_nuevo.pack(pady=5)

        def copiar():
            nombre_original = combo.get()
            nuevo_nombre = entry_nuevo.get().strip()

            if not nombre_original:
                messagebox.showwarning(
                    "Advertencia", "Seleccione un flujo", parent=ventana
                )
                return

            if not nuevo_nombre:
                messagebox.showwarning(
                    "Advertencia", "Ingrese el nuevo nombre", parent=ventana
                )
                return

            if nuevo_nombre == nombre_original:
                messagebox.showerror(
                    "Error", "El nuevo nombre debe ser diferente", parent=ventana
                )
                return

            exito, mensaje = self.flujo_manager.copiar_flujo(
                nombre_original, nuevo_nombre
            )

            if exito:
                messagebox.showinfo("Éxito", mensaje, parent=ventana)
                self.log(f"✅ {mensaje}", "success")
                self.actualizar_lista_flujos()
                ventana.destroy()
            else:
                messagebox.showerror("Error", mensaje, parent=ventana)

        tk.Button(
            ventana,
            text="📋 Copiar",
            command=copiar,
            bg="#3498db",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(pady=15)

    def _duplicar_flujo_seleccionado(self):
        """Duplica el flujo seleccionado en la lista"""
        selection = self.lista_flujos.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un flujo de la lista")
            return

        nombre_original = self.lista_flujos.get(selection[0])

        # Pedir nuevo nombre
        nuevo_nombre = simpledialog.askstring(
            "Duplicar Flujo",
            f"Flujo original: {nombre_original}\n\n" "Ingrese el nuevo nombre:",
            parent=self.root,
        )

        if not nuevo_nombre or nuevo_nombre.strip() == "":
            return

        nuevo_nombre = nuevo_nombre.strip()

        exito, mensaje = self.flujo_manager.copiar_flujo(nombre_original, nuevo_nombre)

        if exito:
            messagebox.showinfo("Éxito", mensaje)
            self.log(f"✅ {mensaje}", "success")
            self.actualizar_lista_flujos()
        else:
            messagebox.showerror("Error", mensaje)

    def _copiar_flujo_rapido(self, nombre):
        """Copia un flujo al portapapeles interno"""
        flujo = self.flujo_manager.obtener_flujo(nombre)
        if not flujo:
            return

        self.portapapeles_flujo = flujo
        self.portapapeles_nombre = nombre

        self.log(f"📋 Flujo '{nombre}' copiado. Use 'Pegar' para duplicar", "info")

        if hasattr(self, "label_estado"):
            self.label_estado.config(text=f"📋 Copiado: {nombre}", fg="#3498db")

    def _pegar_flujo_rapido(self):
        """Pega el flujo copiado con nuevo nombre"""
        if not hasattr(self, "portapapeles_flujo") or not self.portapapeles_flujo:
            messagebox.showwarning(
                "Advertencia", "Primero copie un flujo con '📋 Copiar'"
            )
            return

        nuevo_nombre = simpledialog.askstring(
            "Pegar Flujo",
            f"Flujo copiado: {self.portapapeles_nombre}\n\n" "Ingrese el nuevo nombre:",
            parent=self.root,
        )

        if not nuevo_nombre or nuevo_nombre.strip() == "":
            return

        nuevo_nombre = nuevo_nombre.strip()

        exito, mensaje = self.flujo_manager.guardar_flujo(
            nuevo_nombre,
            self.portapapeles_flujo.get("descripcion", ""),
            self.portapapeles_flujo.get("pasos", []),
            self.portapapeles_flujo.get("variables", {}),
        )

        if exito:
            messagebox.showinfo("Éxito", f"Flujo pegado como '{nuevo_nombre}'")
            self.log(f"✅ Flujo '{nuevo_nombre}' creado", "success")
            self.actualizar_lista_flujos()
        else:
            messagebox.showerror("Error", mensaje)

    def _cargar_flujo_rapido(self, nombre):
        """Carga el flujo en el combo de asignación"""
        self.combo_flujos.set(nombre)
        self._mostrar_info_flujo()
        self.log(f"📂 Flujo '{nombre}' cargado", "info")
        messagebox.showinfo("Cargado", f"Flujo '{nombre}' cargado en Configuración")

    def _eliminar_flujo_rapido(self, nombre):
        """Elimina un flujo directamente"""
        if messagebox.askyesno("Confirmar", f"¿Eliminar el flujo '{nombre}'?"):
            if self.flujo_manager.eliminar_flujo(nombre):
                self.log(f"🗑️ Flujo '{nombre}' eliminado", "warning")
                self.actualizar_lista_flujos()
            else:
                messagebox.showerror("Error", "No se pudo eliminar")


# ==========================================
#  MAIN
# ==========================================

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfiguracionUI(root)
    root.mainloop()
