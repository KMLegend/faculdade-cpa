# Anexo B — Banco de perguntas oficial da CPA

> **Fonte primária:** `historico/dimensoes.xlsx` (mapeamento questão→dimensão→questionário)
> e `historico/consolidado_cpa.xlsx` (193 respostas do ciclo 2024).
> Substitui integralmente o seed sugerido em `04_banco_de_perguntas.md` §5.

## B.1 Estrutura: 163 questões, 4 questionários

| Questionário | Segmento | Nº | Questões | Respostas 2024 |
|---|---|---|---|---|
| DISCENTES | `DISCENTE` | 1–58 | 58 | 166 |
| DOCENTES | `DOCENTE` | 59–118 | 60 | 16 |
| TÉCNICOS_ADMINISTRATIVOS | `TECNICO_ADMINISTRATIVO` | 119–160 | 42 | 11 |
| COMUNIDADE | `COMUNIDADE` | 161–163 | 3 | 0 ⚠️ nenhuma |

> **A numeração é contínua entre os 4 questionários** — não há lacunas nem duplicatas.
> Correção de leitura anterior: a Q68 (`O docente apresenta o plano de ensino…`) **não é
> duplicata** da Q10 — é a versão do questionário DOCENTES da mesma pergunta.

## B.2 Cobertura dimensão × questionário

| Eixo | Dim. | Nome | Disc. | Doc. | Téc. | Com. |
|---|---|---|---|---|---|---|
| 1 | **8** | Planejamento e Avaliação | 5 | 4 | 4 | — |
| 2 | **1** | Missão e Plano de Desenvolvimento Institucional | 4 | 4 | 4 | — |
| 2 | **3** | Responsabilidade Social da Instituição | 6 | 6 | 5 | — |
| 3 | **2** | Políticas para o Ensino, a Pesquisa e a Extensão | 19 | 18 | — | — |
| 3 | **4** | Comunicação com a Sociedade | 3 | 3 | 4 | 3 |
| 3 | **9** | Política de Atendimento aos Discentes | 5 | — | — | — |
| 4 | **5** | Políticas de Pessoal | — | 7 | 7 | — |
| 4 | **6** | Organização e Gestão da Instituição | 5 | 5 | 5 | — |
| 4 | **10** | Sustentabilidade Financeira | — | 2 | 2 | — |
| 5 | **7** | Infraestrutura Física | 11 | 11 | 11 | — |

**Lacunas reais do instrumento atual, a decidir pela CPA:**

- Dimensão **5** (Políticas de Pessoal) e **10** (Sustentabilidade): não há questão para discentes — correto, não é percepção deles.
- Dimensão **9** (Atendimento aos Discentes): só no questionário discente.
- Dimensão **2** (Ensino/Pesquisa/Extensão): ausente no técnico-administrativo.
- **COMUNIDADE tem apenas 3 questões, todas da dimensão 4**, e **nenhuma resposta em 2024**.
  É o instrumento mais frágil do conjunto — ver B.5.

## B.3 ⭐ Questionário DISCENTES — a estrutura que o sistema automatiza

São **58 questões**, divididas em dois comportamentos distintos:

### Bloco INSTITUCIONAL — 48 questões, respondidas **uma vez**

Q1–Q9 e Q20–Q58.

### Bloco POR MATÉRIA — 10 questões, repetidas para **cada** `Disciplina | Professor`

| Nº | Bloco | Questão |
|---|---|---|
| 10 | `PROFESSOR` | O docente apresenta o plano de ensino da disciplina de forma sistematizada no início do semestre? |
| 11 | `PROFESSOR` | O docente domina o conteúdo e está atualizado? |
| 12 | `PROFESSOR` | O docente tem bom relacionamento com os discentes e é disponível para o esclarecimento de dúvidas? |
| 13 | `PROFESSOR` | O docente é pontual e assíduo em suas funções? |
| 14 | `PROFESSOR` | A didática do docente contribui para a aprendizagem? |
| 15 | `DISCIPLINA` | A carga horária e organização dos conteúdos da disciplina são adequadas? |
| 16 | `DISCIPLINA` | Há diversidade e compatibilidade dos instrumentos de avaliação (avaliações bimestrais, trabalhos, atividades onlines, atividades interdisciplinares semanais/quinzenais etc)? |
| 17 | `PROFESSOR` | O docente proporciona os resultados de avaliações como um momento formativo para os discentes? |
| 18 | `DISCIPLINA` | Como você se avalia com a aprendizagem decorrente da disciplina? |
| 19 | `PROFESSOR` | Se você tiver que fazer outra disciplina com esse professor, qual seria seu grau de satisfação? |

