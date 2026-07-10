# W17 — Panel "Información Extraída" (dato · confianza · fuente)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1b hi-fi
> **LLM/det:** — (front) · **Depende de:** (M2 para lo real) · **Datos:** R + **M** · **Invariantes:** P3 · P5 · P7

## 1. Intent

El copiloto diciendo *"encontré esto"*: una tabla con cada campo → **valor · confianza% · fuente**
(Correo / PDF pág. 3 / Denuncia / SOAT / Fotos). El operador sabe **cuánto confiar** y **de dónde salió**;
click en un campo → salta a la evidencia (W12). Es el panel derecho del mockup.

## 2. Criterios de completitud (verificables)

1. **Provider `campos_extraidos(caso) -> list[Campo]`** con `Campo: {label, valor, confianza, fuente,
   origen}`. **Une los campos REALES** (de `extraccion.campos`, con su `origen`+`confianza` VERDADEROS) **con
   los campos ricos MOCK** (asegurado, lugar, vehículo, placa, teléfono…) rotulados `origen="demo"` hasta M2.
2. **Distinción real/demo (P7):** los reales NO se marcan demo; los mock llevan badge. La confianza y la
   fuente de los reales son las verdaderas del contrato (no inventadas).
3. **Render** tabla ícono · label · valor · **confianza% (verde)** · fuente; contador "Ver todos los campos
   (N)".
4. **Click → evidencia:** cada campo enlaza a su fuente vía el provider de anclas (W12; mock hasta M1/M2).
5. **"Editar todo":** enlaza al flujo de corrección existente (`corregir`, re-dictamen determinístico).

## 3. Invariantes / restricciones

- **P3 (trazabilidad):** cada campo cita su `origen` (fuente); los reales de verdad, los mock rotulados.
- **P5:** valores con PII redactados (`|redact`); la fuente no filtra PII.
- **🔴 Blindaje agéntico (P7):** los campos que un agente real produce se muestran **reales**; el mock es solo
  el dato que aún no producimos, y M2 lo reemplaza **sin tocar la vista** (misma interfaz `Campo`).

## 4. Fuera de alcance

- La extracción rica real (M2) y el visor de evidencia (W12). Aquí el panel + el provider (interfaz estable).

## 5. Verificación (tests fail-closed)

- Los campos reales del `Caso` aparecen con su `origen`/`confianza` VERDADEROS (no demo).
- Los campos ricos mock llevan `origen="demo"`/badge; no se confunden con reales.
- Ningún valor con PII aparece crudo (P5).
- La interfaz `Campo` del provider es la que consumirá M2 (contrato estable).

## 6. Notas CÓMO

Provider en `vista_caso.py` (o `dashboard/providers/`) que fusiona `extraccion.campos` (real) + set rico mock.
Panel en la columna derecha del workbench. Reusa `CampoExtraido.origen`/`confianza`.

## 7. Precisiones tras code-review

- **🟠 Contrato `CampoUI` estable (interfaz que M2 llena):**
  `CampoUI: {label: str, valor: str|None, confianza: float|None, fuente: str, origen: "real"|"demo",
  clase: "extraido"|"validado"|"relacionado"}`. `fuente` = string legible ("Correo", "PDF pág. 3") derivado de
  `EvidenciaOrigen.tipo/referencia` en los reales.
- **🟠 Frontera real/demo SIN ambigüedad (P3/P7):** `origen="real"` **si y solo si** el campo viene de
  `extraccion.campos` (lo produjo un agente real) — **su confianza se muestra tal cual, aunque sea baja** (NO
  se degrada un real a "demo"; un real de baja confianza se ve como real de baja confianza). `origen="demo"`
  para el set rico que aún no producimos (asegurado, lugar, vehículo, placa, teléfono…). **M2** los vuelve
  reales con la misma interfaz.
- **Fusión:** reales primero, luego demo; **sin dedup** (si M2 ya emite `asegurado`, ese real desplaza al demo
  del mismo `label`). La confianza consolidada la aporta el overlay de **M3** si existe (ver M3 §7).

### Tras el CÓMO
- **Reviewer: aprobado sin críticos** (blindaje agéntico sólido, P1-P7, Clean Code). Ajustes: `origen:
  Literal["real","demo"]`; guard anti-duplicado entre reales; indicador visual de origen (real=verde·demo=gris);
  test de redacción extendido (email/teléfono). `CampoUI` frozen = interfaz estable que M2/M3 llenarán (DIP/Liskov).
