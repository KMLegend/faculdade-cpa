import { Link } from 'react-router-dom'
import { UploadCloud } from 'lucide-react'
import { Titulo } from '../components/ui'

export default function ImportarGrade() {
  return (
    <>
      <Titulo sub="A grade do semestre em .xlsx, no layout institucional">
        Importar grade
      </Titulo>

      <div className="rounded-lg border-2 border-dashed border-slate-300 bg-white p-10 text-center">
        <UploadCloud size={32} className="mx-auto text-slate-400" />
        <p className="mt-3 font-medium">Arraste o arquivo .xlsx aqui</p>
        <p className="mt-1 text-sm text-slate-500">
          ou clique para escolher · máximo 5 MB
        </p>
        <button className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-sm text-white">
          Escolher arquivo
        </button>
      </div>

      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-medium">Última importação</h2>
        <p className="mt-1 text-sm text-slate-600">
          <strong>horario 20262.xlsx</strong> · 23/09/2026 · aguardando revisão
        </p>
        <p className="mt-1 text-sm text-slate-600">
          164 alocações · 17 turmas · 105 ofertas · 10 pendências
        </p>
        <Link
          to="/admin/grade/importar/12/conciliar"
          className="mt-3 inline-block rounded-md bg-slate-900 px-4 py-2 text-sm text-white"
        >
          Continuar conciliação ▸
        </Link>
      </div>

      <p className="mt-6 text-xs text-slate-500">
        Nada é gravado enquanto a conciliação não for aplicada. A planilha é um documento
        humano: typos, rótulos repetidos e bilhetes administrativos dentro das células
        exigem decisão de pessoa.
      </p>
    </>
  )
}
