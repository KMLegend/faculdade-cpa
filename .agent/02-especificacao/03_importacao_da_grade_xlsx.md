# 03 — Importação da Grade (`.xlsx`)

> Este é o componente de maior risco do sistema. A planilha institucional é um
> **documento humano**, não um formato de dados: tem mesclagens, cabeçalhos
> irregulares, typos, rótulos duplicados e bilhetes administrativos dentro das células.
> O objetivo **não** é acertar 100% sozinho — é acertar a maioria, **medir a confiança**
> e levar o resto para uma tela de conciliação.

Arquivo de referência: `horario 20262.xlsx` (10 abas, 21 colunas de turma → **17 turmas**,
**105 ofertas**, **164 alocações**).
Catálogo extraído: `anexos/A_catalogo_grade_20262.md`.
Fixture de teste: `anexos/grade_20262_esperado.json`.

---

## 1. Pipeline

```
upload .xlsx
   │
   ├─ 1. LEITURA      openpyxl, read_only=False (precisa de merged_cells)
   ├─ 2. SEGMENTAÇÃO  aba → curso+turno; colunas → turmas (curso+turno+período)
   ├─ 3. EXTRAÇÃO     célula → (disciplina, professor, modalidade, flags)
   ├─ 4. MATCHING     texto → entidade existente (alias → exato → fuzzy)
   ├─ 5. STAGING      grava importacao_grade + importacao_linha  ◄── NADA no domínio
   ├─ 6. CONCILIAÇÃO  admin revisa na tela; decisões viram alias
   └─ 7. COMMIT       cria/atualiza Curso, Turma, Disciplina, Professor, Oferta, Alocacao
```

Passos 1–5 rodam na requisição de upload (a planilha é pequena, < 100 KB).
Passo 7 roda em uma transação única; falhou, nada é aplicado.

---

## 2. Leitura e segmentação

### 2.1 Mesclagens — a regra que mais quebra implementações ingênuas

No `.xlsx`, uma célula mesclada tem valor **apenas na célula superior-esquerda**; as
demais vêm `None`. **Expanda as mesclagens antes de qualquer outra coisa:**

```python
for faixa in ws.merged_cells.ranges:
    valor = ws.cell(faixa.min_row, faixa.min_col).value
    for r in range(faixa.min_row, faixa.max_row + 1):
        for c in range(faixa.min_col, faixa.max_col + 1):
            grade[(r, c)] = valor          # mesmo valor em toda a faixa
            tamanho_mescla[(r, c)] = (faixa.max_row - faixa.min_row + 1,
                                      faixa.max_col - faixa.min_col + 1)
```

Semântica das mesclagens nesta planilha:

| Mesclagem | Significado | Consequência |
|---|---|---|
| **Vertical** (`D5:D6`) | Aula ocupando 2+ horários | **Uma** alocação, `duracao_horarios = 2` |
| **Horizontal** (`D5:E5`) em linha de aula | Aula compartilhada entre Turma A e Turma B | **Uma** oferta **por turma** (as duas avaliam) |
| **Horizontal** na **última linha de cabeçalho** | As colunas são **a mesma turma** | **Uma** turma, não N — **RN-04** |

Mas atenção: a mesclagem resolve **parte** da consolidação. Colunas **não mescladas**
também podem ser a mesma turma — `Sub - Turma A`/`Sub - Turma B` e o `Turma A` repetido
de Biomedicina Noturno. Quem resolve isso é a chave da turma (§2.4), não a mesclagem.

> Caso real: em `Educação Física_Matutino`, as colunas D e E estão mescladas no
> cabeçalho (`Turma única`). Sem essa regra o importador cria 2 turmas e **dobra** as
> ofertas (16 em vez de 8).

### 2.2 Layout esperado da aba

```
 col:   A              B                    C/D/E/F...
 lin 1  —              —                    instrução de matrícula ("Matricular 3 e 4 períodos")
 lin 2  —              —                    período + módulo       ("4º PER - Módulo AB")
 lin 3  —              —                    rótulo da turma        ("Turma A" / "Turma Única")
 lin 4+ dia da semana  "1º Horário - 18:30" células de aula
```

