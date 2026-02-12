
# 🧙 Thaddeus Morrowind – Discord RPG Bot

Bot de Discord desarrollado en **Python + discord.py 2.x**, diseñado para manejar un sistema RPG con personajes, árboles de habilidades, equipamiento y estadísticas dinámicas.

Incluye:

- Sistema completo de personajes (CRUD)
- Selección visual interactiva con botones
- Sistema de estadísticas base + adicionales + totales
- Soporte para comandos por prefijo (`=`) y Slash (`/`)
- Logging avanzado y manejo estructurado de errores
- Arquitectura modular por Cogs

----------

## ⚙️ Requisitos del Proyecto

### Python

Recomendado:

- Python 3.12 o 3.13

Ver versión actual:

`python --version`

----------

### Librerías necesarias

`pip install discord.py python-dotenv`

Ver versión de discord.py:

`pip show discord.py`

Debe ser 2.x

----------

## 🔐 Variables de Entorno (.env)

Archivo `.env` en la raíz:

`DISCORD_TOKEN=TU_TOKEN_AQUI LOG_LEVEL=INFO GUILD_ID=ID_DE_TU_SERVIDOR`

### Descripción

- **DISCORD_TOKEN** → Token del bot
- **LOG_LEVEL** → Nivel de logs (DEBUG / INFO / WARNING / ERROR)
- **GUILD_ID** → Para sincronización rápida de Slash Commands

----------

## 🚀 Cómo Ejecutar el Bot

En PowerShell:

`cd  "D:\Thaddeus Morrowind" .\.venv\Scripts\Activate.ps1
python -m src.bot.main`

----------

## 🟢 Verificación de Funcionamiento

### Consola debe mostrar

`Loaded  extension: src.bot.cogs.ping Loaded  extension: src.bot.cogs.personaje Synced  X slash commands BOT  ACTIVO`

----------

## 🧪 Comandos del Bot

### 🔹 Comandos Slash (/)

#### Sistema de Personajes

`/pj crear
/pj ver basica
/pj ver estadisticas`

#### Ping de prueba

`/ping`

----------

## 🔹 Comandos con Prefijo (=)

Prefijo configurado:

`=`

### Ping

`=ping`

### Personajes

`=pj ver  basica  =pj ver estadisticas`

> Nota: La creación de personaje se recomienda vía Slash por la interfaz visual.

----------

## 🎮 Sistema de Personaje

### Flujo de Creación

1. `/pj crear`
2. Modal: Nombre + Apodo
3. Selección visual con botones:
   - Rol
   - Profesión
   - Nación (Pathway)
4. Personaje creado con:

- Estadísticas base fijas
- 2 habilidades iniciales
- Equipamiento vacío

----------

## 📊 Sistema de Estadísticas

El cálculo se divide en:

- **Base** → Estadísticas propias + atributos planos
- **Adicionales** → Porcentajes de artefactos
- **Total** → Base + Adicionales

Ejemplo en visualización:

`Base: 100  Extra: 10  Total: 110`

----------

## 🗂 Sistema de Datos

Cada usuario tiene su propio archivo:

`data/users/<discord_id>.json`

Estructura:

`{ "ID_USUARIO": { "personajes": { "NombrePersonaje": {
        ...
      }
    }
  }
}`

----------

## 🧠 Árboles de Habilidad

Se cargan desde:

- `data/rol.json`
- `data/profesiones.json`
- `data/pathway.json`

Cada uno contiene:

- nombre
- descripcion
- imagen
- datos adicionales por nivel

La selección se realiza con carrusel interactivo.

----------

## 🛑 Apagar el Bot

Forma estándar:

`Ctrl  +  C`

El sistema maneja apagado limpio con logs:

`Señal de apagado recibida
Proceso finalizado`

----------

## 🧾 Sistema de Logging

Controlado por:

`LOG_LEVEL`

Opciones:

- DEBUG → Máximo detalle
- INFO → Información normal (recomendado)
- WARNING → Solo advertencias
- ERROR → Solo errores

----------

## 🧯 Manejo de Errores Implementado

El bot detecta y reporta:

- Extensión no encontrada
- Fallos de carga de cogs
- Errores de sincronización de slash
- Comandos no encontrados
- Permisos insuficientes
- Errores HTTP de Discord
- Desconexiones del Gateway

Cada error:

- Se imprime claro en consola
- Incluye explicación probable
- Incluye traceback en DEBUG

----------

## 📌 Permisos Importantes en Discord Developer Portal

En el Bot → Privileged Gateway Intents:

✅ MESSAGE CONTENT INTENT (necesario para comandos con `??`)

Y al invitar el bot debe incluir:

`scope=bot applications.commands`

----------

## 🔍 Puntos a Revisar Más Adelante

- Sistema real de inventario enlazado a equipamiento
- Restricción de equipamiento por clase
- Sistema de subida de nivel automática
- Persistencia mejorada (migrar a base de datos SQL)
- Sistema de combate
- Control de rate limit
- Deploy en servidor dedicado o VPS
- Sistema de backups automáticos de data/users

----------

## 📈 Estado Actual del Proyecto

✔ Arquitectura modular estable  
✔ Slash Commands sincronizados  
✔ Prefijo activo  
✔ Sistema visual de selección  
✔ Cálculo dinámico de estadísticas  
✔ Manejo avanzado de errores  
✔ Logging estructurado

----------

## 🧩 Recomendaciones Técnicas

- Mantener discord.py actualizado
- Usar Python 3.12 o 3.13
- Hacer backup periódico de `data/users`
- No subir `.env` al repositorio
- Usar control de versiones (Git)

----------

## 📚 Futuro Escalamiento

Posible evolución del proyecto:

- Sistema multi-personaje
- Economía interna
- Sistema de eventos automáticos
- Dashboard web administrativo
- Integración con base de datos externa
