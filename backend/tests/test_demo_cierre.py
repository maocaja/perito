"""Tests del cierre de la demo en vivo (DEMO_LIVE=real/deterministic + demo-mail).

Blindaje fail-closed de los ajustes que hacen que la demo se pueble DE VERDAD:
- **Unidad A** — los 5 cuerpos sintéticos traen entidades es-CO que `extraer_entidades` (M2) puebla
  (placa alineada a `demo_mail._PLACAS_DEMO`; nombre/vehículo/lugar/teléfono). 🔒P5: la cédula se
  enmascara en el display (su valor pelado no lo captura la redacción por spans) y NO llega al prompt
  de C2. El prompt de C2 constriñe `tipo_siniestro` al enum canónico (coberturas robustas en `real`).
"""

import pytest

from app.contracts.enums import TipoSiniestro
from app.intake.entidades import extraer_entidades
from app.security.redaction import build_extraction_prompt_u2
from app.dashboard.vista_caso import _valor_operador


def _campos(key: str) -> dict:
    from demo_run import ESCENARIOS
    esc = next(e for e in ESCENARIOS if e["key"] == key)
    return {c.nombre: c.valor for c in extraer_entidades(esc["aviso"])}


# ───────────────────────── Unidad A · extracción rica real ─────────────────────────

@pytest.mark.parametrize("key", ["feliz", "fraude", "no-encontrada", "campos-faltantes"])
def test_cuerpo_puebla_campos_ricos_reales(key):
    """Cada escenario de auto trae nombre/placa/vehículo/lugar/teléfono → extraer_entidades los puebla
    (en `real` desplazan al mock y les quitan el badge demo)."""
    d = _campos(key)
    for campo in ("placa", "asegurado_nombre", "vehiculo", "lugar", "telefono"):
        assert d.get(campo), f"{key}: falta el campo rico '{campo}' en el cuerpo"


@pytest.mark.parametrize("key", ["feliz", "fraude", "no-encontrada", "campos-faltantes"])
def test_placa_del_cuerpo_alinea_con_demo_mail(key):
    """La placa del cuerpo == la del adjunto denuncia (`_PLACAS_DEMO`) para que M3 correlacione la
    tercera fuente (correo) con la denuncia; en 'fraude' el SOAT difiere → divergencia real."""
    from demo_mail import _PLACAS_DEMO
    assert _campos(key)["placa"] == _PLACAS_DEMO[key][0]


def test_vehiculo_no_arrastra_basura():
    """El vehículo se extrae limpio (marca+modelo), sin arrastrar ' de placas ...' (calidad de dato)."""
    assert _campos("feliz")["vehiculo"] == "Mazda 3"


def test_vivienda_no_inventa_placa_ni_vehiculo():
    """P7 honesto: el escenario de vivienda NO trae placa ni vehículo (no se le inventan papeles de auto)."""
    d = _campos("cobertura-negativa")
    assert "placa" not in d and "vehiculo" not in d


# ───────────────────────── 🔒P5 · dos niveles (LLM redactado · operador ve el dato) ─────────────────────────

def test_operador_ve_el_dato_real():
    """P5 (decisión de gobernanza): el operador —encargado autorizado con finalidad legítima— ve el valor
    REAL (cédula/teléfono incluidos), no un `[REDACTED]`. La minimización P5 es hacia el LLM, no hacia él."""
    assert _valor_operador("79.482.135") == "79.482.135"
    assert _valor_operador("320 444 5566") == "320 444 5566"
    assert _valor_operador(None) == "—"


def test_cedula_cruda_no_llega_al_prompt_de_c2():
    """🔒P5 (lo incuestionable): la cédula (y el teléfono) del cuerpo se redactan ANTES de C2 → el LLM nunca
    los ve, aunque el operador sí."""
    from demo_run import ESCENARIOS
    aviso = next(e for e in ESCENARIOS if e["key"] == "feliz")["aviso"]
    prompt = build_extraction_prompt_u2(aviso)
    assert "79.482.135" not in prompt          # cédula redactada antes del LLM
    assert "310 555 8899" not in prompt         # teléfono redactado antes del LLM


# ───────────────────────── Unidad A · enum de tipo_siniestro (coberturas robustas) ─────────────────────────

