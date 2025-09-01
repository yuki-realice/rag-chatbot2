"""
企業名正規化ユーティリティ
インデックス時と検索時の両方で共通して使用される企業名の正規化処理
"""

import unicodedata
import re
from typing import List, Set

# 法人格トークン（前後で検出・除去）
CORP_TOKENS = [
    "株式会社", "(株)", "有限会社", "(有)", 
    "合同会社", "合資会社", "合名会社", 
    "一般社団法人", "公益社団法人", "一般財団法人", "公益財団法人",
    "特定非営利活動法人", "NPO法人", "学校法人", "社会福祉法人"
]

def to_katakana(s: str) -> str:
    """
    ひらがなをカタカナに変換し、全角半角・記号ゆらぎを吸収
    
    Args:
        s: 変換対象の文字列
        
    Returns:
        正規化された文字列
    """
    if s is None:
        return ""
    
    # Unicode正規化（NFKC: 半角カナ→全角カナ、全角英数→半角英数）
    s = unicodedata.normalize("NFKC", s)
    
    # ひらがな→カタカナ変換
    s = "".join(
        chr(ord(ch) + 0x60) if "ぁ" <= ch <= "ゖ" else ch 
        for ch in s
    )
    
    # 空白・記号ゆらぎ吸収
    s = (s.replace(" ", "").replace("　", "")
          .replace("ｰ", "ー").replace("-", "ー")
          .replace("‐", "ー").replace("−", "ー")
          .replace("・", "").replace("（", "").replace("）", "")
          .replace("(", "").replace(")", "")
          .replace(".", "").replace("．", "")
          .replace(",", "").replace("，", "")
          .replace("[", "").replace("]", "")
          .replace("「", "").replace("」", "")
          .replace("『", "").replace("』", ""))
    
    return s

def strip_corp(s: str) -> str:
    """
    法人格を除去
    
    Args:
        s: 企業名
        
    Returns:
        法人格を除去した企業名
    """
    if not s:
        return ""
    
    result = s
    for corp_token in CORP_TOKENS:
        # 前方除去
        if result.startswith(corp_token):
            result = result[len(corp_token):].strip()
        # 後方除去
        if result.endswith(corp_token):
            result = result[:-len(corp_token)].strip()
    
    return result

def normalize_name(name: str) -> str:
    """
    企業名を正規化（基本正規化）
    
    Args:
        name: 企業名
        
    Returns:
        正規化された企業名
    """
    if not name:
        return ""
    
    # カタカナ化と記号正規化
    normalized = to_katakana(name or "")
    
    # 前後の空白除去
    normalized = normalized.strip()
    
    return normalized

def build_name_variants(name: str) -> List[str]:
    """
    企業名のバリアントを生成（検索用）
    
    Args:
        name: 元の企業名
        
    Returns:
        企業名バリアントのリスト（重複なし）
    """
    if not name:
        return []
    
    # 基本正規化
    k = normalize_name(name)
    if not k:
        return []
    
    # 法人格を除去したコア名
    core = strip_corp(k)
    if not core:
        core = k
    
    # バリアント生成
    variants_set: Set[str] = set()
    
    # 1. 正規化済み名（そのまま）
    variants_set.add(k)
    
    # 2. コア名（法人格除去）
    if core != k:
        variants_set.add(core)
    
    # 3. 法人格バリエーション（後方付与）
    if core:
        variants_set.add(f"{core}株式会社")
        variants_set.add(f"{core}(株)")
        variants_set.add(f"{core}有限会社")
        variants_set.add(f"{core}(有)")
        variants_set.add(f"{core}合同会社")
    
    # 4. 法人格バリエーション（前方付与）
    if core:
        variants_set.add(f"株式会社{core}")
        variants_set.add(f"(株){core}")
        variants_set.add(f"有限会社{core}")
        variants_set.add(f"(有){core}")
    
    # 重複を除去してリストに変換
    variants_list = list(variants_set)
    
    # 空文字列を除去
    variants_list = [v for v in variants_list if v.strip()]
    
    return variants_list

def fuzzy_normalize_for_search(query: str) -> str:
    """
    検索クエリ用の正規化（より寛容）
    
    Args:
        query: 検索クエリ
        
    Returns:
        正規化されたクエリ
    """
    if not query:
        return ""
    
    # 基本正規化
    normalized = normalize_name(query)
    
    # 英数字も含めた正規化
    # 全角英数字→半角英数字
    normalized = normalized.translate(str.maketrans(
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    ))
    
    return normalized.lower()

def extract_core_company_name(text: str) -> str:
    """
    テキストから企業名の中核部分を抽出
    
    Args:
        text: 抽出対象のテキスト
        
    Returns:
        抽出された企業名（なければ空文字）
    """
    if not text:
        return ""
    
    # 正規化
    normalized = fuzzy_normalize_for_search(text)
    
    # 法人格付きパターンの検出
    formal_patterns = [
        r'([^\s]+株式会社)',
        r'([^\s]+有限会社)',
        r'([^\s]+合同会社)',
        r'([^\s]+合資会社)',
        r'([^\s]+合名会社)',
        r'(株式会社[^\s]+)',
        r'(有限会社[^\s]+)',
        r'(合同会社[^\s]+)',
        r'(\(株\)[^\s]+)',
        r'([^\s]+\(株\))',
    ]
    
    for pattern in formal_patterns:
        match = re.search(pattern, normalized)
        if match:
            return match.group(1)
    
    # 一般的な企業名パターン（3文字以上のカタカナ・漢字）
    general_patterns = [
        r'([ア-ヶ]{3,})',      # カタカナ3文字以上
        r'([一-龯]{2,})',      # 漢字2文字以上
        r'([A-Za-z]{3,})',     # アルファベット3文字以上
        r'([ア-ヶ一-龯]{3,})', # カタカナ・漢字混合3文字以上
    ]
    
    for pattern in general_patterns:
        match = re.search(pattern, normalized)
        if match:
            candidate = match.group(1)
            # 一般的すぎる単語は除外
            if candidate not in ['企業', '会社', '検索', '情報', 'ステータス', 'リード', 'データ']:
                return candidate
    
    # 2文字以上なら全体を返す
    if len(normalized.strip()) >= 2:
        return normalized.strip()
    
    return ""