No ciclo 2024 essas questões apareciam no Google Forms com o sufixo literal
`(Disciplina - Professor)`:

```
O docente domina o conteúdo e está atualizado?   (Bioestatística - Pedro)
O docente domina o conteúdo e está atualizado?   (Bioquímica- Preleção - Linda)
O docente domina o conteúdo e está atualizado?   (Bioquímica- Prática -  Victória)
O docente é pontual e assíduo em suas funções?   (Bioestatística - Pedro)
```

**É exatamente a chave `Disciplina | Professor`.** O que era montado à mão em 17 Google
Forms passa a ser gerado da grade — é o coração deste projeto.

Conferência aritmética no formulário *Educação Física Matutino* (2024):
`48 institucionais + 10 × 11 matérias + 2 demográficas + 1 comentário = 161 colunas` ✓

## B.4 ⭐ Fórmula do ISG — **RESOLVIDA**

```
ISG = (média das respostas − 1) / 4          # escala 1–5 normalizada para 0..1
ISG % = ISG × 100                             # formato do painel: 0.00%
```

Deduzida empiricamente comparando `consolidado_cpa.xlsx` com os valores publicados no
Power BI. **Duas correspondências exatas**, em escopos diferentes:

| Questão | Média 2024 | `(m−1)/4` | Publicado no BI |
|---|---|---|---|
| Q68 (docentes, coluna única) | 4,8125 | **95,31%** | **95,31%** |
| Q49 (todos os segmentos) | 4,4093 | **85,23%** | **85,23%** |

As demais fórmulas testadas foram descartadas: `média/5` erra 5,4 pp em média,
`% de 4 e 5` erra 3,0 pp, `% de 5` erra 16,8 pp.

Faixas de cor do painel (do `Report/Layout` do `.pbix`): **0,25 · 0,46 · 0,72**.

## B.5 ⚠️ Problemas encontrados no pipeline de 2024

| # | Problema | Consequência | Como o novo sistema resolve |
|---|---|---|---|
| 1 | O Power BI casa questão com dimensão **pelo texto**, não por identificador | A mesma frase existe em até 3 questionários com números diferentes (ex.: Q28/Q85/Q127). O ISG histórico **mistura segmentos** de forma inconsistente — verificado: Q49 só fecha somando os 3 segmentos, Q68 só fecha isolando docentes | `formulario_pergunta_id` como chave; o segmento é coluna própria |
| 2 | 17 Google Forms montados à mão, um por turma | Retrabalho a cada semestre; o `main.py` precisa de um dicionário com 17 IDs fixos | Geração automática a partir da grade |
| 3 | `pd.concat` de formulários com colunas distintas | Planilha esparsa de **946 colunas** para 163 questões reais | Modelo relacional normalizado |
| 4 | Sufixo `(Disciplina - Professor)` digitado à mão no título da pergunta | Erros de grafia viram disciplinas diferentes no relatório | Vem da `oferta`, com conciliação (RN-13) |
| 5 | Questionário da comunidade com 3 questões e **zero respostas** | Dimensões 1, 2 e 3 sem a visão externa que o SINAES pede | QR público + cartaz; ampliar o instrumento |
| 6 | Sem anonimato verificável (Google Forms coleta e-mail se configurado) | Risco de viés na resposta | Anonimato estrutural (RN-31) |


## B.6 ⭐ Identidade das perguntas — `codigo` e `equivalencia_id`

Em 2024 o cruzamento era feito **pelo texto da pergunta**. Como 155 das 163 perguntas
têm texto repetido em mais de um questionário, o resultado misturava segmentos de forma
imprevisível (§B.5). Duas colunas novas resolvem isso de forma definitiva.

### `codigo` — identidade da pergunta ao longo dos anos

Inteiro estável, atribuído **uma vez**, **nunca renumerado, nunca reutilizado**.
O seed usa a numeração de 2024 (1–163); o próximo livre é **164**.

