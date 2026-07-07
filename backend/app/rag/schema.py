"""Esquema RAG con pgvector (PATTERN-U1-03, M10).

Estructura de índice vectorial parametrizado (dimensión configurable).
En U1: solo definición. El embedding real se conecta en U2/U3.
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, MetaData, Table, create_engine
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid


# Nota: en producción, usar un ORM real (SQLAlchemy + alembic).
# Aquí es solo la definición del esquema (contrato de infra).


class RAGSchema:
    """Definición del índice RAG con pgvector.

    Invariante PATTERN-U1-03: la dimensión del vector es parametrizada
    desde settings.EMBEDDING_DIM, no hardcodeada. Permite cambiar embedding
    en U2/U3 sin reindexar.
    """

    @staticmethod
    def build_metadata(embedding_dim: int | None = None) -> MetaData:
        """Construye el schema de metadata de SQLAlchemy.

        Args:
            embedding_dim: dimensión del vector (None en U1 = "no configurada aún")

        Returns:
            MetaData con tabla 'rag_documents' lista

        Nota: Si embedding_dim es None, la tabla se crea SIN la columna embedding
        (será añadida en U2 tras confirmar el modelo). SQLAlchemy 2.0+ compatible.
        """
        metadata = MetaData()

        # Construir lista de columnas dinámicamente (SQLAlchemy 2.0+ compatible)
        columns = [
            Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column("content", Text, nullable=False),
            Column("source", String(255), nullable=False),  # ej: "CLAUSULA_VIGENCIA_POL_123"
            Column("tipo", String(50), nullable=False),  # CLAUSULA, EXCLUSION, LIMITE, etc
            Column("created_at", DateTime, default=datetime.utcnow),
            Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
        ]

        # Agregar columna de embedding si la dimensión está configurada
        if embedding_dim is not None:
            columns.append(
                Column("embedding", Vector(embedding_dim), nullable=True, comment="pgvector: embeddings")
            )

        # Crear tabla de una sola vez (no usar append_column, deprecated en 2.0+)
        rag_documents = Table("rag_documents", metadata, *columns)
        return metadata


# Funciones de ayuda (mínimas en U1, completas en U2/U3)


def get_rag_connection_string(database_url: str) -> str:
    """Retorna la URL de conexión para pgvector.

    Asegura que la extensión pgvector esté disponible en PostgreSQL.

    Args:
        database_url: URL de conexión (ej: postgresql://user:pwd@host:5432/db)

    Returns:
        URL validada

    Raises:
        ValueError si no es PostgreSQL
    """
    if not database_url.startswith("postgresql"):
        raise ValueError("RAG solo soporta PostgreSQL con extensión pgvector")
    return database_url


def init_rag_schema(database_url: str, embedding_dim: int | None = None):
    """Inicializa el schema RAG en la base de datos (local dev en U1).

    Args:
        database_url: URL de conexión
        embedding_dim: dimensión del vector (None = structure-only en U1)

    Nota: En producción, usar Alembic para migrations.
    """
    engine = create_engine(database_url)
    metadata = RAGSchema.build_metadata(embedding_dim=embedding_dim)

    # Crear tablas (idempotente con if_not_exists=True)
    metadata.create_all(engine, checkfirst=True)

    # En U1: sin datos reales. Estructura lista para U2.
    print(f"✅ RAG schema initialized (embedding_dim={embedding_dim})")
