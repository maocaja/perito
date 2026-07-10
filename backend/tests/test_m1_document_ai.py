"""Tests M1 — Document AI: adjuntos reales al pipeline + contrato `Adjunto`. 🔒 P5.

Estrato: happy (adjunto se lee/redacta/huella) + error/fail-closed (PII redactada, media cruda no persiste,
cotas P4, retro-compat mock↔real). Invariantes: P5 (nada de media/PII cruda), P4 (cotas), P6 (foto
reutilizada solo sugiere), P7 (confianza/origen honestos), Liskov (mismo contrato mock→real).
"""

import email
from email.message import EmailMessage

import pytest

from app.contracts.adjunto import Adjunto, MAX_ADJUNTOS_POR_CASO, MAX_BYTES_POR_ADJUNTO
from app.contracts.caso import Caso
from app.contracts.enums import CalidadDoc, EstadoCaso
from app.contracts.extraccion import AvisoNormalizado
from app.intake.c1 import intake_crear_caso
from app.intake.document_ai import procesar_adjuntos, registrar_huellas, hash_media_de
from app.intake.mailbox import _extraer_adjuntos, CorreoEntrante
from app.dashboard.documentos import documentos_de
from app.dashboard.vista_caso import conteo_adjuntos
from app.fraud.cross_claim import construir_alerta_cross_claim
from app.fraud.historia import get_huella_store, reset_huella_store


def _caso_con(adjuntos):
    caso = intake_crear_caso(AvisoNormalizado(texto_crudo="choque en la 80", calidad=CalidadDoc.LIMPIO))
    return caso.model_copy(update={"adjuntos": adjuntos})


# ---------- P5: redacción + nunca media cruda ----------

def test_texto_de_adjunto_se_redacta_antes_de_persistir():
    """Un .txt con una cédula → el texto del Adjunto ya viene REDACTADO (P5), la cédula no queda cruda."""
    contenido = "El asegurado tiene cédula 1032456789 y reporta el choque.".encode("utf-8")
    [adj] = procesar_adjuntos([("relato.txt", contenido)])
    assert adj.confianza == 1.0 and adj.texto  # legible
    assert "1032456789" not in adj.texto       # 🔒 P5: cédula redactada


def test_media_cruda_no_entra_al_adjunto_solo_huella():
    """Una imagen (bytes binarios) → el Adjunto NO contiene los bytes crudos; solo su huella (P5)."""
    foto = b"\xff\xd8\xff\xe0binario-crudo-de-una-foto-con-cara"
    [adj] = procesar_adjuntos([("IMG_9.jpg", foto)])
    assert adj.tipo == "foto"
    assert adj.huella and len(adj.huella) == 16   # huella perceptual (hex)
    assert adj.texto == "" and adj.confianza == 0.0  # imagen no legible (fase 1), sin texto crudo
    # el contenido crudo no aparece en ninguna parte serializada del adjunto
    serializado = adj.model_dump_json()
    assert "binario-crudo" not in serializado


def test_nombre_de_archivo_con_pii_se_redacta():
    """Un filename con cédula → el `nombre` del Adjunto se redacta (P5: un nombre de archivo puede llevar PII).
    Cubre AMBOS: con marcador ('cedula_...') y SIN marcador (dígitos largos sueltos) — fail-closed."""
    [con_marcador] = procesar_adjuntos([("cedula_1032456789.pdf", b"%PDF-1.4")])
    assert "1032456789" not in con_marcador.nombre
    # sin marcador de cédula, un dígito largo suelto igual se enmascara (el gap que el review encontró)
    [sin_marcador] = procesar_adjuntos([("Documento_52987654.pdf", b"%PDF-1.4")])
    assert "52987654" not in sin_marcador.nombre
    # un sufijo corto de cámara NO se toca (no es PII)
    [camara] = procesar_adjuntos([("IMG_4231.jpg", b"\xff\xd8")])
    assert "4231" in camara.nombre


# ---------- P4: cotas de ingesta ----------

def test_cota_numero_de_adjuntos():
    """P4: se ingieren a lo sumo MAX_ADJUNTOS_POR_CASO (sin límite oculto)."""
    crudos = [(f"f{i}.txt", b"hola") for i in range(MAX_ADJUNTOS_POR_CASO + 5)]
    assert len(procesar_adjuntos(crudos)) == MAX_ADJUNTOS_POR_CASO


def test_cota_tamano_de_adjunto():
    """P4: un adjunto sobre el tope de bytes se omite (no se procesa)."""
    gigante = b"x" * (MAX_BYTES_POR_ADJUNTO + 1)
    assert procesar_adjuntos([("enorme.txt", gigante)]) == []


# ---------- Liskov/DIP: providers mock↔real, mismo contrato ----------

