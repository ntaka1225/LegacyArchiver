# -*- coding: utf-8 -*-
"""
Archiver エントリーポイント。

起動方法（プロトタイプ）:
    コマンドプロンプトで、このファイルがあるフォルダに移動して
        python __main__.py
    を実行してください。

    バージョンを確認したいだけの場合は以下を実行してください。
        python __main__.py -v
        python __main__.py --version

同フォルダの files/ が、フォルダ指定欄のデフォルト（探索対象）であり、
かつ生成物（all_tags_count.csv / tags_output.csv / index.csv）の出力先です。
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from version import __version__  # noqa: E402


def main():
    # -v / --version が指定された場合はバージョンだけ表示して終了する
    # （GUIライブラリの読み込みが不要になるよう、他のimportより先に判定する）
    if any(arg in ("-v", "--version") for arg in sys.argv[1:]):
        print(f"Archiver v{__version__}")
        return

    from controller.app_controller import AppController
    from view.main_window import MainWindow

    files_dir = BASE_DIR / "files"
    controller = AppController(files_dir)

    app = MainWindow(controller)
    app.mainloop()


if __name__ == "__main__":
    main()
