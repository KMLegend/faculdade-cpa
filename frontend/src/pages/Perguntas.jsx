import { useState } from 'react'
import { Pencil, Plus } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Titulo, Tabela, Selo, Carregando, Erro } from '../components/ui'
import ModalPergunta from '../components/ModalPergunta'

// A aba é o instrumento. A pergunta não carrega `segmento`: o backend expõe
// `tipo_instrumento`, e é dele que o segmento decorre.
const ABAS = [
  ['DISCENTE_TURMA', 'Discente'],
  ['DOCENTE', 'Docente'],
  ['TECNICO_ADMINISTRATIVO', 'Técnico-adm.'],
  ['COMUNIDADE', 'Comunidade'],
]

/** Repetida por oferta. `bloco` é quem diz isso — não existe `por_materia`. */
const porMateria = (p) => p.bloco !== 'INSTITUCIONAL'

export default function Perguntas() {
  const { dado, carregando, erro } = useApi('/api/admin/perguntas')
  const dimensoes = useApi('/api/admin/dimensoes')
  const [aba, setAba] = useState('DISCENTE_TURMA')
  const [editando, setEditando] = useState(null)

  async function abrirEdicao(p) {
    const { data } = await api.get(`/api/admin/perguntas/${p.codigo}/impacto`)
    setEditando({ pergunta: p, impacto: data })
  }

  if (erro) return <Erro>{erro}</Erro>
  if (carregando || !dado) return <Carregando />

  // `dimensao_id` é a chave da tabela; o número SINAES (1 a 10) vem do catálogo.
  const numeroDim = (id) => dimensoes.dado?.find((d) => d.id === id)?.numero ?? '—'
  const lista = dado.filter((p) => p.tipo_instrumento === aba)
  const institucionais = lista.filter((p) => !porMateria(p))
  const materia = lista.filter(porMateria)
  const equivalencias = new Set(dado.map((p) => p.equivalencia_id)).size

  const linha = (p) => (
    <tr key={p.codigo} className={!p.ativo ? 'bg-slate-50 text-slate-400' : undefined}>
      <td className="px-3 py-2 font-mono text-xs">Q{p.codigo}</td>
      <td className="px-3 py-2">
        {p.texto}
        {p.versao_texto > 1 && (
          <Selo tom="neutro"> redação v{p.versao_texto}</Selo>
        )}
        {!p.ativo && <Selo tom="atencao"> desativada (duplicata)</Selo>}
      </td>
      <td className="px-3 py-2 text-center tabular-nums">{numeroDim(p.dimensao_id)}</td>
      <td className="px-3 py-2">
        <Selo tom={p.bloco === 'INSTITUCIONAL' ? 'neutro' : 'info'}>{p.bloco}</Selo>
      </td>
      <td className="px-3 py-2 text-center font-mono text-xs text-slate-500">
        E{p.equivalencia_id}
      </td>
      <td className="px-3 py-2 text-right">
        <button
          onClick={() => abrirEdicao(p)}
          title={`Editar Q${p.codigo}`}
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50"
        >
          <Pencil size={12} />
          Editar
        </button>
      </td>
    </tr>
  )

  const COLUNAS = ['Código', 'Pergunta', 'Dim.', 'Bloco', 'Equiv.', '']

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <Titulo
          sub={`${dado.length} perguntas oficiais da CPA · ${equivalencias} grupos de equivalência`}
        >
          Banco de perguntas
        </Titulo>
        <button className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-4 py-2 text-sm text-white">
          <Plus size={15} />
          Nova pergunta
        </button>
      </div>

      <div className="mb-4 rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
        O <strong>código</strong> (Q1–Q163) é a identidade permanente da pergunta: nunca
        renumerado, nunca reutilizado. A <strong>equivalência</strong> (E1–E67) liga a
        mesma pergunta entre segmentos. Nenhum cruzamento usa o texto.
      </div>

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
            {nome} ({dado.filter((p) => p.tipo_instrumento === k).length})
          </button>
        ))}
      </div>

      {materia.length > 0 && (
        <>
          <h2 className="mb-2 text-sm font-medium text-slate-700">
            Repetidas por matéria — {materia.length} perguntas × cada oferta da turma
          </h2>
          <Tabela colunas={COLUNAS}>{materia.map(linha)}</Tabela>
          <p className="mb-6 mt-2 text-xs text-slate-500">
            Em 2025.2 estas apareciam com o sufixo “(Disciplina - Professor)” digitado à mão.
            Agora o rótulo vem da oferta, já conciliada.
          </p>
        </>
      )}

      <h2 className="mb-2 mt-6 text-sm font-medium text-slate-700">
        Bloco institucional — {institucionais.length} perguntas, uma vez por formulário
      </h2>
      <Tabela colunas={COLUNAS}>{institucionais.map(linha)}</Tabela>

      {editando && (
        <ModalPergunta
          pergunta={editando.pergunta}
          impacto={editando.impacto}
          dimensao={numeroDim(editando.pergunta.dimensao_id)}
          segmento={
            ABAS.find(([k]) => k === editando.pergunta.tipo_instrumento)?.[1] ??
            'deste segmento'
          }
          onFechar={() => setEditando(null)}
        />
      )}
    </>
  )
}
