# Blacklist microservice — Entrega 1

Microservicio Flask para agregar emails a la lista negra global y consultar si
un email está bloqueado. `application.py` expone el objeto WSGI `application`
que usa AWS Elastic Beanstalk; `.ebextensions/python.config` configura
`WSGIPath: application:application`. La implementación no incluye CI/CD: el
equipo empaqueta y despliega cada versión manualmente.

## Contratos acordados para integrar el equipo

| Decisión | Valor |
| --- | --- |
| Runtime | Python 3.11, Flask 1.1.4 y dependencias fijadas en `requirements.txt` |
| Persistencia | PostgreSQL vía Flask SQLAlchemy; tabla `blacklist_entries` |
| Autenticación | `Authorization: Bearer <JWT>` en POST y GET, validado por Flask JWT Extended. Es un JWT compartido, preemitido y sin vencimiento para esta entrega; no existe endpoint para emitirlo. |
| Configuración del servidor | `DATABASE_URL` y `JWT_SECRET_KEY` obligatorias. El antiguo `API_TOKEN` propuesto en el plan del equipo **no se usa**. |
| Email | Se quitan espacios exteriores y se convierte a minúsculas tanto al registrar como al consultar. La unicidad es por email normalizado. |
| Duplicado | Se rechaza con HTTP 409; el registro anterior no se modifica. |
| Fecha/hora | Se almacena `created_at` en UTC. |
| IP | Se guarda `source_ip`. En local se usa la IP de la conexión. En Elastic Beanstalk la petición atraviesa **dos** proxies de confianza (el ALB y el nginx de cada instancia, que agrega la IP del ALB a `X-Forwarded-For`), por eso allí se configura `TRUSTED_PROXY_COUNT=2`. |
| Esquema | `python manage.py init-db` se ejecuta explícitamente una vez contra la base antes de probar POST/GET. Los procesos WSGI no crean tablas. |
| Health check | `GET /health` es público y devuelve la versión, sin consultar la base. |

### Variables de entorno

| Variable | Obligatoria | Ejemplo / función |
| --- | --- | --- |
| `DATABASE_URL` | Sí | `postgresql://usuario:clave@host:5432/blacklist` |
| `JWT_SECRET_KEY` | Sí | Secreto aleatorio compartido por todas las instancias; firma y valida el JWT. |
| `TRUSTED_PROXY_COUNT` | No | `0` en local (por defecto); `1` detrás de un solo proxy de confianza; `2` en Elastic Beanstalk (ALB + nginx). |
| `PORT` | No | Puerto del servidor local; `5000` por defecto. Beanstalk usa el objeto WSGI. |

El valor de `JWT_SECRET_KEY`, el JWT emitido y la contraseña de PostgreSQL son
secretos. No se guardan en Git, capturas, Postman público ni en el PDF. Si la
contraseña de la base contiene caracteres reservados en URL (`@`, `:`, `/`,
`#`, etc.), hay que codificarlos en el componente de contraseña de
`DATABASE_URL`. En Beanstalk, configurar las mismas variables para **ambos**
ambientes; el JWT funciona en ambos si comparten la misma clave.

## Ejecución local

Se necesita Python 3.8 o superior (el proyecto se probó con 3.11) y una base
PostgreSQL accesible. Ejemplo opcional con Docker:

```bash
docker run --name blacklist-pg -e POSTGRES_PASSWORD=local -e POSTGRES_DB=blacklist -p 5432:5432 -d postgres:16
```

En PowerShell, desde la raíz del repositorio:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = 'postgresql://postgres:local@localhost:5432/blacklist'
$env:JWT_SECRET_KEY = '<secreto-aleatorio-local>'
$env:TRUSTED_PROXY_COUNT = '0'
python manage.py init-db
python manage.py issue-token
python application.py
```

Sustituir `<secreto-aleatorio-local>` por un valor aleatorio; por ejemplo,
`python -c "import secrets; print(secrets.token_urlsafe(32))"`. Guardar el JWT
que imprime `issue-token` en una ubicación privada para Postman. La misma
`JWT_SECRET_KEY` debe mantenerse en los arranques posteriores o ese JWT dejará
de validar. El token no vence; para revocarlo se cambia la clave y se emite uno
nuevo.

En macOS o Linux, activar con `source .venv/bin/activate`, exportar las mismas
variables y usar `python3` si corresponde. `python application.py` escucha en
`http://127.0.0.1:5000`; `GET /health` responde
`{"status":"ok","version":"v1"}`.

## API para Postman

Usar variables privadas de entorno `base_url` y `token`. El workspace de equipo
debe documentar los siguientes casos contra local y la URL pública de AWS. La
documentación publicada puede incluir ejemplos de respuesta, pero no el token
real.

