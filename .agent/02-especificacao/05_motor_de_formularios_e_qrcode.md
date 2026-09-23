# 05 — Motor de Formulários e QR Code

É aqui que mora o "**de forma automática**": da grade importada aos QR Codes impressos,
sem digitação manual.

> ⚠️ **Leia junto com `10_integracao_google_forms.md`.** Este documento define **o que**
> cada formulário contém e seu ciclo de vida; o doc 10 define **como** isso é materializado
> em Google Forms. O `montar()` do doc 04 §4 produz a estrutura desejada; o sincronizador
> do doc 10 a aplica via API.

---

## 1. Geração em lote

**Entrada:** período letivo + janela de aplicação (pode ser diferente por segmento).
**Saída:** os 5 tipos de instrumento.

```python
def gerar_lote(periodo, janelas: dict[TipoInstrumento, Janela]) -> ResumoGeracao:
    r = ResumoGeracao()

    # 1) DISCENTE_TURMA — uma por turma  → 17
    for turma in turmas_ativas(periodo):
        ofertas = [o for o in turma.ofertas if o.avaliavel and o.ativo]
        if not ofertas:
            r.sem_oferta.append(turma); continue                  # RN-30
        r.registrar(upsert_formulario(periodo, DISCENTE_TURMA, turma=turma,
                                      janela=janelas[DISCENTE_TURMA]))

    # 2) Segmentos institucionais — uma cada  → 3
    for ti in (DOCENTE, TECNICO_ADMINISTRATIVO, COMUNIDADE):
        r.registrar(upsert_formulario(periodo, ti, janela=janelas[ti]))

    return r


def upsert_formulario(periodo, tipo, *, turma=None, janela) -> Formulario:
    existente = buscar(periodo, tipo, turma)                      # índices parciais, RN-25
    if existente and existente.status != RASCUNHO:
        return Pulado(existente)                                  # publicado nunca é regerado
    f = existente or Formulario(uuid=uuid4(), periodo_letivo=periodo,
                                tipo_instrumento=tipo,
                                segmento=SEGMENTO_DO_INSTRUMENTO[tipo],
                                turma=turma, status=RASCUNHO)
    f.titulo = titulo(tipo, turma, periodo)
    f.abre_em, f.fecha_em = janela.abre_em, janela.fecha_em
    apagar_snapshot(f)
    f.itens = montar(f)                                           # doc 04 §4
    if len(f.itens) > LIMITE_ALERTA_PERGUNTAS: registrar_alerta(f, len(f.itens))
    return Criado(f)
```

### Resultado com a grade 2026.2

| Instrumento | Qtd. | Perguntas | Título |
|---|---|---|---|
| `DISCENTE_TURMA` | **17** | 48 + 10×ofertas (88–168) | `CPA 2026.2 — Biomedicina · Noturno · 4º período` |
| `DOCENTE` | **1** | 60 | `CPA 2026.2 — Avaliação Docente` |
| `TECNICO_ADMINISTRATIVO` | **1** | 42 | `CPA 2026.2 — Avaliação Técnico-Administrativa` |
| `COMUNIDADE` | **1** | 3 ⚠️ | `CPA 2026.2 — Avaliação da Comunidade Externa` |
| **Total** | **20** | | |

**Padrões de título:**
- Turma: `CPA {periodo} — {curso} · {turno} · {periodo_numero}º período`
  (o módulo entra como subtítulo, nunca como identidade — RN-04)
- Segmentos: `CPA {periodo} — Avaliação {segmento}`

> **Comparação com 2025.2:** eram **17 Google Forms montados à mão** (15 turmas + docentes
> + técnicos), com os IDs fixos em um dicionário no `main.py` e o sufixo
> `(Disciplina - Professor)` digitado pergunta por pergunta, para cada matéria de cada
> turma. Agora são 20 formulários gerados em um clique a partir da grade.

## 2. Ciclo de vida (RN-28)

```
        gerar_lote              publicar            fecha_em / encerrar
 (∅) ──────────────► RASCUNHO ────────────► PUBLICADO ──────────────► ENCERRADO
                        │                       │                          │
            regerável, sem QR público   aceita respostas          somente leitura
```

| Status | QR acessível | Aceita submissão | Regerável | Excluível |
|---|---|---|---|---|
| `RASCUNHO` | não (404) | não | **sim** | sim |
| `PUBLICADO` | sim | sim, **dentro da janela** | não | não |
| `ENCERRADO` | sim (tela de encerrado) | **não** | não | não |

- Publicar exige `abre_em`, `fecha_em` e ao menos 1 pergunta no snapshot.
- **Publicação em lote por instrumento:** o admin publica os 17 de turma de uma vez,
  ou um segmento — não um a um.
- Abertura e fechamento são aplicados no Google por `setPublishSettings` (doc 10 §7);
  fora da janela o respondente vê a tela padrão do Google.
- `ENCERRADO` é aplicado pela `fecha_em` **verificada ao abrir o painel** — sem job
  agendado, porque o free tier do Render hiberna.

## 3. Link público e QR Code

**URL no QR:** o `responderUri` devolvido pela API do Google
(`https://docs.google.com/forms/d/e/1FAIpQLSc…/viewform`).

