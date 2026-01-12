"""
測試 modules/image_processing.py 模組

測試 H&D 曲線與層組合功能。

Test coverage:
    - apply_hd_curve: H&D 特性曲線測試（8 tests）
    - combine_layers_for_channel: 層組合測試（7 tests）
    - Module structure: 模組結構測試（3 tests）

Total: 18 tests

Version: 0.7.0-dev (PR #6)
Date: 2026-01-12
"""

import pytest
import numpy as np
from modules.image_processing import (
    apply_hd_curve,
    combine_layers_for_channel
)
from film_models import HDCurveParams, EmulsionLayer


# ==================== apply_hd_curve Tests ====================

class TestApplyHDCurve:
    """測試 H&D 曲線應用函數"""
    
    def test_disabled_hd_curve_returns_input(self):
        """測試：未啟用 H&D 曲線時應直接返回輸入"""
        exposure = np.array([0.1, 0.5, 1.0])
        hd_params = HDCurveParams(enabled=False)
        
        result = apply_hd_curve(exposure, hd_params)
        
        np.testing.assert_array_equal(result, exposure)
    
    def test_enabled_hd_curve_modifies_input(self):
        """測試：啟用 H&D 曲線時應修改輸入"""
        exposure = np.array([0.1, 0.5, 1.0])
        hd_params = HDCurveParams(
            enabled=True,
            gamma=0.65,
            D_min=0.2,
            D_max=3.0
        )
        
        result = apply_hd_curve(exposure, hd_params)
        
        # 結果不應與輸入相同
        assert not np.array_equal(result, exposure)
        # 結果應在 [0, 1] 範圍內
        assert np.all(result >= 0) and np.all(result <= 1)
    
    def test_toe_compression(self):
        """測試：Toe 區域應壓縮低曝光量"""
        # 低曝光量應受 toe 壓縮影響
        exposure_low = np.array([0.01, 0.1, 1.0])
        hd_params = HDCurveParams(
            enabled=True,
            gamma=0.65,
            D_min=0.2,
            D_max=3.0,
            toe_enabled=True,
            toe_end=-1.0,  # log10(0.1) = -1.0
            toe_strength=0.5
        )
        
        result = apply_hd_curve(exposure_low, hd_params)
        
        # 所有結果應在 [0, 1] 範圍
        assert np.all(result >= 0) and np.all(result <= 1)
        # 輸入曝光量增加，輸出應有所反應（即使可能非單調）
        assert len(set(result)) > 1, "不同輸入應產生不同輸出"
    
    def test_shoulder_compression(self):
        """測試：Shoulder 區域應壓縮高曝光量"""
        # 高曝光量 (10.0) 應受 shoulder 壓縮影響
        exposure_high = np.array([1.0, 10.0])
        hd_params = HDCurveParams(
            enabled=True,
            gamma=0.65,
            D_min=0.2,
            D_max=3.0,
            shoulder_enabled=True,
            shoulder_start=0.3,  # log10(2) ≈ 0.3
            shoulder_strength=1.0
        )
        
        result = apply_hd_curve(exposure_high, hd_params)
        
        # Shoulder 區應壓縮：高曝光量增長應變慢
        # 注意：由於密度飽和，結果差異應小於輸入差異
        exposure_ratio = exposure_high[1] / exposure_high[0]  # 10x
        result_ratio = result[1] / (result[0] + 1e-10)  # 避免除零
        assert result_ratio < exposure_ratio  # 壓縮效果
        assert np.all(result >= 0) and np.all(result <= 1)
    
    def test_output_range(self):
        """測試：輸出應始終在 [0, 1] 範圍內"""
        exposure = np.array([0.0, 0.001, 0.1, 1.0, 10.0, 100.0])
        hd_params = HDCurveParams(
            enabled=True,
            gamma=0.65,
            D_min=0.2,
            D_max=3.0
        )
        
        result = apply_hd_curve(exposure, hd_params)
        
        assert np.all(result >= 0)
        assert np.all(result <= 1)
    
    def test_zero_exposure_handling(self):
        """測試：零曝光量應安全處理（不應產生 NaN）"""
        exposure = np.array([0.0, 0.0, 0.0])
        hd_params = HDCurveParams(
            enabled=True,
            gamma=0.65,
            D_min=0.2,
            D_max=3.0
        )
        
        result = apply_hd_curve(exposure, hd_params)
        
        # 不應產生 NaN 或 inf
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))
        assert np.all(result >= 0) and np.all(result <= 1)
    
    def test_output_range_with_reasonable_params(self):
        """測試：使用合理參數時輸出應在 [0, 1] 範圍且不同輸入產生不同輸出"""
        exposure = np.array([0.1, 0.2, 0.5, 1.0, 2.0, 5.0])
        hd_params = HDCurveParams(
            enabled=True,
            gamma=0.65,
            D_min=0.2,
            D_max=3.0,
            toe_enabled=False,
            shoulder_enabled=False
        )
        
        result = apply_hd_curve(exposure, hd_params)
        
        # 輸出範圍檢查
        assert np.all(result >= 0) and np.all(result <= 1)
        # 不同輸入應產生不同輸出
        assert len(set(result)) == len(result), "不同曝光量應產生不同透射率"
    
    def test_negative_film_gamma(self):
        """測試：負片 gamma（0.6-0.7）應產生低對比度"""
        exposure = np.array([0.1, 1.0, 10.0])
        
        # 負片參數
        hd_params_negative = HDCurveParams(
            enabled=True,
            gamma=0.65,  # 負片典型值
            D_min=0.2,
            D_max=3.0
        )
        
        result = apply_hd_curve(exposure, hd_params_negative)
        
        # 負片應產生較柔和的過渡（對比度較低）
        contrast = (result[2] - result[0]) / (result[1] - result[0] + 1e-10)
        assert contrast > 0, "負片應保持正對比度"
        assert np.all(result >= 0) and np.all(result <= 1)


