# -*- coding: utf-8 -*-
"""
python -m run_test で実行できるようにするための薄いラッパー。

実体は tests/run_dummy_tests.py にある処理（tests/dummy_data を対象に①②③④を
実行し、結果を tests/results に保存する）をそのまま呼び出すだけ。

実行方法（archiver_app のフォルダで、cd tests をせずに実行できる）:
    python -m run_test
    python -m run_test -tag "a, b, c"
"""
from tests.run_dummy_tests import main

if __name__ == "__main__":
    main()
