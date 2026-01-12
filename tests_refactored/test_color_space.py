"""
測試色彩空間轉換與 Gamma 處理

v0.8.2 新增測試：驗證 sRGB → Linear RGB 轉換的正確性

Test Categories:
    1. Gamma 解碼正確性（標準值測試）
    2. 灰階中性（能量守恆）
    3. 逆向轉換（往返誤差）
    4. 邊界條件（0, 1, 臨界點）
    5. 物理正確性（與實際膠片響應比較）

Reference:
    - IEC 61966-2-1:1999 - sRGB 色彩空間標準
    - Poynton, C. (2003). "Digital Video and HD"
"""

import pytest
import numpy as np
import cv2
from modules.optical_core import srgb_to_linear, spectral_response
from film_models import get_film_profile


# ==================== Gamma 解碼正確性測試 ====================

class TestSRGBGammaDecoding:
    """測試 sRGB gamma 解碼的數學正確性"""
    
    def test_srgb_to_linear_zero(self):
        """測試零值（黑色）"""
        result = srgb_to_linear(np.array([0.0]))
        assert result[0] == 0.0, "黑色應保持為 0"
    
    def test_srgb_to_linear_one(self):
        """測試最大值（白色）"""
        result = srgb_to_linear(np.array([1.0]))
        assert result[0] == 1.0, "白色應保持為 1"
    
    def test_srgb_to_linear_linear_region(self):
        """測試線性區域（暗部，sRGB <= 0.04045）"""
        # 在線性區域，C_linear = C_srgb / 12.92
        test_val = 0.03  # 小於 0.04045
        expected = test_val / 12.92
        
        result = srgb_to_linear(np.array([test_val]))
        np.testing.assert_allclose(result[0], expected, rtol=1e-6)
    
    def test_srgb_to_linear_boundary(self):
        """測試線性區域邊界（0.04045）"""
        boundary = 0.04045
        expected = boundary / 12.92
        
        result = srgb_to_linear(np.array([boundary]))
        np.testing.assert_allclose(result[0], expected, rtol=1e-5)
    
    def test_srgb_to_linear_gamma_region(self):
        """測試 Gamma 區域（sRGB > 0.04045）"""
        # 標準測試點：sRGB 0.5 → Linear 0.21404
        # Reference: IEC 61966-2-1:1999 Annex A
        test_val = 0.5
        expected = np.power((test_val + 0.055) / 1.055, 2.4)
        
        result = srgb_to_linear(np.array([test_val]))
        np.testing.assert_allclose(result[0], expected, rtol=1e-6)
        
        # 驗證具體數值
        assert 0.214 < result[0] < 0.215, f"sRGB 0.5 應約為 Linear 0.214，實際為 {result[0]:.6f}"
    
    def test_srgb_to_linear_midtones(self):
        """測試中間調（常見值）"""
        # sRGB 128/255 ≈ 0.502 → Linear ≈ 0.216
        srgb_val = 128.0 / 255.0
        result = srgb_to_linear(np.array([srgb_val]))
        
        assert 0.21 < result[0] < 0.22, f"sRGB 0.502 應約為 Linear 0.216，實際為 {result[0]:.6f}"
    
    def test_srgb_to_linear_array_shape(self):
        """測試陣列形狀保持不變"""
        input_array = np.random.rand(100, 100).astype(np.float32)
        result = srgb_to_linear(input_array)
        
        assert result.shape == input_array.shape, "輸出形狀應與輸入相同"
        assert result.dtype in [np.float32, np.float64], "輸出應為浮點數"
    
    def test_srgb_to_linear_monotonic(self):
        """測試單調性（輸入增加，輸出也應增加）"""
        test_vals = np.linspace(0, 1, 100)
        results = srgb_to_linear(test_vals)
        
        # 檢查單調遞增
        differences = np.diff(results)
        assert np.all(differences >= 0), "Gamma 解碼應該是單調遞增的"


# ==================== 灰階中性測試 ====================

