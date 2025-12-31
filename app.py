import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import streamlit as st
from openpyxl import load_workbook

XLSX_PATH = Path("quiz.xlsx")
QUESTIONS_PER_RUN = 10


@dataclass
class QuizItem:
    id: str
    ja: str
    cloze_en: str   # ____ を含む
    answer: str
    full_ja: str


def normalize(s: str) -> str:
    return str(s).strip().lower()


def build_full_en(cloze_en: str, answer: str) -> str:
    c = str(cloze_en).replace("＿", "_")
    return c.replace("____", answer)


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
        raise ValueError(f"Excelに必要な列がありません: {missing} / 現在: {headers}")

    def get(row, col):
        i = idx[col]
        v = row[i] if i < len(row) else None
        return "" if v is None else str(v).strip()

    items: List[QuizItem] = []
    bad = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row is None:
            continue
        _id = get(row, "id")
        ja = get(row, "ja")
        cloze_en = get(row, "cloze_en").replace("＿", "_")
        answer = get(row, "answer")
        full_ja = get(row, "full_ja")

        if not cloze_en or "____" not in cloze_en:
            bad.append((_id, "cloze_en に ____ がない"))
            continue
        if not answer:
            bad.append((_id, "answer が空"))
            continue
        if not full_ja:
            bad.append((_id, "full_ja が空"))
            continue

        items.append(QuizItem(_id, ja, cloze_en, answer, full_ja))

    st.session_state["bad_rows"] = bad
    return items


def init_quiz():
    items = load_items_from_xlsx(XLSX_PATH)
    if len(items) < QUESTIONS_PER_RUN:
        raise ValueError(f"有効な問題が {len(items)} 件です。{QUESTIONS_PER_RUN} 件以上必要です。")

    quiz = random.sample(items, QUESTIONS_PER_RUN)
    st.session_state.quiz = [asdict(q) for q in quiz]
    st.session_state.i = 0
    st.session_state.correct = 0
    st.session_state.wrong = 0
    st.session_state.skipped = 0
    st.session_state.phase = "question"  # start | question | feedback | done
    st.session_state.last = None
    st.session_state.user_input = ""


# ===== UI =====
st.set_page_config(page_title="英単語クイズ", page_icon="📝", layout="centered")
st.title("📝 英単語クイズ")

# 初期化
if "phase" not in st.session_state:
    st.session_state.phase = "start"

with st.sidebar:
    st.header("操作")
    if st.button("最初から（リセット）"):
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.caption("Excel列：id / ja / cloze_en / answer / full_ja")

    bad = st.session_state.get("bad_rows", [])
    if bad:
        with st.expander("読み込み時にスキップした行"):
            for _id, reason in bad[:200]:
                st.write(f"- ID={_id}: {reason}")


# start
if st.session_state.phase == "start":
    st.write("Excel（quiz.xlsx）から10問ランダムに出題します。")
    if st.button("▶️ スタート（10問）", type="primary"):
        init_quiz()
        st.rerun()

# question
elif st.session_state.phase == "question":
    quiz = st.session_state.quiz
    i = st.session_state.i
    q = quiz[i]

    st.subheader(f"Q{i+1}/{len(quiz)}")
    if q.get("ja"):
        st.write(f"**日本語**：{q['ja']}")
    st.write(f"**英文**：{q['cloze_en']}")

    st.session_state.user_input = st.text_input(
        "空欄に入る語句を入力（大小は無視します）",
        value=st.session_state.get("user_input", ""),
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("送信", type="primary"):
            user = st.session_state.user_input.strip()
            if user == "":
                st.session_state.skipped += 1
                is_skip = True
                is_correct = False
            else:
                is_skip = False
                is_correct = normalize(user) == normalize(q["answer"])
                if is_correct:
                    st.session_state.correct += 1
                else:
                    st.session_state.wrong += 1

            st.session_state.last = {
                "is_skip": is_skip,
                "is_correct": is_correct,
                "user": user,
                "answer": q["answer"],
                "full_en": build_full_en(q["cloze_en"], q["answer"]),
                "full_ja": q["full_ja"],
            }
            st.session_state.phase = "feedback"
            st.rerun()

    with c2:
        if st.button("スキップ"):
            st.session_state.skipped += 1
            st.session_state.last = {
                "is_skip": True,
                "is_correct": False,
                "user": "",
                "answer": q["answer"],
                "full_en": build_full_en(q["cloze_en"], q["answer"]),
                "full_ja": q["full_ja"],
            }
            st.session_state.phase = "feedback"
            st.rerun()

# feedback
elif st.session_state.phase == "feedback":
    i = st.session_state.i
    total = len(st.session_state.quiz)
    last = st.session_state.last

    st.subheader(f"Q{i+1}/{total} 結果")

    if last["is_skip"]:
        st.info("スキップ")
    elif last["is_correct"]:
        st.success("正解")
    else:
        st.error("不正解")
        st.write(f"あなた：`{last['user']}`")
        st.write(f"正解：`{last['answer']}`")

    st.divider()
    st.write("**EN（全文）**")
    st.write(last["full_en"])
    st.write("**JA（訳）**")
    st.write(last["full_ja"])

    if st.button("次へ ▶️", type="primary"):
        st.session_state.i += 1
        st.session_state.user_input = ""
        st.session_state.last = None
        if st.session_state.i >= total:
            st.session_state.phase = "done"
        else:
            st.session_state.phase = "question"
        st.rerun()

# done
elif st.session_state.phase == "done":
    total = len(st.session_state.quiz)
    st.subheader("結果")
    st.write(f"- 正解：{st.session_state.correct}")
    st.write(f"- 不正解：{st.session_state.wrong}")
    st.write(f"- スキップ：{st.session_state.skipped}")
    st.write(f"- 合計：{total}")

    if st.button("もう一回（別の10問）", type="primary"):
        init_quiz()
        st.rerun()
