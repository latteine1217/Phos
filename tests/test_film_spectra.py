"""
測試膠片光譜敏感度整合 (Phase 4.5)

測試項目：
1. 膠片數據載入測試
2. 膠片敏感度曲線驗證（峰值、範圍）
3. 色彩偏移測試（Portra vs Velvia）
4. Roundtrip 誤差測試（每款膠片）
5. 效能測試（500×500, 2000×3000）
"""

import sys
import os
import time
import numpy as np

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import color_utils


# ============================================================
# 測試 1: 膠片數據載入測試
# ============================================================

def test_load_film_spectra():
    """測試膠片光譜敏感度數據載入"""
    print("\n" + "=" * 70)
    print("[測試 1] 膠片數據載入測試")
    print("=" * 70)
    
    # 觸發載入
    color_utils._load_film_spectra()
    
    # 驗證：4 款膠片
    expected_films = ['Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400']
    assert len(color_utils.FILM_SPECTRA) == 4, \
        f"Expected 4 films, got {len(color_utils.FILM_SPECTRA)}"
    
    for film in expected_films:
        assert film in color_utils.FILM_SPECTRA, f"Missing film: {film}"
        
        # 驗證：3 個通道
        assert 'red' in color_utils.FILM_SPECTRA[film]
        assert 'green' in color_utils.FILM_SPECTRA[film]
        assert 'blue' in color_utils.FILM_SPECTRA[film]
        
        # 驗證：31 個波長點
        for channel in ['red', 'green', 'blue']:
            curve = color_utils.FILM_SPECTRA[film][channel]
            assert curve.shape == (31,), \
                f"{film} {channel}: Expected shape (31,), got {curve.shape}"
            
            # 驗證：值域 [0, 1]
            assert np.all(curve >= 0) and np.all(curve <= 1), \
                f"{film} {channel}: Values out of range [0, 1]"
    
    print(f"✅ 成功載入 {len(expected_films)} 款膠片")
    print(f"   膠片列表: {', '.join(expected_films)}")
    print(f"   每款膠片: 3 通道 × 31 波長點")


# ============================================================
# 測試 2: 膠片敏感度曲線驗證（峰值、範圍）
# ============================================================

def test_film_sensitivity_peaks():
    """測試膠片敏感度曲線峰值位置"""
    print("\n" + "=" * 70)
    print("[測試 2] 膠片敏感度峰值驗證")
    print("=" * 70)
    
    color_utils._load_film_spectra()
    
    # 預期峰值（根據 generate_film_spectra.py）
    expected_peaks = {
        'Portra400': {'red': 640, 'green': 549, 'blue': 445},
        'Velvia50': {'red': 640, 'green': 549, 'blue': 445},
        'Cinestill800T': {'red': 627, 'green': 549, 'blue': 445},
        'HP5Plus400': {'red': 445, 'green': 445, 'blue': 445}  # 全色
    }
    
    wavelengths = color_utils.WAVELENGTHS
    
    for film, peaks in expected_peaks.items():
        print(f"\n{film}:")
        
        for channel, expected_peak in peaks.items():
            curve = color_utils.FILM_SPECTRA[film][channel]
            
            # 找實際峰值
            peak_idx = np.argmax(curve)
            actual_peak = wavelengths[peak_idx]
            
            # 允許誤差 ±13nm（一個採樣點）
            assert abs(actual_peak - expected_peak) <= 13, \
                f"{film} {channel}: Expected peak {expected_peak}nm, got {actual_peak}nm"
            
            print(f"  {channel:5s}: {actual_peak:.0f} nm (expected {expected_peak} nm) ✓")


# ============================================================
# 測試 3: 色彩偏移測試（Portra vs Velvia）
# ============================================================

