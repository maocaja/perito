"""Factory LLM: Anthropic client configurado desde settings.

En U1: solo definición. Los agentes (U2-U5) usan esta factory.
"""

import anthropic
from app.config import get_settings


def get_anthropic_client() -> anthropic.Anthropic:
    """Retorna cliente Anthropic configurado.

    Lee ANTHROPIC_API_KEY desde settings (fail-closed si no existe).
    Versión de API viene de settings.anthropic_api_version.

    Returns:
        anthropic.Anthropic instance

    Raises:
        KeyError si ANTHROPIC_API_KEY no está en env
    """
    settings = get_settings()
    return anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=30.0,
    )
