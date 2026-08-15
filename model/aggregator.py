# -*- coding: utf-8 -*-
"""
①タグ件数カウント／②タグ指定抽出／③索引ファイル生成／④継続的な統合 の集計ロジック。

Model層のみに依存し、UI（customtkinter）には一切依存しない。
"""
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from model.field_meta import FIELD_METAS, TAGS_COLUMN
from model.scanner import (
    load_records_from_csv,
    load_tags_from_files,
    relative_path,
    split_tags,
)

RECORD_DATE_COLUMN = "記録日"
LAST_RECORD_DATE_LABEL = "最終記録日"
EXTRACT_FILE_PREFIX = "tags_output_"
EXTRACT_FILE_SUFFIX = ".csv"

# ファイル名に使えない文字をハイフンに置き換える
_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\s]+')


def sanitize_tag_for_filename(tag: str) -> str:
    """タグ名をファイル名に使える形に変換する。"""
    cleaned = _INVALID_FILENAME_CHARS.sub("-", tag.strip())
    return cleaned or "tag"


def build_extract_filename(selected_tags: List[str], suffix: str = "") -> str:
    """②④で使うファイル名を作る。例: tags_output_DR1_DR2.csv

    suffixを指定すると、拡張子の前に "_<suffix>" を挿入する
    （例: suffix="after" -> tags_output_DR1_after.csv）。
    """
    safe_tags = [sanitize_tag_for_filename(t) for t in selected_tags]
    core = f"{EXTRACT_FILE_PREFIX}{'_'.join(safe_tags)}"
    if suffix:
        core += f"_{suffix}"
    return f"{core}{EXTRACT_FILE_SUFFIX}"


def parse_tags_from_filename(filename: str) -> List[str]:
    """②で生成したファイル名からタグ一覧を復元する（④で使用）。

    例: tags_output_DR1_DR2.csv -> ["DR1", "DR2"]
    ※ タグ名自体にアンダースコアが含まれる場合は正しく復元できない点に注意。
    """
    name = Path(filename).name
    if not (name.startswith(EXTRACT_FILE_PREFIX) and name.endswith(EXTRACT_FILE_SUFFIX)):
        return []
    core = name[len(EXTRACT_FILE_PREFIX): -len(EXTRACT_FILE_SUFFIX)]
    return [t for t in core.split("_") if t]


def parse_record_date(value: str) -> Optional[datetime]:
    """『記録日』列（yyyy/mm/dd想定）をdatetimeに変換する。変換できなければNone。"""
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def latest_record_date(records: List[Dict[str, str]]) -> str:
    """レコード群の中で最も新しい『記録日』を yyyy/mm/dd 形式の文字列で返す。
    有効な日付が1件もなければ空文字を返す。
    """
    parsed = [parse_record_date(r.get(RECORD_DATE_COLUMN, "")) for r in records]
    parsed = [d for d in parsed if d is not None]
    if not parsed:
        return ""
    return max(parsed).strftime("%Y/%m/%d")


def count_tags(root: Path, tag_files: List[Path], csv_files: List[Path]) -> List[Dict[str, str]]:
    """①タグ件数カウント。

    tags.txt から作った一覧に載っているタグのみ集計対象とする。
    戻り値: [{"タグ": ..., "件数": ...}, ...]（tags.txt の出現順）
    """
    tags = load_tags_from_files(tag_files)
    counts = {tag: 0 for tag in tags}

    for csv_path in csv_files:
        for row in load_records_from_csv(csv_path):
            row_tags = split_tags(row.get(TAGS_COLUMN, ""))
            for t in row_tags:
                if t in counts:
                    counts[t] += 1

    return [{"タグ": tag, "件数": str(counts[tag])} for tag in tags]


