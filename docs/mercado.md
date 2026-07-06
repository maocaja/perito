# Análisis de Mercado — Perito

> Tamaño, competidores, regulación y geografías.
> Fuente: `research/validacion.md` y `research/critica.md` (deep research jul 2026, verificado adversarialmente).

## Tamaño y tendencia

- **IA generativa en seguros: ~28% CAGR.** ~$1.39B (2025) → ~$1.77B (2026) → ~$4.83B (2030) según TBRC.
- **Caveat crítico:** los números **absolutos divergen mucho** entre firmas (TBRC $4.83B/2030 vs Allied $14.4B/2032). Lo robusto es **la magnitud del CAGR (~28-34%)**, consenso entre firmas; el número absoluto es un estimado de un solo vendor, NO consenso.

> ⚠️ Refutadas: "$0.46B→$0.97B a 16.2% CAGR" (IA-en-claims) y "$10.36B→$154.39B a 35.7%" (IA-en-seguros). No usar.

## Panorama competitivo (verificado)

| Actor | Qué hace | Relevancia para Perito |
|---|---|---|
| **Duck Creek** | Lanzó **"Agentic FNOL" (28-abr-2026)**: captura + verificación de cobertura + fraude en admisión + enrutamiento — nativo en el core | **Amenaza directa**: cubre el alcance exacto de Perito |
| **Shift Technology** | Detección de fraude + extracción documental (Azure), 2.6B+ pólizas | Valida el stack; foco en fraude, no FNOL intake |
| **Tractable** | Peritaje de daños de autos con visión | Adyacente |
| **CCC Intelligent Solutions** | IA predictiva/generativa para claims (IX Cloud) | Incumbente P&C |
| **Sapiens, Quantiphi, ZestyAI, SimplifAI** | Core systems / servicios IA / plataformas agénticas | Categoría poblada |
| **Hyperscalers (AWS, Google, Azure)** | Stacks verticales silicio→agente→workflow | El lock-in se mueve a agentes/workflow |

**Lectura:** la categoría está **madura y poblada** — no es idea especulativa, pero tampoco un espacio vacío. Como producto comercial, **el core system lo absorbe** (riesgo de comoditización confirmado). El único wedge defensible sería la especialización local.

## Regulación

### Colombia (verificado — el ángulo local)
- **Circular Externa 002 de la SIC (21-ago-2024):** lineamientos para tratamiento de datos personales en sistemas de IA, anclada en **Habeas Data (Art. 15 Constitución)** y **Leyes 1266/2008 y 1581/2012**.
- **Exige un estudio de impacto de privacidad (PIA) documentado ANTES de diseñar** el sistema de IA (descripción del tratamiento + evaluación de riesgos a los titulares + medidas de protección), cuando el producto entraña alto riesgo — umbral que un agente FNOL con datos sensibles plausiblemente cruza.
- *Caveat:* "vinculante" es fuerte — es un instrumento de **lineamientos interpretativos** bajo Ley 1581, no un estatuto de IA autónomo.
- **Implicación:** el cumplimiento es parte del producto (PIA + trazas + HITL). Ángulo difícil de replicar por un vendor global genérico.

### EE.UU. (contexto de riesgo importado)
- **NAIC Model Bulletin** (adoptado por 24+ estados y D.C.): la responsabilidad legal por decisiones de IA **es indelegable** — "comprar IA no transfiere la obligación al vendedor". Exige programa escrito de gobernanza, evaluaciones de riesgo y auditoría.
- **Litigios reales:** Cigna (PxDx), UnitedHealth (nH Predict, dismissal negado feb-2025), State Farm (sesgo racial algorítmico, sobrevivió desestimación). *Mayoría en seguros de salud, no P&C — analogía fuerte, no idéntica.*
- **El seguro excluye el riesgo de IA de sus pólizas** (Berkley, AIG, ISO CG 40 47 ene-2026): la responsabilidad recae en quien despliega.

## Geografías

- Norteamérica domina el mercado; Asia-Pacífico y Europa como oportunidades. **LATAM NO aparece destacado** — se lee como riesgo (mercado inmaduro) o como wedge menos saturado. La evidencia no resuelve cuál.

## Huecos de mercado (para completar con fuente primaria)

1. Costo/tiempo real y verificable del triage manual de FNOL en Colombia.
2. Postura de la **Superintendencia Financiera** (distinta de la SIC) sobre IA en siniestros; interacción con **SOAT**.
3. Tasa real de adopción de IA en aseguradoras Colombia/LATAM (fuente primaria: Fasecolda/Celent) — las cifras encontradas fueron refutadas.
