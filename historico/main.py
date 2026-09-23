import pandas as pd
import requests
import io


class ExtratorCPA:
    def __init__(self):
        # Estrutura: "ID_DA_PLANILHA": ("GID", "TÍTULO_DESEJADO")
        self.config_planilhas = {
            "1BEQEHN58mfUXWzb1XdobuqGPx8-qLUG58yaNEjTiEI8": (
                "633269544",
                "CPA - Docentes",
            ),
            "1-1WCJDvbn2AyuqZ-4utqmTqpr-QKZe3NWanOsMNfL3Q": (
                "617211311",
                "CPA - Discentes - Enfermagem - Matutino - 1 e 2 período",
            ),
            "1OiTGidP7eeEMyBlPkiU0Nin5IEdy5QwQQkurKwznuA8": (
                "2079594692",
                "CPA - Técnicos_Administrativos",
            ),
            "1btGx1smdLW5JEJGI_FWv7B1uKZA5TEeQ6HeEZQx63FU": (
                "101431619",
                "CPA - Discentes - Educação Física- Matutino - 1 e 2 período",
            ),
            "17J7rs_Z0qtbEDMr5YvsEFeNwrms8_c7BG6oscfcZLxk": (
                "45079527",
                "CPA - Discentes - Biomedicina - Matutino - 1 e 2 período",
            ),
            "13W2Pffntk09TSEzE0S2wkoDVbjemF9DB_o-wyquecvI": (
                "1440259853",
                "CPA - Discentes - Educação Física- Noturno - 6 período",
            ),
            "1y-15IYxXjvy13eGhtiAc9AXtZ-CMMjgBYx8RKcRaX-I": (
                "950105135",
                "CPA - Discentes -Biomedicina- Matutino - Módulo HI - 4-6 períodos",
            ),
            "1fysqs3v0nr_ufLEYVuTukd4u8myefqo0NqdZ7iTibqQ": (
                "1853362033",
                "CPA - Discentes - Educação Física- Noturno  - Módulo F - 1-2 períodos",
            ),
            "1L4dBdmc7RszrRbjKht2RQNli4vbAGgA5qiihiYjFi-I": (
                "408489900",
                "CPA - Discentes -Enfermagem- Noturno - 6 período",
            ),
            "1aEAv5tJClXIuq4KnaxoTto_QfJ7bJW-1tVd_-6zE2cg": (
                "2062890358",
                "CPA - Discentes -  Enfermagem - Noturno - Módulo F - 1-2 períodos",
            ),
            "1ZtrJDzk-TA8af1laf6oQVkR89RmxRYByeQaZbQ71kYU": (
                "1086989002",
                "CPA - Discentes -  Enfermagem - Noturno - 10 período",
            ),
            "1WT4WTya6cYpMyD8Vi5VCFYGFtXTvQIPbX0FrOboX9HA": (
                "479019807",
                "CPA - Discentes - GTI - Matutino - 1 e 2 período",
            ),
            "1zfCIunk4SK3nGlAxStKoK1ojKpnWhdk7iN0ozKRG0U0": (
                "807721609",
                "CPA - Discentes - Biomedicina- Noturno - Módulo F - 1-2 períodos",
            ),
            "17vDsr2YzL0jaWiua_Wg9qvwFglcnfOGSvIbQyKmGdkQ": (
                "1063366357",
                "CPA - Discentes -  Biomedicina - Noturno - 7 e 8 períodos",
            ),
            "17jq6u8-ESy2TD5ITtZoVS-fjt6cW0BuTNp2vp-_q3xA": (
                "1250986280",
                "CPA - Discentes - GTI - Noturno - 1 e 2 período",
            ),
            "1tiJBfQImYM3N3U2OjRbL88BVxqwqLMQX1g-J6hNiPJY": (
                "652890438",
                "CPA - Discentes - GTI - Noturno - 4 período",
            ),
            "1pKEh-qw16leoW7Pf908glOnhfzYLF7AEy3CMVpcuqD0": (
                "1069365992",
                "CPA - Discentes - Biomedicina- Noturno -  Módulo AB - 4-6 períodos",
            ),
        }

    def extrair_todos(self):
        lista_dfs = []

        for sheet_id, (gid, titulo) in self.config_planilhas.items():
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

            try:
                response = requests.get(url, timeout=15)

                if response.status_code == 200:
                    df = pd.read_csv(
                        io.StringIO(response.content.decode("utf-8"))
                    ).copy()

                    # Adiciona as colunas de identificação no início
                    df.insert(0, "titulo_formulario", titulo)
                    df.insert(1, "id_resumido", sheet_id[:8])

                    lista_dfs.append(df)
                    print(f"✓ {titulo} extraído com sucesso.")
                else:
                    print(f"✗ Erro {response.status_code} ao acessar: {titulo}")

            except Exception as e:
                print(f"! Falha em '{titulo}': {e}")

        if lista_dfs:
            return pd.concat(lista_dfs, ignore_index=True).copy()
        return pd.DataFrame()


# Execução
extrator = ExtratorCPA()
df_final = extrator.extrair_todos()

if not df_final.empty:
    print(f"\nProcesso concluído! Total de registros: {len(df_final)}")

    # Exportação para Excel (.xlsx)
    # O index=False evita que a coluna de números (índice do pandas) seja criada no Excel
    df_final.to_excel("consolidado_cpa.xlsx", index=False)
    print("Arquivo 'consolidado_cpa.xlsx' gerado com sucesso!")
