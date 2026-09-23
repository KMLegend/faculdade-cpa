import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, FileSpreadsheet, GitCompareArrows, Users,
  ListChecks, ClipboardList, BarChart3, ShieldCheck,
} from 'lucide-react'
import { USANDO_MOCK } from '../api/client'

const LINKS = [
  { to: '/admin', end: true, icone: LayoutDashboard, texto: 'Painel' },
  { to: '/admin/grade/importar', icone: FileSpreadsheet, texto: 'Importar grade' },
  { to: '/admin/grade/importar/12/conciliar', icone: GitCompareArrows, texto: 'Conciliação' },
  { to: '/admin/grade', icone: ListChecks, texto: 'Grade do período' },
  { to: '/admin/cadastros', icone: Users, texto: 'Cadastros' },
  { to: '/admin/perguntas', icone: ClipboardList, texto: 'Perguntas' },
  { to: '/admin/formularios', icone: ShieldCheck, texto: 'Formulários' },
  { to: '/admin/relatorios', icone: BarChart3, texto: 'Relatórios' },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <aside className="shrink-0 border-b border-slate-200 bg-white lg:w-64 lg:border-b-0 lg:border-r">
        <div className="p-4">
          <p className="text-sm font-semibold tracking-tight">CPA · FPM</p>
          <p className="text-xs text-slate-500">Avaliação institucional</p>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-2 pb-2 lg:flex-col lg:overflow-visible">
          {LINKS.map(({ to, end, icone: Icone, texto }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm ${
                  isActive
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-700 hover:bg-slate-100'
                }`
              }
            >
              <Icone size={16} />
              <span className="whitespace-nowrap">{texto}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="min-w-0 flex-1">
        {USANDO_MOCK && (
          <div className="bg-amber-100 px-4 py-1.5 text-center text-xs text-amber-900">
            Modo demonstração — dados reais da grade 2026.2 e do ciclo 2025.2, sem backend
          </div>
        )}
        <main className="p-4 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
