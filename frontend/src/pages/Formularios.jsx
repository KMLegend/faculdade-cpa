import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
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

export default function Formularios() {
  const { dado, carregando } = useApi('/api/admin/formularios')
  const [aba, setAba] = useState('DISCENTE_TURMA')
  if (carregando) return <Carregando />

  const lista = dado.filter((f) => f.tipo_instrumento === aba)
  const bloqueados = dado.filter((f) => !f.anonimato_ok)

  return (
    <>
      <Titulo sub="20 formulários no período · sincronizados com o Google Forms">
        Formulários
      </Titulo>

      <div className="mb-4 flex flex-wrap gap-2">
        <button className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">
          Sincronizar todos
        </button>
        <button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm">
          Publicar em lote
        </button>
        <button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm">
          Importar respostas
        </button>
        <button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm">
          Imprimir folhas
        </button>
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
            className={`rounded-md px-3 py-1.5 text-sm ${
              aba === k
                ? 'bg-slate-900 text-white'
                : 'border border-slate-300 bg-white hover:bg-slate-50'
            }`}
          >
            {nome} ({dado.filter((f) => f.tipo_instrumento === k).length})
          </button>
        ))}
      </div>

      <Tabela
        colunas={['Formulário', 'Matérias', 'Perguntas', 'Tempo', 'Sync', 'Status', 'Subm.', 'Ações']}
      >
        {lista.map((f) => {
          const [icone, tom, titulo] = SYNC[f.estado_sync]
          return (
            <tr key={f.id} className={!f.anonimato_ok ? 'bg-red-50' : undefined}>
              <td className="px-3 py-2">
                <p className="font-medium">{f.turma ?? f.titulo.split('— ')[1]}</p>
                {f.modulo && <p className="text-xs text-slate-500">Módulo {f.modulo}</p>}
              </td>
              <td className="px-3 py-2 tabular-nums">{f.total_ofertas || '—'}</td>
              <td className="px-3 py-2 tabular-nums">
                {f.total_perguntas}
                {f.acima_do_limite && (
                  <span title="acima do limite de alerta"> ⚠️</span>
                )}
              </td>
              <td className="px-3 py-2 tabular-nums text-slate-500">
                ~{f.tempo_estimado_min} min
              </td>
              <td className="px-3 py-2" title={titulo}>
                {icone}
              </td>
              <td className="px-3 py-2">
                <Selo tom={f.status === 'PUBLICADO' ? 'ok' : 'neutro'}>{f.status}</Selo>
              </td>
              <td className="px-3 py-2 tabular-nums">{f.submissoes || '—'}</td>
              <td className="px-3 py-2">
                <div className="flex gap-2 text-sm">
                  <Link
                    to={`/admin/formularios/${f.id}/previa`}
                    className="text-slate-700 underline"
                  >
                    Prévia
                  </Link>
                  {f.google_responder_uri && (
                    <>
                      <span className="text-slate-300">·</span>
                      <button className="text-slate-700 underline">QR</button>
                      <span className="text-slate-300">·</span>
                      <a
                        href={f.google_responder_uri}
                        target="_blank"
                        rel="noreferrer"
                        className="text-slate-700 underline"
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
    </>
  )
}
