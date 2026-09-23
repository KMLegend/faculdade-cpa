import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { Titulo, Tabela, Selo, Carregando } from '../components/ui'

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

export default function Relatorios() {
  const dims = useApi('/api/admin/relatorios/dimensoes')
  const questoes = useApi('/api/admin/relatorios/questoes')
  const [visao, setVisao] = useState('dimensoes')

  if (dims.carregando || questoes.carregando) return <Carregando />

  return (
    <>
      <Titulo sub="ISG = (média − 1) / 4 · métrica oficial da CPA, conferida contra o painel 2024">
        Relatórios
      </Titulo>

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
            colunas={['Eixo', 'Dim.', 'Nome', 'Discente', 'Docente', 'Téc.-adm.', 'ISG', '2024', 'Δ']}
          >
            {dims.dado.eixos.flatMap((e) =>
              e.dimensoes.map((d) => (
                <tr key={d.numero}>
                  <td className="px-3 py-2 text-slate-500">{e.numero}</td>
                  <td className="px-3 py-2 font-medium tabular-nums">{d.numero}</td>
                  <td className="px-3 py-2">{d.nome}</td>
                  {['DISCENTE', 'DOCENTE', 'TECNICO_ADMINISTRATIVO'].map((s) => {
                    const c = d.por_segmento[s]
                    return (
                      <td key={s} className="px-3 py-2">
                        {c?.suprimido ? (
                          <Selo tom={c.motivo === 'DIMENSAO_NAO_APLICADA' ? 'neutro' : 'atencao'}>
                            {c.motivo === 'DIMENSAO_NAO_APLICADA' ? 'não aplicada' : 'amostra insuf.'}
                          </Selo>
                        ) : (
                          <Isg pct={c?.isg_pct} />
                        )}
                      </td>
                    )
                  })}
                  <td className="px-3 py-2">
                    <Isg pct={d.isg_geral_pct} />
                  </td>
                  <td className="px-3 py-2 tabular-nums text-slate-500">
                    {d.isg_2024_pct.toFixed(2).replace('.', ',')}%
                  </td>
                  <td
                    className={`px-3 py-2 tabular-nums ${
                      d.variacao_pp >= 0 ? 'text-emerald-700' : 'text-red-700'
                    }`}
                  >
                    {d.variacao_pp >= 0 ? '+' : ''}
                    {d.variacao_pp.toFixed(2).replace('.', ',')}
                  </td>
                </tr>
              )),
            )}
          </Tabela>
          <p className="mt-3 text-xs text-slate-500">
            “Não aplicada” e “amostra insuficiente” são coisas diferentes: a primeira é de
            projeto, a segunda é proteção de anonimato. Nenhuma das duas é zero.
          </p>
        </>
      ) : (
        <>
          <Tabela colunas={['Código', 'Pergunta', 'Dim.', 'Respostas', 'Média', 'ISG', '2024', 'Δ pp']}>
            {questoes.dado.slice(0, 25).map((q) => (
              <tr key={q.codigo}>
                <td className="px-3 py-2 font-mono text-xs">Q{q.codigo}</td>
                <td className="max-w-md px-3 py-2">{q.texto}</td>
                <td className="px-3 py-2 text-center tabular-nums">{q.dimensao}</td>
                <td className="px-3 py-2 tabular-nums text-slate-500">{q.respostas}</td>
                <td className="px-3 py-2 tabular-nums">{q.media.toFixed(2).replace('.', ',')}</td>
                <td className="px-3 py-2">
                  <Isg pct={q.isg_pct} />
                </td>
                <td className="px-3 py-2 tabular-nums text-slate-500">
                  {q.isg_2024_pct.toFixed(2).replace('.', ',')}%
                </td>
                <td
                  className={`px-3 py-2 tabular-nums ${
                    q.variacao_pp >= 0 ? 'text-emerald-700' : 'text-red-700'
                  }`}
                >
                  {q.variacao_pp >= 0 ? '+' : ''}
                  {q.variacao_pp.toFixed(2).replace('.', ',')}
                </td>
              </tr>
            ))}
          </Tabela>
          <p className="mt-3 text-xs text-slate-500">
            Comparação por <strong>código</strong>, não por texto — é o que o pipeline de
            2024 não conseguia fazer. Mostrando as 25 primeiras de {questoes.dado.length}.
          </p>
        </>
      )}
    </>
  )
}
