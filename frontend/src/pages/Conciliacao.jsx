import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertTriangle, CircleAlert, CircleCheck } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { Titulo, Cartao, Selo, Carregando } from '../components/ui'

const ICONE = {
  OK: <CircleCheck size={16} className="text-emerald-600" />,
  REVISAR: <AlertTriangle size={16} className="text-amber-600" />,
  ERRO: <CircleAlert size={16} className="text-red-600" />,
}
const TOM = { OK: 'ok', REVISAR: 'atencao', ERRO: 'erro' }

export default function Conciliacao() {
  const { id = '12' } = useParams()
  const { dado, carregando } = useApi(`/api/admin/importacoes/${id}`, [id])
  const [filtro, setFiltro] = useState('REVISAR')

  if (carregando || !dado) return <Carregando />

  const { resumo, linhas, avisos } = dado
  const visiveis = filtro === 'TODOS' ? (linhas || []) : (linhas || []).filter((l) => l.status === filtro)
  const pendentes = resumo.REVISAR + resumo.ERRO

  return (
    <>
      <Titulo sub={`${dado.nome_arquivo} · período ${dado.periodo_letivo}`}>
        Conciliação da grade
      </Titulo>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Cartao rotulo="Alocações" valor={resumo.alocacoes} detalhe="células de aula" />
        <Cartao rotulo="OK" valor={resumo.OK} />
        <Cartao rotulo="Revisar" valor={resumo.REVISAR} destaque={resumo.REVISAR > 0} />
        <Cartao rotulo="Erro" valor={resumo.ERRO} destaque={resumo.ERRO > 0} />
        <Cartao
          rotulo="Resultado"
          valor={`${resumo.turmas} / ${resumo.ofertas}`}
          detalhe="turmas / ofertas"
        />
      </section>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {['REVISAR', 'ERRO', 'OK', 'TODOS'].map((f) => (
          <button
            key={f}
            onClick={() => setFiltro(f)}
            className={`rounded-md px-3 py-1.5 text-sm ${
              filtro === f
                ? 'bg-slate-900 text-white'
                : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {f === 'TODOS' ? 'Todas' : f} {f !== 'TODOS' && `(${resumo[f]})`}
          </button>
        ))}
        <span className="ml-auto text-sm text-slate-600">
          {visiveis.length} linha{visiveis.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {visiveis.slice(0, 40).map((l) => (
          <article
            key={l.id}
            className={`rounded-lg border bg-white p-4 ${
              l.status === 'ERRO'
                ? 'border-red-300'
                : l.status === 'REVISAR'
                  ? 'border-amber-300'
                  : 'border-slate-200'
            }`}
          >
            <div className="flex items-start gap-2">
              {ICONE[l.status]}
              <div className="min-w-0 flex-1">
                <p className="text-xs text-slate-500">
                  {l.aba} · célula {l.celula} · {l.dia_semana} {l.horario}
                </p>
                <p className="mt-1 break-words font-mono text-sm text-slate-900">
                  “{l.texto_origem}”
                </p>

                <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs text-slate-500">Disciplina</dt>
                    <dd className="text-sm">{l.disciplina_proposta ?? '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500">Professor</dt>
                    <dd className="text-sm">
                      {l.professor_proposto ?? '—'}
                      {l.sugestao && (
                        <span className="ml-2 text-amber-800">
                          → sugerido <strong>{l.sugestao.professor}</strong> (
                          {Math.round(l.sugestao.similaridade * 100)}% de similaridade)
                        </span>
                      )}
                    </dd>
                  </div>
                </dl>

                {l.motivos.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {l.motivos.map((m) => (
                      <Selo key={m} tom={TOM[l.status]}>
                        {m}
                      </Selo>
                    ))}
                  </div>
                )}

                {l.status !== 'OK' && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {l.sugestao && (
                      <label className="flex items-center gap-1.5 text-sm text-slate-700">
                        <input type="checkbox" defaultChecked className="rounded" />
                        Lembrar: “{l.professor_proposto}” significa “{l.sugestao.professor}”
                      </label>
                    )}
                    <div className="ml-auto flex gap-2">
                      <button className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50">
                        Ignorar linha
                      </button>
                      <button className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white">
                        Confirmar
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </article>
        ))}
        {visiveis.length > 40 && (
          <p className="text-center text-sm text-slate-500">
            … e mais {visiveis.length - 40} linhas
          </p>
        )}
      </div>

      {avisos?.length > 0 && (
        <details className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
          <summary className="cursor-pointer text-sm font-medium">
            Avisos da segmentação de turmas ({avisos.length})
          </summary>
          <ul className="mt-3 space-y-1 text-sm text-slate-700">
            {avisos.map((a, i) => (
              <li key={i}>
                <Selo tom="info">{a.tipo}</Selo>{' '}
                <span className="text-slate-600">
                  {a.aba} · colunas {a.colunas?.join(', ')}
                  {a.cursos && ` → ${a.cursos.join(' + ')}`}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}

      <footer className="sticky bottom-0 mt-6 flex flex-wrap items-center gap-3 border-t border-slate-200 bg-slate-50 px-1 py-3">
        <button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm">
          Criar todas as entidades novas
        </button>
        <button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm">
          Ver diff
        </button>
        <button
          disabled={pendentes > 0}
          title={
            pendentes > 0
              ? `${pendentes} linha(s) pendente(s) — o commit fica bloqueado (RN-13)`
              : undefined
          }
          className="ml-auto rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Aplicar importação ▸
        </button>
      </footer>
      {pendentes > 0 && (
        <p className="pb-4 text-right text-xs text-slate-500">
          {pendentes} linha(s) pendente(s): nada é gravado no domínio até que todas sejam
          tratadas.
        </p>
      )}
    </>
  )
}
