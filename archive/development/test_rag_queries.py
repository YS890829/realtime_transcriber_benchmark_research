#!/usr/bin/env python3
"""
Phase 8-4 Test: RAG Q&A System - Multiple Test Queries
複数のテストクエリでRAGシステムの動作確認
"""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
from rag_qa import RAGQASystem

load_dotenv()

# Gemini API設定
use_paid_tier = os.getenv("USE_PAID_TIER", "").lower() == "true"
api_key = os.getenv("GEMINI_API_KEY_PAID") if use_paid_tier else os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in environment variables")
    sys.exit(1)

genai.configure(api_key=api_key)


def main():
    """メイン処理"""
    print("=" * 70)
    print("Phase 8-4: RAG Q&A System - Multiple Test Queries")
    print("=" * 70)

    rag_system = RAGQASystem(chroma_path="chroma_db")

    # テスト質問リスト
    test_questions = [
        "この会話に登場する人物は誰ですか？",
        "リクルートについてどのような話がありましたか？",
        "起業やビジネスについてどのような議論がありましたか？",
        "AIや機械学習について言及している部分を教えてください。",
    ]

    results = []

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*70}")
        print(f"Question {i}/{len(test_questions)}")
        print(f"{'='*70}")

        try:
            result = rag_system.ask(
                query=question,
                collection_name="transcripts_unified",
                n_contexts=3
            )

            # 結果表示
            print(f"\n❓ Question: {result['query']}")
            print(f"\n💡 Answer:")
            print(f"   {result['answer']}")

            # コンテキストソースの表示
            source_files = set()
            for ctx in result['contexts']:
                source_file = ctx['metadata'].get('source_file', 'N/A')
                source_files.add(source_file)

            print(f"\n📚 Sources:")
            print(f"   Contexts used: {result['num_contexts_used']}")
            print(f"   Source files: {len(source_files)}")
            for sf in sorted(source_files):
                print(f"      - {sf}")

            # Top context詳細
            if result['contexts']:
                top_ctx = result['contexts'][0]
                print(f"\n   Top Context:")
                print(f"      Speaker: {top_ctx['metadata'].get('speaker', 'N/A')}")
                print(f"      Timestamp: {top_ctx['metadata'].get('timestamp', 'N/A')}")
                print(f"      Similarity: {top_ctx['similarity_score']:.4f}")

            results.append({
                "question": question,
                "success": True
            })

        except Exception as e:
            print(f"\n❌ Error: {e}")
            results.append({
                "question": question,
                "success": False
            })

    # 最終結果サマリー
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    successful_queries = sum(1 for r in results if r['success'])
    total_queries = len(results)

    print(f"\n🎯 Success Rate: {successful_queries}/{total_queries} queries answered")

    if successful_queries == total_queries:
        print("\n🎉 All queries completed successfully!")
        return True
    else:
        print(f"\n⚠️  {total_queries - successful_queries} query(ies) failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
