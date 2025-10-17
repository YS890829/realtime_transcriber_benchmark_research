#!/usr/bin/env python3
"""
Phase 6-3 Stage 2: RAG Q&A System
ChromaDBとGemini APIを使用したRAG (Retrieval Augmented Generation) Q&Aシステム

機能:
- 自然言語質問に対して、文字起こしデータを検索して回答生成
- 引用元セグメント情報（タイムスタンプ、トピック）を表示
- 複数ソースからのエビデンス統合
- 回答の信頼性と関連性を評価
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
import google.generativeai as genai

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


class RAGQASystem:
    """RAG Q&Aシステムクラス"""

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

        # Gemini LLM 初期化
        self.llm = genai.GenerativeModel("gemini-2.0-flash-exp")

        print(f"✅ RAG Q&A System initialized")
        print(f"   ChromaDB: {self.chroma_path}")
        print(f"   Embedding: text-embedding-004")
        print(f"   LLM: gemini-2.0-flash-exp")

    def retrieve_context(
        self,
        query: str,
        collection_name: str = "transcripts_unified",
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        質問に関連するコンテキストをChromaDBから検索（デフォルト: 統合コレクション）

        Args:
            query: ユーザーの質問
            collection_name: ChromaDBコレクション名（デフォルト: transcripts_unified）
            n_results: 検索する結果数

        Returns:
            関連セグメントのリスト
        """
        print(f"\n🔍 Retrieving context for: '{query}'")

        collection = self.client.get_collection(name=collection_name)

        # クエリをベクトル化して検索
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )
        query_embedding = result['embedding']

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        # 結果を整形
        contexts = []
        for doc, metadata, distance in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ):
            similarity_score = 1 / (1 + distance)

            context = {
                "text": doc,
                "metadata": metadata,
                "similarity_score": similarity_score,
                "distance": distance
            }
            contexts.append(context)

        print(f"   Retrieved {len(contexts)} relevant segments")

        return contexts

    def generate_answer(
        self,
        query: str,
        contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        検索したコンテキストを元にGemini APIで回答生成

        Args:
            query: ユーザーの質問
            contexts: 検索したコンテキストのリスト

        Returns:
            回答と引用情報
        """
        print(f"\n🤖 Generating answer with Gemini...")

        # コンテキストテキストを構築（統合コレクション対応）
        context_text = "\n\n---\n\n".join([
            f"[セグメント {i+1}] (ソース: {ctx['metadata'].get('source_file', 'N/A')})\n"
            f"話者: {ctx['metadata'].get('speaker', 'N/A')}\n"
            f"タイムスタンプ: {ctx['metadata'].get('timestamp', 'N/A')}\n"
            f"トピック: {ctx['metadata'].get('segment_topics', ctx['metadata'].get('global_topics', '不明'))}\n"
            f"内容: {ctx['text']}"
            for i, ctx in enumerate(contexts)
        ])

        # Gemini APIへのプロンプト
        prompt = f"""以下の文字起こしデータを参照して、ユーザーの質問に答えてください。

【重要な指示】
1. 必ず提供されたコンテキストに基づいて回答してください
2. コンテキストに情報がない場合は「提供された情報では回答できません」と明記してください
3. 回答には具体的なセグメント番号を引用してください（例: [セグメント 1]）
4. 回答は簡潔かつ正確に、日本語で記述してください
5. 複数のセグメントから情報を統合する場合は、すべての関連セグメントを引用してください

【文字起こしコンテキスト】
{context_text}

【質問】
{query}

【回答】
"""

        # Gemini APIで回答生成
        response = self.llm.generate_content(prompt)
        answer_text = response.text.strip()

        print(f"   Answer generated ({len(answer_text)} characters)")

        return {
            "query": query,
            "answer": answer_text,
            "contexts": contexts,
            "num_contexts_used": len(contexts)
        }

    def ask(
        self,
        query: str,
        collection_name: str = "transcripts_unified",
        n_contexts: int = 5
    ) -> Dict[str, Any]:
        """
        質問に回答する（メイン関数）（デフォルト: 統合コレクション）

        Args:
            query: ユーザーの質問
            collection_name: ChromaDBコレクション名（デフォルト: transcripts_unified）
            n_contexts: 使用するコンテキスト数

        Returns:
            回答と引用情報
        """
        # 1. コンテキスト検索
        contexts = self.retrieve_context(query, collection_name, n_contexts)

        # 2. 回答生成
        result = self.generate_answer(query, contexts)

        return result

    def display_answer(self, result: Dict[str, Any]) -> None:
        """回答を見やすく表示"""
        print(f"\n{'='*70}")
        print(f"❓ Question: {result['query']}")
        print(f"{'='*70}")

        print(f"\n💡 Answer:\n")
        print(result['answer'])

        print(f"\n{'─'*70}")
        print(f"📚 Sources ({result['num_contexts_used']} segments used):")
        print(f"{'─'*70}")

        for i, ctx in enumerate(result['contexts'], 1):
            meta = ctx['metadata']

            print(f"\n[セグメント {i}] (類似度: {ctx['similarity_score']:.4f})")

            # ソースファイル表示（統合コレクション対応）
            if meta.get('source_file'):
                print(f"📂 ソース: {meta['source_file']}")

            print(f"🗣️  話者: {meta.get('speaker', 'N/A')}")
            print(f"⏱️  タイムスタンプ: {meta.get('timestamp', 'N/A')}")

            if meta.get('segment_topics'):
                print(f"🏷️  トピック: {meta['segment_topics']}")

            if meta.get('people'):
                print(f"👥 人物: {meta['people']}")

            text = ctx['text']
            if len(text) > 150:
                text = text[:150] + "..."
            print(f"📝 内容: {text}")

    def batch_ask(
        self,
        questions: List[str],
        collection_name: str = "transcripts_unified",
        n_contexts: int = 5
    ) -> List[Dict[str, Any]]:
        """
        複数の質問に一括で回答（デフォルト: 統合コレクション）

        Args:
            questions: 質問のリスト
            collection_name: ChromaDBコレクション名（デフォルト: transcripts_unified）
            n_contexts: 使用するコンテキスト数

        Returns:
            回答結果のリスト
        """
        results = []

        for i, question in enumerate(questions, 1):
            print(f"\n{'='*70}")
            print(f"Question {i}/{len(questions)}")
            print(f"{'='*70}")

            result = self.ask(question, collection_name, n_contexts)
            self.display_answer(result)

            results.append(result)

        return results


def main():
    """メイン処理"""
    print("=" * 70)
    print("Phase 6-3 Stage 2: RAG Q&A System")
    print("=" * 70)

    # RAG Q&Aシステム初期化
    rag_system = RAGQASystem(chroma_path="chroma_db")

    # 利用可能なコレクション表示
    collections = [col.name for col in rag_system.client.list_collections()]
    print(f"\n📚 Available collections:")
    for i, col in enumerate(collections, 1):
        print(f"   {i}. {col}")

    if not collections:
        print("❌ No collections found. Please run build_vector_index.py first.")
        sys.exit(1)

    # コレクション選択
    if len(sys.argv) > 1:
        collection_name = sys.argv[1]
    else:
        collection_name = collections[0]

    print(f"\n✅ Using collection: {collection_name}")

    # サンプル質問
    sample_questions = [
        "この会話の主なトピックは何ですか？",
        "話者は就職活動についてどのように考えていますか？",
        "営業とAIについてどのような議論がありましたか？"
    ]

    # インタラクティブモードまたはサンプル質問モード
    if len(sys.argv) > 2 and sys.argv[2] == "--interactive":
        # インタラクティブモード
        print("\n" + "="*70)
        print("Interactive Q&A Mode (type 'exit' to quit)")
        print("="*70)

        while True:
            try:
                user_question = input("\n❓ Enter your question: ").strip()

                if user_question.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye!")
                    break

                if not user_question:
                    continue

                result = rag_system.ask(user_question, collection_name)
                rag_system.display_answer(result)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    else:
        # サンプル質問モード
        print("\n" + "="*70)
        print("Sample Questions Demo")
        print("="*70)

        results = rag_system.batch_ask(sample_questions, collection_name)

        print("\n" + "="*70)
        print(f"✅ Demo completed: {len(results)} questions answered")
        print("="*70)
        print("\nTip: Run with --interactive flag for interactive Q&A mode")


if __name__ == "__main__":
    main()
