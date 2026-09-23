# 01 — Regras de Negócio

## Personas e segmentos

O SINAES exige que a autoavaliação ouça **todos os segmentos** da comunidade acadêmica.
Cada segmento tem seu próprio instrumento e sua própria forma de acesso.

| Segmento | Quem é | Acesso | Instrumentos |
|---|---|---|---|
| `DISCENTE` | Alunos de graduação | QR Code em sala, sem login | **17** — um por turma |
| `DOCENTE` | Professores | Link/QR distribuído pela CPA | **1** |
| `TECNICO_ADMINISTRATIVO` | Corpo técnico-administrativo | Link/QR distribuído pela CPA | **1** |
| `COMUNIDADE` | Egressos, empregadores, comunidade externa | Link público no site da instituição | **1** |

| Persona operacional | Acesso | O que faz |
|---|---|---|
| **Administrador CPA** | Login simples via env (`ADMIN_USER`/`ADMIN_PASSWORD`) | Importa a grade, mantém o banco de perguntas, gera e imprime QR Codes, lê relatórios |
| **Respondente** | **Nenhum.** Sem cadastro, sem login, sem identificação | Escaneia e responde |

## Fluxo ponta a ponta

```
[1] Admin faz upload de "horario 20262.xlsx"
        ↓
[2] Parse → tabelas de STAGING (nada gravado no domínio ainda)
        ↓
[3] CONCILIAÇÃO: admin confirma professores, disciplinas e a consolidação das turmas
        ↓   (21 colunas da planilha → 17 turmas; "Washignton" = "Washington")
[4] COMMIT → cria Curso, Turma, Disciplina, Professor, Oferta, Alocação
        ↓   → 17 turmas · 105 ofertas · 164 alocações (chave Disciplina | Professor)
[5] Admin revisa o BANCO DE PERGUNTAS, com cada pergunta marcada por DIMENSÃO SINAES
        ↓
[6] Admin clica "Gerar instrumentos do período 2026.2"
        ↓   → 17 + 1 + 1 + 1 = 20 formulários, cada um com UUID + QR
[7] Snapshot das perguntas congelado por formulário (RN-22)
        ↓
[8] Admin baixa os PDFs: folhas por matéria, folhas por turma, cartazes dos 3 segmentos
        ↓
[9] Respondentes escaneiam → respondem anonimamente
        ↓
[10] Relatórios POR DIMENSÃO e POR SEGMENTO, respeitando o limiar de exibição (RN-33)
```

---

## A. Cadastro da grade (regra 1 do usuário)

> *"O usuário deve gravar a grade para identificação de Professores × Matérias,
> tal como o arquivo em anexo 20262."*

- **RN-01** A grade é cadastrada por **importação de `.xlsx`** no layout institucional.
  O cadastro manual é complemento (correções pontuais), nunca o caminho principal.
- **RN-02** Um arquivo pertence a **um Período Letivo**. O sistema sugere o código a
  partir do nome (`20262` → `2026.2`) e o admin confirma.
- **RN-03** ⭐ **`CICLO_BASICO` não é um curso.** Abas de ciclo básico são uma *grade
  compartilhada*: a mesma aula atende alunos de cursos diferentes. A coluna deve ser
  **expandida** nos cursos reais que a instrução de matrícula declara.
  Exemplo real: `"Matricular: Biomedicina (1 e 2 período) - Enfermagem (1 período)"` com
  `2º PER- Módulo P` gera **duas** turmas — `Biomedicina · Matutino · 2º` e
  `Enfermagem · Matutino · 2º` — e as ofertas daquela coluna vinculam-se às **duas**.
  Os cursos são apenas `BIOMEDICINA`, `ENFERMAGEM`, `EDUCACAO_FISICA`, `GTI`.
- **RN-04** ⭐ **A chave da Turma é `(Período Letivo, Curso, Turno, Período)`.**
  *Biomedicina · Noturno · 4º período* é **uma** turma.
  **Não entram na chave:** o módulo (`Módulo AB`), o rótulo (`Turma A`, `Turma B`,
  `Turma Única`) nem a sub-turma de laboratório (`Sub - Turma A/B`) — são recortes
  operacionais da mesma turma de alunos e viram várias colunas da planilha apontando
  para o mesmo registro.
  Consequências no arquivo real (21 colunas → **17 turmas**):
  1. Colunas mescladas no cabeçalho = uma turma;
  2. `Sub - Turma A` + `Sub - Turma B` (Enfermagem e Biomedicina matutino) = uma turma;
  3. `Turma A` + `Turma B` do ciclo básico = uma turma;
  4. Rótulo `Turma A` duplicado (Biomedicina Noturno) = uma turma;
  5. Colunas de **Estágio Supervisionado** **não são turma** — geram oferta sem turma,
     que nasce `avaliavel = false` (RN-15).
  O módulo é guardado como **atributo informativo** (`turma.modulo`), útil no título e na
  conferência, mas **nunca** como parte da identidade.
