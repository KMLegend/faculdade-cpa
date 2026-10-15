"""RN-31 — o schema não pode guardar o que identificaria o respondente.

Inspeção estática do modelo: não toca o banco nem precisa de event loop. É o
teste que impede alguém de acrescentar `ip` ou `user_agent` numa refatoração
futura "só para depurar".
"""

from sqlalchemy import Date

from app.models import Submissao

#: Campos que, se existirem, quebram o anonimato estrutural.
PROIBIDOS = {
    "ip",
    "endereco_ip",
    "email",
    "matricula",
    "user_agent",
    "dispositivo_hash",
    "nome",
    "aluno_id",
    "discente_id",
}


def test_submissao_sem_campo_identificavel():
    colunas = set(Submissao.__table__.c.keys())
    assert not (colunas & PROIBIDOS), f"campos proibidos: {colunas & PROIBIDOS}"


def test_data_envio_e_date_nao_timestamp():
    """Hora permitiria cruzar a resposta com a lista de presença."""
    assert isinstance(Submissao.__table__.c.data_envio.type, Date)


def test_google_response_id_e_unico():
    """Idempotência da ingestão (doc 10 §9) — sem isto, reimportar duplica."""
    assert Submissao.__table__.c.google_response_id.unique
