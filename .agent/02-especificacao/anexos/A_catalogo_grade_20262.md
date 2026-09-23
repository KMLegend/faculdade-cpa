# Anexo A — Catálogo extraído de `horario 20262.xlsx`

> Gerado por script exploratório sobre o arquivo real, aplicando as regras de
> `03_importacao_da_grade_xlsx.md`. **É material de referência e fixture de teste,
> não verdade absoluta.** Tudo passa pela conciliação (RN-13) antes de virar registro.

**Resumo:** 17 turmas · 106 ofertas (102 avaliáveis, 4 sem turma) · 27 ofertas atendem mais de uma turma · **20 formulários** (17 de turma + 3 institucionais) · 137 vínculos oferta↔turma.

## A.1 As 17 turmas — chave `Curso + Turno + Período` (RN-04)

Repare em quantas colunas da planilha alimentam cada turma: é isso que a chave consolida.

| # | Turma | Módulo(s) | Rótulos na planilha | Colunas de origem |
|---|---|---|---|---|
| 1 | **Biomedicina · Matutino · 2º período** 🔗 | P | `Turma A`, `Turma B` | `Matutino (Ciclo básico)![4]`, `Matutino (Ciclo básico)![5]` |
| 5 | **Biomedicina · Matutino · 4º período** | Análises Biomédicas | `Sub - Turma A`, `Sub - Turma B` | `Biomedicina- Matutino![4]`, `Biomedicina- Matutino![5]` |
| 3 | **Educação Física · Matutino · 4º período** | EB-A | `Turma única` | `Educação Física_Matutino![4, 5]` |
| 2 | **Enfermagem · Matutino · 2º período** 🔗 | P | `Turma A`, `Turma B` | `Matutino (Ciclo básico)![4]`, `Matutino (Ciclo básico)![5]` |
| 4 | **Enfermagem · Matutino · 4º período** | — | `Sub - Turma A`, `Sub - Turma B` | `Enfermagem_Matutino![4]`, `Enfermagem_Matutino![5]` |
| 6 | **GTI · Matutino · 2º período** | I | `2 Período - Módulo I` | `GTI - Matutino![4]` |
| 9 | **Biomedicina · Noturno · 2º período** 🔗 | P | `Biomedicina - Turma A`, `Biomedicina Turma B` | `Ciclo Básico Integrado - Noturn![4]`, `Ciclo Básico Integrado - Noturn![5]` |
| 12 | **Biomedicina · Noturno · 4º período** | AB | `Turma A` | `Biomedicina Noturno![4]`, `Biomedicina Noturno![5]` |
| 13 | **Biomedicina · Noturno · 6º período** | CL | `Turma Única` | `Biomedicina Noturno![6]` |
| 11 | **Educação Física · Noturno · 3º período** 🔗 | M | `Educação Física - Turma Única` | `Ciclo Básico Integrado - Noturn![6]` |
| 16 | **Educação Física · Noturno · 4º período** | EB-A | `4º PER - Módulo EB-A` | `Educação Física - Noturno![4]` |
| 17 | **Educação Física · Noturno · 8º período** | EB-E | `8º PER - Módulo EB-E` | `Educação Física - Noturno![5]` |
| 10 | **Enfermagem · Noturno · 2º período** 🔗 | P | `Biomedicina - Turma A`, `Biomedicina Turma B` | `Ciclo Básico Integrado - Noturn![4]`, `Ciclo Básico Integrado - Noturn![5]` |
| 14 | **Enfermagem · Noturno · 4º período** | de Instrumentos | `4º PER - Módulo de Instrumentos` | `Enfermagem - Noturno![4]` |
| 15 | **Enfermagem · Noturno · 8º período** | — | `8º PER - O cuidar nos Processos Clínicos` | `Enfermagem - Noturno![5]` |
| 7 | **GTI · Noturno · 2º período** | I | `2 Período - Módulo I` | `GTI - Noturno![4]` |
| 8 | **GTI · Noturno · 4º período** | IA | `4 Período - Módulo IA` | `GTI - Noturno![5]` |

