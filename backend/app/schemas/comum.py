"""Schemas compartilhados."""

from pydantic import BaseModel, ConfigDict


class Saida(BaseModel):
    """Base de todo payload de saída — lê direto dos models."""

    model_config = ConfigDict(from_attributes=True)


class Pagina(BaseModel):
    total: int
    itens: list