| Regra | Porquê |
|---|---|
| Pergunta nova recebe o próximo código livre (164, 165…), **não** um número no bloco do segmento | Preservar identidade vale mais que a estética dos blocos 1–58 / 59–118 |
| Pergunta removida deixa o código **vago para sempre** | Reutilizar faria o relatório somar duas perguntas diferentes |
| Correção de grafia mantém o código e incrementa `versao_texto` | As respostas continuam somáveis |
| Mudança de **sentido** exige código novo + desativar o antigo | Se as respostas de 2024 e 2026 não podem ser somadas, é outra pergunta |

> **O teste decisivo:** *as respostas dos dois ciclos podem ser somadas na mesma média?*
> Sim → mesmo código. Não → código novo.

### `equivalencia_id` — a mesma pergunta entre segmentos

**67 grupos** cobrem as 163 perguntas. É o que permite comparar segmentos
**de propósito**, em vez de por acidente de texto:

```
Q1  (discente)  Você conhece o PDI da FPM?   →  ISG 72,4%
Q59 (docente)   mesma pergunta               →  ISG 81,2%   equivalencia_id = 1
Q119(técnico)   mesma pergunta               →  ISG 68,9%
```

- 8 perguntas são **exclusivas** de um segmento
- 27 grupos cobrem 2 segmentos
- 29 grupos cobrem 3 segmentos
- 3 grupos cobrem 4 ou mais

✅ **Nenhum grupo tem dimensão divergente entre segmentos** — o mapeamento de 2024 é
consistente nesse ponto. É um bom sinal sobre a qualidade do `dimensoes.xlsx`.

### ⚠️ Uma duplicata real encontrada

Os códigos **[24, 29, 81, 86, 123]** compartilham o mesmo texto:

> *"As atividades de extensão atendem às necessidades da comunidade local?"*

Os segmentos ['DISCENTES', 'DOCENTES'] trazem a pergunta **duas vezes no mesmo
questionário** (discente: Q24 e Q29; docente: Q81 e Q86). No `consolidado_cpa.xlsx`
isso aparece como a coluna `…comunidade local?` e `…comunidade local?.1`.

**Decisão necessária da CPA:** manter as duas (e o ISG de cada uma fica diluído em
metade das respostas) ou consolidar em uma, desativando o código duplicado.
Recomendo **desativar Q29 e Q86**, mantendo Q24 e Q81.

### A cadeia completa de identificadores

```
resposta no Google  ──►  google_question_id      (id do Google, por formulário)
                          │
                          ▼
                    formulario_pergunta          (o snapshot daquele ciclo)
                          │
            ┌─────────────┼──────────────┬───────────────┐
            ▼             ▼              ▼               ▼
       pergunta       equivalencia    dimensao        oferta
       .codigo           _id            _id            _id
            │             │              │               │
     comparar entre  comparar entre   relatório      relatório por
        CICLOS         SEGMENTOS       SINAES         professor
```

**Nenhum elo dessa cadeia usa texto.** É a diferença entre o cruzamento de 2024 e este.

## B.7 As 163 questões

### DISCENTES — `DISCENTE`

