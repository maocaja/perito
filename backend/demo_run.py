"""demo_run.py — `make demo`: el showcase de un comando (Unit G).

Corre los 4 escenarios de Perito y hace visible cada herramienta que construimos:

- **Pipeline real:** con `ANTHROPIC_API_KEY` real, mete cada aviso por `orquestar_fnol`
  (C2 Haiku extrae → C3 Sonnet verifica → C4 grounding → C5 motor R1-R5 → C6 fraude).
  Sin key → cae a los **presets determinísticos** (sin LLM, costo cero) para que el comando
  NUNCA falle (tier degradado, P7 honesto).
- **Narración en vivo:** imprime cada paso (C2 → C3 → C5 motor+cláusula → C6 fraude → estado)
  sin necesidad de abrir Langfuse.
- **Persistencia:** guarda los 4 casos (Neon si `PERSISTENCE=postgres`, si no in-memory) →
  visibles en `/casos` y `/panel`.
- **Trazas:** emite a Langfuse (si hay keys) vía `ReplayStore.save`.
- **Resumen:** costo/caso + % escalado (intervención humana) + links.

REUSA el dominio existente (intake/orquestador/motor/fraude/store/replay/métricas C11); NO
reimplementa nada — solo LEE el `Caso` ya resuelto y el `Tracer`.

P5: cada valor de campo se redacta con `redact_pii_spans_es_co` antes de imprimir; NUNCA se
imprime `texto_crudo` (el aviso crudo va solo en el tier real, que es texto de demo sin PII).

Uso:  make demo   (o, desde backend/:  python demo_run.py)
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.contracts.dictamen import Cotas
from app.contracts.enums import CalidadDoc, EstadoCaso
from app.contracts.extraccion import AvisoNormalizado
from app.intake.c1 import intake_crear_caso
from app.orchestrator.c7 import orquestar_fnol
from app.policy.lookup import set_poliza_store
from app.hitl import c8
from app.observability.tracer import Tracer
from app.observability.replay import get_replay_store
from app.observability import langfuse_sink
from app.dashboard.store import get_caso_repository, reset_caso_repository
from app.dashboard.c11 import calcular_metricas
from app.demo.scenarios import poliza_demo, construir_caso_preset
from app.demo.seed import sembrar_traza_demo
from app.security.redaction import redact_pii_spans_es_co

# Fecha del siniestro: DENTRO de la vigencia de la póliza demo (poliza_demo usa hoy±365) y en el
# pasado (C3 no la marca "futura"). Dinámica para no vencerse cuando avanza el calendario.
FECHA = (date.today() - timedelta(days=30)).isoformat()

# Escenarios: aviso en LENGUAJE NATURAL (como un usuario real lo escribe — el extractor C2 saca los
# campos del texto libre; el usuario NO necesita saber la estructura) + póliza a sembrar (None = NO
# se siembra → escala P4). Las keys coinciden con los presets de `scenarios.py` (fallback determinístico).
ESCENARIOS = [
    # Nota: los números de póliza son NEUTROS a propósito. El verificador adversarial (C3, Sonnet)
    # lee el numero_poliza; un nombre semántico (…-FRAUDE, …-NO-EXISTE) sesga su juicio de fidelidad
    # y escala antes de llegar a C5/C6. El diferenciador vive en los DATOS (suma, tipo, si se sembró),
    # no en el nombre.
    {
        "key": "feliz",
        "titulo": "FELIZ — cobertura OK",
        "aviso": f"Buenos días, espero que se encuentren muy bien. Mi nombre es Andrés Ramírez, con cédula "
                 f"79.482.135, y les escribo bastante preocupado porque tuve un accidente con mi carro, un "
                 f"Mazda 3, placas FBC123, y la verdad es la primera vez que me pasa algo así, no sé bien "
                 f"cómo es el proceso. Resulta que venía saliendo del trabajo por la Carrera 30 con Calle 45, "
                 f"ya era tarde y estaba lloviznando, había mucho tráfico. Un motociclista se me atravesó de "
                 f"repente y por no atropellarlo frené y giré el timón, pero terminé estrellándome contra un "
                 f"poste de la luz del separador. El golpe fue en toda la parte delantera derecha: la puerta "
                 f"del copiloto quedó abollada, el farol derecho destruido y el espejo partido. Gracias a Dios "
                 f"yo salí bien, solo un susto y un golpecito en el brazo, pero el carro sí quedó bastante "
                 f"maltratado. El siniestro fue el {FECHA}. Tengo con ustedes la póliza número POL-DEMO-1001, "
                 f"que saqué hace como un año para el vehículo. Ya lo llevé a un taller de confianza y me "
                 f"dijeron que la reparación, entre latonería, pintura, el farol y el espejo, sale en unos "
                 f"5.000.000 de pesos, aunque todavía me deben pasar la cotización formal. Mi celular es el "
                 f"310 555 8899 por si necesitan contactarme. Quisiera saber qué debo hacer, qué documentos "
                 f"necesitan y si esto lo cubre mi póliza. Quedo muy atento a su respuesta. Mil gracias por la "
                 f"ayuda.",
        "poliza": poliza_demo(numero="POL-DEMO-1001", suma="100000000", deducible="0"),  # deducible 0 → CUBIERTO pleno
        "objetivo": "P2/P3: el motor dictamina y cita regla + cláusula · P1: el caso NO se cierra solo",
    },
    {
        "key": "fraude",
        "titulo": "FRAUDE — monto excede la suma asegurada",
        "aviso": f"Cordial saludo. Mi nombre es Carlos Gutiérrez, con cédula 1.020.457.881. Escribo para "
                 f"reportar un siniestro que tuve con mi vehículo, un Chevrolet Onix, placas GHT456; fue un "
                 f"choque bastante fuerte y estoy muy afectado. Ocurrió el {FECHA} sobre la Autopista Norte "
                 f"con Calle 170; venía a velocidad normal cuando otro carro se pasó el semáforo en rojo y me "
                 f"impactó de lado, mandándome contra el andén. El vehículo quedó prácticamente destruido: el "
                 f"chasis se torció, se activaron todos los airbags, el motor quedó sonando raro, las dos "
                 f"puertas del lado derecho no abren, el eje delantero se dañó y la carrocería quedó doblada. "
                 f"Es un carro que yo cuidaba muchísimo, le había puesto rines nuevos y sonido. Mi póliza con "
                 f"ustedes es la POL-DEMO-1002. Después de hablar con un perito conocido y con el taller, "
                 f"estoy reclamando 15.000.000 de pesos por la totalidad de los daños, porque francamente creo "
                 f"que el carro quedó para pérdida total. Mi celular es 320 444 5566. Necesito que me ayuden "
                 f"con esto lo más pronto posible porque ese carro es mi herramienta de trabajo y sin él no "
                 f"puedo generar ingresos. Agradezco su pronta gestión y quedo pendiente de sus indicaciones.",
        "poliza": poliza_demo(numero="POL-DEMO-1002", suma="10000000"),  # suma 10M < monto 15M → fraude
        "objetivo": "P6: fraude detectado y explicable (monto excede suma) · solo sugiere, decide el humano",
    },
    {
        "key": "cobertura-negativa",
        "titulo": "COBERTURA NEGATIVA — tipo no contratado",
        "aviso": f"Buenas tardes. Mi nombre es Diana Torres, con cédula 52.876.109, y escribo para reportar "
                 f"un daño en mi vivienda ubicada en la Calle 128 # 19-45 y ver si me lo pueden cubrir. El "
                 f"{FECHA} en la madrugada se reventó una tubería del baño del segundo piso, al parecer por la "
                 f"presión del agua, y cuando me desperté ya había un reguero por toda la casa. El agua bajó "
                 f"por las escaleras y me dañó los muebles de la sala: el sofá quedó empapado, la mesa de "
                 f"madera se hinchó y la alfombra quedó inservible. También se levantó una parte del piso "
                 f"laminado del comedor. Fue un desastre, pasamos toda la mañana secando y sacando agua con "
                 f"la familia, imagínese el estrés. Mi póliza es la POL-DEMO-1003. Un conocido que sabe de "
                 f"construcción me ayudó a calcular y dice que reponer los muebles y arreglar el piso sale en "
                 f"unos 3.000.000 de pesos más o menos. Es un daño por agua en la vivienda, tipo HOGAR_AGUA. "
                 f"Mi celular es 315 777 8899. Quisiera saber si mi póliza responde por esto y cómo es el "
                 f"trámite para la reclamación. Muchas gracias de antemano por su atención.",
        "poliza": poliza_demo(numero="POL-DEMO-1003", coberturas=("AUTO_COLISION",), suma="100000000"),  # suma alta → sin fraude incidental
        "objetivo": "P2: NO_CUBIERTO citando la regla de cobertura · lo decide el motor, NO el LLM",
    },
    {
        "key": "no-encontrada",
        "titulo": "PÓLIZA NO ENCONTRADA — escala",
        "aviso": f"Hola, buenas. Mi nombre es Jorge Medina, con cédula 80.145.223. Necesito reportar un "
                 f"choque que tuve con mi carro, un Renault Logan, placas JKL789, el {FECHA}. Iba por la "
                 f"Calle 80 con Carrera 68, camino a la finca, cuando otro vehículo que venía en sentido "
                 f"contrario me cerró y, para esquivarlo, me subí a una cuneta; el carro se raspó todo el "
                 f"costado izquierdo, se dañó el rin delantero y el bómper quedó guindando de un lado. No fue "
                 f"un choque de muerte pero sí quedó feo y me tocó sacarlo con grúa. Mi número de póliza es "
                 f"POL-DEMO-9999, o al menos ese es el que tengo anotado en un papel que me dio el corredor "
                 f"cuando la compré. Los daños, según un mecánico que conozco, salen por ahí en 4.000.000 de "
                 f"pesos entre el rin, el bómper y la latonería de todo el costado. Mi celular es 300 111 "
                 f"2233. Quisiera empezar el proceso de reclamación cuanto antes. Quedo atento a lo que "
                 f"necesiten. Muchas gracias.",
        "poliza": None,  # a propósito NO se siembra → C4 no la encuentra → escala P4
        "objetivo": "P4: escala a REQUIERE_REVISION — NO inventa una póliza ni cierra el caso",
    },
    {
        "key": "campos-faltantes",
        "titulo": "DATOS FALTANTES — escala pidiendo info",
        "aviso": "Buenos días. Mi nombre es Laura Castaño, con cédula 43.998.210. Les cuento que ayer tuve "
                 "un accidente con el carro, un Kia Picanto, placas MNO321, y estoy bastante estresada, no "
                 "había tenido tiempo de reportarlo antes. Fue saliendo de un parqueadero de un centro "
                 "comercial sobre la Calle 80 con Carrera 15: otro carro me pegó por detrás cuando yo estaba "
                 "saliendo en reversa, un golpe en el bómper trasero y la compuerta del baúl que ya no cierra "
                 "bien. La otra persona se bajó, discutimos un rato, tomamos fotos y nos intercambiamos los "
                 "datos del seguro, pero yo estaba muy nerviosa y la verdad no revisé bien todo. Mi póliza "
                 "con ustedes es la POL-DEMO-1001. Todavía no tengo ni idea de cuánto pueda costar el "
                 "arreglo, apenas mañana voy a llevar el carro a un taller para que me den la cotización, así "
                 "que aún no les puedo decir el monto de los daños. Mi celular es 311 222 3344. Quería ir "
                 "adelantando el reporte mientras tanto. ¿Me pueden ir diciendo qué documentos necesito? "
                 "Gracias, quedo muy pendiente.",
        "poliza": None,  # reusa POL-DEMO-1001 (sembrada por 'feliz'); falta el monto → escala (P4)
        "objetivo": "P4: aviso incompleto (sin monto) → escala, no inventa · el humano pide el dato",
    },
]


def _key_es_real() -> bool:
    """True si hay una ANTHROPIC_API_KEY que no sea el placeholder de tests."""
    k = (settings.anthropic_api_key or "").strip()
    return bool(k) and k.lower() != "test"


def _red(valor) -> str:
    """Redacta un valor antes de imprimir (P5, defensa-en-profundidad: `valor` es string libre del LLM)."""
    return redact_pii_spans_es_co(str(valor)) if valor is not None else "—"


def _campo(caso, nombre):
    """Devuelve el CampoExtraido presente por nombre, o None."""
    if not caso.extraccion:
        return None
    return next((c for c in caso.extraccion.campos if c.nombre == nombre and not c.ausente), None)


def _ev(tracer, sub):
    """Primer evento del tracer cuyo nodo contenga `sub` (o None)."""
    if tracer is None:
        return None
    return next((e for e in tracer.events if sub in e.nodo), None)


def _narrar(caso, tracer) -> None:
    """Narra el pipeline en vivo desde el Caso resuelto (+ tokens del tracer). Redacta cada valor (P5)."""
    np_, tp_, mo_ = _campo(caso, "numero_poliza"), _campo(caso, "tipo_siniestro"), _campo(caso, "monto_reclamado")
    confs = [c.confianza for c in (caso.extraccion.campos if caso.extraccion else []) if c.confianza is not None]
    conf_s = f"conf {max(confs):.2f}" if confs else "conf —"
    toks = tracer.get_token_summary()["tokens_total"] if tracer else 0
    tok_s = f"{toks} tok" if toks else "sin LLM"
    print(f"  🔵 C2 extractor   → {_red(np_ and np_.valor)} · {_red(tp_ and tp_.valor)} · {_red(mo_ and mo_.valor)}  · {conf_s} · {tok_s}")

    c3 = _ev(tracer, "c3")
    print(f"  🔵 C3 verifier    → {c3.resultado if c3 else 'consistente'}")

    if caso.dictamen:
        cl = caso.dictamen.clausula
        cl_s = f"cláusula {cl.id}, {cl.referencia}" if cl else "sin cláusula (escala)"
        print(f"  ⚙️  C5 motor R1-R5 → {caso.dictamen.resultado.value}  (regla {caso.dictamen.regla_aplicada} · {cl_s})")
    else:
        print("  ⚙️  C5 motor R1-R5 → escala (sin dictamen)")

    if caso.alerta_fraude:
        print(f"  🔎 C6 fraude       → ⚠ severidad {caso.alerta_fraude.severidad} (sugiere revisión, NO bloquea — P6)")
    else:
        print("  🔎 C6 fraude       → sin inconsistencias")

    icon = "✅" if caso.estado == EstadoCaso.LISTO_PARA_APROBAR else "⏫"
    print(f"  {icon} estado: {caso.estado.value}   ← el orquestador NUNCA cierra (P1: firma el humano)")
    if caso.motivo_escalamiento:
        print(f"     motivo: {_red(caso.motivo_escalamiento)}")


def _correr_escenario(esc, real, cotas, repo) -> None:
    print("\n" + "=" * 72)
    print(f"ESCENARIO: {esc['titulo']}")
    if real:
        print(f"Aviso: {esc['aviso']}")
        caso = intake_crear_caso(AvisoNormalizado(texto_crudo=esc["aviso"], calidad=CalidadDoc.LIMPIO))
        caso = caso.model_copy(update={"id": repo.reservar_codigo()})  # código de siniestro definitivo
        tracer = Tracer(caso.id)
        try:
            caso = orquestar_fnol(caso, c8, cotas, tracer)
        except Exception as e:  # fail-closed (P4): si el pipeline falla, escala — nunca 500 ni inventa
            caso = caso.model_copy(update={
                "estado": EstadoCaso.REQUIERE_REVISION,
                "motivo_escalamiento": f"Orquestación falló: {e}",
            })
        repo.save(caso)
        get_replay_store().save(tracer, caso.estado.value, caso.motivo_escalamiento)  # → Langfuse si on
    else:
        caso = construir_caso_preset(esc["key"])  # determinístico, sin LLM
        caso = caso.model_copy(update={"id": repo.reservar_codigo()})  # código de siniestro definitivo
        repo.save(caso)
        sembrar_traza_demo(caso)
        tracer = None
    _narrar(caso, tracer)
    print(f"  🎯 Objetivo del escenario → {esc['objetivo']}")


def _resumen(real, repo) -> None:
    store = get_replay_store()
    replays = [r for r in (store.load(cid) for cid in store.get_all_cases()) if r is not None]
    casos = repo.list()
    m = calcular_metricas(casos, replays)
    costo_caso = round(m["costo_estimado"] / m["total"], 4) if m["total"] else 0.0

    print("\n" + "=" * 72)
    print("RESUMEN")
    print(f"  casos procesados   : {m['total']}")
    print(f"  por dictamen       : {m['por_dictamen']}")
    print(f"  fraude             : {m['fraude'] or 'sin alertas'}")
    print(f"  % escalado (intervención humana) : {m['pct_escalado']}%")
    if real:
        print(f"  costo estimado     : ~USD {m['costo_estimado']}  ({costo_caso}/caso) — agentes Claude reales")
    else:
        print("  costo real         : USD 0.00 (tier determinístico, sin LLM) · tokens mostrados = traza demo ilustrativa")
    print(f"  cláusula citada    : {m['clausula_ok']}/{m['clausula_total']} dictámenes terminales de cobertura (P2/P3)")

    print("\n  Míralo:")
    if langfuse_sink.is_enabled():
        host = settings.langfuse_host or "https://cloud.langfuse.com"
        print(f"    · Langfuse (traza por paso)   → {host}  (proyecto: fnol-case)")
    else:
        print("    · Langfuse                     → desactivado (export LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY)")
    print("    · Dashboard (bandeja + panel)  → make run  →  http://localhost:8000/casos  y  /panel")
    persist = "Postgres/Neon (sobrevive reinicio)" if settings.persistence == "postgres" else "in-memory (efímero)"
    print(f"    · Persistencia                 → {persist}")
    print("    · Evals agénticos              → make evals  (pytest -m agentic, requiere key real)")
    print("\n  P1 en TODOS: estado ∈ {LISTO_PARA_APROBAR, REQUIERE_REVISION} — nunca terminal; firma el humano.")


def main() -> int:
    real = _key_es_real()
    print("=" * 72)
    print("PERITO — showcase (`make demo`)")
    if real:
        print("Tier REAL: agentes Claude (C2 Haiku + C3 Sonnet) en vivo.")
        print("⚠ Costo: son llamadas reales a la API — ~USD 0.02 los 4 casos (centavos).")
    else:
        print("Tier DETERMINÍSTICO: sin ANTHROPIC_API_KEY real → presets (sin LLM, costo cero).")
        print("  (export ANTHROPIC_API_KEY=<tu-key> para ver los agentes reales corriendo.)")

    reset_caso_repository()
    repo = get_caso_repository()
    repo.clear()
    get_replay_store().clear()

    if real:
        set_poliza_store({p["poliza"].numero: p["poliza"] for p in ESCENARIOS if p["poliza"]})

    cotas = Cotas(max_rondas=1, presupuesto_tokens=50000)
    for esc in ESCENARIOS:
        _correr_escenario(esc, real, cotas, repo)

    _resumen(real, repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
