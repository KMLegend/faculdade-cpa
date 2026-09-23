import { useEffect, useState } from 'react'
import { api } from '../api/client'

/** Busca simples: devolve {dado, carregando, erro}. */
export function useApi(url, deps = []) {
  const [estado, setEstado] = useState({ dado: null, carregando: true, erro: null })

  useEffect(() => {
    let vivo = true
    setEstado((e) => ({ ...e, carregando: true }))
    api
      .get(url)
      .then((r) => vivo && setEstado({ dado: r.data, carregando: false, erro: null }))
      .catch(
        (e) =>
          vivo &&
          setEstado({ dado: null, carregando: false, erro: e.mensagem ?? 'Falha' }),
      )
    return () => {
      vivo = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return estado
}
