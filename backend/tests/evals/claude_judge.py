"""ClaudeJudge — juez LLM (Claude) para DeepEval (D). NUNCA OpenAI.

DeepEval por default usa OpenAI; este wrapper hace que las métricas con juez (Faithfulness,
Hallucination, G-Eval) usen Claude. Soporta el `schema` (structured output) que DeepEval 4.x pasa
para métricas que esperan JSON estructurado del juez.
"""

import json
import re
from typing import Any, Optional

from deepeval.models import DeepEvalBaseLLM


class ClaudeJudge(DeepEvalBaseLLM):
    """Juez Claude para DeepEval. Lee ANTHROPIC_API_KEY del entorno."""

    def __init__(self, model: str = "claude-sonnet-5") -> None:
        self.model = model
        self._client = None

    def get_model_name(self) -> str:
        return f"claude-judge:{self.model}"

    def load_model(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic()  # ANTHROPIC_API_KEY del entorno
        return self._client

    def _call(self, prompt: str, max_tokens: int = 4000) -> str:
        client = self.load_model()
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        # Sonnet 5 puede devolver ThinkingBlock + TextBlock → tomar SOLO el texto (no el thinking).
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return "\n".join(parts).strip()

    def generate(self, prompt: str, schema: Optional[Any] = None) -> Any:
        if schema is None:
            return self._call(prompt)
        # Structured output: pedir JSON conforme al schema Pydantic y validar (con 1 reintento).
        instr = (
            f"{prompt}\n\nResponde ÚNICAMENTE con un JSON válido (sin texto extra) que cumpla este schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        for _ in range(2):
            text = self._call(instr)
            # tolera ```json ...``` o JSON suelto
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```|(\{.*\})", text, re.DOTALL)
            json_str = (m.group(1) or m.group(2)) if m else text
            try:
                return schema.model_validate_json(json_str)
            except Exception:
                continue
        # último intento: dejar que propague si sigue inválido
        return schema.model_validate_json(self._call(instr))

    async def a_generate(self, prompt: str, schema: Optional[Any] = None) -> Any:
        # El eval es on-demand; envolver el síncrono es suficiente.
        return self.generate(prompt, schema=schema)
