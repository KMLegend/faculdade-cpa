# 06 — Contratos da API

Base: `/api`. Documentação automática do FastAPI em `/docs`.
Todos os payloads em `snake_case`, datas em ISO-8601 com timezone.

## 1. Autenticação

| Grupo | Prefixo | Proteção |
|---|---|---|
| Administrativo | `/api/admin/*` | HTTP Basic com `ADMIN_USER` / `ADMIN_PASSWORD` (env) |
| Público (aluno) | `/api/publico/*` | **nenhuma** — RN-30 |

- Comparação da senha com `secrets.compare_digest` (tempo constante).
- Dependência única `Depends(exigir_admin)` em todo o router administrativo.
- ⚠️ Basic Auth é a decisão herdada de `01-init` ("autenticação simples estática").
  É aceitável para o MVP **porque não há dado pessoal de aluno no sistema**. Ao
  adicionar perfis (D-4), troque por JWT antes de ir a produção.

---

## 2. Endpoints públicos — **não existem mais**

Com a arquitetura Google Forms (doc 10), o respondente **nunca** toca a nossa API.
Foram removidos:

| Endpoint | Substituído por |
|---|---|
| `GET /api/publico/formularios/{uuid}` | o próprio Google Form (`responderUri`) |
| `POST /api/publico/formularios/{uuid}/respostas` | coleta do Google + `forms.responses.list` |

Permanece um único endpoint público:

### `GET /api/publico/qrcode/{uuid}`
Query: `formato=png|svg` (padrão `png`), `escala=1..20` (padrão `10`).
Codifica o `google_responder_uri` do formulário.
`200` → `StreamingResponse` `image/png` ou `image/svg+xml`,
`Cache-Control: public, max-age=86400`.
`404` se o formulário não existe **ou** ainda não foi sincronizado
(`google_responder_uri` nulo).

## 3. Endpoints administrativos

### Importação da grade
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/admin/importacoes` | `multipart/form-data`: `arquivo` + `periodo_letivo`. Roda os passos 1–5 e devolve a importação em `AGUARDANDO_REVISAO` |
| `GET` | `/api/admin/importacoes/{id}` | Resumo + contadores por status |
| `GET` | `/api/admin/importacoes/{id}/linhas` | Filtros `status`, `aba`; paginado |
| `PATCH` | `/api/admin/importacoes/{id}/linhas/{linha_id}` | Decisão do admin (ver abaixo) |
| `GET` | `/api/admin/importacoes/{id}/diff` | Prévia do que o commit faria (RN-11) |
| `POST` | `/api/admin/importacoes/{id}/aplicar` | Commit transacional. `409` se houver `ERRO`/`REVISAR` pendente |
| `DELETE` | `/api/admin/importacoes/{id}` | Cancela o staging |

`PATCH` de linha:
```jsonc
{
  "disciplina_id": 12,              // ou
  "disciplina_nova": "Toxicologia",
  "professor_id": 7,                // ou
  "professor_novo": "Washington",
  "criar_alias": true,              // grava washignton → Washington
  "status": "OK"                    // ou "IGNORADA"
}
```

### Cadastros
`GET|POST|PATCH|DELETE` em `/api/admin/professores`, `/api/admin/disciplinas`,
`/api/admin/cursos`, `/api/admin/turmas`, `/api/admin/ofertas`,
`/api/admin/periodos-letivos`, `/api/admin/dimensoes`.

A oferta expõe suas turmas: `GET /api/admin/ofertas/{id}` inclui
`"turmas": [{"id":12,"rotulo":"Biomedicina · Noturno · 4º período"}]`, e
`PUT /api/admin/ofertas/{id}/turmas` substitui o vínculo N:N (RN-07).
`DELETE` é sempre **soft** (`ativo=false`); `409` se a entidade estiver em formulário publicado.

Extras:
- `POST /api/admin/professores/{id}/fundir` — `{"absorver_id": 9}`: move ofertas e aliases, desativa o absorvido. Bloqueado se ambos tiverem submissões no mesmo período.
- `PATCH /api/admin/ofertas/{id}` — alternar `avaliavel` (RN-14).

### Banco de perguntas
| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/admin/perguntas?escopo=PROFESSOR&ativo=true` | Lista |
| `POST` | `/api/admin/perguntas` | Cria (com `vinculos[]` se `ESPECIFICA`) |
| `PATCH` | `/api/admin/perguntas/{id}` | Edita — bloqueia troca de `tipo` se já usada |
| `DELETE` | `/api/admin/perguntas/{id}` | Soft delete |
| `POST` | `/api/admin/perguntas/reordenar` | `[{"id":1,"ordem":3}, …]` |
| `POST` | `/api/admin/perguntas/previa` | `{"turma_id": 4}` → monta sem persistir; usar para ver o tamanho antes de gerar |

