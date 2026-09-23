# Instruções de Código para Agente IA: Frontend (ReactJS)

## Objetivo
Criar uma SPA (Single Page Application) em ReactJS para servir de Painel Administrativo e interface de resposta para os alunos. O app será hospedado na Vercel.

## Tecnologias Requeridas
- ReactJS (inicializado com Vite)
- React Router DOM (Roteamento)
- TailwindCSS (Estilização sem escrever CSS customizado)
- Axios (Requisições HTTP para o backend)
- Lucide React (Ícones)

## Estrutura de Rotas e Páginas
1. **Rotas Administrativas (`/admin/*`):**
   - `/admin/dashboard`: Visão geral e atalhos.
   - `/admin/cadastros`: Formulários simples para cadastrar professores, disciplinas e perguntas.
   - `/admin/gerar-cpa`: Interface onde o admin seleciona uma disciplina, clica em "Gerar Formulário". A tela deve exibir o Link gerado e consumir o endpoint `/api/qrcode/{uuid}` para exibir a imagem do QR Code na tela (permitindo impressão).

2. **Rotas Públicas (Alunos):**
   - `/responder/{uuid}`: A tela principal que o aluno acessa via QR Code.
     - Deve fazer um GET no backend para buscar as perguntas daquele UUID.
     - Renderizar dinamicamente os inputs (escala de 1 a 5 ou campo de texto).
     - Ao final, um botão "Enviar Avaliação Anônima".
   - `/sucesso`: Tela de agradecimento após o envio.

## Variáveis de Ambiente
- O frontend deve utilizar `VITE_API_BASE_URL` para se comunicar com o backend FastAPI.

## Requisitos do Docker (Para Dev Local)
- Embora o deploy final seja na Vercel (que não usa Docker), crie um `Dockerfile` multi-stage para desenvolvimento local integrado.
- Stage 1: Build com Node.
- Stage 2: Serve com Nginx (porta 80).