| Nº | Dim. | Bloco | Questão |
|---|---|---|---|
| 1 | 1 | — | Você conhece o Plano de Desenvolvimento Institucional (PDI) da FPM |
| 2 | 1 | — | Existe uma formulação clara dos objetivos, missão e valores da FPM? |
| 3 | 1 | — | Existe coerência entre as ações praticadas pela FPM e o proposto em sua missão? |
| 4 | 1 | — | As ações praticadas pela FPM favorecem a indissociabilidade entre Ensino, Pesquisa e Extensão? |
| 5 | 2 | — | O coordenador está empenhado no desenvolvimento, na busca de soluções para os problemas e na qualidade do curso? |
| 6 | 2 | — | O coordenador do curso relaciona-se bem com os discentes ou docentes? |
| 7 | 2 | — | O Projeto Pedagógico do Curso está sendo devidamente desenvolvido? |
| 8 | 2 | — | O curso oferece atividades de prática profissional ou acadêmica compatíveis com o proposto no Projeto Pedagógico do Curso? |
| 9 | 2 | — | Os membros do NDE do curso são atuantes? |
| 10 | 2 | **POR MATÉRIA** | O docente apresenta o plano de ensino da disciplina de forma sistematizada no início do semestre? |
| 11 | 2 | **POR MATÉRIA** | O docente domina o conteúdo e está atualizado? |
| 12 | 2 | **POR MATÉRIA** | O docente tem bom relacionamento com os discentes e é disponível para o esclarecimento de dúvidas? |
| 13 | 2 | **POR MATÉRIA** | O docente é pontual e assíduo em suas funções? |
| 14 | 2 | **POR MATÉRIA** | A didática do docente contribui para a aprendizagem? |
| 15 | 2 | **POR MATÉRIA** | A carga horária e organização dos conteúdos da disciplina são adequadas? |
| 16 | 2 | **POR MATÉRIA** | Há diversidade e compatibilidade dos instrumentos de avaliação (avaliações bimestrais, trabalhos, atividades onlines, atividades interdisciplinares semanais/quinzenais etc)? |
| 17 | 2 | **POR MATÉRIA** | O docente proporciona os resultados de avaliações como um momento formativo para os discentes? |
| 18 | 2 | **POR MATÉRIA** | Como você se avalia com a aprendizagem decorrente da disciplina? |
| 19 | 2 | **POR MATÉRIA** | Se você tiver que fazer outra disciplina com esse professor, qual seria seu grau de satisfação? |
| 20 | 2 | — | Você já envolveu com alguma atividade de pesquisa ou extensão? |
| 21 | 2 | — | As atividades de pesquisa são integradas ao ensino e à extensão? |
| 22 | 2 | — | A relação entre orientadores e discentes interessados em desenvolver projetos de pesquisa é adequada? |
| 23 | 2 | — | O programa de bolsas de iniciação científica é adequado? |
| 24 | 3 | — | As atividades de extensão atendem às necessidades da comunidade local? |
| 25 | 3 | — | A política institucional favorece a inclusão de pessoas com deficiências (PCDs)? |
| 26 | 3 | — | Você participa de algum projeto de extensão da FPM? |
| 27 | 3 | — | Existem ações que favoreçam a inclusão e permanência de discentes em situação econômica desfavorecida na FPM? |
| 28 | 3 | — | As atividades institucionais em interação com o meio social (Educação, Saúde, Lazer, Cultura, Esporte, Meio Ambiente, Cidadania, dentre outros) são efetivas? |
| 29 | 3 | — | As atividades de extensão atendem às necessidades da comunidade local? |
| 30 | 4 | — | A comunidade externa tem conhecimento das atividades desenvolvidas pela FPM através das mídias? |
| 31 | 4 | — | A ouvidoria funciona segundo os padrões de qualidade claramente estabelecidos? |
| 32 | 4 | — | Os registros e os resultados são efetivamente levados em consideração pelas instâncias acadêmicas e administrativas da FPM? |
| 33 | 6 | — | Você conhece o organograma administrativo da FPM? |
| 34 | 6 | — | Você conhece os procedimentos administrativos da FPM? |
| 35 | 6 | — | As informações sobre os procedimentos administrativos são de fácil acesso? |
| 36 | 6 | — | A direção atende aos anseios da comunidade acadêmica e administrativa? |
| 37 | 6 | — | Os diretores demonstram interesse pelas reivindicações e agem no sentido de atendê-las? |
| 38 | 7 | — | O campus oferece condições adequadas de facilidade de acesso e segurança? |
| 39 | 7 | — | O ambiente para as aulas é apropriado quanto à acústica, luminosidade, carteiras e ventilação? |
| 40 | 7 | — | Os equipamentos dos laboratórios de informática atendem as necessidades acadêmicas? |
| 41 | 7 | — | Os recursos instrucionais (projetor multimídia, TV, áudio, vídeo etc) atendem as necessidades acadêmicas? |
| 42 | 7 | — | Os laboratórios de ensino atendem as necessidades acadêmicas? |
| 43 | 7 | — | A cantina atende as necessidades da comunidade acadêmica e administrativa? |
| 44 | 7 | — | As instalações físicas atendem aos critérios de acessibilidade às pessoas com deficiência (PCD)? |
| 45 | 7 | — | Os serviços de limpeza são adequados? |
| 46 | 7 | — | Os serviços de biblioteca atendem aos anseios da comunidade acadêmica? |
| 47 | 7 | — | Os serviços do ambiente virtual são adequados? |
| 48 | 7 | — | Os serviços do estacionamento interno são adequados? |
| 49 | 8 | — | Você considera importante a realização da auto avaliação institucional pela CPA? |
| 50 | 8 | — | Você participou de alguma pesquisa de avaliação, por disciplina, conteúdo, professores, didática etc? |
| 51 | 8 | — | Houveram ações para implementar melhorias após os processos de avaliação? |
| 52 | 8 | — | Você tem acesso aos resultados dos processos avaliativos? |
| 53 | 8 | — | Qual seu grau de satisfação em ser aluno da FPM? |
| 54 | 9 | — | A faculdade oferece atendimento acadêmico e administrativo aos discentes? |
| 55 | 9 | — | O programa de estágio funciona adequadamente? |
| 56 | 9 | — | O sistema de registros acadêmicos funciona adequadamente? |
| 57 | 9 | — | Os discentes têm acesso ao núcleo de apoio psicopedagógico (NAP)? |
| 58 | 9 | — | Os programas de intercâmbio atendem a demanda acadêmica? |

