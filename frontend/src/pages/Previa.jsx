import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Titulo, Cartao, Selo, Carregando, Erro } from '../components/ui'

const NOME_INSTRUMENTO = {
  DISCENTE_TURMA: 'Formulário da turma',
  DOCENTE: 'Instrumento docente',
  TECNICO_ADMINISTRATIVO: 'Instrumento técnico-administrativo',
  COMUNIDADE: 'Instrumento da comunidade externa',
}

function BlocoPerguntas({ titulo, selo, sufixo, perguntas }) {
  return (
    <details className="self-start rounded-lg border border-slate-200 bg-white p-3">
      <summary className="cursor-pointer text-sm">
        {selo}
        <span className="font-medium">{titulo}</span>
        {sufixo && <span className="text-slate-500"> · {sufixo}</span>}{' '}
        <span className="text-slate-500">— {perguntas.length} perguntas</span>
      </summary>
      <ol className="mt-2 space-y-1 text-sm text-slate-700">
        {perguntas.map((p) => (
          <li key={p.codigo} className="flex gap-2">
            <span className="shrink-0 font-mono text-xs text-slate-400">Q{p.codigo}</span>
            <span>
              {p.texto}
              {p.bloco !== 'INSTITUCIONAL' && (
                <>
                  {' '}
                  <Selo tom="neutro">{p.bloco}</Selo>
                </>
              )}
            </span>
          </li>
        ))}
      </ol>
    </details>
  )
}

export default function Previa() {
  const { id = '1' } = useParams()
  const { dado, carregando, erro, recarregar } = useApi(
    `/api/admin/formularios/${id}/previa`,
    [id],
  )
  const [sincronizando, setSincronizando] = useState(false)
  const [resultado, setResultado] = useState(null)

  async function sincronizar() {
    setSincronizando(true)
    setResultado(null)
    try {
      const { data } = await api.post(`/api/admin/formularios/${id}/sincronizar`)
      const texto = {
        CRIADO: 'Formulário criado no Google.',
        ATUALIZADO: 'Estrutura atualizada no Google.',
        SEM_MUDANCA: 'Nada a enviar — a estrutura no Google já está igual.',
      }[data.resultado] ?? data.resultado
      setResultado({
        tom: 'ok',
        texto: `${texto}${data.requests ? ` (${data.requests} alterações)` : ''}`,
      })
      recarregar()
    } catch (e) {
      setResultado({ tom: 'erro', texto: e.mensagem ?? 'Falha ao sincronizar.' })
    } finally {
      setSincronizando(false)
    }
  }

  if (carregando) return <Carregando />
  if (erro || !dado) return <Erro>{erro ?? 'Formulário não encontrado.'}</Erro>

  const {
    formulario,
    turma,
    blocos_institucionais: institucionais,
    blocos_materia: materia,
    perguntas_por_materia: qtdPorMateria,
    diff,
  } = dado
  const ehTurma = formulario.tipo_instrumento === 'DISCENTE_TURMA'

  return (
    <>
      <Titulo
        sub={
          ehTurma
            ? `${turma.rotulo}${turma.modulo ? ` · Módulo ${turma.modulo}` : ''}`
            : NOME_INSTRUMENTO[formulario.tipo_instrumento]
        }
      >
        Prévia do formulário
      </Titulo>

      <p className="mb-4 text-sm text-slate-600">
        Estrutura exata que será enviada ao Google. É a última chance de pegar um erro de
        importação antes de o aluno responder.
      </p>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Cartao
          rotulo="Perguntas"
          valor={dado.total_perguntas}
          detalhe={
            formulario.acima_do_limite ? '⚠️ acima do limite de alerta' : undefined
          }
          destaque={formulario.acima_do_limite}
        />
        <Cartao
          rotulo="Páginas"
          valor={dado.total_paginas}
          detalhe="quebras no Google"
        />
        <Cartao rotulo="Tempo" valor={`~${dado.tempo_estimado_min} min`} />
        <Cartao
          rotulo={ehTurma ? 'Matérias' : 'Blocos'}
          valor={ehTurma ? dado.total_ofertas : institucionais.length}
        />
      </section>

      {diff ? (
        diff.incluidas + diff.alteradas + diff.removidas === 0 ? (
          <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
            Sem mudança de estrutura — a sincronização não enviaria nenhuma alteração ao
            Google.
          </div>
        ) : (
          <div className="mt-4 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">
            <strong>Diff contra o Google:</strong> + {diff.incluidas} · ~ {diff.alteradas}{' '}
            · − {diff.removidas} · = {diff.inalteradas} inalteradas{' '}
            <span className="text-sky-700">({diff.unidade})</span>
          </div>
        )
      ) : (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
          Ainda não existe no Google — a sincronização vai <strong>criar</strong> este
          formulário.
        </div>
      )}

      <h2 className="mb-2 mt-8 text-sm font-medium text-slate-700">
        Bloco institucional — {dado.perguntas_institucionais} perguntas, uma vez, em{' '}
        {institucionais.length} dimensões
      </h2>
      <div className="grid items-start gap-2">
        {institucionais.map((b) => (
          <BlocoPerguntas
            key={b.dimensao}
            titulo={b.nome}
            selo={
              <>
                <Selo tom="info">Dim. {b.dimensao}</Selo>{' '}
              </>
            }
            perguntas={b.perguntas}
          />
        ))}
      </div>

      {ehTurma && (
        <>
          <h2 className="mb-2 mt-8 text-sm font-medium text-slate-700">
            Blocos por matéria — {qtdPorMateria} perguntas × {materia.length} ofertas
          </h2>
          {/* items-start: sem isto, um cartão fechado estica até a altura do
              cartão aberto ao lado e deixa um vazio enorme na tela. */}
          <div className="grid items-start gap-2 lg:grid-cols-2">
            {materia.map((b) => (
              <BlocoPerguntas
                key={b.oferta_id}
                titulo={b.disciplina}
                selo={null}
                sufixo={`Prof. ${b.professor}`}
                perguntas={b.perguntas}
              />
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Disciplinas repetidas com professores diferentes são blocos independentes — é
            o professor daquela matéria que está sendo avaliado.
          </p>
        </>
      )}

      <div className="mt-8 flex gap-2">
        <Link
          to="/admin/formularios"
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm"
        >
          Voltar
        </Link>
        <button
          onClick={sincronizar}
          disabled={sincronizando}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {sincronizando ? 'Sincronizando…' : 'Sincronizar com o Google ▸'}
        </button>
      </div>
      {resultado && (
        <p
          className={`mt-3 rounded-md border p-2 text-sm ${
            resultado.tom === 'erro'
              ? 'border-red-200 bg-red-50 text-red-900'
              : 'border-emerald-200 bg-emerald-50 text-emerald-900'
          }`}
        >
          {resultado.texto}
        </p>
      )}
    </>
  )
}
