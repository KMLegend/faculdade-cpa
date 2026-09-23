# 07 — Frontend: Telas e Fluxos

React + Vite + TailwindCSS + React Router + Axios + Lucide (stack fixada em `01-init`).
Sem biblioteca de componentes pesada. Sem CSS customizado fora do Tailwind.

## 1. Mapa de rotas

> ⚠️ **O portal do respondente deixou de existir neste frontend.** Quem exibe e coleta o
> formulário é o **Google Forms** (doc 10). Este app é **apenas o painel administrativo**.

```
ADMIN (protegido)
  /admin/login            senha estática
  /admin                  dashboard
  /admin/grade/importar   upload da planilha
  /admin/grade/importar/:id/conciliar   ◄── tela mais importante do admin
  /admin/grade            turmas e ofertas do período
  /admin/cadastros        professores · disciplinas · cursos (abas)
  /admin/perguntas        banco de perguntas (3 abas: Gerais · Disciplina · Professor)
  /admin/formularios      geração, publicação, QR e folhas (filtro por instrumento)
  /admin/relatorios       resultados
```

---

## 2. O portal do respondente — **fora deste escopo**

O formulário é um **Google Form**. A experiência de resposta (mobile, acessibilidade,
rascunho, validação de obrigatórias, tela de encerrado) é do Google.

O que **este** frontend precisa oferecer no lugar:

| Antes (portal próprio) | Agora |
|---|---|
| `/responder/:uuid` | link `responderUri` no painel, com botão *Copiar* e *Abrir* |
| paginação por matéria | `pageBreakItem` no próprio Google Form (doc 10 §3.2) |
| rascunho em `localStorage` | função nativa do Google Forms |
| honeypot, rate limit, duração mínima | removidos — ver doc 10 §11 |
| `/indisponivel` | tela padrão do Google quando `isAcceptingResponses = false` |

**Responsabilidade que sobra para nós:** a **pré-visualização**. Antes de publicar, o
admin precisa ver a estrutura que será enviada ao Google — blocos, matérias e perguntas —
sem sair do painel. É a última chance de pegar um erro de grade antes de o formulário ir
para a sala. Ver §3.6.

## 3. Admin

### 3.1 `/admin/login`
Campo de senha + `POST` de teste em `/api/health` com Basic Auth. Credencial em
`sessionStorage` (some ao fechar a aba), nunca em `localStorage`.
Interceptor do Axios injeta o header e, em `401`, redireciona ao login.

### 3.2 `/admin` — dashboard
Cartões: período letivo ativo · turmas · ofertas avaliáveis · formulários publicados ·
submissões recebidas. Atalhos: **Importar grade**, **Gerar formulários**, **Imprimir folhas**.
Alerta se houver importação em `AGUARDANDO_REVISAO`.

### 3.3 `/admin/grade/importar`
Drag-and-drop do `.xlsx` + seleção do período letivo (pré-preenchido do nome do arquivo:
`horario 20262.xlsx` → `2026.2`). Após o upload, redireciona para a conciliação.

### 3.4 `/admin/grade/importar/:id/conciliar` — **a tela crítica**

```
Importação #12 · horario 20262.xlsx · 2026.2
┌────────────────────────────────────────────────────────────┐
│  ✅ 158 OK      ⚠️ 5 revisar      ⛔ 1 erro                 │
│  17 turmas · 105 ofertas · 29 professores · 76 disciplinas │
│  [ Todos ] [ Revisar ] [ Erro ]        Aba: [ Todas  ▾ ]   │
├────────────────────────────────────────────────────────────┤
│ ⛔ Enfermagem - Noturno · E29                              │
│    "O cuidar nos Processos Críticos - Preceptor            │
│     (A contratar) - Lançar no nome da Profa Katiulcy"      │
│    Disciplina: [ O cuidar nos Processos Críticos      ▾ ]  │
│    Professor:  [ Katiulcy (novo)                      ▾ ]  │
│    motivo: OBSERVAÇÃO ADMINISTRATIVA NA CÉLULA             │
│                       [ Ignorar linha ]  [ Confirmar ]     │
├────────────────────────────────────────────────────────────┤
│ ⚠️ Biomedicina Noturno · D4                                │
│    "Toxicologia - Preleção - Prof Washignton"              │
│    Professor: [ Washington  (92% de similaridade)     ▾ ]  │
│    ☑ Lembrar: "Washignton" sempre significa "Washington"   │
│                       [ Criar como novo ]  [ Confirmar ]   │
└────────────────────────────────────────────────────────────┘
        [ Cancelar importação ]   [ Ver diff ]   [ Aplicar ▸ ]
```

