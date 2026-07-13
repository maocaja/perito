# W23 — Última pasada de precisión (content + microcopy + flujo)

> NO cambia arquitectura (Cola → Caso → Excepción → Evidencia → Recomendación → Acción, de W22). Es la capa
> final para que un operador nuevo identifique el problema y complete la acción correcta en <1 min, y luego
> ir a pruebas con usuarios reales. Cadencia AI-DLC: por unidad QUÉ+CÓMO → Bolt → code-reviewer → ajustar →
> code-reviewer → bitácora → siguiente. Feedback fuente: revisión del usuario tras W22.

## §1 · Regla de oro (heredada de W22)
**MOVER lo técnico, no borrarlo · label ≠ valor.** El enum/regla/"P1" salen de la superficie del operador y
viven en el nivel técnico ("Ver actividad técnica" / "Ver regla aplicada") — encode-not-hide + P2 intactos;
el valor canónico (enum) sigue en el dato/motor. Todo microcopy nuevo pasa por el fail-closed P1.

## §2 · Unidades (QUÉ + CÓMO)

### M1 · Menos repetición del bloqueo + Estado operativo colapsado  [Prioridad 0]
- **QUÉ:** el problema se dice UNA vez; el panel derecho enfoca la ACCIÓN (no re-enuncia el problema);
  Estado operativo muestra solo el conteo, con los pendientes a un click.
- **CÓMO:**
  1. Panel `wb-reco` (REQUIERE_REVISION): en vez de repetir `rec.titulo` ("Falta un dato: X"), mostrar el
     título de la ACCIÓN (nuevo `rec.accion.titulo`, p.ej. "Solicitar el valor al asegurado"). El "qué falta"
     ya está en el bloque central + el banner.
  2. Estado operativo (`health_check` render): resumen "N de M verificaciones · K pendientes"; la lista
     "Pendiente" pasa a estar **dentro** del `<details>` "Ver todas" (o un "Ver pendientes" propio) — colapsada
     por defecto. Encode-not-hide: todo sigue a un click.

### M2 · Resumen sin jerga interna  [Prioridad 0]
- **QUÉ:** el resumen operativo no dice "(regla PRE_MOTOR)" ni el enum; explica en humano por qué.
- **CÓMO:** `resumen_narrativo` — cuando no hay dictamen terminal (escala), decir "La cobertura no puede
  evaluarse todavía porque falta {campo humano}." (sin `regla_aplicada`). Para cobertura terminal, citar el
  resultado humano; la **regla** (P2) vive en "Cobertura · por qué → Ver regla aplicada" (ya existe, L2). El
  tipo en prosa ya es humano (L2). Migrar el test P2 del resumen → verificar la cita en el bloque de cobertura,
  no en la prosa. 🔒P2: la cita de regla NO desaparece — se mueve al nivel técnico.

### M3 · Enums fuera del formulario  [Prioridad 0]
- **QUÉ:** el campo editable "Tipo de siniestro" muestra "Colisión vehicular", no `AUTO_COLISION`.
- **CÓMO:** en `campos_corregibles`, `tipo_siniestro` pasa a ser un `<select>` (opciones: etiqueta humana →
  valor enum). El operador elige "Colisión vehicular"; el form envía `AUTO_COLISION` (label ≠ valor; el motor
  lo compara exacto, P2). Reusar `_TIPO_LABEL`.

### M4 · Microcopy de acciones + firma + verificación  [Prioridad 0/1]
- **QUÉ:** términos autoexplicativos; "(P1)" fuera de la superficie.
- **CÓMO (solo copy/tooltips):**
  - "Firma (P1)" → **"Firma del analista"** + ayuda "Obligatoria antes de radicar o rechazar." ("P1" solo en
    auditoría/cumplimiento).
  - "No disponible" (Verificación) → **"Verificación no realizada"** (o "Pendiente por información faltante").
  - Tooltips: "Radicar caso" → "Crear formalmente el expediente y enviarlo al siguiente equipo." · "Enviar a
    revisión especializada" → "Enviar el caso a un especialista para evaluación manual."

