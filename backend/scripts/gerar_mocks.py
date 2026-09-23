"""Gera as fixtures do painel mockado a partir dos anexos da especificação.

Fase 1: o painel precisa ser avaliado pela CPA antes do backend existir, e para
isso tem de mostrar os DADOS REAIS — 17 turmas, 106 ofertas, as 163 perguntas e
a conciliação com o typo "Washignton". Os payloads seguem o doc 06.

Números de resposta e ISG são sintéticos e estão marcados como demonstração.
"""

import json
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ANEXOS = RAIZ / ".agent/02-especificacao/anexos"
SAIDA = RAIZ / "frontend/src/api/mock/dados"

random.seed(20262)  # fixtures estáveis entre execuções

grade = json.loads((ANEXOS / "grade_20262_esperado.json").read_text("utf-8"))
banco = json.loads((ANEXOS / "B_banco_perguntas_cpa.json").read_text("utf-8"))

NOME_CURSO = {
    "BIOMEDICINA": "Biomedicina",
    "ENFERMAGEM": "Enfermagem",
    "EDUCACAO_FISICA": "Educação Física",
    "GTI": "GTI",
}
EIXOS = {
    1: "Planejamento e Avaliação Institucional",
    2: "Desenvolvimento Institucional",
    3: "Políticas Acadêmicas",
    4: "Políticas de Gestão",
    5: "Infraestrutura Física",
}


def escrever(nome: str, dado) -> None:
    caminho = SAIDA / f"{nome}.json"
    caminho.write_text(json.dumps(dado, ensure_ascii=False, indent=1), "utf-8")
    print(f"  {nome}.json  ({caminho.stat().st_size // 1024} KB)")


# ─── catálogos derivados da grade ────────────────────────────────────────────
professores = sorted({o["professor"] for o in grade["ofertas"]})
disciplinas = sorted({o["disciplina"] for o in grade["ofertas"]})
por_turma: dict[int, list[dict]] = {t["id"]: [] for t in grade["turmas"]}
for of in grade["ofertas"]:
    for tid in of["turmas"]:
        por_turma[tid].append(of)

escrever(
    "cursos",
    [
        {"id": i, "nome": NOME_CURSO[s], "slug": s, "ativo": True}
        for i, s in enumerate(NOME_CURSO, 1)
    ],
)
escrever(
    "professores",
    [
        {
            "id": i,
            "nome_exibicao": n,
            "nome_completo": None,
            "ativo": True,
            "ofertas": sum(1 for o in grade["ofertas"] if o["professor"] == n),
        }
        for i, n in enumerate(professores, 1)
    ],
)
escrever(
    "disciplinas",
    [
        {"id": i, "nome": n, "curso_id": None, "ativo": True}
        for i, n in enumerate(disciplinas, 1)
    ],
)

# ─── turmas e ofertas ────────────────────────────────────────────────────────
turmas = []
for t in grade["turmas"]:
    ofs = por_turma[t["id"]]
    turmas.append(
        {
            "id": t["id"],
            "rotulo": t["rotulo"],
            "curso": NOME_CURSO[t["curso"]],
            "curso_slug": t["curso"],
            "turno": t["turno"],
            "periodo_numero": t["periodo_numero"],
            "modulo": ", ".join(t["modulos"]) or None,
            "compartilhada_ciclo_basico": t["turma_compartilhada_ciclo_basico"],
            "rotulos_origem": t["rotulos_origem"],
            "colunas_origem": t["colunas_origem"],
            "total_ofertas": len(ofs),
            "total_perguntas": 48 + 10 * len(ofs),
        }
    )
escrever("turmas", turmas)

escrever(
    "ofertas",
    [
        {
            "id": o["id"],
            "disciplina": o["disciplina"],
            "professor": o["professor"],
            "rotulo": f'{o["disciplina"]} · Prof. {o["professor"]}',
            "turmas": o["turmas"],
            "qtd_turmas": o["qtd_turmas"],
            "modalidades": o["modalidades"],
            "avaliavel": o["qtd_turmas"] > 0,
            "flags": o["flags"],
            "celulas_origem": o["celulas_origem"],
        }
        for o in grade["ofertas"]
    ],
)

