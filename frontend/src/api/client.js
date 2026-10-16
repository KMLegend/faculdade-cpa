/**
 * Cliente HTTP único (doc 07 §4).
 *
 * `VITE_USE_MOCK=true` roda o painel com dados de exemplo, sem backend. Os dois
 * caminhos expõem a mesma interface — trocar é mudar a variável de ambiente,
 * não reescrever tela.
 */
import axios from 'axios'
import { clienteMock } from './mock'

export const USANDO_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const CHAVE_CREDENCIAL = 'cpa:credencial'

/** Credencial em sessionStorage: some ao fechar a aba (doc 07 §3.1). */
export function guardarCredencial(usuario, senha) {
  sessionStorage.setItem(CHAVE_CREDENCIAL, btoa(`${usuario}:${senha}`))
}

export function limparCredencial() {
  sessionStorage.removeItem(CHAVE_CREDENCIAL)
}

export function temCredencial() {
  return USANDO_MOCK || Boolean(sessionStorage.getItem(CHAVE_CREDENCIAL))
}

const real = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  timeout: 120000, // sincronizar o período inteiro pode demorar
})

real.interceptors.request.use((config) => {
  const credencial = sessionStorage.getItem(CHAVE_CREDENCIAL)
  if (credencial) config.headers.Authorization = `Basic ${credencial}`
  return config
})

/** Traduz o formato de erro do backend (doc 06 §4) em algo exibível. */
real.interceptors.response.use(
  (r) => r,
  (e) => {
    const corpo = e.response?.data
    if (e.response?.status === 401) limparCredencial()
    return Promise.reject({
      codigo: corpo?.erro ?? (e.response ? 'ERRO' : 'REDE'),
      mensagem:
        corpo?.mensagem ??
        (e.response
          ? `O servidor respondeu ${e.response.status}.`
          : 'Não foi possível falar com o servidor.'),
      detalhes: corpo?.detalhes ?? {},
      status: e.response?.status,
    })
  },
)

export const api = USANDO_MOCK ? clienteMock : real
