import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { Titulo, Tabela, Selo, Carregando } from '../components/ui'

const ABAS = [
  ['DISCENTE', 'Discente'],
  ['DOCENTE', 'Docente'],
  ['TECNICO_ADMINISTRATIVO', 'Técnico-adm.'],
  ['COMUNIDADE', 'Comunidade'],
]

export default function Perguntas() {
  const { dado, carregando } = useApi('/api/admin/perguntas')
  const [aba, setAba] = useState('DISCENTE')
  if (carregando) return <Carregando />

  const lista = dado.filter((p) => p.segmento === aba)
  const institucionais = lista.filter((p) => !p.por_materia)
  const materia = lista.filter((p) => p.por_materia)

  const linha = (p) => (
    <tr key={p.codigo} className={!p.ativo ? 'bg-slate-50 text-slate-400' : undefined}>
      <td className="px-3 py-2 font-mono text-xs">Q{p.codigo}</td>
      <td className="px-3 py-2">
        {p.texto}
        {!p.ativo && <Selo tom="atencao"> desativada (duplicata)</Selo>}
      </td>
      <td className="px-3 py-2 text-center tabular-nums">{p.dimensao}</td>
      <td className="px-3 py-2">
        <Selo tom={p.bloco === 'INSTITUCIONAL' ? 'neutro' : 'info'}>{p.bloco}</Selo>
      </td>
      <td className="px-3 py-2 text-center font-mono text-xs text-slate-500">
        E{p.equivalencia_id}
      </td>
    </tr>
  )

  return (
    <>
      <Titulo sub="163 perguntas oficiais da CPA · 67 grupos de equivalência">
        Banco de perguntas
      </Titulo>

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
            {nome} ({dado.filter((p) => p.segmento === k).length})
          </button>
        ))}
      </div>

      {materia.length > 0 && (
        <>
          <h2 className="mb-2 text-sm font-medium text-slate-700">
            Repetidas por matéria — {materia.length} perguntas × cada oferta da turma
          </h2>
          <Tabela colunas={['Código', 'Pergunta', 'Dim.', 'Bloco', 'Equiv.']}>
            {materia.map(linha)}
          </Tabela>
          <p className="mb-6 mt-2 text-xs text-slate-500">
            Em 2025.2 estas apareciam com o sufixo “(Disciplina - Professor)” digitado à mão.
            Agora o rótulo vem da oferta, já conciliada.
          </p>
        </>
      )}

      <h2 className="mb-2 mt-6 text-sm font-medium text-slate-700">
        Bloco institucional — {institucionais.length} perguntas, uma vez por formulário
      </h2>
      <Tabela colunas={['Código', 'Pergunta', 'Dim.', 'Bloco', 'Equiv.']}>
        {institucionais.map(linha)}
      </Tabela>
    </>
  )
}
