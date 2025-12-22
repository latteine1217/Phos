#!/usr/bin/env python3
"""
Mie 散射修正驗證測試（Decision #014: Phase 1）

驗證項目：
1. 能量比例：藍/紅 ≈ 3.5x（容差 3.2-3.8x）
2. PSF 寬度：藍/紅 ≈ 1.27x（容差 1.20-1.35x）
3. 刀口測試：MTF HWHM_b/HWHM_r ∈ [1.2, 1.4]
4. 能量守恆：誤差 < 0.01%

Reference:
    - Decision #014: context/decisions_log.md
    - Phase 1 Design Corrected: tasks/TASK-003-medium-physics/phase1_design_corrected.md
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from film_models import BloomParams

# 直接導入（重命名以避免點號問題）
import Phos_0_3_0 as phos_module
# 先重命名檔案
import shutil
if not (project_root / "Phos_0_3_0.py").exists():
    shutil.copy(project_root / "Phos_0.3.0.py", project_root / "Phos_0_3_0.py")

import Phos_0_3_0
apply_bloom_mie_corrected = Phos_0_3_0.apply_bloom_mie_corrected


# ============================================================
# Test 1: 能量比例驗證（η_blue / η_red ≈ 3.5x）
# ============================================================

class TestMieEnergyRatio:
    """驗證 Mie 散射能量比例（λ^-3.5）"""
    
    @pytest.fixture
    def bloom_params(self):
        """標準 Mie 修正參數"""
        return BloomParams(
            mode="mie_corrected",
            energy_wavelength_exponent=3.5,
            reference_wavelength=550.0,
            base_scattering_ratio=0.08,
            threshold=0.8,
            energy_conservation=True
        )
    
    @pytest.fixture
    def test_image(self):
        """測試影像：高光區域"""
        img = np.zeros((500, 500), dtype=np.float32)
        img[200:300, 200:300] = 1.0  # 中央高光區域
        return img
    
    def test_blue_red_energy_ratio(self, bloom_params, test_image):
        """驗證藍/紅散射能量比 ≈ 3.5x"""
        # 對紅光和藍光分別處理
        result_r = apply_bloom_mie_corrected(test_image, bloom_params, wavelength=650.0)
        result_b = apply_bloom_mie_corrected(test_image, bloom_params, wavelength=450.0)
        
        # 計算散射能量（總能量變化）
        original_energy = np.sum(test_image)
        
        # 散射能量 = 卷積區域的能量增加
        # 提取擴散到外部的能量（ROI 外的能量）
        mask_outside = np.ones_like(test_image, dtype=bool)
        mask_outside[200:300, 200:300] = False
        
        scattered_energy_r = np.sum(result_r[mask_outside])
        scattered_energy_b = np.sum(result_b[mask_outside])
        
        # 計算比例
        ratio = scattered_energy_b / (scattered_energy_r + 1e-10)
        
        # 驗證：藍/紅 ≈ 3.5x（容差 3.2-3.8x）
        assert 3.2 < ratio < 3.8, f"藍/紅能量比應 ≈3.5x，實際 {ratio:.2f}x"
        print(f"✅ 能量比例測試通過：藍/紅 = {ratio:.2f}x（目標 3.5x）")
    
    def test_green_red_energy_ratio(self, bloom_params, test_image):
        """驗證綠/紅散射能量比 ≈ 1.43x"""
        result_r = apply_bloom_mie_corrected(test_image, bloom_params, wavelength=650.0)
        result_g = apply_bloom_mie_corrected(test_image, bloom_params, wavelength=550.0)
        
        mask_outside = np.ones_like(test_image, dtype=bool)
        mask_outside[200:300, 200:300] = False
        
        scattered_energy_r = np.sum(result_r[mask_outside])
        scattered_energy_g = np.sum(result_g[mask_outside])
        
        ratio = scattered_energy_g / (scattered_energy_r + 1e-10)
        
        # 驗證：綠/紅 ≈ 1.43x（容差 1.35-1.50x）
        assert 1.35 < ratio < 1.50, f"綠/紅能量比應 ≈1.43x，實際 {ratio:.2f}x"
        print(f"✅ 能量比例測試通過：綠/紅 = {ratio:.2f}x（目標 1.43x）")
    
    def test_wavelength_exponent_3_5(self, test_image):
        """驗證 λ^-3.5 關係（非 λ^-4）"""
        bloom_params = BloomParams(
            mode="mie_corrected",
            energy_wavelength_exponent=3.5,
            reference_wavelength=550.0,
            base_scattering_ratio=0.08,
            threshold=0.8
        )
        
        # 多個波長點
        wavelengths = [450, 500, 550, 600, 650]
        energies = []
        
        mask_outside = np.ones_like(test_image, dtype=bool)
        mask_outside[200:300, 200:300] = False
        
        for λ in wavelengths:
            result = apply_bloom_mie_corrected(test_image, bloom_params, wavelength=λ)
            energy = np.sum(result[mask_outside])
            energies.append(energy)
        
        # 驗證 η ∝ λ^-3.5
        energies = np.array(energies)
        wavelengths = np.array(wavelengths)
        
        # 對數線性擬合：log(η) = -3.5·log(λ) + const
        log_e = np.log(energies + 1e-10)
        log_w = np.log(wavelengths)
        
        # 計算斜率
        slope = np.polyfit(log_w, log_e, 1)[0]
        
        # 驗證斜率 ≈ -3.5（容差 ±0.3）
        assert -3.8 < slope < -3.2, f"波長指數應 ≈-3.5，實際 {slope:.2f}"
        print(f"✅ 波長指數測試通過：p = {-slope:.2f}（目標 3.5）")


# ============================================================
# Test 2: PSF 寬度驗證（σ_blue / σ_red ≈ 1.27x）
# ============================================================

class TestMiePSFWidth:
    """驗證 Mie PSF 寬度比例（λ^-0.8）"""
    
    @pytest.fixture
    def bloom_params(self):
        """標準 Mie 修正參數"""
        return BloomParams(
            mode="mie_corrected",
            psf_width_exponent=0.8,
            base_sigma_core=15.0,
            reference_wavelength=550.0,
            threshold=0.8,
            psf_dual_segment=False,  # 單段高斯以便測量
            energy_conservation=True
        )
    
    @pytest.fixture
    def point_source(self):
        """點光源影像"""
        img = np.zeros((500, 500), dtype=np.float32)
        img[250, 250] = 1.0  # 中心點光源
        return img
    
    def measure_hwhm(self, psf_image):
        """測量 PSF 的半高寬（HWHM）"""
        # 提取中心列
        center_row = psf_image[250, :]
        peak = np.max(center_row)
        half_max = peak / 2.0
        
        # 找到半高寬點
        center_idx = 250
        left = center_row[:center_idx]
        right = center_row[center_idx:]
        
        # 左側半高寬
        left_idx = np.where(left < half_max)[0]
        if len(left_idx) > 0:
            hwhm_left = center_idx - left_idx[-1]
        else:
            hwhm_left = center_idx
        
        # 右側半高寬
        right_idx = np.where(right < half_max)[0]
        if len(right_idx) > 0:
            hwhm_right = right_idx[0]
        else:
            hwhm_right = 500 - center_idx
        
        # 平均
        hwhm = (hwhm_left + hwhm_right) / 2.0
        return hwhm
    
    def test_blue_red_width_ratio(self, bloom_params, point_source):
        """驗證藍/紅 PSF 寬度比 ≈ 1.27x"""
        # 對紅光和藍光分別處理
        psf_r = apply_bloom_mie_corrected(point_source, bloom_params, wavelength=650.0)
        psf_b = apply_bloom_mie_corrected(point_source, bloom_params, wavelength=450.0)
        
        # 測量半高寬
        hwhm_r = self.measure_hwhm(psf_r)
        hwhm_b = self.measure_hwhm(psf_b)
        
        # 計算比例
        ratio = hwhm_b / hwhm_r
        
        # 驗證：藍/紅 ≈ 1.27x（容差 1.20-1.35x）
        assert 1.20 < ratio < 1.35, f"藍/紅 HWHM 比應 ≈1.27x，實際 {ratio:.2f}x"
        print(f"✅ PSF 寬度測試通過：藍/紅 = {ratio:.2f}x（目標 1.27x）")
    
    def test_width_exponent_0_8(self, point_source):
        """驗證 (λ_ref/λ)^0.8 關係"""
        bloom_params = BloomParams(
            mode="mie_corrected",
            psf_width_exponent=0.8,
            base_sigma_core=15.0,
            reference_wavelength=550.0,
            threshold=0.0,  # 點光源無需閾值
            psf_dual_segment=False
        )
        
        # 多個波長點
        wavelengths = [450, 500, 550, 600, 650]
        widths = []
        
        for λ in wavelengths:
            psf = apply_bloom_mie_corrected(point_source, bloom_params, wavelength=λ)
            hwhm = self.measure_hwhm(psf)
            widths.append(hwhm)
        
        # 驗證 σ ∝ (λ_ref/λ)^0.8
        widths = np.array(widths)
        wavelengths = np.array(wavelengths)
        
        # 對數線性擬合：log(σ) = -0.8·log(λ) + const
        log_w = np.log(widths)
        log_λ = np.log(wavelengths)
        
        slope = np.polyfit(log_λ, log_w, 1)[0]
        
        # 驗證斜率 ≈ -0.8（容差 ±0.2）
        assert -1.0 < slope < -0.6, f"寬度指數應 ≈-0.8，實際 {slope:.2f}"
        print(f"✅ 寬度指數測試通過：q = {-slope:.2f}（目標 0.8）")


# ============================================================
# Test 3: 刀口測試（Knife-Edge MTF）
# ============================================================

class TestKnifeEdgeMTF:
    """驗證刀口測試（MTF 驗證）"""
    
    @pytest.fixture
    def bloom_params(self):
        """標準 Mie 修正參數"""
        return BloomParams(
            mode="mie_corrected",
            energy_wavelength_exponent=3.5,
            psf_width_exponent=0.8,
            reference_wavelength=550.0,
            base_scattering_ratio=0.08,
            base_sigma_core=15.0,
            threshold=0.5,
            psf_dual_segment=True,
            energy_conservation=True
        )
    
    @pytest.fixture
    def knife_edge(self):
        """刀口影像（左白右黑）"""
        img = np.zeros((1000, 1000), dtype=np.float32)
        img[:, :500] = 1.0
        return img
    
    def compute_esf_hwhm(self, esf):
        """計算邊緣擴散函數（ESF）的半高寬"""
        # 找到 0.25 和 0.75 點（10%-90% 上升距離的一半）
        peak = np.max(esf)
        valley = np.min(esf)
        quarter = valley + (peak - valley) * 0.25
        three_quarter = valley + (peak - valley) * 0.75
        
        quarter_idx = np.where(esf > quarter)[0][0] if np.any(esf > quarter) else 0
        three_quarter_idx = np.where(esf > three_quarter)[0][0] if np.any(esf > three_quarter) else len(esf) - 1
        
        hwhm = (three_quarter_idx - quarter_idx) / 2.0
        return hwhm
    
    def test_knife_edge_blue_red_ratio(self, bloom_params, knife_edge):
        """驗證藍/紅刀口 HWHM 比 ∈ [1.2, 1.4]"""
        # 對紅光和藍光分別處理
        result_r = apply_bloom_mie_corrected(knife_edge, bloom_params, wavelength=650.0)
        result_b = apply_bloom_mie_corrected(knife_edge, bloom_params, wavelength=450.0)
        
        # 提取中央區域的邊緣擴散函數（ESF）
        esf_r = np.mean(result_r[400:600, 450:550], axis=0)
        esf_b = np.mean(result_b[400:600, 450:550], axis=0)
        
        # 計算半高寬
        hwhm_r = self.compute_esf_hwhm(esf_r)
        hwhm_b = self.compute_esf_hwhm(esf_b)
        
        # 計算比例
        ratio = hwhm_b / hwhm_r
        
        # 驗證：藍/紅 HWHM ∈ [1.2, 1.4]（視覺合理範圍）
        assert 1.2 < ratio < 1.4, f"刀口 HWHM 比應 ∈ [1.2, 1.4]，實際 {ratio:.2f}"
        print(f"✅ 刀口測試通過：藍/紅 HWHM = {ratio:.2f}（目標 [1.2, 1.4]）")


# ============================================================
# Test 4: 能量守恆驗證
# ============================================================

class TestMieEnergyConservation:
    """驗證能量守恆（誤差 < 0.01%）"""
    
    @pytest.fixture
    def bloom_params(self):
        """標準 Mie 修正參數"""
        return BloomParams(
            mode="mie_corrected",
            energy_wavelength_exponent=3.5,
            psf_width_exponent=0.8,
            reference_wavelength=550.0,
            base_scattering_ratio=0.08,
            threshold=0.8,
            psf_dual_segment=True,
            energy_conservation=True
        )
    
    @pytest.mark.parametrize("wavelength", [450, 550, 650])
    def test_energy_conservation(self, bloom_params, wavelength):
        """驗證所有波長的能量守恆"""
        # 隨機測試影像
        np.random.seed(42)
        test_image = np.random.rand(500, 500).astype(np.float32)
        
        # 應用 Bloom
        result = apply_bloom_mie_corrected(test_image, bloom_params, wavelength=wavelength)
        
        # 計算能量
        energy_in = np.sum(test_image)
        energy_out = np.sum(result)
        
        # 相對誤差
        relative_error = abs(energy_in - energy_out) / (energy_in + 1e-10)
        
        # 驗證：誤差 < 0.01%
        assert relative_error < 0.0001, \
            f"λ={wavelength}nm 能量守恆誤差應 < 0.01%，實際 {relative_error * 100:.4f}%"
        print(f"✅ 能量守恆測試通過（λ={wavelength}nm）：誤差 {relative_error * 100:.4f}%")


# ============================================================
# 運行測試
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