**Detecção do cabeçalho (não fixe em 3 linhas):** são linhas de cabeçalho as primeiras
linhas em que **A e B estão vazias** e existe conteúdo a partir da coluna C.
`GTI - Matutino` tem só 2 linhas de cabeçalho e ainda coloca texto na coluna A
(`Matricular 1 e 2 períodos`) — o parser precisa tolerar isso.

### 2.3 Mapeamento aba → curso + turno

Por casamento de padrão no nome da aba, **com confirmação do admin**:

| Aba | Curso | Turno |
|---|---|---|
| ` Matutino (Ciclo básico)` | **compartilhada** (expandir) | `MATUTINO` |
| `Educação Física_Matutino` | `EDUCACAO_FISICA` | `MATUTINO` |
| `Enfermagem_Matutino` | `ENFERMAGEM` | `MATUTINO` |
| `Biomedicina- Matutino` | `BIOMEDICINA` | `MATUTINO` |
| `GTI - Matutino` | `GTI` | `MATUTINO` |
| `GTI - Noturno` | `GTI` | `NOTURNO` |
| `Ciclo Básico Integrado - Noturn` | **compartilhada** (expandir) | `NOTURNO` |
| `Biomedicina Noturno` | `BIOMEDICINA` | `NOTURNO` |
| `Enfermagem - Noturno` | `ENFERMAGEM` | `NOTURNO` |
| `Educação Física - Noturno` | `EDUCACAO_FISICA` | `NOTURNO` |

Note: espaço à esquerda, `_` como separador, nome truncado em 31 caracteres
(`... - Noturn`) — limite do Excel. **Normalize antes de comparar.**

### 2.4 ⭐ Identificação da Turma — `Curso + Turno + Período` (RN-04)

**A turma NÃO é a coluna.** Várias colunas apontam para a mesma turma. A chave é
`(periodo_letivo, curso, turno, periodo_numero)`; módulo e rótulo são atributos.

```
                     coluna da planilha  ──┐
   Sub - Turma A ────────────────────────┐ │
   Sub - Turma B ────────────────────────┼─┴──►  Biomedicina · Matutino · 4º período
   Turma A (col D) ──────────────────────┤       (UMA turma, UM formulário institucional)
   Turma A (col E, rótulo repetido) ─────┘
```

**Extração do `periodo_numero`** — é o único campo obrigatório da chave que vem do texto:

```python
m = re.search(r'(\d+)\s*[ºo°]?\s*(?:PER|Período)', texto_cabecalho)
periodo_numero = int(m.group(1)) if m else None
```

Casa com `4º PER - Módulo AB`, `2 Período - Módulo I`, `8º PER - O cuidar nos Processos Clínicos`.

⚠️ **Herança entre colunas irmãs:** a coluna da `Sub - Turma B` (Enfermagem e Biomedicina
matutino) **não repete** a linha de instrução — seu cabeçalho só tem módulo e rótulo.
Se `periodo_numero` vier `None`, **herde da coluna anterior da mesma aba** e registre a
flag `PERIODO_HERDADO`. Sem isso o importador cria duas turmas fantasma sem período.

**Extração do `modulo`** (informativo, fora da chave): o que vem depois de `Módulo`
(`AB`, `Análises Biomédicas`, `EB-A`); se a palavra não aparecer, guarde o texto restante.

**Rótulos e colunas** são **acumulados em listas** (`rotulos_origem`, `colunas_origem`),
porque a mesma turma recebe várias colunas.

### 2.5 ⭐ Expansão do ciclo básico (RN-03)

**`CICLO_BASICO` não é curso.** Uma coluna de ciclo básico é uma aula compartilhada:
os mesmos professores atendem alunos de cursos diferentes ao mesmo tempo.

A linha de instrução de matrícula diz quais cursos:

| Texto na planilha | Expande em |
|---|---|
| `Matricular: Biomedicina (1 e 2 período) - Enfermagem (1 período)` + `2º PER- Módulo P` | `Biomedicina · Matutino · 2º` **e** `Enfermagem · Matutino · 2º` |
| `Biomedicina ( 1 e 2 períodos) - Enfermagem (1 período)` + `2º PER- Módulo P` | `Biomedicina · Noturno · 2º` **e** `Enfermagem · Noturno · 2º` |
| `Educação física ( 1, 2 e 3períodos)` + `3º PER- Módulo M` | `Educação Física · Noturno · 3º` |

```python
CURSOS_NO_TEXTO = {"biomedicina": "BIOMEDICINA", "enfermagem": "ENFERMAGEM",
                   "educacao fisica": "EDUCACAO_FISICA", "gti": "GTI"}

def cursos_da_coluna(aba, cabecalho) -> list[str]:
    if not eh_ciclo_basico(aba):
        return [CURSO_DA_ABA[aba]]
    texto = slugificar(" ".join(cabecalho))
    achados = sorted({v for k, v in CURSOS_NO_TEXTO.items() if k in texto})
    return achados or ["INDEFINIDO"]      # vazio ⇒ REVISAR
```

Cada curso encontrado gera (ou reusa) **sua própria turma**, e **todas as ofertas daquela
coluna se vinculam a todas essas turmas** em `oferta_turma`. Assim o aluno de Enfermagem
do 2º período recebe o formulário institucional do **seu** curso, e não um genérico de
"ciclo básico".

Se nenhum curso for reconhecido, marque `REVISAR` com `CURSO_COMPARTILHADO_INDEFINIDO`.

### 2.6 Colunas que não são turma

| Padrão no cabeçalho | Tratamento |
|---|---|
| `Estágio supervisionado - 7 e 8 períodos` | **Não gera turma.** As ofertas da coluna ficam **sem turma** e nascem `avaliavel = false` (RN-15) |
| `Práticas Hospitalares`, `Extras (Para CH)` (coluna A) | Linhas de complemento de carga horária — alocação da turma da própria aba |

No arquivo real isso produz exatamente **4 ofertas sem turma**: `Estágio Supervisionado I
ou II` (Alexandre e Washington), `Optativa I ou II - Endocrinologia laboratorial`
(Roberpaulo) e `TCC 1 ou TCC 2` (Clayson).

---

## 3. Interpretação da célula de aula

### 3.1 Gramática observada

```
<disciplina> [ "(" <modalidade> ")" ] <separador> [ "(" ] <prefixo> <nome_professor> [ ")" ] [ "(" <sufixo> ")" ]

separador      := " - " | " -" | "- " | " – "
prefixo        := "Prof" | "Profa" | "Prof." | "Profa." | ""      ← pode faltar
modalidade     := Preleção | Prática | Prática Hospitalar | EAD | Extensão | Estágio
sufixo         := Extensão | EAD | EAD - Extensão | 5hrs | ...
```

### 3.2 Algoritmo

```
1. Normalizar espaços (\s+ → " "), aparar. Descartar célula igual a "." ou com < 6 chars.
2. Descartar se casar com o padrão de ruído:
   ^(Turma|Sub ?- ?Turma|\*? ?Matricular|\d+[ºo]? ?(PER|Período)|\w+-feira|Sábado|
     Extras|Práticas Hospitalares|Matutino|Noturno|\d+[ºo] Horário)
3. Extrair e REMOVER os parênteses de modalidade/sufixo, guardando as modalidades.
4. Localizar o professor, nesta ordem:
   a) "(Prof<a?> Nome)" no fim                  → ex.: "TCC 1 ou TCC 2 (Prof Clayson)"
   b) "- Prof<a?> Nome" no fim                  → caso dominante
   c) "- Nome" no fim, Nome capitalizado        → flag SEM_PREFIXO_PROF
   d) nada casou                                → status ERRO, motivo PROFESSOR_NAO_IDENTIFICADO
5. disciplina := tudo à esquerda do trecho do professor, aparando " -–."
6. Aplicar flags (§3.4).
```

### 3.3 Corpus de teste — casos reais **obrigatórios** no teste unitário