def test_prompt_c2_constrine_tipo_al_enum_canonico():
    """El prompt de C2 lista el enum canónico de tipo_siniestro (el motor lo compara verbatim; texto libre
    no calza → NO_CUBIERTO falso). Sin esto, 'coberturas reales' es frágil en modo `real`."""
    prompt = build_extraction_prompt_u2("un choque de carro")
    for tipo in (TipoSiniestro.AUTO_COLISION, TipoSiniestro.HOGAR_AGUA, TipoSiniestro.SOAT_GASTOS_MEDICOS):
        assert tipo.value in prompt


def test_feliz_sin_deducible_para_cubierto_pleno():
    """La póliza de 'feliz' tiene deducible 0 → el motor puede dar CUBIERTO pleno (no PARCIAL por resta)."""
    from demo_run import ESCENARIOS
    from decimal import Decimal
    poliza = next(e for e in ESCENARIOS if e["key"] == "feliz")["poliza"]
    assert poliza.deducible == Decimal(0)


# ───────────────────────── Unidad B · comparativa = M3 real (integración) ─────────────────────────

def _caso_real(key: str):
    """Reconstruye el camino real: extracción rica del correo + adjuntos procesados + M3."""
    from demo_run import ESCENARIOS
    from demo_mail import _adjuntos_demo
    from app.intake.document_ai import procesar_adjuntos
    from app.agents.evidence_correlator import correlacionar
    from app.demo.scenarios import construir_caso_preset
    from app.contracts.extraccion import ExtraccionValidada

    esc = next(e for e in ESCENARIOS if e["key"] == key)
    caso = construir_caso_preset(key)
    campos = list(caso.extraccion.campos) + extraer_entidades(esc["aviso"])
    adjuntos = procesar_adjuntos(_adjuntos_demo(key))
    caso = caso.model_copy(update={"extraccion": ExtraccionValidada(campos=campos), "adjuntos": adjuntos})
    return caso.model_copy(update={"correlaciones": correlacionar(caso)})


def test_m3_correo_alineado_concuerda_entre_fuentes():
    """En 'feliz' la placa del correo coincide con la de los adjuntos → M3 marca coincidencia (varias
    fuentes concuerdan). Es el contexto real que ve el operador."""
    from app.dashboard.comparativa import comparativa_de
    comp = comparativa_de(_caso_real("feliz"))
    assert comp["disponible"] is True and comp["origen"] == "real"
    assert any(ch.icono == "✅" for ch in comp["cambios"])


def test_m3_fraude_diverge_placa_entre_correo_y_soat():
    """🔒P6 · el WOW: en 'fraude' la placa del SOAT (GHT457) difiere del correo/denuncia (GHT456) → M3 emite
    una divergencia REAL con evidencia. Solo sugiere: es un hallazgo, no un veredicto."""
    from app.dashboard.comparativa import comparativa_de
    caso = _caso_real("fraude")
    divergencias = [c for c in caso.correlaciones if not c.coincide]
    assert divergencias, "fraude debe producir ≥1 divergencia (placa correo/denuncia vs SOAT)"
    assert all(c.confianza_ajustada < 1.0 for c in caso.correlaciones)  # P6/P7: nunca veredicto
    comp = comparativa_de(caso)
    assert any(ch.icono == "⚠️" for ch in comp["cambios"])


def test_m3_vivienda_latente_sin_cruce():
    """P7: el escenario de vivienda no tiene fuentes de auto que cruzar → comparativa latente (no fabrica)."""
    from app.dashboard.comparativa import comparativa_de
    comp = comparativa_de(_caso_real("cobertura-negativa"))
    assert comp["disponible"] is False


# ───────────────────────── Unidad C · paridad determinística ─────────────────────────

def _preset_con_aviso(key: str):
    from app.demo.scenarios import construir_caso_preset
    from app.contracts.extraccion import AvisoNormalizado
    from app.contracts.enums import CalidadDoc
    from demo_run import ESCENARIOS

    aviso = next(e for e in ESCENARIOS if e["key"] == key)["aviso"]
    caso = construir_caso_preset(key)
    return caso.model_copy(update={"aviso": AvisoNormalizado(texto_crudo=aviso, calidad=CalidadDoc.LIMPIO)})