🔗 = turma vinda de aba de ciclo básico, compartilhada com outro curso (RN-03).

## A.2 Ofertas que atendem mais de uma turma

27 das 106 ofertas. **Um único QR serve a todas as turmas listadas.**

| Oferta | Turmas |
|---|---|
| Bioestatística · **Sandra** (4) | Biomedicina · Matutino · 2º período<br>Enfermagem · Matutino · 2º período<br>Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Bioquímica · **Andrea** (4) | Biomedicina · Matutino · 2º período<br>Enfermagem · Matutino · 2º período<br>Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Fundamentos Filosóficos e Antropológicos Aplicados à Saúde · **Rogério** (4) | Biomedicina · Matutino · 2º período<br>Enfermagem · Matutino · 2º período<br>Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Práticas Biomédicas - Química · **Alexandre** (4) | Biomedicina · Matutino · 2º período<br>Enfermagem · Matutino · 2º período<br>Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Algoritmos e Lógica de Programação · **Rovilson** (2) | GTI · Matutino · 2º período<br>GTI · Noturno · 2º período |
| Anatomofisiologia Humana - Sistema Nervoso, urinário, repr · **Andrea** (2) | Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Anatomofisiologia Humana - Sistema Nervoso, urinário, repr · **Ivan** (2) | Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Anatomofisiologia Humana, Sistema Nervoso, Urinário. Repro · **Lisiane** (2) | Biomedicina · Matutino · 2º período<br>Enfermagem · Matutino · 2º período |
| Atletismo · **Ernesto** (2) | Educação Física · Matutino · 4º período<br>Educação Física · Noturno · 4º período |
| Bioética · **Rogério** (2) | Educação Física · Matutino · 4º período<br>Educação Física · Noturno · 4º período |
| Bioética e Deontologia · **Clayson** (2) | Biomedicina · Matutino · 4º período<br>Biomedicina · Noturno · 4º período |
| Biomedicina Estética · **Alexandre** (2) | Biomedicina · Matutino · 4º período<br>Biomedicina · Noturno · 4º período |
| Bioquímica · **Vanessa** (2) | Biomedicina · Matutino · 2º período<br>Enfermagem · Matutino · 2º período |
| Bioquímica · **Victória** (2) | Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Caso Problematizador e Avaliação Interdisciplinar Instrume · **Pedro** (2) | Enfermagem · Matutino · 4º período<br>Enfermagem · Noturno · 4º período |
| Caso Problematizador e Avaliação Interdisciplinar P · **Alexandre** (2) | Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Caso Problematizador e Avaliação Interdisciplinar P · **Isabela** (2) | Biomedicina · Matutino · 2º período<br>Enfermagem · Matutino · 2º período |
| Esportes de Raquete · **Ernesto** (2) | Educação Física · Matutino · 4º período<br>Educação Física · Noturno · 4º período |
| Fisiologia do Exercício I · **Linda** (2) | Educação Física · Matutino · 4º período<br>Educação Física · Noturno · 4º período |
| Gestão de Projetos em Tecnologia da Informação · **Rovilson** (2) | GTI · Matutino · 2º período<br>GTI · Noturno · 2º período |
| Histologia e Embriologia · **André** (2) | Biomedicina · Matutino · 2º período<br>Enfermagem · Matutino · 2º período |
| Histologia e Embriologia · **Victória** (2) | Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Imunologia · **Clayson** (2) | Biomedicina · Matutino · 2º período<br>Enfermagem · Matutino · 2º período |
| Imunologia · **Vanessa** (2) | Biomedicina · Noturno · 2º período<br>Enfermagem · Noturno · 2º período |
| Instrumentos Básicos de Enfermagem · **Luciene** (2) | Enfermagem · Matutino · 4º período<br>Enfermagem · Noturno · 4º período |
| Instrumentos Básicos de Enfermagem · **Pedro** (2) | Enfermagem · Matutino · 4º período<br>Enfermagem · Noturno · 4º período |
| Promoção da Saúde · **Régis** (2) | Enfermagem · Matutino · 4º período<br>Enfermagem · Noturno · 4º período |

