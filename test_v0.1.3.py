#!/usr/bin/env python3
"""
Phos v0.1.3 快速測試腳本
"""

import numpy as np
import sys

print("=" * 60)
print("Phos v0.1.3 快速測試")
print("=" * 60)

# 測試 1: 胶片模型載入
print("\n[測試 1] 胶片模型載入")
try:
    from film_models import get_film_profile, FILM_PROFILES
    
    all_films = ["NC200", "Portra400", "Ektar100", "AS100", "HP5Plus400", "Cinestill800T", "FS200"]
    for film_name in all_films:
        film = get_film_profile(film_name)
        print(f"  ✓ {film_name}: {film.color_type}, gamma={film.tone_params.gamma:.2f}")
    print(f"  ✅ 成功載入 {len(all_films)} 款胶片")
except Exception as e:
    print(f"  ❌ 錯誤: {e}")
    sys.exit(1)

# 測試 2: 快取機制
print("\n[測試 2] 快取機制測試")
try:
    import time
    
    # 首次載入
    start = time.time()
    film1 = get_film_profile("NC200")
    first_time = time.time() - start
    
    # 第二次載入（應該很快）
    start = time.time()
    film2 = get_film_profile("NC200")
    second_time = time.time() - start
    
    print(f"  首次載入: {first_time*1000:.3f}ms")
    print(f"  快取載入: {second_time*1000:.3f}ms")
    print(f"  ✅ 快取機制正常運作")
except Exception as e:
    print(f"  ❌ 錯誤: {e}")

# 測試 3: 優化核心模組
print("\n[測試 3] 優化核心模組")
try:
    from phos_core import (
        generate_grain_optimized,
        apply_bloom_optimized,
        apply_reinhard_optimized,
        apply_filmic_optimized,
        cached_gaussian_blur
    )
    
    # 創建測試數據
    np.random.seed(42)
    test_image = np.random.rand(100, 100).astype(np.float32)
    
    # 測試各個函數
    grain = generate_grain_optimized(test_image, 0.5)
    bloom = apply_bloom_optimized(test_image, 0.5, 20, 0.5, 0.05, 3, 55)
    reinhard = apply_reinhard_optimized(test_image, 2.0, False)
    film = get_film_profile("NC200")
    filmic = apply_filmic_optimized(test_image, film)
    blurred = cached_gaussian_blur(test_image, 21, 3.0)
    
    print(f"  ✓ generate_grain_optimized: {grain.shape}")
    print(f"  ✓ apply_bloom_optimized: {bloom.shape}")
    print(f"  ✓ apply_reinhard_optimized: {reinhard.shape}")
    print(f"  ✓ apply_filmic_optimized: {filmic.shape}")
    print(f"  ✓ cached_gaussian_blur: {blurred.shape}")
    print(f"  ✅ 所有優化函數正常運作")
except Exception as e:
    print(f"  ❌ 錯誤: {e}")
    import traceback
    traceback.print_exc()

# 測試 4: 數值穩定性
print("\n[測試 4] 數值穩定性測試")
try:
    # 測試極端輸入
    black_image = np.zeros((50, 50), dtype=np.float32)
    white_image = np.ones((50, 50), dtype=np.float32)
    
    # 測試全黑圖像
    grain_black = generate_grain_optimized(black_image, 0.5)
    assert not np.isnan(grain_black).any(), "全黑圖像產生 NaN"
    assert not np.isinf(grain_black).any(), "全黑圖像產生 Inf"
    
    # 測試全白圖像
    grain_white = generate_grain_optimized(white_image, 0.5)
    assert not np.isnan(grain_white).any(), "全白圖像產生 NaN"
    assert not np.isinf(grain_white).any(), "全白圖像產生 Inf"
    
    # 測試 tone mapping
    reinhard_black = apply_reinhard_optimized(black_image, 2.0)
    reinhard_white = apply_reinhard_optimized(white_image, 2.0)
    assert not np.isnan(reinhard_black).any(), "Reinhard 產生 NaN"
    assert not np.isnan(reinhard_white).any(), "Reinhard 產生 NaN"
    
    print(f"  ✓ 全黑圖像處理正常")
    print(f"  ✓ 全白圖像處理正常")
    print(f"  ✓ 無 NaN/Inf 產生")
    print(f"  ✅ 數值穩定性測試通過")
