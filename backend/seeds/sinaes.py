"""Dados de referência do SINAES: 5 eixos e 10 dimensões (doc 04 §1).

Base legal: Lei 10.861/2004 art. 3º (as dimensões) e a organização em eixos do
instrumento de avaliação institucional do INEP/DAES.

O painel da CPA usa exatamente esta nomenclatura — confirmado em 2025.2 —, então
`nome_institucional` recebe o mesmo texto do nome legal. Se a CPA renomear algo,
é esse campo que muda, nunca o `nome`.
"""

EIXOS: list[tuple[int, str]] = [
    (1, "Planejamento e Avaliação Institucional"),
    (2, "Desenvolvimento Institucional"),
    (3, "Políticas Acadêmicas"),
    (4, "Políticas de Gestão"),
    (5, "Infraestrutura Física"),
]

#: (número, nome legal, eixo)
DIMENSOES: list[tuple[int, str, int]] = [
    (1, "Missão e Plano de Desenvolvimento Institucional", 2),
    (2, "Políticas para o Ensino, a Pesquisa e a Extensão", 3),
    (3, "Responsabilidade Social da Instituição", 2),
    (4, "Comunicação com a Sociedade", 3),
    (5, "Políticas de Pessoal", 4),
    (6, "Organização e Gestão da Instituição", 4),
    (7, "Infraestrutura Física", 5),
    (8, "Planejamento e Avaliação", 1),
    (9, "Política de Atendimento aos Discentes", 3),
    (10, "Sustentabilidade Financeira", 4),
]
