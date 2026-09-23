"""Formato de erro único em toda a API (doc 06 §4)."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErroCPA(Exception):
    """Erro de negócio com código estável — o frontend decide a tela por ele."""

    codigo = "ERRO"
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, mensagem: str, detalhes: dict | None = None):
        self.mensagem = mensagem
        self.detalhes = detalhes or {}
        super().__init__(mensagem)

    def corpo(self) -> dict:
        return {
            "erro": self.codigo,
            "mensagem": self.mensagem,
            "detalhes": self.detalhes,
        }


class NaoEncontrado(ErroCPA):
    codigo = "NAO_ENCONTRADO"
    http_status = status.HTTP_404_NOT_FOUND


class ConflitoEstado(ErroCPA):
    codigo = "CONFLITO_ESTADO"
    http_status = status.HTTP_409_CONFLICT


class ImportacaoPendente(ErroCPA):
    codigo = "IMPORTACAO_PENDENTE"
    http_status = status.HTTP_409_CONFLICT


class AnonimatoViolado(ErroCPA):
    """doc 10 §5 — bloqueia a publicação."""

    codigo = "ANONIMATO_VIOLADO"
    http_status = status.HTTP_409_CONFLICT


class EstruturaCongelada(ErroCPA):
    """doc 10 §6.4 — formulário com respostas não aceita mudança de estrutura."""

    codigo = "ESTRUTURA_CONGELADA"
    http_status = status.HTTP_409_CONFLICT


class RevisaoDesatualizada(ErroCPA):
    codigo = "REVISAO_DESATUALIZADA"
    http_status = status.HTTP_409_CONFLICT


class CotaExcedida(ErroCPA):
    codigo = "COTA_EXCEDIDA"
    http_status = status.HTTP_429_TOO_MANY_REQUESTS


class CredencialInvalida(ErroCPA):
    codigo = "CREDENCIAL_INVALIDA"
    http_status = status.HTTP_502_BAD_GATEWAY


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErroCPA)
    async def _erro_cpa(_: Request, exc: ErroCPA) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.corpo())

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "erro": "VALIDACAO",
                "mensagem": "Os dados enviados são inválidos.",
                "detalhes": {"campos": exc.errors()},
            },
        )
