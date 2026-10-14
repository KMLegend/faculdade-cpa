import { useState } from 'react'
import { Selo } from './ui'

/**
 * Edição de pergunta com a política do doc 04 §5.1 e §6.1.
 *
 * O ponto central: ao mudar o enunciado, o sistema **pergunta** se é correção de
 * redação (mesmo código) ou mudança de sentido (código novo). Não adivinha — errar
 * aqui contamina o histórico em silêncio.
 */
export default function ModalPergunta({ pergunta, impacto, onFechar }) {
  const [texto, setTexto] = useState(pergunta.texto)
  const [decisao, setDecisao] = useState(null)
  const mudou = texto.trim() !== pergunta.texto.trim()

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4">
      <div className="my-8 w-full max-w-2xl rounded-lg bg-white shadow-xl">
        <header className="border-b border-slate-200 p-4">
          <p className="font-mono text-xs text-slate-500">
            Q{pergunta.codigo} · equivalência E{pergunta.equivalencia_id} · dimensão{' '}
            {pergunta.dimensao} · versão de texto {pergunta.versao_texto}
          </p>
          <h2 className="mt-1 text-lg font-semibold">Editar pergunta</h2>
        </header>

        <div className="space-y-4 p-4">
          <label className="block">
            <span className="text-sm font-medium">Enunciado</span>
            <textarea
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm"
            />
          </label>

          {mudou && (
            <fieldset className="rounded-lg border border-amber-300 bg-amber-50 p-3">
              <legend className="px-1 text-sm font-medium text-amber-900">
                O enunciado mudou
              </legend>
              <p className="mb-2 text-sm text-amber-900">
                As respostas antigas e as novas podem entrar na mesma média?
              </p>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="decisao"
                  className="mt-1"
                  onChange={() => setDecisao('versao')}
                />
                <span>
                  <strong>Sim</strong> — é correção de redação.
                  <br />
                  <span className="text-slate-600">
                    Mantém <strong>Q{pergunta.codigo}</strong>, versão de texto{' '}
                    {pergunta.versao_texto} → {pergunta.versao_texto + 1}. Comparativo com
                    2025.2 preservado.
                  </span>
                </span>
              </label>
              <label className="mt-2 flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="decisao"
                  className="mt-1"
                  onChange={() => setDecisao('novo')}
                />
                <span>
                  <strong>Não</strong> — o sentido mudou.
                  <br />
                  <span className="text-slate-600">
                    Cria <strong>Q164</strong> e desativa Q{pergunta.codigo}. No
                    comparativo, a antiga aparece como descontinuada e a nova sem série
                    histórica.
                  </span>
                </span>
              </label>
              <p className="mt-2 text-xs text-amber-800">
                Na dúvida, código novo: perder um comparativo é reparável, somar duas
                perguntas diferentes não.
              </p>
            </fieldset>
          )}

          {decisao === 'novo' && (
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm">
              ⚠️ A equivalência <strong>E{pergunta.equivalencia_id}</strong> liga esta
              pergunta às versões dos outros segmentos. Se só a versão{' '}
              {pergunta.segmento.toLowerCase()} mudou de sentido, elas deixaram de ser a
              mesma pergunta.
              <div className="mt-2 flex gap-3">
                <label className="flex items-center gap-1.5">
                  <input type="radio" name="equiv" defaultChecked /> Manter em E
                  {pergunta.equivalencia_id}
                </label>
                <label className="flex items-center gap-1.5">
                  <input type="radio" name="equiv" /> Abrir grupo próprio
                </label>
              </div>
            </div>
          )}

          <section className="rounded-lg border border-slate-200 p-3">
            <h3 className="text-sm font-medium">Alcance desta alteração</h3>
            <p className="mt-1 text-sm text-slate-700">
              Usada em <strong>{impacto.formularios}</strong> formulários deste período —{' '}
              {impacto.publicados} publicados, <strong>{impacto.congelados}</strong> com
              respostas.
            </p>
            {impacto.congelados > 0 ? (
              <div className="mt-2 rounded-md border border-red-300 bg-red-50 p-2 text-sm">
                <p className="text-red-900">
                  🔒 {impacto.congelados} formulários estão congelados e{' '}
                  <strong>não receberão</strong> esta alteração — editar um Google Forms
                  com respostas corrompe a série.
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm">
                    Aplicar no próximo ciclo
                  </button>
                  <button className="rounded-md border border-red-400 bg-white px-3 py-1.5 text-sm text-red-900">
                    Encerrar e reabrir os {impacto.congelados}
                  </button>
                </div>
              </div>
            ) : (
              <p className="mt-2 text-sm text-emerald-800">
                Nenhum formulário congelado — a alteração entra na próxima sincronização.
              </p>
            )}
          </section>
        </div>

        <footer className="flex items-center gap-2 border-t border-slate-200 p-4">
          <button
            onClick={onFechar}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm"
          >
            Cancelar
          </button>
          <button className="ml-auto rounded-md border border-slate-300 px-4 py-2 text-sm">
            {pergunta.ativo ? 'Desativar pergunta' : 'Reativar pergunta'}
          </button>
          <button
            disabled={mudou && !decisao}
            title={mudou && !decisao ? 'Escolha o tipo de mudança acima' : undefined}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Salvar
          </button>
        </footer>
      </div>
    </div>
  )
}
