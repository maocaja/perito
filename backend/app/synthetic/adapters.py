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

        Args:
            row: diccionario con campos esperados de Kaggle

        Returns:
            FilaEntrada normalizada

        Raises:
            KeyError si faltan campos obligatorios
        """
        # Estructura esperada de Kaggle (ajustar según dataset real)
        return FilaEntrada(
            datos_siniestro=row.get("claim_data", {}),
            etiqueta_fraude=bool(row.get("is_fraud", False)),
            metadatos=row.get("metadata", {}),
        )
