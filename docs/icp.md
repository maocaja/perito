# Ideal Customer Profile (ICP) — Perito

> Buyer personas, pains, objeciones.
> ⚠️ **Advertencia de honestidad:** no hay entrevistas reales con aseguradoras ni con Elite todavía. Las secciones marcadas **[SUPUESTO — validar]** son hipótesis derivadas del deep research y de la experiencia previa de dominio, NO verbatims de clientes. El curso pide marcar esto como TBD en vez de inventarlo. Este es el vacío #1 a cerrar antes de la Estación 2.

## Firmographics (perfil de la empresa)

- **Sector:** aseguradoras (P&C / ramos generales), con foco en **ramos masivos de alto volumen y valor bajo-medio** (autos/SOAT, hogar).
- **Tamaño:** medianas — grandes suficientes para tener volumen de siniestros que justifique automatización, pero sin un core moderno (tipo Guidewire/Duck Creek) que ya traiga intake automático nativo.
- **Geografía:** Colombia / LATAM (superficie es-CO).
- **Estado de digitalización:** intake todavía manual o semi-digital; core legacy o semi-moderno. **[SUPUESTO — validar con Fasecolda/entrevistas]**

## Buyer personas

### 1. Comprador económico — Líder del área de Siniestros / COO de Operaciones
- **Le importa:** tiempo de ciclo, costo operativo por siniestro, satisfacción del asegurado, capacidad del equipo sin crecer headcount.
- **Decide** la adopción; tiene presupuesto.

### 2. Usuario final — Analista de admisión / triage de siniestros
- **Su día:** lee reportes desordenados, transcribe datos, verifica cobertura, evalúa fraude, asigna ajustador.
- **Le importa:** que la herramienta le quite trabajo mecánico sin quitarle el control ni "reemplazarlo". *(Riesgo de sabotaje silencioso si se siente reemplazado — ver `critica.md`.)*

### 3. Veto de confianza — Oficial de Cumplimiento / Legal
- **Puede matar la adopción** aunque el usuario ame la herramienta.
- **Le importa:** Habeas Data (Ley 1581 / Circular SIC 002/2024), PIA documentado, trazabilidad, responsabilidad legal (que es **indelegable**), sesgo en fraude.

## Pains (dolores)

1. **Intake manual y lento** — STP <10% en P&C; el analista es cuello de botella.
2. **Documentos caóticos y heterogéneos** — correos, PDFs, fotos, audios sin estructura.
3. **Verificación de cobertura propensa a error** — requiere leer la póliza a mano.
4. **Presión de fraude** sin capacidad de revisar todo.
5. **Riesgo regulatorio** — manejar datos personales sensibles bajo Habeas Data.

## Triggers de compra **[SUPUESTO — validar]**

- Aumento de volumen de siniestros que satura al equipo.
- Auditoría o presión regulatoria sobre manejo de datos / decisiones automatizadas.
- Iniciativa de transformación digital / reducción de costo operativo.
- Competidor que reduce su tiempo de ciclo y presiona el mercado.

## Objeciones probables y respuestas

| Objeción | Respuesta |
|---|---|
| "Nuestro core (o un vendor global) ya trae esto." | Cierto para features de extracción. Perito se especializa en la capa local: documentos en español, SOAT, cumplimiento Circular SIC, e integración — no compite en features con el core. |
| "¿Y si la IA dictamina mal una cobertura?" | El agente **nunca decide solo**: HITL obligatorio, cobertura por reglas determinísticas (no por juicio del LLM), citas a cláusula y trazas auditables. |
| "¿Esto nos quita responsabilidad legal?" | **No, y no lo prometemos.** La responsabilidad es indelegable (NAIC/SIC). Perito reduce error operativo y deja evidencia auditable — no transfiere responsabilidad. |
| "Manejo de datos personales." | PIA documentado según Circular SIC 002/2024, minimización de datos, trazabilidad. Es parte del producto. |
| "Mis ajustadores se van a resistir." | Se diseña como copiloto que les quita trabajo mecánico y les deja el juicio — no como reemplazo. |

## Verbatims

> **Ninguno disponible aún.** Requiere entrevistas con un área de siniestros real (o con Elite como proxy de dominio). **Vacío crítico #1 para la Estación 2.**