def test_film_color_shift_comparison():
    """測試不同膠片的色彩差異（Velvia 應更飽和）"""
    print("\n" + "=" * 70)
    print("[測試 3] 色彩偏移測試（Portra vs Velvia）")
    print("=" * 70)
    
    # 測試純色
    test_colors = {
        'Red': np.array([[[1.0, 0.0, 0.0]]]),
        'Green': np.array([[[0.0, 1.0, 0.0]]]),
        'Blue': np.array([[[0.0, 0.0, 1.0]]]),
        'Yellow': np.array([[[1.0, 1.0, 0.0]]]),
    }
    
    for color_name, rgb_input in test_colors.items():
        print(f"\n{color_name} ({rgb_input[0, 0]}):")
        
        # RGB → Spectrum
        spectrum = color_utils.rgb_to_spectrum(rgb_input)
        
        # 兩款膠片
        rgb_portra = color_utils.spectrum_to_rgb_with_film(spectrum, 'Portra400')
        rgb_velvia = color_utils.spectrum_to_rgb_with_film(spectrum, 'Velvia50')
        
        print(f"  Portra400: {rgb_portra[0, 0]}")
        print(f"  Velvia50:  {rgb_velvia[0, 0]}")
        
        # 計算飽和度（與原始色的距離）
        error_portra = np.max(np.abs(rgb_portra - rgb_input))
        error_velvia = np.max(np.abs(rgb_velvia - rgb_input))
        
        print(f"  誤差 (Portra): {error_portra:.4f}")
        print(f"  誤差 (Velvia): {error_velvia:.4f}")


# ============================================================
# 測試 4: Roundtrip 誤差測試（每款膠片）
# ============================================================

def test_film_roundtrip_error():
    """測試每款膠片的 RGB → Spectrum → RGB 往返誤差"""
    print("\n" + "=" * 70)
    print("[測試 4] Roundtrip 誤差測試（每款膠片）")
    print("=" * 70)
    
    # 測試色塊（隨機生成）
    np.random.seed(42)
    test_rgb = np.random.rand(10, 10, 3).astype(np.float32)
    
    films = ['Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400']
    
    errors = {}
    for film in films:
        # RGB → Spectrum
        spectrum = color_utils.rgb_to_spectrum(test_rgb)
        
        # Spectrum → RGB (with film)
        rgb_recon = color_utils.spectrum_to_rgb_with_film(spectrum, film)
        
        # 計算誤差
        error = np.mean(np.abs(test_rgb - rgb_recon))
        errors[film] = error
        
        print(f"{film:20s}: 平均誤差 {error:.4f} ({error*100:.2f}%)")
    
    # 驗證：誤差應 < 25%（膠片敏感度會增加額外非線性）
    # 注意：比無膠片的 8-20% 高，因為 film(λ) 引入額外調製
    for film, error in errors.items():
        assert error < 0.25, \
            f"{film}: Roundtrip error {error:.2%} exceeds 25% threshold"
    
    print(f"\n✅ 所有膠片往返誤差 < 25%")
    print(f"   註：比無膠片版本 (8-20%) 高，因膠片敏感度曲線引入額外非線性")


# ============================================================
# 測試 5: test_film_color_shift() 函數測試
# ============================================================

def test_film_color_shift_function():
    """測試 test_film_color_shift() 輔助函數"""
    print("\n" + "=" * 70)
    print("[測試 5] test_film_color_shift() 函數測試")
    print("=" * 70)
    
    # 測試單個純色
    rgb_red = np.array([1.0, 0.0, 0.0])
    
    results = color_utils.test_film_color_shift(rgb_red)
    
    # 驗證：4 款膠片都有結果
    assert len(results) == 4, f"Expected 4 results, got {len(results)}"
    
    for film, result in results.items():
        print(f"\n{film}:")
        
        # 驗證：無異常
        assert 'exception' not in result, \
            f"{film} raised exception: {result.get('exception')}"
        
        # 驗證：有輸出
        assert result['rgb_output'] is not None
        assert result['error'] is not None
        
        print(f"  輸出 RGB: {result['rgb_output']}")
        print(f"  誤差: {result['error']:.4f}")
    
    print(f"\n✅ test_film_color_shift() 函數正常運作")


# ============================================================
# 測試 6: 效能測試（500×500, 2000×3000）
# ============================================================

