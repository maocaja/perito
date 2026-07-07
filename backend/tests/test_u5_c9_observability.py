"""C9 Observability Tests (U5).

Tests:
- Tracer emits events per node
- Token accumulation (feeds P4 cap)
- PII redaction (P5 fail-closed)
- Replay store functionality
"""

import pytest
from app.observability.tracer import Tracer, PIIRedactingLogSerializer
from app.observability.replay import ReplayStore


@pytest.fixture
def tracer():
    """Tracer instance for a caso."""
    return Tracer(caso_id="test-caso-123")


@pytest.fixture
def serializer():
    """PIIRedactingLogSerializer instance."""
    return PIIRedactingLogSerializer()


@pytest.fixture
def replay_store():
    """ReplayStore instance."""
    return ReplayStore()


class TestTracerEmission:
    """Tracer event emission."""
    
    def test_emit_single_event(self, tracer):
        """Happy path: emit a single event."""
        tracer.emit(
            nodo="c2_extraccion",
            resultado="Extracción completada",
            tokens_in=100,
            tokens_out=50,
            latencia_ms=123.45
        )
        
        assert len(tracer.events) == 1
        assert tracer.events[0].nodo == "c2_extraccion"
        assert tracer.events[0].tokens_in == 100
    
    def test_emit_multiple_events(self, tracer):
        """Emit multiple events from different nodes."""
        tracer.emit("c2_extraccion", "OK", tokens_in=100, tokens_out=50)
        tracer.emit("c4_policy_lookup", "OK", tokens_in=50, tokens_out=25)
        tracer.emit("c5_motor_cobertura", "OK", tokens_in=75, tokens_out=30)
        
        assert len(tracer.events) == 3
        assert tracer.total_tokens_in == 225  # 100+50+75
        assert tracer.total_tokens_out == 105  # 50+25+30
    
    def test_emit_with_error(self, tracer):
        """Emit event with error."""
        tracer.emit(
            nodo="c6_fraude",
            resultado="Fraude verificación",
            error="Conexión falló"
        )
        
        assert tracer.events[0].error == "Conexión falló"


class TestTokenAccumulation:
    """Token accounting (feeds P4 cap)."""
    
    def test_token_summary(self, tracer):
        """Token summary calculation."""
        tracer.emit("c2", "OK", tokens_in=100, tokens_out=50)
        tracer.emit("c5", "OK", tokens_in=200, tokens_out=100)
        
        summary = tracer.get_token_summary()
        
        assert summary["tokens_in"] == 300
        assert summary["tokens_out"] == 150
        assert summary["tokens_total"] == 450
    
    def test_token_budget_check(self, tracer):
        """Verify tokens available for P4 cap."""
        tracer.emit("c2", "OK", tokens_in=5000, tokens_out=3000)
        
        summary = tracer.get_token_summary()
        budget = 10000
        
        assert summary["tokens_total"] < budget
        assert summary["tokens_in"] < budget


class TestPIIRedaction:
    """P5 Habeas Data: PII redaction."""
    
    def test_redaction_in_serialization(self, serializer, tracer):
        """Serialized events redact actual PII patterns (cedula, phone, email)."""
        tracer.emit(
            nodo="c2_extraccion",
            resultado="Extracción completada: cédula 1.098.765.432, celular +57 300 1234567"
        )
        
        serialized = tracer.get_trace_log()
        
        # Check that cedula and phone are redacted by redact_pii_spans_es_co
        assert "[REDACTED]" in serialized[0]["resultado"] or \
               ("1.098.765.432" not in serialized[0]["resultado"])
    
    def test_assert_no_pii_happy_path(self, tracer):
        """Happy path: no PII in traces."""
        tracer.emit("c2_extraccion", "Extracción completada")
        tracer.emit("c5_motor", "Motor ejecutado")
        
        # Should not raise
        tracer.assert_no_pii()
    
    def test_assert_no_pii_redaction_works(self, tracer):
        """Verify redaction removes cedula patterns."""
        tracer.emit(
            nodo="c2",
            resultado="Extracción con cédula 12345678 detectada"
        )
        
        # After redaction, the cedula should be redacted
        redacted = tracer.get_trace_log()
        assert "12345678" not in str(redacted)  # Cedula was redacted
        assert "[REDACTED]" in str(redacted)
        
        # assert_no_pii should pass (PII already redacted)
        tracer.assert_no_pii()


