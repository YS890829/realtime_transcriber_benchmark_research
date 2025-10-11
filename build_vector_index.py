#!/usr/bin/env python3
"""
Phase 6-3 Stage 1: Vector Index Builder
ChromaDBを使用して文字起こしセグメントをベクトル化し、セマンティック検索用のインデックスを構築

機能:
- enhanced JSONファイルからセグメントを読み込み
- OpenAI Embeddings API (text-embedding-3-small) でベクトル化
- ChromaDBにメタデータ付きで保存
- トピック、エンティティ、タイムスタンプを含むメタデータ
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.config import Settings

# 環境変数の読み込み
load_dotenv()

# OpenAI API キー確認
if not os.getenv("OPENAI_API_KEY"):
    print("❌ Error: OPENAI_API_KEY not found in environment variables")
    sys.exit(1)


class VectorIndexBuilder:
    """文字起こしデータのベクトルインデックス構築クラス"""

    def __init__(self, chroma_path: str = "chroma_db"):
        """
        Args:
            chroma_path: ChromaDBの保存先ディレクトリ
        """
        self.chroma_path = Path(chroma_path)
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        # ChromaDB クライアント初期化
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # OpenAI Embeddings 初期化 (text-embedding-3-small)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        print(f"✅ ChromaDB initialized at: {self.chroma_path}")
        print(f"✅ Using OpenAI model: text-embedding-3-small")

    def load_enhanced_json(self, json_path: str) -> Dict[str, Any]:
        """enhanced JSONファイルを読み込み"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"✅ Loaded JSON: {json_path}")
        print(f"   Segments: {len(data.get('segments', []))}")
        print(f"   Topics: {len(data.get('topics', []))}")
        print(f"   Entities: {sum(len(v) for v in data.get('entities', {}).values())}")

        return data

    def prepare_documents(self, data: Dict[str, Any]) -> tuple[List[str], List[Dict[str, Any]]]:
        """
        セグメントからドキュメントとメタデータを準備

        Returns:
            texts: ベクトル化するテキストのリスト
            metadatas: 各テキストに対応するメタデータのリスト
        """
        segments = data.get('segments', [])
        topics = data.get('topics', [])
        entities = data.get('entities', {})
        file_metadata = data.get('metadata', {})

        # トピックIDからトピック名へのマッピング作成
        topic_map = {topic['id']: topic['name'] for topic in topics}

        texts = []
        metadatas = []

        for segment in segments:
            # セグメントテキスト
            text = segment.get('text', '').strip()
            if not text:
                continue

            # メタデータ作成
            metadata = {
                'segment_id': segment.get('id'),
                'start_time': segment.get('start'),
                'end_time': segment.get('end'),
                'file_name': file_metadata.get('file', {}).get('file_name', ''),
                'duration': segment.get('end', 0) - segment.get('start', 0),
            }

            # セグメントトピック
            segment_topics = segment.get('topics', [])
            if segment_topics:
                topic_names = [topic_map.get(tid, tid) for tid in segment_topics]
                metadata['topics'] = ', '.join(topic_names)
            else:
                metadata['topics'] = ''

            # グローバルトピック（全体のトピック）
            if topics:
                global_topic_names = [t['name'] for t in topics[:3]]  # 上位3つ
                metadata['global_topics'] = ', '.join(global_topic_names)
            else:
                metadata['global_topics'] = ''

            # エンティティ情報
            metadata['people'] = ', '.join(entities.get('people', [])[:5])  # 上位5名
            metadata['organizations'] = ', '.join(entities.get('organizations', [])[:5])
            metadata['dates'] = ', '.join(entities.get('dates', [])[:5])

            texts.append(text)
            metadatas.append(metadata)

        print(f"✅ Prepared {len(texts)} documents for vectorization")

        return texts, metadatas

    def build_index(self, texts: List[str], metadatas: List[Dict[str, Any]],
                   collection_name: str = "transcripts") -> None:
        """
        ベクトルインデックスを構築してChromaDBに保存

        Args:
            texts: ベクトル化するテキストのリスト
            metadatas: 各テキストに対応するメタデータのリスト
            collection_name: ChromaDBコレクション名
        """
        print(f"\n🔄 Building vector index...")
        print(f"   Collection: {collection_name}")
        print(f"   Documents: {len(texts)}")

        # 既存のコレクションを削除（クリーンスタート）
        try:
            self.client.delete_collection(name=collection_name)
            print(f"   Deleted existing collection: {collection_name}")
        except Exception:
            pass  # コレクションが存在しない場合は無視

        # 新しいコレクション作成
        collection = self.client.create_collection(
            name=collection_name,
            metadata={"description": "Voice memo transcription segments with embeddings"}
        )

        # バッチ処理でベクトル化と保存
        batch_size = 100
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            batch_ids = [f"seg_{meta['segment_id']}" for meta in batch_metadatas]

            # OpenAI Embeddings APIでベクトル化
            print(f"   Batch {i//batch_size + 1}/{total_batches}: Generating embeddings...")
            batch_embeddings = self.embeddings.embed_documents(batch_texts)

            # ChromaDBに保存
            collection.add(
                documents=batch_texts,
                embeddings=batch_embeddings,
                metadatas=batch_metadatas,
                ids=batch_ids
            )

        print(f"✅ Vector index built successfully")
        print(f"   Total documents: {collection.count()}")
        print(f"   Stored in: {self.chroma_path / collection_name}")

    def verify_index(self, collection_name: str = "transcripts") -> None:
        """インデックスの検証（サンプルクエリ実行）"""
        print(f"\n🔍 Verifying index...")

        collection = self.client.get_collection(name=collection_name)

        # サンプルクエリ
        test_query = "テスト"
        print(f"   Test query: '{test_query}'")

        query_embedding = self.embeddings.embed_query(test_query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )

        print(f"\n✅ Top 3 results:")
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
            print(f"\n   {i}. Text: {doc[:100]}...")
            print(f"      Segment ID: {metadata.get('segment_id')}")
            print(f"      Time: {metadata.get('start_time'):.2f}s - {metadata.get('end_time'):.2f}s")
            print(f"      Topics: {metadata.get('topics', 'N/A')}")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python build_vector_index.py <enhanced_json_path>")
        print("Example: python build_vector_index.py 'downloads/Test Recording_20min_enhanced.json'")
        sys.exit(1)

    json_path = sys.argv[1]

    if not os.path.exists(json_path):
        print(f"❌ Error: File not found: {json_path}")
        sys.exit(1)

    print("=" * 70)
    print("Phase 6-3 Stage 1: Vector Index Builder")
    print("=" * 70)

    # インデックスビルダー初期化
    builder = VectorIndexBuilder(chroma_path="chroma_db")

    # JSONファイル読み込み
    data = builder.load_enhanced_json(json_path)

    # ドキュメント準備
    texts, metadatas = builder.prepare_documents(data)

    # ベクトルインデックス構築
    file_name = Path(json_path).stem
    collection_name = f"transcripts_{file_name.replace(' ', '_').replace('(', '').replace(')', '')}"
    builder.build_index(texts, metadatas, collection_name=collection_name)

    # 検証
    builder.verify_index(collection_name=collection_name)

    print("\n" + "=" * 70)
    print("✅ Vector index building completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