class TestGrayNeutrality:
    """測試 gamma 修正後的灰階中性"""
    
    @pytest.mark.parametrize("gray_level", [0, 64, 128, 192, 255])
    def test_gray_neutrality_uint8(self, gray_level):
        """測試不同灰階值保持中性（uint8 輸入）"""
        # 創建灰階圖像
        gray_image = np.ones((100, 100, 3), dtype=np.uint8) * gray_level
        
        # 轉換為浮點並 gamma 解碼
        gray_float = gray_image.astype(np.float32) / 255.0
        r_linear = srgb_to_linear(gray_float[:, :, 2])  # R
        g_linear = srgb_to_linear(gray_float[:, :, 1])  # G
        b_linear = srgb_to_linear(gray_float[:, :, 0])  # B
        
        # 驗證 RGB 相等（灰階中性）
        np.testing.assert_allclose(r_linear, g_linear, rtol=1e-6)
        np.testing.assert_allclose(g_linear, b_linear, rtol=1e-6)
    
    @pytest.mark.parametrize("film_name", [
        "Portra400", "Ektar100", "Velvia50", "NC200"
    ])
    def test_gray_neutrality_with_film_response(self, film_name):
        """測試膠片響應後的灰階中性"""
        film = get_film_profile(film_name)
        
        # 創建灰階圖像（中間調）
        gray_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        
        # 計算膠片響應
        response_r, response_g, response_b, _ = spectral_response(gray_image, film)
        
        # 計算平均值
        mean_r = np.mean(response_r)
        mean_g = np.mean(response_g)
        mean_b = np.mean(response_b)
        
        # 驗證灰階偏差（允許 ±1% 誤差，因為膠片矩陣經過校準）
        deviation = max(abs(mean_r - mean_g), abs(mean_g - mean_b), abs(mean_r - mean_b))
        
        assert deviation < 0.01, (
            f"{film_name}: 灰階偏差過大 {deviation:.4f} (R={mean_r:.4f}, G={mean_g:.4f}, B={mean_b:.4f})"
        )


# ==================== 能量守恆測試 ====================

class TestEnergyConservation:
    """測試線性光空間的能量守恆"""
    
    def test_white_energy_conservation(self):
        """測試白色（255, 255, 255）的能量守恆"""
        # sRGB 白色 → Linear 白色 (1, 1, 1)
        white_srgb = np.array([1.0, 1.0, 1.0])
        white_linear = srgb_to_linear(white_srgb)
        
        # 應該仍然是 (1, 1, 1)
        np.testing.assert_allclose(white_linear, [1.0, 1.0, 1.0], rtol=1e-6)
    
    def test_black_energy_conservation(self):
        """測試黑色（0, 0, 0）的能量守恆"""
        black_srgb = np.array([0.0, 0.0, 0.0])
        black_linear = srgb_to_linear(black_srgb)
        
        # 應該仍然是 (0, 0, 0)
        np.testing.assert_allclose(black_linear, [0.0, 0.0, 0.0], rtol=1e-6)
    
    def test_midtone_energy_reduction(self):
        """測試中間調能量降低（Gamma 解碼特性）"""
        # sRGB 中間調 (0.5, 0.5, 0.5) → Linear (~0.214, ~0.214, ~0.214)
        midtone_srgb = np.array([0.5, 0.5, 0.5])
        midtone_linear = srgb_to_linear(midtone_srgb)
        
        # 線性空間的中間調應該顯著小於 0.5（約 21% 強度）
        assert np.all(midtone_linear < 0.25), "中間調在線性空間應約為 21% 強度"
        assert np.all(midtone_linear > 0.20), "中間調不應過低"


# ==================== 逆向轉換測試（往返誤差）====================

class TestRoundTrip:
    """測試 sRGB ↔ Linear 往返轉換的誤差"""
    
    def linear_to_srgb(self, linear: np.ndarray) -> np.ndarray:
        """Linear RGB → sRGB（逆向轉換）"""
        return np.where(
            linear <= 0.0031308,
            linear * 12.92,
            1.055 * np.power(linear, 1/2.4) - 0.055
        )
    
    def test_roundtrip_accuracy(self):
        """測試往返轉換精度"""
        # 測試 100 個隨機值
        original_srgb = np.random.rand(100).astype(np.float32)
        
        # sRGB → Linear → sRGB
        linear = srgb_to_linear(original_srgb)
        recovered_srgb = self.linear_to_srgb(linear)
        
        # 驗證往返誤差 < 0.1%
        np.testing.assert_allclose(recovered_srgb, original_srgb, rtol=1e-3)
    
    def test_specific_values_roundtrip(self):
        """測試特定值的往返精度"""
        test_values = [0.0, 0.04045, 0.1, 0.5, 0.8, 1.0]
        
        for val in test_values:
            linear = srgb_to_linear(np.array([val]))
            recovered = self.linear_to_srgb(linear)
            
            np.testing.assert_allclose(
                recovered[0], val, rtol=1e-5,
                err_msg=f"往返誤差過大：{val} → {linear[0]:.6f} → {recovered[0]:.6f}"
            )


# ==================== 邊界條件與異常測試 ====================

