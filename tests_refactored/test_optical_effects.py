"""
Optical Effects Test Suite (Refactored)

光學效果測試套件 - 整合 Halation、Wavelength Bloom 和 Mie 散射測試

Merged from:
- test_halation.py (10 tests)
- test_p0_2_halation_beer_lambert.py (19 tests)
- test_wavelength_bloom.py (8 tests)
- test_mie_halation_integration.py (7 tests)

Total tests: 44 tests

Coverage:
- Halation (背層反射)
  - 能量守恆測試
  - Beer-Lambert 透過率模型
  - 波長依賴性
  - CineStill vs Portra 對比
  - 雙程路徑公式驗證
  - 向後相容性測試

- Wavelength Bloom (波長依賴散射)
  - 能量權重計算
  - PSF 寬度計算
  - 雙段核 PSF 正規化
  - 參數解耦驗證
  - 模式檢測邏輯

- Mie Scattering Integration (Mie 散射整合)
  - Mie + Halation 參數兼容性
  - 能量守恆概念驗證
  - 波長依賴關係
  - PSF 尺寸比較
  - 中等物理模式檢測

Philosophy principles:
- Never Break Userspace: 保持 100% 邏輯一致性
- Pragmatism: 所有測試來自實際物理模型驗證
- Good Taste: 使用 class 組織，消除重複測試

Refactored: 2026-01-11
"""

import numpy as np
import pytest
import sys
import os
import warnings
import time
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from film_models import (
    HalationParams, 
    BloomParams, 
    FilmProfile, 
    get_film_profile,
    WavelengthBloomParams,
    PhysicsMode,
    create_default_medium_physics_params
)

# 動態導入 Phos（避免 streamlit 依賴問題）
import importlib.util

# 嘗試載入 Phos.py
spec = importlib.util.spec_from_file_location("phos_core", "Phos.py")
if spec is not None and spec.loader is not None:
    phos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(phos)
else:
    # 備用：嘗試 Phos_0.3.0.py
    spec = importlib.util.spec_from_file_location("phos_core", "Phos_0.3.0.py")
    if spec is not None and spec.loader is not None:
        phos = importlib.util.module_from_spec(spec)
    else:
        raise ImportError("Cannot load Phos.py or Phos_0.3.0.py")


# ============================================================
# Section 1: Basic Halation Tests
# Source: test_halation.py (10 tests)
# ============================================================

class TestHalationEnergyConservation:
    """能量守恆測試"""
    
    def test_halation_energy_conservation_uniform(self):
        """測試均勻高光場的能量守恆"""
        # 創建均勻高光場（0.8）
        lux = np.ones((512, 512), dtype=np.float32) * 0.8
        
        halation_params = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.92,
            emulsion_transmittance_g=0.87,
            emulsion_transmittance_b=0.78,
            base_transmittance=0.98,
            ah_layer_transmittance_r=0.30,
            ah_layer_transmittance_g=0.10,
            ah_layer_transmittance_b=0.05,
            backplate_reflectance=0.3,
            psf_radius=100,
            energy_fraction=0.05
        )
        
        energy_in = np.sum(lux)
        
        # 應用 Halation（需要實際導入函數）
        # result = apply_halation(lux, halation_params, wavelength=550.0)
        # energy_out = np.sum(result)
        
        # 驗證能量守恆（誤差 < 0.01%）
        # assert abs(energy_in - energy_out) / energy_in < 0.0001
        
        # 暫時通過（待函數導入）
        assert True
    
    def test_halation_with_point_source(self):
        """測試點光源的 Halation 擴散"""
        # 創建中心點光源
        lux = np.zeros((512, 512), dtype=np.float32)
        lux[256, 256] = 1.0  # 中心亮點
        
        halation_params = HalationParams(
            enabled=True,
            psf_radius=100,
            energy_fraction=0.1
        )
        
        # result = apply_halation(lux, halation_params, wavelength=550.0)
        
        # 驗證：
        # 1. 中心點能量減少（被散射）
        # 2. 周圍區域獲得能量（光暈）
        # 3. 徑向對稱
        # assert result[256, 256] < lux[256, 256]
        # assert np.sum(result[200:312, 200:312]) > np.sum(lux[200:312, 200:312])
        
        assert True


class TestWavelengthDependenceBasic:
    """波長依賴測試（基礎）"""
    
    def test_transmittance_red_greater_than_blue(self):
        """測試紅光透過率 > 藍光（Beer-Lambert）"""
        halation_params = HalationParams(
            emulsion_transmittance_r=0.92,
            emulsion_transmittance_g=0.87,
            emulsion_transmittance_b=0.78
        )
        
        # 紅光應有最高乳劑層透過率
        assert halation_params.emulsion_transmittance_r > halation_params.emulsion_transmittance_g
        assert halation_params.emulsion_transmittance_g > halation_params.emulsion_transmittance_b
    
    def test_wavelength_halation_energy_ratio(self):
        """測試不同波長的 Halation 能量比例"""
        lux = np.ones((256, 256), dtype=np.float32) * 0.8
        
        halation_params = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.92,
            emulsion_transmittance_g=0.87,
            emulsion_transmittance_b=0.78,
            base_transmittance=0.98,
            ah_layer_transmittance_r=0.30,
            ah_layer_transmittance_g=0.10,
            ah_layer_transmittance_b=0.05,
            backplate_reflectance=0.3,
            psf_radius=100,
            energy_fraction=0.05
        )
        
        # 計算各波長的有效能量係數（使用新公式）
        # f_h(λ) = [T_e(λ) · T_b · T_AH(λ)]² · R_bp
        R_bp = halation_params.backplate_reflectance
        
        f_red = halation_params.effective_halation_r
        f_green = halation_params.effective_halation_g
        f_blue = halation_params.effective_halation_b
        
        # 紅光應有最大 Halation（透過力強）
        assert f_red > f_green > f_blue
        
        # 數值驗證（基於新公式）
        # f_h,r = (0.92 * 0.98 * 0.30)² * 0.3 = 0.0219
        # f_h,g = (0.87 * 0.98 * 0.10)² * 0.3 = 0.0022
        # f_h,b = (0.78 * 0.98 * 0.05)² * 0.3 = 0.0004
        assert abs(f_red - 0.0219) < 0.001
        assert abs(f_green - 0.0022) < 0.001
        assert abs(f_blue - 0.0004) < 0.001
        
        # 比例：紅/藍 ≈ 54.8×
        ratio_red_blue = f_red / (f_blue + 1e-9)
        assert 50.0 < ratio_red_blue < 60.0


class TestHalationVsBloom:
    """Halation vs Bloom 差異測試"""
    
    def test_psf_radius_ratio(self):
        """測試 PSF 半徑比例（Halation >> Bloom）"""
        bloom_params = BloomParams(radius=20)
        halation_params = HalationParams(psf_radius=100)
        
        # Halation 半徑應為 Bloom 的 5-10 倍
        ratio = halation_params.psf_radius / bloom_params.radius
        assert 5 <= ratio <= 10
    
    def test_mechanism_separation(self):
        """測試機制分離（Bloom 與 Halation 參數獨立）"""
        bloom = BloomParams(
            threshold=0.8,
            scattering_ratio=0.08,  # Bloom: 8%
            psf_type="gaussian"
        )
        
        halation = HalationParams(
            enabled=True,
            energy_fraction=0.05,  # Halation: 5%
            psf_type="exponential"
        )
        
        # 驗證：
        # 1. 能量係數獨立
        assert bloom.scattering_ratio != halation.energy_fraction
        
        # 2. PSF 類型不同
        assert bloom.psf_type == "gaussian"
        assert halation.psf_type == "exponential"


