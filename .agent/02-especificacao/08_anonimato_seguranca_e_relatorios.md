# 08 — Anonimato, Segurança e Relatórios

O anonimato não é uma funcionalidade: é a **condição de validade** da CPA. Se o aluno
suspeitar que pode ser identificado, ele responde o que é seguro, não o que é verdade.

---

> ⚠️ **Arquitetura Google Forms.** A coleta acontece no Google (doc 10). As garantias
> abaixo continuam valendo, mas parte delas passa a ser **afirmada por configuração** em
> vez de estrutural no nosso banco. Leia `10_integracao_google_forms.md` §5 junto com esta
> seção — é lá que está o mecanismo de verificação.

## 1. Garantias de anonimato (RN-30)

### Onde mora cada garantia agora

| Garantia | Antes | Agora |
|---|---|---|
| Não coletar identidade | portal próprio sem login | `emailCollectionType = DO_NOT_COLLECT`, afirmado e **relido** a cada sync |
| Não gravar IP | nosso backend | Google não nos expõe IP na API — garantia **melhorou** |
| Sem hora na submissão | nossa tabela | descartamos o `lastSubmittedTime`, gravando só a data |
| Antifraude | honeypot + rate limit | **removido** — sem login não há como impedir duplicata (era assim em 2025.2) |
| Limiar de exibição (k-anonimato) | nosso relatório | **inalterado** — continua nosso |

### O que o sistema **nunca** faz
| Proibido | Por quê |
|---|---|
| Login, matrícula, e-mail ou nome do aluno | Não existe identificação no modelo |
| IP em claro na base | Permite correlação com a rede da instituição |
| `user_agent` em claro | Impressão digital do dispositivo |
| Timestamp com hora na submissão | Cruzar com a lista de presença identifica quem respondeu |
| FK de `submissao` para qualquer tabela de pessoa | — |
| Guardar o `lastSubmittedTime` com hora | Cruzar com a lista de presença identifica quem respondeu |
| Analytics de terceiros no portal do respondente | Vazamento fora do controle |
| Campo "curso" ou "turma" no formulário docente/técnico | Em segmento pequeno, dois campos demográficos já identificam a pessoa |

### O que o sistema guarda e por quê
| Campo | Formato | Finalidade | Reversível? |
|---|---|---|---|
| `submissao.data_envio` | `date` (**sem hora**) | Ordenar por dia, medir adesão | — |
| `submissao.google_response_id` | id opaco do Google | Idempotência da ingestão | Não identifica pessoa |
| `submissao.duracao_segundos` | int | Detectar bot | Não identifica |

Não existe salt nem hash de dispositivo nesta arquitetura: não há o que pseudonimizar,
porque a API do Google não nos entrega identificador algum do respondente.

> ⚠️ **Honestidade técnica sobre a arquitetura Google Forms:** não guardamos nenhum
> identificador de dispositivo — a API não nos expõe IP nem *user agent*, então do nosso
> lado o anonimato é estrutural. **Porém as respostas residem na conta Google
> institucional**, e quem tiver acesso a essa conta vê o conteúdo bruto. Era assim em 2025.2.
> O que o sistema garante é que **nenhum dado de identidade é coletado** — não que a
> instituição não possa ler as respostas. Diga isso à CPA nesses termos.

### Limiar de exibição — k-anonimato (RN-33)

```python
MIN_RESPOSTAS_EXIBICAO = 5   # variável de ambiente
```

Nenhum número, média ou comentário de uma oferta é exibido enquanto ela tiver menos de
5 submissões. Em turmas pequenas isso vai suprimir resultados — **é o comportamento
correto**: com 2 respondentes, uma média baixa somada a um comentário identifica a pessoa.

A verificação acontece **na consulta do backend**, não no frontend. Abaixo do limiar a
API devolve:
```jsonc
{ "oferta_id": 57, "submissoes": 3, "suprimido": true,
  "motivo": "AMOSTRA_INSUFICIENTE", "medias": null, "comentarios": [] }
```

### Moderação de comentários (RN-34)
- Comentários só ficam visíveis após `fecha_em`.
- O admin pode marcar `resposta_item.oculto = true` (nunca apagar).
- Comentário que cite nome próprio de aluno deve ser ocultado — orientação na tela.
- A moderação é registrada em log **sem** referência ao autor (não existe autor).

---

## 2. Segurança

