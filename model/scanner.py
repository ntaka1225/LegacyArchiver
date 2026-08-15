# -*- coding: utf-8 -*-
"""
指定フォルダ配下（サブフォルダ含む）を探索して tags.txt / output.csv を
見つけ、読み込むためのモジュール。UI（customtkinter）には一切依存しない。
"""
import csv
import os
from pathlib import Path
from typing import Dict, List

from model.field_meta import TAGS_COLUMN

TAGS_FILENAME = "tags.txt"
OUTPUT_CSV_FILENAME = "output.csv"


def find_files(root: Path, filename: str) -> List[Path]:
    """root配下（サブフォルダ含む）から指定ファイル名を再帰的に探す。"""
    root = Path(root)
    if not root.exists():
        return []
    return sorted(root.rglob(filename))


def load_tags_from_files(tag_file_paths: List[Path]) -> List[str]:
    """複数のtags.txtから、重複を除いたタグ一覧を作る（出現順を維持）。"""
    seen = []
    for path in tag_file_paths:
        try:
            with Path(path).open("r", encoding="utf-8") as f:
                for line in f:
                    tag = line.strip()
                    if tag and tag not in seen:
                        seen.append(tag)
        except OSError:
            continue
    return seen


def load_records_from_csv(csv_path: Path) -> List[Dict[str, str]]:
    """1つのoutput.csvを読み込み、行（レコード）のリストを返す。"""
    try:
        with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return [dict(row) for row in reader]
    except OSError:
        return []


def split_tags(tag_cell: str) -> List[str]:
    """output.csvの『タグ』列（カンマ区切り）を分割し、前後の空白を除く。"""
    if not tag_cell:
        return []
    return [t.strip() for t in tag_cell.split(",") if t.strip()]


def relative_path(csv_path: Path, root: Path) -> str:
    """rootを基準にした相対パス（表示・記録用）。区切り文字は / に統一する。"""
    rel = os.path.relpath(str(csv_path), start=str(root))
    return rel.replace(os.sep, "/")


def scan_root(root: Path):
    """root配下のtags.txtとoutput.csvをまとめて探索するショートカット。"""
    tag_files = find_files(root, TAGS_FILENAME)
    csv_files = find_files(root, OUTPUT_CSV_FILENAME)
    return tag_files, csv_files