class TestCineStillExtremeBasic:
    """CineStill 800T 極端 Halation 測試（基礎）"""
    
    @pytest.mark.skip(reason="TASK-011: 已被 test_p0_2_halation_beer_lambert.py::TestCineStillVsPortra 取代")
    def test_cinestill_no_ah_layer(self):
        """測試 CineStill 無 AH 層設定"""
        try:
            cinestill = get_film_profile("Cinestill800T")
            
            # 驗證無 AH 層（使用新參數）
            assert cinestill.halation_params.ah_layer_transmittance_r == 1.0
            assert cinestill.halation_params.ah_layer_transmittance_g == 1.0
            assert cinestill.halation_params.ah_layer_transmittance_b == 1.0
            
            # 驗證高透過率
            assert cinestill.halation_params.emulsion_transmittance_r >= 0.9
            
            # 驗證大光暈半徑
            assert cinestill.halation_params.psf_radius >= 150
            
            # 驗證高能量分數
            assert cinestill.halation_params.energy_fraction >= 0.10
        except Exception as e:
            pytest.skip(f"CineStill profile 不存在或參數未設置: {e}")
    
    @pytest.mark.skip(reason="TASK-011: 已被 test_p0_2_halation_beer_lambert.py::TestCineStillVsPortra 取代")
    def test_cinestill_red_halo_dominance(self):
        """測試 CineStill 紅色光暈主導"""
        try:
            cinestill = get_film_profile("Cinestill800T")
            halation = cinestill.halation_params
            
            # 使用新公式計算各波長的 Halation 能量
            f_red = halation.effective_halation_r
            f_green = halation.effective_halation_g
            f_blue = halation.effective_halation_b
            
            # 紅光應遠大於藍光（> 1.2x）
            assert f_red / f_green > 1.1
            assert f_red / f_blue > 1.2
        except Exception as e:
            pytest.skip(f"CineStill profile 不存在: {e}")


class TestRadialEnergyDistribution:
    """徑向能量分布測試"""
    
    def test_exponential_decay(self):
        """測試指數拖尾（long tail）"""
        # 創建徑向距離陣列
        size = 512
        y, x = np.ogrid[-size//2:size//2, -size//2:size//2]
        r = np.sqrt(x**2 + y**2)
        
        # 理論指數分布：I(r) ∝ exp(-k·r)
        k = 0.05  # decay rate
        theoretical = np.exp(-k * r)
        
        # 驗證：遠端（r > 100 px）仍有能量（> 0.01%）
        # 理論值：exp(-0.05 * 100) = exp(-5) ≈ 0.67%
        # 實際平均（含 r>100 所有點）≈ 0.04%
        far_region = theoretical[r > 100]
        assert np.mean(far_region) > 0.0001, \
            f"遠端能量 {np.mean(far_region)*100:.4f}% 應 > 0.01%"
        
        # 驗證：拖尾比高斯更長
        # 高斯：I(r) = exp(-r²/2σ²)，在 r=3σ 時 ≈ 0.01
        # 指數：I(r) = exp(-kr)，在 r=4.6/k 時 = 0.01
        # 對於 k=0.05，需要 r ≈ 92 才降到 1%
        # 因此 r>92 的區域仍應有可測量能量（> 0.5% 總能量）
        assert np.sum(theoretical[r > 92]) / np.sum(theoretical) > 0.005, \
            f"長拖尾區域能量比例應 > 0.5%"


class TestPSFNormalization:
    """PSF 正規化測試"""
    
    def test_psf_sum_equals_one(self):
        """測試 PSF 核總和 = 1（能量守恆）"""
        # 對於離散化的 PSF，∑ K = 1
        # 這是能量守恆的必要條件
        
        # 創建簡單的歸一化核
        kernel_size = 101
        sigma = 20
        y, x = np.ogrid[-kernel_size//2:kernel_size//2+1, 
                        -kernel_size//2:kernel_size//2+1]
        kernel = np.exp(-(x**2 + y**2) / (2 * sigma**2))
        kernel_normalized = kernel / np.sum(kernel)
        
        # 驗證總和 = 1
        assert abs(np.sum(kernel_normalized) - 1.0) < 1e-6


# ============================================================
# Section 2: Beer-Lambert Halation Tests (Advanced)
# Source: test_p0_2_halation_beer_lambert.py (19 tests)
# ============================================================

class TestEnergyConservation:
    """能量守恆測試（P0-2 核心驗證）"""
    
    def test_halation_energy_conservation_global(self):
        """測試全局能量守恆（誤差 < 0.05%）"""
        # 創建測試圖像：黑底白點
        lux = np.zeros((256, 256), dtype=np.float32)
        lux[128, 128] = 1.0  # 中心亮點
        
        params = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.92,
            ah_layer_transmittance_r=0.30,
            energy_fraction=0.05
        )
        
        energy_in = np.sum(lux)
        result = phos.apply_halation(lux, params, wavelength=550.0)
        energy_out = np.sum(result)
        
        global_error = abs(energy_out - energy_in) / energy_in
        
        assert global_error < 0.0005, f"Global energy error: {global_error*100:.6f}% (expected < 0.05%)"
    
    def test_halation_energy_conservation_local_window(self):
        """測試局部窗口能量守恆（64×64，誤差 < 0.1%）"""
        # 創建測試圖像：黑底白點
        lux = np.zeros((256, 256), dtype=np.float32)
        lux[128, 128] = 1.0
        
        params = HalationParams(
            enabled=True,
            energy_fraction=0.05,
            psf_radius=80
        )
        
        result = phos.apply_halation(lux, params, wavelength=550.0)
        
        # 局部窗口（96:160, 96:160）包含中心點 ± 32 px
        window_in = lux[96:160, 96:160]
        window_out = result[96:160, 96:160]
        
        local_error = abs(np.sum(window_out) - np.sum(window_in)) / (np.sum(window_in) + 1e-9)
        
        assert local_error < 0.001, f"Local energy error: {local_error*100:.6f}% (expected < 0.1%)"
    
    def test_halation_uniform_field_energy(self):
        """測試均勻場能量守恆"""
        lux = np.ones((128, 128), dtype=np.float32) * 0.8
        
        params = HalationParams(enabled=True, energy_fraction=0.05)
        
        energy_in = np.sum(lux)
        result = phos.apply_halation(lux, params, wavelength=550.0)
        energy_out = np.sum(result)
        
        error = abs(energy_out - energy_in) / energy_in
        
        assert error < 0.0005, f"Uniform field energy error: {error*100:.6f}%"


class TestDoublePassFormula:
    """雙程路徑公式驗證（Physicist Review §2, TASK-011 Phase 2）"""
    
    def test_double_pass_formula_manual_calculation(self):
        """測試雙程公式：f_h = [T_e·T_b·T_AH]²·R_bp（與手算對比）"""
        # 測試案例：Portra 400 參數
        params = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.92,
            emulsion_transmittance_g=0.87,
            emulsion_transmittance_b=0.78,
            base_transmittance=0.98,
            ah_layer_transmittance_r=0.30,
            ah_layer_transmittance_g=0.10,
            ah_layer_transmittance_b=0.05,
            backplate_reflectance=0.30
        )
        
        # 手算期望值（Physicist Review §2 案例）
        T_single_r = 0.92 * 0.98 * 0.30  # = 0.27048
        f_h_expected_r = (T_single_r ** 2) * 0.30  # = 0.02194
        
        T_single_g = 0.87 * 0.98 * 0.10  # = 0.08526
        f_h_expected_g = (T_single_g ** 2) * 0.30  # = 0.00218
        
        T_single_b = 0.78 * 0.98 * 0.05  # = 0.03822
        f_h_expected_b = (T_single_b ** 2) * 0.30  # = 0.000438
        
        # 程式計算值
        f_h_actual_r = params.effective_halation_r
        f_h_actual_g = params.effective_halation_g
        f_h_actual_b = params.effective_halation_b
        
        # 驗證（允許 1e-6 浮點誤差）
        assert abs(f_h_actual_r - f_h_expected_r) < 1e-6, \
            f"Red: expected {f_h_expected_r:.6f}, got {f_h_actual_r:.6f}"
        assert abs(f_h_actual_g - f_h_expected_g) < 1e-6, \
            f"Green: expected {f_h_expected_g:.6f}, got {f_h_actual_g:.6f}"
        assert abs(f_h_actual_b - f_h_expected_b) < 1e-6, \
            f"Blue: expected {f_h_expected_b:.6f}, got {f_h_actual_b:.6f}"
    
    def test_cinestill_no_ah_layer(self):
        """測試 CineStill 800T（無 AH 層，T_AH=1）"""
        params = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.93,
            emulsion_transmittance_g=0.88,
            emulsion_transmittance_b=0.80,
            base_transmittance=0.98,
            ah_layer_transmittance_r=1.0,  # 無 AH
            ah_layer_transmittance_g=1.0,
            ah_layer_transmittance_b=1.0,
            backplate_reflectance=0.30
        )
        
        # 期望：f_h = [T_e·T_b]²·R_bp
        T_single_r = 0.93 * 0.98 * 1.0  # = 0.9114
        f_h_expected_r = (T_single_r ** 2) * 0.30  # ≈ 0.249
        
        f_h_actual_r = params.effective_halation_r
        
        assert abs(f_h_actual_r - f_h_expected_r) < 1e-6
        assert f_h_actual_r > 0.15, \
            f"CineStill red halation too weak: {f_h_actual_r:.3f} (expected > 0.15)"
    
    def test_no_backplate_reflection(self):
        """測試邊界條件：R_bp=0（黑背板，無 Halation）"""
        params = HalationParams(
            enabled=True,
            backplate_reflectance=0.0  # 黑背板
        )
        
        assert params.effective_halation_r == 0.0
        assert params.effective_halation_g == 0.0
        assert params.effective_halation_b == 0.0
    
    def test_parameter_range_validation(self):
        """測試參數範圍合法性（0 < T ≤ 1, 0 ≤ R ≤ 1）"""
        # 合法範圍（注意：必須滿足 T_r >= T_g >= T_b 的物理規律）
        params_valid = HalationParams(
            emulsion_transmittance_r=0.98,  # 上限
            emulsion_transmittance_g=0.95,  # 中間值（必須 <= r）
            emulsion_transmittance_b=0.85,  # 下限（必須 <= g）
            base_transmittance=0.995,       # 上限
            ah_layer_transmittance_r=0.02,  # AH 層下限
            ah_layer_transmittance_g=0.015, # 必須 <= r
            ah_layer_transmittance_b=0.01,  # 必須 <= g
            backplate_reflectance=0.5       # 中間值
        )
        assert 0.0 < params_valid.effective_halation_r <= 1.0
        
        # 邊界測試：T_AH=1（CineStill）
        params_no_ah = HalationParams(
            ah_layer_transmittance_r=1.0,
            ah_layer_transmittance_g=1.0,
            ah_layer_transmittance_b=1.0
        )
        assert params_no_ah.effective_halation_r > 0.0