| Vetor | Mitigação |
|---|---|
| Coleta de e-mail ativada por engano | Releitura obrigatória a cada sync; publicação bloqueada em divergência (doc 10 §5) |
| Formulário restrito ao domínio | Compartilhamento sempre "qualquer pessoa com o link"; verificado no sync |
| Envio em massa / bot | Proteção nativa do Google Forms. Não implementamos antifraude própria |
| Envio duplicado do mesmo aluno | **Sem mitigação** — "limitar a 1 resposta" exigiria login e quebraria o anonimato. Limitação assumida, igual a 2025.2 |
| Credencial do Google vazada | Conta de serviço com escopos mínimos; `GOOGLE_CREDENTIALS_JSON` fora do repositório |
| XSS via comentário importado | Sanitizar na **ingestão**, escapar na saída do relatório |
| SQL injection | Exclusivamente SQLAlchemy parametrizado; zero SQL por concatenação |
| Credencial de admin fraca | `ADMIN_PASSWORD` ≥ 16 caracteres, `compare_digest`, nunca versionada |
| Segredos no bundle | Só `VITE_API_BASE_URL` no frontend |
| CORS aberto | Lista fixa: `FRONTEND_URL` + `localhost:3000` |
| Upload malicioso de `.xlsx` | Limite de 5 MB, validar extensão **e** assinatura ZIP, `openpyxl` com fórmulas desabilitadas, sem executar macro |

### Rate limit — **não se aplica**
Quem recebe as submissões é o Google. O painel administrativo é protegido por Basic Auth
e não tem superfície pública além do QR.

---

## 3. Relatórios

Todos respeitam RN-33 e só existem no escopo administrativo.

### 3.1 Adesão (disponível **durante** a janela)
Único relatório visível com a avaliação aberta. Mostra **contagem**, nunca conteúdo.

| Curso | Turma | Ofertas | Submissões | Adesão estimada |
|---|---|---|---|---|
| Biomedicina | Noturno · 4º PER T. A | 10 | 23 | — |

> "Adesão estimada" exige o número de matriculados, que o sistema **não** tem
> (a planilha não traz matrícula). Deixe o campo opcional, preenchido manualmente
> em `turma.total_alunos` — ou omita na v1.

### 3.2 Por oferta (após o encerramento)
```jsonc
{ "oferta_id": 57, "disciplina": "Toxicologia", "professor": "Washington",
  "turma": "Biomedicina Noturno · 4º PER Turma A",
  "submissoes": 23, "suprimido": false,
  "perguntas": [
    { "texto": "O professor demonstra domínio do conteúdo da disciplina.",
      "tipo": "LIKERT_5", "respostas": 22, "nao_sei": 1,
      "media": 4.32, "mediana": 5, "desvio_padrao": 0.78,
      "distribuicao": { "1": 0, "2": 1, "3": 3, "4": 7, "5": 11 } }
  ],
  "comentarios": [ { "id": 881, "texto": "Aulas práticas excelentes.", "oculto": false } ] }
```

Sempre exiba a **distribuição**, não só a média: média 3,0 pode ser "todo mundo neutro"
ou "metade ama, metade odeia" — são situações opostas para a coordenação.

`nao_sei` (valor nulo) é contado à parte e **não** entra na média.

### 3.3 ⭐ Por Dimensão SINAES — o relatório que alimenta o documento oficial

Agrega **toda** submissão do período pela `dimensao_id` do snapshot (RN-26), cruzando
com o segmento. É a saída que a CPA leva ao relatório de autoavaliação.

```jsonc
{ "periodo_letivo": "2026.2",
  "eixos": [
    { "numero": 3, "nome": "Políticas Acadêmicas",
      "dimensoes": [
        { "numero": 2, "nome": "Políticas para o Ensino, a Pesquisa e a Extensão",
          "nome_institucional": null, "codigo_institucional": null,
          "por_segmento": {
            "DISCENTE":   { "respostas": 4821, "media": 4.11, "isg_pct": 77.75, "suprimido": false },
            "DOCENTE":    { "respostas": 92,   "media": 3.74, "isg_pct": 68.50, "suprimido": false },
            "TECNICO_ADMINISTRATIVO": { "respostas": 0, "suprimido": true,
                                        "motivo": "DIMENSAO_NAO_APLICADA" } },
          "isg_geral_pct": 77.10, "isg_2025_pct": 75.31, "variacao_pp": +1.79 } ] } ] }
```

