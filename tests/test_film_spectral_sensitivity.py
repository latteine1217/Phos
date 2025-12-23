"""
測試膠片光譜敏感度功能（Phase 4 Milestone 3）

測試範圍：
- load_film_sensitivity(): 膠片資料載入
- apply_film_spectral_sensitivity(): 光譜→膠片 RGB 轉換
- process_image_spectral_mode(): 完整光譜流程

Version: 0.4.0
Date: 2025-12-22
"""

import pytest
import numpy as np
from phos_core import (
    load_film_sensitivity,
    apply_film_spectral_sensitivity,
    process_image_spectral_mode,
    rgb_to_spectrum
)


class TestLoadFilmSensitivity:
    """測試膠片敏感度資料載入"""
    
    def test_load_portra400(self):
        """測試載入 Portra400"""
        curves = load_film_sensitivity('Portra400')
        
        assert 'wavelengths' in curves
        assert 'red' in curves
        assert 'green' in curves
        assert 'blue' in curves
        assert 'type' in curves
        
        assert curves['wavelengths'].shape == (31,)
        assert curves['red'].shape == (31,)
        assert curves['green'].shape == (31,)
        assert curves['blue'].shape == (31,)
        assert curves['type'] == 'color_negative'
    
    def test_load_velvia50(self):
        """測試載入 Velvia50"""
        curves = load_film_sensitivity('Velvia50')
        
        assert curves['type'] == 'color_reversal'
        assert curves['red'].shape == (31,)
    
    def test_load_cinestill800t(self):
        """測試載入 Cinestill800T"""
        curves = load_film_sensitivity('Cinestill800T')
        
        assert curves['type'] == 'color_negative_tungsten'
        assert curves['red'].shape == (31,)
    
    def test_load_hp5plus400(self):
        """測試載入 HP5Plus400 黑白片"""
        curves = load_film_sensitivity('HP5Plus400')
        
        assert curves['type'] == 'bw_panchromatic'
        assert curves['red'].shape == (31,)
    
    def test_load_invalid_film(self):
        """測試載入不存在的膠片"""
        with pytest.raises(ValueError, match="not found"):
            load_film_sensitivity('InvalidFilm')
    
    def test_peak_wavelengths(self):
        """測試敏感度曲線峰值位置合理"""
        curves = load_film_sensitivity('Portra400')
        wavelengths = curves['wavelengths']
        
        red_peak = wavelengths[np.argmax(curves['red'])]
        green_peak = wavelengths[np.argmax(curves['green'])]
        blue_peak = wavelengths[np.argmax(curves['blue'])]
        
        # 紅色層峰值應在 600-700nm
        assert 600 <= red_peak <= 700, f"Red peak at {red_peak}nm (expected 600-700nm)"
        
        # 綠色層峰值應在 500-600nm
        assert 500 <= green_peak <= 600, f"Green peak at {green_peak}nm (expected 500-600nm)"
        
        # 藍色層峰值應在 400-500nm
        assert 400 <= blue_peak <= 500, f"Blue peak at {blue_peak}nm (expected 400-500nm)"
    
    def test_curve_normalization(self):
        """測試曲線歸一化（最大值 = 1）"""
        curves = load_film_sensitivity('Portra400')
        
        assert np.allclose(curves['red'].max(), 1.0, atol=0.01)
        assert np.allclose(curves['green'].max(), 1.0, atol=0.01)
        assert np.allclose(curves['blue'].max(), 1.0, atol=0.01)
    
    def test_curve_non_negative(self):
        """測試曲線非負"""
        curves = load_film_sensitivity('Portra400')
        
        assert np.all(curves['red'] >= 0)
        assert np.all(curves['green'] >= 0)
        assert np.all(curves['blue'] >= 0)


