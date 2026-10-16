"""Gera o GOOGLE_REFRESH_TOKEN e localiza a pasta do Drive (doc 10 §4).

Roda UMA vez, na máquina de quem tem acesso à conta institucional da CPA.
Abre o consentimento no navegador, troca o código e imprime as variáveis
prontas para o `.env`.

    python -m scripts.autorizar_google
    python -m scripts.autorizar_google --pasta "CPA 2026.2"

⚠️ O refresh token é uma credencial de longa duração: trate como senha. Ele não
é gravado em disco por este script — você copia para o `.env`, que não é
versionado.
"""

from __future__ import annotations

import argparse
import os
import sys

#: Escopos mínimos (doc 10 §4.2). `drive.file` dá acesso apenas aos arquivos
#: que o próprio app criar — nunca ao resto do Drive da conta.
ESCOPOS = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


def _exigir(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        sys.exit(
            f"Falta {nome}.\n"
            f"Defina antes de rodar:\n"
            f'  export {nome}="..."\n'
            f"Os dois valores vêm do cliente OAuth criado no Google Cloud — ver\n"
            f".agent/02-especificacao/anexos/C_configurar_google_cloud.md"
        )
    return valor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pasta",
        default="CPA — Formulários",
        help="Nome da pasta no Drive onde os formulários serão criados.",
    )
    parser.add_argument(
        "--porta", type=int, default=8765, help="Porta local do fluxo OAuth."
    )
    args = parser.parse_args()

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit(
            "Dependências do Google ausentes. Instale com:\n"
            "  pip install google-auth google-auth-oauthlib google-api-python-client"
        )

    client_id = _exigir("GOOGLE_CLIENT_ID")
    client_secret = _exigir("GOOGLE_CLIENT_SECRET")

    config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print("Abrindo o consentimento no navegador…")
    print("Entre com a conta INSTITUCIONAL da CPA, não com a sua pessoal.\n")

    flow = InstalledAppFlow.from_client_config(config, ESCOPOS)
    credenciais = flow.run_local_server(
        port=args.porta,
        # offline + consent é o que garante o refresh token; sem os dois, o
        # Google devolve só o access token, que dura 1 hora.
        access_type="offline",
        prompt="consent",
        open_browser=True,
    )

    if not credenciais.refresh_token:
        sys.exit(
            "O Google não devolveu refresh token.\n"
            "Causa comum: a conta já autorizou este app antes. Revogue em\n"
            "https://myaccount.google.com/permissions e rode de novo."
        )

    # ── pasta do Drive ──────────────────────────────────────────────────────
    drive = build("drive", "v3", credentials=credenciais, cache_discovery=False)
    achadas = (
        drive.files()
        .list(
            q=(
                "mimeType='application/vnd.google-apps.folder' "
                f"and name='{args.pasta}' and trashed=false"
            ),
            fields="files(id,name)",
            pageSize=1,
        )
        .execute()
        .get("files", [])
    )
    if achadas:
        pasta = achadas[0]
        print(f"\nPasta encontrada: {pasta['name']}")
    else:
        pasta = (
            drive.files()
            .create(
                body={
                    "name": args.pasta,
                    "mimeType": "application/vnd.google-apps.folder",
                },
                fields="id,name",
            )
            .execute()
        )
        print(f"\nPasta criada: {pasta['name']}")

    print("\n" + "=" * 70)
    print("Copie para o seu .env (NÃO versione este arquivo):\n")
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={credenciais.refresh_token}")
    print(f"GOOGLE_DRIVE_FOLDER_ID={pasta['id']}")
    print("=" * 70)
    print(
        "\nEscopos concedidos:\n  " + "\n  ".join(credenciais.scopes or ESCOPOS)
    )


if __name__ == "__main__":
    main()
