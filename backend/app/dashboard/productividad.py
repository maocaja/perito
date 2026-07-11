"""app/dashboard/productividad.py — métricas de productividad del operador (W14).

Honesto (P7): lo que MEDIMOS va real (casos procesados, pendientes — del repo); lo que aún NO medimos
(tiempo promedio, SLA, errores, la serie del gráfico) va **mock rotulado** (`demo`). Cuando exista telemetría
de tiempos/devoluciones, se reemplaza sin tocar la vista (DIP). Passive (P1): informativo, no decide.
"""

from app.contracts.enums import EstadoCaso
from app.dashboard.store import get_caso_repository

# Serie del gráfico (mock): casos por franja horaria 8am–6pm. La telemetría real la reemplazará.
_SERIE_DEMO = [2, 5, 9, 14, 19, 26, 31, 38, 43, 46, 48]
_TIEMPO_PROM_DEMO = "4m 12s"
_ERRORES_DEMO = 0
_SLA_DEMO = 100


def productividad(rol: str = "ANALISTA") -> dict:
    """Métricas del día del operador. `casos`/`pendientes` son REALES (del repo); `tiempo_prom`/`errores`/
    `sla`/`serie` son mock rotulado (`demo=True`) hasta tener telemetría. {casos, pendientes, tiempo_prom,
    errores, sla, serie, serie_max, demo}."""
    casos = get_caso_repository().list()
    resueltos = sum(1 for c in casos if c.estado in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO))
    pendientes = sum(1 for c in casos if c.estado in (EstadoCaso.REQUIERE_REVISION, EstadoCaso.LISTO_PARA_APROBAR))
    return {
        "casos": resueltos,            # REAL: casos ya resueltos por el humano
        "pendientes": pendientes,      # REAL: en cola de trabajo
        "tiempo_prom": _TIEMPO_PROM_DEMO,  # demo
        "errores": _ERRORES_DEMO,          # demo
        "sla": _SLA_DEMO,                  # demo
        "serie": _SERIE_DEMO,              # demo
        "serie_max": max(_SERIE_DEMO),
        "demo": True,                  # rotula las métricas que aún no medimos
    }
