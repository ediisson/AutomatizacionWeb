# 🤖 BOT_AutomatismoWeb

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.9-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/python-3.x-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/platform-windows-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License">
</p>

> Bot de automatización desarrollado esta pensado para ejecutar procesos repetitivos de manera controlada mediante flujos configurables.

---

## 📦 Versión

**v1.1.4**

---

## 📋 Tabla de Contenidos

- [🚀 Instalación](#-instalación)
- [🌐 ChromeDriver](#-chromedriver)
- [⚙️ Configuración](#️-configuración)
- [🔄 Sistema de Flujos](#-sistema-de-flujos)
- [🧪 Pruebas en tiempo real](#-pruebas-en-tiempo-real)
- [🎯 Captura automática de XPath](#-captura-automática-de-xpath)
- [📊 Integración con Excel](#-integración-con-excel)
- [🔤 Variables dinámicas](#-variables-dinámicas)
- [✏️ Editor de Flujos](#️-editor-de-flujos)
- [📋 Gestión de Flujos](#-gestión-de-flujos)
- [🔐 Flujo de LOGIN](#-flujo-de-login)
- [📋 Flujo de Tareas](#-flujo-de-tareas)
- [📋 Logs](#-logs)
- [🔄 Actualizaciones automáticas](#-actualizaciones-automáticas)
- [🛠️ Tecnologías](#️-tecnologías)
- [✅ Recomendaciones](#-recomendaciones-antes-de-ejecutar)
- [📌 Flujo de trabajo recomendado](#-flujo-de-trabajo-recomendado)
- [👨‍💻 Desarrollador](#-desarrollado-por)

---

## 🚀 Instalación

### 1. Descargar el BOT
Descarga la última versión disponible desde:  
[https://github.com/ediisson/AutomatizacionWeb/releases](https://github.com/ediisson/AutomatizacionWeb/releases)

### 2. Ejecutar
Descarga el archivo `BOT_AutomatismoWeb_v1.1.4.exe` y ejecútalo.

> **Nota:** No necesitas tener Python instalado para utilizar la versión compilada.

### 3. Configurar
Desde la pestaña **⚙️ Configuración** completa los siguientes campos:

| Campo | Descripción |
|-------|-------------|
| 👤 Usuario | Tu usuario de acceso |
| 🔒 Contraseña | Tu contraseña de acceso |
| 🌐 URL del sitio WEB | URL del sistema  |
| 📊 Archivo de tareas | Ruta del archivo Excel con los datos |
| 🌍 Navegador | Navegador a utilizar (Chrome) |
| 💻 ChromeDriver | Ruta del ejecutable ChromeDriver |
| 🔐 Flujo de LOGIN | Flujo para el inicio de sesión |
| 📋 Flujo de Tareas | Flujo para procesar las OTs |

Guarda la configuración para poder reutilizarla posteriormente.

---

## 🌐 ChromeDriver

El BOT utiliza Selenium y ChromeDriver para controlar el navegador.

Descarga ChromeDriver desde:  
[https://googlechromelabs.github.io/chrome-for-testing/](https://googlechromelabs.github.io/chrome-for-testing/)

Debes utilizar una versión compatible con tu navegador. Después de descargarlo, configura la ruta desde:  
**⚙️ Configuración → ChromeDriver**

---

## ⚙️ Configuración

Permite administrar diferentes perfiles de configuración.

**Funciones disponibles:**
- ✅ Guardar configuraciones
- ✅ Cargar configuraciones
- ✅ Eliminar configuraciones
- ✅ Configurar credenciales
- ✅ Configurar URL
- ✅ Seleccionar archivo Excel
- ✅ Configurar navegador
- ✅ Configurar ChromeDriver
- ✅ Seleccionar flujo de LOGIN
- ✅ Seleccionar flujo de tareas

---

## 🔄 Sistema de Flujos

El BOT permite crear automatizaciones mediante flujos compuestos por diferentes pasos.

**Tipos de acciones disponibles:**

| Acción | Descripción |
|--------|-------------|
| `CLICK` | Realiza un clic en un elemento |
| `ESCRIBIR` | Escribe texto en un campo |
| `SELECCIONAR` | Selecciona una opción de un desplegable |
| `ESPERAR` | Pausa la ejecución por un tiempo determinado |
| `JAVASCRIPT` | Ejecuta código JavaScript |
| `VALIDAR` | Valida la presencia o estado de un elemento |
| `SCROLL` | Desplaza la página |
| `OBTENER_TEXTO` | Extrae texto de un elemento |
| `SI_EXISTE` | Condicional basado en existencia de elemento |
| `REPETIR` | Repite un bloque de pasos |

Los pasos se ejecutan en el orden establecido.

---

## 🧪 Pruebas en tiempo real

La pestaña **Pruebas** permite validar acciones antes de utilizarlas en una automatización.

**Permite:**
- ▶️ Ejecutar pasos
- 🚀 Ejecutar flujo completo
- 🎯 Capturar XPath
- 🌐 Abrir navegador
- ❌ Cerrar navegador
- 📂 Cargar flujo
- 💾 Guardar paso
- 📦 Guardar todas las pruebas
- 🔄 Cargar variables
- 💾 Guardar cambios
- ⏭️ Probar siguiente paso

---

## 🎯 Captura automática de XPath

La versión **1.0.9** incorpora captura automática de XPath desde el navegador.

Al activar **🎯 Capturar XPath**, puedes hacer clic directamente sobre un elemento de la página. El BOT intenta generar automáticamente un selector utilizando atributos disponibles como:

- `ID`
- `NAME`
- `data-testid`
- `data-cy`
- `aria-label`
- `title`
- Texto
- Clases

Cuando no existe un identificador suficientemente útil, genera un XPath basado en la estructura del documento. El XPath capturado se coloca automáticamente en el campo **Selector**, facilitando la creación y validación de nuevos pasos.

---

## 📊 Integración con Excel

El BOT permite utilizar un archivo Excel como fuente de información para la automatización. Las columnas del Excel pueden utilizarse como variables dinámicas.

**Ejemplo de columnas:**
- OT
- Caja
- Responsable
- Estado

Dentro de un flujo puedes utilizar `{OT}`, `{CAJA}`, `{RESPONSABLE}` y el BOT reemplazará automáticamente estas variables con los valores correspondientes.

---

## 🔤 Variables dinámicas

Las variables pueden utilizarse en los selectores y valores de los pasos.

**Ejemplo:**
- **Selector:** `//*[@id="input_ot"]`
- **Valor:** `{OT}`

Si el Excel contiene `OT = 12345678`, el BOT utilizará `12345678` automáticamente.

También se generan variables a partir de las demás columnas del Excel.

---

## ✏️ Editor de Flujos

El sistema incluye un editor visual para administrar las automatizaciones.

**Permite:**
- ➕ Agregar paso
- ✏️ Editar paso
- ⬆️ Subir paso
- ⬇️ Bajar paso
- 🗑️ Eliminar paso
- 💾 Guardar flujo
- 🔄 Crear nuevo flujo
- 📂 Cargar flujo

---

## 📋 Gestión de Flujos

Los flujos pueden administrarse desde la pestaña **📋 Flujos**.

**Funciones disponibles:**
- 📋 Copiar
- 📑 Pegar
- 📂 Cargar
- 🗑️ Eliminar
- ✏️ Editor
- 🔄 Actualizar

Esto permite reutilizar y duplicar automatizaciones existentes.

---

## 🔐 Flujo de LOGIN

El BOT permite configurar un flujo específico para el inicio de sesión.

El flujo de LOGIN se ejecuta una sola vez al iniciar la automatización.

**Ejemplo:**
1. Abrir página
2. Escribir usuario
3. Escribir contraseña
4. Hacer clic en ingresar
5. Validar acceso

---

## 📋 Flujo de Tareas

El flujo de tareas se ejecuta para cada OT procesada desde el archivo Excel.

**Ejemplo:**
1. Buscar OT
2. Abrir OT
3. Seleccionar opción
4. Escribir información
5. Guardar
6. Validar resultado

---

## 📋 Logs

El sistema incorpora un registro de ejecución para facilitar el seguimiento y diagnóstico.

Los eventos se muestran mediante diferentes estados:

| Estado | Significado |
|--------|-------------|
| ℹ️ Información | Mensaje informativo |
| ✅ Éxito | Acción completada correctamente |
| ⚠️ Advertencia | Posible problema no crítico |
| ❌ Error | Error en la ejecución |
| 🛑 Detenido | Proceso detenido |

Los logs permiten conocer qué está realizando el BOT y detectar posibles problemas durante la ejecución.

---

## 🔄 Actualizaciones automáticas

El BOT incorpora un sistema de actualización basado en GitHub.

Durante el inicio, el sistema consulta la versión disponible y compara con la versión instalada.

**Actualmente:**
- 📦 Versión instalada: v1.1.4

Cuando existe una nueva versión disponible, el BOT informa:
- 🔄 Nueva versión disponible
- 📦 Versión actual
- 🆕 Nueva versión
- 📝 Notas de actualización

y permite iniciar el proceso de actualización.

---

## 📁 Archivos utilizados

El BOT utiliza diferentes archivos para almacenar configuraciones e información:

📁 Archivos del sistema
├── configuraciones.json # Perfiles de configuración
├── flujos.json # Flujos guardados
├── info_bot.json # Información del BOT
└── version.json # Versión actual


---

## 🛠️ Tecnologías

Proyecto desarrollado principalmente con:

| Tecnología | Propósito |
|------------|-----------|
| **Python** | Lenguaje principal |
| **Tkinter** | Interfaz gráfica |
| **Selenium** | Automatización web |
| **Pandas** | Manejo de datos |
| **OpenPyXL** | Lectura/escritura de Excel |
| **JSON** | Almacenamiento de configuraciones |
| **ChromeDriver** | Control del navegador Chrome |

---

## ✅ Recomendaciones antes de ejecutar

Antes de ejecutar una automatización en producción, verifica:

- [ ] ✓ Usuario
- [ ] ✓ Contraseña
- [ ] ✓ URL
- [ ] ✓ Archivo Excel
- [ ] ✓ Navegador
- [ ] ✓ ChromeDriver
- [ ] ✓ Flujo de LOGIN
- [ ] ✓ Flujo de tareas
- [ ] ✓ Selectores XPath
- [ ] ✓ Variables del Excel

Se recomienda realizar primero las pruebas desde **🧪 Pruebas** y posteriormente ejecutar la automatización completa.

---

## 📌 Flujo de trabajo recomendado
⚙️ Configuración
↓
📋 Crear/Cargar flujo
↓
🧪 Probar pasos
↓
🎯 Capturar XPath
↓
✅ Validar flujo
↓
📊 Cargar Excel
↓
▶️ Ejecutar automatización
↓
📋 Revisar logs

---

## 👨‍💻 Desarrollado por

**AtriaCode** ❤️

---

## 📄 Licencia

MIT License - Copyright (c) 2026 AtriaCode

Este software se proporciona "TAL CUAL", sin garantía de ningún tipo. 
El desarrollador no se hace responsable por el uso indebido, daños directos o indirectos, 
pérdida de datos, o cualquier otro perjuicio que pudiera derivarse de su uso.

**El usuario es el único responsable de:**
- Utilizar el software de acuerdo con las leyes aplicables
- Obtener los permisos necesarios en su organización
- Realizar pruebas antes de usar en producción
- Cumplir con las políticas y procedimientos de su organización

Proyecto destinado a automatizar procesos repetitivos en sistemas o aplicativos WEB.
se debe de leer el documento de  Licencia
---

## 📝 Sugerencias / Reportes

Para reportar problemas o sugerir mejoras, abre un issue en:  
[https://github.com/ediisson/AutomatizacionWeb/issues](https://github.com/ediisson/AutomatizacionWeb/issues)

---

<p align="center">
  <strong>BOT_AutomatismoWeb</strong><br>
  Versión 1.0.9
</p>