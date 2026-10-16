# 10 — Integração com Google Forms

> **Mudança de arquitetura.** O sistema **não hospeda** o formulário do respondente.
> Ele orquestra **Google Forms** via API: cria, atualiza as perguntas que mudam a cada
> ciclo conforme a grade, gera o QR do link e recolhe as respostas de volta.

---

## 1. O que muda

```
                 ANTES (docs 05/07)                 AGORA
  ┌──────────────────────────────┐   ┌────────────────────────────────────┐
  │ React /responder/{uuid}      │   │ Google Forms (hospedado pelo Google)│
  │ POST /respostas              │   │ forms.responses.list → nosso BD     │
  │ antifraude, honeypot, rate   │   │ Google cuida de UX, mobile, uptime  │
  │ limit, rascunho localStorage │   │                                     │
  └──────────────────────────────┘   └────────────────────────────────────┘
```

| Componente | Situação |
|---|---|
| Importador da grade (doc 03) | **Mantido integralmente** |
| Banco de 163 perguntas (doc 04, Anexo B) | **Mantido integralmente** |
| Modelo de domínio (doc 02) | Mantido + campos de identidade do Google |
| Motor de formulários (doc 05) | Vira **sincronizador** |
| Portal do aluno em React | **Removido** |
| `POST /respostas`, antifraude, honeypot, rate limit | **Removidos** — Google assume |
| Relatórios e ISG (doc 08) | **Mantidos integralmente** |
| Geração de QR Code | Mantida, agora sobre o `responderUri` |

### Fluxo

```
grade .xlsx ──► importador ──► turmas + ofertas ─┐
                                                 ├──► SINCRONIZADOR ──► Google Forms API
banco de 163 perguntas (Anexo B) ────────────────┘         │
                                                           ▼
                                          20 formulários + responderUri
                                                           │
                                            ┌──────────────┴──────────────┐
                                            ▼                             ▼
                                    QR Code (backend)          forms.responses.list
                                            │                             │
                                       impressão                     nosso BD
                                                                          │
                                                                    ISG / relatórios
```

---

## 2. O que é estável e o que muda a cada ciclo

Esta é a pergunta central: *"alterar as questões que mudam anualmente"*.

| Parte do formulário | Origem | Muda por ciclo? |
|---|---|---|
| Título e descrição | turma + período letivo | Sim (o período) |
| **Bloco institucional (48 perguntas)** | Anexo B, Q1–Q9 + Q20–Q58 | **Não** — só se a CPA revisar o banco |
| **Bloco por matéria (10 × N ofertas)** | **a grade importada** | **Sim, todo ciclo** |
| Configurações (anonimato, janela) | constantes do sistema | Não |

O bloco por matéria é exatamente o que era digitado à mão em 2025.2:

```
2025.2 (manual):  "O docente domina o conteúdo e está atualizado?   (Bioestatística - Pedro)"
2026 (gerado):  grade "Bioestatística · Prof. Pedro" com as 10 perguntas como linhas
```

---

## 3. Estrutura do formulário no Google Forms

### 3.1 Use `questionGroupItem` (grade) — resolve o problema de tamanho

O doc 04 §7 aponta formulários de 88 a 168 perguntas. Em **grade de múltipla escolha**,
cada oferta vira **um único item visual** com 10 linhas e 5 colunas:

```
┌─ Toxicologia · Prof. Washington ──────────────────────────────┐
│                                        1    2    3    4    5   │
│ O docente apresenta o plano de ensino  ○    ○    ○    ●    ○   │
│ O docente domina o conteúdo             ○    ○    ○    ○    ●   │
│ O docente tem bom relacionamento        ○    ○    ●    ○    ○   │
│ … (10 linhas)                                                  │
└────────────────────────────────────────────────────────────────┘
```

Um formulário de 148 perguntas vira **8 grades institucionais + 10 grades de matéria**:
18 blocos visuais em vez de 148 campos. É a diferença entre viável e inviável no celular.

