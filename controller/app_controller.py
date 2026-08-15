# -*- coding: utf-8 -*-
"""
アプリケーションのコントローラ。

Model にのみ依存し、View（customtkinter）には一切依存しない。
そのため、View を介さずにコマンドプロンプトから直接テストできる。
"""
from pathlib import Path
from typing import List

from model import aggregator, scanner


class AppController:
    def __init__(self, files_dir: Path):
        self.files_dir = Path(files_dir)
        self.files_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------
    # 共通
    # ---------------------------------------------------------------
    def default_folder(self) -> str:
        """フォルダ指定欄のデフォルト値（filesフォルダ直下）。"""
        return str(self.files_dir)

    def is_valid_folder(self, folder: str) -> bool:
        return bool(folder) and Path(folder).is_dir()

    def is_valid_existing_extract_file(self, path: str) -> bool:
        """④で指定する『既存のtags_output_xxx.csv』として有効かどうか。"""
        if not path:
            return False
        p = Path(path)
        return (
            p.is_file()
            and p.name.startswith(aggregator.EXTRACT_FILE_PREFIX)
            and p.name.endswith(aggregator.EXTRACT_FILE_SUFFIX)
        )

    def preview_tags_from_existing_file(self, path: str) -> List[str]:
        """④の実行前に、選択したファイル名からタグを復元してUIに表示するためのプレビュー。"""
        if not self.is_valid_existing_extract_file(path):
            return []
        return aggregator.parse_tags_from_filename(Path(path).name)

    def load_tag_candidates(self, folder: str) -> List[str]:
        """②のタグ候補表示用。指定フォルダ配下のtags.txtから一覧を作る。"""
        if not self.is_valid_folder(folder):
            return []
        tag_files, _ = scanner.scan_root(Path(folder))
        return scanner.load_tags_from_files(tag_files)

    # ---------------------------------------------------------------
    # ①タグ件数カウント
    # ---------------------------------------------------------------
    def run_count(self, folder: str) -> dict:
        root = Path(folder)
        tag_files, csv_files = scanner.scan_root(root)
        count_rows = aggregator.count_tags(root, tag_files, csv_files)

        output_path = self.files_dir / "all_tags_count.csv"
        aggregator.write_count_csv(output_path, count_rows)

        return {
            "output_path": str(output_path),
            "tag_count": len(count_rows),
            "csv_file_count": len(csv_files),
        }

    # ---------------------------------------------------------------
    # ②タグ指定抽出
    # ---------------------------------------------------------------
    def run_extract(self, folder: str, selected_tags: List[str]) -> dict:
        root = Path(folder)
        _, csv_files = scanner.scan_root(root)
        matched_records = aggregator.extract_by_tags(root, csv_files, selected_tags)

        filename = aggregator.build_extract_filename(selected_tags)
        output_path = self.files_dir / filename
        aggregator.write_extract_csv(output_path, matched_records)

        return {
            "output_path": str(output_path),
            "matched_count": len(matched_records),
            "csv_file_count": len(csv_files),
        }

    # ---------------------------------------------------------------
    # ③索引ファイル生成
    # ---------------------------------------------------------------
    def run_index(self, folder: str) -> dict:
        root = Path(folder)
        tag_files, csv_files = scanner.scan_root(root)
        index_rows = aggregator.build_index(root, tag_files, csv_files)

        output_path = self.files_dir / "index.csv"
        aggregator.write_index_csv(output_path, index_rows)

        return {
            "output_path": str(output_path),
            "tag_count": len(index_rows),
            "csv_file_count": len(csv_files),
        }

    # ---------------------------------------------------------------
    # ④継続的な統合（既存のtags_output_xxx.csvに新しい情報を追加する）
    # ---------------------------------------------------------------
    def run_merge(self, existing_file: str, folder: str, output_file: str = None) -> dict:
        """④継続的な統合。

        output_file を指定すると、既存ファイルを上書きせず別ファイルとして保存する
        （比較確認用。通常のGUI操作では指定せず、既存ファイルを更新する）。
        """
        existing_path = Path(existing_file)
        tags = aggregator.parse_tags_from_filename(existing_path.name)
        existing_records, last_date = aggregator.read_extract_csv(existing_path)

        root = Path(folder)
        _, csv_files = scanner.scan_root(root)
        candidates = aggregator.extract_by_tags(root, csv_files, tags, since_date=last_date)

        # 既存レコードと完全に同一の内容は追加しない（同日中の再実行による重複を軽減）
        existing_set = {tuple(sorted(r.items())) for r in existing_records}
        new_records = [
            r for r in candidates if tuple(sorted(r.items())) not in existing_set
        ]

        combined_records = existing_records + new_records
        target_path = Path(output_file) if output_file else existing_path
        aggregator.write_extract_csv(target_path, combined_records)

        return {
            "output_path": str(target_path),
            "tags": tags,
            "previous_last_date": last_date,
            "added_count": len(new_records),
            "total_count": len(combined_records),
        }
