# -*- coding: utf-8 -*-
"""アプリ全体で共通利用するフォント設定（Legacy Recipeと同じサイズ体系）。"""

FONT_FAMILY = "Meiryo"


def font(size: int = 13, weight: str = "normal"):
    """customtkinterのfont引数にそのまま渡せるタプルを返す。"""
    return (FONT_FAMILY, size, weight)