Regras:
- Dimensão não aplicada a um segmento aparece como `DIMENSAO_NAO_APLICADA`, **nunca**
  como média zero — zero seria lido como avaliação péssima.
- ⭐ A resposta emite **os dois rótulos**: o legal (`nome`) e o institucional
  (`nome_institucional`, como no Power BI histórico — doc 04 §1.1). O frontend exibe o
  institucional quando existir, para que a comunidade reconheça a mesma nomenclatura do
  painel do ano anterior.
- A média por dimensão pondera **por resposta**, não por formulário: uma dimensão
  medida em 137 blocos de matéria não pode pesar o mesmo que uma medida em 17.
- Perguntas `TEXTO_LIVRE` não entram na média; entram na contagem de comentários.
- O limiar de exibição (RN-34) se aplica **por célula** segmento × dimensão.

### 3.4 Por professor (consolidado do período)
Média por pergunta agregada entre as ofertas do professor, **com a lista de ofertas**.
Ofertas suprimidas não entram no consolidado — e o relatório informa quantas foram
excluídas por amostra insuficiente, para não mascarar viés.

### 3.5 Por curso
Médias dos blocos `GERAL` e `DISCIPLINA` por curso/turno, e ranking de disciplinas —
sempre respeitando o limiar.

### 3.7 ⭐ ISG — Índice de Satisfação Geral

```python
def calcular_isg(valores: list[int]) -> float:
    """Métrica oficial da CPA. Escala 1–5 normalizada para 0..1.
    Confirmada contra o painel 2025.2: Q68 -> 95,31% e Q49 -> 85,23%, ambos exatos."""
    if not valores:
        return None
    return (statistics.mean(valores) - 1) / 4
```

Publicado como percentual com 2 casas (`0.00%`), igual ao painel histórico.
Faixas de cor herdadas do `.pbix`: **0,25 · 0,46 · 0,72**.

| Faixa | Leitura |
|---|---|
| ≥ 72% | satisfatório |
| 46% – 72% | atenção |
| 25% – 46% | crítico |
| < 25% | grave |

Toda agregação — questão, dimensão, eixo, oferta, professor, turma, curso, segmento —
é publicada em ISG %, **com a média 1–5 e a distribuição ao lado**. Média sozinha esconde
polarização; ISG sozinho esconde a escala.

⚠️ **Agregue sempre a partir das respostas individuais (`pooled`), nunca fazendo média de
ISGs já calculados** — médias de médias distorcem quando as amostras têm tamanhos
diferentes, e com 4 a 12 matérias por turma elas têm.

### 3.8 ⭐ Comparativos — por ciclo e por segmento

Os dois relatórios que só existem porque as perguntas têm identidade estável (doc 04 §5.1).

**Entre ciclos** — agrega por `formulario_pergunta.codigo`:

```jsonc
{ "de": "2025.2", "para": "2026.2",
  "questoes": [
    { "codigo": 11, "texto": "O docente domina o conteúdo e está atualizado?",
      "dimensao": 2, "versao_texto": 1,
      "isg_2025_pct": 81.48, "isg_2026_pct": 84.20, "variacao_pp": +2.72,
      "respostas_2025": 1214, "respostas_2026": 1602 } ],
  "nao_comparaveis": [
    { "codigo": 164, "motivo": "PERGUNTA_NOVA" },
    { "codigo": 29,  "motivo": "DESATIVADA_DUPLICATA" } ] }
```

- ⚠️ Se `versao_texto` mudou entre os ciclos, exiba a variação **com marca de atenção** —
  a redação não é idêntica, embora a pergunta seja a mesma.
- Pergunta sem par em um dos ciclos vai para `nao_comparaveis` **com o motivo**, nunca
  sumindo em silêncio.

**Entre segmentos** — agrega por `equivalencia_id`:

```jsonc
{ "equivalencia_id": 1, "texto": "Você conhece o PDI da FPM?", "dimensao": 1,
  "segmentos": {
    "DISCENTE":               { "codigo": 1,   "isg_pct": 72.4, "respostas": 166 },
    "DOCENTE":                { "codigo": 59,  "isg_pct": 81.2, "respostas": 16  },
    "TECNICO_ADMINISTRATIVO": { "codigo": 119, "isg_pct": 68.9, "respostas": 11  } },
  "amplitude_pp": 12.3 }
```