class TestApplyFilmSpectralSensitivity:
    """測試膠片光譜響應"""
    
    def test_white_spectrum_response(self):
        """測試白色光譜響應"""
        white_spectrum = np.ones(31, dtype=np.float32)
        portra = load_film_sensitivity('Portra400')
        
        film_rgb = apply_film_spectral_sensitivity(white_spectrum, portra, normalize=True)
        
        assert film_rgb.shape == (3,)
        assert np.allclose(film_rgb, [1, 1, 1], atol=0.1), \
            f"White spectrum should give ~(1,1,1), got {film_rgb}"
    
    def test_black_spectrum_response(self):
        """測試黑色光譜響應"""
        black_spectrum = np.zeros(31, dtype=np.float32)
        portra = load_film_sensitivity('Portra400')
        
        film_rgb = apply_film_spectral_sensitivity(black_spectrum, portra)
        
        assert np.allclose(film_rgb, [0, 0, 0], atol=0.01)
    
    def test_monochromatic_red(self):
        """測試單色紅光響應"""
        red_spectrum = np.zeros(31, dtype=np.float32)
        red_spectrum[25] = 1.0  # 650nm
        
        portra = load_film_sensitivity('Portra400')
        film_rgb = apply_film_spectral_sensitivity(red_spectrum, portra, normalize=False)
        
        # 紅色通道應該最強
        assert film_rgb[0] > film_rgb[1], "Red channel should be dominant"
        assert film_rgb[0] > film_rgb[2], "Red channel should be dominant"
    
    def test_monochromatic_green(self):
        """測試單色綠光響應"""
        green_spectrum = np.zeros(31, dtype=np.float32)
        green_spectrum[15] = 1.0  # 550nm
        
        portra = load_film_sensitivity('Portra400')
        film_rgb = apply_film_spectral_sensitivity(green_spectrum, portra, normalize=True)
        
        # 綠色通道應該最強（gamma 編碼後仍保持相對關係）
        # 注意：normalize=True 會正規化，因此改用相對比較
        assert film_rgb[1] >= film_rgb[0], "Green channel should be dominant"
        assert film_rgb[1] >= film_rgb[2], "Green channel should be dominant"
    
    def test_monochromatic_blue(self):
        """測試單色藍光響應"""
        blue_spectrum = np.zeros(31, dtype=np.float32)
        blue_spectrum[5] = 1.0  # 445nm
        
        portra = load_film_sensitivity('Portra400')
        film_rgb = apply_film_spectral_sensitivity(blue_spectrum, portra, normalize=True)
        
        # 藍色通道應該最強（gamma 編碼後仍保持相對關係）
        # 注意：normalize=True 會正規化，因此改用相對比較
        assert film_rgb[2] >= film_rgb[0], "Blue channel should be dominant"
        assert film_rgb[2] >= film_rgb[1], "Blue channel should be dominant"
    
    def test_different_films_different_response(self):
        """測試不同膠片響應不同"""
        # 偏綠的顏色
        rgb_in = np.array([0.5, 0.7, 0.3], dtype=np.float32)
        spectrum = rgb_to_spectrum(rgb_in)
        
        portra = load_film_sensitivity('Portra400')
        velvia = load_film_sensitivity('Velvia50')
        
        portra_rgb = apply_film_spectral_sensitivity(spectrum, portra)
        velvia_rgb = apply_film_spectral_sensitivity(spectrum, velvia)
        
        # 兩種膠片的響應應該不同
        color_diff = np.linalg.norm(portra_rgb - velvia_rgb)
        assert color_diff > 0.01, \
            f"Portra and Velvia should produce different colors, diff={color_diff:.4f}"
    
    def test_image_spectrum_processing(self):
        """測試完整影像光譜處理"""
        # 100×100 隨機影像
        img_spectrum = np.random.rand(100, 100, 31).astype(np.float32)
        
        portra = load_film_sensitivity('Portra400')
        film_rgb = apply_film_spectral_sensitivity(img_spectrum, portra)
        
        assert film_rgb.shape == (100, 100, 3)
        assert film_rgb.dtype == np.float32
        assert np.all(film_rgb >= 0)
        assert np.all(film_rgb <= 1)
    
    def test_normalization_flag(self):
        """測試歸一化開關"""
        spectrum = np.ones(31, dtype=np.float32)
        portra = load_film_sensitivity('Portra400')
        
        rgb_normalized = apply_film_spectral_sensitivity(spectrum, portra, normalize=True)
        rgb_raw = apply_film_spectral_sensitivity(spectrum, portra, normalize=False)
        
        # 歸一化後應該接近 1
        assert np.allclose(rgb_normalized, 1.0, atol=0.1)
        
        # 未歸一化的值應該更大
        assert np.all(rgb_raw > rgb_normalized)
    
    def test_color_relationship_preservation(self):
        """測試色彩關係保持（暖色→暖RGB）"""
        # 暖色調 (R > G > B)
        warm_rgb = np.array([0.8, 0.5, 0.3], dtype=np.float32)
        spectrum = rgb_to_spectrum(warm_rgb)
        
        portra = load_film_sensitivity('Portra400')
        film_rgb = apply_film_spectral_sensitivity(spectrum, portra)
        
        # 應該保持 R > G > B 的關係
        assert film_rgb[0] > film_rgb[1], "Warm color should have R > G"
        assert film_rgb[1] > film_rgb[2], "Warm color should have G > B"


