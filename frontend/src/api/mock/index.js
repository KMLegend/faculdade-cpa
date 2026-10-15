/**
 * Cliente falso — mesma interface do Axios para os verbos que o painel usa.
 *
 * As fixturas em `dados/` são geradas por `backend/scripts/gerar_mocks.py` a
 * partir dos anexos da especificação e do leitor real da planilha: 17 turmas,
 * 105 ofertas, 164 alocações e as 163 perguntas oficiais da CPA. O painel pode
 * então ser avaliado antes de o backend existir, sem dado inventado.
 *
 * Os payloads seguem o doc 06 — trocar para o backend real é mudar
 * VITE_USE_MOCK, não reescrever tela.
 */
import cursos from './dados/cursos.json'
import professores from './dados/professores.json'
import disciplinas from './dados/disciplinas.json'
import turmas from './dados/turmas.json'
import ofertas from './dados/ofertas.json'
import perguntas from './dados/perguntas.json'
import equivalencias from './dados/equivalencias.json'
import dimensoes from './dados/dimensoes.json'
import importacao from './dados/importacao.json'

const LATENCIA_MS = 180

/* ── derivados: formulários e relatórios ─────────────────────────────────── */

/**
 * Fonte ÚNICA da estrutura de um formulário — espelha `montar()` do doc 04 §4.
 *
 * Antes isto era calculado em dois lugares com regras diferentes (a listagem
 * fixava 48 institucionais, a prévia contava só as ativas), e as telas exibiam
 * totais divergentes para o mesmo formulário.
 */
const INSTRUMENTOS = {
  DISCENTE_TURMA: 'DISCENTE',
  DOCENTE: 'DOCENTE',
  TECNICO_ADMINISTRATIVO: 'TECNICO_ADMINISTRATIVO',
  COMUNIDADE: 'COMUNIDADE',
}

const ativasDo = (segmento, porMateria) =>
  perguntas.filter(
    (p) => p.segmento === segmento && p.ativo && p.por_materia === porMateria,
  )

const SEGUNDOS_POR_PERGUNTA = 5

function montar(tipoInstrumento, turmaId = null) {
  const segmento = INSTRUMENTOS[tipoInstrumento]
  const institucionais = ativasDo(segmento, false)
  const porMateria = ativasDo(segmento, true)

  const ofs =
    tipoInstrumento === 'DISCENTE_TURMA'
      ? ofertas.filter((o) => o.turmas.includes(turmaId) && o.avaliavel)
      : []

  // Só entram dimensões que de fato têm pergunta neste instrumento.
  const blocosInstitucionais = dimensoes.dimensoes
    .map((d) => ({
      dimensao: d.numero,
      nome: d.nome,
      perguntas: institucionais.filter((p) => p.dimensao === d.numero),
    }))
    .filter((b) => b.perguntas.length > 0)

  const blocosMateria = ofs.map((o) => ({
    oferta_id: o.id,
    rotulo: o.rotulo,
    disciplina: o.disciplina,
    professor: o.professor,
    perguntas: porMateria,
  }))

  const total = institucionais.length + porMateria.length * ofs.length
  return {
    tipo_instrumento: tipoInstrumento,
    segmento,
    turma: turmaId ? turmas.find((t) => t.id === turmaId) : null,
    perguntas_institucionais: institucionais.length,
    perguntas_por_materia: porMateria.length,
    total_ofertas: ofs.length,
    total_perguntas: total,
    // páginas: uma de abertura + uma por bloco institucional + uma por matéria
    total_paginas: 1 + blocosInstitucionais.length + blocosMateria.length,
    tempo_estimado_min: Math.max(
      1,
      Math.round((total * SEGUNDOS_POR_PERGUNTA) / 60),
    ),
    blocos_institucionais: blocosInstitucionais,
    blocos_materia: blocosMateria,
  }
}

const LIMITE_ALERTA_PERGUNTAS = 150

const ESTADOS = ['SINCRONIZADO', 'SINCRONIZADO', 'PENDENTE', 'NAO_CRIADO', 'CONGELADO']