`amplitude_pp` (maior − menor) ordena o relatório: as maiores divergências entre públicos
são o achado mais acionável para a CPA — onde a instituição se vê de um jeito e a
comunidade de outro.

⚠️ O limiar de exibição (§RN-34) se aplica **por célula segmento × pergunta**. Com 11
respostas de técnicos em 2025.2, boa parte dessas células ficaria suprimida sob limiar 10 —
ver a decisão D-4 no doc 01.

### 3.9 Exportação CSV
Uma linha por `(oferta, pergunta)` com agregados — **nunca** uma linha por submissão,
que facilitaria reidentificação por cruzamento.

```csv
periodo,segmento,instrumento,codigo,equivalencia_id,versao_texto,eixo,dimensao,curso,turno,turma,disciplina,professor,bloco,pergunta,submissoes,respostas,media,isg_pct,mediana,d1,d2,d3,d4,d5
2026.2,DISCENTE,DISCENTE_TURMA,11,7,1,3,2,Biomedicina,NOTURNO,4º período,Toxicologia,Washington,PROFESSOR,"O docente domina o conteúdo e está atualizado?",23,22,4.32,83.00,5,0,1,3,7,11
```

As colunas `eixo` e `dimensao` são obrigatórias — sem elas o CSV não serve ao relatório
oficial. `codigo` e `equivalencia_id` são obrigatórias para que a planilha possa ser
cruzada com a de qualquer outro ciclo **sem casar por texto**.

Comentários em livre exportação ficam em arquivo separado, sem chave que os ligue à
submissão (só à oferta), e apenas os não ocultos.

---

## 4. Variáveis de ambiente (contrato completo)

### Backend
| Variável | Exemplo | Obrigatória |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…@…supabase.co:5432/postgres` | sim |
| `FRONTEND_URL` | `https://cpa-instituicao.vercel.app` (sem barra final) | sim |
| `ADMIN_USER` | `cpa` | sim |
| `ADMIN_PASSWORD` | ≥ 16 caracteres | sim |
| `GOOGLE_CREDENTIALS_JSON` | JSON da conta de serviço | sim |
| `GOOGLE_SUBJECT_EMAIL` | conta personificada (`cpa@fpm.edu.br`) | sim |
| `GOOGLE_DRIVE_FOLDER_ID` | pasta do ciclo no Drive | não |
| `MIN_RESPOSTAS_EXIBICAO` | `5` | não (padrão 5) — discentes |
| `MIN_RESPOSTAS_EXIBICAO_RESTRITO` | `10` | não (padrão 10) — técnico-adm. e comunidade (RN-34) |
| `POWERBI_URL_HISTORICO` | link do painel do ciclo anterior | não — exibido no admin como referência |
| `ISG_FAIXAS` | `0.25,0.46,0.72` | não — faixas de cor herdadas do painel 2025.2 |
| `LIMITE_ALERTA_PERGUNTAS` | `40` | não (padrão 40) |
| `TIMEZONE` | `America/Sao_Paulo` | não |
| `MAX_UPLOAD_MB` | `5` | não |

### Frontend
| Variável | Exemplo |
|---|---|
| `VITE_API_BASE_URL` | `https://cpa-api.onrender.com` |

`.env.example` na raiz deve listar todas, com valor vazio e comentário.
**Nunca** versionar `.env`.

## 5. Critérios de aceite

1. Nenhuma tabela contém IP, e-mail, matrícula ou `user_agent` em claro
   (verificável por inspeção do schema).
2. `submissao.data_envio` é `date`, não `timestamp`.
3. Oferta com 4 submissões devolve `suprimido: true` e `medias: null`.
4. A mesma oferta com 5 submissões passa a exibir os números.
4.1 Formulário `TECNICO_ADMINISTRATIVO` com 9 submissões continua suprimido (limiar 10).
4.2 O relatório por dimensão suprime **por célula** segmento × dimensão, e distingue
    `AMOSTRA_INSUFICIENTE` de `DIMENSAO_NAO_APLICADA`.
5. Comentário permanece invisível enquanto o formulário não estiver `ENCERRADO`.
6. O CSV exportado não permite reconstruir uma submissão individual.
7. `forms.get` de todo formulário publicado devolve `emailCollectionType = DO_NOT_COLLECT`.
8. Nenhuma tabela guarda identificador de dispositivo, IP ou hora de submissão.
