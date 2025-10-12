#!/usr/bin/env python3
"""
Gemini APIの有料枠・無料枠を確認するテストスクリプト
レート制限をテストして現在のTierを判定します
"""

import os
import time
from dotenv import load_dotenv
import google.generativeai as genai

# 環境変数読み込み
load_dotenv()

# Gemini API Key選択（デフォルト: 無料枠）
USE_PAID_TIER = os.getenv("USE_PAID_TIER", "false").lower() == "true"
if USE_PAID_TIER:
    api_key = os.getenv("GEMINI_API_KEY_PAID")
    if not api_key:
        print("❌ GEMINI_API_KEY_PAID not set but USE_PAID_TIER=true")
        exit(1)
    tier_name = "PAID"
else:
    api_key = os.getenv("GEMINI_API_KEY_FREE")
    if not api_key:
        print("❌ GEMINI_API_KEY_FREE not set")
        exit(1)
    tier_name = "FREE"

# Gemini API設定
genai.configure(api_key=api_key)

print("=" * 60)
print(f"Gemini API Tier テスト ({tier_name} tier)")
print("=" * 60)
print()

# モデル情報取得
print("📋 利用可能なモデル一覧:")
for model in genai.list_models():
    if 'gemini' in model.name.lower():
        print(f"  - {model.name}")
print()

# レート制限テスト
print("🔄 レート制限テスト（Gemini 2.5 Pro）:")
print("   無料枠: 5 RPM (1リクエスト/12秒)")
print("   有料枠: より高いRPM")
print()

model = genai.GenerativeModel('gemini-2.0-flash-exp')

# 短時間に複数リクエスト送信
test_requests = 6  # 無料枠の制限（5 RPM）を超える数
success_count = 0
error_count = 0
start_time = time.time()

print(f"📊 {test_requests}回のリクエストを連続送信中...")
print()

for i in range(test_requests):
    try:
        response = model.generate_content(f"テスト{i+1}: 1+1は？", request_options={"timeout": 10})
        success_count += 1
        elapsed = time.time() - start_time
        print(f"  ✅ リクエスト {i+1}/{test_requests} 成功 (経過時間: {elapsed:.1f}秒)")

        # レート制限エラーを避けるため少し待機
        if i < test_requests - 1:
            time.sleep(1)

    except Exception as e:
        error_count += 1
        elapsed = time.time() - start_time
        error_msg = str(e)

        # レート制限エラーかチェック
        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            print(f"  ⚠️  リクエスト {i+1}/{test_requests} レート制限エラー (経過時間: {elapsed:.1f}秒)")
            print(f"      エラー: {error_msg[:100]}...")
        else:
            print(f"  ❌ リクエスト {i+1}/{test_requests} エラー (経過時間: {elapsed:.1f}秒)")
            print(f"      エラー: {error_msg[:100]}...")

total_time = time.time() - start_time

print()
print("=" * 60)
print("📊 テスト結果:")
print("=" * 60)
print(f"  成功: {success_count}/{test_requests}")
print(f"  エラー: {error_count}/{test_requests}")
print(f"  総実行時間: {total_time:.1f}秒")
print()

# 判定
if error_count == 0 and total_time < 60:
    print("✅ 判定: 有料枠の可能性が高い")
    print("   → 短時間（1分未満）で6回のリクエストが全て成功")
elif error_count > 0:
    print("⚠️  判定: 無料枠の可能性が高い")
    print("   → レート制限エラーが発生（5 RPM制限）")
else:
    print("❓ 判定: 不明")
    print("   → より多くのテストが必要")

print()
print("=" * 60)
print("💡 注意事項:")
print("   - 無料枠: 5 RPM（1分間に5リクエスト）、25 RPD（1日25リクエスト）")
print("   - 有料枠: Google Cloud Billingを有効化すると自動的に制限が緩和")
print("   - レート制限はプロジェクト単位で適用")
print("=" * 60)