- **RN-05** Cada **célula preenchida** é uma **Alocação**. Mescla vertical = uma aula de
  N horários (uma alocação, `duracao_horarios = N`).
- **RN-06** ⭐ **A Oferta — a unidade avaliada — é o par `(Disciplina, Professor)` no
  período letivo. A turma NÃO faz parte da chave.**
  Todas as alocações da mesma dupla, em qualquer turma, colapsam em **uma** oferta.
- **RN-07** Uma Oferta **atende 0..N turmas** (`oferta_turma`, N:N). Em 2026.2,
  **27 das 105 ofertas atendem mais de uma turma**. Oferta com **zero** turmas (as 4 da
  coluna de estágio) não gera formulário — RN-30.
- **RN-08** Se a mesma disciplina tem **professores diferentes**, são **ofertas
  independentes** — mesmo na mesma turma. Caso real: `Bioquímica (Preleção) - Profa Andrea`
  e `Bioquímica (Prática) - Profa Vanessa` = duas ofertas, dois formulários, dois QRs.
- **RN-09** Chave de unicidade: `UNIQUE (periodo_letivo_id, disciplina_id, professor_id)`.
- **RN-10** A **modalidade** (`Preleção`, `Prática`, `EAD`…) é atributo da **Alocação**,
  não da Oferta. `Histologia (Preleção)` e `Histologia (Prática)` do mesmo professor são
  **uma** oferta.
- **RN-11** A planilha não é descartada: arquivo e texto bruto de cada célula ficam
  guardados (`importacao_grade`, `alocacao.texto_origem`).
- **RN-12** Importação **idempotente por período**: reimportar o mesmo arquivo não duplica;
  produz um *diff* (incluídos / alterados / removidos) que o admin aprova.
- **RN-13** **A importação nunca grava no domínio sem confirmação humana.** Linhas
  classificadas `REVISAR`/`ERRO` bloqueiam o commit.
- **RN-14** Professores aparecem só com o **primeiro nome**. O sistema mantém
  `nome_exibicao` (obrigatório) e `nome_completo` (opcional).
  **Homônimos são risco real** — a conciliação sempre pergunta antes de fundir e
  **nunca** funde automaticamente nomes de cursos diferentes.
  *(Verificado em 2026.2: nenhum professor leciona a mesma disciplina em dois cursos,
  então a chave global é segura neste arquivo — mas a regra vale para os próximos.)*
- **RN-15** Uma Oferta pode ser **não avaliável** (`avaliavel = false`) — TCC, Estágio
  Supervisionado, Optativa. Não gera formulário.
  No arquivo real são exatamente as **4 ofertas sem turma**: `Estágio Supervisionado I ou II`
  (Alexandre e Washington), `Optativa I ou II - Endocrinologia laboratorial` (Roberpaulo)
  e `TCC 1 ou TCC 2` (Clayson) — todas vindas da coluna de estágio, que não é turma (RN-04.5).
  **A regra "sem turma ⇒ não avaliável" e a lista de exceções coincidem: bom sinal de que
  o modelo está correto.**

---

## B. Banco de perguntas (regras 2 e 3 do usuário)

> *"Gravar quais são as perguntas padrões a todos os formulários."*
> *"Gravar quais perguntas são destinadas ao Professor referente àquela disciplina."*

- **RN-16** ⭐ Toda pergunta pertence a **uma Dimensão do SINAES** (`dimensao_id`,
  obrigatório). É isso que permite o relatório "por dimensão" que o MEC pede.
  As 10 dimensões e os 5 eixos estão em `04_banco_de_perguntas.md` §1.
- **RN-17** Toda pergunta pertence a **um instrumento** (`tipo_instrumento`) e a
  **um bloco** (`bloco`):
  | Instrumento | Blocos permitidos | Perguntas (Anexo B) |
  |---|---|---|
  | `DISCENTE_TURMA` | `INSTITUCIONAL` (48) + `DISCIPLINA`/`PROFESSOR` (10) | Q1–Q58 |
  | `DOCENTE` | `INSTITUCIONAL` | Q59–Q118 |
  | `TECNICO_ADMINISTRATIVO` | `INSTITUCIONAL` | Q119–Q160 |
  | `COMUNIDADE` | `INSTITUCIONAL` | Q161–Q163 |