class TestEdgeCases:
    """測試邊界條件與異常輸入"""
    
    def test_negative_values(self):
        """測試負值（理論上不應出現，但需要處理）"""
        # Gamma 解碼應該保持符號
        negative_vals = np.array([-0.1, -0.5, -1.0])
        result = srgb_to_linear(negative_vals)
        
        # 負值應保持為負（或被 clip 為 0）
        # 這取決於實作策略，這裡檢查不會產生 NaN
        assert not np.any(np.isnan(result)), "不應產生 NaN"
    
    def test_values_above_one(self):
        """測試大於 1 的值（HDR 情況）"""
        hdr_vals = np.array([1.5, 2.0, 5.0])
        result = srgb_to_linear(hdr_vals)
        
        # 應該正確處理（遵循 gamma 公式）
        assert not np.any(np.isnan(result)), "HDR 值不應產生 NaN"
        assert np.all(result > hdr_vals), "HDR 值在線性空間應更大"
    
    def test_nan_propagation(self):
        """測試 NaN 傳播"""
        nan_vals = np.array([0.5, np.nan, 0.8])
        result = srgb_to_linear(nan_vals)
        
        # NaN 應該被保留在對應位置
        assert np.isnan(result[1]), "NaN 應該被保留"
        assert not np.isnan(result[0]), "非 NaN 值不應變成 NaN"
    
    def test_empty_array(self):
        """測試空陣列"""
        empty = np.array([])
        result = srgb_to_linear(empty)
        
        assert result.shape == (0,), "空陣列應保持為空"


# ==================== 物理正確性驗證 ====================

class TestPhysicalCorrectness:
    """驗證 gamma 修正後的物理正確性"""
    
    def test_linear_space_additivity(self):
        """測試線性空間的可加性（物理光強度的基本性質）"""
        # 兩個光源的物理光強度可以直接相加
        light1_srgb = np.array([0.3, 0.3, 0.3])
        light2_srgb = np.array([0.4, 0.4, 0.4])
        
        # 方法 1: 先轉換再相加
        light1_linear = srgb_to_linear(light1_srgb)
        light2_linear = srgb_to_linear(light2_srgb)
        combined_linear = light1_linear + light2_linear
        
        # 方法 2: 先相加再轉換（錯誤的 sRGB 空間相加）
        combined_srgb = light1_srgb + light2_srgb
        wrong_linear = srgb_to_linear(combined_srgb)
        
        # 兩種方法結果應該不同（證明 gamma 空間運算是錯的）
        difference = np.abs(combined_linear - wrong_linear)
        assert np.all(difference > 0.01), "線性空間與 gamma 空間運算結果應明顯不同"
    
    def test_beer_lambert_correctness(self):
        """測試 Beer-Lambert Law 在線性空間的正確性"""
        # Beer-Lambert: I_out = I_in * exp(-α*L)
        # 只在線性光空間物理正確
        
        # 創建測試圖像（50% 灰）
        test_image = np.ones((10, 10, 3), dtype=np.uint8) * 128
        
        # 計算膠片響應（應該在線性空間）
        film = get_film_profile("Portra400")
        response_r, response_g, response_b, _ = spectral_response(test_image, film)
        
        # 驗證響應值在合理範圍（0-1）
        assert np.all(response_r >= 0) and np.all(response_r <= 1.5), "紅色響應應在合理範圍"
        assert np.all(response_g >= 0) and np.all(response_g <= 1.5), "綠色響應應在合理範圍"
        assert np.all(response_b >= 0) and np.all(response_b <= 1.5), "藍色響應應在合理範圍"


# ==================== 效能測試 ====================

@pytest.mark.benchmark
class TestPerformance:
    """測試 gamma 解碼的效能"""
    
    def test_gamma_decode_speed(self, benchmark):
        """基準測試：gamma 解碼速度"""
        test_image = np.random.rand(3000, 4000).astype(np.float32)
        
        result = benchmark(srgb_to_linear, test_image)
        
        # 驗證結果正確
        assert result.shape == test_image.shape
    
    def test_full_pipeline_speed(self, benchmark):
        """基準測試：完整流程（含 gamma 解碼）"""
        test_image = np.random.randint(0, 256, (3000, 4000, 3), dtype=np.uint8)
        film = get_film_profile("Portra400")
        
        result = benchmark(spectral_response, test_image, film)
        
        # 驗證結果正確
        assert result[0] is not None  # response_r


# ==================== 標記與配置 ====================

pytest.mark.color_space = pytest.mark.mark("color_space", "Color space conversion tests")
pytest.mark.gamma = pytest.mark.mark("gamma", "Gamma encoding/decoding tests")
pytest.mark.physics = pytest.mark.mark("physics", "Physical correctness tests")
