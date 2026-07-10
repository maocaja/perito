"""app/dashboard/branding.py — identidad visual de la Workbench (W16). Fuente ÚNICA de marca/nav.

Clean Code/SOLID: toda la config de marca vive aquí (SRP); las plantillas dependen de esta abstracción
(DIP), no de literales dispersos. `registrar(templates)` la inyecta como globals de Jinja (DRY: una sola
verdad para las dos instancias de templates, dashboard e intake).

`WORKBENCH_BRAND` permite override por entorno; "MAPFRE" es el contexto de la demo (rotulado), no un dato de
caso (P7).
"""

from app.config import settings

# Marca (override por entorno con WORKBENCH_BRAND si algún día se multi-tenant-iza).
_MARCA = getattr(settings, "workbench_brand", None) or "claims_copilot"

BRANDING = {
    "producto": "Claims Copilot",
    "sufijo": "AI",
    "vendor": "MAPFRE",          # contexto de demo (P7)
    "subtitulo": "Operaciones de siniestros",
    "marca": _MARCA,
}

# Navegación lateral: cada ítem apunta a una ruta REAL existente; los que no tienen destino → habilitado=False
# (placeholder honesto, no un link falso). Ver W16 §7.
# Acoplamiento declarado: los valores de `carril=` deben existir en `vista_caso.CARRILES` (amarillo/ambar) y
# los de `estado=` en `EstadoCaso`/pseudo-filtros de `_filtrar_bandeja` (EN_PROCESO/RESUELTOS). Si cambian allá,
# actualizar aquí (un carril inválido filtra a vacío, no rompe).
# Todo lo operacional se queda DENTRO del workbench (no salta a la bandeja vieja): filtra por estado/carril.
SIDEBAR: list[dict] = [
    {"label": "Inbox",      "icono": "inbox",    "ruta": "/workbench",                          "habilitado": True},
    {"label": "En Proceso", "icono": "proceso",  "ruta": "/workbench?estado=EN_PROCESO",         "habilitado": True},
    {"label": "Pendientes", "icono": "pendiente","ruta": "/workbench?carril=amarillo",           "habilitado": True},
    {"label": "Radicados",  "icono": "radicado", "ruta": "/workbench?estado=RESUELTOS",          "habilitado": True},
    {"label": "Escalados",  "icono": "escalado", "ruta": "/workbench?estado=REQUIERE_REVISION",  "habilitado": True},
    {"label": "Historial",  "icono": "historial","ruta": "/panel",                              "habilitado": True},
    {"label": "Reportes",   "icono": "reportes", "ruta": "/panel",                              "habilitado": True},
    {"label": "Ayuda",      "icono": "ayuda",    "ruta": "#",                                   "habilitado": False},
]

# Íconos de línea (path SVG único por ícono). Estilo minimal, coherente con el mockup.
ICONOS = {
    "inbox":    "M22 12h-6l-2 3h-4l-2-3H2 M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z",
    "proceso":  "M22 12h-4l-3 9L9 3l-3 9H2",
    "pendiente":"M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M12 6v6l4 2",
    "radicado": "M22 11.08V12a10 10 0 1 1-5.93-9.14 M22 4 12 14.01l-3-3",
    "escalado": "m10.29 3.86-8.18 14A2 2 0 0 0 3.87 21h16.26a2 2 0 0 0 1.76-3l-8.18-14a2 2 0 0 0-3.42 0z M12 9v4 M12 17h.01",
    "historial":"M3 3v5h5 M3.05 13A9 9 0 1 0 6 5.3L3 8 M12 7v5l4 2",
    "reportes": "M12 20V10 M18 20V4 M6 20v-4",
    "ayuda":    "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3 M12 17h.01",
    "panel":    "M22 12 18 12 15 21 9 3 6 12 2 12",  # nav "Panel de trazas" heredado
    "workbench":"M3 3h7v18H3z M12 3h9v9h-9z M12 14h9v7h-9z",
}


def es_activo(item: dict, path: str, query_params) -> bool:
    """¿El ítem de nav es el activo? Considera el FILTRO (carril/estado), no solo el path — así no se marcan
    todos los ítems de /workbench a la vez. SRP, testeable."""
    ruta = item["ruta"]
    if ruta == "#":
        return False
    base = ruta.split("?")[0]
    if not path.startswith(base):
        return False
    if "?" not in ruta:  # ítem sin filtro (Inbox /workbench, /panel): activo si no hay filtro de cola activo
        return not query_params.get("carril") and not query_params.get("estado")
    clave, _, valor = ruta.split("?", 1)[1].partition("=")  # p.ej. estado=EN_PROCESO
    return query_params.get(clave) == valor


def registrar(templates) -> None:
    """Inyecta la marca como globals de Jinja (DIP): las plantillas la consumen sin literales dispersos."""
    templates.env.globals["branding"] = BRANDING
    templates.env.globals["sidebar"] = SIDEBAR
    templates.env.globals["nav_icons"] = ICONOS
    templates.env.globals["nav_activo"] = es_activo
