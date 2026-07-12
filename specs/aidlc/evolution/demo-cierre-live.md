# Cierre de la demo en vivo — `DEMO_LIVE=real|deterministic` + `demo-mail`

> Fuente de verdad del cierre de la demo. Sigue la cadencia AI-DLC: por unidad se define el **QUÉ** y el
> **CÓMO**, luego Bolt → code-reviewer → ajustar → code-reviewer → bitácora §5 → siguiente unidad.
> Anclado en el panel de 3 expertos (pipeline · narrativa de seguros · guardián P1–P7).

---

## §1 · Intent

La demo se lanza con `DEMO_LIVE=real make run` (agentes Claude) o `deterministic` (presets sin LLM), y
`MAIL_TOTAL=5 make demo-mail` inyecta 5 correos FNOL sintéticos que la orquesta procesa. Objetivo: que los
datos se **pueblen de verdad** y se vean **muy realistas**, que las **coberturas** sean reales/realistas
(motor R1–R5, cláusula citada), y que el **análisis de correos asociados** dé contexto rico al operador.

Hallazgo raíz: el cableado campos-ricos→UI y M3→estado **ya existe**; lo que faltaba es que los cuerpos de
correo fueran ricos en entidades, que la comparativa consumiera M3, y datos de póliza realistas. El grueso
del efecto es **datos**, no lógica.

## §2 · Decisión del panel — qué verá el asegurador (5 correos = 1 de cada escenario)

| Correo | Siniestro | Qué demuestra | Dictamen (motor real) |
|---|---|---|---|
| Feliz | Auto vs poste | Extracción real (placa/vehículo/lugar/nombre limpios; cédula/tel `[REDACTED]`) | CUBIERTO |
| **Fraude** ⭐ | Pérdida total, reclama 15M | Placa correo `GHT456` ≠ SOAT `GHT457` → M3 cruza 2 fuentes; monto 15M > suma 10M; **solo sugiere** (P6) | CUBIERTO_PARCIAL + alerta |
| Cobertura-negativa | Daño por agua vivienda | Cobertura negada por **reglas**, no por el LLM (P2) | NO_CUBIERTO |
| No-encontrada | Auto, póliza inexistente | Escala, no inventa póliza (P4) | REQUIERE_REVISION |
| Campos-faltantes | Auto sin monto | Corrección inline con firma → re-dictamina (P1) | REQUIERE_REVISION |

**Wow:** el caso Fraude — extracción real + cobertura determinística + divergencia real entre correo/SOAT
+ contención (solo sugiere). El "análisis de correos asociados" real vive en el **Evidence Correlator M3**
(no en el drawer mock de "Comparar correos", que se cablea en la Unidad B).

## §3 · Invariantes heredados + guardarraíles del guardián

- **P2** — cobertura la decide el motor (`rules/`, protegido, NO se toca); los campos ricos no son inputs
  del motor (verificado: solo lee póliza+fecha+tipo+monto). Coberturas se tunean por **dato de póliza**.
- **P5** — cédula/teléfono/email se redactan **antes** de C2 y en display; nombre/placa/dirección son el
  **gap NER fase-1 declarado** (sintéticos, ok) — no se vende "cero PII al LLM". La cédula pelada se
  enmascara por identidad de campo (`_red_valor`) porque la redacción por spans exige marcador.
- **P6/P1** — M3 y fraude `confianza < 1.0`, nunca cambian estado; el humano firma.
- **P7** — el badge "demo" lo maneja `origen`; se quita solo cuando el dato es real. Mock↔real honesto.

## §4 · Unidades (QUÉ + CÓMO)

