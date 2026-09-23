# 04 — Dimensões SINAES, Banco de Perguntas e Montagem

Cobre as regras 2 e 3 do usuário e o requisito de avaliação **por dimensão**, que é o que
o MEC/SINAES cobra da CPA.

---

## 1. As 10 dimensões e os 5 eixos — seed obrigatório

Base legal: **Lei 10.861/2004, art. 3º** (as 10 dimensões) e a organização em **5 eixos**
adotada pelo instrumento de avaliação institucional do INEP/DAES.

| Eixo | Nome do eixo | Dim. | Nome da dimensão |
|---|---|---|---|
| **1** | Planejamento e Avaliação Institucional | 8 | Planejamento e Avaliação |
| **2** | Desenvolvimento Institucional | 1 | Missão e Plano de Desenvolvimento Institucional |
| | | 3 | Responsabilidade Social da Instituição |
| **3** | Políticas Acadêmicas | 2 | Políticas para o Ensino, a Pesquisa e a Extensão |
| | | 4 | Comunicação com a Sociedade |
| | | 9 | Política de Atendimento aos Discentes |
| **4** | Políticas de Gestão | 5 | Políticas de Pessoal |
| | | 6 | Organização e Gestão da Instituição |
| | | 10 | Sustentabilidade Financeira |
| **5** | Infraestrutura Física | 7 | Infraestrutura Física |

> ⚠️ Este agrupamento é **dado de referência**, carregado por seed e editável pelo admin.
> A CPA da instituição é quem valida o enquadramento de cada pergunta — o sistema não
> deve tratar o mapeamento como imutável.

### 1.1 ⭐ Alinhamento com o Power BI do ciclo anterior — **CONFIRMADO**

O painel público da CPA foi lido (23/09/2026): **193 respostas**, **68 questões**,
**10 dimensões**. Detalhes completos em `anexos/B_banco_perguntas_bi.md`.

**Resultado: as dimensões do painel são exatamente as 10 da Lei 10.861/2004, com a mesma
numeração e nomes idênticos aos da tabela acima.** Não há taxonomia institucional
divergente — `nome_institucional` pode ser preenchido igual ao nome legal, e a série
histórica do painel fica automaticamente comparável.

Distribuição real das 68 questões do ciclo anterior:

| Dim. | Nome | Questões no BI |
|---|---|---|
| 1 | Missão e PDI | 4 |
| 2 | Ensino, Pesquisa e Extensão | **20** |
| 3 | Responsabilidade Social | 5 |
| 4 | Comunicação com a Sociedade | 4 |
| 5 | Políticas de Pessoal | 7 |
| 6 | Organização e Gestão | 5 |
| 7 | Infraestrutura Física | **11** |
| 8 | Planejamento e Avaliação | 5 |
| 9 | Atendimento aos Discentes | 5 |
| 10 | Sustentabilidade Financeira | 2 |

**O banco do Anexo B tem precedência sobre o seed sugerido em §5.** Reaproveitar os
enunciados preserva a comparabilidade ano a ano, que se perde por completo se o texto
mudar — mesmo mantendo a dimensão. O §5 só se aplica onde o Anexo B não cobrir.

Três pontos exigem decisão da CPA antes de semear (Anexo B §B.4 e §B.5):

1. **Q68 é duplicata da Q10** (texto idêntico) — descartar.
2. **A numeração vai até 129, mas só 68 questões aparecem** — 61 números ausentes.
   Confirmar se existe um banco maior, com as questões dos outros segmentos.
3. **A métrica do painel é ISG %, não média 1–5** — a fórmula não está exposta.
   Ver `08_anonimato_seguranca_e_relatorios.md` §3.7.

---

## 2. Os quatro instrumentos

Estrutura confirmada pelo ciclo 2025.2 (`historico/dimensoes.xlsx`): **163 perguntas
oficiais**, numeração contínua, divididas em 4 questionários.

| Instrumento | Segmento | Nº das perguntas | Qtd. | Respostas 2025.2 |
|---|---|---|---|---|
| `DISCENTE_TURMA` | `DISCENTE` | 1–58 | 58 | 166 |
| `DOCENTE` | `DOCENTE` | 59–118 | 60 | 16 |
| `TECNICO_ADMINISTRATIVO` | `TECNICO_ADMINISTRATIVO` | 119–160 | 42 | 11 |
| `COMUNIDADE` | `COMUNIDADE` | 161–163 | 3 | **0** ⚠️ |