⚠️ **Teste em tela de 375px antes de publicar.** Grades de 5 colunas no Google Forms
móvel ficam apertadas; se necessário, reduza os rótulos das colunas a `1 … 5` com a
legenda na descrição do item.

### 3.2 Paginação com `pageBreakItem`

```
Página 1   Abertura: o que é a CPA, anonimato, tempo estimado
Página 2   Dimensão 1 — Missão e PDI                     (grade, 4 linhas)
Página 3   Dimensão 2 — Ensino, Pesquisa e Extensão      (grade, 9 linhas)
…
Página 9   Dimensão 9 — Atendimento aos Discentes        (grade, 5 linhas)
Página 10  Avaliação das disciplinas — Toxicologia · Prof. Washington
Página 11  Avaliação das disciplinas — Bioética · Prof. Clayson
…
Página 21  Comentários livres (opcional)
```

Uma matéria por página dá ao aluno a mesma sensação de progresso que a paginação do
doc 07 daria — só que implementada pelo Google.

### 3.3 Mapa de tipos

| Elemento | Item da API |
|---|---|
| Bloco Likert (dimensão ou matéria) | `questionGroupItem` + `grid` com `columns.type = RADIO` |
| Pergunta Likert isolada | `questionItem` + `choiceQuestion` `RADIO` |
| Comentário livre | `questionItem` + `textQuestion` `paragraph: true` |
| Quebra de página | `pageBreakItem` |
| Texto explicativo | `textItem` |

---

## 4. Autenticação

**Decisão do projeto: OAuth2 com *refresh token***, de uma conta Google
institucional da CPA. O roteiro completo, do console às quatro variáveis, está em
`anexos/C_configurar_google_cloud.md`.

### 4.1 ⚠️ `forms.body` é escopo sensível — e isso decide a configuração

O Google classifica `forms.body` como **escopo sensível**. A consequência depende do
tipo de usuário do projeto no Cloud Console:

| Tipo | Situação | Consequência |
|---|---|---|
| **Interno** | projeto sob o Google Workspace da FPM | ✅ Sem verificação, sem expiração. **É o caminho.** |
| **Externo**, *Testing* | conta comum | Refresh token **expira em 7 dias** — a integração para no meio do ciclo |
| **Externo**, publicado | conta comum | Exige **verificação do Google**: semanas, política de privacidade, domínio próprio e vídeo de demonstração |

> Publicar como *In production* **não** basta num projeto externo: dispara o processo
> de verificação. Se houver Workspace, use **Interno** e nada disso se aplica.

**Alternativa sem consentimento interativo:** conta de serviço com *domain-wide
delegation*, personificando `cpa@fpm.edu.br`. Exige um administrador do Workspace
autorizar o *client ID*. Mais robusta para operação contínua, mas depende de acesso
administrativo que nem sempre existe.

⚠️ **Nunca** use conta de serviço *sem* delegação: os formulários ficariam sob uma
identidade sem Drive próprio, e ninguém da CPA conseguiria abri-los pela interface.

### 4.2 Escopos

| Escopo | Para quê |
|---|---|
| `https://www.googleapis.com/auth/forms.body` | criar e editar formulários, `setPublishSettings` |
| `https://www.googleapis.com/auth/forms.responses.readonly` | ler respostas |
| `https://www.googleapis.com/auth/drive.file` | criar e organizar os formulários na pasta do ciclo |

`drive.file` dá acesso **apenas aos arquivos que o app criar** — o resto do Drive da
conta permanece inacessível. Foi escolhido no lugar do `drive` completo por isso.

### 4.3 Variáveis de ambiente

| Variável | Conteúdo |
|---|---|
| `GOOGLE_CLIENT_ID` | do cliente OAuth criado no Cloud Console |
| `GOOGLE_CLIENT_SECRET` | idem — **nunca versionado** |
| `GOOGLE_REFRESH_TOKEN` | gerado por `python -m scripts.autorizar_google` |
| `GOOGLE_DRIVE_FOLDER_ID` | pasta do ciclo, criada pelo mesmo script |