### DOCENTES — `DOCENTE`

| Nº | Dim. | Bloco | Questão |
|---|---|---|---|
| 59 | 1 | — | Você conhece o Plano de Desenvolvimento Institucional (PDI) da FPM |
| 60 | 1 | — | Existe uma formulação clara dos objetivos, missão e valores da FPM? |
| 61 | 1 | — | Existe coerência entre as ações praticadas pela FPM e o proposto em sua missão? |
| 62 | 1 | — | As ações praticadas pela FPM favorecem a indissociabilidade entre Ensino, Pesquisa e Extensão? |
| 63 | 2 | — | O coordenador está empenhado no desenvolvimento, na busca de soluções para os problemas e na qualidade do curso? |
| 64 | 2 | — | O coordenador do curso relaciona-se bem com os discentes ou docentes? |
| 65 | 2 | — | O Projeto Pedagógico do Curso está sendo devidamente desenvolvido? |
| 66 | 2 | — | O curso oferece atividades de prática profissional ou acadêmica compatíveis com o proposto no Projeto Pedagógico do Curso? |
| 67 | 2 | — | Os membros do NDE do curso são atuantes? |
| 68 | 2 | — | O docente apresenta o plano de ensino da disciplina de forma sistematizada no início do semestre? |
| 69 | 2 | — | O docente domina o conteúdo e está atualizado? |
| 70 | 2 | — | O docente tem bom relacionamento com os discentes e é disponível para o esclarecimento de dúvidas? |
| 71 | 2 | — | O docente é pontual e assíduo em suas funções? |
| 72 | 2 | — | A didática do docente contribui para a aprendizagem? |
| 73 | 2 | — | A carga horária e organização dos conteúdos da disciplina são adequadas? |
| 74 | 2 | — | Há diversidade e compatibilidade dos instrumentos de avaliação (avaliações bimestrais, trabalhos, atividades onlines, atividades interdisciplinares semanais/quinzenais etc)? |
| 75 | 2 | — | O docente proporciona os resultados de avaliações como um momento formativo para os discentes? |
| 76 | 2 | — | Como você se avalia com a aprendizagem decorrente da disciplina? |
| 77 | 2 | — | Você já envolveu com alguma atividade de pesquisa ou extensão? |
| 78 | 2 | — | As atividades de pesquisa são integradas ao ensino e à extensão? |
| 79 | 2 | — | A relação entre orientadores e discentes interessados em desenvolver projetos de pesquisa é adequada? |
| 80 | 2 | — | O programa de bolsas de iniciação científica é adequado? |
| 81 | 3 | — | As atividades de extensão atendem às necessidades da comunidade local? |
| 82 | 3 | — | A política institucional favorece a inclusão de pessoas com deficiências (PCDs)? |
| 83 | 3 | — | Você participa de algum projeto de extensão da FPM? |
| 84 | 3 | — | Existem ações que favoreçam a inclusão e permanência de discentes em situação econômica desfavorecida na FPM? |
| 85 | 3 | — | As atividades institucionais em interação com o meio social (Educação, Saúde, Lazer, Cultura, Esporte, Meio Ambiente, Cidadania, dentre outros) são efetivas? |
| 86 | 3 | — | As atividades de extensão atendem às necessidades da comunidade local? |
| 87 | 4 | — | A comunidade externa tem conhecimento das atividades desenvolvidas pela FPM através das mídias? |
| 88 | 4 | — | A ouvidoria funciona segundo os padrões de qualidade claramente estabelecidos? |
| 89 | 4 | — | Os registros e os resultados são efetivamente levados em consideração pelas instâncias acadêmicas e administrativas da FPM? |
| 90 | 5 | — | As condições de trabalho oferecidas pela FPM são adequadas? |
| 91 | 5 | — | O número de docentes é suficiente para atender satisfatoriamente a FPM? |
| 92 | 5 | — | O número de técnico-administrativos é suficiente para atender satisfatoriamente a FPM? |
| 93 | 5 | — | Os servidores recebem apoio para a sua qualificação? |
| 94 | 5 | — | A FPM possibilita o crescimento profissional dos servidores? |
| 95 | 5 | — | Há organização, por parte dos servidores, no desempenho de suas atividades? |
| 96 | 5 | — | Os servidores desempenham suas tarefas com responsabilidade? |
| 97 | 6 | — | Você conhece o organograma administrativo da FPM? |
| 98 | 6 | — | Você conhece os procedimentos administrativos da FPM? |
| 99 | 6 | — | As informações sobre os procedimentos administrativos são de fácil acesso? |
| 100 | 6 | — | A direção atende aos anseios da comunidade acadêmica e administrativa? |
| 101 | 6 | — | Os diretores demonstram interesse pelas reivindicações e agem no sentido de atendê-las? |
| 102 | 7 | — | O campus oferece condições adequadas de facilidade de acesso e segurança? |
| 103 | 7 | — | O ambiente para as aulas é apropriado quanto à acústica, luminosidade, carteiras e ventilação? |
| 104 | 7 | — | Os equipamentos dos laboratórios de informática atendem as necessidades acadêmicas? |
| 105 | 7 | — | Os recursos instrucionais (projetor multimídia, TV, áudio, vídeo etc) atendem as necessidades acadêmicas? |
| 106 | 7 | — | Os laboratórios de ensino atendem as necessidades acadêmicas? |
| 107 | 7 | — | A cantina atende as necessidades da comunidade acadêmica e administrativa? |
| 108 | 7 | — | As instalações físicas atendem aos critérios de acessibilidade às pessoas com deficiência (PCD)? |
| 109 | 7 | — | Os serviços de limpeza são adequados? |
| 110 | 7 | — | Os serviços de biblioteca atendem aos anseios da comunidade acadêmica? |
| 111 | 7 | — | Os serviços do ambiente virtual são adequados? |
| 112 | 7 | — | Os serviços do estacionamento interno são adequados? |
| 113 | 8 | — | Você considera importante a realização da auto avaliação institucional pela CPA? |
| 114 | 8 | — | Você participou de alguma pesquisa de avaliação, por disciplina, conteúdo, professores, didática etc? |
| 115 | 8 | — | Houveram ações para implementar melhorias após os processos de avaliação? |
| 116 | 8 | — | Você tem acesso aos resultados dos processos avaliativos? |
| 117 | 10 | — | Os recursos materiais disponíveis são adequados as necessidades dos cursos? |
| 118 | 10 | — | A FPM dispõe de recursos para realização de pesquisa, ensino e extensão? |

