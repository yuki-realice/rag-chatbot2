"""
企業データベース用の高度な検索ロジック。
ベクトル検索、BM25検索、企業名フィルタリングを組み合わせたハイブリッド検索を提供。
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from collections import Counter
import math
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from pydantic.v1 import SecretStr
from pathlib import Path
import chromadb

from .config import Config
from .gemini import GeminiEmbeddings
from .utils.name_normalize import to_katakana


class EnhancedRetriever:
    """企業データベース用の高度な検索機能を提供するクラス"""
    
    def __init__(self):
        self.config = Config()
        
        self.top_k = 5
        self.final_k = 3
        self.score_threshold = 0.40  # 0.60から0.40に変更
        self.mmr_lambda = 0.5
        self.similarity_metric = "cosine"
        
        self.embeddings = GeminiEmbeddings()
        
        persist_dir = str(Path(self.config.CHROMA_STORE_DIR).resolve())
        self.vectorstore = Chroma(
            collection_name="leads",
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )
    
    def hybrid_search(
        self, 
        query: str, 
        company_filter: Optional[str] = None,
        row_id_filter: Optional[int] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None
    ) -> List[Document]:
        top_k = top_k or self.top_k
        score_threshold = score_threshold or self.score_threshold
        
        try:
            if not company_filter:
                company_filter = self._extract_company_name(query)
            vector_docs = self._vector_search(query, company_filter, row_id_filter, top_k)
            bm25_docs = self._bm25_search(query, company_filter, row_id_filter, top_k)
            combined_docs = self._combine_and_rerank(
                vector_docs, bm25_docs, query, score_threshold
            )
            
            # 行単位でグループ化
            row_grouped_docs = self._group_by_row_and_reconstruct(combined_docs, query)
            
            final_docs = row_grouped_docs[:self.final_k]
            
            # 検索デバッグ情報を出力
            self._print_search_debug_info(query, company_filter, final_docs)
            
            print(f"INFO: ハイブリッド検索完了 - ベクトル: {len(vector_docs)}, BM25: {len(bm25_docs)}, 行統合: {len(row_grouped_docs)}, 最終: {len(final_docs)}")
            return final_docs
        except Exception as e:
            print(f"ERROR: ハイブリッド検索エラー: {e}")
            return []
    
    def _extract_company_name(self, query: str) -> Optional[str]:
        """クエリから企業名を抽出（法人格の有無に関係なく検出）"""
        # 正規化されたクエリ
        normalized_query = self._normalize_search_query(query)
        
        # 1. 法人格付きの企業名パターン
        formal_patterns = [
            r'([^\s]+株式会社)',
            r'([^\s]+有限会社)', 
            r'([^\s]+合同会社)',
            r'([^\s]+合資会社)',
            r'([^\s]+合名会社)',
            r'([^\s]+会社)',
            r'(株式会社[^\s]+)',
            r'(有限会社[^\s]+)',
            r'(合同会社[^\s]+)',
            r'(合資会社[^\s]+)',
            r'(合名会社[^\s]+)',
        ]
        
        # 法人格付きパターンを優先検索
        for pattern in formal_patterns:
            match = re.search(pattern, normalized_query)
            if match:
                company_name = match.group(1)
                print(f"INFO: クエリから法人格付き企業名を抽出: {company_name}")
                return company_name
        
        # 2. 一般的な企業名パターン（法人格なし）
        # 3文字以上のカタカナ・ひらがな・漢字の組み合わせを企業名として扱う
        general_patterns = [
            r'([ア-ヶ]{3,})',  # カタカナ3文字以上
            r'([ひ-ゞ]{3,})',  # ひらがな3文字以上  
            r'([一-龯]{2,})',  # 漢字2文字以上
            r'([A-Za-z]{3,})', # アルファベット3文字以上
            r'([ア-ヶ一-龯]{3,})', # カタカナ・漢字混合3文字以上
        ]
        
        for pattern in general_patterns:
            match = re.search(pattern, normalized_query)
            if match:
                company_name = match.group(1)
                # 一般的すぎる単語は除外
                if company_name not in ['企業', '会社', '検索', '情報', 'ステータス', 'リード']:
                    print(f"INFO: クエリから一般企業名を抽出: {company_name}")
                    return company_name
        
        # 3. クエリ全体を企業名として扱う（短い場合）
        if len(normalized_query.strip()) >= 2:
            print(f"INFO: クエリ全体を企業名として使用: {normalized_query.strip()}")
            return normalized_query.strip()
            
        return None
    
    def _vector_search(
        self, 
        query: str, 
        company_filter: Optional[str],
        row_id_filter: Optional[int], 
        top_k: int
    ) -> List[Document]:
        try:
            where_filter = None
            
            # row_id_filterが指定されている場合は優先して適用
            if row_id_filter is not None:
                where_filter = {"row_id": row_id_filter}
                print(f"INFO: ベクトル検索でrow_id={row_id_filter}によるフィルタリングを適用")
            elif company_filter:
                # 会社名の順序・表記ゆれで検索結果を落とさないため、ベクター側の厳密フィルタは外す
                # （BM25側の事前フィルタと最終リランキングで十分に絞り込む）
                where_filter = None
            docs = self.vectorstore.max_marginal_relevance_search(
                query,
                k=top_k,
                fetch_k=max(20, top_k * 2),
                lambda_mult=self.mmr_lambda,
                filter=where_filter
            )
            print(f"INFO: ベクトル検索結果: {len(docs)}件")
            return docs
        except Exception as e:
            print(f"WARNING: ベクトル検索エラー: {e}")
            return []
    
    def _bm25_search(
        self, 
        query: str, 
        company_filter: Optional[str],
        row_id_filter: Optional[int], 
        top_k: int
    ) -> List[Document]:
        try:
            collection = self.vectorstore._collection
            all_docs = collection.get(include=["documents", "metadatas"])
            if not all_docs or not all_docs.get("documents"):
                return []
            documents = all_docs["documents"]
            metadatas = all_docs["metadatas"] or [{}] * len(documents)
            
            # row_id_filterが指定されている場合は優先して適用
            if row_id_filter is not None:
                filtered_docs = []
                filtered_metas = []
                for doc, meta in zip(documents, metadatas):
                    if meta.get("row_id") == row_id_filter:
                        filtered_docs.append(doc)
                        filtered_metas.append(meta)
                documents = filtered_docs
                metadatas = filtered_metas
                print(f"INFO: BM25検索でrow_id={row_id_filter}によるフィルタリングを適用（{len(documents)}件）")
            elif company_filter:
                filtered_docs = []
                filtered_metas = []
                for doc, meta in zip(documents, metadatas):
                    company = meta.get("company", "")
                    if (company_filter.lower() in company.lower() or 
                        company_filter.lower() in doc.lower()):
                        filtered_docs.append(doc)
                        filtered_metas.append(meta)
                documents = filtered_docs
                metadatas = filtered_metas
            if not documents:
                return []
            scored_docs = self._calculate_bm25_scores(query, documents, metadatas)
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            top_docs = scored_docs[:top_k]
            result_docs = []
            for score, doc, meta in top_docs:
                result_docs.append(Document(page_content=doc, metadata={**meta, "bm25_score": score}))
            print(f"INFO: BM25検索結果: {len(result_docs)}件")
            return result_docs
        except Exception as e:
            print(f"WARNING: BM25検索エラー: {e}")
            return []
    
    def _calculate_bm25_scores(
        self, 
        query: str, 
        documents: List[str], 
        metadatas: List[Dict]
    ) -> List[Tuple[float, str, Dict]]:
        k1 = 1.2
        b = 0.75
        doc_tokens = []
        doc_lengths = []
        for doc in documents:
            tokens = self._tokenize_japanese(doc)
            doc_tokens.append(tokens)
            doc_lengths.append(len(tokens))
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0
        query_tokens = self._tokenize_japanese(query)
        scored_docs = []
        for i, (doc, meta, tokens, doc_len) in enumerate(zip(documents, metadatas, doc_tokens, doc_lengths)):
            score = 0.0
            for query_token in query_tokens:
                tf = tokens.count(query_token)
                if tf == 0:
                    continue
                df = sum(1 for doc_tokens_i in doc_tokens if query_token in doc_tokens_i)
                idf = math.log((len(documents) - df + 0.5) / (df + 0.5))
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / avg_doc_length))
                score += idf * (numerator / denominator)
            company = meta.get("company", "")
            company_alias = meta.get("company_alias", "")
            url_domain = meta.get("url_domain", "")
            for query_token in query_tokens:
                if (query_token in company.lower() or 
                    query_token in (company_alias.lower() if company_alias else "") or 
                    query_token in (url_domain.lower() if url_domain else "")):
                    score += 2.0
            scored_docs.append((score, doc, meta))
        return scored_docs
    
    def _normalize_search_query(self, query: str) -> str:
        """検索クエリの正規化処理（全角半角、カタカナひらがな統一など）"""
        if not query:
            return ""
        
        # 全角英数字を半角に変換
        query = query.translate(str.maketrans(
            'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９',
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        ))
        
        # ひらがなをカタカナに統一（インデックス時と統一）
        query = to_katakana(query)
        
        # 不要な記号・空白を除去
        query = re.sub(r'[^\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '', query)
        
        # 「株」を「株式会社」に正規化
        query = re.sub(r'(株)$', '株式会社', query)
        query = re.sub(r'^(株)', '株式会社', query)
        
        return query.strip().lower()
    
    def _katakana_to_hiragana(self, text: str) -> str:
        """カタカナをひらがなに変換"""
        katakana = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴァィゥェォャュョッー"
        hiragana = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽゔぁぃぅぇぉゃゅょっー"
        
        for k, h in zip(katakana, hiragana):
            text = text.replace(k, h)
        return text
    
    def _tokenize_japanese(self, text: str) -> List[str]:
        if not text:
            return []
        tokens = re.findall(r'[a-zA-Z0-9]+|[ひらがなカタカナ一-龯]+', text.lower())
        tokens = [token for token in tokens if len(token) > 1 or re.match(r'[a-zA-Z0-9]', token)]
        return tokens
    
    def _combine_and_rerank(
        self, 
        vector_docs: List[Document], 
        bm25_docs: List[Document], 
        query: str,
        score_threshold: float
    ) -> List[Document]:
        seen_contents = set()
        combined_docs = []
        for doc in vector_docs:
            content_hash = hash(doc.page_content[:100])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                doc.metadata["vector_rank"] = len(combined_docs) + 1
                combined_docs.append(doc)
        for doc in bm25_docs:
            content_hash = hash(doc.page_content[:100])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                doc.metadata["bm25_rank"] = len([d for d in combined_docs if "bm25_score" not in d.metadata]) + 1
                combined_docs.append(doc)
        for doc in combined_docs:
            doc.metadata["final_score"] = self._calculate_final_score(doc, query)
        filtered_docs = [doc for doc in combined_docs if doc.metadata.get("final_score", 0) >= score_threshold * 0.1]
        filtered_docs.sort(key=lambda x: x.metadata.get("final_score", 0), reverse=True)
        return filtered_docs
    
    def _calculate_final_score(self, doc: Document, query: str) -> float:
        score = 0.0
        query_terms = query.lower().split()
        
        # ベクターランクスコア
        vector_rank = doc.metadata.get("vector_rank")
        if vector_rank:
            score += (10 - vector_rank) * 0.3
        
        # BM25スコア
        bm25_score = doc.metadata.get("bm25_score", 0)
        score += bm25_score * 0.2
        
        # セル値の直接マッチング（最高優先度）
        cell_value = doc.metadata.get("cell_value", "")
        if cell_value:
            for term in query_terms:
                if term in cell_value.lower():
                    score += 5.0
                    print(f"DEBUG: セル値直接マッチ - '{term}' in '{cell_value}'")
        
        # 列名マッチング
        column_name = doc.metadata.get("column_name", "")
        if column_name:
            for term in query_terms:
                if term in column_name.lower():
                    score += 2.0
                    print(f"DEBUG: 列名マッチ - '{term}' in '{column_name}'")
        
        # 企業名マッチング（強化版）
        company = doc.metadata.get("company", "")
        company_alias = doc.metadata.get("company_alias", "")
        url_domain = doc.metadata.get("url_domain", "")
        if company:
            normalized_company = self._normalize_search_query(company)
            normalized_query = self._normalize_search_query(query)
            normalized_alias = self._normalize_search_query(company_alias) if company_alias else ""
            normalized_domain = self._normalize_search_query(url_domain) if url_domain else ""
            
            # 1. 完全一致（最高スコア）
            if normalized_query == normalized_company:
                score += 15.0  # 10.0から15.0に増加
                print(f"DEBUG: 企業名完全一致 - '{normalized_query}' == '{normalized_company}'")
            
            # 2. 前方一致
            elif normalized_company.startswith(normalized_query):
                score += 8.0
                print(f"DEBUG: 企業名前方一致 - '{normalized_query}' starts '{normalized_company}'")
            
            # 3. 後方一致（法人格を除いた部分）
            elif normalized_company.endswith(normalized_query):
                score += 7.0
                print(f"DEBUG: 企業名後方一致 - '{normalized_query}' ends '{normalized_company}'")
            
            # 4. 部分一致
            elif (normalized_query in normalized_company or 
                  (normalized_alias and normalized_query in normalized_alias) or 
                  (normalized_domain and normalized_query in normalized_domain)):
                score += 5.0
                print(f"DEBUG: 企業名部分一致 - '{normalized_query}' in '{normalized_company or normalized_alias or normalized_domain}'")
            
            # 5. 個別単語マッチング
            else:
                for term in query_terms:
                    normalized_term = self._normalize_search_query(term)
                    if len(normalized_term) >= 2:  # 2文字以上の単語のみ
                        if normalized_term in normalized_company:
                            score += 3.0
                            print(f"DEBUG: 企業名単語マッチ - '{normalized_term}' in '{normalized_company}'")
        
        # リードステータスマッチング
        lead_status = doc.metadata.get("lead_status", "")
        if lead_status in ["アポイント獲得", "リード獲得"]:
            score += 1.0
        elif lead_status in ["未コール"]:
            score += 0.5
            
        # セル位置情報を追加
        if doc.metadata.get("cell_position"):
            doc.metadata["cell_position_info"] = f"行{doc.metadata.get('excel_row', '?')}・{doc.metadata.get('column_name', '?')}列"
        
        return score
    
    def _group_by_row_and_reconstruct(self, docs: List[Document], query: str) -> List[Document]:
        """セル単位の検索結果を行単位でグループ化し、行全体を再構築"""
        if not docs:
            return docs
        
        # 行番号でグループ化
        row_groups = {}
        for doc in docs:
            excel_row = doc.metadata.get("excel_row")
            if excel_row:
                if excel_row not in row_groups:
                    row_groups[excel_row] = []
                row_groups[excel_row].append(doc)
        
        print(f"DEBUG: 検索結果を{len(row_groups)}行にグループ化")
        
        # 各行グループを処理
        reconstructed_docs = []
        for excel_row, row_docs in row_groups.items():
            try:
                # その行の全セル情報を取得
                full_row_data = self._get_full_row_data(excel_row, row_docs[0].metadata.get("sheet", ""))
                
                if full_row_data:
                    # 行全体の統合ドキュメントを作成
                    row_doc = self._create_row_document(full_row_data, row_docs, query)
                    reconstructed_docs.append(row_doc)
                    print(f"DEBUG: 行{excel_row}を再構築 - {len(full_row_data)}セル統合")
                    
            except Exception as e:
                print(f"WARNING: 行{excel_row}の再構築エラー: {e}")
                # エラー時は元のドキュメントの先頭を使用
                if row_docs:
                    reconstructed_docs.append(row_docs[0])
        
        # 行レベルでのスコアソート
        reconstructed_docs.sort(key=lambda x: x.metadata.get("final_score", 0), reverse=True)
        
        return reconstructed_docs
    
    def _get_full_row_data(self, excel_row: int, sheet_name: str) -> List[Dict]:
        """指定行の全セル情報をベクターストアから取得"""
        try:
            # その行の全セルを検索
            collection = self.vectorstore._collection
            where_clause = {"excel_row": excel_row}
            
            results = collection.get(
                where=where_clause,
                include=["metadatas", "documents"]
            )
            
            if not results or not results.get("metadatas"):
                return []
            
            # セル情報を列インデックス順にソート
            cell_data = []
            for meta, doc in zip(results["metadatas"], results["documents"]):
                cell_data.append({
                    "column_index": meta.get("column_index", 999),
                    "column_name": meta.get("column_name", ""),
                    "cell_value": meta.get("cell_value", ""),
                    "content": doc,
                    "metadata": meta
                })
            
            # 列インデックス順にソート
            cell_data.sort(key=lambda x: x["column_index"])
            
            return cell_data
            
        except Exception as e:
            print(f"ERROR: 行データ取得エラー: {e}")
            return []
    
    def _create_row_document(self, full_row_data: List[Dict], matching_docs: List[Document], query: str) -> Document:
        """行全体の統合ドキュメントを作成"""
        # 行全体のコンテンツを構築
        row_parts = []
        matched_columns = set()
        
        # マッチしたセルを特定
        for doc in matching_docs:
            col_name = doc.metadata.get("column_name", "")
            if col_name:
                matched_columns.add(col_name)
        
        # 全セルを順番に追加（マッチしたセルは強調）
        for cell in full_row_data:
            col_name = cell["column_name"]
            cell_value = cell["cell_value"]
            
            if col_name in matched_columns:
                row_parts.append(f"★{col_name}: {cell_value}")  # マッチしたセルを強調
            else:
                row_parts.append(f"{col_name}: {cell_value}")
        
        # 統合コンテンツ
        integrated_content = " | ".join(row_parts)
        
        # 代表メタデータ（最初のマッチしたセルから取得）
        base_metadata = matching_docs[0].metadata.copy()
        
        # 行レベルの追加情報
        base_metadata.update({
            "row_type": "integrated_row",
            "matched_columns": list(matched_columns),
            "total_columns": len(full_row_data),
            "row_content": integrated_content,
            "cell_position_info": f"行{base_metadata.get('excel_row', '?')}の全セル統合"
        })
        
        # 最高スコアを継承
        max_score = max([doc.metadata.get("final_score", 0) for doc in matching_docs])
        base_metadata["final_score"] = max_score
        
        return Document(
            page_content=integrated_content,
            metadata=base_metadata
        )
    
    def search_by_company_name(self, company_name: str) -> List[Document]:
        return self.hybrid_search(query=company_name, company_filter=company_name, top_k=self.final_k)
    
    def search_by_lead_status(self, lead_status: str) -> List[Document]:
        try:
            collection = self.vectorstore._collection
            results = collection.get(where={"lead_status": {"$eq": lead_status}}, include=["documents", "metadatas"])
            docs = []
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            for doc, meta in zip(documents, metadatas):
                docs.append(Document(page_content=doc, metadata=meta))
            docs.sort(key=lambda x: x.metadata.get("updated_at", ""), reverse=True)
            return docs[:self.final_k]
        except Exception as e:
            print(f"ERROR: リードステータス検索エラー: {e}")
            return []
    
    def _print_search_debug_info(self, query: str, company_filter: Optional[str], final_docs: List[Document]):
        """検索デバッグ情報を出力"""
        print(f"=== 検索デバッグ情報 ===")
        print(f"検索クエリ: '{query}'")
        print(f"正規化クエリ: '{self._normalize_search_query(query)}'")
        print(f"抽出企業名フィルタ: {company_filter}")
        
        if final_docs:
            print(f"検索結果企業:")
            for i, doc in enumerate(final_docs):
                company = doc.metadata.get("company", "Unknown")
                lead_status = doc.metadata.get("lead_status", "未設定")
                score = doc.metadata.get("final_score", 0)
                excel_row = doc.metadata.get("excel_row", "?")
                print(f"  {i+1}. 企業名: '{company}' | ステータス: {lead_status} | スコア: {score:.2f} | 行: {excel_row}")
        else:
            print("検索結果: マッチなし")
        print(f"========================")
    
    def get_search_statistics(self) -> Dict[str, Any]:
        try:
            collection = self.vectorstore._collection
            total_count = collection.count()
            
            # 既存のカウント処理
            lead_status_counts = {}
            company_counts = {}
            
            # 新しく追加するカウント処理
            sheet_counts = {}
            column_counts = {}
            domain_counts = {}
            row_type_counts = {}
            company_variant_counts = {}
            
            all_docs = collection.get(include=["metadatas"])
            metadatas = all_docs.get("metadatas", [])
            
            for meta in metadatas:
                # 既存の処理
                status = meta.get("lead_status", "未設定")
                lead_status_counts[status] = lead_status_counts.get(status, 0) + 1
                
                company = meta.get("company", "Unknown")
                company_counts[company] = company_counts.get(company, 0) + 1
                
                # 新しく追加する処理
                sheet = meta.get("sheet", "Unknown")
                sheet_counts[sheet] = sheet_counts.get(sheet, 0) + 1
                
                column_name = meta.get("column_name", "Unknown")
                if column_name and column_name != "Unknown":
                    column_counts[column_name] = column_counts.get(column_name, 0) + 1
                
                url_domain = meta.get("url_domain", "")
                if url_domain and url_domain != "Unknown":
                    domain_counts[url_domain] = domain_counts.get(url_domain, 0) + 1
                
                row_type = meta.get("row_type", "standard")
                row_type_counts[row_type] = row_type_counts.get(row_type, 0) + 1
                
                # 企業名バリアント数（文字列として保存されているので分割してカウント）
                variants = meta.get("company_name_variants", "")
                if variants and variants != "Unknown":
                    variant_count = len(variants.split("|"))
                    company_variant_counts[variant_count] = company_variant_counts.get(variant_count, 0) + 1
            
            # 企業名のトップ10
            top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # シート別のトップ5
            top_sheets = sorted(sheet_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 列別のトップ5
            top_columns = sorted(column_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # ドメイン別のトップ5
            top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                "total_documents": total_count, 
                "lead_status_distribution": lead_status_counts, 
                "top_companies": top_companies,
                
                # 新しく追加する統計情報
                "sheet_distribution": sheet_counts,
                "top_sheets": top_sheets,
                "column_distribution": column_counts,
                "top_columns": top_columns,
                "domain_distribution": domain_counts,
                "top_domains": top_domains,
                "row_type_distribution": row_type_counts,
                "company_variant_distribution": company_variant_counts,
                
                "search_parameters": {
                    "top_k": self.top_k, 
                    "final_k": self.final_k, 
                    "score_threshold": self.score_threshold, 
                    "mmr_lambda": self.mmr_lambda
                }
            }
        except Exception as e:
            return {"error": str(e)}