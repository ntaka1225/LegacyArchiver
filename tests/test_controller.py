# -*- coding: utf-8 -*-
"""
AppController（Model + Controller）のテスト。View（customtkinter）は使わない。

実行方法（コマンドプロンプトから）:
    python -m unittest discover -s tests -v
または
    python -m pytest tests -v

ダミーデータ（tests/dummy_data/output.csv 40件, tests/dummy_data/tags.txt 10件）を
一時フォルダにコピーしてから実行することで、実行のたびに files/ 配下が汚れないようにしている。
"""
import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from controller.app_controller import AppController  # noqa: E402
from model import scanner  # noqa: E402
from model.aggregator import read_extract_csv as aggregator_read_extract_csv  # noqa: E402

DUMMY_DIR = BASE_DIR / "tests" / "dummy_data"
DUMMY_TAGS = [
    "開発", "DR1", "xxxドキュメント", "セキュリティ", "品質",
    "見積", "契約", "運用", "新規顧客", "定例会議",
]


class ControllerTestBase(unittest.TestCase):
    """ダミーデータを一時フォルダにコピーし、独立した files フォルダで実行する。"""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

        # 探索対象フォルダ（ダミーデータをコピー）
        self.target_dir = self.tmpdir / "target"
        shutil.copytree(DUMMY_DIR, self.target_dir)

        # 出力先 files フォルダ
        self.files_dir = self.tmpdir / "files"
        self.controller = AppController(self.files_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _read_csv_rows(self, path):
        with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.reader(f))


class TestFolderValidation(ControllerTestBase):
    def test_default_folder_matches_files_dir(self):
        self.assertEqual(self.controller.default_folder(), str(self.files_dir))

    def test_is_valid_folder(self):
        self.assertTrue(self.controller.is_valid_folder(str(self.target_dir)))
        self.assertFalse(self.controller.is_valid_folder(str(self.tmpdir / "no_such_dir")))
        self.assertFalse(self.controller.is_valid_folder(""))

    def test_load_tag_candidates_recursively(self):
        tags = self.controller.load_tag_candidates(str(self.target_dir))
        self.assertEqual(tags, DUMMY_TAGS)


class TestPattern1Count(ControllerTestBase):
    """①タグの件数カウント"""

    def test_run_count_generates_all_tags_count_csv(self):
        result = self.controller.run_count(str(self.target_dir))

        self.assertEqual(result["tag_count"], 10)
        self.assertEqual(result["csv_file_count"], 1)

        output_path = Path(result["output_path"])
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path, self.files_dir / "all_tags_count.csv")

        rows = self._read_csv_rows(output_path)
        self.assertEqual(rows[0], ["タグ", "件数"])
        # ヘッダー + 10タグ分
        self.assertEqual(len(rows), 11)

        total_count = sum(int(r[1]) for r in rows[1:])
        # 40件のレコードそれぞれに1〜3個のタグが付与されているので、
        # 延べタグ件数は40件以上になっているはず
        self.assertGreaterEqual(total_count, 40)


class TestPattern2Extract(ControllerTestBase):
    """②指定タグの情報を抽出"""

    def test_run_extract_with_single_tag(self):
        result = self.controller.run_extract(str(self.target_dir), ["開発"])
        output_path = Path(result["output_path"])
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path, self.files_dir / "tags_output_開発.csv")

        rows = self._read_csv_rows(output_path)
        header = rows[0]
        self.assertEqual(header[0], "項目")
        self.assertEqual(header[1], "入力すべき内容")
        # ヘッダーの列数 = 項目+入力すべき内容 + 抽出件数
        self.assertEqual(len(header), 2 + result["matched_count"])

        # データ行数 = 項目数（タグ列を含め26項目）+ 最終記録日の行
        self.assertEqual(len(rows) - 1, 26 + 1)

        # 1行目は「記録日」であること
        self.assertEqual(rows[1][0], "記録日")

        # 最終行は「最終記録日」であること
        self.assertEqual(rows[-1][0], "最終記録日")
        self.assertNotEqual(rows[-1][1], "")

    def test_run_extract_with_multiple_tags_returns_union(self):
        single_result = self.controller.run_extract(str(self.target_dir), ["開発"])
        union_result = self.controller.run_extract(
            str(self.target_dir), ["開発", "セキュリティ"]
        )
        # 複数タグ指定時は、単一タグ指定時以上の件数がヒットするはず
        self.assertGreaterEqual(union_result["matched_count"], single_result["matched_count"])
        # ファイル名にも両方のタグが含まれる
        self.assertEqual(
            Path(union_result["output_path"]).name, "tags_output_開発_セキュリティ.csv"
        )

    def test_run_extract_with_no_matching_tag_returns_zero(self):
        result = self.controller.run_extract(str(self.target_dir), ["存在しないタグ"])
        self.assertEqual(result["matched_count"], 0)


