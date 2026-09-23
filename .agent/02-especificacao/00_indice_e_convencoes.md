# 02 — Especificação Funcional do Sistema CPA

> **Para o agente de IA:** esta pasta é a **fonte da verdade funcional**. A pasta `01-init`
> define a *stack* e a infraestrutura; esta pasta define **o que o sistema faz**.
> Em caso de conflito, **esta pasta prevalece** e o conflito deve ser reportado ao
> usuário, não resolvido silenciosamente.

## Objetivo do produto

Plataforma que, a partir da **grade horária institucional** (`.xlsx` real do semestre),
gera e mantém **automaticamente** os **Google Forms** da CPA — atualizando a cada ciclo
as perguntas que dependem da grade —, produz o **QR Code** de cada formulário e recolhe
as respostas para os relatórios por **dimensão do SINAES**, tudo **100% anônimo**.

> **O respondente responde no Google Forms**, não em tela nossa. O sistema é o
> orquestrador: grade → perguntas → formulário → QR → respostas → ISG.
> Ver `10_integracao_google_forms.md`.

## A arquitetura em um quadro

O ciclo 2025.2 foi feito à mão em **17 Google Forms** (ver `historico/`). Esta é a mesma
estrutura, gerada automaticamente da grade. Com o período **2026.2**:

| Instrumento | Segmento | Chave | Qtd. | Tamanho |
|---|---|---|---|---|
| **Turma** | `DISCENTE` | Curso + Turno + Período | **17** | 48 + 10 × nº de matérias |
| **Docente** | `DOCENTE` | Período letivo | **1** | 60 perguntas |
| **Técnico-administrativo** | `TECNICO_ADMINISTRATIVO` | Período letivo | **1** | 42 perguntas |
| **Comunidade externa** | `COMUNIDADE` | Período letivo | **1** | 3 perguntas ⚠️ |
| | | | **20** | |

O formulário da turma tem **dois blocos**, e é essa divisão que resolve tudo:

```
┌─ CPA 2026.2 · Biomedicina · Noturno · 4º período ────────────────┐
│                                                                  │
│  BLOCO INSTITUCIONAL — 48 perguntas, respondidas UMA vez         │
│    Q1–Q9, Q20–Q58 · dimensões 1,2,3,4,6,7,8,9                    │
│                                                                  │
│  BLOCO POR MATÉRIA — 10 perguntas × cada `Disciplina | Professor`│
│    ── Toxicologia · Prof. Washington ──────── Q10–Q19            │
│    ── Bioética e Deontologia · Prof. Clayson ─ Q10–Q19            │
│    ── … (10 ofertas nesta turma)                                 │
│                                                                  │
│  Total: 48 + 10 × 10 = 148 perguntas                             │
└──────────────────────────────────────────────────────────────────┘
```

> **A chave da avaliação é `Disciplina | Professor`** — sem a turma. Em 2025.2 isso
> aparecia no título da pergunta como sufixo digitado à mão:
> `O docente domina o conteúdo e está atualizado? (Bioquímica- Prática - Victória)`.
> Se a mesma disciplina tem professores diferentes, são blocos independentes.
> Em 2026.2: **105 ofertas**, **136 vínculos oferta↔turma** (27 ofertas atendem mais
> de uma turma), **8,0 ofertas por turma** em média, em **164 alocações** na grade.

⚠️ **Tamanho é o risco central deste desenho** — de 88 a 168 perguntas por formulário.
Ver `04_banco_de_perguntas.md` §6.

## Ordem de leitura

| # | Arquivo | Conteúdo | Quem consome |
|---|---|---|---|
| 00 | `00_indice_e_convencoes.md` | Este arquivo. Glossário e convenções | Todos |
| 01 | `01_regras_de_negocio.md` | Regras `RN-xx`, segmentos, fluxo ponta a ponta | Todos |
| 02 | `02_modelo_de_dominio.md` | Entidades, ER, DDL, constraints | Backend |
| 03 | `03_importacao_da_grade_xlsx.md` | Parser da planilha e conciliação | Backend |
| 04 | `04_banco_de_perguntas.md` | Dimensões SINAES, escopos, montagem | Backend + Frontend |
| 05 | `05_motor_de_formularios_e_qrcode.md` | Geração dos 125 instrumentos, QR | Backend |
| 06 | `06_contratos_da_api.md` | Endpoints, payloads, erros | Backend + Frontend |
| 07 | `07_frontend_telas_e_fluxos.md` | Telas do admin e dos 4 segmentos | Frontend |
| 08 | `08_anonimato_seguranca_e_relatorios.md` | Anonimato, antifraude, relatório por dimensão | Backend + Frontend |
| 09 | `09_roadmap_e_criterios_de_aceite.md` | Fases e critérios de aceite testáveis | Todos |
| 10 | `10_integracao_google_forms.md` | ⭐ **Sincronização com Google Forms, anonimato e ingestão** | Backend |
| A | `anexos/A_catalogo_grade_20262.md` | Catálogo real extraído da grade | Backend (testes) |
| B | `anexos/B_banco_perguntas_cpa.md` | **As 163 perguntas oficiais da CPA** + fórmula do ISG | Backend (seed) |
| C | `anexos/grade_20262_esperado.json` | *Golden fixture* do importador | Backend (testes) |

## Glossário (use exatamente estes termos no código)