### 2.1 `DISCENTE_TURMA` — os dois blocos

As 58 perguntas discentes **não se comportam da mesma forma**:

| Bloco | Perguntas | Comportamento |
|---|---|---|
| `INSTITUCIONAL` | **48** — Q1–Q9, Q20–Q58 | Aparecem **uma vez** no formulário |
| `DISCIPLINA` / `PROFESSOR` | **10** — Q10–Q19 | Repetidas **para cada oferta** da turma |

As 10 por matéria, com o bloco a que pertencem:

| Nº | Bloco | Pergunta |
|---|---|---|
| 10 | `PROFESSOR` | O docente apresenta o plano de ensino da disciplina de forma sistematizada no início do semestre? |
| 11 | `PROFESSOR` | O docente domina o conteúdo e está atualizado? |
| 12 | `PROFESSOR` | O docente tem bom relacionamento com os discentes e é disponível para o esclarecimento de dúvidas? |
| 13 | `PROFESSOR` | O docente é pontual e assíduo em suas funções? |
| 14 | `PROFESSOR` | A didática do docente contribui para a aprendizagem? |
| 15 | `DISCIPLINA` | A carga horária e organização dos conteúdos da disciplina são adequadas? |
| 16 | `DISCIPLINA` | Há diversidade e compatibilidade dos instrumentos de avaliação (…)? |
| 17 | `PROFESSOR` | O docente proporciona os resultados de avaliações como um momento formativo para os discentes? |
| 18 | `DISCIPLINA` | Como você se avalia com a aprendizagem decorrente da disciplina? |
| 19 | `PROFESSOR` | Se você tiver que fazer outra disciplina com esse professor, qual seria seu grau de satisfação? |

**Todas de dimensão 2.** É o núcleo didático-pedagógico — e é exatamente o que as regras
2 e 3 do usuário pedem: perguntas padrão a todos os formulários (Q1–Q9, Q20–Q58) e
perguntas destinadas ao professor daquela disciplina (Q10–Q19).

Em 2025.2 o sufixo era digitado à mão no título da pergunta:

```
O docente domina o conteúdo e está atualizado?   (Bioestatística - Pedro)
O docente domina o conteúdo e está atualizado?   (Bioquímica- Preleção - Linda)
O docente domina o conteúdo e está atualizado?   (Bioquímica- Prática -  Victória)
```

No novo sistema esse rótulo vem da `oferta`, já conciliada (RN-13) — acaba o risco de a
mesma disciplina virar duas por erro de digitação.

### 2.2 Os três instrumentos institucionais

Não são vinculados a turma nem a oferta; um de cada por período letivo.
O de **comunidade** é o ponto fraco herdado: 3 perguntas, todas da dimensão 4, e nenhuma
resposta em 2025.2 — ver Anexo B §B.5.

## 3. Aplicação: `TODAS` vs `ESPECIFICA` (RN-20)

Só perguntas de `bloco IN (DISCIPLINA, PROFESSOR)` admitem `ESPECIFICA` — são as únicas
que se repetem por oferta.

- `TODAS` — o caso comum. Uma pergunta `PROFESSOR/TODAS` entra em **todos** os blocos de
  matéria, nos 17 formulários (136 vínculos oferta↔turma em 2026.2).
- `ESPECIFICA` — entra apenas nas ofertas cujo alvo consta em `pergunta_vinculo`:
  - vínculo `DISCIPLINA:12` → só naquela disciplina;
  - vínculo `CURSO:3` → em todas as disciplinas daquele curso;
  - vínculo `PROFESSOR:7` → só quando aquele professor for avaliado.

Exemplos reais:
- "O laboratório dispunha dos reagentes necessários?" → bloco `DISCIPLINA`, `ESPECIFICA`,
  vinculada a `Práticas Biomédicas - Química` e `Toxicologia`. Dimensão **7**.
  ⚠️ É uma pergunta **nova**, fora do Anexo B — só entra com aval da CPA, e não terá
  comparativo com 2025.2.
- "As atividades de extensão foram bem articuladas com o conteúdo?" → `DISCIPLINA`,
  `ESPECIFICA`, vinculada às disciplinas de Caso Problematizador. Dimensão **2**.
