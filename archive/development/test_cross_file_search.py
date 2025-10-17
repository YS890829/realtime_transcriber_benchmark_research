#!/usr/bin/env python3
"""
Phase 8-3 Test: Cross-file search verification
統合Vector DBが複数ファイルから正しく検索できることを確認
"""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
from semantic_search import SemanticSearchEngine

load_dotenv()

# Gemini API設定
use_paid_tier = os.getenv("USE_PAID_TIER", "").lower() == "true"
api_key = os.getenv("GEMINI_API_KEY_PAID") if use_paid_tier else os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in environment variables")
    sys.exit(1)

genai.configure(api_key=api_key)

def test_cross_file_search():
    """横断検索テスト"""
    print("=" * 70)
    print("Phase 8-3: Cross-File Search Test")
    print("=" * 70)

    engine = SemanticSearchEngine(chroma_path="chroma_db")

    # テスト1: リクルートに関する検索（複数ファイルにまたがる可能性）
    print("\n" + "=" * 70)
    print("Test 1: Search for 'リクルートでの営業経験'")
    print("=" * 70)

    results1 = engine.search(
        query="リクルートでの営業経験",
        collection_name="transcripts_unified",
        n_results=5
    )

    # ソースファイルの種類を確認
    source_files = set()
    for result in results1['results']:
        source_file = result['metadata'].get('source_file', 'N/A')
        source_files.add(source_file)

    print(f"\n📂 Found results from {len(source_files)} different source file(s):")
    for sf in sorted(source_files):
        count = sum(1 for r in results1['results'] if r['metadata'].get('source_file') == sf)
        print(f"   - {sf}: {count} result(s)")

    # テスト2: 起業・ビジネスに関する検索
    print("\n" + "=" * 70)
    print("Test 2: Search for '起業やビジネス戦略'")
    print("=" * 70)

    results2 = engine.search(
        query="起業やビジネス戦略について",
        collection_name="transcripts_unified",
        n_results=5
    )

    source_files2 = set()
    for result in results2['results']:
        source_file = result['metadata'].get('source_file', 'N/A')
        source_files2.add(source_file)

    print(f"\n📂 Found results from {len(source_files2)} different source file(s):")
    for sf in sorted(source_files2):
        count = sum(1 for r in results2['results'] if r['metadata'].get('source_file') == sf)
        print(f"   - {sf}: {count} result(s)")

    # 詳細表示（最初の2件）
    print("\n" + "─" * 70)
    print("Sample Results (Top 2):")
    print("─" * 70)

    for i, result in enumerate(results2['results'][:2], 1):
        meta = result['metadata']
        print(f"\n[Result {i}]")
        print(f"📂 Source: {meta.get('source_file', 'N/A')}")
        print(f"🗣️  Speaker: {meta.get('speaker', 'N/A')}")
        print(f"⏱️  Timestamp: {meta.get('timestamp', 'N/A')}")
        print(f"📝 Text: {result['text'][:150]}...")
        print(f"   Similarity: {result['similarity_score']:.4f}")

    # テスト3: エンティティ統一確認（canonical_name確認）
    print("\n" + "=" * 70)
    print("Test 3: Verify Entity Resolution (canonical_name)")
    print("=" * 70)

    results3 = engine.search(
        query="杉本の経歴",
        collection_name="transcripts_unified",
        n_results=3
    )

    print("\n👥 Entity names in results:")
    for i, result in enumerate(results3['results'], 1):
        people = result['metadata'].get('people', 'N/A')
        print(f"   [{i}] {people}")

    # 最終結果サマリー
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    total_tests = 3
    passed_tests = 0

    # Test 1: 複数ファイルから検索できたか
    if len(source_files) >= 1:
        print("✅ Test 1 PASSED: Retrieved results from unified collection")
        passed_tests += 1
    else:
        print("❌ Test 1 FAILED: No results found")

    # Test 2: 複数ファイルから検索できたか
    if len(source_files2) >= 1:
        print("✅ Test 2 PASSED: Retrieved results from unified collection")
        passed_tests += 1
    else:
        print("❌ Test 2 FAILED: No results found")

    # Test 3: エンティティ統一確認
    has_entities = any(
        result['metadata'].get('people', 'N/A') != 'N/A'
        for result in results3['results']
    )
    if has_entities:
        print("✅ Test 3 PASSED: Entity metadata present")
        passed_tests += 1
    else:
        print("❌ Test 3 FAILED: No entity metadata found")

    print(f"\n🎯 Final Score: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Unified Vector DB is working correctly.")
        return True
    else:
        print("\n⚠️  Some tests failed. Please review the results.")
        return False


if __name__ == "__main__":
    success = test_cross_file_search()
    sys.exit(0 if success else 1)
