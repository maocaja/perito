"""Tests W16 — Rebrand a Perito: marca config-driven, nav de íconos, búsqueda.

Invariantes: config-driven (branding único), retro-compat (todas las páginas siguen vivas), P7 (Perito es la
marca actual, sin referencias a demo/MAPFRE). Clean Code: la marca vive en un solo módulo (branding.py), sin
literales dispersos.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import branding, vista_caso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


# ---------- marca config-driven ----------

def test_marca_perito(client):
    html = client.get("/workbench").text
    assert branding.BRANDING["producto"] in html    # "Perito" (topbar/título)
    assert branding.BRANDING["logo"] in html         # el logo de marca se referencia (sidebar)
    assert "MAPFRE" not in html                       # la marca de demo se retiró por completo


def test_nav_desde_branding(client):
    """El sidebar se renderiza desde la fuente única de branding (DIP), no hardcodeado."""
    html = client.get("/workbench").text
    for item in branding.SIDEBAR:
        assert item["label"] in html


def test_nav_activo_por_filtro_no_todos_a_la_vez():
    """Bug arreglado: solo UN ítem de /workbench se marca activo según el filtro (no todos)."""
    from app.dashboard import branding

    class _QP(dict):
        pass
    inbox = {"ruta": "/workbench"}
    enproc = {"ruta": "/workbench?estado=EN_PROCESO"}
    # En /workbench sin filtro → Inbox activo, En Proceso NO.
    sin = _QP()
    assert branding.es_activo(inbox, "/workbench", sin) is True
    assert branding.es_activo(enproc, "/workbench", sin) is False
    # En /workbench?estado=EN_PROCESO → En Proceso activo, Inbox NO.
    con = _QP(estado="EN_PROCESO")
    assert branding.es_activo(enproc, "/workbench", con) is True
    assert branding.es_activo(inbox, "/workbench", con) is False


def test_ayuda_deshabilitada(client):
    """Un ítem sin destino real va deshabilitado (honesto), no como link falso."""
    html = client.get("/workbench").text
    assert "nav-disabled" in html  # Ayuda


# ---------- búsqueda global ----------

def test_barra_de_busqueda_presente(client):
    html = client.get("/workbench").text
    assert "topbar-search" in html
    assert "Buscar por póliza, cliente, placa, caso" in html


def test_busqueda_filtra_la_cola(client):
    """q filtra la cola por póliza/tipo/caso/asegurado."""
    caso = get_caso_repository().list()[0]
    # busca por el código completo del siniestro → debe quedar SOLO ese caso (es único)
    r = client.get(f"/workbench?q={caso.id}")
    assert r.status_code == 200
    assert r.text.count("data-caso-id=") == sum(
        1 for c in get_caso_repository().list()
        if caso.id.lower() in c.id.lower())


def test_busqueda_sin_resultados_no_crashea(client):
    r = client.get("/workbench?q=zzz-no-existe-xyz")
    assert r.status_code == 200
    assert r.text.count("data-caso-id=") == 0


# ---------- navegación: todo se queda en el workbench ----------

def test_nav_operacional_apunta_al_workbench(client):
    """La nav operacional (Listos/Radicados/Escalados) filtra DENTRO del workbench, no salta a la bandeja."""
    from app.dashboard import branding
    operacionales = [i for i in branding.SIDEBAR if i["label"] in
                     ("Inbox", "Listos", "Pendientes", "Radicados", "Escalados")]
    assert operacionales and all(i["ruta"].startswith("/workbench") for i in operacionales)


def test_nav_no_apunta_a_estado_transitorio():
    """Fail-closed: ningún link de la nav filtra por un estado TRANSITORIO de la orquestación (EN_PROCESO):
    ahí no reposa ningún caso → la cola saldría siempre vacía (link que aparenta filtrar y no muestra nada).
    La nav solo apunta a estados de REPOSO o agregados de UI."""
    from urllib.parse import parse_qs, urlparse
    from app.dashboard import branding
    TRANSITORIOS = {"EN_PROCESO", "RECIBIDO"}
    for item in branding.SIDEBAR:
        estados = parse_qs(urlparse(item["ruta"]).query).get("estado", [])
        assert not (set(estados) & TRANSITORIOS), f"{item['label']} apunta a un estado transitorio: {estados}"


def test_nav_listos_apunta_a_casos_accionables():
    """El atajo 'Listos' lleva al bucket accionable del analista (LISTO_PARA_APROBAR), no a un filtro vacío."""
    from app.dashboard import branding
    listos = next((i for i in branding.SIDEBAR if i["label"] == "Listos"), None)
    assert listos is not None and listos["ruta"] == "/workbench?estado=LISTO_PARA_APROBAR"


def test_cola_tarjetas_simples(client):
    """Fase 0: la cola es de escaneo rápido (chip prioridad · #id · asegurado · tipo). Se QUITARON los campos
    mock (placa/conteos/pct) → menos ruido y más honestidad P7."""
    html = client.get("/workbench").text
    for marca in ("wb-card-id", "wb-card-aseg", "wb-card-tipo"):
        assert marca in html, f"falta {marca} en la tarjeta de la cola"
    # los campos mock se retiraron de la cola
    for retirado in ("wb-card-pol", "wb-card-counts", "wb-card-pct"):
        assert retirado not in html, f"{retirado} debería haberse retirado de la cola (era mock)"


def test_clic_en_vivo_no_hereda_hx_select_del_poll(client, monkeypatch):
    """Regresión: en modo EN VIVO el #wb-cola trae hx-select="#wb-cola" (auto-poll). Sin hx-disinherit, los
    .wb-cola-item HEREDARÍAN ese hx-select y al hacer clic htmx buscaría #wb-cola en la respuesta del caso
    (que no lo tiene) → swap VACÍO ("no pinta nada al lado derecho"). El poll debe llevar hx-disinherit."""
    from app.dashboard import c11
    monkeypatch.setattr(c11.settings, "demo_live", "real")  # → en_vivo=True: se activa el auto-poll
    html = client.get("/workbench?rol=CUMPLIMIENTO").text
    assert 'hx-select="#wb-cola"' in html, "el auto-poll debe estar activo en vivo"
    assert 'hx-disinherit' in html, "el poll debe cortar la herencia para no romper el clic del caso"


def test_seleccion_persiste_y_sin_hx_on_fragil(client):
    """La selección del caso se re-resalta tras el auto-refresh (JS), y ya no se usa el hx-on:click frágil."""
    html = client.get("/workbench").text
    assert "htmx:afterSwap" in html and "function marcar" in html  # persistencia
    assert "hx-on:click" not in html                                # se quitó el frágil


def test_filtro_por_estado_en_el_workbench(client):
    """El nav 'Escalados' (estado=REQUIERE_REVISION) filtra la cola sin salir de la estación."""
    from app.contracts.enums import EstadoCaso
    esperado = sum(1 for c in get_caso_repository().list() if c.estado == EstadoCaso.REQUIERE_REVISION)
    r = client.get("/workbench?estado=REQUIERE_REVISION")
    assert r.status_code == 200
    assert r.text.count("data-caso-id=") == esperado


# ---------- acciones: una primaria, el resto secundario (V1·5) ----------

def test_acciones_una_primaria_resto_secundario(client):
    """V1·5 (colega senior): Radicar es la ÚNICA primaria (verde/go); las demás son secundarias calmas
    (btn-ghost), no botones de color fuera de paleta (antes azul .btn-solicitar / morado .btn-escalar)."""
    html = client.get(f"/workbench/caso/{get_caso_repository().list()[0].id}").text
    assert "btn-radicar" in html          # la primaria (verde = firmar/go)
    assert "btn-ghost" in html            # las secundarias calmas
    assert "btn-solicitar" not in html and "btn-escalar" not in html  # sin azul/morado fuera de paleta


# ---------- retro-compat ----------

def test_todas_las_paginas_vivas(client):
    # W20/A6+A7: el board `/casos` y la página `detalle` se retiraron; superficies vivas = Workbench + panel + nuevo.
    assert client.get("/workbench").status_code == 200
    assert client.get("/panel").status_code == 200
    assert client.get("/nuevo").status_code == 200  # branding inyectado también en intake


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