### M5 · "Preparar solicitud" + flujo conectado  [Prioridad 1]
- **QUÉ:** la primaria de un caso con falta deja claro que PREPARA (no envía a ciegas) y conecta con el dato.
- **CÓMO:** `rec.accion.label` "Solicitar al asegurado" → **"Preparar solicitud"** (endpoint carta/solicitud
  que abre un borrador en el drawer, prellenado, con el mensaje visible; el operador revisa y envía; el caso
  queda "Pendiente de respuesta"). 🔒P1: draft ≠ send (ya es el patrón de la carta). Resaltar el campo
  faltante al abrir (data-attr).

### M6 · Refinamiento visual del bloque de excepción  [Prioridad 1/2]
- **QUÉ:** el bloque ámbar central pesa menos; los campos ya verificados se ven "primero la excepción".
- **CÓMO:** reducir alto/padding del `wb-revisar`; **colapsar los campos verificados** bajo "Ver información
  extraída" (`<details>`), dejando visible la excepción + el form. encode-not-hide: los datos siguen a un click.

## §3 · Reconciliación de invariantes
- **P2** — la cita de regla+cláusula NO se borra; se mueve del resumen/superficie al bloque técnico "Ver regla
  aplicada" (M2). El enum del tipo sigue siendo el valor real del `<select>` (M3).
- **P1** — quitar "(P1)" es solo etiqueta; el gate del servidor (firma obligatoria) intacto. "Preparar
  solicitud" es draft (no terminal). Todo microcopy pasa el fail-closed de PALABRAS_PROHIBIDAS.
- **encode-not-hide** — colapsar (Estado operativo, campos verificados) es `<details>`, no borrado.

## §4 · Orden
Prioridad 0: **M1 → M2 → M3 → M4**. Luego M5 → M6. Cada unidad: Bolt → code-reviewer → ajustar → code-reviewer.

## §5 · Fuera de alcance (del usuario)
Prueba con operadores reales (identificar el problema + completar la acción en <1 min) + auditoría WCAG 2.2.

## §6 · Bitácora

### M1 — Menos repetición + Estado operativo colapsado
- **Bolt:** `_accion_primaria` añade `titulo` (imperativo de acción); panel `wb-reco` usa `rec.accion.titulo`
  (no re-enuncia el problema); Estado operativo → header "N de M · K pendiente(s)" + detalle (pendientes
  primero, luego el resto) bajo `<details>` colapsado. Tests `test_w23_precision.py` (+4); 1 W22 migrado.
- **Code-review:** APROBADA — P1–P6 intactos, fail-closed blindado (accion=None si degrada), encode-not-hide
  (colapsa, no borra; conteo fiel), dedup correcto. Hallazgo MENOR (docstring sin `titulo`) → **corregido**.
  Doc-only, sin cambio de conducta → sin 2ª pasada. Suite 605 verde.

### M2 — Resumen sin jerga interna
- **Bolt:** `resumen_narrativo` — cobertura humana: terminal → "Cobertura: {label}." (sin "(regla X)"); escala
  por falta → "La cobertura no puede evaluarse todavía porque falta {campo}."; sin faltante → "…requiere
  revisión.". La cita de regla (P2) se queda en `resumen_copiloto` + "Ver regla aplicada". Tests +4; 2 migrados.
- **Code-review:** APROBADA — 🔒P2 MOVIDO no borrado (verificado: `resumen_copiloto` y "Ver regla aplicada"
  siguen citando la regla); P1/P5/P6/P7 OK; cubre los 4 casos. Hallazgo MENOR (L2): `motivo` del carril con
  nombres técnicos → **corregido** (humanizado con `_LABEL_CAMPO`, 2 sitios). Suite 609 verde. Sin 2ª pasada.

### M3 — Enums fuera del formulario (dropdown de tipo)
- **Bolt:** `campos_corregibles` — `tipo_siniestro` como `select` (opciones {valor: enum, label: humano}); los
  2 formularios renderizan `<option value=enum>humano`. `label ≠ valor`: el motor recibe el enum (P2). Tests +3.
