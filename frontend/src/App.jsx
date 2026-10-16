import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import RotaProtegida from './components/RotaProtegida'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ImportarGrade from './pages/ImportarGrade'
import Conciliacao from './pages/Conciliacao'
import Grade from './pages/Grade'
import Cadastros from './pages/Cadastros'
import Perguntas from './pages/Perguntas'
import Formularios from './pages/Formularios'
import Previa from './pages/Previa'
import Relatorios from './pages/Relatorios'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin" replace />} />
      <Route path="/login" element={<Login />} />
      <Route element={<RotaProtegida />}>
        <Route path="/admin" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="grade" element={<Grade />} />
          <Route path="grade/importar" element={<ImportarGrade />} />
          <Route path="grade/conciliacao" element={<Conciliacao />} />
          <Route path="grade/importar/:id/conciliar" element={<Conciliacao />} />
          <Route path="cadastros" element={<Cadastros />} />
          <Route path="perguntas" element={<Perguntas />} />
          <Route path="formularios" element={<Formularios />} />
          <Route path="formularios/:id/previa" element={<Previa />} />
          <Route path="relatorios" element={<Relatorios />} />
        </Route>
      </Route>
    </Routes>
  )
}
