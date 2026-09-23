# 09 — Roadmap e Critérios de Aceite

Ordem pensada para que cada fase entregue algo **demonstrável**, e para que o risco maior
(o importador da planilha) seja atacado cedo — não na véspera.

---

## Fase 0 — Esqueleto (meio dia)
- `backend/` FastAPI + `frontend/` Vite + `docker-compose.yml` + `.env.example`
  conforme `01-init`.
- Postgres local no compose (perfil `offline`) **e** opção Supabase por `DATABASE_URL`.
- `GET /api/health` respondendo e frontend consumindo.
- Alembic configurado, migration inicial vazia.

**Aceite:** `docker compose up` sobe tudo; `localhost:3000` mostra a home; `localhost:8000/docs` abre.

---

## Fase 1 — Domínio e cadastros (1–2 dias)
- Migrations 1–4 do doc 02, **incluindo o seed de `eixo_sinaes`, `dimensao_sinaes`
  (10 dimensões / 5 eixos), os 67 grupos de equivalência e as 163 perguntas do Anexo B**
  com `codigo` e `equivalencia_id`.
- CRUD administrativo + Basic Auth.
- Telas `/admin/cadastros` e `/admin/perguntas` com o seed do doc 04 §5.

**Aceite:** cadastrar professor, disciplina, turma e oferta pela tela; vincular uma
oferta a 2 turmas; o banco tem 163 perguntas com `codigo` 1–163, sendo 48
`INSTITUCIONAL` e 10 `DISCIPLINA`/`PROFESSOR` no instrumento discente; os 67 grupos de
equivalência resolvem `codigo 1 ↔ 59 ↔ 119`; criar pergunta nova recebe `codigo` 164.

---

## Fase 2 — Importador da grade ⚠️ **maior risco** (2–3 dias)
- Parser completo do doc 03 (mesclagens, cabeçalho, gramática da célula).
- Staging + matching + tela de conciliação + commit transacional + aliases.
- **Testes contra `anexos/grade_20262_esperado.json`.**

**Aceite (obrigatório antes de seguir):**
1. `horario 20262.xlsx` → **17 turmas**, **105 ofertas**, **164 alocações**, 4 ofertas sem turma.
2. Nenhum curso `CICLO_BASICO` criado; a aba do ciclo básico gera turmas de
   Biomedicina **e** Enfermagem, vinculadas às mesmas ofertas.
3. *Biomedicina · Noturno · 4º período* é uma turma só, vinda de duas colunas `Turma A`.
4. As 17 células do corpus (doc 03 §3.3) interpretadas como na tabela.
5. Nada gravado no domínio antes do `aplicar`.
6. Reimportação do mesmo arquivo → diff vazio, zero duplicata.
7. Alias `Washignton → Washington` faz a próxima importação passar `OK`.

---

## Fase 3 — Motor de formulários e QR (2 dias)
- Montagem com snapshot (doc 04 §4), ciclo de vida, geração e publicação em lote.
- Os **4 instrumentos**; `GET /api/publico/qrcode/{uuid}` (PNG e SVG); os artefatos de
  impressão: folha A4 da turma, lista de conferência das matérias e cartaz por segmento.

**Aceite:** um clique gera **20 formulários** (17 + 3); *Biomedicina · Noturno · 6º
período* sai com **168 perguntas** (48 + 10×12) e dispara o alerta; o QR fotografado da
tela abre o formulário certo; editar uma pergunta não altera formulário publicado.

---

## Fase 4 — Integração com Google Forms ⚠️ **novo maior risco** (3–4 dias)

Substitui o antigo "portal do aluno". Ver `10_integracao_google_forms.md`.

- Autenticação (conta de serviço com delegação) e `integracao/status`.
- Sincronizador: `create` → `batchUpdate` único por formulário → `setPublishSettings`.
- Estrutura em `questionGroupItem` (grades) + `pageBreakItem` por dimensão e por matéria.
- Anonimato: afirmar **e reler** `emailCollectionType`.
- Tela de prévia com *diff* antes de sincronizar.
- Ingestão incremental de respostas por `google_question_id`.

**Aceite:**
1. Sincronizar 2026.2 cria **20 formulários** no Drive institucional.
2. Todo formulário devolve `emailCollectionType = DO_NOT_COLLECT` na releitura.
3. Segunda sincronização seguida não emite request de estrutura (`SEM_MUDANCA` nos 20).
4. Trocar o professor de uma oferta gera **exatamente um** `updateItem`.
5. Com ≥ 1 resposta, alteração de estrutura é bloqueada.
6. Ingerir duas vezes não duplica submissão; `questionId` desconhecido vira alerta de órfã.
7. QR impresso a 5 cm abre o formulário certo em rede móvel.

## Fase 5 — Relatórios e anonimato (2 dias)
- Adesão durante a janela; **relatório por dimensão × segmento** (doc 08 §3.3);
  por oferta / professor / curso / turma após o encerramento.
- Limiares `MIN_RESPOSTAS_EXIBICAO` e `..._RESTRITO`, moderação, exportação CSV com
  as colunas de eixo e dimensão.

**Aceite:** `calcular_isg([5]*16 + ...)` reproduz **95,31%** para a Q68 do ciclo 2024;
oferta com 4 submissões suprimida, com 5 exibida; o relatório por dimensão distingue
`AMOSTRA_INSUFICIENTE` de `DIMENSAO_NAO_APLICADA`; CSV sem linha por submissão.

---

