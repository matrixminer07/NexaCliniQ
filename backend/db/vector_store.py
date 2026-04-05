from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class MoleculeEmbedding(Base):
    __tablename__ = "molecule_embeddings"

    id = Column(Integer, primary_key=True)
    smiles = Column(String, unique=True, index=True, nullable=False)
    embedding = Column(Vector(512), nullable=False)

    @classmethod
    def find_similar(cls, session, query_embedding, limit: int = 10):
        return session.query(cls).order_by(cls.embedding.cosine_distance(query_embedding)).limit(limit).all()