- **Code-review:** CORRECTO — 🔒P2 label≠valor verificado (el motor recibe el enum, no la etiqueta); P1/P5/P7
  OK; las 6 opciones del enum presentes. Hallazgo MEDIUM/LOW (DRY): select duplicado en los 2 forms →
  **corregido** (macro `corregir_campo` en `_macros.html`, importado en workbench_caso; fuente única).
  Suite 612 verde; ambos forms renderizan igual. Verificado por los tests M3 → sin 2ª pasada (extracción
  mecánica, conducta idéntica).

### M4 — Microcopy (firma · verificación · tooltips)
- **Bolt:** "Firma (P1)" → "Firma del analista" (2 forms) + placeholder del panel; ayuda "Obligatoria antes de
  radicar o rechazar."; tira Verificación "No disponible" → "No realizada"; tooltips Radicar ("Crear
  formalmente el expediente y enviarlo al siguiente equipo") y "revisión especializada" ("Enviar el caso a un
  especialista para evaluación manual"). Solo copy/tooltips, cero lógica. Tests +3. Suite 615 verde.
- **Code-review:** CLEAN (sin hallazgos) — P1 el gate de firma sigue `required` + servidor (quitar "(P1)" es
  solo superficie); P7 "No realizada" honesto (C3 no corrió, no inventa "Verificado"); P5/P6 intactos; sin
  palabras prohibidas. Sin 2ª pasada (cambio puro de copy, nada que ajustar).

### M5 — "Preparar solicitud" + flujo conectado (draft ≠ send)
- **Bolt:** `_accion_primaria` — la primaria de REQUIERE_REVISION+faltantes pasa de POST directo `/solicitar_docs`
  a **"Preparar solicitud"** (`endpoint=carta`, `drawer=True`): abre el borrador editable en el drawer (la carta
  de datos ya nombra el faltante); el humano revisa y ENVÍA con firma (`/carta/enviar`). Clave `drawer` en las 3
  ramas. Plantilla: rama `drawer` → botón `hx-post→#wb-drawer`; dedup de la carta secundaria. Tests +3; 2 W22 migrados.
- **Code-review:** PASA P1–P7 — 🔒P1 draft≠send verificado (preparar = borrador sin firma/sin estado/sin
  persistencia; enviar exige `usuario`, 400 si falta; ningún terminal sin firma); P2 plantilla determinística
  nombra solo faltantes; P5 sin PII; arquitectura limpia. Hallazgos MENORES: guard muerto (`endpoint=='solicitar_docs'`
  ya inalcanzable) → **eliminado**; docstring de `solicitar_docs` (ahora secundaria) → **actualizado**; +1 test de
  fallback ('Solicitar documentos' sigue como secundaria). Suite 619 verde. Ajustes mecánicos (conducta idéntica,
  cubiertos por test) → sin 2ª pasada.

### M6 — Refinamiento del bloque de excepción ("primero la excepción")
- **Bolt:** `wb-datos` — en caso BLOQUEADO los datos ya extraídos se colapsan bajo `<details>` "Ver información
  extraída" (sin duplicar el loop: solo se abre/cierra el wrapper condicional); en caso LISTO se ven expandidos.
  `.wb-revisar` aligerado (padding/gap/ícono). Disclosure con `list-style:none` cross-browser (patrón del resto).
  Tests +2. Suite 621 verde.
- **Code-review:** PASS P1–P7 — 🔴 encode-not-hide verificado (los campos SIGUEN en el DOM, solo colapsados;
  confianza codificada igual); tags del `<details>` balanceados en ambos ramos (HTML válido); cambio puramente
  presentacional (motor/decisión intactos); tests fail-closed. Hallazgo MEDIUM (UX, no bug): riesgo bajo de
  corregir sin expandir → trade-off deliberado ("primero la excepción"), documentado + dato a un click →
  ACEPTADO sin cambio. Sin 2ª pasada.

## §7 · Cierre
W23 completa (M1–M6). Suite **621 passed**, 3 skipped. Todos los invariantes P1–P7 + encode-not-hide verdes por
code-review unidad a unidad. Regla de oro sostenida: se MOVIÓ lo técnico (regla, enum, "P1", % de confianza,
datos verificados) a un nivel a un click — nunca se borró. Sin tocar `rules/` ni `orchestrator/`. Pendiente:
commit (queda staged; lo decide el usuario) + prueba con operadores reales (fuera de alcance, §5).
