export function Titulo({ children, sub }) {
  return (
    <header className="mb-6">
      <h1 className="text-xl font-semibold tracking-tight lg:text-2xl">{children}</h1>
      {sub && <p className="mt-1 text-sm text-slate-600">{sub}</p>}
    </header>
  )
}

export function Cartao({ rotulo, valor, detalhe, destaque }) {
  return (
    <div
      className={`rounded-lg border bg-white p-4 ${
        destaque ? 'border-slate-900' : 'border-slate-200'
      }`}
    >
      <p className="text-xs uppercase tracking-wide text-slate-500">{rotulo}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{valor}</p>
      {detalhe && <p className="mt-0.5 text-xs text-slate-500">{detalhe}</p>}
    </div>
  )
}

const TONS = {
  neutro: 'bg-slate-100 text-slate-700',
  ok: 'bg-emerald-100 text-emerald-800',
  atencao: 'bg-amber-100 text-amber-900',
  erro: 'bg-red-100 text-red-800',
  info: 'bg-sky-100 text-sky-800',
}

export function Selo({ tom = 'neutro', children }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${TONS[tom]}`}>
      {children}
    </span>
  )
}

export function Tabela({ colunas, children }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full min-w-[40rem] text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-left">
          <tr>
            {colunas.map((c) => (
              <th key={c} className="px-3 py-2 font-medium text-slate-600">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  )
}

export function Carregando({ children = 'Carregando…' }) {
  return <p className="py-8 text-center text-sm text-slate-500">{children}</p>
}