### Sincronização com o Google (doc 10)
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/admin/formularios/{id}/sincronizar` | Aplica a estrutura desejada via `batchUpdate`. `409` se `CONGELADO` |
| `POST` | `/api/admin/periodos/{id}/sincronizar` | Fila sequencial de todos os formulários do período |
| `GET` | `/api/admin/formularios/{id}/previa` | Estrutura que será enviada + *diff* contra o Google |
| `GET` | `/api/admin/formularios/{id}/divergencia` | Itens órfãos, revisão alterada à mão, anonimato |
| `POST` | `/api/admin/formularios/{id}/importar-respostas` | `forms.responses.list` incremental |
| `POST` | `/api/admin/periodos/{id}/importar-respostas` | Idem, todos os formulários |
| `GET` | `/api/admin/integracao/status` | Validade da credencial, cota consumida, último sync |

Erros próprios: `ANONIMATO_VIOLADO`, `ESTRUTURA_CONGELADA`, `REVISAO_DESATUALIZADA`,
`COTA_EXCEDIDA`, `CREDENCIAL_INVALIDA`.

### Formulários
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/admin/formularios/gerar-lote` | `{"periodo_letivo_id":1,"janelas":{"DISCENTE_TURMA":{"abre_em":…,"fecha_em":…}, …}}` → resumo `{criados, pulados, sem_turma, alertas}` por instrumento |
| `POST` | `/api/admin/formularios/publicar-lote` | `{"tipo_instrumento":"DISCENTE_TURMA"}` — publica os 17 de uma vez |
| `GET` | `/api/admin/formularios?periodo_letivo_id=1&tipo_instrumento=DISCENTE_TURMA&status=PUBLICADO` | Lista com contagem de submissões |
| `POST` | `/api/admin/formularios/{id}/publicar` | `RASCUNHO` → `PUBLICADO`; chama `setPublishSettings` (doc 10 §7). `409 ANONIMATO_VIOLADO` se a releitura falhar |
| `POST` | `/api/admin/formularios/{id}/encerrar` | → `ENCERRADO`; `isAcceptingResponses: false` |
| `DELETE` | `/api/admin/formularios/{id}` | Só se `RASCUNHO` |
| `GET` | `/api/admin/formularios/{id}/folha.pdf` | Folha de aplicação (matéria, turma ou cartaz de segmento) |
| `GET` | `/api/admin/periodos/{id}/folhas.pdf?tipo_instrumento=DISCENTE_TURMA` | Todas as folhas de um instrumento |
| `GET` | `/api/admin/turmas/{id}/conferencia.pdf` | Lista de conferência: matérias da turma vindas da grade |

### Relatórios — ver doc 08
| Método | Rota |
|---|---|
| `GET` | `/api/admin/relatorios/adesao?periodo_letivo_id=1` |
| `GET` | `/api/admin/relatorios/dimensoes?periodo_letivo_id=1&segmento=DISCENTE` ⭐ **o relatório que o MEC pede**, em ISG % |
| `GET` | `/api/admin/relatorios/questoes?periodo_letivo_id=1` — ISG por `codigo`, reproduzindo a página *ISG por Questão* do painel |
| `GET` | `/api/admin/relatorios/comparativo?de=2024&para=2026.2` — variação do ISG por questão entre ciclos |
| `GET` | `/api/admin/relatorios/oferta/{oferta_id}` |
| `GET` | `/api/admin/relatorios/professor/{professor_id}?periodo_letivo_id=1` |
| `GET` | `/api/admin/relatorios/curso/{curso_id}?periodo_letivo_id=1` |
| `GET` | `/api/admin/relatorios/turma/{turma_id}` |
| `GET` | `/api/admin/relatorios/exportar.csv?periodo_letivo_id=1` |
| `PATCH` | `/api/admin/comentarios/{resposta_item_id}` — `{"oculto": true}` (RN-34) |

### Saúde
`GET /api/health` → `{"status":"ok","banco":"ok","versao":"1.0.0"}` — sem autenticação,
usado pelo *health check* do Render.

---

## 4. Formato de erro (único em toda a API)

```jsonc
{ "erro": "ANONIMATO_VIOLADO",
  "mensagem": "O formulário está com coleta de e-mail ativada. Publicação bloqueada.",
  "detalhes": { "google_form_id": "1AbC…", "emailCollectionType": "VERIFIED" } }
```

`erro` é um código estável (o frontend decide a tela por ele);
`mensagem` é texto pronto para exibir ao usuário.

Códigos: `NAO_ENCONTRADO`, `VALIDACAO`, `IMPORTACAO_PENDENTE`, `CONFLITO_ESTADO`,
`NAO_AUTORIZADO`, `ANONIMATO_VIOLADO`, `ESTRUTURA_CONGELADA`, `REVISAO_DESATUALIZADA`,
`COTA_EXCEDIDA`, `CREDENCIAL_INVALIDA`.

## 5. CORS

Permitir apenas `FRONTEND_URL` e `http://localhost:3000`, métodos
`GET, POST, PATCH, DELETE`, **sem** `allow_credentials`.
Como não há mais portal público, o CORS pode ser fechado no domínio do painel apenas.
