"""Formato de erro único em toda a API (doc 06 §4)."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


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

    @app.exception_handler(IntegrityError)
    async def _integridade(_: Request, exc: IntegrityError) -> JSONResponse:
        """Constraint do banco barrou a operação.

        São as regras que vivem no schema (doc 02): chave da turma, chave da
        oferta, coerência de bloco, código único. Devolver 500 esconderia do
        cliente que foi ELE quem violou uma regra.
        """
        detalhe = str(getattr(exc, "orig", exc))
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "erro": "CONFLITO_INTEGRIDADE",
                "mensagem": (
                    "A operação viola uma regra do banco de dados. "
                    "Verifique chaves duplicadas e coerência dos campos."
                ),
                "detalhes": {"banco": detalhe[:400]},
            },
        )

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
