
## Reglas de codigo

- En Python, usa `snake_case` para modulos, funciones, metodos y variables, y `PascalCase` para clases.
- En SQL, usa `snake_case` para tablas y columnas.
- Nombra los tests de Python como `test_*.py` y utiliza `unittest`, siguiendo el ejemplo existente en `inventoryManager/`.
- No anadas dependencias, gestores de paquetes ni frameworks sin justificar la necesidad y documentar el cambio. El repositorio no tiene un manifiesto de dependencias en la raiz; el ejemplo ejecutable existente usa la biblioteca estandar de Python y SQLite.

## Reglas de estructura

- Coloca las APIs y workers de compania bajo `services/`, siguiendo su README.
- Coloca las interfaces de usuario bajo `uis/`; el backoffice interno pertenece a `uis/backoffice/`.
- Coloca la documentacion transversal del repositorio bajo `docs/`.
- Mantén cada aplicacion o servicio en su subcarpeta y documenta su objetivo, tecnologia, pruebas y forma de ejecucion en un README local.
- No reorganices ni cambies codigo ajeno a la tarea para acomodarlo a estas reglas.

## Reglas de dominio para incidencias

- Obtén tipos, severidades, canales y areas responsables del briefing de HealthCore; no inventes valores de catalogo.
- Registra cada cambio de estado y de area responsable con actor y marca temporal consultables.
- No incluyas datos identificables de pacientes en incidencias de operaciones; usa referencias opacas cuando sean necesarias.

## Activacion

Estas reglas se aplican al crear o modificar codigo, pruebas, configuracion y documentacion del proyecto.
---------