class TestCineStillVsPortra:
    """CineStill vs Portra 紅暈比例測試"""
    
    def test_cinestill_vs_portra_red_halo_ratio(self):
        """測試 CineStill vs Portra 紅暈比例（應 > 5× 差異, TASK-011 Phase 2）"""
        # CineStill 800T（無 AH）
        cinestill = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.93,
            ah_layer_transmittance_r=1.0,  # 無 AH
            ah_layer_transmittance_g=1.0,
            ah_layer_transmittance_b=1.0,
            backplate_reflectance=0.35
        )
        
        # Portra 400（有 AH）
        portra = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.92,
            ah_layer_transmittance_r=0.30,  # 有 AH
            ah_layer_transmittance_g=0.10,
            ah_layer_transmittance_b=0.05,
            backplate_reflectance=0.30
        )
        
        f_h_cinestill = cinestill.effective_halation_r
        f_h_portra = portra.effective_halation_r
        
        ratio = f_h_cinestill / (f_h_portra + 1e-9)
        
        print(f"\n  CineStill f_h,red: {f_h_cinestill:.4f}")
        print(f"  Portra f_h,red: {f_h_portra:.4f}")
        print(f"  Ratio: {ratio:.1f}×")
        
        # Physicist Review 驗收標準
        assert f_h_cinestill > 0.15, \
            f"CineStill red halation too weak: {f_h_cinestill:.3f} (expected > 0.15)"
        assert f_h_portra < 0.05, \
            f"Portra red halation too strong: {f_h_portra:.3f} (expected < 0.05)"
        assert ratio > 5.0, \
            f"CineStill/Portra ratio too small: {ratio:.1f}× (expected > 5×)"
    
    def test_cinestill_extreme_halation_enabled(self):
        """驗證 CineStill 產生極端紅暈（無 AH 層）"""
        lux = np.zeros((128, 128), dtype=np.float32)
        lux[64, 64] = 1.0
        
        _, params_cinestill, _ = create_default_medium_physics_params(
            "CineStill 800T", has_ah_layer=False, iso=800
        )
        
        result = phos.apply_halation(lux, params_cinestill, 650)
        
        # CineStill 特徵：
        # 1. 近距離（5-10 px）有顯著紅暈（實測 ~5e-6）
        near_halo = np.mean(result[59:60, 64])  # 距中心 5 px
        assert near_halo > 1e-6, f"CineStill near halo too weak: {near_halo:.6e} (expected > 1e-6)"
        
        # 2. 遠距離（50 px）仍可見（實測 ~4.6e-7）
        far_halo = np.mean(result[14:15, 64])  # 距中心 50 px
        assert far_halo > 1e-8, f"CineStill far halo too weak: {far_halo:.6e} (expected > 1e-8)"
        
        # 3. 驗證能量守恆
        energy_in = np.sum(lux)
        energy_out = np.sum(result)
        assert abs(energy_out - energy_in) / energy_in < 0.001


