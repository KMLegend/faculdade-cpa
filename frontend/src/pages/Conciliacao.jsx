import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, CircleAlert, CircleCheck } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Titulo, Cartao, Selo, Carregando, Erro } from '../components/ui'

const ICONE = {
  OK: <CircleCheck size={16} className="text-emerald-600" />,
  REVISAR: <AlertTriangle size={16} className="text-amber-600" />,
  ERRO: <CircleAlert size={16} className="text-red-600" />,
  IGNORADA: <CircleAlert size={16} className="text-slate-400" />,
}
const TOM = { OK: 'ok', REVISAR: 'atencao', ERRO: 'erro', IGNORADA: 'neutro' }
const LIMITE = 40

export default function Conciliacao() {
  const { id } = useParams()
  // Sem id na URL (item do menu), resolve a importação mais recente. Havia um
  // `12` fixo aqui, herdado da fixture do mock: no banco real não existe, e a
  // tela ficava carregando para sempre — foi o que escondeu os defeitos abaixo.
  const lista = useApi(id ? null : '/api/admin/importacoes', [id])
  const idImp = id ?? lista.dado?.[0]?.id

  const imp = useApi(idImp ? `/api/admin/importacoes/${idImp}` : null, [idImp])
  const linhas = useApi(idImp ? `/api/admin/importacoes/${idImp}/linhas` : null, [idImp])
  // Para mostrar o nome por trás de `professor_id_sugerido` / `disciplina_id_sugerida`.
  const profs = useApi('/api/admin/professores')
  const discs = useApi('/api/admin/disciplinas')

  const [filtro, setFiltro] = useState('REVISAR')
  const [ocupado, setOcupado] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [diff, setDiff] = useState(null)

  if (!id && !lista.carregando && !lista.dado?.length) {
    return (
      <Erro
        titulo="Nenhuma importação de grade ainda"
        acao={
          <Link to="/admin/grade/importar" className="text-sm font-medium underline">
            Importar a grade do período
          </Link>
        }
      >
        A conciliação só existe depois que uma planilha é enviada.
      </Erro>
    )
  }
  const falha = lista.erro ?? imp.erro ?? linhas.erro
  if (falha) {
    return (
      <Erro
        acao={
          <Link to="/admin/grade/importar" className="text-sm font-medium underline">
            Voltar para Importar grade
          </Link>
        }
      >
        {falha}
      </Erro>
    )
  }
  if (imp.carregando || linhas.carregando || !imp.dado || !linhas.dado) {
    return <Carregando />
  }

  const dado = imp.dado
  const resumo = dado.resumo ?? {}
  const todas = linhas.dado
  const avisos = resumo.avisos_segmentacao ?? []
  const nomeProf = (i) => profs.dado?.find((p) => p.id === i)?.nome_exibicao
  const nomeDisc = (i) => discs.dado?.find((d) => d.id === i)?.nome

  // Contagem a partir das linhas, não do resumo: o resumo é do momento do
  // upload e não acompanha as decisões tomadas aqui.
  const porStatus = todas.reduce((a, l) => ({ ...a, [l.status]: (a[l.status] ?? 0) + 1 }), {})
  const pendentes = (porStatus.REVISAR ?? 0) + (porStatus.ERRO ?? 0)
  const visiveis = filtro === 'TODOS' ? todas : todas.filter((l) => l.status === filtro)
  const aplicada = dado.status === 'APLICADA'

  async function acao(chave, fn) {
    setOcupado(chave)
    setAviso(null)
    try {
      setAviso(await fn())
      linhas.recarregar()
      imp.recarregar()
    } catch (e) {
      setAviso({ tom: 'erro', texto: e.mensagem ?? 'Falhou.' })
    } finally {
      setOcupado(null)
    }
  }

  const decidir = (l, corpo, rotulo) =>
    acao(`l${l.id}`, async () => {
      await api.patch(`/api/admin/importacoes/${idImp}/linhas/${l.id}`, corpo)
      return { tom: 'ok', texto: `${l.celula}: ${rotulo}.` }
    })

  return (
    <>
      <Titulo sub={`${dado.nome_arquivo} · enviado em ${new Date(dado.criado_em).toLocaleString('pt-BR')}`}>
        Conciliação da grade
      </Titulo>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Cartao rotulo="Alocações" valor={resumo.alocacoes} detalhe="células de aula" />
        <Cartao rotulo="OK" valor={porStatus.OK ?? 0} />
        <Cartao rotulo="Revisar" valor={porStatus.REVISAR ?? 0} destaque={(porStatus.REVISAR ?? 0) > 0} />
        <Cartao rotulo="Erro" valor={porStatus.ERRO ?? 0} destaque={(porStatus.ERRO ?? 0) > 0} />
        <Cartao
          rotulo="Turmas propostas"
          valor={resumo.turmas_propostas}
          detalhe="curso + turno + período"
        />
      </section>

      {aplicada && (
        <p className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          Importação já aplicada em{' '}
          {new Date(dado.aplicada_em).toLocaleString('pt-BR')}. As decisões abaixo
          ficam como histórico.
        </p>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {['REVISAR', 'ERRO', 'OK', 'IGNORADA', 'TODOS'].map((f) => (
          <button
            key={f}
            onClick={() => setFiltro(f)}
            className={`rounded-md px-3 py-1.5 text-sm ${
              filtro === f
                ? 'bg-slate-900 text-white'
                : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {f === 'TODOS' ? 'Todas' : f} {f !== 'TODOS' && `(${porStatus[f] ?? 0})`}
          </button>
        ))}
        <span className="ml-auto text-sm text-slate-600">
          {visiveis.length} linha{visiveis.length === 1 ? '' : 's'}
        </span>
      </div>

      {aviso && (
        <p
          className={`mt-3 rounded-md border p-2 text-sm ${
            aviso.tom === 'erro'
              ? 'border-red-200 bg-red-50 text-red-900'
              : 'border-emerald-200 bg-emerald-50 text-emerald-900'
          }`}
        >
          {aviso.texto}
        </p>
      )}

      <div className="mt-4 space-y-3">
        {visiveis.slice(0, LIMITE).map((l) => {
          const sugProf = nomeProf(l.professor_id_sugerido)
          const sugDisc = nomeDisc(l.disciplina_id_sugerida)
          const trocouProf = sugProf && sugProf !== l.professor_proposto
          return (
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
                    {l.aba} · célula {l.celula}
                    {l.horario && ` · ${l.horario}`}
                  </p>
                  <p className="mt-1 break-words font-mono text-sm text-slate-900">
                    “{l.texto_origem}”
                  </p>

                  <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                    <div>
                      <dt className="text-xs text-slate-500">Disciplina</dt>
                      <dd className="text-sm">
                        {l.disciplina_proposta ?? '—'}
                        {sugDisc && sugDisc !== l.disciplina_proposta && (
                          <span className="ml-2 text-amber-800">
                            → <strong>{sugDisc}</strong>
                          </span>
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Professor</dt>
                      <dd className="text-sm">
                        {l.professor_proposto ?? '—'}
                        {trocouProf && (
                          <span className="ml-2 text-amber-800">
                            → <strong>{sugProf}</strong>
                            {l.confianca != null &&
                              ` (${Math.round(l.confianca * 100)}% de similaridade)`}
                          </span>
                        )}
                      </dd>
                    </div>
                  </dl>

                  {l.motivos?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {l.motivos.map((m) => (
                        <Selo key={m} tom={TOM[l.status]}>
                          {m}
                        </Selo>
                      ))}
                    </div>
                  )}

                  {!aplicada && (l.status === 'REVISAR' || l.status === 'ERRO') && (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {trocouProf && (
                        <span className="text-sm text-slate-700">
                          Confirmar grava o alias: “{l.professor_proposto}” passa a
                          casar com “{sugProf}” nas próximas importações.
                        </span>
                      )}
                      <div className="ml-auto flex gap-2">
                        <button
                          disabled={ocupado === `l${l.id}`}
                          onClick={() =>
                            decidir(l, { status: 'IGNORADA' }, 'linha ignorada')
                          }
                          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
                        >
                          Ignorar linha
                        </button>
                        <button
                          disabled={ocupado === `l${l.id}`}
                          onClick={() =>
                            decidir(
                              l,
                              {
                                status: 'OK',
                                criar_alias: Boolean(trocouProf),
                                ...(l.professor_id_sugerido
                                  ? { professor_id: l.professor_id_sugerido }
                                  : {}),
                                ...(l.disciplina_id_sugerida
                                  ? { disciplina_id: l.disciplina_id_sugerida }
                                  : {}),
                              },
                              'confirmada',
                            )
                          }
                          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
                        >
                          Confirmar
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </article>
          )
        })}
        {visiveis.length > LIMITE && (
          <p className="text-center text-sm text-slate-500">
            … e mais {visiveis.length - LIMITE} linhas
          </p>
        )}
      </div>

      {avisos.length > 0 && (
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

      {diff && (
        <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <p className="font-medium">
            {diff.vazio
              ? 'Diff vazio — reimportar não mudaria nada.'
              : 'O que o commit faria:'}
          </p>
          <ul className="mt-2 space-y-1 text-slate-700">
            <li>
              Turmas: {diff.turmas_novas.length} nova(s), {diff.turmas_existentes}{' '}
              existente(s)
            </li>
            <li>
              Ofertas: {diff.ofertas_novas.length} nova(s), {diff.ofertas_existentes}{' '}
              existente(s), {diff.ofertas_desativadas.length} a desativar
            </li>
            <li>
              Cadastros novos: {diff.professores_novos.length} professor(es),{' '}
              {diff.disciplinas_novas.length} disciplina(s)
            </li>
          </ul>
        </div>
      )}

      {!aplicada && (
        <footer className="sticky bottom-0 mt-6 flex flex-wrap items-center gap-3 border-t border-slate-200 bg-slate-50 px-1 py-3">
          <button
            disabled={ocupado === 'novas'}
            onClick={() =>
              acao('novas', async () => {
                const { data } = await api.post(
                  `/api/admin/importacoes/${idImp}/criar-novas`,
                )
                return {
                  tom: 'ok',
                  texto: `${data.professores ?? 0} professor(es) e ${
                    data.disciplinas ?? 0
                  } disciplina(s) criados.`,
                }
              })
            }
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm disabled:opacity-50"
          >
            Criar todas as entidades novas
          </button>
          <button
            disabled={ocupado === 'diff'}
            onClick={() =>
              acao('diff', async () => {
                const { data } = await api.get(
                  `/api/admin/importacoes/${idImp}/diff`,
                )
                setDiff(data)
                return null
              })
            }
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm disabled:opacity-50"
          >
            Ver diff
          </button>
          <button
            disabled={pendentes > 0 || ocupado === 'aplicar'}
            title={
              pendentes > 0
                ? `${pendentes} linha(s) pendente(s) — o commit fica bloqueado (RN-13)`
                : undefined
            }
            onClick={() =>
              acao('aplicar', async () => {
                const { data } = await api.post(
                  `/api/admin/importacoes/${idImp}/aplicar`,
                )
                return {
                  tom: 'ok',
                  texto: `Aplicada: ${data.turmas ?? 0} turma(s), ${
                    data.ofertas ?? 0
                  } oferta(s).`,
                }
              })
            }
            className="ml-auto rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Aplicar importação ▸
          </button>
        </footer>
      )}
      {!aplicada && pendentes > 0 && (
        <p className="pb-4 text-right text-xs text-slate-500">
          {pendentes} linha(s) pendente(s): nada é gravado no domínio até que todas
          sejam tratadas.
        </p>
      )}
    </>
  )
}