## A.3 Ofertas sem turma — nascem `avaliavel = false` (RN-15)

| Oferta | Origem |
|---|---|
| Estágio Supervisionado I ou II · **Alexandre** | coluna de Estágio Supervisionado |
| Estágio Supervisionado I ou II · **Washington** | coluna de Estágio Supervisionado |
| Optativa I ou II - Endocrinologia laboratorial · **Roberpaulo** | coluna de Estágio Supervisionado |
| TCC 1 ou TCC 2 · **Clayson** | coluna de Estágio Supervisionado |

## A.4 Linhas que exigem decisão humana

| Flag | Qtd. | Ofertas |
|---|---|---|
| `DISCIPLINA_AMBIGUA_OU` | 4 | Estágio Supervisionado I ou II · Alexandre; Estágio Supervisionado I ou II · Washington; Optativa I ou II - Endocrinologia la · Roberpaulo; TCC 1 ou TCC 2 · Clayson |
| `SEM_PREFIXO_PROF` | 1 | Promoção da Saúde · Régis |

### Avisos da segmentação de turmas

| Tipo | Aba | Colunas | Motivo |
|---|---|---|---|
| `CICLO_BASICO_EXPANDIDO` | Matutino (Ciclo básico) | [4] | Coluna compartilhada — alunos de BIOMEDICINA, ENFERMAGEM no 2º período |
| `CICLO_BASICO_EXPANDIDO` | Matutino (Ciclo básico) | [5] | Coluna compartilhada — alunos de BIOMEDICINA, ENFERMAGEM no 2º período |
| `CICLO_BASICO_EXPANDIDO` | Ciclo Básico Integrado - Noturn | [4] | Coluna compartilhada — alunos de BIOMEDICINA, ENFERMAGEM no 2º período |
| `CICLO_BASICO_EXPANDIDO` | Ciclo Básico Integrado - Noturn | [5] | Coluna compartilhada — alunos de BIOMEDICINA, ENFERMAGEM no 2º período |
| `CICLO_BASICO_EXPANDIDO` | Ciclo Básico Integrado - Noturn | [6] | Coluna compartilhada — alunos de EDUCACAO_FISICA no 3º período |
| `COLUNA_NAO_E_TURMA` | Biomedicina Noturno | [7, 8] | Estágio supervisionado — gera oferta, não turma |

## A.5 Professores

Somente **primeiro nome** — não há sobrenome em nenhuma célula (RN-14).

| Nome | Ofertas | Observação |
|---|---|---|
| Alexandre | 7 |  |
| Andrea | 3 |  |
| André | 1 |  |
| Arissa | 2 |  |
| Carlos | 3 |  |
| Clayson | 5 |  |
| Diony | 2 |  |
| Ernesto | 2 |  |
| Isabela | 4 |  |
| Ivan | 8 |  |
| Jonas | 3 |  |
| Katiulcy | 1 | Só em observação administrativa (`Preceptor a contratar`) |
| Leonardo | 6 |  |
| Linda | 7 |  |
| Lisiane | 4 |  |
| Luciene | 3 |  |
| Mauro | 1 |  |
| Monatha | 1 |  |
| Pablo | 2 |  |
| Pedro | 4 |  |
| Renato | 1 |  |
| Roberpaulo | 6 |  |
| Rogério | 5 |  |
| Rovilson | 4 |  |
| Régis | 5 | Uma ocorrência sem o prefixo `Prof` |
| Sandra | 4 |  |
| Vanessa | 4 |  |
| Victória | 3 | Aparece também como `Vitória` — fundido, **confirmar** |
| Vitória | 1 |  |
| Washignton | 2 |  |
| Washington | 2 | `Washignton` no arquivo é typo da mesma pessoa — fundido |
