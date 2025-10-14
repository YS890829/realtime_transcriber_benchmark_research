#!/usr/bin/env python3
"""
Phase 8-3: Unified Vector Index Builder
全5ファイルを1つのコレクション"transcripts_unified"に統合

機能:
- 5ファイルの_enhanced.jsonを統合
- 統一されたentity_idでベクトル化
- メタデータにsource_file追加
- 1クエリで5ファイル横断検索
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
from chromadb.config import Settings

# 環境変数の読み込み
load_dotenv()

# Gemini APIキー選択（FREE/PAID tier）
use_paid_tier = os.getenv("USE_PAID_TIER", "").lower() == "true"
api_key = os.getenv("GEMINI_API_KEY_PAID") if use_paid_tier else os.getenv("GEMINI_API_KEY_FREE")

if not api_key:
    print("❌ Error: GEMINI_API_KEY_FREE or GEMINI_API_KEY_PAID not found in environment variables")
    sys.exit(1)

genai.configure(api_key=api_key)
print(f"✅ Using Gemini API: {'PAID' if use_paid_tier else 'FREE'} tier")


class UnifiedVectorIndexBuilder:
    """統合ベクトルインデックス構築クラス"""

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

        print(f"✅ ChromaDB initialized at: {self.chroma_path}")
        print(f"✅ Using Gemini model: text-embedding-004")

    def load_enhanced_json(self, json_path: str) -> Dict[str, Any]:
        """enhanced JSONファイルを読み込み"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        file_name = Path(json_path).stem
        print(f"✅ Loaded: {file_name}")
        print(f"   Segments: {len(data.get('segments', []))}")
        print(f"   Topics: {len(data.get('topics', []))}")

        # エンティティ統計
        entities = data.get('entities', {})
        people_count = len(entities.get('people', []))
        org_count = len(entities.get('organizations', []))
        print(f"   Entities: People={people_count}, Orgs={org_count}")

        return data

    def prepare_unified_documents(self, json_files: List[str]) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        複数のJSONファイルから統合ドキュメントとメタデータを準備

        Returns:
            texts: ベクトル化するテキストのリスト
            metadatas: 各テキストに対応するメタデータのリスト
            ids: 各ドキュメントのユニークID
        """
        all_texts = []
        all_metadatas = []
        all_ids = []

        print(f"\n🔄 Preparing documents from {len(json_files)} files...")

        for json_file in json_files:
            data = self.load_enhanced_json(json_file)

            segments = data.get('segments', [])
            topics = data.get('topics', [])
            entities = data.get('entities', {})
            file_metadata = data.get('metadata', {})

            # ソースファイル名（元の音声ファイル名）
            source_file = file_metadata.get('file', {}).get('file_name', Path(json_file).stem)

            # トピックIDからトピック名へのマッピング
            topic_map = {topic['id']: topic['name'] for topic in topics}

            for segment in segments:
                text = segment.get('text', '').strip()
                if not text:
                    continue

                # セグメントID（ファイル横断でユニーク）
                segment_id = segment.get('id')
                file_prefix = Path(json_file).stem.replace('_structured_enhanced', '')[:20]
                unique_id = f"{file_prefix}_seg_{segment_id}"

                # メタデータ作成
                metadata = {
                    'segment_id': str(segment_id),
                    'source_file': source_file,
                    'speaker': segment.get('speaker', 'Unknown'),
                    'timestamp': segment.get('timestamp', '00:00'),
                }

                # セグメントトピック
                segment_topics = segment.get('topics', [])
                if segment_topics:
                    topic_names = [topic_map.get(tid, tid) for tid in segment_topics]
                    metadata['segment_topics'] = ', '.join(topic_names)
                else:
                    metadata['segment_topics'] = ''

                # グローバルトピック（全体のトピック）
                if topics:
                    global_topic_names = [t['name'] for t in topics[:3]]
                    metadata['global_topics'] = ', '.join(global_topic_names)
                else:
                    metadata['global_topics'] = ''

                # エンティティ情報（canonical_name + entity_id使用）
                people_list = []
                for person in entities.get('people', []):
                    if isinstance(person, dict):
                        canonical = person.get('canonical_name', person.get('name', ''))
                        entity_id = person.get('entity_id', '')
                        if canonical and entity_id:
                            people_list.append(f"{canonical}({entity_id})")
                    elif isinstance(person, str):
                        people_list.append(person)

                metadata['people'] = ', '.join(people_list[:5])  # 上位5名

                org_list = []
                for org in entities.get('organizations', []):
                    if isinstance(org, dict):
                        canonical = org.get('canonical_name', org.get('name', ''))
                        entity_id = org.get('entity_id', '')
                        if canonical and entity_id:
                            org_list.append(f"{canonical}({entity_id})")
                    elif isinstance(org, str):
                        org_list.append(org)

                metadata['organizations'] = ', '.join(org_list[:5])  # 上位5組織

                all_texts.append(text)
                all_metadatas.append(metadata)
                all_ids.append(unique_id)

        print(f"✅ Prepared {len(all_texts)} documents from {len(json_files)} files")

        return all_texts, all_metadatas, all_ids

    def build_unified_index(self, texts: List[str], metadatas: List[Dict[str, Any]],
                           ids: List[str], collection_name: str = "transcripts_unified") -> None:
        """
        統合ベクトルインデックスを構築してChromaDBに保存

        Args:
            texts: ベクトル化するテキストのリスト
            metadatas: 各テキストに対応するメタデータのリスト
            ids: 各ドキュメントのユニークID
            collection_name: ChromaDBコレクション名
        """
        print(f"\n🔄 Building unified vector index...")
        print(f"   Collection: {collection_name}")
        print(f"   Total documents: {len(texts)}")

        # 既存のコレクションを削除（クリーンスタート）
        try:
            self.client.delete_collection(name=collection_name)
            print(f"   Deleted existing collection: {collection_name}")
        except Exception:
            pass

        # 新しいコレクション作成
        collection = self.client.create_collection(
            name=collection_name,
            metadata={"description": "Unified transcription segments across all files"}
        )

        # バッチ処理でベクトル化と保存
        # Gemini batch embedding: 最大100テキスト/リクエスト
        batch_size = 100
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            print(f"   Batch {i//batch_size + 1}/{total_batches}: Generating embeddings for {len(batch_texts)} docs...")

            # Gemini Embeddings APIでバッチベクトル化
            try:
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=batch_texts,  # リスト全体を渡す
                    task_type="retrieval_document"
                )

                # 結果の取得: result['embedding'] = [[[emb1]], [[emb2]], ...] の形式
                # 最初の次元を取り除く: [[[emb]]] -> [[emb]] -> [emb]
                embeddings_data = result['embedding']
                batch_embeddings = [emb[0] if isinstance(emb, list) and isinstance(emb[0], list) else emb
                                   for emb in embeddings_data]

                print(f"      ✓ Generated {len(batch_embeddings)} embeddings")

            except Exception as e:
                print(f"\n   ⚠️  Batch embedding failed: {e}")
                print(f"   Falling back to individual calls...")
                # フォールバック: 個別にベクトル化
                batch_embeddings = []
                for j, text in enumerate(batch_texts, 1):
                    try:
                        result = genai.embed_content(
                            model="models/text-embedding-004",
                            content=text,
                            task_type="retrieval_document"
                        )
                        batch_embeddings.append(result['embedding'])
                        if j % 10 == 0:
                            print(f"      Progress: {j}/{len(batch_texts)}", end='\r')
                    except Exception as e2:
                        print(f"\n      Error on doc {j}: {e2}")
                        batch_embeddings.append([0.0] * 768)
                print(f"      Progress: {len(batch_texts)}/{len(batch_texts)} ✓")

            # ChromaDBに保存
            collection.add(
                documents=batch_texts,
                embeddings=batch_embeddings,
                metadatas=batch_metadatas,
                ids=batch_ids
            )

            print(f"   ✅ Batch {i//batch_size + 1}/{total_batches} completed")

            # Rate limit対策（FREE tier: 1500 requests/day = 約1.04 req/min）
            # 安全のため2秒待機
            if i + batch_size < len(texts):
                time.sleep(2)

        print(f"✅ Unified vector index built successfully")
        print(f"   Total documents: {collection.count()}")
        print(f"   Collection: {collection_name}")

    def verify_unified_index(self, collection_name: str = "transcripts_unified") -> None:
        """統合インデックスの検証（サンプルクエリ実行）"""
        print(f"\n🔍 Verifying unified index...")

        collection = self.client.get_collection(name=collection_name)

        # サンプルクエリ
        test_query = "起業"
        print(f"   Test query: '{test_query}'")

        result = genai.embed_content(
            model="models/text-embedding-004",
            content=test_query,
            task_type="retrieval_query"
        )
        query_embedding = result['embedding']

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )

        print(f"\n✅ Top 3 results from unified index:")
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
            print(f"\n   {i}. {doc[:100]}...")
            print(f"      Source: {metadata.get('source_file', 'N/A')}")
            print(f"      Speaker: {metadata.get('speaker', 'N/A')}")
            print(f"      Timestamp: {metadata.get('timestamp', 'N/A')}")
            print(f"      Topics: {metadata.get('segment_topics', 'N/A')}")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python build_unified_vector_index.py <enhanced_json1> <enhanced_json2> ...")
        print("Example: python build_unified_vector_index.py downloads/*_enhanced.json")
        sys.exit(1)

    json_files = sys.argv[1:]

    print("=" * 70)
    print("Phase 8-3: Unified Vector Index Builder")
    print("=" * 70)

    # インデックスビルダー初期化
    builder = UnifiedVectorIndexBuilder(chroma_path="chroma_db")

    # 統合ドキュメント準備
    texts, metadatas, ids = builder.prepare_unified_documents(json_files)

    # 統合ベクトルインデックス構築
    builder.build_unified_index(texts, metadatas, ids, collection_name="transcripts_unified")

    # 検証
    builder.verify_unified_index(collection_name="transcripts_unified")

    print("\n" + "=" * 70)
    print("✅ Unified vector index building completed!")
    print(f"   Total files: {len(json_files)}")
    print(f"   Total documents: {len(texts)}")
    print(f"   Collection: transcripts_unified")
    print("=" * 70)


if __name__ == "__main__":
    main()