Regras:
- `Aplicar` fica **desabilitado** enquanto houver linha `REVISAR` ou `ERRO` (RN-12) —
  com o motivo visível ao passar o mouse.
- `Ver diff` abre modal com incluídos / alterados / desativados / inalterados (RN-11).
- O *checkbox* "Lembrar" grava o alias — é o que reduz o trabalho no semestre seguinte.
- Texto bruto da célula **sempre** visível: é o que permite ao admin decidir.
- **Primeira importação do sistema:** com o cadastro vazio, as 164 linhas viriam como
  `DISCIPLINA_NOVA`/`PROFESSOR_NOVA`. Nesse caso a tela oferece
  **"Criar todas as entidades novas"** em um clique (doc 03 §4), deixando para revisão
  individual apenas as linhas com flag de ambiguidade ou erro.

### 3.5 `/admin/perguntas`
Quatro abas, uma por instrumento, com contagem real do Anexo B:
`Discente (58)` · `Docente (60)` · `Técnico-adm. (42)` · `Comunidade (3)`.

Dentro da aba `Discente`, dois grupos: **Institucional (48)** e
**Por matéria (10)** — este último com os blocos `DISCIPLINA` e `PROFESSOR` (RN-18, RN-19).
Cada linha mostra o `codigo` (1–163) e o grupo de equivalência — é por eles que a CPA
reconhece a pergunta e enxerga suas versões nos outros segmentos.
Editar o texto avisa: *"correção de grafia mantém o código; mudança de sentido exige
código novo"* (doc 04 §5.1).
Cada linha: texto, **dimensão SINAES**, tipo, obrigatória, ativa, alça de reordenar.
Filtro lateral por eixo/dimensão, e um indicador de **cobertura**: quais das 10 dimensões
ainda não têm nenhuma pergunta naquele instrumento — é o alerta que evita entregar um
relatório com dimensão vazia.

Ao criar/editar:
- **Dimensão é obrigatória** (RN-16), escolhida em um seletor agrupado por eixo.
- Instrumento `DISCENTE_TURMA` ⇒ escolher bloco: `INSTITUCIONAL` (aparece uma vez) ou
  `DISCIPLINA`/`PROFESSOR` (repete por matéria). Só os dois últimos liberam
  `Aplicação: Específicas`, com multiselect de disciplinas/professores/cursos.
- Demais instrumentos ⇒ bloco fixo `INSTITUCIONAL`, sem vínculo (RN-20).
- Perguntas do Anexo B são marcadas **"oficial CPA"** e avisam ao editar: alterar o
  enunciado quebra o comparativo com 2024.
- Painel lateral **"Prévia do formulário"**: escolhe uma turma e mostra o total de
  perguntas resultante, com alerta em vermelho acima de `LIMITE_ALERTA_PERGUNTAS` (doc 04 §7).

### 3.6 `/admin/formularios`
Ação principal: **Gerar formulários do período** (janela `abre_em`/`fecha_em` no modal).
Resultado em tabela:

Abas por instrumento: `Turmas (17)` · `Docente` · `Técnico-adm.` · `Comunidade`.

