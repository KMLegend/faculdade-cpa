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
  // A última importação aplicada é o que data a grade em uso.
  const importacoes = useApi('/api/admin/importacoes')

  if (turmas.carregando || ofertas.carregando || forms.carregando) {
    return <Carregando />
  }

  const publicados = forms.dado.filter((f) => f.status === 'PUBLICADO')
  const submissoes = forms.dado.reduce((s, f) => s + f.submissoes, 0)
  const semResposta = publicados.filter((f) => f.submissoes === 0).length
  const alertaAnonimato = forms.dado.filter((f) => !f.anonimato_ok)

  const aplicada = importacoes.dado?.find((i) => i.aplicada_em)
  const subtitulo = [
    periodo ? `Período letivo ${periodo.codigo}` : null,
    aplicada
      ? `grade aplicada em ${new Date(aplicada.aplicada_em).toLocaleDateString('pt-BR')}`
      : 'nenhuma importação de grade aplicada',
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <>
      <Titulo sub={subtitulo}>Painel</Titulo>

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
        <Cartao
          rotulo="Submissões"
          valor={submissoes}
          detalhe="referência externa 2025.2: 193"
          destaque
        />
        <Cartao
          rotulo="Sem resposta"
          valor={semResposta}
          detalhe="aplicação não aconteceu"
        />
      </section>

      <h2 className="mb-3 mt-8 text-sm font-medium text-slate-700">
        Adesão por instrumento
      </h2>
      {/* Sem coluna de 2025.2: as respostas daquele ciclo não estão no sistema
          (ficaram fora do MVP), então ela só sabia mostrar "—". */}
      {adesao.dado?.instrumentos && (
        <Tabela colunas={['Instrumento', 'Formulários', 'Submissões']}>
          {adesao.dado.instrumentos.map((i) => (
            <tr key={i.tipo_instrumento ?? i.nome}>
              <td className="px-3 py-2">
                {NOME_INSTRUMENTO[i.tipo_instrumento] ?? i.nome ?? i.tipo_instrumento}
              </td>
              <td className="px-3 py-2 tabular-nums">{i.formularios}</td>
              <td className="px-3 py-2 font-medium tabular-nums">
                {i.submissoes || <Selo tom="atencao">nenhuma</Selo>}
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
        Referência do ciclo anterior (2025.2, aplicado de 24/11 a 01/12/2025):{' '}
        <strong>193 respostas</strong> no total, nenhuma da comunidade externa — a
        lacuna mais séria do instrumento atual. Número vindo do{' '}
        <code>consolidado_cpa.xlsx</code>; aquelas respostas não estão neste banco,
        por isso não há comparação por instrumento.
      </p>
    </>
  )
}