def test_fusion_agrega_ricos_sin_duplicar_base():
    """La fusión M2 añade los campos ricos del cuerpo SIN duplicar los 4 base (nombres disjuntos)."""
    from app.intake.poller import _fusionar_entidades_del_correo
    caso = _preset_con_aviso("feliz")
    base = {c.nombre for c in caso.extraccion.campos}
    fusionado = _fusionar_entidades_del_correo(caso)
    nombres = [c.nombre for c in fusionado.extraccion.campos]
    assert len(nombres) == len(set(nombres))              # sin duplicados
    assert base <= set(nombres)                            # conserva los base
    assert {"placa", "vehiculo", "asegurado_nombre"} <= set(nombres)  # añade ricos


def test_deterministic_puebla_campos_ricos_como_reales():
    """🔴 Paridad: en `deterministic` los campos ricos salen `origen='real'` (no mock), igual que en `real`."""
    from app.intake.poller import _fusionar_entidades_del_correo
    from app.dashboard.vista_caso import campos_extraidos
    caso = _fusionar_entidades_del_correo(_preset_con_aviso("feliz"))
    ui = {c.label: c.origen for c in campos_extraidos(caso)}
    assert ui.get("Placa") == "real" and ui.get("Vehículo") == "real"


def test_deterministic_procesa_correo_completo(monkeypatch):
    """Integración: `_procesar` en modo deterministic guarda un caso con los campos ricos reales del cuerpo."""
    from app.intake import poller
    from app.dashboard.store import get_caso_repository, reset_caso_repository
    from demo_run import ESCENARIOS

    reset_caso_repository()
    monkeypatch.setattr(poller.settings, "demo_live", "deterministic")

    class _Correo:
        uid = "1"
        asunto = "[DEMO:feliz] Reporte FNOL"
        cuerpo = next(e for e in ESCENARIOS if e["key"] == "feliz")["aviso"]
        adjuntos: list = []

    poller._procesar(_Correo())
    caso = get_caso_repository().list()[0]
    nombres = {c.nombre for c in caso.extraccion.campos}
    assert "placa" in nombres and "vehiculo" in nombres  # el cuerpo pobló los ricos (paridad)


# ───────────────────────── Unidad D · documentos ricos + etiquetas semánticas ─────────────────────────

def test_adjuntos_cruzan_placa_y_vehiculo():
    """El correo 'feliz' cruza DOS campos (Placa + Vehículo) entre Correo/Denuncia/SOAT, ambos coinciden →
    contexto más rico para el operador (no solo la placa)."""
    caso = _caso_real("feliz")
    labels = {c.campo_label for c in caso.correlaciones}
    assert {"Placa", "Vehículo"} <= labels
    assert all(c.coincide for c in caso.correlaciones)  # todo concuerda en el caso limpio


def test_fraude_diverge_solo_placa_vehiculo_coincide():
    """🔒P6 · señal nítida: en 'fraude' el MISMO carro (Vehículo coincide) pero la placa del SOAT NO concuerda
    → la divergencia aísla la placa (fraude realista: placa cambiada sobre el mismo vehículo)."""
    caso = _caso_real("fraude")
    por_label = {c.campo_label: c for c in caso.correlaciones}
    assert por_label["Placa"].coincide is False       # la placa diverge (GHT456 vs SOAT GHT457)
    assert por_label["Vehículo"].coincide is True     # el vehículo coincide (mismo carro)


def test_etiqueta_semantica_denuncia_y_soat():
    """M1-lite: los adjuntos se nombran por su TIPO legible (Denuncia/SOAT), no 'Documento 1/2' → el cruce
    dice 'Denuncia dice X; SOAT dice Y' (legible para el operador)."""
    from app.intake.document_ai import procesar_adjuntos
    from demo_mail import _adjuntos_demo
    etiquetas = {a.etiqueta for a in procesar_adjuntos(_adjuntos_demo("fraude"))}
    assert "Denuncia" in etiquetas and "SOAT" in etiquetas


def test_etiqueta_no_filtra_filename_crudo():
    """🔒P5: la etiqueta semántica es un TIPO ('SOAT'), nunca el nombre de archivo crudo."""
    from app.intake.document_ai import procesar_adjuntos
    [adj] = procesar_adjuntos([("denuncia_juan_perez.txt", b"DENUNCIA POLICIAL\nplaca ABC123.\n")])
    assert adj.etiqueta == "Denuncia"           # tipo semántico
    assert "juan" not in adj.etiqueta.lower()    # no filtra el filename crudo


