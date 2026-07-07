"""Adaptador de entrada del generador (RULE-GEN-03, Plan B riesgo #1).

Puerto abstracto: FilaEntrada permite cambiar el backbone de datos sin tocar el generador.
Kaggle es un adaptador concreto; Plan B permite cambiarlo sin rediseño.
"""

from app.contracts.dataset import FilaEntrada


class KaggleAdapter:
    """Adaptador del esquema Kaggle al contrato FilaEntrada.

    Uso: desacoplar generador del esquema Kaggle.
    Si el esquema cambia, solo adapta aquí, no en generator.py.

    En U1: interface solo. La ingesta real vive en synthetic/generator.py
    cuando se conecte a CSV/API de Kaggle.
    """

    @staticmethod
    def from_kaggle_row(row: dict) -> FilaEntrada:
        """Convierte una fila Kaggle al contrato FilaEntrada.

        Validación fail-closed: campos obligatorios deben existir.
        Si faltan, lanza KeyError (no silencia con .get()).

        Args:
            row: diccionario con campos esperados de Kaggle

        Returns:
            FilaEntrada normalizada

        Raises:
            KeyError si faltan campos obligatorios (claim_data, is_fraud)
        """
        # Validar que existan los campos obligatorios
        required_fields = {"claim_data", "is_fraud"}
        missing = required_fields - set(row.keys())
        if missing:
            raise KeyError(
                f"Kaggle row missing required fields: {missing}. "
                f"Got keys: {set(row.keys())}"
            )

        # Campos validados, extraer con confianza
        return FilaEntrada(
            datos_siniestro=row["claim_data"],
            etiqueta_fraude=bool(row["is_fraud"]),
            metadatos=row.get("metadata", {}),  # metadata es opcional
        )
