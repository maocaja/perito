"""Fixtures compartidos de la suite.

Autouse: limpia los cachés del Summary Agent (W19) antes de cada test. Los cachés son módulo-scope
(viven con el proceso, como los stores), así que sin reset un test podría heredar el resumen cacheado
de otro. Con el reset, cada test arranca limpio → comportamiento idéntico al de antes del caché.
"""

import pytest

from app.llm import summary


@pytest.fixture(autouse=True)
def _reset_summary_caches():
    summary._reset_caches()
    yield
    summary._reset_caches()
