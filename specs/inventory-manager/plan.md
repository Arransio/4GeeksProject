# Plan de implementacion: inventario de HealthCore

## Alcance y ubicacion

- Mantener el dominio bajo `inventoryManager/`, la ruta existente asignada a este proyecto.
- Mantener las decisiones de comportamiento en `specs/inventory-manager/`.
- Crear la interfaz operativa en `uis/backoffice/inventory/`, conforme al README de `uis/`.
- La API nueva usara FastAPI, siguiendo la recomendacion de API centralizada del README raiz y el runtime FastAPI ya fijado en `services/incident_manager/`. El ejemplo WSGI anterior de inventario se reemplazara; no se trasladara su API parcial como convencion general.
- SQLite y `sqlite3` de la biblioteca estandar seran la persistencia. No se incorporara ORM ni libreria de frontend.

## Modelo de datos

- `products`: identificador, nombre, unidad y punto de reorden no negativo. No contiene una columna de existencia.
- `lots`: identificador de lote y referencia al articulo propietario; los lotes no se comparten entre articulos.
- `movements`: identificador, articulo, lote, tipo, cantidad, motivo y `occurred_at` UTC. Las filas son append-only.
- La vista `product_stock` calcula la existencia agregada desde `movements`. Un disparador de SQLite rechaza movimientos que la harian negativa; claves foraneas rechazan articulos/lotes inexistentes o inconsistentes.
- El primer movimiento de entrada crea el lote y la entrada dentro de una transaccion. Salidas y ajustes requieren lote existente del mismo articulo.

## Reglas de movimientos

- `entrada`: cantidad positiva; aumenta existencia.
- `salida`: cantidad positiva; disminuye existencia.
- `ajuste`: cantidad firmada no nula; el signo indica aumento o disminucion.
- Todos los movimientos requieren motivo no vacio. La marca temporal UTC se genera en el servidor, no en el cliente.
- Una falla de validacion revierte la transaccion completa: no queda lote ni movimiento parcial.

## API y backoffice

- FastAPI expone alta/listado/edicion de articulos, alta de movimientos y consulta de existencia, lotes e inventario bajo el punto de reorden.
- El backoffice consume la API para registrar articulos y movimientos y mostrar una alerta visible cuando `stock < reorder_point`; la igualdad no genera alerta.
- Los nombres y unidades son configurables. El briefing de HealthCore no define categorias ni un catalogo fijo; las pruebas usaran fixtures identificados como datos de prueba, no valores oficiales.
- No se almacenaran datos de pacientes ni se añadira autenticacion, fuera del alcance indicado.

## Verificacion

- `unittest` cubrira cada ID de `spec.md`, incluyendo articulo/lote inexistente, lote de otro articulo, razon/cantidad invalidas, intento de stock negativo, inmutabilidad, stock derivado y ambos lados del umbral de reorden.
- Las pruebas de SQLite verificaran vistas, claves foraneas, triggers y rollback; las pruebas HTTP usaran `TestClient` de FastAPI.
- Los commits de implementacion seran pequenos y cada uno referenciara los `TASK-*` y los IDs EARS implementados.
- El entorno local dispone de Python 3.7.7; las anotaciones y dependencias se mantendran compatibles con esa version para poder ejecutar las pruebas disponibles.