# ─── dimensões e eixos ───────────────────────────────────────────────────────
dims = {}
for q in banco["questoes"]:
    dims.setdefault(
        q["dim"], {"numero": q["dim"], "nome": q["nome_dim"], "eixo": q["eixo"]}
    )
escrever(
    "dimensoes",
    {
        "eixos": [{"numero": n, "nome": v} for n, v in EIXOS.items()],
        "dimensoes": [
            {**d, "eixo_nome": EIXOS[d["eixo"]], "nome_institucional": d["nome"]}
            for d in sorted(dims.values(), key=lambda x: x["numero"])
        ],
    },
)

# ─── perguntas e equivalências ───────────────────────────────────────────────
INSTRUMENTO = {
    "DISCENTE": "DISCENTE_TURMA",
    "DOCENTE": "DOCENTE",
    "TECNICO_ADMINISTRATIVO": "TECNICO_ADMINISTRATIVO",
    "COMUNIDADE": "COMUNIDADE",
}
escrever(
    "perguntas",
    [
        {
            "id": q["codigo"],
            "codigo": q["codigo"],
            "texto": q["questao"],
            "tipo_instrumento": INSTRUMENTO[q["segmento"]],
            "segmento": q["segmento"],
            "bloco": q["bloco"],
            "por_materia": q["por_materia"],
            "dimensao": q["dim"],
            "dimensao_nome": q["nome_dim"],
            "eixo": q["eixo"],
            "equivalencia_id": q["equivalencia_id"],
            "tipo": "LIKERT_5",
            "aplicacao": "TODAS",
            "obrigatoria": True,
            "versao_texto": 1,
            "ativo": q["codigo"] not in (29, 86),  # duplicata — Anexo B §B.6
        }
        for q in banco["questoes"]
    ],
)
escrever("equivalencias", banco["equivalencias"])
print(f"  (perguntas: {len(banco['questoes'])}, equivalências: {len(banco['equivalencias'])})")


# ─── importação / conciliação (doc 07 §3.4) ──────────────────────────────────
# As linhas vêm do LEITOR REAL, não do fixture agregado: a tela de conciliação
# precisa mostrar a célula bruta, que é o que permite ao admin decidir.
from app.services.importador.leitor_xlsx import ler  # noqa: E402

PLANILHA = ANEXOS / "horario_20262.xlsx"
colunas_grade, linhas_grade = ler(PLANILHA)

SUGESTAO_ALIAS = {"Washignton": ("Washington", 0.95), "Vitória": ("Victória", 0.93)}

linhas = []
for i, ln in enumerate(linhas_grade, 1):
    aula = ln.aula
    registro = {
        "id": i,
        "aba": ln.aba,
        "celula": ln.celula,
        "texto_origem": aula.texto_origem,
        "disciplina_proposta": aula.disciplina,
        "professor_proposto": aula.professor,
        "modalidades": [m.value for m in aula.modalidades],
        "dia_semana": ln.dia_semana,
        "horario": ln.horario,
        "duracao_horarios": ln.duracao_horarios,
        "turma": ln.coluna_turma.referencia,
        "status": aula.status.value,
        "motivos": aula.flags,
        "confianca": 1.0 if aula.status.value == "OK" else 0.82,
    }
    if aula.professor in SUGESTAO_ALIAS:
        nome, score = SUGESTAO_ALIAS[aula.professor]
        registro["status"] = "REVISAR"
        registro["motivos"] = [*aula.flags, "MATCH_FUZZY"]
        registro["confianca"] = score
        registro["sugestao"] = {"professor": nome, "similaridade": score}
    linhas.append(registro)

contagem = {"OK": 0, "REVISAR": 0, "ERRO": 0}
for ln in linhas:
    contagem[ln["status"]] += 1

escrever(
    "importacao",
    {
        "id": 12,
        "nome_arquivo": "horario 20262.xlsx",
        "periodo_letivo": "2026.2",
        "status": "AGUARDANDO_REVISAO",
        "criado_em": "2026-09-23T09:14:00-03:00",
        "resumo": {
            **contagem,
            "alocacoes": len(linhas),
            "turmas": len(grade["turmas"]),
            "ofertas": len(grade["ofertas"]),
            "professores": len(professores),
            "disciplinas": len(disciplinas),
        },
        "avisos": grade.get("avisos", []),
        "linhas": linhas,
    },
)
print(f"  (conciliação: {contagem}, {len(linhas)} alocações)")
