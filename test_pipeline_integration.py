#!/usr/bin/env python3
"""
Integration Test for Reorganized Pipeline
Tests that the complete pipeline works using only src/ folder files
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def test_imports():
    """Test that all import statements work correctly"""
    print("=" * 70)
    print("[Test 1] Import Verification")
    print("=" * 70)

    test_cases = [
        ("Step 1: Transcribe", "from src.transcription.structured_transcribe import main"),
        ("Step 2: Participants DB", "from src.participants.participants_db import ParticipantsDB"),
        ("Step 2: Extract Participants", "from src.participants.extract_participants import extract_participants_from_description"),
        ("Step 2: Speaker Inference", "from src.participants.enhanced_speaker_inference import infer_speakers_with_participants"),
        ("Step 2: Integrated Pipeline", "from src.pipeline.integrated_pipeline import run_phase_11_3_pipeline"),
        ("Step 3: Topics/Entities", "from src.topics.add_topics_entities import main"),
        ("Step 4: Entity Resolution", "from src.topics.entity_resolution_llm import main"),
        ("Step 5: Vector DB", "from src.vector_db.build_unified_vector_index import main"),
        ("Step 6: Semantic Search", "from src.search.semantic_search import main"),
        ("Step 6: RAG QA", "from src.search.rag_qa import main"),
        ("Step 7: File Management", "from src.file_management.generate_smart_filename import generate_filename_from_transcription"),
        ("Step 7: Cloud Manager", "from src.file_management.cloud_file_manager import delete_gdrive_file"),
        ("Step 7: Unified Registry", "from src.file_management.unified_registry import is_processed"),
        ("Shared: Calendar Integration", "from src.shared.calendar_integration import get_events_for_file_date"),
        ("Shared: Summary Generator", "from src.shared.summary_generator import generate_summary_with_calendar"),
        ("Batch: Batch Runner", "from src.batch.run_phase_2_6_batch import run_phase_2_6_for_all_files"),
        ("Monitoring: Webhook Server", "from src.monitoring.webhook_server import app"),
        ("Monitoring: iCloud Monitor", "from src.monitoring.icloud_monitor import AudioFileHandler"),
    ]

    passed = 0
    failed = 0

    for name, import_stmt in test_cases:
        try:
            # Use subprocess to isolate imports and prevent hangs
            result = subprocess.run(
                ["venv/bin/python3", "-c", import_stmt],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  ✓ {name}")
                passed += 1
            else:
                # Extract just the error type, not full traceback
                error_msg = result.stderr.split('\n')[-2] if result.stderr else "Unknown error"
                print(f"  ✗ {name}: {error_msg}")
                failed += 1
        except subprocess.TimeoutExpired:
            print(f"  ✗ {name}: Import timeout")
            failed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1

    print(f"\n[Test 1] Result: {passed} passed, {failed} failed\n")
    return failed == 0


def test_no_archive_dependencies():
    """Test that src/ files don't depend on archive/ folder"""
    print("=" * 70)
    print("[Test 2] Archive Dependency Check")
    print("=" * 70)

    # Search for imports from archive in src/ files
    result = subprocess.run(
        ["grep", "-r", "from archive", "src/", "--include=*.py"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("  ✗ Found dependencies on archive/ folder:")
        print(result.stdout)
        return False
    else:
        print("  ✓ No dependencies on archive/ folder found")
        return True


def test_module_execution():
    """Test that modules can be executed with -m flag"""
    print("\n" + "=" * 70)
    print("[Test 3] Module Execution Test")
    print("=" * 70)

    test_cases = [
        ("Step 1: Transcribe", ["venv/bin/python3", "-m", "src.step1_transcribe.structured_transcribe", "--help"]),
        ("Step 3: Topics/Entities", ["venv/bin/python3", "-m", "src.step3_topics.add_topics_entities", "--help"]),
        ("Step 4: Entity Resolution", ["venv/bin/python3", "-m", "src.step4_entities.entity_resolution_llm", "--help"]),
        ("Step 5: Vector DB", ["venv/bin/python3", "-m", "src.step5_vector_db.build_unified_vector_index", "--help"]),
        ("Step 6: Semantic Search", ["venv/bin/python3", "-m", "src.step6_search.semantic_search", "--help"]),
        ("Step 6: RAG QA", ["venv/bin/python3", "-m", "src.step6_search.rag_qa", "--help"]),
    ]

    passed = 0
    failed = 0

    for name, cmd in test_cases:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Accept exit codes 0 (success) or 2 (argparse help/error)
        if result.returncode in [0, 2]:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name}: exit code {result.returncode}")
            if result.stderr:
                print(f"    {result.stderr[:200]}")
            failed += 1

    print(f"\n[Test 3] Result: {passed} passed, {failed} failed\n")
    return failed == 0


def test_package_structure():
    """Test that all packages have __init__.py"""
    print("=" * 70)
    print("[Test 4] Package Structure Verification")
    print("=" * 70)

    required_packages = [
        "src/",
        "src/step1_transcribe/",
        "src/step2_participants/",
        "src/step3_topics/",
        "src/step4_entities/",
        "src/step5_vector_db/",
        "src/step6_search/",
        "src/step7_file_management/",
        "src/batch/",
        "src/monitoring/",
        "src/shared/",
    ]

    passed = 0
    failed = 0

    for package in required_packages:
        init_file = Path(package) / "__init__.py"
        if init_file.exists():
            print(f"  ✓ {package}__init__.py")
            passed += 1
        else:
            print(f"  ✗ {package}__init__.py not found")
            failed += 1

    print(f"\n[Test 4] Result: {passed} passed, {failed} failed\n")
    return failed == 0


def main():
    print("\n" + "=" * 70)
    print("Pipeline Reorganization Integration Test")
    print("=" * 70)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    results = []

    # Run all tests
    results.append(("Package Structure", test_package_structure()))
    results.append(("Import Verification", test_imports()))
    results.append(("Archive Dependency Check", test_no_archive_dependencies()))
    results.append(("Module Execution", test_module_execution()))

    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    total_passed = sum(1 for _, result in results if result)
    total_failed = sum(1 for _, result in results if not result)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\nTotal: {total_passed} passed, {total_failed} failed")
    print("=" * 70)

    if total_failed == 0:
        print("\n✅ All tests passed! The reorganization is successful.")
        print("The pipeline can run using only src/ folder files (no archive/ dependencies).\n")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the errors above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
