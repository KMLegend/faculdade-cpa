import { useApi } from '../hooks/useApi'
import { Titulo, Tabela, Selo, Carregando } from '../components/ui'

export default function Grade() {
  const turmas = useApi('/api/admin/turmas')
  const ofertas = useApi('/api/admin/ofertas')
  if (turmas.carregando || ofertas.carregando) return <Carregando />

  const multi = ofertas.dado.filter((o) => o.qtd_turmas > 1)
  const semTurma = ofertas.dado.filter((o) => o.qtd_turmas === 0)
  const nome = (id) => turmas.dado.find((t) => t.id === id)?.rotulo ?? `#${id}`

  return (
    <>
      <Titulo sub="Período 2026.2 · importado de horario 20262.xlsx">
        Grade do período
      </Titulo>

      <h2 className="mb-2 text-sm font-medium text-slate-700">
        {turmas.dado.length} turmas — chave: curso + turno + período
      </h2>
      <Tabela colunas={['#', 'Turma', 'Módulo', 'Ofertas', 'Perguntas', 'Origem na planilha']}>
        {turmas.dado.map((t) => (
          <tr key={t.id}>
            <td className="px-3 py-2 text-slate-500">{t.id}</td>
            <td className="px-3 py-2 font-medium">
              {t.rotulo}
              {t.compartilhada_ciclo_basico && <Selo tom="info"> ciclo básico</Selo>}
            </td>
            <td className="px-3 py-2 text-slate-600">{t.modulo ?? '—'}</td>
            <td className="px-3 py-2 tabular-nums">{t.total_ofertas}</td>
            <td className="px-3 py-2 tabular-nums">{t.total_perguntas}</td>
            <td className="px-3 py-2 text-xs text-slate-500">
              {t.rotulos_origem.join(', ')}
              <br />
              {t.colunas_origem.join(' · ')}
            </td>
          </tr>
        ))}
      </Tabela>
      <p className="mb-8 mt-2 text-xs text-slate-500">
        Repare em quantas colunas da planilha alimentam cada turma: “Sub - Turma A” e “Sub
        - Turma B” são a mesma turma de alunos.
      </p>

      <h2 className="mb-2 text-sm font-medium text-slate-700">
        {multi.length} ofertas atendem mais de uma turma — um único bloco serve a todas
      </h2>
      <Tabela colunas={['Oferta', 'Turmas']}>
        {multi.slice(0, 15).map((o) => (
          <tr key={o.id}>
            <td className="px-3 py-2">
              {o.disciplina} · <strong>Prof. {o.professor}</strong>
              <Selo tom="info"> {o.qtd_turmas}</Selo>
            </td>
            <td className="px-3 py-2 text-xs text-slate-600">
              {o.turmas.map(nome).join(' · ')}
            </td>
          </tr>
        ))}
      </Tabela>

      <h2 className="mb-2 mt-8 text-sm font-medium text-slate-700">
        {semTurma.length} ofertas sem turma — nascem não avaliáveis
      </h2>
      <Tabela colunas={['Oferta', 'Origem']}>
        {semTurma.map((o) => (
          <tr key={o.id}>
            <td className="px-3 py-2">
              {o.disciplina} · <strong>Prof. {o.professor}</strong>
            </td>
            <td className="px-3 py-2 text-xs text-slate-500">
              coluna de Estágio Supervisionado
            </td>
          </tr>
        ))}
      </Tabela>
    </>
  )
}
