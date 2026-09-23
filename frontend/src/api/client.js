/**
 * Cliente HTTP único (doc 07 §4).
 *
 * VITE_USE_MOCK=true faz o painel rodar com dados de exemplo, sem backend.
 * Trocar para o backend real é mudar a variável de ambiente — a interface é a
 * mesma nos dois casos (doc 06 define os payloads).
 */
import axios from 'axios'
import { clienteMock } from './mock'

export const USANDO_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const real = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  timeout: 30000,
})

/** Traduz o formato de erro do backend (doc 06 §4) em algo exibível. */
real.interceptors.response.use(
  (r) => r,
  (e) => {
    const corpo = e.response?.data
    return Promise.reject({
      codigo: corpo?.erro ?? 'REDE',
      mensagem: corpo?.mensagem ?? 'Não foi possível falar com o servidor.',
      detalhes: corpo?.detalhes ?? {},
      status: e.response?.status,
    })
  },
)

export const api = USANDO_MOCK ? clienteMock : real
