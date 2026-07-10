# Unit de Evolución — Carta al asegurado (borrador, demo-scope) (M)

> **Tipo:** spec a nivel de cambio (brownfield) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto (revisado tras code-reviewer) — pendiente de validación antes del CÓMO.
> **Construye sobre:** Unit H (SMTP/IMAP del Gmail demo). **Alcance: DEMO** (los temas de producción, §8, van aparte).

## 1. Intent

Cerrar el loop del workflow real: el copiloto **redacta** la comunicación al asegurado, y el **humano la
revisa, firma y envía**. Es el showcase de P1 (la IA prepara, la persona actúa). **Acotado a la demo** para
ser construible sin tocar el contrato `Caso` ni la capa de seguridad.

## 2. Cómo se resuelven los bloqueos del code-reviewer (demo-scope)

| Bloqueo del review | Resolución demo-scope |
|---|---|
| Faltan campos en `Caso` (persistencia/auditoría) | **Borrador generado on-demand, sin persistir** → cero cambios de contrato. La auditoría del envío se registra en log + confirmación en sesión. |
| No hay destinatario (el remitente del FNOL se descarta por P5) | **Destinatario fijo = `settings.demo_gmail_address`** (el buzón demo responde). Persistir el email real → §8 (producción). |
| Colisión P2/P5 en `clausula.texto` | En los datos de Perito `clausula.texto` es **genérico** ("Cobertura de colisión"), **no PII** → se usa tal cual. NER para texto libre → §8. |
| Guardrail vago | **Concreto** (ver criterio 4). |
| Flujo de UI ambiguo | **Especificado** (criterio 1). |

## 3. Criterios de completitud (verificables)

1. **Flujo de UI explícito en el detalle** (`detalle.html`), condicional al estado:
   - **`REQUIERE_REVISION` + faltantes:** aparece "Preparar carta — pedir datos".
   - **`APROBADO` / `RECHAZADO`:** aparece "Preparar carta — resolución".
   - Secuencia: clic **"Preparar carta"** → `POST /casos/{id}/carta` genera el borrador → se muestra en un
     **textarea editable** → el humano edita → clic **"Enviar"** → `POST /casos/{id}/carta/enviar` con firma →
     SMTP → confirmación "Carta enviada por [usuario]".
2. **Borrador on-demand (sin persistir):** se regenera al pedirlo; no se guarda en `Caso`.
3. **Envío = acción humana con firma (P1):** el endpoint de envío **exige `usuario`** (400 si falta), igual que
   aprobar/rechazar. **Cero auto-envío.** Destinatario **fijo al Gmail demo**.
4. **Guardrail de cobertura verbatim (P2/P7, fail-closed):** el borrador se arma con **plantilla
   determinística** que inserta `regla_aplicada` + `clausula.id` + `clausula.referencia` + `clausula.texto`.
   Si hay LLM (pulido de prosa), tras el pulido se verifica que **`clausula.id`, `regla_aplicada` Y el
   veredicto (ADMITIDA/NO ADMITIDA, sin voltear) siguen presentes**; si falta cualquiera → **se descarta el
   pulido y se usa la plantilla**. El veredicto en el guardrail cierra el vector de inyección por texto libre
   (`motivo_escalamiento`). Sin key → siempre plantilla (hermético, cero costo).
5. **Contenido correcto por tipo:**
   - Pedir-datos: nombra el/los campos faltantes ("falta **monto reclamado**; adjunte la cotización").
   - Resolución: estado (admitido/negado) + **cita del dictamen literal** (regla + cláusula).
6. **Fail-safe:** si el SMTP falla → se informa el error, el caso queda **intacto** (no cambia estado), no 500.

## 4. Restricciones e invariantes

- **P1:** ningún envío sin firma humana; el agente solo redacta. `usuario` obligatorio → 400.
- **P2/P7:** cobertura verbatim con guardrail fail-closed; el LLM no decide ni inventa términos.
- **P5:** el borrador en la UI pasa por el redactor; destinatario acotado al buzón demo (no fuga a terceros).
- **Ubicación:** rutas en `api/` (capa ACTIVA, con side-effect de correo), **no** en el dashboard passive.
- **No toca** `contracts/`, `rules/`, `orchestrator/`, `hitl/`.

## 5. Fuera de alcance (demo)

- Persistir el borrador / el envío en `Caso` (auditoría full).
- Destinatario real del asegurado, reintentos SMTP, envío masivo.
- NER para redactar nombres/direcciones en texto libre.

## 6. Verificación (tests fail-closed)

- **P1:** `POST …/carta/enviar` sin `usuario` → 400. No existe ruta de auto-envío.
- **P2/P7:** el borrador de resolución contiene `clausula.id` y `regla_aplicada` literales; con LLM simulado
  que los borra, el guardrail cae a la plantilla (el id sigue presente).
- **Estado:** resolución solo en terminal; pedir-datos solo con faltantes.
- **Hermético:** sin key, la generación usa plantilla (los tests base no llaman API).
- **Fail-safe:** un fallo de SMTP (simulado) no cambia el estado del caso.

## 7. Notas para el CÓMO (Bolt)

Nuevo router `api/cartas.py` (2 rutas), registrado en `main.py`. Reusa el SMTP de `intake/mailbox.py`
(Unit H) con `to = settings.demo_gmail_address`. Generación: `plantilla_carta(caso, tipo)` determinística
+ `pulir_prosa(texto, dictamen)` opcional con guardrail. UI en `detalle.html` (botón + textarea + form de
envío con firma). Tests en `tests/`. El LLM debe ser mockeable (como el extractor) para hermeticidad.

## 8. FLAG — unidad de producción (no en esta Unit)

Para producción real: persistir `email_asegurado` (con redacción en logs), campos de auditoría de carta en
`Caso` (enviado_por/timestamp/contenido), reintentos SMTP con backoff, y NER para redactar texto libre.
Toca `contracts/` + `security/` → unidad aparte.

**Riesgo residual conocido (demo-scope):** el `motivo_escalamiento` (texto libre) se interpola en la carta
que va al LLM del pulido. El guardrail protege la cita (regla+cláusula) **y el veredicto**, pero un pulido
manipulado podría añadir prosa espuria manteniendo esos anclas. Mitigación de producción: sanitizar el input
del analista o mantenerlo fuera del prompt del LLM (append verbatim post-pulido). Aceptable en demo (input
del analista, no del asegurado).