- **RN-18** **Perguntas padrão de todo formulário** *(regra 2 do usuário)*: as 48 de
  `bloco = INSTITUCIONAL` no instrumento discente (Q1–Q9, Q20–Q58). Aparecem **uma vez**
  em cada um dos 17 formulários de turma.
- **RN-19** **Perguntas do professor daquela disciplina** *(regra 3 do usuário)*: as 10
  de `bloco IN (DISCIPLINA, PROFESSOR)` (Q10–Q19), **repetidas para cada oferta** da
  turma. Cada repetição carrega `oferta_id` e o rótulo `Disciplina · Prof. Nome`, que em
  2024 era digitado à mão no título da pergunta.
- **RN-20** `aplicacao`: `TODAS` (o caso comum) ou `ESPECIFICA` (só para alvos vinculados
  em `pergunta_vinculo`: disciplina, professor ou curso).
- **RN-21** Tipos: `LIKERT_5` (padrão), `SIM_NAO`, `TEXTO_LIVRE`, `MULTIPLA_ESCOLHA_UNICA`.
  Perguntas `TEXTO_LIVRE` nascem **opcionais**, para não travar o envio.

---

## C. Geração automática dos instrumentos

- **RN-22** ⭐ **Um formulário por turma** (`DISCENTE_TURMA`), com **dois blocos**:
  1. **INSTITUCIONAL** — as 48 perguntas Q1–Q9 e Q20–Q58, respondidas **uma vez**;
  2. **POR MATÉRIA** — as 10 perguntas Q10–Q19 repetidas para **cada oferta**
     (`Disciplina | Professor`) que a turma cursa.

  Em 2026.2: **17 formulários**, de 88 a 168 perguntas (média 129).
  É a mesma estrutura do ciclo 2024 (Anexo B §B.3), que era montada à mão em Google Forms.
- **RN-23** ⭐ A ordem dos blocos de matéria é **determinística**, por
  `slug(disciplina), slug(professor)` — o mesmo aluno, reabrindo o formulário, vê a mesma
  sequência, e o rascunho local continua válido.
  A chave da turma (RN-04) garante que os mesmos alunos recebam **um só** formulário:
  se o módulo ou o rótulo `Turma A/B` entrassem na chave, receberiam dois.
- **RN-24** **Um formulário por segmento não-discente** por período: `DOCENTE`,
  `TECNICO_ADMINISTRATIVO`, `COMUNIDADE`. Não são vinculados a turma nem a oferta.
- **RN-25** Geração em **lote**, um clique por período letivo, **idempotente**: reexecutar
  não recria formulários existentes, apenas cria os que faltam.
- **RN-26** No instante da geração o sistema **congela um snapshot** das perguntas
  (`formulario_pergunta`). Alterar o banco depois **não** altera formulários já gerados.
- **RN-27** Janela de aplicação (`abre_em`, `fecha_em`). Fora dela, o link mostra
  "avaliação encerrada" e **recusa** submissões. As janelas podem diferir por segmento —
  a da comunidade externa costuma ser mais longa.
- **RN-28** Status: `RASCUNHO` → `PUBLICADO` → `ENCERRADO`. Só `PUBLICADO` aceita resposta.
- **RN-29** O QR codifica o `responderUri` do Google Form, gerado no nosso backend.
  Artefatos de impressão: folha A4 por matéria, folha por turma, cartaz por segmento.
- **RN-30** Oferta sem turma vinculada ou não avaliável **não** gera formulário; o admin
  é avisado.

---

## D. Resposta e anonimato

- **RN-31** **Anonimato é inegociável, em todos os 4 segmentos.** Sem login, sem IP em
  claro, sem matrícula, sem e-mail. Na tabela de submissão grava-se **data** (sem hora),
  para impedir correlação com registros de acesso.
  ⚠️ Atenção especial ao segmento `TECNICO_ADMINISTRATIVO`: são poucas pessoas, e o
  risco de reidentificação é o maior de todos — ver RN-34.
- **RN-32** Submissão **atômica**: ou grava tudo, ou nada. Rascunho fica no `localStorage`.
- **RN-33** ⭐ A coleta acontece em **Google Forms** (doc 10). Não implementamos
  antifraude própria: sem login não há como impedir resposta duplicada, e exigir login
  quebraria o anonimato. **Limitação assumida — era assim em 2024.**
  Em contrapartida, a API do Google **não nos expõe IP nem *user agent***, então a
  garantia de anonimato fica mais forte do que no portal próprio.