### TÉCNICOS_ADMINISTRATIVOS — `TECNICO_ADMINISTRATIVO`

| Nº | Dim. | Bloco | Questão |
|---|---|---|---|
| 119 | 1 | — | Você conhece o Plano de Desenvolvimento Institucional (PDI) da FPM |
| 120 | 1 | — | Existe uma formulação clara dos objetivos, missão e valores da FPM? |
| 121 | 1 | — | Existe coerência entre as ações praticadas pela FPM e o proposto em sua missão? |
| 122 | 1 | — | As ações praticadas pela FPM favorecem a indissociabilidade entre Ensino, Pesquisa e Extensão? |
| 123 | 3 | — | As atividades de extensão atendem às necessidades da comunidade local? |
| 124 | 3 | — | A política institucional favorece a inclusão de pessoas com deficiências (PCDs)? |
| 125 | 3 | — | Você participa de algum projeto de extensão da FPM? |
| 126 | 3 | — | Existem ações que favoreçam a inclusão e permanência de discentes em situação econômica desfavorecida na FPM? |
| 127 | 3 | — | As atividades institucionais em interação com o meio social (Educação, Saúde, Lazer, Cultura, Esporte, Meio Ambiente, Cidadania, dentre outros) são efetivas? |
| 128 | 4 | — | A comunidade externa tem conhecimento das atividades desenvolvidas pela FPM através das mídias? |
| 129 | 4 | — | As atividades de divulgação da FPM são eficientes? |
| 130 | 4 | — | A ouvidoria funciona segundo os padrões de qualidade claramente estabelecidos? |
| 131 | 4 | — | Os registros e os resultados são efetivamente levados em consideração pelas instâncias acadêmicas e administrativas da FPM? |
| 132 | 5 | — | As condições de trabalho oferecidas pela FPM são adequadas? |
| 133 | 5 | — | O número de docentes é suficiente para atender satisfatoriamente a FPM? |
| 134 | 5 | — | O número de técnico-administrativos é suficiente para atender satisfatoriamente a FPM? |
| 135 | 5 | — | Os servidores recebem apoio para a sua qualificação? |
| 136 | 5 | — | A FPM possibilita o crescimento profissional dos servidores? |
| 137 | 5 | — | Há organização, por parte dos servidores, no desempenho de suas atividades? |
| 138 | 5 | — | Os servidores desempenham suas tarefas com responsabilidade? |
| 139 | 6 | — | Você conhece o organograma administrativo da FPM? |
| 140 | 6 | — | Você conhece os procedimentos administrativos da FPM? |
| 141 | 6 | — | As informações sobre os procedimentos administrativos são de fácil acesso? |
| 142 | 6 | — | A direção atende aos anseios da comunidade acadêmica e administrativa? |
| 143 | 6 | — | Os diretores demonstram interesse pelas reivindicações e agem no sentido de atendê-las? |
| 144 | 7 | — | O campus oferece condições adequadas de facilidade de acesso e segurança? |
| 145 | 7 | — | O ambiente para as aulas é apropriado quanto à acústica, luminosidade, carteiras e ventilação? |
| 146 | 7 | — | Os equipamentos dos laboratórios de informática atendem as necessidades acadêmicas? |
| 147 | 7 | — | Os recursos instrucionais (projetor multimídia, TV, áudio, vídeo etc) atendem as necessidades acadêmicas? |
| 148 | 7 | — | Os laboratórios de ensino atendem as necessidades acadêmicas? |
| 149 | 7 | — | A cantina atende as necessidades da comunidade acadêmica e administrativa? |
| 150 | 7 | — | As instalações físicas atendem aos critérios de acessibilidade às pessoas com deficiência (PCD)? |
| 151 | 7 | — | Os serviços de limpeza são adequados? |
| 152 | 7 | — | Os serviços de biblioteca atendem aos anseios da comunidade acadêmica? |
| 153 | 7 | — | Os serviços do ambiente virtual são adequados? |
| 154 | 7 | — | Os serviços do estacionamento interno são adequados? |
| 155 | 8 | — | Você considera importante a realização da auto avaliação institucional pela CPA? |
| 156 | 8 | — | Você participou de alguma pesquisa de avaliação, por disciplina, conteúdo, professores, didática etc? |
| 157 | 8 | — | Houveram ações para implementar melhorias após os processos de avaliação? |
| 158 | 8 | — | Você tem acesso aos resultados dos processos avaliativos? |
| 159 | 10 | — | Os recursos materiais disponíveis são adequados as necessidades dos cursos? |
| 160 | 10 | — | A FPM dispõe de recursos para realização de pesquisa, ensino e extensão? |

### COMUNIDADE — `COMUNIDADE`

| Nº | Dim. | Bloco | Questão |
|---|---|---|---|
| 161 | 4 | — | A comunidade externa tem conhecimento das atividades desenvolvidas pela FPM através das mídias? |
| 162 | 4 | — | A ouvidoria funciona segundo os padrões de qualidade claramente estabelecidos? |
| 163 | 4 | — | Os registros e os resultados são efetivamente levados em consideração pelas instâncias acadêmicas e administrativas da FPM? |

