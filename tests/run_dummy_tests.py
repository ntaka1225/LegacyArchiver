# -*- coding: utf-8 -*-
"""
tests/dummy_data を対象に①②③④を実際に実行し、結果をtests/resultsに保存するスクリプト。

View（customtkinter）を一切使わず、Controller（Model）のみを直接呼び出す。
unittestの自動テスト（test_controller.py）とは別に、生成物を目視確認したいときに使う。

実行方法（コマンドプロンプトから、このファイルがあるフォルダに移動して）:
    python run_dummy_tests.py
    python run_dummy_tests.py -tag "a, b, c"

-tag を指定しない場合、②のタグ指定抽出は "DR1" のみを選択したものとして実行する。

④は、②の結果ファイル（tags_output_タグ名.csv）に対して、
dummy_data/after_output.csv（output.csvに10件を追加したもの）を使って
継続的な統合を試す。上書きはせず、tags_output_タグ名_after.csv として別名で保存する。
"""
import argparse
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # tests/
APP_DIR = BASE_DIR.parent                             # archiver_app/ (Archiver本体)
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from controller.app_controller import AppController  # noqa: E402
from model import aggregator  # noqa: E402

DUMMY_DATA_DIR = BASE_DIR / "dummy_data"
RESULTS_DIR = BASE_DIR / "results"
AFTER_OUTPUT_CSV = DUMMY_DATA_DIR / "after_output.csv"

DEFAULT_TAGS = ["DR1"]


def parse_tags(tag_arg: str) -> list:
    """-tag "a, b, c" 形式の文字列を、前後の空白を除いたタグのリストに変換する。"""
    if not tag_arg:
        return DEFAULT_TAGS
    tags = [t.strip() for t in tag_arg.split(",") if t.strip()]
    return tags if tags else DEFAULT_TAGS


def run(tags_for_extract):
    if not DUMMY_DATA_DIR.exists():
        print(f"ダミーデータフォルダが見つかりません: {DUMMY_DATA_DIR}")
        sys.exit(1)

    # 実行のたびにresultsフォルダをクリアしてから生成する
    if RESULTS_DIR.exists():
        shutil.rmtree(RESULTS_DIR)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    controller = AppController(RESULTS_DIR)
    target = str(DUMMY_DATA_DIR)

    print("=== ①タグの件数カウント ===")
    result1 = controller.run_count(target)
    print(f"対象CSV数: {result1['csv_file_count']}件 / 集計タグ数: {result1['tag_count']}件")
    print(f"出力先: {result1['output_path']}")

    print()
    print(f"=== ②指定タグの情報を抽出（指定タグ: {', '.join(tags_for_extract)}） ===")
    result2 = controller.run_extract(target, tags_for_extract)
    print(f"対象CSV数: {result2['csv_file_count']}件 / 抽出件数: {result2['matched_count']}件")
    print(f"出力先: {result2['output_path']}")

    print()
    print("=== ③索引ファイルの生成 ===")
    result3 = controller.run_index(target)
    print(f"対象CSV数: {result3['csv_file_count']}件 / タグ数: {result3['tag_count']}件")
    print(f"出力先: {result3['output_path']}")

    print()
    print("=== ④継続的な統合（after_output.csvを使用） ===")
    if not AFTER_OUTPUT_CSV.exists():
        print(f"after_output.csv が見つかりません: {AFTER_OUTPUT_CSV}")
    else:
        # scanner はファイル名が厳密に output.csv のものだけを対象にするため、
        # after_output.csv を output.csv という名前で別フォルダに複製してから読み込ませる。
        after_source_dir = RESULTS_DIR / "_after_source"
        after_source_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(AFTER_OUTPUT_CSV, after_source_dir / "output.csv")

        after_filename = aggregator.build_extract_filename(tags_for_extract, suffix="after")
        after_output_path = RESULTS_DIR / after_filename

        result4 = controller.run_merge(
            existing_file=result2["output_path"],
            folder=str(after_source_dir),
            output_file=str(after_output_path),
        )
        print(f"対象タグ（ファイル名から復元）: {', '.join(result4['tags'])}")
        print(f"取込み基準日（②時点の最終記録日）: {result4['previous_last_date']}")
        print(f"追加件数: {result4['added_count']}件 / 合計件数: {result4['total_count']}件")
        print(f"出力先: {result4['output_path']}")

    print()
    print(f"すべての結果を {RESULTS_DIR} に保存しました。")


def main():
    parser = argparse.ArgumentParser(
        description="tests/dummy_data を対象に①②③④を実行し、tests/results に結果を保存する。"
    )
    parser.add_argument(
        "-tag",
        dest="tag",
        default=None,
        help='②④で使うタグをカンマ区切りで指定する（例: -tag "a, b, c"）。'
             '未指定の場合は "DR1" のみを使う。',
    )
    args = parser.parse_args()

    tags_for_extract = parse_tags(args.tag)
    run(tags_for_extract)


if __name__ == "__main__":
    main()