- **RN-34** **Limiar de exibição (k-anonimato):** nenhum resultado — número ou comentário —
  é exibido enquanto o formulário tiver menos de `MIN_RESPOSTAS_EXIBICAO` submissões
  (padrão **5**). Abaixo disso: "amostra insuficiente".
  Para `TECNICO_ADMINISTRATIVO` e `COMUNIDADE`, o limiar é configurável à parte e
  **recomendado em 10**, porque o universo é pequeno.
- **RN-35** Comentários de texto livre só ficam visíveis **após o encerramento** e passam
  por moderação (ocultar ofensivo ou identificável), registrada sem vínculo com autor.
- **RN-36** ⭐ **Relatórios agregam por Dimensão SINAES e por Segmento**, além de por
  oferta/professor/curso. É a saída que alimenta o relatório oficial da CPA.

---

- **RN-37** ⭐ **ISG (Índice de Satisfação Geral) é a métrica oficial:**
  `ISG = (média das respostas − 1) / 4`, exibido como percentual. Confirmada contra o
  painel 2024 (Anexo B §B.4). Toda agregação — por questão, dimensão, eixo, oferta,
  professor, turma, curso e segmento — é publicada em ISG %.
- **RN-38** O banco de perguntas nasce do **Anexo B** (163 perguntas oficiais).
  Reescrever enunciado quebra a comparação com 2024; só a CPA autoriza.

---

## D-bis. Integração com Google Forms (doc 10)

- **RN-39** ⭐ Cada formulário do nosso BD é **espelhado em um Google Form**. Nosso lado é
  a fonte da verdade da **estrutura**; o Google é a fonte da verdade das **respostas**.
- **RN-40** A sincronização é **idempotente**: `hash_estrutura` igual ⇒ nenhuma request.
  Num ciclo típico apenas os blocos de matéria mudam; o institucional não é tocado.
- **RN-41** ⭐ **`emailCollectionType = DO_NOT_COLLECT` é afirmado e relido a cada
  sincronização.** Divergência **bloqueia a publicação**. É onde o anonimato passa a morar.
- **RN-42** ⭐ **Formulário com ≥ 1 resposta tem a estrutura congelada.** Editar um Google
  Forms com respostas desloca as colunas e corrompe a série. Mudança de grade após a
  primeira resposta exige decisão explícita do admin (doc 10 §6.4).
- **RN-43** A ingestão de respostas usa `google_response_id` como chave de idempotência e
  `google_question_id` para mapear cada resposta à `formulario_pergunta` — **nunca** por
  texto da pergunta, que é o defeito do pipeline de 2024 (Anexo B §B.5).
- **RN-44** Resposta cujo `questionId` não existe no snapshot é **registrada como órfã e
  alertada**, nunca descartada em silêncio: é o sintoma de que alguém editou o formulário
  à mão.

---

## E. Não-escopo (não implementar sem pedido explícito)

- Integração com o sistema acadêmico (importação é por planilha).
- Autenticação individual de respondente, SSO, e-mail institucional.
- Notificação por e-mail / push.
- Geração do relatório oficial da CPA no formato do e-MEC.
- Histórico comparativo entre semestres (só a partir do 2º período importado).

## ⚠️ Decisões pendentes

| # | Questão | Padrão assumido |
|---|---|---|
| D-1 | Estágio, TCC e Extensão entram na CPA? | Viram oferta, mas nascem `avaliavel = false` (RN-15) |
| D-2 | `Educação Física · Noturno · 3º período` (aba do ciclo básico integrado, `3º PER- Módulo M`) é a única turma de período ímpar e não se encaixa no padrão 2/4/6/8. É turma própria ou pertence a outra? | Mantida como turma própria → **17**. Se ela se funde a outra, o total vai a **16** |
| D-3 | As 10 dimensões do SINAES valem integralmente para os 4 segmentos, ou cada segmento responde só as dimensões aplicáveis? | Cada segmento responde as dimensões que a CPA marcar — o banco permite as duas |
| D-4 | Limiar de exibição para docente/técnico: 5 ou 10? | ⚠️ Em 2024 **docentes tiveram 16 respostas e técnicos 11**. Limiar 10 quase zera o relatório técnico. Proposto: **5** para todos, com aviso de amostra pequena |
| D-6 | Introduzir "Não sei responder"? | **Não** no primeiro ciclo — muda a base do ISG e quebra a comparação com 2024 |
| D-7 | O instrumento de COMUNIDADE tem só 3 perguntas e teve 0 respostas em 2024. Ampliar? | Manter as 3 e priorizar a **divulgação**; ampliar só com aval da CPA |
| D-5 | Como a comunidade externa chega ao formulário? | Link público no site + QR em cartaz |
