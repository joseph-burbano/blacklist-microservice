# Blacklist microservice

Estructura inicial del microservicio de listas negras. La aplicación expone un
objeto WSGI llamado `application` para AWS Elastic Beanstalk. Los recursos REST,
la persistencia y la autenticación se incorporarán en entregas posteriores.

## Requisitos

- Python 3.8 o superior

## Ejecución local

Crear y activar un entorno virtual, instalar las dependencias fijadas y arrancar
el servidor de desarrollo:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python application.py
```

En macOS o Linux, activar el entorno con `source .venv/bin/activate` y sustituir
`py` por `python3`.

La aplicación escucha en `http://127.0.0.1:5000` por defecto. El endpoint
`GET /health` responde `{"status":"ok","version":"v1"}`.

## Variables de entorno

| Variable | Uso | Valor por defecto |
| --- | --- | --- |
| `PORT` | Puerto del servidor de desarrollo local | `5000` |

No se necesitan credenciales ni conexión a una base de datos para iniciar esta
estructura. En Elastic Beanstalk, `.ebextensions/python.config` configura el
punto de entrada `application:application`.