| Célula (texto literal da planilha) | Disciplina | Professor | Modalidades | Flags |
|---|---|---|---|---|
| `Imunologia - Prof Clayson` | Imunologia | Clayson | — | — |
| `Bioquímica (Preleção) - Profa Andrea` | Bioquímica | Andrea | PRELECAO | — |
| `Bioética -Prof Rogério` | Bioética | Rogério | — | — |
| `Histologia e Embriologia (Preleção)- Prof  Prof André` | Histologia e Embriologia | André | PRELECAO | `PREFIXO_DUPLICADO` |
| `Caso Problematizador e Avaliação Interdisciplinar P - (Profa Isabela)` | Caso Problematizador e Avaliação Interdisciplinar P | Isabela | — | — |
| `Promoção da Saúde - Régis` | Promoção da Saúde | Régis | — | `SEM_PREFIXO_PROF` |
| `Caso Problematizador ... EF - Profa Lisiane (Extensão)` | Caso Problematizador ... EF | Lisiane | EXTENSAO | — |
| `Instrumentos Básicos de Enfermagem (Prática Hospitalar) - Prof Luciene` | Instrumentos Básicos de Enfermagem | Luciene | PRATICA_HOSPITALAR | — |
| `Práticas Biomédicas - Química (Prática) - Prof Alexandre` | Práticas Biomédicas - Química | Alexandre | PRATICA | `HIFEN_NO_NOME` |
| `Ecologia, análises físico-químicas e microbiológicas em saneamento ambiental (Prática) - Profa Vanessa` | Ecologia, análises físico-químicas e microbiológicas em saneamento ambiental | Vanessa | PRATICA | — |
| `Optativa I ou II - Endocrinologia laboratorial - Prof Roberpaulo` | Optativa I ou II - Endocrinologia laboratorial | Roberpaulo | — | `DISCIPLINA_AMBIGUA_OU` |
| `Estágio Supervisionado I ou II (Prof Washington)` | Estágio Supervisionado I ou II | Washington | — | `DISCIPLINA_AMBIGUA_OU` |
| `TCC 1 ou TCC 2 (Prof Clayson)` | TCC 1 ou TCC 2 | Clayson | — | `DISCIPLINA_AMBIGUA_OU` |
| `Toxicologia - Preleção - Prof Washignton` | Toxicologia | Washignton | PRELECAO | `MODALIDADE_SEM_PARENTESES`, `PROFESSOR_TYPO` |
| `Estudos Disciplinares e Projeto Integrador II- Prof Leonardo (EAD` | Estudos Disciplinares e Projeto Integrador II | Leonardo | EAD | `PARENTESE_NAO_FECHADO` |
| `O cuidar nos Processos Críticos - Preceptor (A contratar) - Lançar no nome da Profa Katiulcy` | O cuidar nos Processos Críticos | Katiulcy | — | `OBSERVACAO_ADMINISTRATIVA`, **status ERRO** |
| `.` | — | — | — | descartada |

> Atenção ao penúltimo: `Preceptor (A contratar)` **não é professor**. A instrução
> humana embutida (`Lançar no nome da Profa Katiulcy`) só pode ser aplicada por uma
> pessoa. Marque `ERRO` e mostre o texto integral na conciliação.

### 3.4 Flags e status resultante

| Flag | Status | Significado |
|---|---|---|
| `PROFESSOR_NAO_IDENTIFICADO` | `ERRO` | Bloqueia o commit |
| `OBSERVACAO_ADMINISTRATIVA` | `ERRO` | Bilhete humano na célula |
| `DISCIPLINA_VAZIA` | `ERRO` | Só sobrou o professor |
| `DISCIPLINA_AMBIGUA_OU` | `REVISAR` | `X ou Y` — admin decide se vira 1 ou 2 disciplinas |
| `SEM_PREFIXO_PROF` | `REVISAR` | Pode ser disciplina cortada |
| `PERIODO_HERDADO` | `OK` | Período herdado da coluna irmã (§2.4) |
| `COLUNAS_CONSOLIDADAS` | `OK` | Duas ou mais colunas apontaram para a mesma turma |
| `CURSO_COMPARTILHADO_INDEFINIDO` | `REVISAR` | Aba de ciclo básico sem curso reconhecível (§2.5) |
| `PERIODO_NAO_IDENTIFICADO` | `ERRO` | Sem `periodo_numero` e sem coluna irmã — não há chave de turma |
| `PROFESSOR_NOVO` / `DISCIPLINA_NOVA` | `REVISAR` | Sem correspondência no cadastro |
| `MATCH_FUZZY` (0,80 ≤ score < 0,95) | `REVISAR` | Provável typo |
| `PREFIXO_DUPLICADO`, `HIFEN_NO_NOME`, `MODALIDADE_SEM_PARENTESES`, `PARENTESE_NAO_FECHADO` | `OK` | Só informativo |

