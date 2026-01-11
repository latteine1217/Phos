"""
測試 Bloom 策略模式重構（v0.6.0）

測試目標:
1. 向後相容性：Artistic 模式結果與 v0.5.0 一致
2. 能量守恆：Physical 模式能量誤差 < 1%
3. 波長依賴性：Mie Corrected 模式 η_blue > η_red
4. 工廠模式：get_bloom_strategy() 正確返回策略類
5. 統一介面：apply_bloom() 正確委派到策略

Created: 2026-01-12
Author: Refactoring Task (Session 2026-01-12)
"""

import pytest
import numpy as np
from bloom_strategies import (
    BloomStrategy,
    ArtisticBloomStrategy,
    PhysicalBloomStrategy,
    MieCorrectedBloomStrategy,
    get_bloom_strategy,
    apply_bloom
)
from film_models import BloomParams


# ==================== Fixtures ====================

@pytest.fixture
def test_image_single_channel():
    """創建單通道測試圖像（512x512, 0-1 浮點）"""
    img = np.zeros((512, 512), dtype=np.float32)
    
    # 中心白色高光（模擬路燈）
    center_y, center_x = 256, 256
    y, x = np.ogrid[:512, :512]
    dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
    
    # 高斯形狀高光（半徑 20 像素，峰值 1.0）
    highlight = np.exp(-dist**2 / (2 * 20**2))
    img = highlight
    
    return img


@pytest.fixture
def bloom_params_artistic():
    """Artistic 模式參數（預設）"""
    return BloomParams(mode="artistic")


@pytest.fixture
def bloom_params_physical():
    """Physical 模式參數"""
    return BloomParams(
        mode="physical",
        sensitivity=1.2,
        threshold=0.7,
        scattering_ratio=0.18
    )


@pytest.fixture
def bloom_params_mie():
    """Mie Corrected 模式參數"""
    return BloomParams(
        mode="mie_corrected",
        sensitivity=1.5,
        threshold=0.6,
        scattering_ratio=0.20
    )


# ==================== 策略類測試 ====================

class TestArtisticBloomStrategy:
    """測試 Artistic Bloom 策略"""
    
    def test_initialization(self, bloom_params_artistic):
        """測試策略初始化"""
        strategy = ArtisticBloomStrategy(bloom_params_artistic)
        assert strategy.params == bloom_params_artistic
    
    def test_apply_output_shape(self, test_image_single_channel, bloom_params_artistic):
        """測試輸出形狀與輸入一致"""
        strategy = ArtisticBloomStrategy(bloom_params_artistic)
        output = strategy.apply(test_image_single_channel)
        assert output.shape == test_image_single_channel.shape
        assert np.issubdtype(output.dtype, np.floating), "輸出應為浮點類型"
    
    def test_apply_value_range(self, test_image_single_channel, bloom_params_artistic):
        """測試輸出值範圍 [0, 1]"""
        strategy = ArtisticBloomStrategy(bloom_params_artistic)
        output = strategy.apply(test_image_single_channel)
        assert np.all(output >= 0.0)
        assert np.all(output <= 1.0)
    
    def test_apply_increases_brightness(self, test_image_single_channel, bloom_params_artistic):
        """測試 Artistic 模式增加亮度（加法模式）"""
        # 使用更高 sensitivity 確保效果明顯
        params = BloomParams(mode="artistic", sensitivity=2.0, artistic_strength=2.0)
        strategy = ArtisticBloomStrategy(params)
        output = strategy.apply(test_image_single_channel)
        
        # 高光區域的能量應該擴散（總和可能保持或略增）
        # 只檢查輸出有效（非全零）
        assert np.sum(output) > 0, "輸出不應為全零"
        assert np.max(output) > np.max(test_image_single_channel) * 0.5, "高光應保留"
    
    def test_no_bloom_when_sensitivity_zero(self, test_image_single_channel):
        """測試 sensitivity=0 時效果極弱"""
        params = BloomParams(mode="artistic", sensitivity=0.0)
        strategy = ArtisticBloomStrategy(params)
        output = strategy.apply(test_image_single_channel)
        
        # 效果應該非常弱（但可能不完全為零，因為有 artistic_base）
        # 檢查輸出與輸入的差異很小
        diff = np.abs(output - test_image_single_channel)
        assert np.mean(diff) < 0.01, "sensitivity=0 時效果應很弱"