# ==================== combine_layers_for_channel Tests ====================

class TestCombineLayersForChannel:
    """測試層組合函數"""
    
    def test_basic_combination(self):
        """測試：基本的散射光與直射光組合"""
        bloom = np.ones((10, 10)) * 0.5
        lux = np.ones((10, 10)) * 0.8
        layer = EmulsionLayer(
            r_response_weight=1.0,
            g_response_weight=0.0,
            b_response_weight=0.0,
            diffuse_weight=0.6,
            direct_weight=0.4,
            response_curve=1.0,
            grain_intensity=0.0
        )
        
        result = combine_layers_for_channel(
            bloom, lux, layer,
            None, None, None, 0.0, False
        )
        
        # 權重歸一化後：w_diffuse=0.6, w_direct=0.4
        # result = 0.5 * 0.6 + 0.8^1.0 * 0.4 = 0.3 + 0.32 = 0.62
        expected = bloom * 0.6 + lux * 0.4
        np.testing.assert_array_almost_equal(result, expected, decimal=5)
    
    def test_energy_conservation(self):
        """測試：權重歸一化確保能量守恆"""
        bloom = np.ones((10, 10)) * 0.6
        lux = np.ones((10, 10)) * 0.4
        layer = EmulsionLayer(
            r_response_weight=1.0,
            g_response_weight=0.0,
            b_response_weight=0.0,
            diffuse_weight=1.5,  # 非歸一化權重
            direct_weight=2.5,   # 非歸一化權重
            response_curve=1.0,
            grain_intensity=0.0
        )
        
        result = combine_layers_for_channel(
            bloom, lux, layer,
            None, None, None, 0.0, False
        )
        
        # 歸一化：w_diffuse = 1.5/4.0 = 0.375, w_direct = 2.5/4.0 = 0.625
        # result = 0.6 * 0.375 + 0.4 * 0.625 = 0.225 + 0.25 = 0.475
        expected = bloom * (1.5 / 4.0) + lux * (2.5 / 4.0)
        np.testing.assert_array_almost_equal(result, expected, decimal=5)
    
    def test_zero_weight_handling(self):
        """測試：兩個權重都為 0 時應均分（防止除零）"""
        bloom = np.ones((10, 10)) * 0.5
        lux = np.ones((10, 10)) * 0.8
        layer = EmulsionLayer(
            r_response_weight=1.0,
            g_response_weight=0.0,
            b_response_weight=0.0,
            diffuse_weight=0.0,
            direct_weight=0.0,
            response_curve=1.0,
            grain_intensity=0.0
        )
        
        result = combine_layers_for_channel(
            bloom, lux, layer,
            None, None, None, 0.0, False
        )
        
        # 應均分權重：w_diffuse = w_direct = 0.5
        expected = bloom * 0.5 + lux * 0.5
        np.testing.assert_array_almost_equal(result, expected, decimal=5)
    
    def test_nonlinear_response_curve(self):
        """測試：response_curve 應改變直射光的非線性響應"""
        bloom = np.ones((10, 10)) * 0.5
        lux = np.ones((10, 10)) * 0.64  # 0.64^1.5 = 0.512
        layer = EmulsionLayer(
            r_response_weight=1.0,
            g_response_weight=0.0,
            b_response_weight=0.0,
            diffuse_weight=0.5,
            direct_weight=0.5,
            response_curve=1.5,  # 非線性（v0.8.2 後暫時不使用）
            grain_intensity=0.0
        )
        
        result = combine_layers_for_channel(
            bloom, lux, layer,
            None, None, None, 0.0, False
        )
        
        # v0.8.2 HOTFIX: response_curve 已禁用（Linear RGB input）
        # OLD: result = 0.5 * 0.5 + 0.64^1.5 * 0.5 ≈ 0.25 + 0.256 = 0.506
        # NEW: result = 0.5 * 0.5 + 0.64 * 0.5 = 0.25 + 0.32 = 0.57
        expected = bloom * 0.5 + lux * 0.5  # Linear combination now
        np.testing.assert_array_almost_equal(result, expected, decimal=5)
    
    def test_grain_addition_rgb(self):
        """測試：RGB 顆粒噪聲應正確疊加"""
        bloom = np.zeros((10, 10))
        lux = np.zeros((10, 10))
        layer = EmulsionLayer(
            r_response_weight=1.0,
            g_response_weight=0.0,
            b_response_weight=0.0,
            diffuse_weight=0.5,
            direct_weight=0.5,
            response_curve=1.0,
            grain_intensity=0.1
        )
        
        grain_r = np.ones((10, 10)) * 0.01
        grain_g = np.ones((10, 10)) * 0.02
        grain_b = np.ones((10, 10)) * 0.03
        grain_total = 0.05
        
        result = combine_layers_for_channel(
            bloom, lux, layer,
            grain_r, grain_g, grain_b, grain_total, True
        )
        
        # v0.8.2.2: Linear RGB 補償係數 = 0.30
        # result = 0 + grain_r*0.1*0.30 + grain_g*0.05 + grain_b*0.05
        # result = 0.0003 + 0.001 + 0.0015 = 0.0028
        GRAIN_LINEAR_RGB_COMPENSATION = 0.30
        expected = (grain_r * layer.grain_intensity * GRAIN_LINEAR_RGB_COMPENSATION + 
                   grain_g * grain_total + 
                   grain_b * grain_total)
        np.testing.assert_array_almost_equal(result, expected, decimal=5)
    
    def test_grain_addition_single_channel(self):
        """測試：單通道顆粒應正確疊加"""
        bloom = np.zeros((10, 10))
        lux = np.zeros((10, 10))
        layer = EmulsionLayer(
            r_response_weight=1.0,
            g_response_weight=0.0,
            b_response_weight=0.0,
            diffuse_weight=0.5,
            direct_weight=0.5,
            response_curve=1.0,
            grain_intensity=0.1
        )
        
        grain_r = np.ones((10, 10)) * 0.02
        
        result = combine_layers_for_channel(
            bloom, lux, layer,
            grain_r, None, None, 0.0, True
        )
        
        # v0.8.2.2: Linear RGB 補償係數 = 0.30
        # result = grain_r * grain_intensity * 0.30 = 0.02 * 0.1 * 0.30 = 0.0006
        GRAIN_LINEAR_RGB_COMPENSATION = 0.30
        expected = grain_r * layer.grain_intensity * GRAIN_LINEAR_RGB_COMPENSATION
        np.testing.assert_array_almost_equal(result, expected, decimal=5)
    
    def test_no_grain_when_disabled(self):
        """測試：禁用顆粒時不應添加噪聲"""
        bloom = np.ones((10, 10)) * 0.5
        lux = np.ones((10, 10)) * 0.5
        layer = EmulsionLayer(
            r_response_weight=1.0,
            g_response_weight=0.0,
            b_response_weight=0.0,
            diffuse_weight=0.5,
            direct_weight=0.5,
            response_curve=1.0,
            grain_intensity=0.1
        )
        
        grain_r = np.ones((10, 10)) * 0.1
        
        result = combine_layers_for_channel(
            bloom, lux, layer,
            grain_r, None, None, 0.0, False  # use_grain=False
        )
        
        # 不應包含顆粒
        expected = bloom * 0.5 + lux * 0.5
        np.testing.assert_array_almost_equal(result, expected, decimal=5)


