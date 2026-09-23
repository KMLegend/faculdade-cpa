import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { Titulo, Tabela, Selo, Carregando } from '../components/ui'

export default function Cadastros() {
  const professores = useApi('/api/admin/professores')
  const disciplinas = useApi('/api/admin/disciplinas')
  const cursos = useApi('/api/admin/cursos')
  const [aba, setAba] = useState('professores')
  if (professores.carregando || disciplinas.carregando || cursos.carregando)
    return <Carregando />

  const ABAS = [
    ['professores', `Professores (${professores.dado.length})`],
    ['disciplinas', `Disciplinas (${disciplinas.dado.length})`],
    ['cursos', `Cursos (${cursos.dado.length})`],
  ]

  return (
    <>
      <Titulo sub="Alimentados pela importação da grade; editáveis para correção">
        Cadastros
      </Titulo>

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
            {nome}
          </button>
        ))}
      </div>

      {aba === 'professores' && (
        <>
          <Tabela colunas={['Nome de exibição', 'Nome completo', 'Ofertas']}>
            {professores.dado.map((p) => (
              <tr key={p.id}>
                <td className="px-3 py-2 font-medium">{p.nome_exibicao}</td>
                <td className="px-3 py-2 text-slate-500">
                  {p.nome_completo ?? (
                    <Selo tom="atencao">exigido antes do relatório oficial</Selo>
                  )}
                </td>
                <td className="px-3 py-2 tabular-nums">{p.ofertas}</td>
              </tr>
            ))}
          </Tabela>
          <p className="mt-2 text-xs text-slate-500">
            A planilha traz só o primeiro nome. Homônimos entre cursos são risco real: o
            sistema nunca funde automaticamente.
          </p>
        </>
      )}

      {aba === 'disciplinas' && (
        <Tabela colunas={['Disciplina', 'Curso']}>
          {disciplinas.dado.map((d) => (
            <tr key={d.id}>
              <td className="px-3 py-2">{d.nome}</td>
              <td className="px-3 py-2 text-slate-500">
                {d.curso_id ?? 'interdisciplinar'}
              </td>
            </tr>
          ))}
        </Tabela>
      )}

      {aba === 'cursos' && (
        <>
          <Tabela colunas={['Curso', 'Slug']}>
            {cursos.dado.map((c) => (
              <tr key={c.id}>
                <td className="px-3 py-2 font-medium">{c.nome}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-500">{c.slug}</td>
              </tr>
            ))}
          </Tabela>
          <p className="mt-2 text-xs text-slate-500">
            Não existe curso “Ciclo Básico”: as abas compartilhadas expandem nos cursos
            reais que a instrução de matrícula declara.
          </p>
        </>
      )}
    </>
  )
}
