"""Regera `anexos/grade_20262_esperado.json` a partir do leitor real.

O fixture original foi produzido por um script exploratório durante a
especificação. O leitor de produção o supera em dois pontos:

  1. remove modalidade escrita fora de parênteses ("Toxicologia - Preleção"),
     que antes contaminava o nome da disciplina e duplicava a oferta (RN-10);
  2. trata mescla vertical como UMA alocação de N horários, em vez de repetir
     a aula em cada linha.

Este script é a ponte: o fixture passa a ser saída verificável do código.
"""

import json
from pathlib import Path

from app.core.texto import slugificar
from app.services.importador.leitor_xlsx import ler

RAIZ = Path(__file__).resolve().parents[2]
ANEXOS = RAIZ / ".agent/02-especificacao/anexos"
PLANILHA = ANEXOS / "horario_20262.xlsx"

# Aliases conhecidos, separados por entidade (doc 02).
ALIAS_PROFESSOR = {"washignton": "Washington", "vitoria": "Victória"}
ALIAS_DISCIPLINA = {
    "cinnesiologia e biomecanica": "Cinesiologia e Biomecânica",
    "promocao a saude": "Promoção da Saúde",
    "gestao de projetos em tecnologia de informacao": (
        "Gestão de Projetos em Tecnologia da Informação"
    ),
}
NOME_CURSO = {
    "BIOMEDICINA": "Biomedicina",
    "ENFERMAGEM": "Enfermagem",
    "EDUCACAO_FISICA": "Educação Física",
    "GTI": "GTI",
}


def canonico(texto: str, aliases: dict[str, str]) -> tuple[str, str]:
    """Devolve (slug canônico, nome de exibição)."""
    slug = slugificar(texto)
    if slug in aliases:
        nome = aliases[slug]
        return slugificar(nome), nome
    return slug, texto


def main() -> None:
    colunas, linhas = ler(PLANILHA)

    # ── turmas: (curso, turno, periodo) ──────────────────────────────────────
    turmas: dict[tuple, dict] = {}
    col_para_turmas: dict[int, list[int]] = {}
    for ct in colunas:
        if not ct.e_turma:
            col_para_turmas[id(ct)] = []
            continue
        ids = []
        for curso in ct.cursos:
            chave = (curso, ct.turno, ct.periodo_numero)
            reg = turmas.setdefault(
                chave,
                {
                    "id": len(turmas) + 1,
                    "curso": curso,
                    "turno": ct.turno,
                    "periodo_numero": ct.periodo_numero,
                    "rotulo": (
                        f"{NOME_CURSO.get(curso, curso)} · "
                        f"{ct.turno.title()} · {ct.periodo_numero}º período"
                    ),
                    "modulos": set(),
                    "rotulos_origem": set(),
                    "colunas_origem": set(),
                    "turma_compartilhada_ciclo_basico": ct.compartilhada,
                },
            )
            if ct.modulo:
                reg["modulos"].add(ct.modulo)
            reg["rotulos_origem"].add(ct.rotulo)
            reg["colunas_origem"].add(ct.referencia)
            ids.append(reg["id"])
        col_para_turmas[id(ct)] = ids

    # ── ofertas: (disciplina, professor) ─────────────────────────────────────
    ofertas: dict[tuple[str, str], dict] = {}
    alocacoes = 0
    for ln in linhas:
        if not ln.aula.professor:
            continue
        alocacoes += 1
        sd, nome_d = canonico(ln.aula.disciplina or "", ALIAS_DISCIPLINA)
        sp, nome_p = canonico(ln.aula.professor, ALIAS_PROFESSOR)
        reg = ofertas.setdefault(
            (sd, sp),
            {
                "disciplina": nome_d,
                "professor": nome_p,
                "chave": f"{sd} | {sp}",
                "turmas": set(),
                "modalidades": set(),
                "flags": set(),
                "celulas_origem": set(),
            },
        )
        if len(nome_d) > len(reg["disciplina"]):
            reg["disciplina"] = nome_d
        reg["turmas"].update(col_para_turmas[id(ln.coluna_turma)])
        reg["modalidades"].update(m.value for m in ln.aula.modalidades)
        reg["flags"].update(ln.aula.flags)
        reg["celulas_origem"].add(ln.aula.texto_origem)

    lista_turmas = []
    for t in sorted(turmas.values(), key=lambda x: x["id"]):
        lista_turmas.append(
            {
                **t,
                "modulos": sorted(t["modulos"]),
                "rotulos_origem": sorted(t["rotulos_origem"]),
                "colunas_origem": sorted(t["colunas_origem"]),
            }
        )
    lista_ofertas = []
    for i, ((sd, sp), o) in enumerate(sorted(ofertas.items()), 1):
        lista_ofertas.append(
            {
                "id": i,
                "disciplina": o["disciplina"],
                "professor": o["professor"],
                "chave": o["chave"],
                "turmas": sorted(o["turmas"]),
                "qtd_turmas": len(o["turmas"]),
                "modalidades": sorted(o["modalidades"]),
                "flags": sorted(o["flags"]),
                "celulas_origem": sorted(o["celulas_origem"]),
            }
        )

    avisos = [
        {
            "tipo": aviso,
            "aba": ct.aba,
            "colunas": ct.colunas,
            "cursos": ct.cursos,
            "periodo_numero": ct.periodo_numero,
        }
        for ct in colunas
        for aviso in ct.avisos
    ]

    status = {"OK": 0, "REVISAR": 0, "ERRO": 0}
    for ln in linhas:
        status[ln.aula.status.value] += 1

    avaliaveis = sum(1 for o in lista_ofertas if o["qtd_turmas"] > 0)
    saida = {
        "periodo_letivo": "2026.2",
        "arquivo_origem": "horario 20262.xlsx",
        "chave_da_turma": "(curso, turno, periodo_numero) — módulo e rótulo A/B NÃO entram",
        "chave_da_oferta": "(disciplina, professor) — global no período letivo",
        "gerado_por": "backend/scripts/gerar_fixture_grade.py (leitor de produção)",
        "turmas": lista_turmas,
        "ofertas": lista_ofertas,
        "avisos": avisos,
        "resumo": {
            "turmas": len(lista_turmas),
            "ofertas": len(lista_ofertas),
            "ofertas_avaliaveis": avaliaveis,
            "ofertas_sem_turma": len(lista_ofertas) - avaliaveis,
            "ofertas_multiturma": sum(1 for o in lista_ofertas if o["qtd_turmas"] > 1),
            "vinculos_oferta_turma": sum(o["qtd_turmas"] for o in lista_ofertas),
            "alocacoes": len(linhas),
            "linhas_por_status": status,
            "professores": len({o["professor"] for o in lista_ofertas}),
            "disciplinas": len({o["disciplina"] for o in lista_ofertas}),
            "formularios_discente_turma": len(lista_turmas),
            "formularios_total": len(lista_turmas) + 3,
        },
    }
    destino = ANEXOS / "grade_20262_esperado.json"
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=1), "utf-8")
    print(json.dumps(saida["resumo"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
