# W9 — Acciones ampliadas 🔒 P1

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** ⚙️ det · **Depende de:** — · **Datos:** R + **M** (envío de docs) · **🔒 P1 → OK + code-reviewer antes del CÓMO.**

## 1. Intent

No "botones": **acciones** claras en la columna derecha. *Enviar solicitud de documentos faltantes · Radicar ·
Escalar · Enviar a fraude · Guardar borrador.* El operador decide rápido; la IA preparó el terreno.

## 2. Criterios de completitud (verificables)

1. **Radicar** = la aprobación humana existente (`aprobar`, exige `aprobado_por`) — **estado terminal solo con
   humano** (P1 intacto). Copy "Radicar" en vez de "Aprobar".
2. **Escalar** — transición a `REQUIERE_REVISION` con motivo (acción HITL explícita; hoy el sistema escala,
   ahora también el humano puede).
3. **Enviar a fraude** — **rutea** el caso al carril SIU (marca/etiqueta), **NO decide** fraude ni cambia
   estado terminal (P6). Reusa la señal de `alerta_fraude`.
4. **Enviar solicitud de documentos faltantes** — genera el borrador de solicitud desde `faltantes`/
   `checklist_documentos`; **provider de envío mock** (rotulado): hoy prepara el texto, no envía correo real.
5. **Guardar borrador** — persiste el estado de trabajo del operador (correcciones sin radicar), sin alcanzar
   terminal.

## 3. Invariantes / restricciones

- **🔒 P1:** ninguna acción alcanza `APROBADO`/`RECHAZADO` sin **humano registrado** (`aprobado_por`). Radicar
  usa el flujo `hitl` existente. Escalar/enviar-a-fraude/solicitar-docs/borrador **no** son estados terminales.
- **P6:** "Enviar a fraude" **sugiere/rutea**, no dictamina.
- **P7:** el envío de la solicitud de docs es **mock rotulado** (prepara, no envía) hasta tener el conector.

## 4. Fuera de alcance

- Envío real de correos (conector) — mejora futura; aquí el borrador + la acción.

## 5. Verificación (tests fail-closed)

- Radicar sin `aprobado_por` → rechazado por el contrato/HITL (P1, aserción).
- Escalar / a-fraude / solicitar-docs / borrador → el caso **no** queda en estado terminal.
- "Enviar a fraude" no cambia el dictamen ni deshabilita nada por sí solo (P6).
- La solicitud de docs lista exactamente los faltantes reales del caso.

## 6. Notas CÓMO

Extiende `api/hitl_actions.py` con endpoints `escalar`, `enviar_fraude` (routing), `solicitar_docs`
(borrador + provider de envío mock), `guardar_borrador`. Radicar reusa `aprobar`. Parcial de acciones en la
columna derecha. **Toca la capa HITL → P1.**

## 7. Precisiones tras code-review

- **🟠 "Enviar a fraude" = routing, no creación de alerta:** reusa la señal existente de `alerta_fraude` si
  la hay. Si NO hay alerta, el operador igual puede rutear el caso al carril SIU — esto **NO crea una alerta
  falsa** (P6/P7); solo registra una anotación de routing (`derivado_siu_por={usuario}`, campo aditivo). **No
  cambia el `dictamen` ni el `estado`.** Es una acción de trabajo, no un veredicto de fraude.

### Tras el CÓMO
- **🔒 P1 gate reforzado server-side:** `radicar` valida `estado == LISTO_PARA_APROBAR` → **409** si no (no
  salta revisión), además del gate de `hitl.aprobar`. Test dedicado (no-LISTO → 409).
- **Rechazar NO va en el workbench:** no estaba en las 5 acciones del QUÉ; se omite del panel (evita el PRG a
  la página vieja). Escalar cubre "devolver a revisión".
- **Defensa:** las anotaciones usan `model_validate` (re-ejecuta validadores), no `model_copy`. Mocks
  rotulados ("[demo · no enviado]").