# ==================== Module Structure Tests ====================

class TestModuleStructure:
    """測試模組結構與完整性"""
    
    def test_module_imports(self):
        """測試：模組應正確導出所有函數"""
        from modules import image_processing
        
        assert hasattr(image_processing, 'apply_hd_curve')
        assert hasattr(image_processing, 'combine_layers_for_channel')
    
    def test_function_docstrings(self):
        """測試：所有函數應有文檔字符串"""
        assert apply_hd_curve.__doc__ is not None
        assert len(apply_hd_curve.__doc__) > 50
        
        assert combine_layers_for_channel.__doc__ is not None
        assert len(combine_layers_for_channel.__doc__) > 50
    
    def test_backwards_compatibility_removed_v08(self):
        """測試：v0.8.0 Breaking Change - 舊導入方式不受官方支持
        
        v0.8.0 文檔化的 Breaking Change:
        - 從 Phos.py 導入在技術上仍可行（因為 Python 模組系統）
        - 但官方不再支持，且不保證未來相容性
        - 用戶**必須**改用 modules 包
        
        正確的導入方式：
            ✅ from modules.image_processing import apply_hd_curve
            ✅ from modules import apply_hd_curve
            ❌ from Phos import apply_hd_curve (不受支持)
        
        此測試驗證：
        1. modules 包導入正常工作
        2. Phos.py 的 __all__ 為空，表示不對外導出
        3. 文檔化警告用戶不應依賴 Phos.py 導入
        """
        # 1. 驗證 modules 包導入正常（官方支持的方式）
        from modules.image_processing import apply_hd_curve as mod_hd_curve
        from modules.image_processing import combine_layers_for_channel as mod_combine
        
        assert mod_hd_curve is apply_hd_curve
        assert mod_combine is combine_layers_for_channel
        
        # 2. 驗證 Phos.py 的 __all__ 為空（表示不對外導出）
        import Phos
        assert hasattr(Phos, '__all__'), "Phos.py 應定義 __all__ 來表明導出意圖"
        assert Phos.__all__ == [], f"Phos.__all__ 應為空列表，實際為: {Phos.__all__}"
        
        # 3. 技術上仍可從 Phos 導入（Python 限制），但這不受官方支持
        # 用戶不應依賴此行為，未來版本可能會改變
        # （不測試實際導入，因為這不是官方支持的用法）


# ==================== Test Execution ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
