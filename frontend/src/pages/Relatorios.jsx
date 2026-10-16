import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { usePeriodo } from '../hooks/usePeriodo'
import { Titulo, Tabela, Selo, Carregando } from '../components/ui'

/** Faixas herdadas do painel 2025.2 (doc 08 §3.7). */
function corIsg(pct) {
  if (pct == null) return 'text-slate-400'
  const v = pct / 100
  if (v >= 0.72) return 'text-emerald-700'
  if (v >= 0.46) return 'text-amber-700'
  if (v >= 0.25) return 'text-orange-700'
  return 'text-red-700'
}

function Isg({ pct }) {
  if (pct == null) return <span className="text-slate-400">—</span>
  return (
    <span className={`font-medium tabular-nums ${corIsg(pct)}`}>
      {pct.toFixed(2).replace('.', ',')}%
    </span>
  )
}

/** Uma célula do relatório — ou a razão de ela não aparecer. */
function Celula({ dado }) {
  if (!dado) return <span className="text-slate-400">—</span>
  if (dado.suprimido) {
    const naoAplicada = dado.motivo === 'DIMENSAO_NAO_APLICADA'
    return (
      <Selo tom={naoAplicada ? 'neutro' : 'atencao'}>
        {naoAplicada ? 'não aplicada' : `amostra insuf. (${dado.respostas})`}
      </Selo>
    )
  }
  return <Isg pct={dado.isg_pct} />
}

const SEGMENTOS = ['DISCENTE', 'DOCENTE', 'TECNICO_ADMINISTRATIVO']

export default function Relatorios() {
  const { periodo, carregando: carregandoPeriodo } = usePeriodo()
  // `null` enquanto o período não resolve: consultar sem ele devolve 422.
  const base = periodo ? `?periodo_letivo_id=${periodo.id}` : null
  const dims = useApi(base && `/api/admin/relatorios/dimensoes${base}`, [periodo?.id])
  const questoes = useApi(base && `/api/admin/relatorios/questoes${base}`, [periodo?.id])
  const [visao, setVisao] = useState('dimensoes')

  if (carregandoPeriodo || dims.carregando || questoes.carregando)
    return <Carregando />

  const temResposta = (questoes.dado ?? []).length > 0

  return (
    <>
      <Titulo sub="ISG = (média − 1) / 4 · métrica oficial da CPA, conferida contra o painel 2025.2">
        Relatórios
      </Titulo>

      {!temResposta && (
        <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
          <strong>Nenhuma resposta importada neste período.</strong> Os números
          aparecem depois de <em>Importar respostas</em> na tela de formulários. A
          estrutura abaixo mostra quais dimensões cada segmento avalia.
        </div>
      )}

      <div className="mb-4 flex gap-1">
        {[
          ['dimensoes', 'Por dimensão × segmento'],
          ['questoes', 'ISG por questão'],
        ].map(([k, nome]) => (
          <button
            key={k}
            onClick={() => setVisao(k)}
            className={`rounded-md px-3 py-1.5 text-sm ${
              visao === k
                ? 'bg-slate-900 text-white'
                : 'border border-slate-300 bg-white hover:bg-slate-50'
            }`}
          >
            {nome}
          </button>
        ))}
      </div>

      {visao === 'dimensoes' ? (
        <>
          <Tabela
            colunas={['Eixo', 'Dim.', 'Nome', 'Discente', 'Docente', 'Téc.-adm.', 'Geral']}
          >
            {(dims.dado?.eixos ?? []).flatMap((e) =>
              e.dimensoes.map((d) => (
                <tr key={`${e.numero}-${d.numero}`}>
                  <td className="px-3 py-2 text-slate-500">{e.numero}</td>
                  <td className="px-3 py-2 font-medium tabular-nums">{d.numero}</td>
                  <td className="px-3 py-2">{d.nome_institucional ?? d.nome}</td>
                  {SEGMENTOS.map((seg) => (
                    <td key={seg} className="px-3 py-2">
                      <Celula dado={d.por_segmento?.[seg]} />
                    </td>
                  ))}
                  <td className="px-3 py-2">
                    <Celula dado={d.geral} />
                  </td>
                </tr>
              )),
            )}
          </Tabela>
          <p className="mt-3 text-xs text-slate-500">
            “Não aplicada” e “amostra insuficiente” são coisas diferentes: a primeira
            é de projeto, a segunda é proteção de anonimato. Nenhuma das duas é zero.
          </p>
        </>
      ) : (
        <>
          <Tabela colunas={['Código', 'Pergunta', 'Dim.', 'Respostas', 'Média', 'ISG']}>
            {(questoes.dado ?? []).slice(0, 25).map((q) => (
              <tr key={q.codigo}>
                <td className="px-3 py-2 font-mono text-xs">Q{q.codigo}</td>
                <td className="max-w-md px-3 py-2">{q.texto}</td>
                <td className="px-3 py-2 text-center tabular-nums">{q.dimensao}</td>
                <td className="px-3 py-2 tabular-nums text-slate-500">
                  {q.respostas}
                </td>
                <td className="px-3 py-2 tabular-nums">
                  {q.media != null ? q.media.toFixed(2).replace('.', ',') : '—'}
                </td>
                <td className="px-3 py-2">
                  <Celula dado={q} />
                </td>
              </tr>
            ))}
          </Tabela>
          <p className="mt-3 text-xs text-slate-500">
            Agregado por <strong>código</strong>, não por texto — é o que o pipeline
            de 2025.2 não conseguia fazer. Mostrando as 25 primeiras de{' '}
            {(questoes.dado ?? []).length}.
          </p>
        </>
      )}
    </>
  )
}