### Unidad A — Poblar de verdad (datos + extracción)
- **QUÉ:** los 5 campos ricos pasan a reales y las coberturas se ven realistas en modo `real`.
- **CÓMO:**
  1. Reescribir los 5 cuerpos de `ESCENARIOS` (`demo_run.py`) con entidades es-CO (nombre, cédula, placa
     alineada a `demo_mail._PLACAS_DEMO`, teléfono, vehículo marca+modelo, lugar). Vivienda sin placa/auto.
  2. `deducible="0"` en la póliza de `feliz` → CUBIERTO pleno (antes PARCIAL por la resta).
  3. Enseñar a C2 el enum canónico de `tipo_siniestro` en el prompt (`redaction.py`) — el motor lo compara
     verbatim; texto libre daría NO_CUBIERTO falso.
  4. 🔒P5: enmascarar la cédula por identidad de campo en el display (`vista_caso._red_valor`).
- **Verificación:** `tests/test_demo_cierre.py` (extracción rica, alineación de placa, cédula `[REDACTED]`,
  cédula/tel fuera del prompt de C2, enum en el prompt, deducible 0).

### Unidad B — Análisis de correos real (comparativa → M3)
- **QUÉ:** el drawer "Comparar correos" muestra el cruce REAL de fuentes del caso (M3), no un mock fijo.
- **CÓMO:** `comparativa_de(caso)` mapea `caso.correlaciones` (`Correlacion`) → `Comparativa` sin fabricar
  cambios; `origen="real"` solo con ≥2 fuentes reales; fallback al mock `demo` si no hay correlaciones
  (honesto, P7). Plantilla: badge condicional a `origen`; copy "fuentes" cuando real.
- **Verificación:** `origen="real"` solo con ≥2 fuentes; no fabrica cambios con <2; divergencia trae
  evidencia (P6, ya en contrato).

### Unidad C — Paridad determinística
- **QUÉ:** los campos ricos también salen reales en modo `deterministic` (no solo en `real`).
- **CÓMO:** en la rama `deterministic` del poller (`poller.py`), tras fijar `caso.aviso`, fusionar
  `extraer_entidades(correo.cuerpo)` en `caso.extraccion.campos`. Sigue siendo determinístico (regex, sin
  LLM) — es el agente M2 real, no un mock.
- **Verificación:** un caso `deterministic` con cuerpo rico expone los campos ricos como reales.

### Unidad D — Documentos e imágenes más ricos
- **QUÉ:** el análisis multi-fuente cruza más campos (contexto para el operador); la galería muestra los
  adjuntos reales por caso.
- **CÓMO:** enriquecer `denuncia.txt`/`soat.txt` en `demo_mail._adjuntos_demo` (placa + fecha + más) para
  que M3 correlacione más campos. Dentro de P5: huella + texto redactado, nunca media cruda.
- **Verificación:** M3 emite ≥1 correlación adicional; la galería lista los adjuntos.

## §5 · Bitácora (una entrada por unidad: Bolt → code-review → ajustes)

### Unidad A — Poblar de verdad
- **Bolt:** cuerpos reescritos (`demo_run.py`), `deducible=0` en feliz, enum de tipo en `redaction.py`,
  `_red_valor` (redacción de cédula por identidad) en `vista_caso.py`. Tests nuevos en `test_demo_cierre.py`.
- **Ajustes propios durante el Bolt:** (i) el vehículo arrastraba " de placas …" → coma antes de "placas"
  para cortar el match limpio; (ii) la cédula pelada no la redactaba la regex por spans → `_red_valor`.
- **Verificación:** 539 + 14 nuevos en verde (hermético).
- **Code-review:** APROBADA — P1–P7 cumplidos, clean code/SOLID OK, **cero ajustes de invariantes**.
  Hallazgos no bloqueantes: (i) nombre/dirección sin redactar en display = gap NER fase-1 **declarado**
  (P7 honesto, no oculto); (ii) el reviewer reportó fallos de test por falta de `pydantic_settings` en SU
  venv — falsa alarma: la corrida hermética pasa 14/14. Sin fixes → no aplica 2ª pasada (verifica fixes).

### Unidad B — Comparativa → M3 real
- **Bolt:** `comparativa_de(caso)` reescrito para leer `caso.correlaciones` (overlay M3); mock eliminado;
  fallback latente `disponible=False` (<1 correlación). Plantillas: "Cruce de fuentes", badge condicional,
  empty state honesto. Tests `test_w13_comparativa.py` migrados + 3 de integración M3.
