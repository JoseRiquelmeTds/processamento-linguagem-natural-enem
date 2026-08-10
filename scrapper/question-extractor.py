import csv, re
import pdfplumber
import pandas as pd
from pathlib import Path

folder_path = Path(r"C:\Users\JoséRiquelme\codigos\processamento-linguagem-natural-enem\PDFs")

pdf_archives = [str(file) for file in folder_path.glob("*.pdf")]




def is_two_column(cut_page, tolerancia=15):
    mid_x = cut_page.width / 2
    words = cut_page.extract_words()

    center_words = sum(
        1
        for w in words
        if w["x0"] < (mid_x - tolerancia) and w["x1"] > (mid_x + tolerancia)
    )
    return center_words < 4


def extract_page_text(page):
    width = page.width
    height = page.height

    top = height * 0.07
    bottom = height * 0.93
    mid_x = width / 2

    cropped_page = page.crop((0, top, width, bottom))

    if is_two_column(cropped_page):
        left_column = page.crop((0, top, mid_x, bottom))
        right_column = page.crop((mid_x, top, width, bottom))
        return (left_column.extract_text() or "") + "\n" + (
            right_column.extract_text() or ""
        )
    else:
        return cropped_page.extract_text() or ""


def text_cleaner(text):
    text = re.sub(r"(?:ENEM|ENEN)\d{4}", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\*\d+[A-Z0-9]+\*", "", text)
    text = re.sub(r".*?indb.*", "", text, flags=re.IGNORECASE)

    header_pattern = r"(CIÊNCIAS HUMANAS|CIÊNCIAS DA NATUREZA|LINGUAGENS|MATEMÁTICA).*?CADERNO.*?\d+.*"
    text = re.sub(header_pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r"\n\s*\n", "\n", text)
    
    return text.strip()


def classify_area(id_number):
    if id_number <= 45:
        return "LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS"
    elif id_number <= 90:
        return "CIÊNCIAS HUMANAS E SUAS TECNOLOGIAS"
    elif id_number <= 135:
        return "CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS"
    else:
        return "MATEMÁTICA E SUAS TECNOLOGIAS"


def extract_questions_from_pdf(path):
    complete_text = ""
    file_name = Path(path).stem  

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            content = extract_page_text(page)
            if content:
                complete_text += content + "\n"

    clean_text = text_cleaner(complete_text)

    pattern = r"(QUEST[ÃA]O\s+\d+)"
    parts = re.split(pattern, clean_text, flags=re.IGNORECASE)

    questions = []
    for i in range(1, len(parts), 2):
        title = parts[i].strip().upper()
        body = parts[i + 1].strip()

        match_num = re.search(r"\d+", title)
        if match_num:
            num_questao = int(match_num.group())
            area = classify_area(num_questao)

            unique_id = f"{file_name}_{num_questao}"

            questions.append(
                {
                    "ID_Unico": unique_id,
                    "Arquivo": file_name,
                    "Numero": num_questao,
                    "Questao": body,
                    "Área": area,
                }
            )

    return questions


def process_notebooks(path_list):
    all_questions = []

    for path in path_list:
        print(f"Lendo arquivo: {path}...")
        questions = extract_questions_from_pdf(path)
        all_questions.extend(questions)

    df = pd.DataFrame(all_questions)

    df = (
        df.drop_duplicates(subset=["ID"], keep="first")
        .sort_values(by=["Arquivo", "Numero"])
        .reset_index(drop=True)
    )

    return df


if __name__ == "__main__":
    df = process_notebooks(pdf_archives)

    print(f"\nTotal de questões catalogadas: {len(df)}")
    print("\nDistribuição por Área:")
    print(df["Área"].value_counts())

    # Exporta para CSV com aspas e ponto e vírgula
    df.to_csv(
        "questions_data_set.csv",
        index=False,
        sep=";",
        quoting=csv.QUOTE_ALL,
        encoding="utf-8-sig",
    )