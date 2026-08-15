# -*- coding: utf-8 -*-
"""
Legacy Recipe が出力する output.csv の列構成に対応する項目メタ情報。

Legacy Recipe とは別スクリプトとして独立させるため、ここでは同じ内容を
（importせず）値として複製している。output.csv の列順・列名が変わった
場合は、ここも合わせて更新すること。
"""
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class FieldMeta:
    label: str  # output.csv の列名（＝項目名）
    desc: str   # 入力すべき内容（何を書く項目かの説明）


# output.csv の列順と完全に一致させること（タグ列を含む）
FIELD_METAS: List[FieldMeta] = [
    FieldMeta("記録日", "この記録を作成した日"),
    FieldMeta("案件名・タイトル", "何についての依頼・判断かが一目でわかる名称"),
    FieldMeta("依頼元 / 依頼者", "誰から来た依頼か（社内・社外、部署、役職）"),
    FieldMeta("依頼内容", "何を頼まれたか（評価してほしい／参画してほしい 等）"),
    FieldMeta("対応者（判断者）", "実際に判断した先輩・課長の名前"),
    FieldMeta("依頼の背景", "なぜこの依頼が発生したか（経緯）"),
    FieldMeta("制約条件", "納期、予算、体制、当時特有の事情など"),
    FieldMeta("最終決裁者", "誰が最終的にGOを出したか"),
    FieldMeta("判断・回答", "実際にどう判断・回答したか"),
    FieldMeta("判断理由", "なぜその判断に至ったか（考え方の流れ）"),
    FieldMeta("根拠（基準・文書）", "判断の拠り所とした社内規定・過去事例・数値基準など"),
    FieldMeta("検討した他の選択肢", "採用しなかった案"),
    FieldMeta("却下した理由", "その案を選ばなかった理由"),
    FieldMeta("判断への確信度", "迷わず決めたか、五分五分だったか"),
    FieldMeta("通常と異なる対応か", "Yes / No"),
    FieldMeta("異なる対応をした理由", "通常基準からあえて外れた背景"),
    FieldMeta("その後の結果", "うまくいった／問題が起きた 等"),
    FieldMeta("今なら同じ判断をするか", "後から振り返っての評価"),
    FieldMeta("トラブルになったこと", "過去に問題が起きた対応"),
    FieldMeta("やってはいけないこと", "明確に避けるべき対応・言動"),
    FieldMeta("この判断の時期", "いつの話か（古い制度に基づく可能性を明示）"),
    FieldMeta("見直し時期・有効期限", "制度改正等で陳腐化しそうな時期の目安"),
    FieldMeta("社内特有の用語・言い回し", "この案件で出てきた社内用語の説明"),
    FieldMeta("配慮した人間関係・政治的背景", "表には出しにくいが判断に影響した要素"),
    FieldMeta("先輩が大事にしていること", "基準には書かれていない、その人の価値観・こだわり"),
    FieldMeta("タグ", "この記録に付与されたタグ（カンマ区切り）"),
]

TAGS_COLUMN = "タグ"