const formularios = [
  ...turmas.map((t, i) => {
    const e = montar('DISCENTE_TURMA', t.id)
    return {
      id: t.id,
      uuid: `8f14e45f-ea6f-4c1b-9a2e-${String(t.id).padStart(12, '0')}`,
      tipo_instrumento: 'DISCENTE_TURMA',
      segmento: 'DISCENTE',
      titulo: `CPA 2026.2 — ${t.rotulo}`,
      turma_id: t.id,
      turma: t.rotulo,
      modulo: t.modulo,
      total_ofertas: e.total_ofertas,
      total_perguntas: e.total_perguntas,
      tempo_estimado_min: e.tempo_estimado_min,
      acima_do_limite: e.total_perguntas > LIMITE_ALERTA_PERGUNTAS,
      status: i < 12 ? 'PUBLICADO' : 'RASCUNHO',
      estado_sync: ESTADOS[i % ESTADOS.length],
      submissoes: i < 12 ? Math.max(0, 22 - i * 2) : 0,
      anonimato_ok: i !== 3,
      google_responder_uri:
        i < 12 ? `https://docs.google.com/forms/d/e/1FAIpQLSc${t.id}/viewform` : null,
    }
  }),
  ...[
    ['DOCENTE', 'Avaliação Docente', 16],
    ['TECNICO_ADMINISTRATIVO', 'Avaliação Técnico-Administrativa', 9],
    ['COMUNIDADE', 'Avaliação da Comunidade Externa', 0],
  ].map(([tipo, nome, subs], i) => {
    const e = montar(tipo)
    return {
      id: 100 + i,
      uuid: `8f14e45f-ea6f-4c1b-9a2e-9000000000${i}`,
      tipo_instrumento: tipo,
      segmento: tipo,
      titulo: `CPA 2026.2 — ${nome}`,
      turma_id: null,
      turma: null,
      modulo: null,
      total_ofertas: 0,
      total_perguntas: e.total_perguntas,
      tempo_estimado_min: e.tempo_estimado_min,
      acima_do_limite: e.total_perguntas > LIMITE_ALERTA_PERGUNTAS,
      status: 'PUBLICADO',
      estado_sync: 'SINCRONIZADO',
      submissoes: subs,
      anonimato_ok: true,
      google_responder_uri: `https://docs.google.com/forms/d/e/1FAIpQLSc9${i}/viewform`,
    }
  }),
]

/** ISG de demonstração, na fórmula real: (média − 1) / 4. */
const isgDe = (media) => Number((((media - 1) / 4) * 100).toFixed(2))

const relatorioDimensoes = {
  periodo_letivo: '2026.2',
  eixos: dimensoes.eixos.map((e) => ({
    ...e,
    dimensoes: dimensoes.dimensoes
      .filter((d) => d.eixo === e.numero)
      .map((d) => {
        const base = 3.6 + ((d.numero * 7) % 11) / 10
        const porSegmento = {
          DISCENTE: { respostas: 120 + d.numero * 9, media: base, isg_pct: isgDe(base) },
          DOCENTE: { respostas: 16, media: base + 0.3, isg_pct: isgDe(base + 0.3) },
          TECNICO_ADMINISTRATIVO:
            d.numero === 9 || d.numero === 2
              ? { respostas: 0, suprimido: true, motivo: 'DIMENSAO_NAO_APLICADA' }
              : { respostas: 9, suprimido: true, motivo: 'AMOSTRA_INSUFICIENTE' },
        }
        return {
          numero: d.numero,
          nome: d.nome,
          nome_institucional: d.nome_institucional,
          por_segmento: porSegmento,
          isg_geral_pct: isgDe(base),
          isg_2025_pct: isgDe(base - 0.08),
          variacao_pp: Number((isgDe(base) - isgDe(base - 0.08)).toFixed(2)),
        }
      }),
  })),
}

const relatorioQuestoes = perguntas
  .filter((p) => p.segmento === 'DISCENTE' && p.ativo)
  .map((p) => {
    const media = 3.5 + ((p.codigo * 13) % 15) / 10
    return {
      codigo: p.codigo,
      equivalencia_id: p.equivalencia_id,
      texto: p.texto,
      dimensao: p.dimensao,
      bloco: p.bloco,
      respostas: p.por_materia ? 1200 : 160,
      media: Number(media.toFixed(2)),
      isg_pct: isgDe(media),
      isg_2025_pct: isgDe(media - 0.1),
      variacao_pp: Number((isgDe(media) - isgDe(media - 0.1)).toFixed(2)),
    }
  })
  .sort((a, b) => b.isg_pct - a.isg_pct)

/**
 * Alcance de uma alteração de pergunta (doc 04 §6.1): em quantos formulários ela
 * entra, quantos estão publicados e quantos estão congelados por já terem resposta.
 * É o que o admin precisa ver ANTES de confirmar a edição.
 */
function impactoDaPergunta(codigo) {
  const p = perguntas.find((x) => x.codigo === Number(codigo))
  if (!p) return null
  const doInstrumento = formularios.filter(
    (f) => INSTRUMENTOS[f.tipo_instrumento] === p.segmento,
  )
  const publicados = doInstrumento.filter((f) => f.status === 'PUBLICADO')
  const congelados = doInstrumento.filter((f) => f.submissoes > 0)
  return {
    codigo: p.codigo,
    formularios: doInstrumento.length,
    publicados: publicados.length,
    congelados: congelados.length,
    rascunhos: doInstrumento.length - publicados.length,
    formularios_congelados: congelados.map((f) => ({
      id: f.id,
      titulo: f.titulo,
      submissoes: f.submissoes,
    })),
    proximo_codigo_livre: Math.max(...perguntas.map((x) => x.codigo)) + 1,
  }
}