### 4.4 Quando o token morre

`invalid_grant` é **erro fatal com alerta no painel**, nunca falha silenciosa. A
sincronização e a ingestão param, mas **os formulários continuam no ar recebendo
respostas** — nada se perde. Basta regerar o token e atualizar a variável.

---

## 5. ⭐ Anonimato — o ponto mais sensível desta arquitetura

O anonimato deixa de ser garantido pelo **nosso** modelo de dados e passa a depender de
uma configuração do Google. Por isso ele é **afirmado em toda sincronização** e
**verificado por releitura**:

```python
BODY_SETTINGS = {
    "updateSettings": {
        "settings": {"emailCollectionType": "DO_NOT_COLLECT"},   # RN-31
        "updateMask": "emailCollectionType",
    }
}

def garantir_anonimato(form_id: str) -> None:
    service.forms().batchUpdate(formId=form_id,
                                body={"requests": [BODY_SETTINGS]}).execute()
    # releitura obrigatória — nunca confie no write
    form = service.forms().get(formId=form_id).execute()
    tipo = form.get("settings", {}).get("emailCollectionType")
    if tipo != "DO_NOT_COLLECT":
        raise AnonimatoViolado(form_id, tipo)     # bloqueia a publicação
```

**Regras inegociáveis:**

1. `emailCollectionType = DO_NOT_COLLECT` afirmado a cada sincronização e **relido**.
   Divergência ⇒ o formulário **não é publicado** e o admin é alertado.
2. O formulário é compartilhado como **"qualquer pessoa com o link"**. Restringir ao
   domínio faz o Google identificar o respondente.
3. **Não** ative "limitar a 1 resposta" — exige login e quebra o anonimato.
   Consequência assumida: não há como impedir resposta duplicada (era assim em 2025.2).
4. Na ingestão, **descarte o `lastSubmittedTime` com hora**; grave apenas a data (RN-31).
5. A planilha vinculada (`linkedSheetId`) não deve ser criada — ela duplica os dados em
   um artefato fora do controle do sistema.

> **Seja honesto com a CPA:** as respostas passam a residir na infraestrutura do Google,
> sob a conta institucional. Quem tiver acesso a essa conta vê as respostas brutas — o
> mesmo que acontecia em 2025.2. O que o sistema garante é que **nenhum dado de identidade
> é coletado**; não que a instituição não possa ver o conteúdo.

---

## 6. Sincronização idempotente

### 6.1 Identidade: o que guardamos do Google

Acrescentar a `formulario`:

| Campo | Tipo | Conteúdo |
|---|---|---|
| `google_form_id` | varchar(80) NULL **UNIQUE** | `formId` da API |
| `google_responder_uri` | text NULL | URL do QR |
| `google_edit_uri` | text NULL | link de edição, para a CPA |
| `google_revision_id` | varchar(40) NULL | concorrência otimista |
| `sincronizado_em` | timestamptz NULL | |
| `hash_estrutura` | char(64) NULL | sha256 da estrutura desejada — detecta se precisa sincronizar |

Acrescentar a `formulario_pergunta`:

| Campo | Tipo | Conteúdo |
|---|---|---|
| `google_item_id` | varchar(40) NULL | id do item (grade) |
| `google_question_id` | varchar(40) NULL | ⭐ id da pergunta — **chave da ingestão** |

> **`google_question_id` é o que conserta o defeito de 2025.2.** O pipeline antigo casava
> pergunta com dimensão **pelo texto**, e como a mesma frase existe em até 3
> questionários, o ISG histórico mistura segmentos (Anexo B §B.5). Com o id estável do
> Google, cada resposta aponta para exatamente uma `formulario_pergunta`, que já carrega
> `oferta_id`, `codigo`, `equivalencia_id` e `dimensao_id`.

### 6.1.1 ⭐ A cadeia de identificadores

Nenhum elo usa texto — é o que separa este desenho do de 2025.2:

```
resposta no Google
   │  answers[questionId]
   ▼
google_question_id ──► formulario_pergunta ──┬─► codigo          → comparar CICLOS
  (id do Google,        (snapshot do ciclo)   ├─► equivalencia_id → comparar SEGMENTOS
   por formulário)                            ├─► dimensao_id     → relatório SINAES
                                              └─► oferta_id       → relatório por professor
```

| Identificador | Escopo | Estável entre ciclos? |
|---|---|---|
| `pergunta.id` | nosso banco | sim (PK interna) |
| **`pergunta.codigo`** | **negócio, entre ciclos** | **sim — nunca renumerado** |
| **`equivalencia_id`** | **negócio, entre segmentos** | **sim** |
| `formulario_pergunta.id` | um formulário de um ciclo | não (por natureza) |
| `google_question_id` | um formulário no Google | não — muda se o item for recriado |

⚠️ **`google_question_id` é volátil.** Um `deleteItem` + `createItem` gera id novo.
Por isso ele **nunca** é a identidade de negócio: é só a ponte entre a resposta bruta e o
nosso snapshot, que é quem carrega `codigo`.

### 6.1.2 Recuperação do vínculo

Se o mapeamento `google_question_id → formulario_pergunta` se perder (restauração de
backup, sincronização interrompida no meio), **não recase por texto** — foi assim que o
pipeline de 2025.2 se contaminou. Recupere por:

1. `sincronizacao_log.detalhe` — guarda o JSON completo do formulário devolvido pelo
   último `batchUpdate`, com todos os `itemId`/`questionId` na ordem enviada;
2. em último caso, `forms.get` + casamento por **posição** dentro da estrutura conhecida
   (grade *n*, linha *m*), que é determinística porque `montar()` é determinístico.

Se nem isso resolver, marque o formulário como `DIVERGENTE` e exija decisão humana.
**Uma resposta mal atribuída é pior que uma resposta perdida.**

### 6.2 Algoritmo

```python
def sincronizar(formulario) -> ResultadoSync:
    desejado = montar(formulario)                      # doc 04 §4
    h = hash_estrutura(desejado)
    if formulario.hash_estrutura == h and formulario.google_form_id:
        return ResultadoSync.SEM_MUDANCA               # idempotência

    if formulario.tem_respostas:
        raise EstruturaCongelada(formulario)           # §6.4 — nunca edite com respostas

    if not formulario.google_form_id:
        criado = service.forms().create(
            body={"info": {"title": formulario.titulo,
                           "documentTitle": formulario.titulo}}).execute()
        formulario.google_form_id = criado["formId"]
        mover_para_pasta(criado["formId"], GOOGLE_DRIVE_FOLDER_ID)

    atual = service.forms().get(formId=formulario.google_form_id).execute()
    requests = diff_para_requests(atual, desejado)      # §6.3
    requests.insert(0, BODY_SETTINGS)                   # anonimato sempre primeiro

    if requests:
        resp = service.forms().batchUpdate(
            formId=formulario.google_form_id,
            body={"requests": requests,
                  "writeControl": {"requiredRevisionId": atual["revisionId"]},
                  "includeFormInResponse": True}).execute()
        gravar_ids(formulario, resp["form"])            # item_id e question_id
    garantir_anonimato(formulario.google_form_id)
    formulario.hash_estrutura = h
    formulario.google_responder_uri = resp["form"]["responderUri"]
    return ResultadoSync.ATUALIZADO
```

**Pontos obrigatórios:**

- **Um único `batchUpdate` por formulário.** Não faça uma chamada por pergunta: 20
  formulários × 150 itens estouraria a cota em minutos (§8).
- `writeControl.requiredRevisionId` sempre. Se alguém da CPA editou o formulário à mão,
  a chamada falha com `400` em vez de sobrescrever o trabalho da pessoa.
- `includeFormInResponse: true` devolve o formulário já atualizado, com os
  `itemId`/`questionId` novos — evita um `get` extra.

### 6.3 O *diff* que importa: só o bloco de matéria muda