def test_etiqueta_fallback_generico_no_filtra_pii():
    """🔒P5 (code-review D): sin keyword de tipo, la etiqueta cae al genérico ('PDF 1') — nunca los dígitos
    del filename (una cédula sin marcador)."""
    from app.intake.document_ai import _etiqueta
    etiqueta = _etiqueta("cedula_1032456789.pdf", "pdf", 1)
    assert etiqueta == "PDF 1"
    assert "1032456789" not in etiqueta


# ───────────────────────── Assets reales de demo (visor pinta imágenes) ─────────────────────────

def test_asset_solo_sirve_archivos_de_la_carpeta():
    """🔒P5 anti-traversal: `ruta_de_asset` solo resuelve archivos DENTRO de demo_assets/ con extensión
    renderizable; jamás sube de carpeta ni sirve texto/código."""
    from app.dashboard import demo_assets
    assert demo_assets.ruta_de_asset("../config.py") is None       # traversal
    assert demo_assets.ruta_de_asset("SOAT.png/../../app/main.py") is None
    assert demo_assets.ruta_de_asset("soat.txt") is None            # extensión no renderizable
    assert demo_assets.ruta_de_asset("no_existe.png") is None       # no existe


def test_asset_url_por_nombre_y_por_etiqueta():
    """El visor obtiene la URL del asset: por NOMBRE del adjunto (foto real) o por ETIQUETA semántica
    (SOAT → SOAT.png), aunque el adjunto que alimenta M3 sea el texto sintético."""
    from app.dashboard import demo_assets

    class _Doc:  # forma mínima de Documento (nombre, etiqueta)
        def __init__(self, nombre, etiqueta):
            self.nombre, self.etiqueta = nombre, etiqueta

    # foto real → calza por nombre
    assert demo_assets.url_de(_Doc("SOAT.png", "Foto 1")) == "/workbench/asset/SOAT.png"
    # el adjunto SOAT es el .txt (para M3), pero la imagen se pinta por etiqueta
    url = demo_assets.url_de(_Doc("soat.txt", "SOAT"))
    assert url == "/workbench/asset/SOAT.png"
    # sin asset que calce → None (el visor usa el mock)
    assert demo_assets.url_de(_Doc("denuncia.txt", "Denuncia")) is None


def test_foto_real_por_escenario_alineada():
    """demo_mail adjunta la foto REAL del escenario (demo_assets), con nombre que el visor pinta."""
    from demo_mail import _adjuntos_demo
    nombres_fraude = [n for n, _ in _adjuntos_demo("fraude")]
    assert "Colision_lateral_derecha.png" in nombres_fraude
    # vivienda no lleva foto de auto (P7)
    nombres_vivienda = [n for n, _ in _adjuntos_demo("cobertura-negativa")]
    assert not any(n.lower().endswith((".png", ".jpg")) for n in nombres_vivienda)


# ───────────────────────── Checklist de preparación refleja los adjuntos REALES (M1) ─────────────────────────

def test_checklist_marca_documentos_adjuntos():
    """El health-check ya NO es ciego: un documento con adjunto real sale ✔ (no 'demo'); uno sin adjunto sale
    neutro SIN badge demo; sin adjuntos del todo → 'demo' (no se puede validar)."""
    from app.demo.scenarios import construir_caso_preset
    from app.intake.document_ai import procesar_adjuntos
    from demo_mail import _adjuntos_demo
    from app.dashboard.vista_caso import health_check

    caso = construir_caso_preset("fraude").model_copy(
        update={"adjuntos": procesar_adjuntos(_adjuntos_demo("fraude"))})
    checks = {c["label"]: c for c in health_check(caso, traza=None)["checks"]}
    # adjuntos reales → ✔, sin badge demo
    for doc in ("Denuncia de tránsito", "SOAT vigente", "Fotos del vehículo"):
        assert checks[doc]["estado"] == "ok" and checks[doc]["demo"] is False, doc
    # no adjuntado → honesto, sin fingir 'demo'
    assert checks["Licencia de conducción"]["estado"] == "na" and checks["Licencia de conducción"]["demo"] is False


def test_checklist_sin_adjuntos_sigue_demo():
    """Un caso sin adjuntos (seed estático) mantiene los documentos como 'demo' (no se puede validar, P7)."""
    from app.demo.scenarios import construir_caso_preset
    from app.dashboard.vista_caso import health_check
    caso = construir_caso_preset("fraude")  # sin adjuntos
    docs = [c for c in health_check(caso, traza=None)["checks"] if c["label"] == "SOAT vigente"]
    assert docs and docs[0]["demo"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
