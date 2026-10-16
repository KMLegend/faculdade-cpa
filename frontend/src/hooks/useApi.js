import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

/** Busca simples: devolve {dado, carregando, erro, recarregar}. */
export function useApi(url, deps = []) {
  const [estado, setEstado] = useState({ dado: null, carregando: true, erro: null })
  // Trocar este número força o efeito a rodar de novo sem mexer nas deps.
  const [gatilho, setGatilho] = useState(0)

  const recarregar = useCallback(() => setGatilho((n) => n + 1), [])

  useEffect(() => {
    let vivo = true
    // `null` = ainda não dá para consultar (ex.: período não resolvido).
    if (!url) {
      setEstado({ dado: null, carregando: true, erro: null })
      return undefined
    }
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
  }, [...deps, gatilho])

  return { ...estado, recarregar }
}
