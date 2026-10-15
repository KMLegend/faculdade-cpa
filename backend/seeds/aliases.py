"""Aliases conhecidos, extraídos do Anexo A.

São as grafias que a conciliação de 2025.2 já resolveria — semeá-las faz a
primeira importação do novo ciclo passar direto nesses casos.
"""

#: slug de origem → nome canônico
ALIAS_PROFESSOR: dict[str, str] = {
    "washignton": "Washington",   # typo recorrente na planilha
    "vitoria": "Victória",        # mesma pessoa, grafia alternativa
}

ALIAS_DISCIPLINA: dict[str, str] = {
    "cinnesiologia e biomecanica": "Cinesiologia e Biomecânica",
    "promocao a saude": "Promoção da Saúde",
    "gestao de projetos em tecnologia de informacao": (
        "Gestão de Projetos em Tecnologia da Informação"
    ),
}
