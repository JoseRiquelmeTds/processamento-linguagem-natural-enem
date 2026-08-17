import re, unicodedata
import pandas as pd
from pathlib import Path

project_path = Path(__file__).resolve().parent.parent
input_path = project_path / "questions_data_set.csv"
output_path = project_path / "data" / "questions_data_set_preprocessed.csv"

area_mapping = {
    "LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS": "linguagens",
    "CIÊNCIAS HUMANAS E SUAS TECNOLOGIAS": "humanas",
    "CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS": "natureza",
    "MATEMÁTICA E SUAS TECNOLOGIAS": "matematica",
}

url_pattern = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"']+")
whitespace_pattern = re.compile(r"\s+")


def replace_url(match):
    url = match.group(0)
    punctuation = ""

    while url and url[-1] in ".,;:!?)]}":
        punctuation = url[-1] + punctuation
        url = url[:-1]

    return "URL" + punctuation


def clean_text(text):
    text = unicodedata.normalize("NFC", str(text))
    text = url_pattern.sub(replace_url, text)
    text = whitespace_pattern.sub(" ", text)
    return text.strip()


def normalize_area(area):
    area = unicodedata.normalize("NFC", str(area))
    return whitespace_pattern.sub(" ", area).strip()


def preprocess_data(path):
    df = pd.read_csv(
        path,
        sep=";",
        encoding="utf-8-sig",
        dtype="string",
        keep_default_na=False,
    )

    df["questao_original"] = df["Questao"].copy()
    df["questao_limpa"] = df["Questao"].map(clean_text).astype("string")
    normalized_areas = df["Área"].map(normalize_area).astype("string")
    df["area_classe"] = normalized_areas.map(area_mapping).fillna(normalized_areas)

    return df
