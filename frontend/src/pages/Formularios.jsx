import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api, USANDO_MOCK } from '../api/client'
import { Titulo, Tabela, Selo, Carregando } from '../components/ui'

const SYNC = {
  NAO_CRIADO: ['⚪', 'neutro', 'não existe no Google'],
  PENDENTE: ['🟡', 'atencao', 'a grade mudou'],
  SINCRONIZADO: ['🟢', 'ok', 'Google reflete a estrutura'],
  DIVERGENTE: ['🔴', 'erro', 'editado à mão no Google'],
  CONGELADO: ['🔒', 'info', 'já tem respostas'],
}

const ABAS = [
  ['DISCENTE_TURMA', 'Turmas'],
  ['DOCENTE', 'Docente'],
  ['TECNICO_ADMINISTRATIVO', 'Técnico-adm.'],
  ['COMUNIDADE', 'Comunidade'],
]

const BASE_API_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export default function Formularios() {
  const { dado, carregando, recarregar } = useApi('/api/admin/formularios')
  const [aba, setAba] = useState('DISCENTE_TURMA')
  const [modalGerar, setModalGerar] = useState(false)
  const [modalQr, setModalQr] = useState(null)
  const [gerando, setGerando] = useState(false)
  const [mensagemSucesso, setMensagemSucesso] = useState(null)
  const [copiado, setCopiado] = useState(false)

  // Janela de datas no modal de geração
  const [abreEm, setAbreEm] = useState('2026-10-01')
  const [fechaEm, setFechaEm] = useState('2026-10-15')

  if (carregando) return <Carregando />

  const lista = (dado || []).filter((f) => f.tipo_instrumento === aba)
  const bloqueados = (dado || []).filter((f) => !f.anonimato_ok)

  async function handleGerarLote(e) {
    e.preventDefault()
    setGerando(true)
    try {
      const payload = {
        periodo_letivo_id: 1,
        janelas: {
          [aba]: {
            abre_em: abreEm ? `${abreEm}T08:00:00Z` : null,
            fecha_em: fechaEm ? `${fechaEm}T23:59:59Z` : null,
          },
        },
      }
      const resp = await api.post('/api/admin/formularios/gerar-lote', payload)
      setMensagemSucesso(
        `Geração concluída! ${resp.data?.criados ?? 20} formulários gerados.`,
      )
      setModalGerar(false)
      if (recarregar) recarregar()
    } catch (err) {
      alert(err.mensagem || 'Erro ao gerar formulários em lote.')
    } finally {
      setGerando(false)
    }
  }

  async function handlePublicarLote() {
    if (!confirm(`Deseja publicar em lote todos os formulários da aba "${aba}"?`)) {
      return
    }
    try {
      const resp = await api.post('/api/admin/formularios/publicar-lote', {
        tipo_instrumento: aba,
      })
      alert(`Publicação concluída! ${resp.data?.publicados ?? 0} formulários publicados.`)
      if (recarregar) recarregar()
    } catch (err) {
      alert(err.mensagem || 'Erro ao publicar formulários.')
    }
  }

  function handleCopiarLink(url) {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(url)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    }
  }

  return (
    <>
      <Titulo sub="20 formulários no período · sincronizados com o Google Forms">
        Formulários
      </Titulo>

      {mensagemSucesso && (
        <div className="mb-4 rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900 flex justify-between items-center">
          <span>{mensagemSucesso}</span>
          <button
            onClick={() => setMensagemSucesso(null)}
            className="text-emerald-700 hover:text-emerald-900 text-xs font-bold"
          >
            ✕
          </button>
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          onClick={() => setModalGerar(true)}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800"
        >
          Gerar formulários do período
        </button>
        <button
          onClick={handlePublicarLote}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
        >
          Publicar em lote ({aba})
        </button>
        <a
          href={`${BASE_API_URL}/api/admin/periodos/1/folhas.pdf?tipo_instrumento=${aba}`}
          target="_blank"
          rel="noreferrer"
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 inline-flex items-center"
        >
          Imprimir todas as folhas (PDF)
        </a>
      </div>

      {bloqueados.length > 0 && (
        <div className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm">
          <strong className="text-red-900">
            Coleta de e-mail ativada em {bloqueados.length} formulário
          </strong>
          <span className="text-red-800">
            {' '}— publicação bloqueada até corrigir no Google. É o anonimato que está em
            jogo.
          </span>
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-1">
        {ABAS.map(([k, nome]) => (
          <button
            key={k}
            onClick={() => setAba(k)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              aba === k
                ? 'bg-slate-900 text-white'
                : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {nome} ({(dado || []).filter((f) => f.tipo_instrumento === k).length})
          </button>
        ))}
      </div>

      <Tabela
        colunas={[
          'Formulário',
          'Matérias',
          'Perguntas',
          'Tempo',
          'Sync',
          'Status',
          'Subm.',
          'Ações',
        ]}
      >
        {lista.map((f) => {
          const syncInfo = SYNC[f.estado_sync] || ['⚪', 'neutro', 'desconhecido']
          const [icone, tom, tituloSync] = syncInfo
          return (
            <tr key={f.id} className={!f.anonimato_ok ? 'bg-red-50' : undefined}>
              <td className="px-3 py-2">
                <p className="font-medium">{f.turma ?? f.titulo.split('— ')[1] ?? f.titulo}</p>
                {f.modulo && <p className="text-xs text-slate-500">Módulo {f.modulo}</p>}
              </td>
              <td className="px-3 py-2 tabular-nums">{f.total_ofertas || '—'}</td>
              <td className="px-3 py-2 tabular-nums">
                {f.total_perguntas}
                {f.acima_do_limite && (
                  <span title="acima do limite de alerta (150 perguntas)" className="cursor-help">
                    {' '}⚠️
                  </span>
                )}
              </td>
              <td className="px-3 py-2 tabular-nums text-slate-500">
                ~{f.tempo_estimado_min} min
              </td>
              <td className="px-3 py-2" title={tituloSync}>
                {icone}
              </td>
              <td className="px-3 py-2">
                <Selo tom={f.status === 'PUBLICADO' ? 'ok' : 'neutro'}>{f.status}</Selo>
              </td>
              <td className="px-3 py-2 tabular-nums">{f.submissoes || '—'}</td>
              <td className="px-3 py-2">
                <div className="flex items-center gap-2 text-sm">
                  <Link
                    to={`/admin/formularios/${f.id}/previa`}
                    className="text-slate-700 underline hover:text-slate-900"
                  >
                    Prévia
                  </Link>

                  <span className="text-slate-300">·</span>

                  <button
                    onClick={() => setModalQr(f)}
                    className="text-slate-700 underline hover:text-slate-900"
                  >
                    QR
                  </button>

                  <span className="text-slate-300">·</span>

                  <a
                    href={`${BASE_API_URL}/api/admin/formularios/${f.id}/folha.pdf`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-slate-700 underline hover:text-slate-900"
                    title="Baixar folha A4 de aplicação"
                  >
                    Folha
                  </a>

                  {f.turma_id && (
                    <>
                      <span className="text-slate-300">·</span>
                      <a
                        href={`${BASE_API_URL}/api/admin/turmas/${f.turma_id}/conferencia.pdf`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-slate-700 underline hover:text-slate-900"
                        title="Baixar lista de conferência da turma"
                      >
                        Conferência
                      </a>
                    </>
                  )}

                  {f.google_responder_uri && (
                    <>
                      <span className="text-slate-300">·</span>
                      <a
                        href={f.google_responder_uri}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sky-600 underline hover:text-sky-800"
                      >
                        Google
                      </a>
                    </>
                  )}
                </div>
              </td>
            </tr>
          )
        })}
      </Tabela>

      <p className="mt-3 text-xs text-slate-500">
        O tempo estimado sai impresso na folha de aplicação: ninguém deve descobrir no meio
        que faltam 100 perguntas.
      </p>

      {/* Modal de Geração em Lote */}
      {modalGerar && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="text-lg font-bold text-slate-900">
              Gerar Formulários do Período
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Gera os 20 formulários institucionais e de turmas com base na grade ativa.
            </p>

            <form onSubmit={handleGerarLote} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-600">
                  Data de Abertura
                </label>
                <input
                  type="date"
                  value={abreEm}
                  onChange={(e) => setAbreEm(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 p-2 text-sm"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-600">
                  Data de Fechamento
                </label>
                <input
                  type="date"
                  value={fechaEm}
                  onChange={(e) => setFechaEm(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 p-2 text-sm"
                  required
                />
              </div>

              <div className="mt-6 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModalGerar(false)}
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={gerando}
                  className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {gerando ? 'Gerando…' : 'Gerar Formulários'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de QR Code */}
      {modalQr && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl text-center">
            <h2 className="text-base font-bold text-slate-900">
              {modalQr.turma || modalQr.titulo}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Escaneie ou copie o link direto para o formulário
            </p>

            <div className="my-6 flex justify-center">
              <div className="rounded-lg border border-slate-200 p-3 bg-white shadow-sm inline-block">
                <img
                  src={`${BASE_API_URL}/api/publico/qrcode/${modalQr.uuid}?formato=png&escala=8`}
                  alt="QR Code do Formulário"
                  className="h-48 w-48 object-contain"
                  onError={(e) => {
                    // Fallback visual caso ainda não sincronizado
                    e.target.style.display = 'none'
                    e.target.nextSibling.style.display = 'flex'
                  }}
                />
                <div
                  style={{ display: 'none' }}
                  className="h-48 w-48 flex-col items-center justify-center text-xs text-slate-400 border border-dashed rounded p-4"
                >
                  <span>QR disponível após sincronização e publicação</span>
                </div>
              </div>
            </div>

            {modalQr.google_responder_uri && (
              <div className="mb-4">
                <input
                  type="text"
                  readOnly
                  value={modalQr.google_responder_uri}
                  className="w-full text-xs font-mono bg-slate-50 p-2 rounded border border-slate-200 select-all"
                />
              </div>
            )}

            <div className="flex flex-wrap justify-center gap-2">
              {modalQr.google_responder_uri && (
                <button
                  onClick={() => handleCopiarLink(modalQr.google_responder_uri)}
                  className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
                >
                  {copiado ? '✓ Copiado!' : 'Copiar link'}
                </button>
              )}
              <a
                href={`${BASE_API_URL}/api/publico/qrcode/${modalQr.uuid}?formato=png&escala=12`}
                download={`qrcode_${modalQr.id}.png`}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Baixar PNG
              </a>
              <a
                href={`${BASE_API_URL}/api/publico/qrcode/${modalQr.uuid}?formato=svg`}
                download={`qrcode_${modalQr.id}.svg`}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Baixar SVG
              </a>
              <button
                onClick={() => setModalQr(null)}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
