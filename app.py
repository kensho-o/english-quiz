import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

import streamlit as st
from openpyxl import load_workbook

XLSX_PATH = Path("quiz.xlsx")
QUESTIONS_PER_RUN = 10


# =====================
# データ定義
# =====================
@dataclass
class QuizItem:
    id: str
    id_num: int
    ja: str
    cloze_en: str
    answer: str
    full_ja: str


def normalize(s: str) -> str:
    return str(s).strip().lower()


def build_full_en(cloze_en: str, answer: str) -> str:
    return cloze_en.replace("＿", "_").replace("____", answer)


# =====================
# Excel 読み込み
# =====================
def load_items_from_xlsx(path: Path) -> List[QuizItem]:
    if not path.exists():
        raise FileNotFoundError("quiz.xlsx が見つかりません（app.pyと同じ階層に置いてください）")

    wb = load_workbook(path, data_only=True)
    ws = wb.worksheets[0]

    header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    headers = [str(v).strip() for v in header]
    idx = {name: i for i, name in enumerate(headers)}

    required = ["id", "ja", "cloze_en", "answer", "full_ja"]
    missing = [c for c in required if c not in idx]
    if missing:
        raise ValueError(f"Excelに必要な列がありません: {missing}")

    def get(row, col):
        i = idx[col]
        v = row[i] if i < len(row) else None
        return "" if v is None else str(v).strip()

    items: List[QuizItem] = []
    bad = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        _id = get(row, "id")
        ja = get(row, "ja")
        cloze_en = get(row, "cloze_en").replace("＿", "_")
        answer = get(row, "answer")
        full_ja = get(row, "full_ja")

        # id を数値化
        try:
            id_num = int(_id)
        except:
            bad.append((_id, "id が数字ではありません"))
            continue

        if "____" not in cloze_en:
            bad.append((_id, "cloze_en に ____ がありません"))
            continue
        if not answer or not full_ja:
            bad.append((_id, "answer または full_ja が空です"))
            continue

        items.append(
            QuizItem(
                id=_id,
                id_num=id_num,
                ja=ja,
                cloze_en=cloze_en,
                answer=answer,
                full_ja=full_ja,
            )
        )

    st.session_state["bad_rows"] = bad
    return items


# =====================
# クイズ初期化（ID範囲指定）
# =====================
def init_quiz(min_id: int, max_id: int):
    items = load_items_from_xlsx(XLSX_PATH)

    pool = [it for it in items if min_id <= it.id_num <= max_id]

    if len(pool) < QUESTIONS_PER_RUN:
        raise ValueError(
            f"指定範囲（ID {min_id}〜{max_id}）の有効問題が {len(pool)} 件です。"
            f"{QUESTIONS_PER_RUN} 件以上必要です。"
        )

    quiz = random.sample(pool, QUESTIONS_PER_RUN)

    st.session_state.quiz = [asdict(q) for q in quiz]
    st.session_state.i = 0
    st.session_state.correct = 0
    st.session_state.wrong = 0
    st.session_state.skipped = 0
    st.session_state.phase = "question"
    st.session_state.last = None
    st.session_state.user_input = ""


# =====================
# UI
# =====================
st.set_page_config(page_title="英単語クイズ", page_icon="📝")
st.title("📝 英単語クイズ")

if "phase" not in st.session_state:
    st.session_state.phase = "start"

# --