```
para cada oferta desejada:
    se não existe item com essa oferta   → createItem  (grade nova, no índice certo)
    se o rótulo mudou (professor trocou) → updateItem  (só o título da grade)
    se as linhas mudaram                 → updateItem  (rows do grid)
para cada item existente sem oferta correspondente:
                                         → deleteItem
```

O bloco institucional só entra no *diff* se a CPA alterar o banco de perguntas.
Num ciclo típico, **o institucional não gera nenhuma request** e só as matérias mudam —
que é exatamente o requisito: *"alterar as questões que mudam anualmente"*.

⚠️ `deleteItem` e `createItem` usam **índice**, não id. Ordene as requests de trás para
frente ao deletar, senão os índices deslizam e você apaga o item errado.

### 6.4 Congelamento após a primeira resposta

**Editar um Google Forms que já tem respostas desloca as colunas da planilha e corrompe
a série.** Regra: assim que `forms.responses.list` retornar ≥ 1 resposta, a estrutura
fica congelada.

| Situação | Ação |
|---|---|
| Grade corrigida **antes** da publicação | sincroniza normalmente |
| Grade corrigida **depois**, sem respostas | sincroniza, com aviso |
| Grade corrigida **depois**, com respostas | **bloqueado**. O admin decide: manter e anotar a divergência, ou encerrar e criar um formulário novo |

---

## 7. Publicação e janela de aplicação

`setPublishSettings` controla abertura e fechamento — mapeia direto no ciclo de vida do
doc 05 §2:

| Status no nosso BD | `publishState` |
|---|---|
| `RASCUNHO` | `isPublished: false` |
| `PUBLICADO` | `isPublished: true`, `isAcceptingResponses: true` |
| `ENCERRADO` | `isPublished: true`, `isAcceptingResponses: false` |

```python
def publicar(formulario):
    service.forms().setPublishSettings(
        formId=formulario.google_form_id,
        body={"publishSettings": {"publishState": {
                  "isPublished": True, "isAcceptingResponses": True}},
              "updateMask": "publishState"}).execute()
```

O fechamento pela `fecha_em` é aplicado por uma varredura no acesso ao painel — **sem job
agendado**, porque o free tier do Render hiberna (doc 09, Fase 6). Quem passar do prazo vê
a tela padrão do Google ("não está mais aceitando respostas"), o que é aceitável.

---

## 8. Cotas

| Limite | Valor |
|---|---|
| Leituras / min / projeto | 975 |
| Leituras caras (`responses.list`) / min / projeto | 450 |
| **Escritas / min / projeto** | **375** |
| Escritas / min / usuário / projeto | **150** |

Uma sincronização completa: 20 formulários × (1 `get` + 1 `batchUpdate` + 1
`setPublishSettings`) ≈ **60 requisições**. Folgado — desde que cada formulário use
**um** `batchUpdate`.

Obrigatório mesmo assim:
- *Backoff* exponencial com jitter em `429` e `5xx`;
- fila sequencial (um formulário por vez) — não paralelize a sincronização;
- `hash_estrutura` para pular formulários sem mudança.

---

## 9. Ingestão das respostas

Substitui o `main.py` de 2025.2 (que baixava 17 CSVs por URL de exportação).

```python
def ingerir(formulario, desde: datetime | None) -> int:
    filtro = f'timestamp > "{desde.isoformat()}"' if desde else None
    token, novas = None, 0
    while True:
        r = service.forms().responses().list(
            formId=formulario.google_form_id,
            filter=filtro, pageToken=token).execute()
        for resp in r.get("responses", []):
            if ja_importada(resp["responseId"]):       # idempotência
                continue
            sub = Submissao(formulario=formulario,
                            data_envio=parse(resp["lastSubmittedTime"]).date(),  # RN-31: só data
                            google_response_id=resp["responseId"])
            for qid, ans in resp.get("answers", {}).items():
                fp = por_question_id.get(qid)          # ⭐ id estável, não texto
                if not fp:
                    registrar_orfa(formulario, qid); continue
                sub.itens.append(montar_item(fp, ans))
            salvar(sub); novas += 1
        token = r.get("nextPageToken")
        if not token: break
    return novas
```