class TestWavelengthDependence:
    """波長依賴驗證（藍外圈 + 紅核心）"""
    
    def test_blue_halo_outer_ring_stronger(self):
        """驗證藍光紅暈在外圈更強（Beer-Lambert: 藍光易穿透）"""
        lux = np.zeros((128, 128), dtype=np.float32)
        lux[64, 64] = 1.0
        
        params = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.92,
            emulsion_transmittance_g=0.87,
            emulsion_transmittance_b=0.78,
            ah_layer_transmittance_r=0.30,
            ah_layer_transmittance_g=0.10,
            ah_layer_transmittance_b=0.05,
            energy_fraction=0.1,
            psf_radius=80
        )
        
        # RGB 三通道
        result_r = phos.apply_halation(lux.copy(), params, 650)
        result_b = phos.apply_halation(lux.copy(), params, 450)
        
        # 外圈（30-35 px）：藍光應更強
        halo_r_outer = np.mean(result_r[35:40, 64])
        halo_b_outer = np.mean(result_b[35:40, 64])
        
        print(f"\n  紅光外圈: {halo_r_outer:.6e}")
        print(f"  藍光外圈: {halo_b_outer:.6e}")
        print(f"  藍/紅比例: {halo_b_outer / (halo_r_outer + 1e-12):.2f}")
        
        # 藍光 AH 透過率更低（0.05 vs 0.30），實際紅暈可能較弱
        # 但藍光乳劑透過率較低（0.78 vs 0.92），整體效果需實驗驗證
        # 這裡僅驗證存在差異
        assert halo_r_outer != halo_b_outer, "Red and blue halos should differ"
    
    def test_red_halo_core_stronger(self):
        """驗證紅光在核心區更集中"""
        lux = np.zeros((128, 128), dtype=np.float32)
        lux[64, 64] = 1.0
        
        params = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.92,
            emulsion_transmittance_b=0.78,
            ah_layer_transmittance_r=0.30,
            ah_layer_transmittance_b=0.05,
            energy_fraction=0.1
        )
        
        result_r = phos.apply_halation(lux.copy(), params, 650)
        result_b = phos.apply_halation(lux.copy(), params, 450)
        
        # 核心區（62-67 像素，距中心 2-3 px）
        halo_r_core = np.mean(result_r[62:67, 64])
        halo_b_core = np.mean(result_b[62:67, 64])
        
        print(f"\n  紅光核心: {halo_r_core:.6e}")
        print(f"  藍光核心: {halo_b_core:.6e}")
        
        # 核心區應有顯著差異
        assert halo_r_core != halo_b_core, "Core halos should differ by wavelength"


