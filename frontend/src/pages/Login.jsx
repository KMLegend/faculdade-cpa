import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, guardarCredencial } from '../api/client'

export default function Login() {
  const [usuario, setUsuario] = useState('cpa')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState(null)
  const [entrando, setEntrando] = useState(false)
  const navegar = useNavigate()

  async function entrar(evento) {
    evento.preventDefault()
    setErro(null)
    setEntrando(true)
    guardarCredencial(usuario, senha)
    try {
      // /health não exige auth; a validação real é numa rota protegida.
      await api.get('/api/admin/periodos-letivos')
      navegar('/admin')
    } catch (e) {
      setErro(
        e.status === 401 ? 'Usuário ou senha incorretos.' : e.mensagem,
      )
    } finally {
      setEntrando(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={entrar}
        className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6"
      >
        <h1 className="text-lg font-semibold">CPA · FPM</h1>
        <p className="mt-1 text-sm text-slate-600">Painel administrativo</p>

        <label className="mt-6 block text-sm">
          Usuário
          <input
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            autoComplete="username"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="mt-3 block text-sm">
          Senha
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            autoComplete="current-password"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          />
        </label>

        {erro && (
          <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
            {erro}
          </p>
        )}

        <button
          type="submit"
          disabled={entrando || !senha}
          className="mt-5 w-full rounded-md bg-slate-900 py-2 text-sm text-white disabled:bg-slate-300"
        >
          {entrando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </main>
  )
}
