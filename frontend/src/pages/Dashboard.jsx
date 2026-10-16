import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { usePeriodo } from '../hooks/usePeriodo'
import { Titulo, Cartao, Tabela, Selo, Carregando } from '../components/ui'

/** O backend devolve o enum; a tela mostra o nome legível. */
const NOME_INSTRUMENTO = {
  DISCENTE_TURMA: 'Turma',
  DOCENTE: 'Docente',
  TECNICO_ADMINISTRATIVO: 'Técnico-administrativo',
  COMUNIDADE: 'Comunidade',
}

export default function Dashboard() {
  const turmas = useApi('/api/admin/turmas')
  const ofertas = useApi('/api/admin/ofertas')
  const forms = useApi('/api/admin/formularios')
  const { periodo } = usePeriodo()
  const adesao = useApi(
    periodo ? `/api/admin/relatorios/adesao?periodo_letivo_id=${periodo.id}` : null,
    [periodo?.id],
  )

  if (turmas.carregando || ofertas.carregando || forms.carregando) {
    return <Carregando />
  }

  const publicados = forms.dado.filter((f) => f.status === 'PUBLICADO')
  const submissoes = forms.dado.reduce((s, f) => s + f.submissoes, 0)
  const semResposta = publicados.filter((f) => f.submissoes === 0).length
  const alertaAnonimato = forms.dado.filter((f) => !f.anonimato_ok)

  return (
    <>
      <Titulo sub="Período letivo 2026.2 · grade importada em 23/09/2026">
        Painel
      </Titulo>

      {alertaAnonimato.length > 0 && (
        <div className="mb-6 rounded-lg border border-red-300 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-900">
            {alertaAnonimato.length} formulário com coleta de e-mail ativada no Google
          </p>
          <p className="mt-1 text-sm text-red-800">
            A publicação está bloqueada até que a configuração seja corrigida — é o
            anonimato da avaliação que está em jogo.
          </p>
          <Link
            to="/admin/formularios"
            className="mt-2 inline-block text-sm font-medium text-red-900 underline"
          >
            Ver formulários
          </Link>
        </div>
      )}

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Cartao rotulo="Turmas" valor={turmas.dado.length} detalhe="curso + turno + período" />
        <Cartao
          rotulo="Ofertas"
          valor={ofertas.dado.length}
          detalhe={`${ofertas.dado.filter((o) => o.avaliavel).length} avaliáveis`}
        />
        <Cartao
          rotulo="Formulários"
          valor={forms.dado.length}
          detalhe={`${publicados.length} publicados`}
        />
        <Cartao rotulo="Submissões" valor={submissoes} detalhe="2025.2: 193" destaque />
        <Cartao
          rotulo="Sem resposta"
          valor={semResposta}
          detalhe="aplicação não aconteceu"
        />
      </section>

      <h2 className="mb-3 mt-8 text-sm font-medium text-slate-700">
        Adesão por instrumento
      </h2>
      {adesao.dado?.instrumentos && (
        <Tabela colunas={['Instrumento', 'Formulários', 'Submissões', '2025.2']}>
          {adesao.dado.instrumentos.map((i) => (
            <tr key={i.tipo_instrumento ?? i.nome}>
              <td className="px-3 py-2">
                {NOME_INSTRUMENTO[i.tipo_instrumento] ?? i.nome ?? i.tipo_instrumento}
              </td>
              <td className="px-3 py-2 tabular-nums">{i.formularios}</td>
              <td className="px-3 py-2 font-medium tabular-nums">
                {i.submissoes || <Selo tom="atencao">nenhuma</Selo>}
              </td>
              <td className="px-3 py-2 tabular-nums text-slate-500">
                {i.em_2025 ?? '—'}
              </td>
            </tr>
          ))}
        </Tabela>
      )}

      {adesao.dado?.publicados_sem_resposta?.length > 0 && (
        <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
          <strong className="text-amber-900">
            {adesao.dado.publicados_sem_resposta.length} formulário(s) publicado(s)
            sem nenhuma resposta
          </strong>
          <p className="mt-1 text-amber-800">
            A aplicação não aconteceu nessas turmas — é o que a CPA precisa cobrar.
          </p>
        </div>
      )}
      <p className="mt-3 text-xs text-slate-500">
        Referência: o ciclo 2025.2 teve 193 respostas no total, e a comunidade externa
        não teve nenhuma — é a lacuna mais séria do instrumento atual.
      </p>
    </>
  )
}