def extract_by_tags(
    root: Path,
    csv_files: List[Path],
    selected_tags: List[str],
    since_date: str = "",
):
    """②③④共通：指定タグが1つでも含まれるレコードを抽出する。

    since_date（yyyy/mm/dd）を指定すると、『記録日』がその日付以降
    （同日を含む）のレコードのみを対象にする（④の継続的な統合で使用）。
    since_dateが空文字、または『記録日』が解釈できない場合は対象に含める。

    戻り値: matched_records（output.csvの行(dict)のリスト）
    """
    selected = set(selected_tags)
    since = parse_record_date(since_date) if since_date else None
    matched_records: List[Dict[str, str]] = []

    for csv_path in csv_files:
        for row in load_records_from_csv(csv_path):
            row_tags = set(split_tags(row.get(TAGS_COLUMN, "")))
            if not (row_tags & selected):
                continue
            if since is not None:
                row_date = parse_record_date(row.get(RECORD_DATE_COLUMN, ""))
                if row_date is not None and row_date < since:
                    continue
            matched_records.append(row)

    return matched_records


def build_index(root: Path, tag_files: List[Path], csv_files: List[Path]) -> List[List[str]]:
    """③タグごとに、そのタグを含むoutput.csvのファイル名（root相対パス）一覧を作る。

    戻り値: [[タグ, ファイル1, ファイル2, ...], ...]（tags.txt の出現順）
    """
    tags = load_tags_from_files(tag_files)
    tag_to_files: Dict[str, List[str]] = {tag: [] for tag in tags}

    for csv_path in csv_files:
        rel = relative_path(csv_path, root)
        rows = load_records_from_csv(csv_path)
        tags_in_this_file = set()
        for row in rows:
            tags_in_this_file |= set(split_tags(row.get(TAGS_COLUMN, "")))

        for tag in tags_in_this_file:
            if tag in tag_to_files and rel not in tag_to_files[tag]:
                tag_to_files[tag].append(rel)

    return [[tag] + tag_to_files[tag] for tag in tags]


# ---------------------------------------------------------------------
# CSV書き出し
# ---------------------------------------------------------------------
def write_count_csv(output_path: Path, count_rows: List[Dict[str, str]]) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["タグ", "件数"])
        writer.writeheader()
        for row in count_rows:
            writer.writerow(row)


def write_extract_csv(output_path: Path, matched_records: List[Dict[str, str]]) -> None:
    """②④の抽出結果を、項目名・入力すべき内容・情報1・情報2... の横長CSVで書き出す。

    最終行に『最終記録日』（matched_records中で最も新しい記録日）を追記する。
    ④で継続的に取り込む際の『どこまで取り込み済みか』の目印として使う。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = ["項目", "入力すべき内容"] + [
        f"情報{i + 1}" for i in range(len(matched_records))
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for meta in FIELD_METAS:
            row = [meta.label, meta.desc]
            for record in matched_records:
                row.append(record.get(meta.label, ""))
            writer.writerow(row)
        writer.writerow([LAST_RECORD_DATE_LABEL, latest_record_date(matched_records)])


def read_extract_csv(input_path: Path) -> Tuple[List[Dict[str, str]], str]:
    """②④で生成した横長CSVを読み込み、レコード（dictのリスト）と
    最終記録日を復元する（④で既存ファイルに追記する際に使用）。

    ファイルが存在しない場合は ([], "") を返す。
    """
    input_path = Path(input_path)
    if not input_path.exists():
        return [], ""

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    if not rows:
        return [], ""

    header = rows[0]
    n_records = max(len(header) - 2, 0)

    field_rows = []
    last_date = ""
    for row in rows[1:]:
        if not row:
            continue
        if row[0] == LAST_RECORD_DATE_LABEL:
            last_date = row[1] if len(row) > 1 else ""
            continue
        field_rows.append(row)

    records: List[Dict[str, str]] = [dict() for _ in range(n_records)]
    for row in field_rows:
        label = row[0]
        for i in range(n_records):
            col_index = 2 + i
            value = row[col_index] if len(row) > col_index else ""
            records[i][label] = value

    return records, last_date


def write_index_csv(output_path: Path, index_rows: List[List[str]]) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for row in index_rows:
            writer.writerow(row)
