"""Regera data/questions_data_set_clean.csv a partir do CSV bruto do scrapper.

As colunas ID, Arquivo, Numero, Questao, Área, questao_original, questao_limpa,
area_classe e ano são derivadas diretamente do CSV bruto.

A coluna `texto` é o enunciado sem o que não pertence à questão (cabeçalhos do
caderno, chamadas de seção, bloco da redação e marca d'água do PDF). O gerador
original dessa limpeza não está versionado neste repositório, então esta etapa
não a refaz: ela parte do `texto` da base atual e propaga para dentro dele as
correções que surgiram no CSV bruto.

Isso mantém intactas as decisões de limpeza já embutidas na base — que o
exercise_list/lista_2.ipynb também consome — e altera apenas as palavras que o
scrapper passou a extrair corretamente.

A propagação é derivada, questão a questão, do diff entre o `questao_limpa`
antigo e o novo; nenhuma regra de substituição é escrita à mão aqui.
"""

import csv
import difflib
import importlib.util
from pathlib import Path

import pandas as pd

PROJECT_PATH = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_PATH / "questions_data_set.csv"
CLEAN_PATH = PROJECT_PATH / "data" / "questions_data_set_clean.csv"

# Anos que compõem a base de análise.
ANOS = ("2020", "2023", "2024", "2025")

COLUNAS = [
    "ID", "Arquivo", "Numero", "Questao", "Área",
    "questao_original", "questao_limpa", "area_classe", "ano", "texto",
]


def _carregar_preprocessamento():
    """Reaproveita clean_text/area_mapping de preprocess_questions.py.

    O módulo é carregado por caminho porque o diretório não é um pacote.
    """
    spec = importlib.util.spec_from_file_location(
        "preprocess_questions", Path(__file__).with_name("preprocess_questions.py")
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def ler_csv(path):
    return pd.read_csv(
        path, sep=";", encoding="utf-8-sig", dtype="string", keep_default_na=False
    )


def correcoes_da_questao(texto_antigo, texto_novo):
    """Palavras que mudaram entre as duas versões do enunciado.

    Devolve pares (antiga, nova) na ordem em que aparecem. Só considera trechos
    em que o número de palavras se manteve, que é o caso das correções de glifo
    duplicado ("AA" -> "A", "HCll" -> "HCl").
    """
    antigas, novas = texto_antigo.split(), texto_novo.split()
    pares = []
    matcher = difflib.SequenceMatcher(None, antigas, novas, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "replace" or (i2 - i1) != (j2 - j1):
            continue
        for antiga, nova in zip(antigas[i1:i2], novas[j1:j2]):
            if antiga != nova:
                pares.append((antiga, nova))

    return pares


def propagar(texto, correcoes):
    """Aplica as correções ao `texto`, palavra a palavra."""
    if not correcoes:
        return texto

    substituicoes = dict(correcoes)
    return " ".join(substituicoes.get(p, p) for p in texto.split())


def construir():
    pq = _carregar_preprocessamento()

    bruto = ler_csv(RAW_PATH)
    base_atual = ler_csv(CLEAN_PATH)

    bruto["questao_original"] = bruto["Questao"]
    bruto["questao_limpa"] = bruto["Questao"].map(pq.clean_text).astype("string")
    areas = bruto["Área"].map(pq.normalize_area).astype("string")
    bruto["area_classe"] = areas.map(pq.area_mapping).fillna(areas)
    bruto["ano"] = bruto["Arquivo"].str.extract(r"(\d{4})")

    df = bruto[bruto["ano"].isin(ANOS)].copy()

    # `texto` vem da base atual, com as correções do CSV bruto propagadas.
    anterior = base_atual.set_index("ID")
    textos = []
    for linha in df.itertuples(index=False):
        if linha.ID not in anterior.index:
            raise KeyError(f"questão ausente na base atual: {linha.ID}")
        registro = anterior.loc[linha.ID]
        correcoes = correcoes_da_questao(registro["questao_limpa"], linha.questao_limpa)
        textos.append(propagar(registro["texto"], correcoes))

    df["texto"] = textos

    return df[COLUNAS].reset_index(drop=True)


if __name__ == "__main__":
    df = construir()

    print(f"Questões: {len(df)}")
    print("\nPor ano:")
    print(df["ano"].value_counts().sort_index().to_string())
    print("\nPor área:")
    print(df["area_classe"].value_counts().to_string())

    df.to_csv(
        CLEAN_PATH,
        index=False,
        sep=";",
        quoting=csv.QUOTE_ALL,
        encoding="utf-8-sig",
    )
    print(f"\nGravado em {CLEAN_PATH}")