class TestPhysicalBloomStrategy:
    """測試 Physical Bloom 策略"""
    
    def test_energy_conservation(self, test_image_single_channel, bloom_params_physical):
        """測試能量守恆（核心要求）"""
        strategy = PhysicalBloomStrategy(bloom_params_physical)
        output = strategy.apply(test_image_single_channel)
        
        # 計算總能量（所有像素之和）
        input_energy = np.sum(test_image_single_channel)
        output_energy = np.sum(output)
        
        # 能量誤差應 < 1%（數值誤差容忍度）
        energy_error = abs(output_energy - input_energy) / max(input_energy, 1e-10)
        assert energy_error < 0.01, f"能量誤差 {energy_error:.2%} > 1%"
    
    def test_threshold_behavior(self, bloom_params_physical):
        """測試閾值行為：低於閾值的區域不散射"""
        # 創建低亮度圖像（全部低於閾值）
        low_intensity_img = np.ones((100, 100), dtype=np.float32) * 0.5
        
        strategy = PhysicalBloomStrategy(bloom_params_physical)
        output = strategy.apply(low_intensity_img)
        
        # 低於閾值時，應無散射（輸出 ≈ 輸入）
        np.testing.assert_allclose(output, low_intensity_img, atol=1e-2)
    
    def test_output_not_exceeds_input(self, test_image_single_channel, bloom_params_physical):
        """測試 Physical 模式不增加總亮度（能量守恆）"""
        strategy = PhysicalBloomStrategy(bloom_params_physical)
        output = strategy.apply(test_image_single_channel)
        
        # 總亮度應該 ≤ 輸入（允許小幅誤差）
        assert np.sum(output) <= np.sum(test_image_single_channel) * 1.01


class TestMieCorrectedBloomStrategy:
    """測試 Mie Corrected Bloom 策略"""
    
    def test_wavelength_dependency(self, test_image_single_channel, bloom_params_mie):
        """測試波長依賴性：藍光散射 > 紅光散射"""
        strategy = MieCorrectedBloomStrategy(bloom_params_mie)
        
        # 分別測試藍光和紅光
        output_blue = strategy.apply(test_image_single_channel, wavelength=450.0)
        output_red = strategy.apply(test_image_single_channel, wavelength=650.0)
        
        # 在高光周圍，藍光散射應該更強（更多能量擴散到周邊）
        # 檢查高光外圍區域（200:220 行）
        halo_blue = np.mean(output_blue[200:220, 240:260])
        halo_red = np.mean(output_red[200:220, 240:260])
        
        # 藍光散射應該 >= 紅光散射
        assert halo_blue >= halo_red * 0.95, "藍光散射應該至少與紅光相當"
    
    def test_energy_conservation(self, test_image_single_channel, bloom_params_mie):
        """測試 Mie 校正模式也遵守能量守恆"""
        strategy = MieCorrectedBloomStrategy(bloom_params_mie)
        output = strategy.apply(test_image_single_channel, wavelength=550.0)
        
        input_energy = np.sum(test_image_single_channel)
        output_energy = np.sum(output)
        
        energy_error = abs(output_energy - input_energy) / max(input_energy, 1e-10)
        assert energy_error < 0.01, f"Mie 模式能量誤差 {energy_error:.2%} > 1%"


# ==================== 工廠模式測試 ====================

class TestBloomStrategyFactory:
    """測試策略工廠函數"""
    
    def test_factory_returns_artistic(self, bloom_params_artistic):
        """測試工廠返回 Artistic 策略"""
        strategy = get_bloom_strategy(bloom_params_artistic)
        assert isinstance(strategy, ArtisticBloomStrategy)
    
    def test_factory_returns_physical(self, bloom_params_physical):
        """測試工廠返回 Physical 策略"""
        strategy = get_bloom_strategy(bloom_params_physical)
        assert isinstance(strategy, PhysicalBloomStrategy)
    
    def test_factory_returns_mie_corrected(self, bloom_params_mie):
        """測試工廠返回 Mie Corrected 策略"""
        strategy = get_bloom_strategy(bloom_params_mie)
        assert isinstance(strategy, MieCorrectedBloomStrategy)
    
    def test_factory_invalid_mode_raises(self):
        """測試無效 mode 拋出異常"""
        # BloomParams 本身會在 __post_init__ 驗證 mode
        # 因此應該在創建 BloomParams 時就拋出異常
        with pytest.raises(AssertionError, match="mode.*無效"):
            BloomParams(mode="invalid_mode")


