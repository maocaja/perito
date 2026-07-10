"""Tests W11 — Centro de documentos / galería.

Provider (DIP): interfaz `Documento` estable que M1 llenará con datos reales. P7: todo mock rotulado demo.
P5: la galería muestra etiqueta/tipo/estado, nunca media cruda con PII.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import documentos


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _un_caso():
    return get_caso_repository().list()[0]


# ---------- provider ----------

def test_documentos_de_devuelve_demo():
    docs = documentos.documentos_de(_un_caso())
    assert docs and all(isinstance(d, documentos.Documento) for d in docs)
    assert all(d.origen == "demo" for d in docs)  # P7: mock rotulado hasta M1


def test_contrato_documento_estable():
    """La interfaz que M1 implementará: {nombre, tipo, etiqueta, estado, huella, origen}."""
    d = documentos.documentos_de(_un_caso())[0]
    for campo in ("nombre", "tipo", "etiqueta", "estado", "huella", "origen"):
        assert hasattr(d, campo)
    assert d.estado in ("extraido", "validado", "relacionado")


def test_agrupar_por_tipo_suma_el_total():
    docs = documentos.documentos_de(_un_caso())
    grupos = documentos.agrupar_por_tipo(docs)
    assert sum(g["count"] for g in grupos) == len(docs)
    # los tipos del panel están todos presentes (aunque count=0)
    assert {g["tipo"] for g in grupos} == {"foto", "documento", "pdf", "audio", "video", "otro"}


def test_agrupar_por_tipo_lista_vacia():
    """Edge: sin docs, todos los tipos aparecen con count=0 (slots vacíos, no crashea)."""
    grupos = documentos.agrupar_por_tipo([])
    assert len(grupos) == 6 and all(g["count"] == 0 for g in grupos)


def test_icono_de_tipos_y_default():
    for tipo, _lbl, icono in documentos.TIPOS_PANEL:
        assert documentos.icono_de(tipo) == icono
    assert documentos.icono_de("desconocido") == "🗂️"  # default


def test_galeria_no_expone_nombre_crudo(client):
    """P5 defensivo: el nombre de archivo (posible PII con M1) NO aparece en el HTML de la galería."""
    caso = _un_caso()
    html = client.get(f"/workbench/caso/{caso.id}").text
    for d in documentos.documentos_de(caso):
        assert d.nombre not in html   # solo etiqueta/tipo/estado, nunca el nombre crudo


def test_huella_no_media_cruda():
    """P5: el mock no guarda media; la huella es None (M1 guardará la huella, no la imagen)."""
    assert all(d.huella is None for d in documentos.documentos_de(_un_caso()))


# ---------- render ----------

def test_render_galeria(client):
    html = client.get(f"/workbench/caso/{_un_caso().id}").text
    assert "Documentos e imágenes" in html
    assert "wb-galeria" in html
    assert "Foto Vehículo Frente" in html   # auto-etiqueta legible
    assert "badge-demo" in html              # rotulado


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
