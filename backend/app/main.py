"""Sistema CPA — API.

Especificação: .agent/02-especificacao/
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import publico
from app.api.admin import (
    cadastros, formularios, importacoes, integracao, perguntas, relatorios,
)
from app.core.config import obter_settings
from app.core.errors import registrar_handlers

settings = obter_settings()

app = FastAPI(
    title="Sistema CPA",
    description=(
        "Avaliação institucional da CPA: importa a grade, gera e sincroniza os "
        "Google Forms, recolhe as respostas e publica os relatórios por dimensão "
        "do SINAES."
    ),
    version=settings.versao,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origens_cors,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=False,  # não há cookie de sessão
)

registrar_handlers(app)
app.include_router(publico.router, prefix="/api")
app.include_router(cadastros.router, prefix="/api/admin")
app.include_router(perguntas.router, prefix="/api/admin")
app.include_router(formularios.router, prefix="/api/admin")
app.include_router(importacoes.router, prefix="/api/admin")
app.include_router(integracao.router, prefix="/api/admin")
app.include_router(relatorios.router, prefix="/api/admin")
