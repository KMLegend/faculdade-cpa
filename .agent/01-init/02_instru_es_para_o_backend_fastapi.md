# Instruções de Código para Agente IA: Backend (Python/FastAPI)

## Objetivo
Desenvolver uma API RESTful utilizando FastAPI para gerenciar os dados da CPA e fornecer endpoints para o frontend.

## Tecnologias Requeridas
- Python 3.11+
- FastAPI
- Uvicorn (Servidor ASGI)
- SQLAlchemy + asyncpg (ORM e driver assíncrono para PostgreSQL/Supabase)
- Pydantic (Validação de schemas)
- `qrcode` e `Pillow` (Para geração do QR code)

## Estrutura do Banco de Dados (PostgreSQL)
Crie os modelos SQLAlchemy para as seguintes entidades:
1. `Professor` (id, nome)
2. `Disciplina` (id, nome, professor_id)
3. `Pergunta` (id, texto, tipo [likert, texto], escopo [padrao, disciplina, professor], referencia_id [null, disciplina_id, professor_id])
4. `Formulario` (id [UUID v4], disciplina_id, ativo [bool])
5. `Resposta` (id, formulario_id, pergunta_id, valor_numerico, comentario_texto)

## Endpoints Necessários
Crie as rotas documentadas automaticamente pelo FastAPI (Swagger UI):
- **CRUD básico:** `/api/professores`, `/api/disciplinas`, `/api/perguntas`.
- **Geração de Formulário:** `POST /api/formularios/gerar/{disciplina_id}` -> Cria um registro de formulário com um UUID único e retorna este UUID.
- **Busca de Formulário (Para o Aluno):** `GET /api/formularios/{uuid}` -> Retorna a disciplina e a lista concatenada de perguntas (Padrão + Específicas da Disciplina + Específicas do Professor).
- **Submissão:** `POST /api/respostas/{formulario_uuid}` -> Recebe um array de respostas e salva no banco.
- **Gerador de QR Code:** `GET /api/qrcode/{formulario_uuid}` -> Usa a biblioteca `qrcode` do Python para gerar uma imagem PNG/SVG contendo a URL do frontend (`https://seu-dominio.vercel.app/responder/{formulario_uuid}`) e retorna como `StreamingResponse`.

## Requisitos do Docker
- Crie um `Dockerfile` leve baseado em `python:3.11-slim`.
- Exponha a porta 8000.
- Defina o entrypoint com Uvicorn.
- O banco de dados (`DATABASE_URL`) e a URL do frontend (`FRONTEND_URL`) devem ser lidos de variáveis de ambiente.