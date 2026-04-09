# SETUP — Agente Deportivo

Guía para levantar todos los servicios del proyecto en local.

---

## Requisitos previos

- Python 3.10+ con el entorno virtual `.venv` creado
- ngrok instalado y autenticado (`ngrok config add-authtoken <token>`)
- Archivo `.env` con las claves necesarias (ver sección Variables de entorno)

---

## Variables de entorno (`.env`)

```
FOOTBALL_DATA_API_KEY=<tu_clave>
THESPORTSDB_API_KEY=<tu_clave>
TELEGRAM_BOT_TOKEN=<token_del_bot>

# Contraseñas beta para el dashboard (opcional, si no se define usa las de app.py)
BETA_PASSWORDS=claveJuan:Juan García,claveMaría:María López
```

---

## Activar el entorno virtual

Antes de cualquier comando, activa el venv:

```powershell
.venv\Scripts\Activate.ps1
```

---

## Servicios — cada uno en su propia terminal

### Terminal 1 — FastAPI (API REST)

```powershell
uvicorn src.api:app --reload --port 8000
```

- Docs interactivos: http://localhost:8000/docs
- Health check: http://localhost:8000/

---

### Terminal 2 — Streamlit (Dashboard web)

```powershell
streamlit run app.py --server.port 8501
```

- Dashboard local: http://localhost:8501
- Pide contraseña beta al abrir (configurada en `.env` o en `app.py`)

---

### Terminal 3 — Bot Telegram

```powershell
python bot.py
```

- El bot queda escuchando en modo polling.
- Comandos disponibles en Telegram: `/start`, `/liga`, `/equipo`, `/jornada`, `/compare`, `/equipos`, `/competiciones`

---

### Terminal 4 — ngrok (túnel público para Streamlit)

```powershell
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
ngrok http 8501
```

- La URL pública aparece en la línea `Forwarding`:
  ```
  Forwarding   https://xxxx.ngrok-free.app -> http://localhost:8501
  ```
- Comparte esa URL con los usuarios beta. Ellos verán la pantalla de login.

> **Nota:** El plan gratuito de ngrok permite 1 túnel simultáneo y la URL cambia cada vez que reinicias ngrok.

---

## Orden recomendado de arranque

1. Activar venv
2. Levantar **API** (terminal 1)
3. Levantar **Streamlit** (terminal 2)
4. Levantar **Bot Telegram** (terminal 3)
5. Levantar **ngrok** (terminal 4)

---

## Gestión de usuarios beta

Edita el diccionario en [app.py](app.py) (líneas ~41-48):

```python
_DEFAULT_BETA_USERS: dict[str, str] = {
    "clave_juan": "Juan García",
    "clave_maria": "María López",
}
```

O sin tocar código, añade en `.env`:

```
BETA_PASSWORDS=clave_juan:Juan García,clave_maria:María López
```

Formato: `contraseña:Nombre`, separados por comas. Para revocar acceso, elimina la entrada.

---

## Parar los servicios

- **Streamlit / API / Bot**: `Ctrl+C` en cada terminal
- **ngrok**: `Ctrl+C` en su terminal

---

## Resumen de puertos

| Servicio    | Puerto | URL local                  |
|-------------|--------|----------------------------|
| FastAPI     | 8000   | http://localhost:8000      |
| Streamlit   | 8501   | http://localhost:8501      |
| ngrok       | —      | https://xxxx.ngrok-free.app |
| Bot Telegram| —      | Solo polling, sin puerto   |