- O `uuid` interno continua existindo como chave do nosso lado, mas **não** aparece em
  URL pública — quem endereça o respondente é o Google.
- A URL é longa (~120 caracteres): QR mais denso, ver doc 10 §10.
- Formulário ainda não sincronizado (`google_responder_uri` nulo) → QR indisponível.

```python
import qrcode
from qrcode.image.svg import SvgPathImage

def gerar_qrcode(url: str, formato: str = "png", escala: int = 10) -> bytes:
    qr = qrcode.QRCode(
        version=None,                                       # ajusta ao tamanho da URL
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # 15% — tolera impressão comum
        box_size=escala, border=4,                          # border 4 = quiet zone mínima
    )
    qr.add_data(url); qr.make(fit=True)
    ...
```

- Formatos `png` (Pillow) e `svg` (`SvgPathImage`, sem Pillow — melhor para impressão).
- `StreamingResponse` com `Cache-Control: public, max-age=86400` — o QR de um UUID
  nunca muda.
- QR de formulário `RASCUNHO` → **404**.

## 4. Artefatos de impressão

Três artefatos distintos, porque as formas de aplicação são distintas:

### 4.1 Folha da turma (A4, uma por turma — 17 páginas)
Entregue ao professor, aplicada ao final da aula.

```
┌─────────────────────────────────────────────┐
│  AVALIAÇÃO CPA 2026.2                       │
│  Biomedicina · Noturno                      │
│  4º período — Módulo AB                     │
│                                             │
│        ███████████████████                  │
│        ██ ▄▄▄▄▄ █▀▄█ ▄▄▄▄▄ ██    ≥ 5 cm     │
│        ███████████████████                  │
│                                             │
│  docs.google.com/forms/d/e/1FAIpQLSc…/view  │
│                                             │
│  10 matérias avaliadas · 148 perguntas      │
│  cerca de 12 minutos                        │
│                                             │
│  Resposta ANÔNIMA. Sem login, nenhum dado   │
│  seu é registrado.  01/10 a 15/10/2026      │
└─────────────────────────────────────────────┘
```

> O tempo estimado é obrigatório na folha: um formulário de 148 perguntas exige que o
> aluno saiba no que está entrando. Calcule por `nº de perguntas × 5s`.

### 4.2 Lista de conferência da turma (A4, uma por turma)
Para a CPA conferir antes de aplicar: as matérias que a turma vai avaliar, com disciplina,
professor e modalidade, tal como vieram da grade. É o artefato que pega erro de
importação **antes** de o aluno responder.

### 4.3 Cartaz por segmento (3 páginas)
Docente, técnico-administrativo e comunidade — QR grande, texto explicativo do propósito
da CPA e o período de resposta. O da comunidade vai ao site e à recepção.

**Implementação:** `reportlab` (leve) ou HTML com `@media print` renderizado pelo
frontend. Escolha uma e documente — não faça as duas.

## 5. Acompanhamento de adesão

Durante a janela o admin vê **apenas contagens** — nunca conteúdo (RN-34).

| Instrumento | Formulários | Publicados | Submissões | 2025.2 (referência) |
|---|---|---|---|---|
| Turma | 17 | 17 | 210 | 166 |
| Docente | 1 | 1 | 23 | 16 |
| Técnico-administrativo | 1 | 1 | 9 | 11 |
| Comunidade | 1 | 1 | 41 | **0** |

A coluna de 2025.2 é o alvo: o ciclo anterior teve **193 respostas no total**. Turma sem
nenhuma submissão é acionável — a aplicação não aconteteceu e a CPA precisa cobrar.

## 6. Critérios de aceite

1. `gerar_lote` sobre a grade 2026.2 cria **20 formulários**: 17 + 1 + 1 + 1.
2. Os 20 têm UUIDs distintos.
3. *Biomedicina · Noturno · 6º período* tem 12 ofertas ⇒ **168 perguntas**
   (48 institucionais + 10 × 12) e dispara o alerta de tamanho.
3.1 *Biomedicina · Noturno · 4º período* recebe **um** formulário, embora apareça em duas
    colunas `Turma A` da planilha (RN-04).
3.2 `Bioquímica | Andrea` e `Bioquímica | Vanessa` geram **dois blocos distintos** na
    mesma turma (RN-08).
3.3 As **4 ofertas sem turma** (coluna de estágio) não aparecem em nenhum formulário.
4. `Bioquímica | Andrea` e `Bioquímica | Vanessa` geram **dois** formulários distintos.
5. Rodar `gerar_lote` duas vezes seguidas não cria duplicata.
6. Formulário não sincronizado: `GET /api/publico/qrcode/{uuid}` → 404.
7. Publicar chama `setPublishSettings` e o formulário passa a aceitar respostas;
   encerrar desliga `isAcceptingResponses`.
8. Editar o texto de uma pergunta após a publicação não altera o formulário publicado.
9. O PNG do QR decodifica exatamente para o `google_responder_uri` do formulário.
10. Oferta sem turma vinculada ou `avaliavel = false` não gera formulário e aparece no resumo.