class TestPattern4Merge(ControllerTestBase):
    """④継続的な統合"""

    def setUp(self):
        super().setUp()
        # 記録日の異なる4件を持つ独自のターゲットフォルダを用意する
        self.merge_target = self.tmpdir / "merge_target"
        self.merge_target.mkdir()
        (self.merge_target / "tags.txt").write_text("タグA\n", encoding="utf-8")

        header = (
            "記録日,案件名・タイトル,依頼元 / 依頼者,依頼内容,対応者（判断者）,依頼の背景,"
            "制約条件,最終決裁者,判断・回答,判断理由,根拠（基準・文書）,検討した他の選択肢,"
            "却下した理由,判断への確信度,通常と異なる対応か,異なる対応をした理由,その後の結果,"
            "今なら同じ判断をするか,トラブルになったこと,やってはいけないこと,この判断の時期,"
            "見直し時期・有効期限,社内特有の用語・言い回し,配慮した人間関係・政治的背景,"
            "先輩が大事にしていること,タグ\n"
        )

        def make_row(record_date, marker):
            cells = [""] * 25
            cells[0] = record_date
            cells[1] = marker  # 案件名・タイトルにマーカーを入れて判別できるようにする
            return ",".join(cells) + f",タグA\n"

        rows = (
            make_row("2026/01/01", "old-1")
            + make_row("2026/01/05", "old-2")
            + make_row("2026/01/10", "new-1")
            + make_row("2026/01/15", "new-2")
        )
        (self.merge_target / "output.csv").write_text(
            header + rows, encoding="utf-8-sig"
        )

    def test_run_merge_adds_only_records_after_last_recorded_date(self):
        # 1回目：2026/01/05までのデータだけが見えるフォルダで先に抽出しておく
        partial_target = self.tmpdir / "partial_target"
        partial_target.mkdir()
        (partial_target / "tags.txt").write_text("タグA\n", encoding="utf-8")
        header_and_two_rows = (self.merge_target / "output.csv").read_text(
            encoding="utf-8-sig"
        )
        # 先頭2件（old-1, old-2）だけを使う
        lines = header_and_two_rows.splitlines(keepends=True)
        (partial_target / "output.csv").write_text(
            "".join(lines[:3]), encoding="utf-8-sig"
        )

        first_result = self.controller.run_extract(str(partial_target), ["タグA"])
        self.assertEqual(first_result["matched_count"], 2)

        base_file = Path(first_result["output_path"])
        _, last_date = aggregator_read_extract_csv(base_file)
        self.assertEqual(last_date, "2026/01/05")

        # 2回目：全4件が見えるフォルダに対して④統合を実行する
        merge_result = self.controller.run_merge(str(base_file), str(self.merge_target))

        self.assertEqual(merge_result["tags"], ["タグA"])
        self.assertEqual(merge_result["previous_last_date"], "2026/01/05")
        # new-1, new-2 の2件が新たに追加される
        self.assertEqual(merge_result["added_count"], 2)
        self.assertEqual(merge_result["total_count"], 4)

        records, new_last_date = aggregator_read_extract_csv(base_file)
        self.assertEqual(len(records), 4)
        self.assertEqual(new_last_date, "2026/01/15")

        titles = [r["案件名・タイトル"] for r in records]
        self.assertEqual(titles, ["old-1", "old-2", "new-1", "new-2"])

    def test_run_merge_does_not_duplicate_unchanged_boundary_record(self):
        first_result = self.controller.run_extract(str(self.merge_target), ["タグA"])
        self.assertEqual(first_result["matched_count"], 4)
        base_file = Path(first_result["output_path"])

        # 同じフォルダに対してもう一度④を実行しても、内容が同じレコードは増えない
        merge_result = self.controller.run_merge(str(base_file), str(self.merge_target))
        self.assertEqual(merge_result["added_count"], 0)
        self.assertEqual(merge_result["total_count"], 4)


