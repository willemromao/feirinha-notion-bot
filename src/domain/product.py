"""Tipos estruturados para produtos validados."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ValidatedProduct:
    """Representa um produto já validado e normalizado."""

    data: str
    produto: str
    tipo: str
    qnt: float
    valor: float
    desconto: float
    categoria: str
    forma_de_pagamento: str
    emoji: Optional[str] = None