**O commit só é permitido com zero linhas `ERRO` e zero `REVISAR` pendentes.**

---

## 4. Matching com o cadastro existente

Para professor e disciplina, nesta ordem — pare no primeiro que casar:

| Etapa | Critério | Confiança | Ação |
|---|---|---|---|
| 1 | `professor_alias.slug_origem` / `disciplina_alias.slug_origem` | `1.00` | vincula, `OK` |
| 2 | `slugificar(texto) == entidade.slug` | `1.00` | vincula, `OK` |
| 3 | Levenshtein normalizado ≥ `0.95` | score | vincula, `OK` |
| 4 | Levenshtein normalizado ≥ `0.80` | score | sugere, `REVISAR` |
| 5 | nada | `0.00` | entidade nova, `REVISAR` |

Implementação: `difflib.SequenceMatcher` da biblioteca padrão — **não** adicione
dependência de fuzzy matching (restrição de pacotes leves de `01-init`).

Casos que a etapa 3 resolve, comprovados no arquivo real:

| Texto A | Texto B | Score aprox. |
|---|---|---|
| `washignton` | `washington` | 0,95 |
| `cinnesiologia e biomecanica` | `cinesiologia e biomecanica` | 0,98 |
| `gestao de projetos em tecnologia de informacao` | `... da informacao` | 0,98 |
| `promocao a saude` | `promocao da saude` | 0,94 → **REVISAR** |
| `vitoria` | `victoria` | 0,93 → **REVISAR** |
| `anatomofisiologia humana sistema nervoso urinario...` (2 grafias) | | 0,99 |

> **Nunca funde automaticamente professores que aparecem em cursos diferentes** (RN-13),
> mesmo com score 1,00 — `Linda` da Educação Física pode não ser a `Linda` da Biomedicina.
> Nesse caso, `REVISAR` com o alerta `HOMONIMO_ENTRE_CURSOS`.

**Toda decisão tomada na conciliação vira um registro em `*_alias`.** Na importação de
`2027.1`, `Washignton` casa na etapa 1 e não incomoda mais ninguém.

### 4.1 Primeira importação — cadastro vazio

Na primeira vez, **nada** casa: as 164 linhas chegam como `PROFESSOR_NOVO` +
`DISCIPLINA_NOVA` e revisar uma a uma é inviável. Por isso:

- Se a base de professores/disciplinas está **vazia**, a conciliação oferece a ação em
  lote **"Criar todas as entidades novas"**, que promove a `OK` toda linha cujo único
  motivo seja `*_NOVO`.
- Antes de criar, o sistema aplica o fuzzy **entre as próprias linhas do arquivo** e
  mostra os agrupamentos propostos — é assim que `Washignton`/`Washington` e
  `Victória`/`Vitória` aparecem para decisão logo na primeira carga.
- Linhas com `DISCIPLINA_AMBIGUA_OU`, `SEM_PREFIXO_PROF`, `ROTULO_TURMA_DUPLICADO`,
  `OBSERVACAO_ADMINISTRATIVA` ou `HOMONIMO_ENTRE_CURSOS` **nunca** entram na ação em
  lote — essas seguem individuais.

**Números esperados na primeira carga de `horario 20262.xlsx`, após a criação em lote:**
São **164 alocações**, e o número muda entre as duas etapas do pipeline:

| Etapa | OK | REVISAR | ERRO |
|---|---|---|---|
| Após o parser (§3) | 158 | 5 | 1 |
| Após o matching contra cadastro vazio (§4) | 154 | 9 | 1 |

