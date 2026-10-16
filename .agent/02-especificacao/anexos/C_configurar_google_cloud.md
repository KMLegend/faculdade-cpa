# Anexo C — Configurar o Google Cloud e gerar as credenciais

Roteiro para produzir as quatro variáveis que a Fase 5 precisa:

```
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
GOOGLE_DRIVE_FOLDER_ID=
```

Faz-se **uma vez**. Quem executa precisa de acesso à conta Google **institucional**
da CPA — não à conta pessoal de quem desenvolve: os formulários ficam sob a conta
que autorizar, e ela precisa sobreviver à troca de pessoas na comissão.

---

## ⚠️ Antes de começar: o tipo de usuário decide tudo

O sistema usa o escopo `forms.body`, que o Google classifica como **sensível**.
Isso cria dois caminhos muito diferentes:

| Situação | Tipo | Consequência |
|---|---|---|
| A FPM tem **Google Workspace** e o projeto fica sob esse domínio | **Interno** | ✅ Sem verificação, sem expiração. **Use este.** |
| Conta comum (`@gmail.com`), sem Workspace | **Externo** | ⚠️ Em *Testing*, o refresh token **expira em 7 dias**. Para publicar, o Google exige **verificação** do app (semanas, exige política de privacidade, domínio e vídeo de demonstração). |

> **Se houver Workspace, use Interno.** É a diferença entre configurar em 15 minutos
> e abrir um processo de verificação com o Google. O escopo sensível só dispara
> verificação para apps **externos**; uso interno à organização é exceção prevista.

Se não houver Workspace e a verificação não for viável, o caminho realista é
**conta de serviço com delegação** (doc 10 §4.1) — mas ela também exige um
administrador de Workspace. Sem Workspace algum, resta operar em *Testing*
regenerando o token a cada 7 dias, o que **não serve** para um ciclo de avaliação.

---

## 1. Criar o projeto

1. Entre em [console.cloud.google.com](https://console.cloud.google.com) **com a conta
   institucional da CPA**.
2. No seletor de projetos (topo), **Novo projeto**.
3. Nome: `CPA FPM`. Se aparecer o campo **Organização**, escolha o domínio da FPM —
   é isso que habilita o tipo *Interno* adiante.
4. **Criar** e aguarde o projeto ficar selecionado.

## 2. Ativar as APIs

Em **APIs e serviços → Biblioteca**, procure e ative, uma a uma:

- **Google Forms API**
- **Google Drive API**

Sem as duas ativadas, a sincronização falha com `403 SERVICE_DISABLED`.

## 3. Configurar a tela de consentimento

Em **APIs e serviços → Tela de permissão OAuth** (nos consoles mais novos:
**Google Auth Platform → Branding**):

1. **Tipo de usuário:** **Interno** se a opção aparecer. Se só houver **Externo**,
   releia o quadro no topo antes de seguir.
2. Nome do app: `CPA — Avaliação Institucional`
3. E-mail de suporte e e-mail do desenvolvedor: o da CPA.
4. **Escopos:** pode deixar vazio aqui. O app pede os escopos em tempo de execução,
   e é isso que o script faz.
5. Se o tipo for **Externo**, adicione a conta da CPA em **Usuários de teste** —
   sem isso o consentimento é recusado.

## 4. Criar o cliente OAuth

Em **APIs e serviços → Credenciais → Criar credenciais → ID do cliente OAuth**:

1. **Tipo de aplicativo: Aplicativo para computador** (*Desktop app*).
   Escolha este mesmo sendo um sistema web: o redirecionamento por *loopback*
   (`http://localhost`) é liberado automaticamente, e você não precisa cadastrar
   URI de redirecionamento nenhuma. O cliente serve só para gerar o token.
2. Nome: `CPA — geração de token`.
3. **Criar.** A tela mostra o **ID do cliente** e a **Chave secreta do cliente**.

Guarde os dois — são o `GOOGLE_CLIENT_ID` e o `GOOGLE_CLIENT_SECRET`.

## 5. Gerar o refresh token

Na raiz do `backend/`, com as duas variáveis no ambiente:

```bash
export GOOGLE_CLIENT_ID="...apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="GOCSPX-..."
python -m scripts.autorizar_google
```

O navegador abre o consentimento. **Entre com a conta institucional.** Se aparecer
"Google não verificou este app" (acontece no tipo Externo), clique em *Avançado* →
*Acessar CPA (não seguro)* — é o próprio app da instituição.

Ao final o script imprime as quatro variáveis prontas, já tendo criado a pasta no
Drive:

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=1//0g...
GOOGLE_DRIVE_FOLDER_ID=1a2B3c...
```

Para nomear a pasta de outro jeito:

```bash
python -m scripts.autorizar_google --pasta "CPA 2026.2"
```

## 6. Guardar as variáveis

Cole no `.env` da raiz do projeto — que **não** é versionado. Em produção, cadastre
as mesmas quatro no painel do Render, em *Environment*.

```bash
docker compose up -d --build backend
curl -s localhost:8000/api/admin/integracao/status -u cpa:SENHA
```

---

## Se der errado

| Sintoma | Causa provável |
|---|---|
| Script diz "não devolveu refresh token" | A conta já autorizou antes. Revogue em [myaccount.google.com/permissions](https://myaccount.google.com/permissions) e rode de novo. |
| `403 SERVICE_DISABLED` | Faltou ativar Forms API ou Drive API (passo 2). |
| `403 access_denied` no consentimento | Tipo Externo sem a conta em *Usuários de teste* (passo 3.5). |
| `invalid_grant` depois de uns dias | App Externo em *Testing*: o token expirou em 7 dias. Releia o quadro do topo. |
| `redirect_uri_mismatch` | O cliente foi criado como *Aplicativo da Web*. Crie outro como *Aplicativo para computador*. |

## O que fazer se o token for revogado no meio do ciclo

A sincronização e a importação de respostas param com `CREDENCIAL_INVALIDA`, e o
painel alerta. Os formulários no Google **continuam no ar recebendo respostas** —
nada se perde. Basta rodar o script de novo e atualizar o `GOOGLE_REFRESH_TOKEN`.

## Segurança

- O refresh token é credencial de longa duração: trate como senha. **Nunca** vai
  para o repositório, nem para o Power BI, nem para planilha compartilhada.
- `drive.file` dá acesso **apenas aos arquivos que o app criar** — o resto do Drive
  da conta permanece inacessível. É por isso que esse escopo foi escolhido em vez
  do `drive` completo.
- Ao encerrar o ciclo letivo, considere revogar e regerar: limita a janela de uso
  indevido de um token vazado.