class TestPattern3Index(ControllerTestBase):
    """③索引ファイルの生成"""

    def test_run_index_generates_index_csv(self):
        result = self.controller.run_index(str(self.target_dir))
        output_path = Path(result["output_path"])
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path, self.files_dir / "index.csv")

        rows = self._read_csv_rows(output_path)
        self.assertEqual(len(rows), 10)  # タグ数ぶんの行

        row_by_tag = {r[0]: r[1:] for r in rows}
        self.assertIn("開発", row_by_tag)
        # ダミーデータのoutput.csvは1つなので、ファイル名は1件のみ載るはず
        self.assertEqual(row_by_tag["開発"], ["output.csv"])


class TestRecursiveScan(unittest.TestCase):
    """複数フォルダにまたがるファイルを正しく再帰的に見つけられるかの確認。"""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.files_dir = self.tmpdir / "files"
        self.controller = AppController(self.files_dir)

        # target/a/tags.txt, target/b/output.csv のように分散配置する
        self.target_dir = self.tmpdir / "target"
        (self.target_dir / "a").mkdir(parents=True)
        (self.target_dir / "b" / "c").mkdir(parents=True)

        (self.target_dir / "a" / "tags.txt").write_text("タグ1\nタグ2\n", encoding="utf-8")
        (self.target_dir / "b" / "tags.txt").write_text("タグ2\nタグ3\n", encoding="utf-8")

        header = "記録日,案件名・タイトル,依頼元 / 依頼者,依頼内容,対応者（判断者）,依頼の背景,制約条件,最終決裁者,判断・回答,判断理由,根拠（基準・文書）,検討した他の選択肢,却下した理由,判断への確信度,通常と異なる対応か,異なる対応をした理由,その後の結果,今なら同じ判断をするか,トラブルになったこと,やってはいけないこと,この判断の時期,見直し時期・有効期限,社内特有の用語・言い回し,配慮した人間関係・政治的背景,先輩が大事にしていること,タグ\n"
        row_tag1_only = ",,,,,,,,,,,,,,,,,,,,,,,,," + "タグ1\n"
        row_tag2_and_3 = ",,,,,,,,,,,,,,,,,,,,,,,,," + "タグ2,タグ3\n"
        # b/c/output.csv にはタグ1とタグ2の両方が登場するようにする
        (self.target_dir / "b" / "c" / "output.csv").write_text(
            header + row_tag1_only + row_tag2_and_3, encoding="utf-8-sig"
        )
        # a/output.csv にもタグ2が登場するようにする（複数ファイルにまたがる確認用）
        (self.target_dir / "a" / "output.csv").write_text(
            header + row_tag2_and_3, encoding="utf-8-sig"
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_scan_root_finds_nested_files(self):
        tag_files, csv_files = scanner.scan_root(self.target_dir)
        self.assertEqual(len(tag_files), 2)
        self.assertEqual(len(csv_files), 2)

    def test_tags_merged_without_duplicates(self):
        tags = self.controller.load_tag_candidates(str(self.target_dir))
        self.assertEqual(tags, ["タグ1", "タグ2", "タグ3"])

    def test_index_records_correct_relative_paths(self):
        result = self.controller.run_index(str(self.target_dir))
        with Path(result["output_path"]).open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        row_by_tag = {r[0]: sorted(r[1:]) for r in rows}
        self.assertEqual(row_by_tag["タグ2"], sorted(["a/output.csv", "b/c/output.csv"]))


if __name__ == "__main__":
    unittest.main()