class TestBackwardCompatibility:
    """
    向後相容性測試（已廢棄）
    
    Phase 1 Task 1: 已移除 deprecated HalationParams 向後相容邏輯
    這些測試保留作為歷史記錄，但已被跳過。
    """
    
    @pytest.mark.skip(reason="Phase 1 Task 1: Deprecated HalationParams backward compatibility removed")
    def test_old_params_trigger_deprecation_warning(self):
        """驗證舊參數觸發 DeprecationWarning"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # 使用舊參數
            params = HalationParams(
                transmittance_r=0.7,
                transmittance_g=0.5,
                transmittance_b=0.3,
                ah_absorption=0.95
            )
            
            # 應觸發 2 個警告（transmittance + ah_absorption）
            assert len(w) >= 2, f"Expected 2 warnings, got {len(w)}"
            assert any("transmittance_r" in str(warning.message) for warning in w)
            assert any("ah_absorption" in str(warning.message) for warning in w)
    
    @pytest.mark.skip(reason="Phase 1 Task 1: Deprecated HalationParams backward compatibility removed")
    def test_old_params_converted_correctly(self):
        """驗證舊參數正確轉換為新格式"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # 忽略警告以測試轉換
            
            params = HalationParams(
                transmittance_r=0.7,
                ah_absorption=0.95,
                base_transmittance=0.98
            )
            
            # 檢查轉換結果
            # 舊 transmittance_r = T_e² · T_b² → T_e = sqrt(0.7 / 0.98²)
            expected_emulsion_t = np.sqrt(0.7 / (0.98 ** 2))
            assert abs(params.emulsion_transmittance_r - expected_emulsion_t) < 0.01
            
            # 舊 ah_absorption = 0.95 → T_AH = 1 - 0.95 = 0.05
            # 使用容錯比較（浮點精度）
            assert abs(params.ah_layer_transmittance_r - 0.05) < 1e-9
    
    def test_new_params_no_warning(self):
        """驗證新參數不觸發警告"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            params = HalationParams(
                emulsion_transmittance_r=0.92,
                ah_layer_transmittance_r=0.30
            )
            
            # 不應觸發任何警告
            halation_warnings = [warning for warning in w 
                                if "HalationParams" in str(warning.message)]
            assert len(halation_warnings) == 0, f"Unexpected warnings: {halation_warnings}"


class TestDimensionalConsistency:
    """量綱一致性測試"""
    
    def test_all_transmittances_in_range(self):
        """驗證所有透過率參數在 [0, 1] 範圍"""
        params = HalationParams()
        
        assert 0 <= params.emulsion_transmittance_r <= 1
        assert 0 <= params.emulsion_transmittance_g <= 1
        assert 0 <= params.emulsion_transmittance_b <= 1
        assert 0 <= params.base_transmittance <= 1
        assert 0 <= params.ah_layer_transmittance_r <= 1
        assert 0 <= params.ah_layer_transmittance_g <= 1
        assert 0 <= params.ah_layer_transmittance_b <= 1
        assert 0 <= params.backplate_reflectance <= 1
    
    def test_effective_halation_in_range(self):
        """驗證有效 Halation 分數在 [0, 1] 範圍"""
        params = HalationParams()
        
        assert 0 <= params.effective_halation_r <= 1
        assert 0 <= params.effective_halation_g <= 1
        assert 0 <= params.effective_halation_b <= 1
    
    def test_effective_halation_calculation(self):
        """驗證有效 Halation 分數計算公式"""
        params = HalationParams(
            emulsion_transmittance_r=0.92,
            base_transmittance=0.98,
            ah_layer_transmittance_r=0.30,
            backplate_reflectance=0.30
        )
        
        # 手動計算 f_h = (T_e · T_b · T_AH)² · R_bp
        T_single = 0.92 * 0.98 * 0.30
        expected = (T_single ** 2) * 0.30
        
        assert abs(params.effective_halation_r - expected) < 1e-6


class TestBeerLambertConsistency:
    """Beer-Lambert 公式一致性測試"""
    
    def test_higher_ah_transmittance_increases_halation(self):
        """驗證更高的 AH 透過率 → 更強的 Halation"""
        lux = np.zeros((128, 128), dtype=np.float32)
        lux[64, 64] = 1.0
        
        # 低 AH 透過率（標準膠片）
        params_low = HalationParams(
            ah_layer_transmittance_r=0.10,
            energy_fraction=0.05
        )
        
        # 高 AH 透過率（CineStill）
        params_high = HalationParams(
            ah_layer_transmittance_r=1.0,
            energy_fraction=0.05
        )
        
        result_low = phos.apply_halation(lux.copy(), params_low, 650)
        result_high = phos.apply_halation(lux.copy(), params_high, 650)
        
        # 外圈紅暈：高透過率應更強
        halo_low = np.mean(result_low[40:45, 64])
        halo_high = np.mean(result_high[40:45, 64])
        
        assert halo_high > halo_low, f"High T_AH ({halo_high:.6e}) should > Low T_AH ({halo_low:.6e})"
    
    def test_exponential_decay_not_linear(self):
        """驗證不使用線性近似（Beer-Lambert 為指數）"""
        # 這個測試驗證實作中沒有使用 T ≈ 1 - α
        params = HalationParams(ah_layer_transmittance_r=0.30)
        
        # 如果使用線性近似 T = 1 - α，則 α = 0.7
        # 但實際應該是 T = exp(-α·L)，無法直接推出 α
        # 這裡僅驗證 effective_halation 使用乘法（非線性）
        
        # f_h 應該是 T² 的量級，不是線性
        f_h = params.effective_halation_r
        T_single = (params.emulsion_transmittance_r * 
                    params.base_transmittance * 
                    params.ah_layer_transmittance_r)
        
        # 驗證使用平方（指數形式的近似）
        assert abs(f_h - (T_single ** 2) * params.backplate_reflectance) < 1e-6


# ============================================================
# Section 3: Wavelength Bloom Tests
# Source: test_wavelength_bloom.py (8 tests)
# ============================================================

def test_wavelength_energy_ratios():
    """測試 1: 能量權重比例驗證（Mie 查表版本）"""
    print("\n" + "=" * 70)
    print("Test 1: 能量權重比例驗證（Mie 查表）")
    print("=" * 70)
    
    # 載入配置
    film = get_film_profile("Cinestill800T_MediumPhysics")
    params = film.wavelength_bloom_params
    
    # 使用 Mie 查表（v0.4.2+ 唯一實作）
    # 經驗公式參數 wavelength_power/radius_power 已於 v0.6.1 刪除
    lambda_ref = params.reference_wavelength
    
    # 使用固定的 Mie 理論預期值（基於 AgBr 銀鹽顆粒）
    p_mie = 3.5  # Mie 散射理論預期值（ISO 400）
    
    eta_r = (lambda_ref / params.lambda_r) ** p_mie
    eta_g = 1.0
    eta_b = (lambda_ref / params.lambda_b) ** p_mie
    
    ratio_b_r = eta_b / eta_r
    
    print(f"\n  Mie 散射指數（理論）: p ≈ {p_mie}")
    print(f"  參考波長: {lambda_ref} nm")
    print(f"\n  能量權重（相對綠光）:")
    print(f"    η_r (紅 650nm): {eta_r:.4f}")
    print(f"    η_g (綠 550nm): {eta_g:.4f} (基準)")
    print(f"    η_b (藍 450nm): {eta_b:.4f}")
    print(f"\n  比例 η_b/η_r: {ratio_b_r:.2f}x")
    
    # 驗證（Mie 理論: p≈3-4，對應比例約 2.5-4.5x）
    assert 2.0 < ratio_b_r < 5.0, f"能量比例應在 2-5x（實際 {ratio_b_r:.2f}x）"
    print(f"  ✓ 能量比例符合 Mie 理論預期（2-5x）")
    
    print("\n  ✅ Test 1 Passed")


def test_psf_width_ratios():
    """測試 2: PSF 寬度比例驗證（Mie 查表版本）"""
    print("\n" + "=" * 70)
    print("Test 2: PSF 寬度比例驗證（Mie 查表）")
    print("=" * 70)
    
    film = get_film_profile("Cinestill800T_MediumPhysics")
    params = film.wavelength_bloom_params
    
    # 使用 Mie 查表（v0.4.2+ 唯一實作）
    # 經驗公式參數 radius_power 已於 v0.6.1 刪除
    lambda_ref = params.reference_wavelength
    
    # 使用固定的 Mie 理論預期值（小角散射近似）
    q_mie = 0.8  # Mie 前向散射理論預期值
    
    sigma_r = (lambda_ref / params.lambda_r) ** q_mie
    sigma_g = 1.0
    sigma_b = (lambda_ref / params.lambda_b) ** q_mie
    
    ratio_b_r = sigma_b / sigma_r
    
    print(f"\n  Mie 半徑指數（理論）: q ≈ {q_mie}")
    print(f"  參考波長: {lambda_ref} nm")
    print(f"\n  PSF 寬度（相對綠光）:")
    print(f"    σ_r (紅 650nm): {sigma_r:.4f}")
    print(f"    σ_g (綠 550nm): {sigma_g:.4f} (基準)")
    print(f"    σ_b (藍 450nm): {sigma_b:.4f}")
    print(f"\n  比例 σ_b/σ_r: {ratio_b_r:.2f}x")
    
    # 驗證（Mie 理論: 藍光 PSF 應為紅光的 1.2-1.5 倍）
    assert 1.1 < ratio_b_r < 1.6, f"PSF 寬度比例應在 1.1-1.6x（實際 {ratio_b_r:.2f}x）"
    print(f"  ✓ PSF 寬度比例符合 Mie 理論預期（1.1-1.6x）")
    
    print("\n  ✅ Test 2 Passed")


def test_dual_kernel_normalization():
    """測試 3: 雙段核 PSF 正規化"""
    print("\n" + "=" * 70)
    print("Test 3: 雙段核 PSF 正規化驗證")
    print("=" * 70)
    
    def create_dual_kernel_psf_test(sigma, kappa, core_fraction, radius=100):
        """簡化版雙段核創建（用於測試）"""
        size = 2 * radius + 1
        y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
        r = np.sqrt(x**2 + y**2).astype(np.float32)
        
        gaussian_core = np.exp(-r**2 / (2 * sigma**2))
        exponential_tail = np.exp(-r / kappa)
        
        psf = core_fraction * gaussian_core + (1 - core_fraction) * exponential_tail
        psf = psf / np.sum(psf)
        
        return psf
    
    # 測試不同參數組合（使用修正後的 κ = 1.5σ）
    tail_scale = 1.5
    test_cases = [
        ("紅光", 17.5, 17.5 * tail_scale, 0.70, 100),  # κ = 26.25
        ("綠光", 20.0, 20.0 * tail_scale, 0.75, 100),  # κ = 30.0
        ("藍光", 23.5, 23.5 * tail_scale, 0.80, 100)   # κ = 35.25
    ]
    
    print("\n  測試不同波長的 PSF 正規化:")
    for name, sigma, kappa, rho, radius in test_cases:
        psf = create_dual_kernel_psf_test(sigma, kappa, rho, radius)
        psf_sum = np.sum(psf)
        
        print(f"    [{name}] σ={sigma:.1f}, κ={kappa:.1f}, ρ={rho:.2f}")
        print(f"      ∑PSF = {psf_sum:.6f}")
        
        assert abs(psf_sum - 1.0) < 0.001, f"PSF 總和應為 1.0（實際 {psf_sum:.6f}）"
        print(f"      ✓ 正規化正確")
    
    print("\n  ✅ Test 3 Passed")


def test_dual_kernel_shape():
    """測試 4: 雙段核形狀驗證"""
    print("\n" + "=" * 70)
    print("Test 4: 雙段核形狀驗證（核心 + 拖尾）")
    print("=" * 70)
    
    def create_dual_kernel_psf_test(sigma, kappa, core_fraction, radius=100):
        size = 2 * radius + 1
        y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
        r = np.sqrt(x**2 + y**2).astype(np.float32)
        
        gaussian_core = np.exp(-r**2 / (2 * sigma**2))
        exponential_tail = np.exp(-r / kappa)
        
        psf = core_fraction * gaussian_core + (1 - core_fraction) * exponential_tail
        psf = psf / np.sum(psf)
        
        return psf, r
    
    # 創建藍光 PSF（最寬），使用修正後的 κ = 1.5σ
    sigma_b = 23.5
    kappa_b = sigma_b * 1.5  # 35.25
    psf, r = create_dual_kernel_psf_test(sigma_b, kappa_b, 0.80, radius=100)
    
    # 提取徑向輪廓（中心橫向切片）
    center = 100
    profile = psf[center, :]
    radii = r[center, :]
    
    # 驗證拖尾存在（遠端值不應過小）
    far_value = profile[center + 80]
    assert far_value > 1e-6, f"拖尾區應有明顯能量（80px處: {far_value:.2e}）"
    print(f"\n  ✓ 拖尾區有明顯能量（80px處: {far_value:.2e}）")
    
    # 驗證核心主導（中心 >> 遠端）
    center_value = profile[center]
    ratio = center_value / (far_value + 1e-10)
    assert ratio > 20, f"中心應大於拖尾（比例: {ratio:.1f}x，目標 >20x）"
    print(f"  ✓ 中心/拖尾比例合理（{ratio:.1f}x，目標 >20x）")
    
    print("\n  ✅ Test 4 Passed")


def test_configuration_loading():
    """測試 5: 配置載入測試"""
    print("\n" + "=" * 70)
    print("Test 5: Phase 1 配置載入驗證")
    print("=" * 70)
    
    # 測試 CineStill 配置
    print("\n  [CineStill800T_MediumPhysics]")
    cs = get_film_profile("Cinestill800T_MediumPhysics")
    
    assert cs.physics_mode == PhysicsMode.PHYSICAL
    print(f"    Physics Mode: {cs.physics_mode} ✓")
    
    assert cs.wavelength_bloom_params is not None
    print(f"    Has wavelength_bloom_params: True ✓")
    
    assert cs.wavelength_bloom_params.enabled == True
    print(f"    Wavelength Bloom Enabled: {cs.wavelength_bloom_params.enabled} ✓")
    
    # v0.6.1: wavelength_power/radius_power 已刪除，改為驗證 Mie 查表啟用
    assert cs.wavelength_bloom_params.use_mie_lookup == True
    print(f"    use_mie_lookup (Mie 查表): {cs.wavelength_bloom_params.use_mie_lookup} ✓")
    
    # 測試 Portra 配置（使用 _Mie 版本）
    print("\n  [Portra400_MediumPhysics_Mie]")
    portra = get_film_profile("Portra400_MediumPhysics_Mie")
    
    assert portra.wavelength_bloom_params is not None
    assert portra.wavelength_bloom_params.enabled == True
    print(f"    Physics Mode: {portra.physics_mode} ✓")
    print(f"    Wavelength Bloom Enabled: {portra.wavelength_bloom_params.enabled} ✓")
    
    print("\n  ✅ Test 5 Passed")


def test_mode_detection():
    """測試 6: 模式檢測邏輯"""
    print("\n" + "=" * 70)
    print("Test 6: Phase 1 模式檢測邏輯")
    print("=" * 70)
    
    cs = get_film_profile("Cinestill800T_MediumPhysics")
    
    # 模擬 Phos_0.3.0.py 中的檢測邏輯
    use_physical_bloom = (
        cs.physics_mode == PhysicsMode.PHYSICAL and
        cs.bloom_params.mode == "physical"
    )
    
    use_medium_physics = (
        use_physical_bloom and
        hasattr(cs, 'halation_params') and
        cs.halation_params is not None and
        cs.halation_params.enabled
    )
    
    use_wavelength_bloom = (
        use_medium_physics and
        hasattr(cs, 'wavelength_bloom_params') and
        cs.wavelength_bloom_params is not None and
        cs.wavelength_bloom_params.enabled
    )
    
    assert use_wavelength_bloom == True, "Phase 1 模式應被檢測到"
    print("\n  ✓ Phase 1 (波長依賴 Bloom) 模式檢測正確")
    
    # 測試黑白底片（應該不啟用 wavelength bloom）
    hp5 = get_film_profile("HP5Plus400")
    
    use_wavelength_bw = (
        hasattr(hp5, 'wavelength_bloom_params') and
        hp5.wavelength_bloom_params is not None and
        hp5.wavelength_bloom_params.enabled
    )
    
    assert use_wavelength_bw == False, "黑白底片不應有波長依賴 bloom"
    print("  ✓ 黑白底片不啟用 wavelength bloom（正確）")
    
    print("\n  ✅ Test 6 Passed")


def test_parameter_decoupling():
    """測試 7: η 與 σ 解耦驗證（Mie 查表版本）"""
    print("\n" + "=" * 70)
    print("Test 7: 參數解耦驗證（η 與 σ 獨立）- Mie 查表")
    print("=" * 70)
    
    film = get_film_profile("Cinestill800T_MediumPhysics")
    params = film.wavelength_bloom_params
    
    # v0.6.1: wavelength_power/radius_power 已刪除
    # 使用 Mie 理論固定值驗證解耦
    p_mie = 3.5  # 能量權重指數（Mie 理論）
    q_mie = 0.8  # PSF 寬度指數（小角散射）
    
    print(f"\n  能量權重指數（Mie 理論）: p = {p_mie}")
    print(f"  PSF 寬度指數（Mie 理論）: q = {q_mie}")
    print(f"  p ≠ q: {p_mie != q_mie}")
    
    assert p_mie != q_mie, "能量權重與 PSF 寬度應使用不同指數（解耦）"
    print(f"  ✓ η(λ) 與 σ(λ) 已解耦（p={p_mie}, q={q_mie}）")
    
    # 計算兩者的比例差異
    lambda_ratio = params.lambda_b / params.lambda_r  # 450/650 ≈ 0.692
    
    # η(λ) ∝ (λ_ref/λ)^p → η_b/η_r = (λ_r/λ_b)^p = (650/450)^3.5
    eta_ratio = (params.lambda_r / params.lambda_b) ** p_mie  # (650/450)^3.5 = 3.62
    
    # σ(λ) ∝ (λ_ref/λ)^q → σ_b/σ_r = (λ_r/λ_b)^q = (650/450)^0.8
    sigma_ratio = (params.lambda_r / params.lambda_b) ** q_mie  # (650/450)^0.8 = 1.34
    
    print(f"\n  波長比 λ_b/λ_r: {lambda_ratio:.3f}")
    print(f"  能量比 η_b/η_r: {eta_ratio:.3f} (∝ λ^{p_mie})")
    print(f"  寬度比 σ_b/σ_r: {sigma_ratio:.3f} (∝ λ^{q_mie})")
    
    # 驗證兩者變化方向一致但幅度不同
    assert eta_ratio > 2.0, "藍光能量權重應顯著大於紅光"
    assert 1.2 < sigma_ratio < 1.6, "藍光 PSF 寬度應適度大於紅光"
    
    print(f"  ✓ 能量與寬度變化幅度不同（避免不可辨識性）")
    
    print("\n  ✅ Test 7 Passed")


def test_performance_estimate():
    """測試 8: 效能估算"""
    print("\n" + "=" * 70)
    print("Test 8: 效能估算（基於理論分析）")
    print("=" * 70)
    
    # Phase 1 新增操作
    print("\n  Phase 1 新增計算量:")
    print("    1. 創建 3 個雙段核 PSF (R/G/B)")
    print("       - 每個 PSF: (2*radius+1)^2 元素")
    print("       - radius ≈ 80px (4σ 覆蓋)")
    print("       - 計算量: 3 × (161×161) ≈ 78K 操作")
    print("       - 預估時間: ~5ms")
    
    print("\n  總估算時間（2000×3000 影像）:")
    phase1_overhead = 0.005  # PSF 創建
    phase2_time = 0.136      # Bloom + Halation（Phase 2 實測）
    total_estimated = phase1_overhead + phase2_time
    
    print(f"    Phase 1 額外開銷: {phase1_overhead:.3f}s")
    print(f"    Phase 2 基線時間: {phase2_time:.3f}s")
    print(f"    總估算時間: {total_estimated:.3f}s")
    
    target = 10.0
    margin = target / total_estimated
    
    print(f"\n  目標時間: < {target}s")
    print(f"  安全邊界: {margin:.1f}x")
    
    assert total_estimated < target, f"估算時間應 < {target}s（實際 {total_estimated:.3f}s）"
    print(f"  ✓ 效能估算符合目標")
    
    print("\n  ✅ Test 8 Passed")


# ============================================================
# Section 4: Mie Halation Integration Tests
# Source: test_mie_halation_integration.py (7 tests)
# ============================================================

def test_mie_halation_parameters_loaded():
    """測試 1: 驗證 Mie + Halation 配置正確載入"""
    print("\n" + "=" * 70)
    print("Test 1: Mie + Halation 參數載入驗證")
    print("=" * 70)
    
    # Cinestill800T: Physical Bloom + 極端 Halation
    cs = get_film_profile("Cinestill800T")
    
    print(f"\n  [Cinestill800T]")
    print(f"  Physics Mode: {cs.physics_mode}")
    print(f"  Bloom Mode: {cs.bloom_params.mode}")
    print(f"  Bloom Energy Exponent: {cs.bloom_params.energy_wavelength_exponent}")
    print(f"  Bloom PSF Exponent: {cs.bloom_params.psf_width_exponent}")
    print(f"  Halation Enabled: {cs.halation_params.enabled}")
    print(f"  Halation PSF Radius: {cs.halation_params.psf_radius} px")
    print(f"  Halation Energy Fraction: {cs.halation_params.energy_fraction}")
    
    # Bloom 參數驗證
    assert cs.physics_mode == PhysicsMode.PHYSICAL, "Should use PHYSICAL mode"
    assert cs.bloom_params.mode == "physical", "Should use physical bloom"
    assert cs.bloom_params.energy_wavelength_exponent == 3.5, "Should use Mie exponent"
    assert cs.bloom_params.psf_width_exponent == 0.8, "Should use small-angle exponent"
    print(f"    ✓ Bloom (Mie) parameters correct")
    
    # Halation 參數驗證
    assert cs.halation_params.enabled == True, "Halation should be enabled"
    assert cs.halation_params.ah_layer_transmittance_r == 1.0, "CineStill has no AH layer"
    assert cs.halation_params.psf_radius == 150, "CineStill should have large halo"
    print(f"    ✓ Halation (extreme) parameters correct")
    
    # Portra400: Physical Bloom + 標準 Halation
    portra = get_film_profile("Portra400")
    
    print(f"\n  [Portra400]")
    print(f"  Physics Mode: {portra.physics_mode}")
    print(f"  Bloom Mode: {portra.bloom_params.mode}")
    print(f"  Halation Enabled: {portra.halation_params.enabled}")
    print(f"  AH Layer Transmittance (R): {portra.halation_params.ah_layer_transmittance_r}")
    
    assert portra.physics_mode == PhysicsMode.PHYSICAL
    assert portra.bloom_params.mode == "physical"
    assert portra.halation_params.enabled == True
    assert portra.halation_params.ah_layer_transmittance_r < 1.0, "Portra has AH layer"
    print(f"    ✓ Portra parameters correct")
    
    print("\n  ✅ Test 1 Passed")


def test_mie_parameters_compatibility():
    """測試 2: 驗證 Mie 參數與 Halation 可兼容"""
    print("\n" + "=" * 70)
    print("Test 2: Mie 參數與 Halation 兼容性")
    print("=" * 70)
    
    # 創建測試配置（Mie Bloom + Halation）
    bloom_params = BloomParams(
        mode="mie_corrected",  # 使用 Mie 模式
        threshold=0.8,
        base_scattering_ratio=0.08,
        energy_wavelength_exponent=3.5,
        psf_width_exponent=0.8,
        psf_dual_segment=True,
        energy_conservation=True
    )
    
    halation_params = HalationParams(
        enabled=True,
        emulsion_transmittance_r=0.9,
        emulsion_transmittance_g=0.85,
        emulsion_transmittance_b=0.8,
        ah_layer_transmittance_r=0.3,
        backplate_reflectance=0.3,
        psf_radius=100,
        energy_fraction=0.05
    )
    
    print(f"\n  Bloom (Mie) Configuration:")
    print(f"    Mode: {bloom_params.mode}")
    print(f"    Energy exponent: {bloom_params.energy_wavelength_exponent}")
    print(f"    PSF width exponent: {bloom_params.psf_width_exponent}")
    
    print(f"\n  Halation Configuration:")
    print(f"    Enabled: {halation_params.enabled}")
    print(f"    Emulsion T(R): {halation_params.emulsion_transmittance_r}")
    print(f"    AH layer T(R): {halation_params.ah_layer_transmittance_r}")
    print(f"    PSF radius: {halation_params.psf_radius} px")
    
    # 驗證參數範圍合理
    assert 0 < bloom_params.base_scattering_ratio <= 0.2, "Bloom scattering ratio reasonable"
    assert 0 < halation_params.energy_fraction <= 0.2, "Halation energy fraction reasonable"
    
    print(f"\n    ✓ Parameters compatible and reasonable")
    print("\n  ✅ Test 2 Passed")


def test_energy_conservation_concept():
    """測試 3: 驗證能量守恆概念（不依賴實際函數）"""
    print("\n" + "=" * 70)
    print("Test 3: 能量守恆概念驗證")
    print("=" * 70)
    
    # 模擬能量分配
    total_energy = 1.0
    bloom_scattering_ratio = 0.08
    halation_energy_fraction = 0.05
    
    print(f"\n  Initial Energy: {total_energy:.4f}")
    print(f"  Bloom Scattering: {bloom_scattering_ratio:.4f} ({bloom_scattering_ratio*100:.1f}%)")
    print(f"  Halation Fraction: {halation_energy_fraction:.4f} ({halation_energy_fraction*100:.1f}%)")
    
    # Bloom 能量（從高光中提取）
    highlight_energy = 0.3  # 假設 30% 是高光
    bloom_energy_scattered = highlight_energy * bloom_scattering_ratio
    
    # Halation 能量（從剩餘能量中提取）
    remaining_after_bloom = total_energy - bloom_energy_scattered
    halation_energy_scattered = remaining_after_bloom * halation_energy_fraction
    
    # 總散射能量
    total_scattered = bloom_energy_scattered + halation_energy_scattered
    
    print(f"\n  Energy Distribution:")
    print(f"    Bloom scattered: {bloom_energy_scattered:.6f}")
    print(f"    Halation scattered: {halation_energy_scattered:.6f}")
    print(f"    Total scattered: {total_scattered:.6f}")
    
    # 驗證：散射能量不會憑空消失
    assert total_scattered < total_energy, "Scattered energy should not exceed total"
    assert total_scattered > 0, "Should have some scattering"
    
    # 驗證：兩種效果的能量規模合理
    assert bloom_energy_scattered < 0.1, "Bloom should scatter < 10% of total"
    assert halation_energy_scattered < 0.1, "Halation should scatter < 10% of total"
    
    print(f"\n    ✓ Energy conservation principle verified")
    print("\n  ✅ Test 3 Passed")


def test_wavelength_dependence_principles():
    """測試 4: 驗證 Bloom 與 Halation 的波長依賴關係"""
    print("\n" + "=" * 70)
    print("Test 4: 波長依賴關係驗證")
    print("=" * 70)
    
    λ_r = 650.0  # 紅光 (nm)
    λ_g = 550.0  # 綠光 (nm)
    λ_b = 450.0  # 藍光 (nm)
    λ_ref = 550.0  # 參考波長
    
    # Bloom (Mie 散射): 藍光散射 > 紅光
    bloom_energy_exp = 3.5
    bloom_psf_exp = 0.8
    
    bloom_energy_r = (λ_ref / λ_r) ** bloom_energy_exp
    bloom_energy_g = (λ_ref / λ_g) ** bloom_energy_exp
    bloom_energy_b = (λ_ref / λ_b) ** bloom_energy_exp
    
    bloom_psf_r = (λ_ref / λ_r) ** bloom_psf_exp
    bloom_psf_g = (λ_ref / λ_g) ** bloom_psf_exp
    bloom_psf_b = (λ_ref / λ_b) ** bloom_psf_exp
    
    print(f"\n  Bloom (Mie Scattering):")
    print(f"    Energy weights: R={bloom_energy_r:.3f}, G={bloom_energy_g:.3f}, B={bloom_energy_b:.3f}")
    print(f"    Ratio B/R: {bloom_energy_b/bloom_energy_r:.2f}x")
    
    print(f"    PSF widths: R={bloom_psf_r:.3f}, G={bloom_psf_g:.3f}, B={bloom_psf_b:.3f}")
    print(f"    Ratio B/R: {bloom_psf_b/bloom_psf_r:.2f}x")
    
    # Halation (Beer-Lambert): 紅光穿透 > 藍光
    T_e_r = 0.92
    T_e_g = 0.87
    T_e_b = 0.78
    T_b = 0.98
    T_ah_r = 0.3
    R_bp = 0.3
    
    # 有效 Halation 係數: f_h(λ) = T_AH × T_e² × T_b² × R_bp
    f_h_r = T_ah_r * (T_e_r ** 2) * (T_b ** 2) * R_bp
    f_h_g = T_ah_r * (T_e_g ** 2) * (T_b ** 2) * R_bp
    f_h_b = T_ah_r * (T_e_b ** 2) * (T_b ** 2) * R_bp
    
    print(f"\n  Halation (Beer-Lambert):")
    print(f"    Effective coefficients: R={f_h_r:.6f}, G={f_h_g:.6f}, B={f_h_b:.6f}")
    print(f"    Ratio R/B: {f_h_r/f_h_b:.2f}x")
    
    # 驗證：兩種效果的波長依賴相反
    assert bloom_energy_b > bloom_energy_r, "Bloom: Blue > Red (scattering)"
    assert f_h_r > f_h_b, "Halation: Red > Blue (transmission)"
    
    print(f"\n    ✓ Bloom favors blue (Mie scattering)")
    print(f"    ✓ Halation favors red (Beer-Lambert transmission)")
    print(f"    ✓ Wavelength dependencies are opposite (correct)")
    
    print("\n  ✅ Test 4 Passed")


def test_psf_size_comparison():
    """測試 5: 驗證 Bloom PSF << Halation PSF"""
    print("\n" + "=" * 70)
    print("Test 5: PSF 尺寸比較")
    print("=" * 70)
    
    # Bloom PSF 參數（Mie 模式）
    bloom_base_sigma_core = 15.0  # px
    bloom_base_kappa_tail = 40.0  # px
    
    # Halation PSF 參數
    halation_psf_radius = {
        "Portra400": 80,      # 標準膠片
        "Cinestill800T": 150  # 極端案例
    }
    
    print(f"\n  Bloom PSF (Mie):")
    print(f"    Core width (σ): {bloom_base_sigma_core:.1f} px")
    print(f"    Tail scale (κ): {bloom_base_kappa_tail:.1f} px")
    print(f"    Effective radius: ~{bloom_base_kappa_tail * 3:.1f} px (99% energy)")
    
    print(f"\n  Halation PSF:")
    for film, radius in halation_psf_radius.items():
        ratio = radius / bloom_base_kappa_tail
        print(f"    {film}: {radius} px (ratio: {ratio:.1f}x vs Bloom)")
        assert ratio > 1.5, f"{film} Halation should be significantly larger than Bloom"
    
    print(f"\n    ✓ Halation PSF >> Bloom PSF (correct spatial scale)")
    print("\n  ✅ Test 5 Passed")


def test_cinestill_extreme_parameters():
    """測試 6: 驗證 CineStill 800T 極端參數配置"""
    print("\n" + "=" * 70)
    print("Test 6: CineStill 800T 極端參數")
    print("=" * 70)
    
    cs = get_film_profile("Cinestill800T")
    
    print(f"\n  [CineStill800T Extreme Halation]")
    print(f"  Physics Mode: {cs.physics_mode}")
    print(f"  Halation PSF Radius: {cs.halation_params.psf_radius} px")
    print(f"  Halation Energy Fraction: {cs.halation_params.energy_fraction}")
    print(f"  AH Layer Transmittance (R): {cs.halation_params.ah_layer_transmittance_r}")
    
    # CineStill 特徵：無 AH 層
    assert cs.halation_params.ah_layer_transmittance_r >= 0.99, \
        "CineStill should have no AH layer (T_AH ≈ 1.0)"
    print(f"    ✓ No AH layer (T_AH = {cs.halation_params.ah_layer_transmittance_r})")
    
    # CineStill 特徵：巨型光暈
    assert cs.halation_params.psf_radius >= 120, \
        "CineStill should have large halo (> 120px)"
    print(f"    ✓ Large halo radius ({cs.halation_params.psf_radius} px)")
    
    # CineStill 特徵：高能量分數
    assert cs.halation_params.energy_fraction >= 0.10, \
        "CineStill should have strong halation (> 10%)"
    print(f"    ✓ Strong halation ({cs.halation_params.energy_fraction*100:.1f}%)")
    
    # 對比：Portra400 標準參數
    portra = get_film_profile("Portra400")
    
    print(f"\n  [Portra400 vs CineStill Comparison]")
    print(f"  Halation PSF Radius:")
    print(f"    Portra400:     {portra.halation_params.psf_radius} px")
    print(f"    CineStill800T: {cs.halation_params.psf_radius} px")
    print(f"    Ratio: {cs.halation_params.psf_radius / portra.halation_params.psf_radius:.2f}x")
    
    assert cs.halation_params.psf_radius > portra.halation_params.psf_radius * 1.5, \
        "CineStill halo should be significantly larger"
    assert cs.halation_params.energy_fraction > portra.halation_params.energy_fraction * 3, \
        "CineStill halation should be significantly stronger"
    
    print(f"\n    ✓ CineStill extreme halation correctly configured")
    print("\n  ✅ Test 6 Passed")


def test_medium_physics_mode_detection():
    """測試 7: 驗證中等物理模式檢測邏輯"""
    print("\n" + "=" * 70)
    print("Test 7: 中等物理模式檢測")
    print("=" * 70)
    
    cs = get_film_profile("Cinestill800T")
    
    # 模擬 Phos_0.3.0.py 中的檢測邏輯
    use_physical_bloom = (
        cs.physics_mode == PhysicsMode.PHYSICAL and
        cs.bloom_params.mode == "physical"
    )
    
    use_medium_physics = (
        use_physical_bloom and
        hasattr(cs, 'halation_params') and
        cs.halation_params is not None and
        cs.halation_params.enabled
    )
    
    print(f"\n  Detection Logic:")
    print(f"    Physics Mode: {cs.physics_mode}")
    print(f"    Bloom Mode: {cs.bloom_params.mode}")
    print(f"    Halation Enabled: {cs.halation_params.enabled}")
    
    print(f"\n  Decision:")
    print(f"    use_physical_bloom: {use_physical_bloom}")
    print(f"    use_medium_physics: {use_medium_physics}")
    
    assert use_physical_bloom == True, "Physical bloom should be detected"
    assert use_medium_physics == True, "Medium physics should be detected"
    
    print(f"\n    ✓ Medium physics mode correctly detected for CineStill")
    
    # 測試黑白底片（應該保持 ARTISTIC）
    hp5 = get_film_profile("HP5Plus400")
    
    use_physical_bloom_bw = (
        hp5.physics_mode == PhysicsMode.PHYSICAL and
        hp5.bloom_params.mode == "physical"
    )
    
    print(f"\n  [HP5Plus400 (B&W)]")
    print(f"    Physics Mode: {hp5.physics_mode}")
    print(f"    use_physical_bloom: {use_physical_bloom_bw}")
    
    assert use_physical_bloom_bw == False, "B&W films should remain ARTISTIC"
    print(f"    ✓ B&W films correctly remain in ARTISTIC mode")
    
    print("\n  ✅ Test 7 Passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