- "A prática hospitalar foi bem supervisionada?" → `DISCIPLINA`, `ESPECIFICA`,
  vinculada a `Instrumentos Básicos de Enfermagem`. Dimensão **2**.

---

## 4. Algoritmo de montagem

```python
def montar(formulario) -> list[FormularioPergunta]:
    itens, ordem = [], 0
    ti = formulario.tipo_instrumento

    if ti == DISCENTE_TURMA:
        # 1) bloco institucional — 48 perguntas, UMA vez
        for p in perguntas(tipo_instrumento=ti, bloco=INSTITUCIONAL, ativo=True,
                           order_by=(ordem_exibicao, codigo)):
            ordem += 1
            itens.append(snapshot(p, oferta=None, ordem=ordem))

        # 2) um bloco por oferta avaliável da turma — 10 perguntas cada
        ofertas = [o for o in formulario.turma.ofertas if o.avaliavel and o.ativo]
        ofertas.sort(key=lambda o: (slugificar(o.disciplina.nome),
                                    slugificar(o.professor.nome_exibicao), o.id))  # RN-23
        for oferta in ofertas:
            for bloco in (PROFESSOR, DISCIPLINA):
                for p in perguntas(tipo_instrumento=ti, bloco=bloco, ativo=True,
                                   order_by=(ordem_exibicao, codigo)):
                    if p.aplicacao == TODAS or vinculo_casa(p, oferta):
                        ordem += 1
                        itens.append(snapshot(p, oferta=oferta, ordem=ordem))
    else:
        # docente, técnico-administrativo, comunidade
        for p in perguntas(tipo_instrumento=ti, ativo=True,
                           order_by=(dimensao.eixo.numero, dimensao.numero, ordem_exibicao, codigo)):
            ordem += 1
            itens.append(snapshot(p, oferta=None, ordem=ordem))
    return itens


def snapshot(p, oferta, ordem) -> FormularioPergunta:
    return FormularioPergunta(
        pergunta_id=p.id, codigo=p.codigo,                   # identidade entre ciclos
        equivalencia_id=p.equivalencia_id,               # identidade entre segmentos
        versao_texto=p.versao_texto,
        dimensao_id=p.dimensao_id,                           # dimensão COPIADA — RN-26
        oferta_id=oferta.id if oferta else None, bloco=p.bloco,
        texto_snapshot=p.texto, tipo_snapshot=p.tipo,
        rotulo_oferta=f"{oferta.disciplina.nome} · Prof. {oferta.professor.nome_exibicao}"
                      if oferta else None,
        obrigatoria_snapshot=p.obrigatoria, ordem=ordem)
```

**Garantias:**
- Determinístico: mesma entrada ⇒ mesma ordem (RN-23).
- `codigo`, `equivalencia_id` e `versao_texto` preservados no snapshot: são as chaves
  de comparação entre ciclos e entre segmentos (§5.1). **Nunca** se compara por texto.
- `rotulo_oferta` substitui o sufixo `(Disciplina - Professor)` que era digitado à mão.
- Instrumentos institucionais agrupados por eixo e dimensão.

## 5. Seed do banco — **use o Anexo B**

O banco não é proposto por esta especificação: são as **163 perguntas oficiais da CPA**,
extraídas de `historico/dimensoes.xlsx`. Estão em `anexos/B_banco_perguntas_cpa.md`
e `anexos/B_banco_perguntas_cpa.json`, com número, dimensão, bloco e questionário.

Cada pergunta carrega `codigo` (1–163) e `equivalencia_id` — é o que permite ao
relatório dizer *"Q11 subiu de 81,5% para 84,2% entre 2025.2 e 2026.2"* e
*"na equivalência 1, discentes deram 72,4% e docentes 81,2%"*. Ver §5.1.

### Escala
`LIKERT_5`: `1 · 2 · 3 · 4 · 5`. O ciclo 2025.2 usou exatamente essa escala
(distribuição real: 12.732 notas 5, 3.134 notas 4, 2.519 notas 3, 945 notas 2, 2.179 notas 1).

⚠️ **O instrumento de 2025.2 não tinha opção "Não sei responder".** Introduzi-la muda a
base de cálculo do ISG e quebra a comparabilidade. Decisão da CPA — ver D-6 no doc 01.

## 5.1 ⭐ Identidade das perguntas — a regra que sustenta todo cruzamento