/** Prévia: a mesma estrutura de `montar`, mais o diff contra o Google. */
function previaDe(id) {
  const f = formularios.find((x) => x.id === Number(id))
  if (!f) return null
  const e = montar(f.tipo_instrumento, f.turma_id)
  return {
    formulario: {
      id: f.id,
      titulo: f.titulo,
      tipo_instrumento: f.tipo_instrumento,
      segmento: f.segmento,
      estado_sync: f.estado_sync,
      acima_do_limite: f.acima_do_limite,
    },
    ...e,
    diff:
      f.estado_sync === 'NAO_CRIADO'
        ? null
        : f.tipo_instrumento === 'DISCENTE_TURMA'
          ? {
              unidade: 'matérias',
              incluidas: 2,
              alteradas: 1,
              removidas: 0,
              inalteradas: Math.max(0, e.total_ofertas - 3),
            }
          : {
              // instrumentos institucionais não têm matérias: o que muda são as
              // perguntas do banco
              unidade: 'perguntas',
              incluidas: 0,
              alteradas: 0,
              removidas: 0,
              inalteradas: e.total_perguntas,
            },
  }
}

/* ── roteamento ──────────────────────────────────────────────────────────── */
const ROTAS = [
  [/^\/api\/health$/, () => ({ status: 'ok', banco: 'demonstração', versao: '0.1.0' })],
  [/^\/api\/admin\/cursos$/, () => cursos],
  [/^\/api\/admin\/professores$/, () => professores],
  [/^\/api\/admin\/disciplinas$/, () => disciplinas],
  [/^\/api\/admin\/turmas$/, () => turmas],
  [/^\/api\/admin\/ofertas$/, () => ofertas],
  [/^\/api\/admin\/perguntas$/, () => perguntas],
  [/^\/api\/admin\/equivalencias$/, () => equivalencias],
  [/^\/api\/admin\/dimensoes$/, () => dimensoes],
  [/^\/api\/admin\/importacoes\/\d+$/, () => importacao],
  [/^\/api\/admin\/formularios$/, () => formularios],
  [/^\/api\/admin\/formularios\/gerar-lote$/, () => ({
    criados: 20,
    pulados: 0,
    sem_oferta: [],
    alertas: [{ formulario_id: 1, titulo: 'CPA 2026.2 — Biomedicina · Noturno · 6º período', total_perguntas: 168 }],
  })],
  [/^\/api\/admin\/formularios\/publicar-lote$/, () => ({
    publicados: formularios.filter(f => f.status === 'RASCUNHO').length,
    ids: formularios.map(f => f.id),
  })],
  [/^\/api\/admin\/formularios\/(\d+)\/publicar$/, (m) => {
    const f = formularios.find(x => x.id === Number(m[1]))
    if (f) f.status = 'PUBLICADO'
    return f
  }],
  [/^\/api\/admin\/formularios\/(\d+)\/encerrar$/, (m) => {
    const f = formularios.find(x => x.id === Number(m[1]))
    if (f) f.status = 'ENCERRADO'
    return f
  }],
  [/^\/api\/admin\/perguntas\/previa$/, () => ({
    turma_id: 1,
    total_perguntas: 148,
    perguntas_institucionais: 48,
    perguntas_por_materia: 10,
    total_ofertas: 10,
    tempo_estimado_min: 12,
    acima_do_limite: false,
  })],
  [/^\/api\/admin\/formularios\/(\d+)\/previa$/, (m) => previaDe(m[1])],
  [/^\/api\/publico\/qrcode\/([a-f0-9-]+)$/, (m) => ({
    uuid: m[1],
    tipo: 'image/svg+xml',
    mock_url: `https://docs.google.com/forms/d/e/${m[1]}/viewform`,
  })],
  [/^\/api\/admin\/perguntas\/(\d+)\/impacto$/, (m) => impactoDaPergunta(m[1])],
  [/^\/api\/admin\/relatorios\/dimensoes$/, () => relatorioDimensoes],
  [/^\/api\/admin\/relatorios\/questoes$/, () => relatorioQuestoes],
  [
    /^\/api\/admin\/relatorios\/adesao$/,
    () => ({
      periodo_letivo: '2026.2',
      instrumentos: [
        { nome: 'Turma', formularios: 17, publicados: 12, submissoes: 210, em_2025: 166 },
        { nome: 'Docente', formularios: 1, publicados: 1, submissoes: 23, em_2025: 16 },
        { nome: 'Técnico-administrativo', formularios: 1, publicados: 1, submissoes: 9, em_2025: 11 },
        { nome: 'Comunidade', formularios: 1, publicados: 1, submissoes: 41, em_2025: 0 },
      ],
    }),
  ],
]

function resolver(url) {
  const caminho = url.split('?')[0]
  for (const [padrao, handler] of ROTAS) {
    const m = caminho.match(padrao)
    if (m) {
      return new Promise((ok) =>
        setTimeout(() => ok({ data: handler(m) }), LATENCIA_MS),
      )
    }
  }
  return Promise.reject({
    codigo: 'NAO_ENCONTRADO',
    mensagem: `Rota não mockada: ${caminho}`,
    detalhes: {},
    status: 404,
  })
}

export const clienteMock = {
  get: resolver,
  post: resolver,
  patch: resolver,
  put: resolver,
  delete: resolver,
}
