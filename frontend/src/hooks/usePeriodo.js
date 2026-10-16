import { useEffect, useState } from 'react'
import { api } from '../api/client'

/** Período letivo ativo — quase toda consulta do painel depende dele. */
export function usePeriodo() {
  const [periodo, setPeriodo] = useState(null)
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    let vivo = true
    api
      .get('/api/admin/periodos-letivos')
      .then((r) => {
        if (!vivo) return
        const lista = r.data ?? []
        setPeriodo(lista.find((p) => p.ativo) ?? lista[0] ?? null)
      })
      .catch(() => vivo && setPeriodo(null))
      .finally(() => vivo && setCarregando(false))
    return () => {
      vivo = false
    }
  }, [])

  return { periodo, carregando }
}