Em 2025.2 o cruzamento era **por texto**, e 155 das 163 perguntas têm texto repetido em
mais de um questionário. O resultado misturava segmentos (Anexo B §B.5). A correção são
dois identificadores estáveis.

### `codigo` — a mesma pergunta ao longo dos anos

Inteiro atribuído **uma vez**, **nunca renumerado, nunca reutilizado**.
Seed: 1–163 do ciclo 2025.2; próximo livre **164**.

| Evento | O que fazer com o código |
|---|---|
| Pergunta nova | próximo livre (164, 165…) — **não** encaixe no bloco do segmento |
| Pergunta removida | código fica **vago para sempre** |
| Correção de grafia/pontuação | **mesmo** código, `versao_texto += 1` |
| Mudança de sentido | **novo** código; o antigo vira `ativo = false` |
| Pergunta movida de segmento | **novo** código no segmento de destino |

> **O teste decisivo, e é só um:** *as respostas de 2025.2 e de 2026 podem entrar na mesma
> média?* Sim → mesmo código. Não → código novo. Na dúvida, código novo: perder um
> comparativo é reparável, somar duas perguntas diferentes não.

### `equivalencia_id` — a mesma pergunta entre segmentos

**67 grupos** cobrindo as 163 perguntas. Permite a comparação entre públicos que o SINAES
espera, feita de propósito:

```
equivalencia_id = 1  "Você conhece o PDI da FPM?"
    ├─ codigo   1  DISCENTE                 ISG 72,4%
    ├─ codigo  59  DOCENTE                  ISG 81,2%
    └─ codigo 119  TECNICO_ADMINISTRATIVO   ISG 68,9%
```

Regra de integridade: **todos os membros de um grupo têm a mesma `dimensao_id`.**
Verificado no ciclo 2025.2 — zero divergências.

### O que o sistema nunca faz

- ❌ casar pergunta por texto, em qualquer etapa
- ❌ renumerar códigos para "arrumar" os blocos
- ❌ reaproveitar o código de uma pergunta desativada
- ❌ alterar o `codigo` no snapshot de um formulário já publicado

## 6. ⚠️ Tamanho do formulário — o risco central deste desenho

Com o banco real e a grade 2026.2:

| Turma | Ofertas | Perguntas |
|---|---|---|
| Biomedicina · Noturno · 6º período | 12 | **168** |
| Biomedicina · Noturno · 2º / 4º período | 10 | 148 |
| GTI · Noturno · 4º período | 5 | 98 |
| Enfermagem · Noturno · 8º período | 4 | **88** |
| **Média** | **8,1** | **129** |

Em 2025.2 isso funcionou — 166 respostas discentes com formulários de até 161 colunas.
Mas é longo, e o abandono no meio não aparece nos dados (só os envios completos chegam).

**Mitigações obrigatórias no frontend** (doc 07):
- Uma tela por bloco: o institucional paginado por dimensão, e **uma tela por matéria**.
- Barra de progresso `Matéria 4 de 10` e rascunho em `localStorage`.
- `LIMITE_ALERTA_PERGUNTAS` (padrão **150**) avisa o admin na geração.

**Alternativa registrada, não adotada:** separar o bloco institucional em um formulário
próprio (17 institucionais + 102 por matéria = 119 QRs). Reduz cada formulário a 48 ou 10
perguntas, mas multiplica por 7 a logística de aplicação em sala. Só vale se a adesão cair.

## 6. Edição do banco — o que é permitido

| Situação | Permitido? |
|---|---|
| Criar, editar, desativar, reordenar pergunta | Sempre |
| Editar pergunta já usada em formulário `PUBLICADO` | Sim — **não afeta** o publicado (snapshot, RN-26) |
| Reclassificar a dimensão de pergunta já usada | Sim — vale só para formulários futuros |
| Excluir fisicamente pergunta já usada | **Não.** Só `ativo = false` |
| Alterar `tipo` de pergunta já usada | **Não.** Desative e crie outra — invalidaria a agregação |
| Alterar o `codigo` de qualquer pergunta | **Nunca.** É a identidade (§5.1) |
| Reutilizar código de pergunta desativada | **Nunca.** Somaria perguntas diferentes |
| Mover pergunta entre instrumentos após publicação | **Não.** Crie uma nova no instrumento de destino |


