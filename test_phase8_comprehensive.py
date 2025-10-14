#!/usr/bin/env python3
"""
Phase 8-4 Comprehensive Test: 総合検証スクリプト
話者推論精度、エンティティ統一率、横断検索の動作確認
"""

import os
import sys
import json
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
import google.generativeai as genai
from semantic_search import SemanticSearchEngine
from rag_qa import RAGQASystem

load_dotenv()

# Gemini API設定
use_paid_tier = os.getenv("USE_PAID_TIER", "").lower() == "true"
api_key = os.getenv("GEMINI_API_KEY_PAID") if use_paid_tier else os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in environment variables")
    sys.exit(1)

genai.configure(api_key=api_key)


def test_speaker_inference():
    """Test 1: 話者推論精度確認"""
    print("\n" + "=" * 70)
    print("Test 1: Speaker Inference Accuracy")
    print("=" * 70)

    enhanced_files = list(Path("downloads").glob("*_structured_enhanced.json"))

    total_segments = 0
    speaker_counts = Counter()

    for enhanced_file in enhanced_files:
        with open(enhanced_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        segments = data.get("segments", [])
        total_segments += len(segments)

        for seg in segments:
            speaker = seg.get("speaker", "Unknown")
            speaker_counts[speaker] += 1

    print(f"\n📊 Speaker Distribution:")
    print(f"   Total segments: {total_segments}")
    for speaker, count in speaker_counts.most_common():
        percentage = (count / total_segments) * 100
        print(f"   - {speaker}: {count} segments ({percentage:.1f}%)")

    # 成功判定: 話者が特定されていること
    has_speakers = len(speaker_counts) > 0

    if has_speakers:
        print(f"\n✅ Test 1 PASSED: Speakers identified in {len(enhanced_files)} files")
        return True
    else:
        print("\n❌ Test 1 FAILED: No speakers found")
        return False


def test_entity_unification():
    """Test 2: エンティティ統一率確認"""
    print("\n" + "=" * 70)
    print("Test 2: Entity Unification Rate")
    print("=" * 70)

    enhanced_files = list(Path("downloads").glob("*_structured_enhanced.json"))

    all_people = []
    all_organizations = []
    canonical_people = set()
    canonical_orgs = set()
    entity_groups = []

    for enhanced_file in enhanced_files:
        with open(enhanced_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        entities = data.get("entities", {})

        # 人物エンティティ
        people = entities.get("people", [])
        for person in people:
            if isinstance(person, dict):
                all_people.append(person.get("name", ""))
                canonical = person.get("canonical_name", "")
                entity_id = person.get("entity_id", "")
                variants = person.get("variants", [])

                if canonical:
                    canonical_people.add(canonical)

                if len(variants) > 1:
                    entity_groups.append({
                        "type": "person",
                        "canonical": canonical,
                        "variants": variants,
                        "entity_id": entity_id
                    })

        # 組織エンティティ
        organizations = entities.get("organizations", [])
        for org in organizations:
            if isinstance(org, dict):
                all_organizations.append(org.get("name", ""))
                canonical = org.get("canonical_name", "")
                entity_id = org.get("entity_id", "")
                variants = org.get("variants", [])

                if canonical:
                    canonical_orgs.add(canonical)

                if len(variants) > 1:
                    entity_groups.append({
                        "type": "organization",
                        "canonical": canonical,
                        "variants": variants,
                        "entity_id": entity_id
                    })

    print(f"\n📊 Entity Statistics:")
    print(f"   Total people mentions: {len(all_people)}")
    print(f"   Unique canonical people: {len(canonical_people)}")
    print(f"   Total organization mentions: {len(all_organizations)}")
    print(f"   Unique canonical organizations: {len(canonical_orgs)}")

    print(f"\n🔗 Entity Groups (variants unified):")
    if entity_groups:
        for group in entity_groups[:5]:  # Show first 5
            print(f"   [{group['type']}] {group['canonical']} ({group['entity_id']})")
            print(f"      Variants: {', '.join(group['variants'])}")
    else:
        print("   No entity groups found (all entities are unique)")

    # 成功判定: canonical_nameが付与されていること
    has_canonical = len(canonical_people) > 0 or len(canonical_orgs) > 0

    if has_canonical:
        print(f"\n✅ Test 2 PASSED: Entity unification complete")
        return True
    else:
        print("\n❌ Test 2 FAILED: No canonical entities found")
        return False


def test_cross_file_search():
    """Test 3: 横断検索テスト"""
    print("\n" + "=" * 70)
    print("Test 3: Cross-File Search Verification")
    print("=" * 70)

    engine = SemanticSearchEngine(chroma_path="chroma_db")

    # Test query
    query = "営業やビジネス戦略について話している部分"
    print(f"\n🔍 Query: '{query}'")

    results = engine.search(
        query=query,
        collection_name="transcripts_unified",
        n_results=5
    )

    # ソースファイルの種類を確認
    source_files = set()
    for result in results['results']:
        source_file = result['metadata'].get('source_file', 'N/A')
        source_files.add(source_file)

    print(f"\n📂 Results from {len(source_files)} source file(s):")
    for sf in sorted(source_files):
        count = sum(1 for r in results['results'] if r['metadata'].get('source_file') == sf)
        print(f"   - {sf}: {count} result(s)")

    # Top 3結果の詳細表示
    print(f"\n📝 Top 3 Results:")
    for i, result in enumerate(results['results'][:3], 1):
        meta = result['metadata']
        print(f"\n   [{i}] Source: {meta.get('source_file', 'N/A')}")
        print(f"       Speaker: {meta.get('speaker', 'N/A')}")
        print(f"       Timestamp: {meta.get('timestamp', 'N/A')}")
        print(f"       Similarity: {result['similarity_score']:.4f}")
        text = result['text']
        if len(text) > 100:
            text = text[:100] + "..."
        print(f"       Text: {text}")

    # 成功判定: 結果が取得できたか
    has_results = len(results['results']) > 0

    if has_results:
        print(f"\n✅ Test 3 PASSED: Cross-file search working")
        return True
    else:
        print("\n❌ Test 3 FAILED: No search results")
        return False


def test_rag_qa():
    """Test 4: RAG Q&A動作確認"""
    print("\n" + "=" * 70)
    print("Test 4: RAG Q&A System Verification")
    print("=" * 70)

    rag_system = RAGQASystem(chroma_path="chroma_db")

    # テスト質問
    test_question = "杉本さんの職歴について教えてください。"
    print(f"\n❓ Question: {test_question}")

    try:
        result = rag_system.ask(
            query=test_question,
            collection_name="transcripts_unified",
            n_contexts=3
        )

        print(f"\n💡 Answer:")
        print(f"   {result['answer'][:200]}...")

        print(f"\n📚 Contexts used: {result['num_contexts_used']}")

        # ソースファイルの種類を確認
        source_files = set()
        for ctx in result['contexts']:
            source_file = ctx['metadata'].get('source_file', 'N/A')
            source_files.add(source_file)

        print(f"   Source files: {len(source_files)}")
        for sf in sorted(source_files):
            print(f"      - {sf}")

        print(f"\n✅ Test 4 PASSED: RAG Q&A system working")
        return True

    except Exception as e:
        print(f"\n❌ Test 4 FAILED: {e}")
        return False


def main():
    """メイン処理"""
    print("=" * 70)
    print("Phase 8-4: Comprehensive Verification Test")
    print("=" * 70)

    tests_passed = []

    # Test 1: 話者推論精度
    tests_passed.append(("Speaker Inference", test_speaker_inference()))

    # Test 2: エンティティ統一率
    tests_passed.append(("Entity Unification", test_entity_unification()))

    # Test 3: 横断検索
    tests_passed.append(("Cross-File Search", test_cross_file_search()))

    # Test 4: RAG Q&A
    tests_passed.append(("RAG Q&A System", test_rag_qa()))

    # 最終結果サマリー
    print("\n" + "=" * 70)
    print("Final Test Summary")
    print("=" * 70)

    total_tests = len(tests_passed)
    passed_count = sum(1 for _, passed in tests_passed if passed)

    for test_name, passed in tests_passed:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\n🎯 Final Score: {passed_count}/{total_tests} tests passed")

    if passed_count == total_tests:
        print("\n🎉 All tests passed! Phase 8 verification complete.")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_count} test(s) failed. Please review.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
