"""Leitura única de variáveis de ambiente (doc 00, convenção 6)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- banco ---
    database_url: str = Field(
        default="postgresql+asyncpg://cpa:cpa@localhost:5432/cpa",
        description="Supabase em produção; Postgres do compose em desenvolvimento.",
    )

    # --- painel administrativo ---
    admin_user: str = "cpa"
    admin_password: str = "trocar-esta-senha-agora"

    # --- aplicação ---
    frontend_url: str = "http://localhost:3000"
    timezone: str = "America/Sao_Paulo"
    versao: str = "0.1.0"

    # --- regras de exibição (doc 08 §4) ---
    min_respostas_exibicao: int = 5
    min_respostas_exibicao_restrito: int = 10
    limite_alerta_perguntas: int = 150
    isg_faixas: str = "0.25,0.46,0.72"

    # --- importação ---
    max_upload_mb: int = 5
    #: Onde ficam os anexos da especificação (planilha e banco de perguntas).
    #: No container o compose monta em /anexos; no host, resolve pelo repositório.
    anexos_dir: str = ""

    # --- Google Forms (doc 10 §4) — só necessários a partir da Fase 5 ---
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    google_drive_folder_id: str = ""

    @property
    def frontend_url_limpa(self) -> str:
        """FRONTEND_URL nunca tem barra final (doc 05 §3)."""
        return self.frontend_url.rstrip("/")

    @property
    def origens_cors(self) -> list[str]:
        return list({self.frontend_url_limpa, "http://localhost:3000"})

    @property
    def faixas_isg(self) -> list[float]:
        return [float(x) for x in self.isg_faixas.split(",")]

    @property
    def caminho_anexos(self) -> Path:
        """Resolve os anexos no container (/anexos) ou no repositório."""
        if self.anexos_dir:
            return Path(self.anexos_dir)
        if Path("/anexos").is_dir():
            return Path("/anexos")
        aqui = Path(__file__).resolve()
        for base in aqui.parents:
            candidato = base / ".agent/02-especificacao/anexos"
            if candidato.is_dir():
                return candidato
        raise FileNotFoundError(
            "Anexos da especificação não encontrados. Defina ANEXOS_DIR."
        )


@lru_cache
def obter_settings() -> Settings:
    return Settings()