- `google_response_id` com `UNIQUE` torna a ingestão repetível sem duplicar.
- **Resposta órfã** (`questionId` desconhecido) = alguém editou o formulário à mão.
  Não descarte em silêncio: registre e alerte — é o sintoma de estrutura divergente.
- ⚠️ **Nunca** tente resolver uma órfã casando o texto da pergunta. Sem `questionId`
  conhecido, a resposta fica pendente até decisão humana (§6.1.2).
- A ingestão roda sob demanda (botão no painel) e ao abrir o relatório. Sem agendador.

---

## 10. QR Code

O `responderUri` do Google é longo
(`https://docs.google.com/forms/d/e/1FAIpQLSc…/viewform`, ~120 caracteres), o que aumenta
a densidade do QR:

- Mantenha `ERROR_CORRECT_M` e **no mínimo 5 cm** impressos — mais que isso se a folha
  for fotocopiada.
- Imprima a URL em texto abaixo do QR, como já previsto no doc 05 §4.
- Se a leitura em sala se mostrar ruim, use um encurtador **próprio**
  (`cpa.fpm.edu.br/t/{codigo}` → 302), nunca um serviço de terceiros: um encurtador
  externo registra quem clicou, e isso contamina o anonimato.

---

## 11. Riscos desta arquitetura

| Risco | Gravidade | Mitigação |
|---|---|---|
| `emailCollectionType` alterado à mão na interface | **Alta** — quebra o anonimato | Afirmar + **reler** a cada sync; bloquear publicação se divergir (§5) |
| CPA edita o formulário à mão durante o ciclo | Alta — desloca colunas, gera respostas órfãs | `requiredRevisionId`; alerta de órfãs; orientar a equipe a editar só pelo painel |
| Estrutura alterada depois de haver respostas | Alta — corrompe a série | Congelamento (§6.4) |
| Token/credencial revogado no meio do ciclo | Média — para a sincronização e a ingestão | Conta de serviço com delegação; alerta no painel ao primeiro `401` |
| Cota estourada | Baixa | Um `batchUpdate` por formulário, fila sequencial, *backoff* |
| Dependência de disponibilidade do Google | Baixa | Aceita — é melhor que a nossa em free tier |
| Respostas residem no Google | Média — questão de governança | Explicitar à CPA; ingerir para o BD próprio e tratar o Google como fonte transitória |

---

## 12. Critérios de aceite

1. Sincronizar o período 2026.2 cria **20 formulários** no Drive da conta institucional.
2. *Biomedicina · Noturno · 6º período* sai com **8 grades institucionais + 12 grades de
   matéria**, uma por oferta, com o rótulo `Disciplina · Prof. Nome`.
3. `forms.get` de qualquer formulário devolve `emailCollectionType = DO_NOT_COLLECT`.
4. Publicar um formulário deixa `isPublished` e `isAcceptingResponses` verdadeiros;
   encerrar deixa `isAcceptingResponses` falso.
5. Rodar a sincronização duas vezes seguidas: a segunda não emite nenhuma request de
   estrutura (`hash_estrutura` igual) e devolve `SEM_MUDANCA` para os 20.
6. Trocar o professor de uma oferta e ressincronizar emite **exatamente um** `updateItem`
   — o título da grade daquela matéria. O bloco institucional não é tocado.
7. Com ≥ 1 resposta registrada, qualquer tentativa de alterar a estrutura é bloqueada.
8. Ingerir duas vezes a mesma resposta não cria submissão duplicada.
9. Uma resposta cujo `questionId` não existe no snapshot gera alerta de órfã, não silêncio,
   e **não** é reatribuída por texto.
9.1 Toda `resposta_item` gravada tem `codigo` e `equivalencia_id` resolvidos pelo
    snapshot — nunca nulos, nunca inferidos.
10. O QR impresso a 5 cm, fotografado por celular em rede móvel, abre o formulário certo.