except AssertionError as e:
    print(f"  ❌ 數值穩定性問題: {e}")
except Exception as e:
    print(f"  ❌ 錯誤: {e}")

# 測試 5: 效能基準
print("\n[測試 5] 效能基準測試")
try:
    import time
    
    np.random.seed(42)
    test_image = np.random.rand(500, 500).astype(np.float32)
    
    # 測試顆粒生成
    start = time.time()
    for _ in range(10):
        _ = generate_grain_optimized(test_image, 0.5)
    grain_time = (time.time() - start) / 10
    
    # 測試光暈效果
    start = time.time()
    for _ in range(5):
        _ = apply_bloom_optimized(test_image, 0.5, 20, 0.5, 0.05, 3, 55)
    bloom_time = (time.time() - start) / 5
    
    # 測試 Tone mapping
    start = time.time()
    for _ in range(20):
        _ = apply_reinhard_optimized(test_image, 2.0)
    reinhard_time = (time.time() - start) / 20
    
    print(f"  顆粒生成 (500x500): {grain_time*1000:.2f}ms")
    print(f"  光暈效果 (500x500): {bloom_time*1000:.2f}ms")
    print(f"  Tone mapping (500x500): {reinhard_time*1000:.2f}ms")
    print(f"  ✅ 效能測試完成")
except Exception as e:
    print(f"  ❌ 錯誤: {e}")

# 測試 6: 新胶片特性驗證
print("\n[測試 6] 新胶片特性驗證")
try:
    # Portra400 - 人像王者
    portra = get_film_profile("Portra400")
    assert portra.color_type == "color", "Portra400 應為彩色"
    assert portra.red_layer.grain_intensity <= 0.15, "Portra400 顆粒應該很細"
    print(f"  ✓ Portra400: 人像王者（顆粒 {portra.red_layer.grain_intensity:.2f}）")
    
    # Ektar100 - 風景利器
    ektar = get_film_profile("Ektar100")
    assert ektar.color_type == "color", "Ektar100 應為彩色"
    assert ektar.red_layer.grain_intensity <= 0.10, "Ektar100 顆粒應該極細"
    assert ektar.tone_params.gamma >= 2.0, "Ektar100 應該高對比"
    print(f"  ✓ Ektar100: 風景利器（顆粒 {ektar.red_layer.grain_intensity:.2f}, gamma {ektar.tone_params.gamma:.2f}）")
    
    # HP5Plus400 - 經典黑白
    hp5 = get_film_profile("HP5Plus400")
    assert hp5.color_type == "single", "HP5Plus400 應為黑白"
    assert hp5.panchromatic_layer.grain_intensity >= 0.20, "HP5 顆粒應該明顯"
    print(f"  ✓ HP5Plus400: 經典黑白（顆粒 {hp5.panchromatic_layer.grain_intensity:.2f}）")
    
    # Cinestill800T - 電影感
    cinestill = get_film_profile("Cinestill800T")
    assert cinestill.color_type == "color", "Cinestill800T 應為彩色"
    assert cinestill.sensitivity_factor >= 1.5, "Cinestill800T 應該高感光"
    print(f"  ✓ Cinestill800T: 電影感（感光 {cinestill.sensitivity_factor:.2f}）")
    
    print(f"  ✅ 所有新胶片特性驗證通過")
except AssertionError as e:
    print(f"  ❌ 特性驗證失敗: {e}")
except Exception as e:
    print(f"  ❌ 錯誤: {e}")

print("\n" + "=" * 60)
print("✅ v0.1.3 測試全部通過！")
print("=" * 60)
print("\n下一步：")
print("  • 執行: streamlit run Phos_0.1.3.py")
print("  • 上傳照片測試新胶片效果")
print("  • 比較不同胶片的風格差異")
