# Anexos

| Arquivo | O que é | Como usar |
|---|---|---|
| `horario_20262.xlsx` | Cópia da grade institucional real de 2026.2 (10 abas) | Entrada dos testes do importador |
| `A_catalogo_grade_20262.md` | Catálogo extraído: 17 turmas, ofertas multiturma, flags e professores | Leitura humana; base do seed de aliases |
| `B_banco_perguntas_cpa.md` / `.json` | **As 163 perguntas oficiais da CPA** (4 questionários), com dimensão, bloco e a fórmula do ISG | **Seed do banco de perguntas** (doc 04 §5) |
| `grade_20262_esperado.json` | *Golden fixture*: saída esperada do parser | Asserções do teste do importador (doc 03 §6) |

## Os números de 2026.2

```
21 colunas de turma na planilha  ──►  17 turmas     (chave: curso + turno + período)
164 alocações na grade           ──► 105 ofertas    (chave: disciplina + professor)
                                     ├─ 101 avaliáveis, em 136 vínculos oferta↔turma
                                     └─   4 sem turma ──► avaliavel = false

FORMULÁRIOS DO PERÍODO:  17 de turma  (48 institucionais + 10 × nº de matérias)
                       +  1 docente + 1 técnico-administrativo + 1 comunidade
                       = 20
```

**27 das 105 ofertas atendem mais de uma turma** — um único bloco serve a todas elas.

## As duas chaves que o importador não pode errar

| Entidade | Chave | O que **não** entra |
|---|---|---|
| `turma` | `periodo + curso + turno + periodo_numero` | módulo, `Turma A/B`, `Sub - Turma A/B` |
| `oferta` | `periodo + disciplina + professor` | **turma** |

Errar a primeira infla 17 turmas para 21 e entrega dois formulários institucionais aos
mesmos alunos. Errar a segunda infla os blocos de matéria de 136 para 164.

## ⚠️ Não é verdade absoluta

É a saída de uma heurística sobre um documento humano. Precisam de decisão de pessoa:

- **`DISCIPLINA_AMBIGUA_OU`** — `Optativa I ou II`, `TCC 1 ou TCC 2`, `Estágio Supervisionado I ou II`
- **`OBSERVACAO_ADMINISTRATIVA`** — `"…Preceptor (A contratar) - Lançar no nome da Profa Katiulcy"`
- **`SEM_PREFIXO_PROF`** — `Promoção da Saúde - Régis`
- **`Educação Física · Noturno · 3º período`** — única turma de período ímpar; não segue o
  padrão 2/4/6/8 dos demais cursos (decisão D-2 em `01_regras_de_negocio.md`)

Use o fixture para travar o comportamento do parser; use a conciliação (RN-13) para o
que o parser não pode decidir sozinho.

## Estrutura do JSON

```jsonc
{ "periodo_letivo": "2026.2",
  "chave_da_turma":  "(curso, turno, periodo_numero) — módulo e rótulo A/B NÃO entram",
  "chave_da_oferta": "(disciplina, professor) — global no período letivo",
  "turmas": [
    { "id": 12, "curso": "BIOMEDICINA", "turno": "NOTURNO", "periodo_numero": 4,
      "rotulo": "Biomedicina · Noturno · 4º período",
      "modulos": ["AB"], "rotulos_origem": ["Turma A"],
      "colunas_origem": ["Biomedicina Noturno![4]", "Biomedicina Noturno![5]"],
      "turma_compartilhada_ciclo_basico": false }
  ],
  "ofertas": [
    { "id": 7, "disciplina": "Bioestatística", "professor": "Sandra",
      "chave": "bioestatistica | sandra",
      "turmas": [1, 2, 9, 10], "qtd_turmas": 4,
      "modalidades": [], "flags": [],
      "celulas_origem": ["Bioestatística - Profa Sandra"] }
  ],
  "avisos": [ { "tipo": "CICLO_BASICO_EXPANDIDO", "aba": "...", "motivo": "..." } ],
  "resumo": { "turmas": 17, "ofertas": 106, "formularios_total": 122, ... } }
```
