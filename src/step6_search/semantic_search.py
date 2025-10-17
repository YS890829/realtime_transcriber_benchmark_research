#!/usr/bin/env python3
"""
Phase 6-3 Stage 1: Semantic Search Tool
ChromaDBに保存されたベクトルインデックスを使用してセマンティック検索を実行

機能:
- 自然言語クエリによるセマンティック検索
- トピック、エンティティ、時間範囲によるフィルタリング
- タイムスタンプ付き結果表示
- 類似度スコア表示
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
from chromadb.config import Settings

# 環境変数の読み込み
load_dotenv()

# Gemini APIキー選択（FREE/PAID tier）
use_paid_tier = os.getenv("USE_PAID_TIER", "").lower() == "true"
api_key = os.getenv("GEMINI_API_KEY_PAID") if use_paid_tier else os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in environment variables")
    sys.exit(1)

genai.configure(api_key=api_key)
print(f"✅ Using Gemini API: {'PAID' if use_paid_tier else 'FREE'} tier")


class SemanticSearchEngine:
    """セマンティック検索エンジンクラス"""

    def __init__(self, chroma_path: str = "chroma_db"):
        """
        Args:
            chroma_path: ChromaDBの保存先ディレクトリ
        """
        self.chroma_path = Path(chroma_path)

        if not self.chroma_path.exists():
            raise FileNotFoundError(f"ChromaDB not found at: {self.chroma_path}")

        # ChromaDB クライアント初期化
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )

        print(f"✅ Semantic Search Engine initialized")
        print(f"   ChromaDB path: {self.chroma_path}")
        print(f"   Embedding model: text-embedding-004")

    def list_collections(self) -> List[str]:
        """利用可能なコレクション一覧を取得"""
        collections = self.client.list_collections()
        return [col.name for col in collections]

    def search(
        self,
        query: str,
        collection_name: str = "transcripts_unified",
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        セマンティック検索を実行（デフォルト: 統合コレクション）

        Args:
            query: 検索クエリ（自然言語）
            collection_name: ChromaDBコレクション名（デフォルト: transcripts_unified）
            n_results: 返す結果の数
            filter_metadata: メタデータフィルター（例: {"source_file": {"$contains": "09-22"}}）

        Returns:
            検索結果のディクショナリ
        """
        print(f"\n🔍 Searching for: '{query}'")
        print(f"   Collection: {collection_name}")
        print(f"   Max results: {n_results}")

        # コレクション取得
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception as e:
            print(f"❌ Error: Collection '{collection_name}' not found")
            print(f"   Available collections: {', '.join(self.list_collections())}")
            return {"results": []}

        # クエリをベクトル化
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )
        query_embedding = result['embedding']

        # 検索実行
        search_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results
        }

        if filter_metadata:
            search_kwargs["where"] = filter_metadata

        results = collection.query(**search_kwargs)

        # 結果整形
        formatted_results = []
        for i, (doc, metadata, distance) in enumerate(
            zip(results['documents'][0], results['metadatas'][0], results['distances'][0]),
            1
        ):
            # 類似度スコア計算（距離から変換: 小さいほど類似）
            similarity_score = 1 / (1 + distance)

            result = {
                "rank": i,
                "text": doc,
                "metadata": metadata,
                "similarity_score": similarity_score,
                "distance": distance
            }
            formatted_results.append(result)

        return {
            "query": query,
            "collection": collection_name,
            "total_results": len(formatted_results),
            "results": formatted_results
        }

    def display_results(self, search_results: Dict[str, Any]) -> None:
        """検索結果を見やすく表示"""
        print(f"\n{'='*70}")
        print(f"Search Results for: '{search_results['query']}'")
        print(f"{'='*70}")

        if not search_results['results']:
            print("❌ No results found")
            return

        print(f"\nFound {search_results['total_results']} results:\n")

        for result in search_results['results']:
            print(f"{'─'*70}")
            print(f"Rank #{result['rank']} (Similarity: {result['similarity_score']:.4f})")
            print(f"{'─'*70}")

            # テキスト表示（長い場合は省略）
            text = result['text']
            if len(text) > 200:
                text = text[:200] + "..."
            print(f"\n📝 Text:\n   {text}")

            # メタデータ表示
            meta = result['metadata']

            # ソースファイル表示（統合コレクション用）
            if meta.get('source_file'):
                print(f"\n📂 Source: {meta['source_file']}")

            print(f"🗣️  Speaker: {meta.get('speaker', 'N/A')}")
            print(f"⏱️  Timestamp: {meta.get('timestamp', 'N/A')}")
            print(f"   Segment ID: {meta.get('segment_id', 'N/A')}")

            if meta.get('segment_topics'):
                print(f"\n🏷️  Segment Topics: {meta['segment_topics']}")

            if meta.get('global_topics'):
                print(f"   Global Topics: {meta['global_topics']}")

            if meta.get('people'):
                print(f"\n👥 People: {meta['people']}")

            if meta.get('organizations'):
                print(f"   Organizations: {meta['organizations']}")

            if meta.get('dates'):
                print(f"   Dates: {meta['dates']}")

            print()

    def search_by_topic(
        self,
        topic: str,
        collection_name: str = "transcripts_unified",
        n_results: int = 5
    ) -> Dict[str, Any]:
        """トピックで検索（デフォルト: 統合コレクション）"""
        print(f"\n🏷️  Searching by topic: '{topic}'")

        filter_metadata = {
            "$or": [
                {"segment_topics": {"$contains": topic}},
                {"global_topics": {"$contains": topic}}
            ]
        }

        return self.search(
            query=topic,
            collection_name=collection_name,
            n_results=n_results,
            filter_metadata=filter_metadata
        )

    def search_by_time_range(
        self,
        query: str,
        collection_name: str = "transcripts_unified",
        start_time: float = 0,
        end_time: float = 99999,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """時間範囲で検索（デフォルト: 統合コレクション）"""
        print(f"\n⏱️  Searching in time range: {start_time}s - {end_time}s")

        filter_metadata = {
            "$and": [
                {"start_time": {"$gte": start_time}},
                {"start_time": {"$lte": end_time}}
            ]
        }

        return self.search(
            query=query,
            collection_name=collection_name,
            n_results=n_results,
            filter_metadata=filter_metadata
        )


def main():
    """メイン処理"""
    print("=" * 70)
    print("Phase 6-3 Stage 1: Semantic Search Tool")
    print("=" * 70)

    # 検索エンジン初期化
    engine = SemanticSearchEngine(chroma_path="chroma_db")

    # 利用可能なコレクション表示
    collections = engine.list_collections()
    print(f"\n📚 Available collections:")
    for i, col in enumerate(collections, 1):
        print(f"   {i}. {col}")

    if not collections:
        print("❌ No collections found. Please run build_vector_index.py first.")
        sys.exit(1)

    # コレクション選択（デフォルト: transcripts_unified、またはCLI引数で指定）
    if len(sys.argv) > 1:
        collection_name = sys.argv[1]
    elif "transcripts_unified" in collections:
        collection_name = "transcripts_unified"
    else:
        collection_name = collections[0]  # デフォルトは最初のコレクション

    print(f"\n✅ Using collection: {collection_name}")

    # サンプル検索実行
    print(f"\n{'='*70}")
    print("Sample Searches")
    print(f"{'='*70}")

    # 1. 基本的なセマンティック検索
    print("\n" + "="*70)
    print("1. Basic Semantic Search")
    print("="*70)

    results1 = engine.search(
        query="プロダクト開発について",
        collection_name=collection_name,
        n_results=3
    )
    engine.display_results(results1)

    # 2. 別のクエリ
    print("\n" + "="*70)
    print("2. Another Search")
    print("="*70)

    results2 = engine.search(
        query="採用活動の課題",
        collection_name=collection_name,
        n_results=3
    )
    engine.display_results(results2)

    # 3. インタラクティブモード（オプション）
    if len(sys.argv) > 2 and sys.argv[2] == "--interactive":
        print("\n" + "="*70)
        print("Interactive Mode (type 'exit' to quit)")
        print("="*70)

        while True:
            try:
                user_query = input("\n🔍 Enter search query: ").strip()

                if user_query.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye!")
                    break

                if not user_query:
                    continue

                results = engine.search(
                    query=user_query,
                    collection_name=collection_name,
                    n_results=5
                )
                engine.display_results(results)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