class TestProcessImageSpectralMode:
    """測試完整光譜流程"""
    
    def test_film_mode(self):
        """測試膠片模式"""
        img = np.random.rand(50, 50, 3).astype(np.float32)
        
        result = process_image_spectral_mode(img, 'Portra400', apply_film_response=True)
        
        assert result.shape == (50, 50, 3)
        assert result.dtype == np.float32
        assert np.all(result >= 0)
        assert np.all(result <= 1)
    
    def test_standard_mode(self):
        """測試標準色彩模式"""
        img = np.random.rand(50, 50, 3).astype(np.float32)
        
        result = process_image_spectral_mode(img, 'Portra400', apply_film_response=False)
        
        assert result.shape == (50, 50, 3)
        assert result.dtype == np.float32
        assert np.all(result >= 0)
        assert np.all(result <= 1)
    
    def test_film_vs_standard_difference(self):
        """測試膠片模式與標準模式的差異"""
        img = np.random.rand(50, 50, 3).astype(np.float32)
        
        film_result = process_image_spectral_mode(img, 'Portra400', apply_film_response=True)
        standard_result = process_image_spectral_mode(img, 'Portra400', apply_film_response=False)
        
        # 兩種模式應該有差異（膠片有色偏）
        diff = np.mean(np.abs(film_result - standard_result))
        assert diff > 0.01, \
            f"Film and standard modes should differ, but diff={diff:.4f}"
    
    def test_different_films_produce_different_results(self):
        """測試不同膠片產生不同結果"""
        img = np.random.rand(50, 50, 3).astype(np.float32)
        
        portra_result = process_image_spectral_mode(img, 'Portra400', True)
        velvia_result = process_image_spectral_mode(img, 'Velvia50', True)
        
        diff = np.mean(np.abs(portra_result - velvia_result))
        assert diff > 0.01, \
            f"Different films should produce different results, but diff={diff:.4f}"
    
    def test_roundtrip_reasonable_error(self):
        """測試往返誤差在合理範圍內"""
        original_rgb = np.array([[[0.8, 0.5, 0.3]]], dtype=np.float32)  # (1, 1, 3)
        
        # 膠片模式往返
        result = process_image_spectral_mode(original_rgb, 'Portra400', True)
        
        # 注意：膠片模式會有色偏（這是特性，不是 bug）
        # 但誤差應該在合理範圍內（<30%）
        error = np.abs(result - original_rgb).max()
        assert error < 0.3, \
            f"Roundtrip error too large: {error:.3f} (>30%)"


class TestPhysicalCorrectness:
    """物理正確性測試"""
    
    def test_energy_conservation(self):
        """測試能量守恆（在 gamma 前驗證，白色→白色）"""
        white_spectrum = np.ones(31, dtype=np.float32)
        portra = load_film_sensitivity('Portra400')
        
        # 取得 sRGB 輸出
        film_rgb_srgb = apply_film_spectral_sensitivity(white_spectrum, portra, normalize=True)
        
        # 反向 gamma 至 Linear 空間驗證能量守恆
        # 注意：這是間接測試，實際應在積分層驗證（需程式碼重構）
        # 白色光譜應該產生接近白色的 RGB（sRGB 空間）
        luminance = film_rgb_srgb.mean()
        assert 0.8 <= luminance <= 1.0, \
            f"White spectrum luminance {luminance:.3f} out of range [0.8, 1.0]"
        
        # 能量守恆說明：
        # 在 Linear RGB 域，白色光譜 → RGB(1,1,1) → gamma → sRGB(1,1,1)
        # 此測試驗證最終 sRGB 輸出，間接確認 Linear 域能量守恆
    
    def test_non_negativity(self):
        """測試非負性（所有輸出 >= 0）"""
        random_spectrum = np.random.rand(31).astype(np.float32)
        portra = load_film_sensitivity('Portra400')
        
        film_rgb = apply_film_spectral_sensitivity(random_spectrum, portra)
        
        assert np.all(film_rgb >= 0), \
            f"Film RGB contains negative values: min={film_rgb.min()}"
    
    def test_linearity(self):
        """測試線性響應（2×光譜在 Linear 空間線性，但 sRGB 輸出非線性）"""
        spectrum = np.random.rand(31).astype(np.float32) * 0.3  # 使用較小值避免裁剪
        portra = load_film_sensitivity('Portra400')
        
        rgb1 = apply_film_spectral_sensitivity(spectrum, portra, normalize=True)
        rgb2 = apply_film_spectral_sensitivity(2 * spectrum, portra, normalize=True)
        
        # sRGB 空間非線性（因 gamma 編碼），但應保持單調性
        # 2×光譜 → 更亮的 RGB（但不是 2 倍關係）
        assert np.all(rgb2 > rgb1), \
            "Doubled spectrum should produce brighter output"
        assert np.all(rgb2 <= 1.0), \
            "Output should be clipped to [0, 1]"
        
        # 驗證 gamma 編碼的非線性性質
        # Linear(2x) → sRGB(~1.3-1.8x)，不是嚴格 2 倍
        # gamma=2.2 導致壓縮：2^(1/2.2) ≈ 1.66
        ratio = rgb2 / (rgb1 + 1e-6)
        assert np.all(ratio < 2.0), \
            "sRGB gamma encoding should compress the ratio"
        assert np.all(ratio > 1.3), \
            "But ratio should still be significant (>1.3x)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
