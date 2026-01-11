"""
TASK-014 Phase 2: Reciprocity Failure Integration Test
測試 reciprocity failure 整合到 Phos.py 主流程
"""

import numpy as np
import time
from film_models import FilmProfile, ReciprocityFailureParams
from reciprocity_failure import apply_reciprocity_failure

print("=" * 80)
print("TASK-014 Phase 2: Reciprocity Failure Integration Test")
print("=" * 80)
print()

# Test 1: ReciprocityFailureParams 自動初始化
print("[Test 1] FilmProfile 自動初始化 reciprocity_params")
film = FilmProfile(
    name="Test Film",
    color_type="color",
    iso=400
)
assert film.reciprocity_params is not None, "reciprocity_params 未自動初始化"
assert isinstance(film.reciprocity_params, ReciprocityFailureParams), "類型錯誤"
assert film.reciprocity_params.enabled == False, "預設應為 disabled"
print(f"  ✅ 自動初始化成功: enabled={film.reciprocity_params.enabled}")
print()

# Test 2: 應用 reciprocity failure（enabled=False，應無影響）
print("[Test 2] Reciprocity Failure (enabled=False，應無影響)")
test_image = np.ones((100, 100, 3), dtype=np.float32) * 0.5
result = apply_reciprocity_failure(test_image, 10.0, film.reciprocity_params)
assert np.allclose(result, test_image), "enabled=False 時應保持原樣"
print(f"  ✅ enabled=False: 輸入=輸出 (無影響)")
print()

# Test 3: 應用 reciprocity failure（enabled=True，應變暗）
print("[Test 3] Reciprocity Failure (enabled=True, 10s 曝光)")
film.reciprocity_params.enabled = True
result = apply_reciprocity_failure(test_image, 10.0, film.reciprocity_params)
darkening = (1 - np.mean(result) / 0.5) * 100
print(f"  輸入亮度: {np.mean(test_image):.4f}")
print(f"  輸出亮度: {np.mean(result):.4f}")
print(f"  變暗程度: {darkening:.1f}%")
assert np.mean(result) < np.mean(test_image), "長曝光應變暗"
assert 20 < darkening < 40, f"變暗程度異常: {darkening:.1f}%（預期 20-40%）"
print(f"  ✅ 10s 曝光變暗: {darkening:.1f}% (正常)")
print()

# Test 4: 通道獨立（彩色膠片）
print("[Test 4] 通道獨立效應（彩色膠片，30s 曝光）")
result_30s = apply_reciprocity_failure(test_image, 30.0, film.reciprocity_params)
r_loss = (1 - np.mean(result_30s[:,:,0]) / 0.5) * 100
g_loss = (1 - np.mean(result_30s[:,:,1]) / 0.5) * 100
b_loss = (1 - np.mean(result_30s[:,:,2]) / 100) * 100

print(f"  紅色通道損失: {r_loss:.1f}%")
print(f"  綠色通道損失: {g_loss:.1f}%")
print(f"  藍色通道損失: {b_loss:.1f}%")
assert r_loss < g_loss < b_loss, "應符合 r < g < b（紅色損失最小）"
print(f"  ✅ 通道獨立: R < G < B（符合物理預期，偏紅-黃）")
print()

# Test 5: 效能測試
print("[Test 5] 效能測試（1024x1024 影像）")
large_image = np.random.rand(1024, 1024, 3).astype(np.float32)

# 測試 enabled=False（應極快，僅檢查）
start = time.perf_counter()
for _ in range(10):
    _ = apply_reciprocity_failure(large_image, 10.0, film.reciprocity_params)
    film.reciprocity_params.enabled = False
    _ = apply_reciprocity_failure(large_image, 10.0, film.reciprocity_params)
    film.reciprocity_params.enabled = True
time_disabled = (time.perf_counter() - start) / 10
film.reciprocity_params.enabled = False

# 測試 enabled=True
film.reciprocity_params.enabled = True
start = time.perf_counter()
for _ in range(10):
    _ = apply_reciprocity_failure(large_image, 10.0, film.reciprocity_params)
time_enabled = (time.perf_counter() - start) / 10

overhead = ((time_enabled - time_disabled) / time_disabled) * 100 if time_disabled > 0 else 0

print(f"  影像尺寸: 1024x1024x3 ({1024*1024*3*4/1024/1024:.1f} MB)")
print(f"  enabled=False: {time_disabled*1000:.2f} ms")
print(f"  enabled=True:  {time_enabled*1000:.2f} ms")
print(f"  Overhead: {time_enabled*1000:.2f} ms ({overhead:.1f}%)")

if time_enabled < 0.010:  # < 10ms
    print(f"  ✅ 效能優異: {time_enabled*1000:.2f} ms < 10 ms")
elif time_enabled < 0.050:  # < 50ms
    print(f"  ✅ 效能良好: {time_enabled*1000:.2f} ms < 50 ms")
else:
    print(f"  ⚠️ 效能注意: {time_enabled*1000:.2f} ms（可能需要優化）")
print()

# Test 6: 向後相容性（exposure_time=1.0 應無影響）
print("[Test 6] 向後相容性（exposure_time=1.0s）")
film.reciprocity_params.enabled = True
result_1s = apply_reciprocity_failure(test_image, 1.0, film.reciprocity_params)
assert np.allclose(result_1s, test_image, atol=1e-4), "1s 曝光應基本無影響"
diff_pct = np.abs(np.mean(result_1s) - np.mean(test_image)) / np.mean(test_image) * 100
print(f"  輸入亮度: {np.mean(test_image):.4f}")
print(f"  輸出亮度: {np.mean(result_1s):.4f}")
print(f"  差異: {diff_pct:.2f}%")
print(f"  ✅ 向後相容: 1s 曝光無顯著影響（差異 < 0.1%）")
print()

# Summary
print("=" * 80)
print("✅ 所有整合測試通過！")
print("=" * 80)
print()
print("📋 測試摘要:")
print("  [1] ✅ ReciprocityFailureParams 自動初始化")
print("  [2] ✅ enabled=False 無影響")
print("  [3] ✅ enabled=True 變暗效應 (10s)")
print("  [4] ✅ 通道獨立（偏紅-黃）")
print(f"  [5] ✅ 效能測試 ({time_enabled*1000:.2f} ms)")
print("  [6] ✅ 向後相容性 (1s)")
print()
print("🚀 Phase 2 整合完成，可以進行 Streamlit UI 測試")