- **Verificación:** 559 en verde. En vivo: feliz/no-encontrada/campos-faltantes → placa coincide (3 fuentes);
  fraude → divergencia real GHT456 vs GHT457 (el WOW); vivienda → latente.
- **Code-review:** APROBADA — SIN BLOQUEOS, P1–P7 OK, redacción defensa-en-profundidad. Hallazgo MEDIA:
  `FuenteCorreo.fecha` siempre vacío en M3 → **ajustado** (default `""`, ya no se pasa explícito). Fix menor
  aplicado; sin 2ª pasada (cambio de una línea).

### Unidad C — Paridad determinística
- **Bolt:** `_fusionar_entidades_del_correo(caso)` en `poller.py`; se llama en la rama `deterministic` antes de
  M1/M3, así el correo también es fuente del cruce. Sin colisión con los 4 base; determinístico (regex, sin LLM).
- **Verificación:** 562 en verde. `deterministic` ahora muestra Placa/Vehículo como `origen="real"` (paridad).
- **Code-review:** APROBADA — SIN BLOQUEANTES, P1–P7 OK, paridad garantizada (mismo `extraer_entidades` real).
  2 hallazgos MEDIA opcionales (try-except local redundante — el llamador ya lo tiene; test redundante) → sin
  acción.
- **Ajuste posterior (paridad de cobertura):** el `deducible=0` de 'feliz' vivía solo en la póliza de
  `demo_run` (modo real). El preset de `scenarios.py` tenía deducible 1000 → 'feliz' daba CUBIERTO en real
  pero CUBIERTO_PARCIAL en deterministic. Se alineó el preset a `deducible=0` → **CUBIERTO en ambos modos**.
  Test parametrizado `test_evolution_front_ingest` migrado (feliz → CUBIERTO). 569 en verde.

### Unidad D — Documentos ricos + etiquetas semánticas
- **Bolt:** denuncia/SOAT ahora traen VEHÍCULO (alineado al correo) → M3 cruza Placa Y Vehículo. `_etiqueta`
  mapea el tipo de documento (denuncia/soat/…) → etiqueta semántica legible ('Denuncia'/'SOAT').
- **Ajuste propio durante el Bolt:** el formato del SOAT (`Vehículo: X\nPlaca:`) hacía que la regex de vehículo
  capturara a través del salto de línea → falsa divergencia; se añadió un punto tras el valor.
- **Verificación:** 567 en verde. Sin falsas divergencias: fraude diverge SOLO en Placa (Vehículo coincide);
  feliz/no-encontrada/campos-faltantes coinciden en Placa+Vehículo; vivienda latente.
- **Code-review:** APROBADA con ajustes. Hallazgos evaluados: (i) 🔴 log filtraba el filename crudo
  (`document_ai.py`) → **ajustado** (se redacta con `_redactar_nombre`; verificado: `cedula_[REDACTED]9.pdf`);
  (ii) 🔴 "crash en `combinar_alertas`" → **FALSO POSITIVO** (el guard `len(presentes)==1` ya lo cubre; no se
  tocó `fraud/`); (iii) 🟠 nombre crudo en prompt de `multimodal` → fuera de alcance, código dormido
  (solo tests), se deja como hardening futuro; (iv) 🟡 test de etiqueta fallback → **añadido**.

## §6 · Cómo lanzar la demo

Modo agentes (Claude reales) o determinístico + inyección de correos:
```
DEMO_LIVE=real make run VENV=/tmp/perito-v          # o DEMO_LIVE=deterministic
MAIL_TOTAL=5 make demo-mail VENV=/tmp/perito-v      # inyecta los 5 FNOL sintéticos
```
Requiere `DEMO_GMAIL_*` en `.env` (buzón demo) y, para `real`, `ANTHROPIC_API_KEY`. Los campos ricos, el
cruce de fuentes (M3) y las coberturas se ven reales en AMBOS modos (paridad, Unidad C).
