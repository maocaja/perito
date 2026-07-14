"""Tests W11 — Centro de documentos / galería.

Provider (DIP): interfaz `Documento` estable, llenada con los adjuntos REALES del correo (M1).
🔒 P7: NO se fabrican documentos — un correo sin adjuntos deja la galería vacía (estado honesto).
P5: la galería muestra etiqueta/tipo/estado, nunca media cruda con PII.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import documentos
from app.contracts.enums import CalidadDoc
from app.contracts.extraccion import AvisoNormalizado
from app.intake.c1 import intake_crear_caso
from app.intake.document_ai import procesar_adjuntos


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _caso_con_adjuntos():
    """Caso con adjuntos REALES (foto + pdf), como los deja la ingesta de correo (M1)."""
    caso = intake_crear_caso(AvisoNormalizado(texto_crudo="choque en la 80", calidad=CalidadDoc.LIMPIO))
    adj = procesar_adjuntos([("foto.jpg", b"\xff\xd8foto-siniestro"), ("denuncia.pdf", b"%PDF-1.4")])
    return caso.model_copy(update={"adjuntos": adj})


def _caso_sin_adjuntos():
    return intake_crear_caso(AvisoNormalizado(texto_crudo="reporte sin adjuntos", calidad=CalidadDoc.LIMPIO))


# ---------- provider ----------

def test_documentos_de_mapea_adjuntos_reales():
    docs = documentos.documentos_de(_caso_con_adjuntos())
    assert docs and all(isinstance(d, documentos.Documento) for d in docs)
    assert all(d.origen == "real" for d in docs)  # solo lo que llegó en el correo


def test_sin_adjuntos_no_fabrica_documentos():
    """🔒 P7: un correo sin adjuntos → galería vacía, NUNCA un set demo fabricado."""
    assert documentos.documentos_de(_caso_sin_adjuntos()) == []


def test_contrato_documento_estable():
    """La interfaz `Documento`: {nombre, tipo, etiqueta, estado, huella, texto, origen}."""
    d = documentos.documentos_de(_caso_con_adjuntos())[0]
    for campo in ("nombre", "tipo", "etiqueta", "estado", "huella", "texto", "origen"):
        assert hasattr(d, campo)
    assert d.estado in ("extraido", "validado", "relacionado")


def test_agrupar_por_tipo_suma_el_total():
    docs = documentos.documentos_de(_caso_con_adjuntos())
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


def test_huella_es_la_huella_no_media_cruda():
    """P5: del adjunto se guarda la HUELLA perceptual, nunca la media cruda."""
    foto = next(d for d in documentos.documentos_de(_caso_con_adjuntos()) if d.tipo == "foto")
    assert foto.huella  # huella poblada (hex), no la imagen


def _seeded_con_adjuntos():
    """Caso sembrado con adjuntos reales (auto); robusto al orden de `list()`."""
    return next(c for c in get_caso_repository().list() if c.adjuntos)


def _seeded_sin_adjuntos():
    """Caso sembrado de vivienda, sin adjuntos (correo sin documentos)."""
    return next(c for c in get_caso_repository().list() if not c.adjuntos)


def test_galeria_no_expone_nombre_crudo(client):
    """P5 defensivo: el nombre de archivo (posible PII) NO aparece en el HTML de la galería."""
    caso = _seeded_con_adjuntos()
    html = client.get(f"/workbench/caso/{caso.id}").text
    for d in documentos.documentos_de(caso):
        assert d.nombre not in html   # solo etiqueta/tipo/estado, nunca el nombre crudo


# ---------- render ----------

def test_render_galeria_con_adjuntos(client):
    caso = _seeded_con_adjuntos()
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Documentos e imágenes" in html
    assert "wb-galeria" in html
    assert "Adjuntos de demostración" not in html   # ya no se fabrica ni rotula demo el bloque de docs


def test_render_galeria_vacia_sin_adjuntos(client):
    """🔒 P7: correo sin adjuntos → estado vacío honesto, sin galería fabricada."""
    caso = _seeded_sin_adjuntos()
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "El correo no traía documentos adjuntos" in html
    assert "wb-galeria" not in html


def test_visor_pinta_texto_redactado(client):
    """El visor de un documento de TEXTO pinta el texto real (redactado, P5), no un placeholder."""
    caso = _seeded_con_adjuntos()
    docs = documentos.documentos_de(caso)
    idx = next(i for i, d in enumerate(docs) if d.texto)   # el primer doc con texto legible (.txt)
    html = client.get(f"/workbench/documento/{caso.id}?doc={idx}").text
    assert "wb-ev-texto" in html            # se pinta el bloque de texto real
    assert "DENUNCIA POLICIAL" in html      # contenido del documento
    assert "wb-ev-page" not in html         # NO el placeholder skeleton


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