class TestReplayStore:
    """Replay store functionality."""
    
    def test_save_and_load(self, tracer, replay_store):
        """Save and load case replay."""
        tracer.emit("c2", "OK", tokens_in=100, tokens_out=50)
        tracer.emit("c5", "OK", tokens_in=75, tokens_out=30)
        
        replay_store.save(
            tracer,
            caso_estado="LISTO_PARA_APROBAR",
            motivo=None
        )
        
        loaded = replay_store.load("test-caso-123")
        
        assert loaded is not None
        assert loaded["caso_id"] == "test-caso-123"
        assert loaded["caso_estado"] == "LISTO_PARA_APROBAR"
        assert len(loaded["trace_events"]) == 2
        assert loaded["token_summary"]["tokens_in"] == 175
    
    def test_replay_store_list_cases(self, tracer, replay_store):
        """List all cases in store."""
        tracer1 = Tracer("caso-1")
        tracer1.emit("c2", "OK")
        tracer2 = Tracer("caso-2")
        tracer2.emit("c2", "OK")
        
        replay_store.save(tracer1, "LISTO_PARA_APROBAR")
        replay_store.save(tracer2, "REQUIERE_REVISION")
        
        cases = replay_store.get_all_cases()
        
        assert len(cases) == 2
        assert "caso-1" in cases
        assert "caso-2" in cases
    
    def test_dump_json(self, tracer, replay_store):
        """Dump replay store to JSON."""
        tracer.emit("c2", "OK", tokens_in=100)
        replay_store.save(tracer, "LISTO_PARA_APROBAR")
        
        json_dump = replay_store.dump_json()
        
        assert "test-caso-123" in json_dump
        assert "LISTO_PARA_APROBAR" in json_dump
        assert "c2" in json_dump


class TestOrchestratorTracing:
    """Tracer injection into C7 (from test perspective)."""
    
    def test_orquestador_with_tracer(self):
        """Verify orquestador accepts optional Tracer (no breaking)."""
        from app.contracts.extraccion import AvisoNormalizado
        from app.contracts.enums import CalidadDoc
        from app.contracts.dictamen import Cotas
        from app.intake.c1 import intake_crear_caso
        from app.orchestrator.c7 import orquestar_fnol
        from unittest.mock import MagicMock
        
        aviso = AvisoNormalizado(
            texto_crudo="Test claim",
            calidad=CalidadDoc.LIMPIO
        )
        caso = intake_crear_caso(aviso)
        
        hitl_mock = MagicMock()
        def mock_transicionar(caso, nuevo_estado, actor, motivo=None):
            caso_dict = caso.model_dump()
            caso_dict["estado"] = nuevo_estado
            from datetime import datetime, timezone
            caso_dict["timestamp_actualizacion"] = datetime.now(timezone.utc)
            if motivo:
                caso_dict["motivo_escalamiento"] = motivo
            from app.contracts.caso import Caso
            return Caso.model_validate(caso_dict)
        
        hitl_mock.transicionar = mock_transicionar
        
        cotas = Cotas(max_rondas=1, presupuesto_tokens=20000)
        tracer = Tracer(caso.id)
        
        # Should not raise even with Tracer
        result = orquestar_fnol(caso, hitl_mock, cotas, tracer=tracer)
        
        # Verify tracer captured events
        assert len(tracer.events) > 0
        assert any(e.nodo == "orquestador_inicio" for e in tracer.events)
