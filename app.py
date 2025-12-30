import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from openpyxl import load_workbook


@dataclass
class QuizItem:
    id: str
    ja: str
    cloze_en: str
    answer: str
    full_ja: str


def normalize(s: str) -> str:
    """採点用：前後空白除去＋小文字化（大文字小文字を無視）"""
    return str(s).strip().lower()


def build_full_en(cloze_en: str, answer: str) -> str:
    """____ を answer で置き換えて全文英文を生成"""
    return cloze_en.replace("____", answer).replace("＿", "_").replace("_" * 4, answer)


def load_quiz_items_from_xlsx(xlsx_path: Path, sheet_name: Optional[str] = None) -> List[QuizItem]:
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Excelファイルが見つかりません: {xlsx_path}")

    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.worksheets[0]

    headers = [str(v).strip() for v in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    index = {name: i for i, name in enumerate(headers)}

    required = ["id", "ja", "cloze_en", "answer", "full_ja"]
    missing = [c for c in required if c not in index]
    if missing:
        raise ValueError(f"Excelに必要な列がありません: {missing}")

    def get(row, col):
        i = index[col]
        return "" if i >= len(row) or row[i] is None else str(row[i]).strip()

    items: List[QuizItem] = []
    bad_rows = []

    for r in ws.iter_rows(min_row=2, values_only=True):
        if r is None or all(v is None or str(v).strip() == "" for v in r):
            continue

        _id = get(r, "id")
        ja = get(r, "ja")
        cloze_en = get(r, "cloze_en").replace("＿", "_")
        answer = get(r, "answer")
        full_ja = get(r, "full_ja")

        if not cloze_en or "____" not in cloze_en:
            bad_rows.append((_id, "cloze_en に ____ がない"))
            continue
        if not answer:
            bad_rows.append((_id, "answer が空"))
            continue
        if not full_ja:
            bad_rows.append((_id, "full_ja が空"))
            continue

        items.append(QuizItem(_id, ja, cloze_en, answer, full_ja))

    if bad_rows:
        print("\n[読み込み時にスキップした行]")
        for _id, reason in bad_rows[:50]:
            print(f" - ID={_id}: {reason}")

    if not items:
        raise ValueError("有効な問題が1件もありません。")

    return items


def show_answer(q: QuizItem) -> None:
    full_en = build_full_en(q.cloze_en, q.answer)
    print("\n--- 解答（全文と訳）---")
    print(f"EN: {full_en}")
    print(f"JA: {q.full_ja}")
    print("-" * 60)


def ask_one(q: QuizItem, number: int, total: int) -> Optional[bool]:
    print("\n" + "=" * 60)
    print(f"Q{number}/{total}")
    if q.ja:
        print(f"日本語: {q.ja}")
    print(f"英文  : {q.cloze_en}")
    print("-" * 60)
    print("空欄に入る語句を入力してください（/s=スキップ, /q=終了）")
    user = input("> ").strip()

    if user == "/q":
        print("終了します。")
        sys.exit(0)

    if user == "/s" or user == "":
        print("\n[SKIP]")
        show_answer(q)
        return None

    correct = normalize(user) == normalize(q.answer)
    if correct:
        print("\n✅ 正解")
    else:
        print("\n❌ 不正解")
        print(f"あなたの解答: {user}")
        print(f"正解      : {q.answer}")

    show_answer(q)
    return correct


def main():
    xlsx_path = Path("quiz.xlsx")

    try:
        items = load_quiz_items_from_xlsx(xlsx_path)
    except Exception as e:
        print(f"読み込みエラー: {e}")
        sys.exit(1)

    if len(items) < 10:
        print(f"有効な問題数が不足しています（{len(items)} 問）。10問以上必要です。")
        sys.exit(1)

    quiz_set = random.sample(items, 10)

    correct = wrong = skipped = 0
    for i, q in enumerate(quiz_set, start=1):
        result = ask_one(q, i, 10)
        if result is True:
            correct += 1
        elif result is False:
            wrong += 1
        else:
            skipped += 1

    print("\n" + "=" * 60)
    print("結果")
    print(f"正解    : {correct}")
    print(f"不正解  : {wrong}")
    print(f"スキップ: {skipped}")
    print("=" * 60)
    print("おつかれさまでした！")


if __name__ == "__main__":
    main()
