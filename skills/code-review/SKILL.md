# Skill: revision de codigo antes del commit

## Objetivo unico

Revisar los cambios pendientes de un commit contra las reglas del repositorio (`.agents/rules.md` y `AGENTS.md`) y decidir si estan listos para commitear, produciendo una lista de hallazgos verificables.

Esta skill **solo** evalua cambios sin commitear; no reescribe codigo, no ejecuta el commit y no revisa codigo ya versionado salvo que el usuario lo pida expresamente.

## Inputs documentados

| Input | Origen | Obligatorio | Descripcion |
| --- | --- | --- | --- |
| Cambios pendientes | Salida de `git status` y `git diff` (incluidos ficheros staged) | Si | Dif a revisar; si esta vacio, la skill termina con `SIN_CAMBIOS`. |
| Reglas del repositorio | `.agents/rules.md` | Si | Convenciones de codigo, estructura y dominio con su alcance. |
| Flujo de entrega | `AGENTS.md` | Si | Pasos obligatorios previos al commit. |
| Contexto del proyecto | `memory-bank/techcontext.md` | No | Stack y restricciones tecnicas para juzgar decisiones afectadas. |
| Archivos nuevos no tracked | `git status --porcelain` con `??` | Si | Deben revisarse tambien; `git diff` no los incluye. |

Salida esperada: lista de hallazgos (`BLOQUEANTE` o `AVISO`) con archivo, regla infringida y accion sugerida, o el veredicto `LISTO_PARA_COMMIT`.

## Procedimiento

1. Ejecutar `git fetch` y `git status --porcelain` y recoger los cambios pendientes (staged, unstaged y untracked).
2. Ejecutar `git diff` (staged y sin stage) y leer los ficheros afectados completos si son nuevos.
3. Contrastar cada cambio con las reglas aplicables por alcance (codigo, estructura, dominio) y con el flujo de `AGENTS.md`.
4. Emitir el veredicto `LISTO_PARA_COMMIT` o los hallazgos ordenados: primero `BLOQUEANTE`, luego `AVISO`.

## Criterios de aceptacion

Todos los criterios son verificables de forma independiente sobre la salida de la skill:

- **CA-01**: si `git status` no muestra cambios, la salida es exactamente `SIN_CAMBIOS` y no hay mas acciones.
- **CA-02**: cada hallazgo incluye ruta de archivo, regla infringida (nombre de la seccion de `.agents/rules.md`) y accion sugerida; ningun hallazgo queda sin estos tres campos.
- **CA-03**: los ficheros nuevos no tracked aparecen revisados aunque `git diff` este vacio.
- **CA-04**: no se ejecuta `git commit` (ni ninguna escritura en el repositorio) durante la ejecucion; el veredicto es de solo lectura.
- **CA-05**: el veredicto final es `LISTO_PARA_COMMIT` solo si la lista de hallazgos `BLOQUEANTE` esta vacia.
- **CA-06**: si un cambio incumple una regla con alcance que no le aplica, no se marca como hallazgo (el alcance declarado en `.agents/rules.md` se respeta).

## Ejemplo de uso

```
Entrada: cambios pendientes en `services/inventory_api/` (fichero nuevo `api.py`)
Salida: BLOQUEANTE | services/inventory_api/api.py | Reglas de estructura (siempre activa): documentar el servicio en un README local con objetivo, tecnologia, pruebas y ejecucion | anadir README.md
Veredicto: BLOQUEANTE si existe algun hallazgo; en otro caso LISTO_PARA_COMMIT.
```