## Fase 6 — Deploy (meio dia)
- Backend no Render (Docker), banco no Supabase, frontend na Vercel.
- `GOOGLE_CREDENTIALS_JSON` e `GOOGLE_SUBJECT_EMAIL` configurados no Render.
- Variáveis de ambiente configuradas nos 3 serviços; CORS fechado no domínio real.
- ⚠️ **Free tier do Render hiberna após ~15 min de inatividade** — o primeiro acesso
  leva ~50s. Em dia de aplicação em sala isso é um problema concreto:
  aqueça o serviço antes (acesso a `/api/health` alguns minutos antes da aula) e
  mostre um *loading* honesto no portal ("carregando avaliação…").
- ⚠️ Supabase free pausa projetos inativos por 7 dias — acessar ao menos semanalmente.

**Aceite:** QR impresso, escaneado por um celular em rede móvel (fora do Wi-Fi da
instituição), abre o Google Form, responde, e a resposta aparece no painel após
*Importar respostas*.

> ⚠️ A hibernação do Render **deixa de afetar o aluno** — quem serve o formulário é o
> Google. Ela afeta só o painel administrativo, o que é aceitável.

---

## Depois do MVP (não implementar sem pedido)
| Item | Motivo de estar fora |
|---|---|
| Importar as respostas de 2024 para dentro do sistema | O comparativo pode ler o `consolidado_cpa.xlsx` como fonte externa; migrar 946 colunas esparsas não compensa |
| Perfil de Coordenação (D-4) | Exige autorização por papel, JWT |
| Comparativo entre semestres | Só faz sentido com 2+ períodos importados |
| Importação direta do sistema acadêmico | Depende da instituição |
| Relatório em PDF para o MEC/CPA oficial | Formato precisa ser definido pela comissão |
| Códigos de participação de uso único | Só se houver suspeita real de fraude |

---

## Checklist de "pronto"

- [ ] `docker compose up` sobe backend, frontend e banco sem intervenção manual
- [ ] `.env.example` lista todas as variáveis dos docs 08 §4
- [ ] Testes do importador verdes contra o fixture real (17 turmas, 105 ofertas, 164 alocações)
- [ ] Seed das 10 dimensões / 5 eixos aplicado
- [ ] Banco semeado com as **163 perguntas do Anexo B**, com `codigo` e `equivalencia_id`
- [ ] **67 grupos de equivalência** carregados; todos com dimensão única entre membros
- [ ] Nenhum ponto do código casa pergunta por texto
- [ ] `calcular_isg()` isolada, com teste reproduzindo 95,31% (Q68/2024)
- [ ] Nenhum formulário gerado sem tempo estimado na folha de aplicação
- [ ] Toda pergunta tem `dimensao_id`
- [ ] Nenhum `DELETE` físico em entidade referenciada por formulário publicado
- [ ] Schema sem IP, e-mail, matrícula ou `user_agent` em claro
- [ ] `submissao.data_envio` é `date`
- [ ] Grades do Google Forms testadas em 375px (doc 10 §3.1)
- [ ] CORS restrito ao domínio de produção
- [ ] `ADMIN_PASSWORD` e `GOOGLE_CREDENTIALS_JSON` fora do repositório
- [ ] Releitura de `emailCollectionType` implementada e bloqueando publicação
- [ ] README com o passo a passo: importar grade → perguntas → gerar → imprimir → coletar → relatório

---

## Riscos conhecidos e o que fazer

| Risco | Impacto | Resposta |
|---|---|---|
| `emailCollectionType` alterado à mão no Google | **Alto — quebra o anonimato** | Afirmar + reler a cada sync; publicação bloqueada em divergência (RN-41) |
| Editar formulário do Google com respostas | Alto — corrompe a série | Congelamento (RN-42) |
| CPA edita o formulário pela interface do Google | Médio — respostas órfãs | `requiredRevisionId`, alerta de órfãs, orientação de equipe |
| Credencial do Google revogada no meio do ciclo | Médio — para sync e ingestão | Conta de serviço com delegação; alerta ao primeiro `401` |
| Planilha do próximo semestre com layout diferente | Alto | Parser tolerante + conciliação obrigatória; nunca assumir posição fixa de linha/coluna |
| Homônimos entre cursos (RN-14) | Alto — mistura avaliação de dois docentes | Nunca fundir automaticamente entre cursos; exigir `nome_completo` antes do relatório oficial |
| Reescrever os enunciados das perguntas | Alto — quebra a série ano a ano, que é o que o MEC quer ver | Semear do Anexo B (textos reais do ciclo anterior); dimensões já confirmadas idênticas às da lei |

| Incluir turma na chave da oferta, ou módulo/rótulo na chave da turma | Alto — 136 blocos em vez de 105, e alunos recebendo dois formulários | Constraints do doc 02 + testes da Fase 3 |
| **Formulário de 88 a 168 perguntas** | Alto — abandono no meio, e só envios completos aparecem nos dados | Paginação por dimensão e por matéria, progresso, rascunho local, tempo estimado na folha (doc 04 §6, doc 07 §2) |
| Reproduzir o ISG com fórmula errada | Alto — números incomparáveis com 2024 | `calcular_isg()` isolada, com teste que reproduz 95,31% da Q68 |
| Agregar ISG como média de médias | Médio — distorce turmas com poucas matérias | Agregar sempre `pooled`, a partir das respostas (doc 08 §3.7) |
| Render hibernando na hora da aplicação | Médio | Aquecer antes; avisar a coordenação |
| Turma pequena com resultado suprimido | Médio — coordenação frustrada | Explicar o limiar na tela; é proteção, não falha |
| Aluno respondendo várias vezes | Médio | Melhor esforço (RN-32); assumido como limitação do anonimato total |
