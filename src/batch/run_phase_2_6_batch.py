#!/usr/bin/env python3
"""
Phase 11-3: Phase 2-6 バッチ処理スクリプト
作成日: 2025-10-16

Phase 2: 話者推論（enhanced_speaker_inference.py）※ Phase 11-3で実行済み
Phase 3: トピック/エンティティ抽出（add_topics_entities.py）
Phase 4: エンティティ解決（entity_resolution_llm.py）
Phase 5: Vector DB構築（build_unified_vector_index.py）
Phase 6: RAG検証（当面スキップ）
"""

import os
import glob
import subprocess
import sys
from datetime import datetime


def run_phase_2_6_for_all_files(downloads_dir: str = "downloads"):
    """
    全ての構造化JSONファイルに対してPhase 3-6を実行

    Phase 2（話者推論）はPhase 11-3のintegrated_pipeline.pyで既に実行済みなので、
    ここではPhase 3-6のみを実行します。

    Args:
        downloads_dir: 構造化JSONファイルが格納されているディレクトリ
    """
    print(f"\n{'='*70}")
    print(f"[Batch] Phase 2-6 バッチ処理開始")
    print(f"{'='*70}\n")
    print(f"対象ディレクトリ: {downloads_dir}")

    # 構造化JSONファイルを取得
    structured_files = glob.glob(os.path.join(downloads_dir, "*_structured.json"))
    print(f"対象ファイル数: {len(structured_files)}\n")

    if not structured_files:
        print("[Batch] 処理対象ファイルが見つかりません")
        return

    # ========================
    # Phase 2: 話者推論（スキップ）
    # ========================
    print(f"{'='*70}")
    print(f"[Phase 2] 話者推論")
    print(f"{'='*70}")
    print("⏭ スキップ（Phase 11-3 integrated_pipeline.py で既に実行済み）\n")

    # ========================
    # Phase 3: トピック/エンティティ抽出
    # ========================
    print(f"{'='*70}")
    print(f"[Phase 3] トピック/エンティティ抽出")
    print(f"{'='*70}")
    print("実行中...\n")

    success_count = 0
    error_count = 0

    for i, file_path in enumerate(structured_files, 1):
        file_name = os.path.basename(file_path)
        print(f"[{i}/{len(structured_files)}] {file_name}")

        try:
            result = subprocess.run(
                ["venv/bin/python3", "-m", "src.step3_topics.add_topics_entities", file_path],
                capture_output=True,
                text=True,
                timeout=300  # 5分タイムアウト
            )

            if result.returncode == 0:
                print(f"  ✓ 成功")
                success_count += 1
            else:
                print(f"  ✗ エラー（exit code: {result.returncode}）")
                if result.stderr:
                    print(f"    stderr: {result.stderr[:200]}")
                error_count += 1

        except subprocess.TimeoutExpired:
            print(f"  ✗ タイムアウト（5分経過）")
            error_count += 1
        except Exception as e:
            print(f"  ✗ 例外: {e}")
            error_count += 1

    print(f"\n[Phase 3] 完了: 成功 {success_count}件、エラー {error_count}件\n")

    # ========================
    # Phase 4: エンティティ解決
    # ========================
    print(f"{'='*70}")
    print(f"[Phase 4] エンティティ解決")
    print(f"{'='*70}")
    print("実行中...\n")

    # Phase 3で生成された _enhanced.json ファイルを取得
    enhanced_files = glob.glob(os.path.join(downloads_dir, "*_structured_enhanced.json"))
    if not enhanced_files:
        print("  ⚠ 処理対象ファイルが見つかりません（_structured_enhanced.json）")
        print(f"\n[Phase 4] 完了\n")
    else:
        print(f"  対象ファイル数: {len(enhanced_files)}")

        try:
            # entity_resolution_llm.py は個別JSONファイルを引数として受け取る
            result = subprocess.run(
                ["venv/bin/python3", "-m", "src.step4_entities.entity_resolution_llm"] + enhanced_files,
                capture_output=True,
                text=True,
                timeout=600  # 10分タイムアウト
            )

            if result.returncode == 0:
                print(f"  ✓ 成功")
                # 出力の最後の20行を表示
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[-20:]:
                        print(f"    {line}")
            else:
                print(f"  ✗ エラー（exit code: {result.returncode}）")
                if result.stderr:
                    print(f"    stderr: {result.stderr[:500]}")

        except subprocess.TimeoutExpired:
            print(f"  ✗ タイムアウト（10分経過）")
        except Exception as e:
            print(f"  ✗ 例外: {e}")

        print(f"\n[Phase 4] 完了\n")

    # ========================
    # Phase 5: Vector DB構築
    # ========================
    print(f"{'='*70}")
    print(f"[Phase 5] Vector DB構築")
    print(f"{'='*70}")
    print("実行中...\n")

    # Phase 4で処理済みの _enhanced.json ファイルを取得
    enhanced_files = glob.glob(os.path.join(downloads_dir, "*_structured_enhanced.json"))
    if not enhanced_files:
        print("  ⚠ 処理対象ファイルが見つかりません（_structured_enhanced.json）")
        print(f"\n[Phase 5] 完了\n")
    else:
        print(f"  対象ファイル数: {len(enhanced_files)}")

        try:
            # build_unified_vector_index.py は個別JSONファイルを引数として受け取る
            result = subprocess.run(
                ["venv/bin/python3", "-m", "src.step5_vector_db.build_unified_vector_index"] + enhanced_files,
                capture_output=True,
                text=True,
                timeout=900  # 15分タイムアウト
            )

            if result.returncode == 0:
                print(f"  ✓ 成功")
                # 出力の最後の30行を表示
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[-30:]:
                        print(f"    {line}")
            else:
                print(f"  ✗ エラー（exit code: {result.returncode}）")
                if result.stderr:
                    print(f"    stderr: {result.stderr[:500]}")

        except subprocess.TimeoutExpired:
            print(f"  ✗ タイムアウト（15分経過）")
        except Exception as e:
            print(f"  ✗ 例外: {e}")

        print(f"\n[Phase 5] 完了\n")

    # ========================
    # Phase 6: RAG検証（スキップ）
    # ========================
    print(f"{'='*70}")
    print(f"[Phase 6] RAG検証")
    print(f"{'='*70}")
    print("⏭ スキップ（学習データ蓄積待ち、Phase 5のVector DBは継続構築）\n")

    # ========================
    # 完了
    # ========================
    print(f"{'='*70}")
    print(f"[Batch] Phase 2-6 バッチ処理完了")
    print(f"{'='*70}\n")
    print(f"処理時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"対象ファイル数: {len(structured_files)}")
    print(f"Phase 3 成功: {success_count}件、エラー: {error_count}件")


if __name__ == "__main__":
    downloads_dir = sys.argv[1] if len(sys.argv) > 1 else "downloads"

    if not os.path.exists(downloads_dir):
        print(f"エラー: ディレクトリが見つかりません: {downloads_dir}")
        sys.exit(1)

    try:
        run_phase_2_6_for_all_files(downloads_dir)
        print("\n✅ バッチ処理完了")
    except KeyboardInterrupt:
        print("\n\n⚠️  ユーザーによる中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ バッチ処理エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