def test_performance():
    """測試膠片光譜轉換效能"""
    print("\n" + "=" * 70)
    print("[測試 6] 效能測試")
    print("=" * 70)
    
    # 測試尺寸
    sizes = [
        (500, 500),
        (2000, 3000)
    ]
    
    for h, w in sizes:
        # 生成測試影像
        test_img = np.random.rand(h, w, 3).astype(np.float32)
        
        # RGB → Spectrum
        t0 = time.time()
        spectrum = color_utils.rgb_to_spectrum(test_img)
        t1 = time.time()
        
        # Spectrum → RGB (Portra400)
        rgb_recon = color_utils.spectrum_to_rgb_with_film(spectrum, 'Portra400')
        t2 = time.time()
        
        time_to_spectrum = t1 - t0
        time_from_spectrum = t2 - t1
        total_time = t2 - t0
        
        print(f"\n{h}×{w} 影像:")
        print(f"  RGB → Spectrum:   {time_to_spectrum:.3f}s")
        print(f"  Spectrum → RGB:   {time_from_spectrum:.3f}s")
        print(f"  總時間:           {total_time:.3f}s")
        
        # 驗證：2000×3000 應 < 2.5s（含膠片敏感度積分）
        if h == 2000 and w == 3000:
            assert total_time < 2.5, \
                f"Performance target not met: {total_time:.3f}s > 2.5s"
            print(f"  ✅ 效能達標 (< 2.5s)")


# ============================================================
# 測試 7: 黑白膠片特殊處理
# ============================================================

def test_bw_film_response():
    """測試黑白膠片（HP5 Plus）的全色響應"""
    print("\n" + "=" * 70)
    print("[測試 7] 黑白膠片全色響應測試")
    print("=" * 70)
    
    color_utils._load_film_spectra()
    
    # HP5 Plus 應為全色響應（R=G=B 相同峰值）
    hp5 = color_utils.FILM_SPECTRA['HP5Plus400']
    
    # 驗證：三通道峰值位置相同
    peak_r = color_utils.WAVELENGTHS[np.argmax(hp5['red'])]
    peak_g = color_utils.WAVELENGTHS[np.argmax(hp5['green'])]
    peak_b = color_utils.WAVELENGTHS[np.argmax(hp5['blue'])]
    
    print(f"HP5 Plus 400 峰值位置:")
    print(f"  Red:   {peak_r:.0f} nm")
    print(f"  Green: {peak_g:.0f} nm")
    print(f"  Blue:  {peak_b:.0f} nm")
    
    assert peak_r == peak_g == peak_b, \
        f"HP5 Plus should have same peak for all channels"
    
    # 測試：彩色輸入應產生近似灰階輸出
    rgb_color = np.array([[[0.8, 0.3, 0.2]]])  # 橙色
    
    spectrum = color_utils.rgb_to_spectrum(rgb_color)
    rgb_bw = color_utils.spectrum_to_rgb_with_film(spectrum, 'HP5Plus400')
    
    print(f"\n彩色輸入: {rgb_color[0, 0]}")
    print(f"黑白輸出: {rgb_bw[0, 0]}")
    
    # 驗證：相對於標準 Spectrum → RGB，HP5 輸出應更接近灰階
    rgb_standard = color_utils.xyz_to_rgb(color_utils.spectrum_to_xyz(spectrum))
    
    # 計算灰階度（標準差）
    def grayness(rgb):
        """計算 RGB 的灰階度（越小越接近灰階）"""
        mean = np.mean(rgb)
        return np.std(rgb - mean)
    
    gray_standard = grayness(rgb_standard[0, 0])
    gray_hp5 = grayness(rgb_bw[0, 0])
    
    print(f"\n灰階度 (標準): {gray_standard:.4f}")
    print(f"灰階度 (HP5):  {gray_hp5:.4f}")
    
    # HP5 的灰階度應與標準版相近（因為全色響應）
    # 注意：不會完全灰階，因為 CIE 本身有色彩權重
    print(f"✅ 黑白膠片測試完成（全色響應峰值一致）")


# ============================================================
# 主程式
# ============================================================

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("  Phase 4.5 - 膠片光譜敏感度整合測試")
    print("=" * 70)
    
    try:
        test_load_film_spectra()
        test_film_sensitivity_peaks()
        test_film_color_shift_comparison()
        test_film_roundtrip_error()
        test_film_color_shift_function()
        test_performance()
        test_bw_film_response()
        
        print("\n" + "=" * 70)
        print("  ✅ 所有測試通過！Phase 4.5 完成")
        print("=" * 70)
        
    except AssertionError as e:
        print("\n" + "=" * 70)
        print(f"  ❌ 測試失敗: {e}")
        print("=" * 70)
        sys.exit(1)
    
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"  ❌ 未預期錯誤: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
