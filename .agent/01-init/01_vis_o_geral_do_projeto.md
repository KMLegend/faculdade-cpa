# Escopo do Projeto: Sistema de CPA Acadêmico

## Objetivo
Criar um sistema de Comissão Própria de Avaliação (CPA) para uma instituição de ensino. O sistema deve ser 100% gratuito em sua hospedagem e infraestrutura, modular, conteinerizado via Docker e focado em avaliações anônimas de disciplinas e professores.

## Stack Tecnológica Escolhida
- **Frontend:** ReactJS (criado via Vite), estilizado com TailwindCSS. Hospedagem e domínio via Vercel.
- **Backend:** Python com FastAPI. Hospedagem gratuita sugerida: Render.
- **Banco de Dados:** PostgreSQL hospedado no Supabase.
- **Geração de QR Code:** Feita no Backend (Python) usando a biblioteca `qrcode`.
- **Infraestrutura:** Docker e Docker Compose para ambiente de desenvolvimento local.

## Módulos do Sistema
1. **Painel Administrativo (CRUD):**
   - Gerenciamento de Grade (Cursos, Disciplinas, Turmas, Professores).
   - Gerenciamento de Perguntas (Padrão para todas, Específicas por Disciplina, Específicas por Professor).
2. **Motor de Formulários:**
   - Composição dinâmica de questionários baseados na vinculação da turma.
   - Geração de link único (UUID) e QR Code associado para os alunos acessarem.
3. **Portal do Aluno (Respostas):**
   - Acesso via QR Code ou Link.
   - Respostas 100% anônimas (sem necessidade de login).

## Regras de Negócio e Restrições para a IA
- TODO o código gerado deve prever que a aplicação rodará em contêineres Docker.
- NÃO deve haver autenticação complexa de usuários alunos (anonimato total). O painel admin pode ter uma autenticação simples estática via variáveis de ambiente por enquanto.
- Mantenha os pacotes o mais leves possível.