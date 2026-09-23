# Instruções de Código para Agente IA: Docker Compose

## Objetivo
Criar um arquivo `docker-compose.yml` que orquestre o frontend e o backend localmente para facilitar o desenvolvimento e testes antes do deploy.

## Estrutura do docker-compose.yml
- **Serviço `backend`:**
  - Build apontando para o diretório `./backend`.
  - Mapear porta 8000 para 8000.
  - Injetar variável `DATABASE_URL` conectando ao Supabase (fornecida no `.env` local) ou subir um container Postgres temporário para testes offline.
  - Injetar `FRONTEND_URL=http://localhost:3000`.

- **Serviço `frontend`:**
  - Build apontando para o diretório `./frontend`.
  - Mapear porta 3000 para 80.
  - Injetar variável `VITE_API_BASE_URL=http://localhost:8000`.
  - Depender do serviço `backend`.

## Instruções adicionais
- Forneça também um arquivo `.env.example` mostrando as chaves que o desenvolvedor precisa preencher (como a string de conexão do Supabase).