| Formulário | Matérias | Perguntas | Status | Submissões | Ações |
|---|---|---|---|---|---|
| Biomedicina · Noturno · 6º período | 12 | 168 | 🟢 sincronizado | 19 | QR · Folha · Abrir no Google |
| Biomedicina · Noturno · 4º período | 10 | 148 | 🟢 sincronizado | 23 | QR · Folha · Abrir no Google |
| GTI · Noturno · 4º período | 5 | 98 | 🟡 pendente | — | Prévia · Sincronizar |
| Enfermagem · Noturno · 8º período | 4 | 88 | 🔴 divergente | 7 | Ver divergência |

Ações principais no topo: **Sincronizar todos** · **Publicar em lote** · **Importar
respostas** · **Imprimir folhas**.

Estados de sincronização (doc 10 §6):

| Ícone | Estado | Significado |
|---|---|---|
| ⚪ | `NAO_CRIADO` | ainda não existe no Google |
| 🟡 | `PENDENTE` | a grade mudou; `hash_estrutura` difere |
| 🟢 | `SINCRONIZADO` | Google reflete a estrutura desejada |
| 🔴 | `DIVERGENTE` | editado à mão no Google, ou respostas órfãs |
| 🔒 | `CONGELADO` | já tem respostas; estrutura bloqueada (doc 10 §6.4) |

⚠️ **O alerta de anonimato é o mais importante da tela.** Se a releitura devolver
`emailCollectionType ≠ DO_NOT_COLLECT`, o formulário aparece em vermelho com
*"Coleta de e-mail ativada — publicação bloqueada"*, e o botão de publicar fica inerte.

- `QR` abre modal com a imagem (de `/api/publico/qrcode/{uuid}`), botão de imprimir e o
  link em texto com "copiar".
- `Folha` baixa o PDF A4 da turma; no topo, **Imprimir todas as folhas** baixa o PDF do período.
- ⚠️ ao lado da contagem quando ultrapassar o limite (doc 04 §7).

### 3.6 `/admin/formularios/:id/previa`

A última barreira antes de o formulário ir para a sala. Mostra a estrutura **exatamente
como será enviada ao Google**:

- blocos institucionais agrupados por dimensão, com contagem;
- **um cartão por matéria**, com `Disciplina · Prof. Nome` e as 10 perguntas;
- totais: nº de perguntas, nº de páginas, tempo estimado;
- um *diff* contra o que já está no Google, quando o formulário já existe:
  `+ 2 matérias · ~ 1 professor alterado · − 1 matéria`.

É aqui que a CPA pega um erro de importação da grade — professor trocado, disciplina
duplicada — **antes** de o aluno responder.

### 3.7 `/admin/relatorios`
Ver doc 08. Toda célula abaixo do limiar exibe **"amostra insuficiente"**, nunca o número.

---

## 4. Padrões técnicos do frontend

- `src/api/client.js`: instância única do Axios com `baseURL: import.meta.env.VITE_API_BASE_URL`,
  interceptor de erro que traduz o campo `erro` do backend em mensagem de tela.
- Estado do servidor: `useState` + `useEffect` bastam para este escopo. **Não** adicione
  Redux/Zustand/React Query sem necessidade comprovada (pacotes leves — `01-init`).
- Componentes reutilizáveis mínimos: `EscalaLikert`, `CampoTexto`, `BlocoPergunta`,
  `Paginacao`, `Modal`, `Badge`, `TabelaSimples`.
- Rotas admin envolvidas por `<RotaProtegida>`.
- Nenhuma chave, senha ou URL de banco no bundle — só `VITE_API_BASE_URL`.
- Mobile-first: o portal do aluno é desenvolvido na largura de 375px primeiro.

## 5. Critérios de aceite

1. A prévia de uma turma com 10 ofertas mostra 8 blocos institucionais e 10 cartões de
   matéria, com o *diff* contra o Google quando o formulário já existe.
2. O painel exibe o estado de sincronização correto para cada um dos 20 formulários.
3. Formulário com coleta de e-mail ativada aparece em vermelho e com *Publicar* inerte.
4. O link `responderUri` é copiável em um clique.
5. `Aplicar` da conciliação permanece bloqueado com qualquer linha pendente.
6. O QR exibido no admin, fotografado da tela, abre o formulário correto.