def test_documentos_de_real_cuando_hay_adjuntos():
    """Con adjuntos reales → `documentos_de` devuelve `origen='real'`, misma interfaz `Documento` (Liskov)."""
    adj = procesar_adjuntos([("denuncia.pdf", b"%PDF-1.4"), ("IMG_1.jpg", b"\xff\xd8foto")])
    docs = documentos_de(_caso_con(adj))
    assert {d.origen for d in docs} == {"real"}
    assert len(docs) == 2
    assert all(hasattr(d, "etiqueta") and hasattr(d, "huella") for d in docs)  # mismo contrato


def test_providers_caen_al_mock_sin_adjuntos():
    """Retro-compat (P7): un caso SIN adjuntos sigue mostrando el mock rotulado `demo`."""
    caso = intake_crear_caso(AvisoNormalizado(texto_crudo="x", calidad=CalidadDoc.LIMPIO))
    assert {d.origen for d in documentos_de(caso)} == {"demo"}
    assert conteo_adjuntos(caso)["origen"] == "demo"


def test_conteo_adjuntos_real():
    """`conteo_adjuntos` real cuenta pdf/foto de los adjuntos (mismo shape {pdfs,fotos,origen})."""
    adj = procesar_adjuntos([("a.pdf", b"%PDF"), ("b.pdf", b"%PDF"), ("c.jpg", b"\xff\xd8")])
    c = conteo_adjuntos(_caso_con(adj))
    assert c == {"pdfs": 2, "fotos": 1, "origen": "real"}


# ---------- P6/U6: foto reutilizada real (dos casos, misma foto) ----------

def test_foto_reutilizada_dispara_cross_claim():
    """Dos casos con la MISMA foto → foto reutilizada dispara (U6). 🔒 P6: es una SUGERENCIA (confianza<1.0)."""
    reset_huella_store()
    foto = b"\xff\xd8\xff\xe0-la-misma-foto-de-siempre"
    adj_a = procesar_adjuntos([("IMG.jpg", foto)])
    registrar_huellas(adj_a, "caso-A")
    alerta = construir_alerta_cross_claim(
        caso_id="caso-B", hash_media=hash_media_de(adj_a), huella_store=get_huella_store())
    assert alerta is not None
    assert alerta.confianza < 1.0                       # 🔒 P6/P7: sugerencia, nunca veredicto
    assert any("FOTO_REUTILIZADA" in i.referencia for i in alerta.inconsistencias)
    assert "caso-B" not in alerta.model_dump_json()     # P5: evidencia referencia solo el caso previo opaco


def test_foto_reutilizada_no_cambia_estado_ni_firma():
    """🔒 P6: registrar/detectar foto reutilizada NO transiciona estado (sigue preparándose para el humano)."""
    reset_huella_store()
    foto = b"\xff\xd8foto"
    adj = procesar_adjuntos([("IMG.jpg", foto)])
    registrar_huellas(adj, "caso-A")
    caso = _caso_con(adj)
    assert caso.estado == EstadoCaso.RECIBIDO  # la ingesta de adjuntos no toca el estado (solo HITL, P1)


# ---------- captura de adjuntos en el correo (mailbox) ----------

def test_mailbox_captura_adjuntos():
    """`_extraer_adjuntos` recupera (nombre, bytes) de las partes attachment (antes se descartaban)."""
    msg = EmailMessage()
    msg["Subject"] = "Siniestro"
    msg.set_content("Reporto el choque.")
    msg.add_attachment(b"%PDF-1.4 denuncia", maintype="application", subtype="pdf", filename="denuncia.pdf")
    parsed = email.message_from_bytes(msg.as_bytes())
    adjuntos = _extraer_adjuntos(parsed)
    assert [n for n, _ in adjuntos] == ["denuncia.pdf"]
    assert adjuntos[0][1].startswith(b"%PDF")


def test_correo_entrante_adjuntos_default_vacio():
    """Retro-compat: `CorreoEntrante` sin adjuntos default a lista vacía (no rompe el poller determinístico)."""
    correo = CorreoEntrante(uid="1", asunto="x", cuerpo="y")
    assert correo.adjuntos == []


# ---------- persistencia round-trip (el Adjunto sobrevive al JSON blob) ----------

def test_adjuntos_persisten_en_el_caso():
    """El caso con adjuntos se serializa/reconstruye (JSON blob) sin perderlos ni alterar validators (P1)."""
    adj = procesar_adjuntos([("IMG.jpg", b"\xff\xd8foto")])
    caso = _caso_con(adj)
    reconstruido = Caso.model_validate_json(caso.model_dump_json())
    assert len(reconstruido.adjuntos) == 1
    assert isinstance(reconstruido.adjuntos[0], Adjunto)
    assert reconstruido.adjuntos[0].huella == adj[0].huella


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
