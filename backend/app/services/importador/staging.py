"""Área de espera da importação (doc 03 §1, passo 5 — RN-13).

Lê a planilha, casa com o cadastro e grava TUDO em `importacao_*`. Nada toca o
domínio aqui: é a conciliação que libera o commit.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NaoEncontrado
from app.models import (
    ImportacaoGrade, ImportacaoLinha, Modalidade, PeriodoLetivo, StatusImportacao,
    StatusLinha,
)
from app.services.importador.celula import StatusLinha as StatusCelula
from app.services.importador.leitor_xlsx import ColunaTurma, LinhaGrade, ler
from app.services.importador.matching import Catalogo, agrupar_por_similaridade

DIAS = {
    "segunda": 1, "terca": 2, "terça": 2, "quarta": 3,
    "quinta": 4, "sexta": 5, "sabado": 6, "sábado": 6,
}


def _dia_para_numero(texto: str | None) -> int | None:
    if not texto:
        return None
    alvo = texto.lower()
    for nome, numero in DIAS.items():
        if alvo.startswith(nome):
            return numero
    return None


def _turma_proposta(ct: ColunaTurma) -> dict:
    return {
        "cursos": ct.cursos,
        "turno": ct.turno,
        "periodo_numero": ct.periodo_numero,
        "modulo": ct.modulo,
        "rotulo": ct.rotulo,
        "aba": ct.aba,
        "colunas": ct.colunas,
        "referencia": ct.referencia,
        "compartilhada_ciclo_basico": ct.compartilhada,
        "e_turma": ct.e_turma,
        "avisos": ct.avisos,
    }


async def criar_importacao(
    caminho: str | Path,
    nome_arquivo: str,
    periodo_letivo_id: int,
    s: AsyncSession,
) -> ImportacaoGrade:
    """Executa os passos 1–5 do pipeline e devolve a importação em revisão."""
    periodo = await s.get(PeriodoLetivo, periodo_letivo_id)
    if periodo is None:
        raise NaoEncontrado(f"Período letivo {periodo_letivo_id} não encontrado.")

    conteudo = Path(caminho).read_bytes()
    importacao = ImportacaoGrade(
        periodo_letivo_id=periodo_letivo_id,
        nome_arquivo=nome_arquivo,
        hash_arquivo=hashlib.sha256(conteudo).hexdigest(),
        status=StatusImportacao.PROCESSANDO,
    )
    s.add(importacao)
    await s.flush()

    colunas, linhas_grade = ler(caminho)
    catalogo = await Catalogo.carregar(s, periodo_letivo_id)

    contagem = {StatusLinha.OK: 0, StatusLinha.REVISAR: 0, StatusLinha.ERRO: 0}
    for ln in linhas_grade:
        linha = _montar_linha(ln, catalogo, importacao.id)
        contagem[linha.status] = contagem.get(linha.status, 0) + 1
        s.add(linha)

    # Grafias parecidas DENTRO do arquivo — o que o cadastro vazio não revela.
    grupos_professor = agrupar_por_similaridade(
        [ln.aula.professor for ln in linhas_grade if ln.aula.professor]
    )
    grupos_disciplina = agrupar_por_similaridade(
        [ln.aula.disciplina for ln in linhas_grade if ln.aula.disciplina]
    )

    importacao.status = StatusImportacao.AGUARDANDO_REVISAO
    importacao.resumo = {
        "alocacoes": len(linhas_grade),
        "OK": contagem[StatusLinha.OK],
        "REVISAR": contagem[StatusLinha.REVISAR],
        "ERRO": contagem[StatusLinha.ERRO],
        "colunas_lidas": len(colunas),
        "turmas_propostas": len(
            {
                (curso, ct.turno, ct.periodo_numero)
                for ct in colunas
                if ct.e_turma
                for curso in ct.cursos
            }
        ),
        "cadastro_vazio": catalogo.cadastro_vazio,
        "grupos_similares_professor": grupos_professor,
        "grupos_similares_disciplina": grupos_disciplina,
        "avisos_segmentacao": [
            {
                "tipo": aviso,
                "aba": ct.aba,
                "colunas": ct.colunas,
                "cursos": ct.cursos,
                "periodo_numero": ct.periodo_numero,
            }
            for ct in colunas
            for aviso in ct.avisos
        ],
    }
    await s.flush()
    return importacao


def _montar_linha(
    ln: LinhaGrade, catalogo: Catalogo, importacao_id: int
) -> ImportacaoLinha:
    aula = ln.aula
    motivos = list(aula.flags)
    status = StatusLinha(aula.status.value)

    disciplina_id = professor_id = None
    confianca = 0.0

    if aula.status is not StatusCelula.ERRO and aula.professor:
        r_prof = catalogo.casar_professor(
            aula.professor, cursos_da_coluna=ln.coluna_turma.cursos
        )
        r_disc = catalogo.casar_disciplina(aula.disciplina or "")

        for r, rotulo in ((r_prof, "PROFESSOR"), (r_disc, "DISCIPLINA")):
            if r.etapa.value == "NOVO":
                motivos.append(f"{rotulo}_NOVO")
            motivos.extend(m for m in r.motivos if m not in motivos)

        professor_id = r_prof.entidade_id if not r_prof.precisa_revisao else None
        disciplina_id = r_disc.entidade_id if not r_disc.precisa_revisao else None
        confianca = min(r_prof.confianca, r_disc.confianca)

        if (r_prof.precisa_revisao or r_disc.precisa_revisao) and status is StatusLinha.OK:
            status = StatusLinha.REVISAR

    return ImportacaoLinha(
        importacao_id=importacao_id,
        aba=ln.aba,
        celula=ln.celula,
        texto_origem=aula.texto_origem,
        dia_semana=ln.dia_semana,
        horario=ln.horario,
        duracao_horarios=ln.duracao_horarios,
        turma_proposta=_turma_proposta(ln.coluna_turma),
        disciplina_proposta=aula.disciplina,
        professor_proposto=aula.professor,
        modalidade_proposta=(
            Modalidade(aula.modalidades[0].value)
            if aula.modalidades
            else Modalidade.NAO_INFORMADA
        ),
        disciplina_id_sugerida=disciplina_id,
        professor_id_sugerido=professor_id,
        confianca=round(confianca, 3),
        status=status,
        motivos=motivos,
    )


async def criar_entidades_novas_em_lote(
    importacao_id: int, s: AsyncSession
) -> dict:
    """Promove a OK as linhas cujo único pendente é `*_NOVO` (doc 03 §4.1).

    Na primeira carga nada casa e revisar 164 linhas uma a uma é inviável. Linhas
    com ambiguidade real — `DISCIPLINA_AMBIGUA_OU`, `SEM_PREFIXO_PROF`,
    `MATCH_FUZZY`, `HOMONIMO_ENTRE_CURSOS` — nunca entram nesta ação.
    """
    BLOQUEANTES = {
        "DISCIPLINA_AMBIGUA_OU",
        "SEM_PREFIXO_PROF",
        "MATCH_FUZZY",
        "HOMONIMO_ENTRE_CURSOS",
        "ROTULO_TURMA_DUPLICADO",
        "OBSERVACAO_ADMINISTRATIVA",
        "PROFESSOR_NAO_IDENTIFICADO",
        "DISCIPLINA_VAZIA",
    }
    linhas = (
        await s.scalars(
            select(ImportacaoLinha).where(
                ImportacaoLinha.importacao_id == importacao_id,
                ImportacaoLinha.status == StatusLinha.REVISAR,
            )
        )
    ).all()

    promovidas = 0
    for linha in linhas:
        motivos = set(linha.motivos or [])
        if motivos & BLOQUEANTES:
            continue
        # As demais flags (PREFIXO_DUPLICADO, HIFEN_NO_NOME,
        # MODALIDADE_SEM_PARENTESES, PARENTESE_NAO_FECHADO) são informativas e
        # já nascem OK no parser (doc 03 §3.4) — não impedem a criação em lote.
        linha.status = StatusLinha.OK
        linha.decisao_admin = {"acao": "CRIAR_NOVAS_EM_LOTE"}
        promovidas += 1

    await s.flush()
    return {"promovidas": promovidas, "restantes_em_revisao": len(linhas) - promovidas}