| Termo | Definição | Nunca confundir com |
|---|---|---|
| **Segmento** | Público respondente exigido pelo SINAES: `DISCENTE`, `DOCENTE`, `TECNICO_ADMINISTRATIVO`, `COMUNIDADE` | Curso |
| **Dimensão** | Uma das **10 dimensões** do SINAES (Lei 10.861/2004), agrupadas em **5 eixos**. Toda pergunta pertence a uma. Confirmadas idênticas às do Power BI da CPA (Anexo B) | Escopo |
| **ISG** | Índice de Satisfação Geral: **`(média − 1) / 4`**, exibido como %. Métrica oficial da CPA, confirmada contra o painel 2025.2 | Média 1–5 |
| **`codigo`** | Identidade permanente de uma pergunta (1–163 em 2025.2, novas a partir de 164). **Nunca renumerado nem reutilizado** | `pergunta.id`, `ordem_exibicao` |
| **`equivalencia_id`** | Grupo que reúne a mesma pergunta nos vários segmentos (67 grupos) | `dimensao_id` |
| **Instrumento** | Um dos 5 tipos de formulário da tabela acima | Formulário (a instância) |
| **Curso** | Graduação: **apenas** `BIOMEDICINA`, `ENFERMAGEM`, `EDUCACAO_FISICA`, `GTI`. **`CICLO_BASICO` não é curso** — é grade compartilhada (RN-03) | Disciplina |
| **Turno** | `MATUTINO` \| `NOTURNO` | — |
| **Período Letivo** | Semestre: `2026.2` (arquivo `20262`) | Período do curso |
| **Turma** | ⭐ `Curso + Turno + Período`. Ex.: *Biomedicina · Noturno · 4º período*. **17 no período.** Módulo, `Turma A/B` e sub-turmas de laboratório **não** entram na chave — são várias colunas da planilha para a mesma turma | Coluna da planilha |
| **Disciplina** | Matéria ministrada: `Bioquímica` | Módulo |
| **Professor** | Docente. Na planilha, **só o primeiro nome** | — |
| **Oferta** | **A unidade avaliada:** o par `(Disciplina, Professor)` em um Período Letivo. **106 no período.** Atende 0..N turmas. Gera um **bloco** dentro do formulário da turma, não um formulário próprio | Alocação, Turma |
| **Alocação** | Uma célula da planilha: aula em um dia/horário, com modalidade | Oferta |
| **Modalidade** | `PRELECAO` \| `PRATICA` \| `PRATICA_HOSPITALAR` \| `EAD` \| `EXTENSAO` \| `ESTAGIO` | Tipo de pergunta |
| **Formulário** | Instância gerada, espelhada em um **Google Form** (`google_form_id`), com QR sobre o `responderUri` | Instrumento (o tipo) |
| **Submissão** | Um envio anônimo completo | Resposta (item individual) |

## Convenções obrigatórias de código

1. **Idioma:** entidades, campos, tabelas e rotas em **português sem acento**
   (`professor`, `oferta`, `periodo_letivo`, `dimensao`). Comentários e mensagens ao
   usuário em português com acento. Não misture inglês no domínio.
2. **IDs:** PK `int` autoincremento, **exceto** `formulario.uuid` (UUID v4), a chave
   pública exposta no QR. **Nunca** exponha `id` interno em URL pública.
3. **Timestamps:** `criado_em` e `atualizado_em` (`timestamptz`) em todas as tabelas,
   **exceto** as de resposta — ver RN-30 (anonimato).
4. **Soft delete:** cadastros usam `ativo boolean default true`. Nunca `DELETE` físico em
   algo referenciado por formulário publicado.
5. **Migrations:** Alembic sempre. Nada de `create_all()` em produção.
6. **Configuração:** só por variável de ambiente, lida por um único `core/config.py`
   com Pydantic `BaseSettings`.
7. **Idempotência:** importação da grade e geração de formulários rodam duas vezes sem
   duplicar dados (RN-11, RN-21).

## Regras para o agente que for implementar

- **Não invente regra de negócio.** Pontos em aberto estão marcados `⚠️ DECISÃO PENDENTE`.
- **Não faça a importação 100% automática sem revisão humana** (RN-12) — o anexo A mostra
  por quê: a planilha real tem typos, rótulos duplicados e bilhetes administrativos.
- **Escreva o teste do importador contra** `anexos/grade_20262_esperado.json`.
- **Semeie o banco de perguntas a partir do Anexo B** (163 perguntas reais da CPA).
  Reescrever enunciado quebra a comparação com o ciclo 2025.2.
- **Nunca inclua a turma na chave da oferta** — multiplicaria as 105 ofertas para 136.
- **Nunca edite um Google Forms que já tem respostas** — desloca colunas e corrompe a
  série (doc 10 §6.4).
- **Afirme e releia `emailCollectionType = DO_NOT_COLLECT` a cada sincronização** — é
  onde o anonimato passa a morar (doc 10 §5).
- **O ISG é `(média − 1) / 4`** — não invente outra normalização (Anexo B §B.4).
- ⭐ **Nunca case pergunta por texto, em etapa alguma.** Use `codigo` (entre ciclos) e
  `equivalencia_id` (entre segmentos). Foi o cruzamento por texto que contaminou o
  histórico de 2025.2 (Anexo B §B.5).
- **Nunca inclua módulo ou rótulo `Turma A/B` na chave da turma** — inflaria 17 turmas
  para 21 e criaria formulários institucionais duplicados para os mesmos alunos.
- Mantenha as dependências mínimas (restrição herdada de `01-init`).