As 5 de revisão do parser são 4 `DISCIPLINA_AMBIGUA_OU` + 1 `SEM_PREFIXO_PROF`;
a de erro é a célula do `Preceptor (A contratar)`. O matching acrescenta 4
`MATCH_FUZZY` — as alocações de `Washignton` e `Vitória`, que precisam da decisão
de fusão. Depois de criados os aliases, a próxima importação volta a 158/5/1.

---

## 5. Commit (passo 7)

Transação única, nesta ordem:

```
1. upsert curso        (por slug; nunca cria CICLO_BASICO)
2. upsert professor    (por slug ou id confirmado na conciliação) + grava aliases
3. upsert disciplina   (idem)
4. upsert turma        (chave: periodo, curso, turno, periodo_numero)  ← RN-04
                       acumula modulo, rotulos_origem[], colunas_origem[]
5. upsert oferta       (chave: periodo, disciplina, professor)         ← RN-09
6. upsert oferta_turma (N:N; expansão do ciclo básico entra aqui)      ← RN-03, RN-07
7. marca avaliavel=false nas ofertas sem nenhuma turma                 ← RN-15
8. DELETE alocacao de ofertas do período; INSERT das alocações novas
9. marca ofertas ausentes no arquivo como ativo = false  (não apaga)
10. importacao_grade.status = APLICADA
```

**Idempotência (RN-11):** reimportar o mesmo arquivo produz zero alterações.
Antes do commit, mostre o *diff*:

```
+ 3 ofertas novas        ~ 1 professor renomeado
- 2 ofertas desativadas  = 163 sem alteração
```

⚠️ **Formulários já publicados nunca são alterados por uma reimportação.** Se uma oferta
avaliada for desativada, o formulário mantém seu snapshot e o relatório continua válido.

---

## 6. Critérios de aceite do importador

1. Importar `horario 20262.xlsx` produz exatamente **17 turmas**, **105 ofertas** e
   **164 alocações**, conferindo com `anexos/grade_20262_esperado.json`.
2. `Educação Física_Matutino` produz **1** turma (não 2).
2.1 *Biomedicina · Matutino · 4º período* é **uma** turma, alimentada pelas colunas
    `Sub - Turma A` e `Sub - Turma B` — com `PERIODO_HERDADO` na segunda (§2.4).
2.2 *Biomedicina · Noturno · 4º período* é **uma** turma, embora `Turma A` apareça em
    duas colunas.
2.3 A aba ` Matutino (Ciclo básico)` cria **duas** turmas — `Biomedicina · Matutino · 2º`
    e `Enfermagem · Matutino · 2º` — e vincula as mesmas ofertas às duas (§2.5).
2.4 Nenhum curso `CICLO_BASICO` é criado.
2.5 A coluna de Estágio Supervisionado **não** cria turma; suas **4 ofertas** ficam sem
    turma e com `avaliavel = false`.
3. As 17 células do corpus §3.3 são interpretadas conforme a tabela.
4. Nenhum registro de domínio é criado enquanto a importação estiver `AGUARDANDO_REVISAO`.
5. Reimportar o mesmo arquivo gera diff vazio e nenhuma duplicata.
6. Após conciliar `Washignton → Washington`, uma nova importação classifica essa célula
   como `OK` sem intervenção.
7. `alocacao.texto_origem` está preenchido em 100% das alocações.
8. Na primeira carga, após "Criar todas as entidades novas", restam exatamente
   **6 linhas `REVISAR` e 2 `ERRO`** — conferindo com as `flags` do fixture.
9. `Bioestatística | Sandra` é **uma** oferta, vinculada a todas as turmas que a cursam
   (`oferta_turma` com mais de uma linha). **27 ofertas** têm mais de uma turma.
10. ⭐ `Toxicologia - Preleção - Prof Washignton` e `Toxicologia - Prática - Prof
    Washignton` são **uma** oferta com duas alocações — a modalidade escrita **fora de
    parênteses** também precisa ser removida do nome da disciplina (RN-10).
11. Mescla vertical vira **uma** alocação com `duracao_horarios = N`, não N alocações.
