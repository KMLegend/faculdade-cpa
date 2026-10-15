"""Geração de QR Codes em PNG e SVG (doc 05 §3)."""

from __future__ import annotations

import io
import qrcode
from qrcode.image.svg import SvgPathImage


def gerar_qrcode(url: str, formato: str = "png", escala: int = 10) -> bytes:
    """Gera o QR Code da URL informada nos formatos PNG ou SVG.

    - escala: box_size (tamanho de cada módulo em pixels)
    - quiet zone: border=4
    - tolerância de erro: M (15%) para tolerar impressão comum
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=max(1, min(20, escala)),
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    buf = io.BytesIO()
    if formato.lower() == "svg":
        img = qr.make_image(image_factory=SvgPathImage)
        img.save(buf)
    else:
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(buf, format="PNG")

    return buf.getvalue()