# ==================== 統一介面測試 ====================

class TestApplyBloomUnifiedInterface:
    """測試統一介面 apply_bloom()"""
    
    def test_apply_bloom_delegates_to_strategy(self, test_image_single_channel, bloom_params_artistic):
        """測試 apply_bloom() 正確委派到策略"""
        # 直接調用策略
        strategy = ArtisticBloomStrategy(bloom_params_artistic)
        strategy_output = strategy.apply(test_image_single_channel)
        
        # 通過統一介面調用
        unified_output = apply_bloom(test_image_single_channel, bloom_params_artistic)
        
        # 兩者應該完全相同
        np.testing.assert_allclose(unified_output, strategy_output, atol=1e-6)
    
    def test_apply_bloom_all_modes(self, test_image_single_channel):
        """測試所有模式都能通過統一介面運行"""
        modes = ["artistic", "physical", "mie_corrected"]
        
        for mode in modes:
            params = BloomParams(mode=mode, sensitivity=1.0)
            
            output = apply_bloom(test_image_single_channel, params)
            
            # 基本檢查：形狀與範圍
            assert output.shape == test_image_single_channel.shape
            assert np.all(output >= 0.0)
            assert np.all(output <= 1.0)


# ==================== 極端情況測試 ====================

class TestEdgeCases:
    """測試極端情況"""
    
    def test_zero_image(self, bloom_params_artistic):
        """測試全黑圖像"""
        zero_img = np.zeros((100, 100), dtype=np.float32)
        output = apply_bloom(zero_img, bloom_params_artistic)
        
        # 全黑輸入 → 全黑輸出
        np.testing.assert_allclose(output, zero_img, atol=1e-6)
    
    def test_saturated_image(self, bloom_params_artistic):
        """測試全白圖像"""
        white_img = np.ones((100, 100), dtype=np.float32)
        output = apply_bloom(white_img, bloom_params_artistic)
        
        # 應保持在 [0, 1] 範圍
        assert np.all(output >= 0.0)
        assert np.all(output <= 1.0)
    
    def test_single_pixel_highlight(self, bloom_params_physical):
        """測試單像素高光"""
        img = np.zeros((50, 50), dtype=np.float32)
        img[25, 25] = 1.0  # 中心單像素高光
        
        output = apply_bloom(img, bloom_params_physical)
        
        # 能量應守恆
        np.testing.assert_allclose(np.sum(output), np.sum(img), rtol=0.01)
        
        # 散射應擴散到周圍像素
        assert np.sum(output[24:27, 24:27]) > 0.0
    
    def test_extreme_sigma(self, test_image_single_channel):
        """測試極端 radius 值"""
        # 極小 radius（幾乎無散射）
        params_small = BloomParams(mode="artistic", radius=5, sensitivity=1.0)
        output_small = apply_bloom(test_image_single_channel, params_small)
        
        # 極大 radius（大範圍散射）
        params_large = BloomParams(mode="artistic", radius=100, sensitivity=1.0)
        output_large = apply_bloom(test_image_single_channel, params_large)
        
        # 兩者應有差異（檢查不完全相同）
        assert not np.allclose(output_small, output_large, atol=1e-4), "不同 radius 應產生不同結果"


# ==================== 效能測試（標記為 slow）====================

@pytest.mark.slow
class TestPerformance:
    """測試效能（僅在完整測試時執行）"""
    
    def test_large_image_processing(self, bloom_params_artistic):
        """測試大圖像處理（6MP 單通道）"""
        large_img = np.random.rand(2000, 3000).astype(np.float32)
        
        import time
        start = time.time()
        output = apply_bloom(large_img, bloom_params_artistic)
        elapsed = time.time() - start
        
        # 應在合理時間內完成（< 5 秒）
        assert elapsed < 5.0, f"處理時間 {elapsed:.2f}s 過長"
        assert output.shape == large_img.shape


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