| Caso | Método y ruta | HTTP | Respuesta JSON |
| --- | --- | --- | --- |
| Agregar | `POST /blacklists` | 201 | `{"message":"Email agregado a la lista negra.","email":"persona@example.com"}` |
| Email duplicado | `POST /blacklists` | 409 | `{"message":"El email ya está en la lista negra."}` |
| Datos inválidos | `POST /blacklists` o `GET /blacklists/<email>` | 400 | `{"message":"Datos inválidos.","errors":{"campo":["detalle"]}}` |
| Token ausente, inválido o vencido | POST o GET | 401 | `{"message":"Token de autorización requerido o inválido."}` |
| Encontrado | `GET /blacklists/persona@example.com` | 200 | `{"email":"persona@example.com","blacklisted":true,"blocked_reason":"Motivo"}` |
| No encontrado | `GET /blacklists/otro@example.com` | 200 | `{"email":"otro@example.com","blacklisted":false,"blocked_reason":null}` |
| Salud | `GET /health` | 200 | `{"status":"ok","version":"v1"}` |

Ejemplo de solicitud POST:

```http
POST /blacklists HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{"email":"Persona@Example.com","app_uuid":"33154f55-2a0a-4dd4-876a-bc84d5f1467f","blocked_reason":"Motivo"}
```

`email` y `app_uuid` son obligatorios; `app_uuid` debe ser UUID válido.
`blocked_reason` es opcional, puede ser `null` y admite hasta 255 caracteres.
Los campos desconocidos se rechazan con 400. El motivo y el booleano aparecen
en la respuesta GET; IP y fecha/hora se conservan internamente, no se exponen
en la API. Los errores de validación detallan el campo afectado.

## Preparación y despliegue manual en Beanstalk

1. Juan crea la base PostgreSQL en RDS y permite tráfico 5432 **solo** desde
   el grupo de seguridad de las instancias de Beanstalk. Configura
   `DATABASE_URL`, `JWT_SECRET_KEY` y `TRUSTED_PROXY_COUNT=2` en las propiedades
   del ambiente. La clave y la URL completa no se incluyen en capturas.
2. Tras integrar un PR a `main`, crear el tag de versión sobre ese commit. Para
   obtener un ZIP con los archivos en la raíz: `git archive --format=zip -o
   blacklist-v1.zip v1`. Subirlo con **Upload and deploy**. No empaquetar la
   carpeta `.venv` ni un directorio padre.
3. La primera versión puede arrancar y responder `/health` antes de que exista
   la tabla. Desde **una sola sesión dentro de la VPC** con acceso a RDS (por
   ejemplo, una instancia de Beanstalk mediante el mecanismo de acceso del
   equipo), ejecutar `python manage.py init-db` desde la raíz de la aplicación
   con el Python que tenga instaladas las dependencias y las mismas variables
   del ambiente. El comando es idempotente; no es una migración de cambios
   futuros al esquema. No ejecutarlo simultáneamente en todas las instancias.
4. Verificar desde Postman público: `/health`, POST y GET con token y sin token.
   Confirmar en RDS que el registro conserva la IP del cliente vista por el
   balanceador y la fecha/hora UTC. Si la topología tiene un número distinto de
   proxies de confianza, ajustar `TRUSTED_PROXY_COUNT` y volver a verificar la
   IP; un valor incorrecto permite guardar una IP suministrada por el cliente.
5. Para las cuatro estrategias de despliegue, cambiar `VERSION` en
   `version.py` y preparar tags/ZIP distintos `v2` a `v5`, manteniendo la API
   funcional. `/health` permite comprobar qué versión sirve cada instancia.

El endpoint de salud comprueba disponibilidad del proceso, no conectividad de
RDS. Tras cambiar credenciales, red o esquema, ejecutar también POST/GET para
comprobar la integración real.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas automatizadas usan SQLite en memoria para verificar contrato HTTP,
autenticación, normalización, persistencia de IP/fecha y comportamiento del
proxy; no necesitan RDS ni secretos reales. Para ejecutar la prueba opcional
contra una **base PostgreSQL dedicada a pruebas**, preparar primero el esquema
con `python manage.py init-db`, asignar su URL a `INTEGRATION_DATABASE_URL` y
ejecutar:

```powershell
python -m unittest discover -s tests -p test_postgres_integration.py -v
```

La prueba crea un email único y lo borra al terminar. Si no se define
`INTEGRATION_DATABASE_URL`, se omite. Se verificó localmente con PostgreSQL 16;
Juan y Joseph aún deben repetir POST y GET contra RDS en AWS y comprobar la IP
real detrás del balanceador.
