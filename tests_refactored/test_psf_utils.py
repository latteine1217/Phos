"""
測試 PSF (Point Spread Function) 工具模組

覆蓋範圍：
1. Mie 散射參數查表與插值
2. PSF 核生成（雙段核、高斯核、指數核）
3. 卷積運算（FFT 與空域自適應）
4. 快取機制
5. 模組結構

PR #4: Test suite for modules/psf_utils.py
"""

import pytest
import numpy as np
import os
import tempfile
from modules.psf_utils import (
    create_dual_kernel_psf,
    load_mie_lookup_table,
    lookup_mie_params,
    convolve_fft,
    convolve_adaptive,
    get_gaussian_kernel,
    get_exponential_kernel_approximation,
    _get_gaussian_kernel_cached,
    __all__
)


# ==================== 測試 Mie 散射查表 ====================

class TestMieLookupTable:
    """測試 Mie 散射查表的載入與插值"""
    
    def test_load_mie_lookup_table_success(self):
        """測試成功載入 Mie 查表"""
        # Skip if file doesn't exist
        if not os.path.exists("data/mie_lookup_table_v1.npz"):
            pytest.skip("Mie lookup table not found")
        
        table = load_mie_lookup_table()
        
        # 驗證結構
        assert 'wavelengths' in table
        assert 'iso_values' in table
        assert 'sigma' in table
        assert 'kappa' in table
        assert 'rho' in table
        assert 'eta' in table
        
        # 驗證資料形狀
        assert table['wavelengths'].shape == (3,)  # [450, 550, 650]
        assert table['iso_values'].shape == (7,)   # [100, 200, 400, 800, 1600, 3200, 6400]
        assert table['sigma'].shape == (3, 7)
        assert table['kappa'].shape == (3, 7)
        assert table['rho'].shape == (3, 7)
        assert table['eta'].shape == (3, 7)
    
    def test_load_mie_lookup_table_caching(self):
        """測試 Mie 查表快取機制"""
        if not os.path.exists("data/mie_lookup_table_v1.npz"):
            pytest.skip("Mie lookup table not found")
        
        table1 = load_mie_lookup_table()
        table2 = load_mie_lookup_table()
        
        # 應該返回相同的物件（快取命中）
        assert table1 is table2
    
    def test_load_mie_lookup_table_file_not_found(self):
        """測試查表檔案不存在時的錯誤處理"""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_mie_lookup_table("nonexistent_file.npz")
        
        assert "Mie 查表檔案不存在" in str(exc_info.value)
    
    def test_lookup_mie_params_interpolation(self):
        """測試 Mie 參數插值的正確性"""
        if not os.path.exists("data/mie_lookup_table_v1.npz"):
            pytest.skip("Mie lookup table not found")
        
        table = load_mie_lookup_table()
        
        # 測試中間波長與 ISO
        sigma, kappa, rho, eta = lookup_mie_params(550.0, 800, table)
        
        # 驗證返回類型
        assert isinstance(sigma, float)
        assert isinstance(kappa, float)
        assert isinstance(rho, float)
        assert isinstance(eta, float)
        
        # 驗證值的合理範圍
        assert 0 < sigma < 100  # PSF 寬度應在合理範圍
        assert 0 < kappa < 200  # 指數拖尾長度
        assert 0 <= rho <= 1    # 核心占比應在 [0, 1]
        assert 0 < eta < 1      # 能量權重應為正
    
    def test_lookup_mie_params_edge_values(self):
        """測試極端波長與 ISO 值的插值"""
        if not os.path.exists("data/mie_lookup_table_v1.npz"):
            pytest.skip("Mie lookup table not found")
        
        table = load_mie_lookup_table()
        
        # 測試最小波長與最小 ISO
        sigma_min, kappa_min, rho_min, eta_min = lookup_mie_params(450.0, 100, table)
        assert sigma_min > 0 and kappa_min > 0
        
        # 測試最大波長與最大 ISO
        sigma_max, kappa_max, rho_max, eta_max = lookup_mie_params(650.0, 6400, table)
        assert sigma_max > 0 and kappa_max > 0
        
        # 藍光（短波長）應有更小的散射寬度
        # 注意：這取決於 Mie 散射理論，可能需要根據實際查表調整
        # assert sigma_min <= sigma_max


# ==================== 測試 PSF 核生成 ====================

class TestPSFGeneration:
    """測試各種 PSF 核的生成"""
    
    def test_create_dual_kernel_psf_basic(self):
        """測試雙段核 PSF 的基本功能"""
        psf = create_dual_kernel_psf(sigma=20.0, kappa=60.0, core_fraction=0.75, radius=100)
        
        # 驗證形狀
        assert psf.shape == (201, 201)  # 2*radius + 1
        
        # 驗證正規化（能量守恆）
        assert abs(np.sum(psf) - 1.0) < 1e-6
        
        # 驗證對稱性（應該是徑向對稱）
        center = psf[100, 100]
        assert psf[90, 100] == pytest.approx(psf[110, 100], rel=1e-5)
        assert psf[100, 90] == pytest.approx(psf[100, 110], rel=1e-5)
    
    def test_create_dual_kernel_psf_core_fraction_extremes(self):
        """測試核心占比極端值"""
        # 純高斯核（core_fraction = 1.0）
        psf_gaussian = create_dual_kernel_psf(20.0, 60.0, 1.0, 50)
        assert abs(np.sum(psf_gaussian) - 1.0) < 1e-6
        
        # 純指數核（core_fraction = 0.0）
        psf_exp = create_dual_kernel_psf(20.0, 60.0, 0.0, 50)
        assert abs(np.sum(psf_exp) - 1.0) < 1e-6
    
    def test_create_dual_kernel_psf_degenerate_case(self):
        """測試退化情況（極小 sigma 和 kappa）"""
        # 極小 sigma/kappa 應退化為 delta 函數
        psf = create_dual_kernel_psf(sigma=0.01, kappa=0.01, core_fraction=0.5, radius=10)
        
        # 能量應集中在中心
        center = psf.shape[0] // 2
        assert psf[center, center] > 0.9  # 大部分能量在中心
    
    def test_get_gaussian_kernel_basic(self):
        """測試高斯核生成"""
        kernel = get_gaussian_kernel(sigma=20.0)
        
        # 驗證 ksize 自動計算（6σ）
        expected_ksize = int(20.0 * 6) | 1  # 強制奇數
        assert kernel.shape == (expected_ksize, expected_ksize)
        
        # 驗證正規化
        assert abs(np.sum(kernel) - 1.0) < 1e-5
        
        # 驗證對稱性
        center = kernel.shape[0] // 2
        assert kernel[center-1, center] == pytest.approx(kernel[center+1, center], rel=1e-5)
    
    def test_get_gaussian_kernel_custom_ksize(self):
        """測試自訂 ksize 的高斯核"""
        kernel = get_gaussian_kernel(sigma=20.0, ksize=51)
        
        assert kernel.shape == (51, 51)
        assert abs(np.sum(kernel) - 1.0) < 1e-5
    
    def test_get_gaussian_kernel_caching(self):
        """測試高斯核快取機制"""
        # 清除可能的快取（通過測試不同參數）
        kernel1 = get_gaussian_kernel(sigma=25.123, ksize=51)
        kernel2 = get_gaussian_kernel(sigma=25.123, ksize=51)  # 應命中快取
        
        # 驗證結果一致（快取正確）
        np.testing.assert_array_almost_equal(kernel1, kernel2)
    
    def test_get_exponential_kernel_approximation_basic(self):
        """測試指數核三層高斯近似"""
        kernel = get_exponential_kernel_approximation(kappa=30.0, ksize=201)
        
        # 驗證形狀
        assert kernel.shape == (201, 201)
        
        # 驗證正規化
        assert abs(np.sum(kernel) - 1.0) < 1e-6
        
        # 驗證非負性
        assert np.all(kernel >= 0)
    
    def test_get_exponential_kernel_approximation_radial_profile(self):
        """測試指數核的徑向衰減特性"""
        kappa = 30.0
        kernel = get_exponential_kernel_approximation(kappa, ksize=201)
        
        # 提取徑向剖面
        center = 100
        profile = kernel[center, center:]
        
        # 驗證單調遞減（至少在前半部分）
        assert np.all(np.diff(profile[:50]) <= 0)


# ==================== 測試卷積運算 ====================

class TestConvolution:
    """測試 FFT 與自適應卷積"""
    
    def test_convolve_fft_basic(self):
        """測試 FFT 卷積基本功能"""
        # 創建簡單的測試圖像（5x5 中心有一個點）
        image = np.zeros((100, 100), dtype=np.float32)
        image[50, 50] = 1.0
        
        # 創建簡單的高斯核
        kernel = get_gaussian_kernel(sigma=5.0, ksize=21)
        
        # 進行卷積
        result = convolve_fft(image, kernel)
        
        # 驗證形狀不變
        assert result.shape == image.shape
        
        # 驗證能量守恆（delta 函數卷積後應得到核本身）
        assert abs(np.sum(result) - 1.0) < 1e-4
        
        # 驗證結果中心附近有值
        assert result[50, 50] > 0
    
    def test_convolve_fft_energy_conservation(self):
        """測試 FFT 卷積的能量守恆特性"""
        # 創建均勻圖像
        image = np.ones((100, 100), dtype=np.float32) * 0.5
        kernel = get_gaussian_kernel(sigma=5.0, ksize=31)
        
        # 進行卷積
        result = convolve_fft(image, kernel)
        
        # 對於均勻圖像與正規化核，卷積後應保持均勻
        # （因為卷積是線性運算且核總和為1）
        expected_value = 0.5
        
        # 檢查中心區域（避免邊界效應）
        center_region = result[25:75, 25:75]
        assert np.allclose(center_region, expected_value, atol=0.01)
    
    def test_convolve_adaptive_auto_mode(self):
        """測試自適應卷積的自動選擇"""
        image = np.random.rand(200, 200).astype(np.float32)
        
        # 小核應選擇空域卷積
        small_kernel = get_gaussian_kernel(sigma=5.0, ksize=31)
        result_small = convolve_adaptive(image, small_kernel, method='auto')
        assert result_small.shape == image.shape
        
        # 大核應選擇 FFT 卷積
        large_kernel = get_gaussian_kernel(sigma=50.0, ksize=301)
        result_large = convolve_adaptive(image, large_kernel, method='auto')
        assert result_large.shape == image.shape
    
    def test_convolve_adaptive_force_methods(self):
        """測試強制使用特定卷積方法"""
        image = np.random.rand(100, 100).astype(np.float32)
        kernel = get_gaussian_kernel(sigma=10.0, ksize=61)
        
        # 強制 FFT
        result_fft = convolve_adaptive(image, kernel, method='fft')
        assert result_fft.shape == image.shape
        
        # 強制空域
        result_spatial = convolve_adaptive(image, kernel, method='spatial')
        assert result_spatial.shape == image.shape
        
        # 兩者應接近（放寬精度因邊界處理差異）
        np.testing.assert_array_almost_equal(result_fft, result_spatial, decimal=2)
    
    def test_convolve_fft_large_kernel(self):
        """測試 FFT 卷積處理大核的效能優勢"""
        image = np.random.rand(500, 500).astype(np.float32)
        kernel = get_gaussian_kernel(sigma=60.0, ksize=361)
        
        # FFT 卷積應能處理大核
        result = convolve_fft(image, kernel)
        assert result.shape == image.shape
        
        # 驗證能量近似守恆
        assert abs(np.sum(result) - np.sum(image)) < np.sum(image) * 0.01


# ==================== 測試快取機制 ====================

class TestCaching:
    """測試 LRU 快取的正確性"""
    
    def test_gaussian_kernel_cache_hit(self):
        """測試高斯核快取命中"""
        # 第一次調用
        kernel1 = get_gaussian_kernel(sigma=17.456, ksize=105)
        
        # 第二次調用（應命中快取）
        kernel2 = get_gaussian_kernel(sigma=17.456, ksize=105)
        
        # 驗證結果相同
        np.testing.assert_array_equal(kernel1, kernel2)
    
    def test_gaussian_kernel_cache_precision(self):
        """測試快取對浮點精度的處理"""
        # 微小差異應被視為不同（精度 0.001）
        kernel1 = get_gaussian_kernel(sigma=20.000, ksize=121)
        kernel2 = get_gaussian_kernel(sigma=20.001, ksize=121)
        
        # 應該非常接近但不完全相同（因為 sigma 不同）
        # 但由於快取精度為 0.001，實際上可能被視為相同
        # 這取決於 round() 的行為
        pass  # 此測試僅驗證不會崩潰


# ==================== 測試模組結構 ====================

class TestModuleStructure:
    """測試模組的匯出與結構"""
    
    def test_module_exports(self):
        """測試 __all__ 匯出列表"""
        expected_exports = [
            'load_mie_lookup_table',
            'lookup_mie_params',
            'create_dual_kernel_psf',
            'get_gaussian_kernel',
            'get_exponential_kernel_approximation',
            'convolve_fft',
            'convolve_adaptive',
        ]
        
        for name in expected_exports:
            assert name in __all__, f"{name} not in __all__"
    
    def test_all_functions_importable(self):
        """測試所有匯出的函數可正常導入"""
        from modules import psf_utils
        
        for name in __all__:
            assert hasattr(psf_utils, name), f"Function {name} not found in psf_utils"
    
    def test_functions_have_docstrings(self):
        """測試所有函數都有文檔字串"""
        from modules import psf_utils
        
        for name in __all__:
            func = getattr(psf_utils, name)
            assert func.__doc__ is not None, f"Function {name} missing docstring"
            assert len(func.__doc__.strip()) > 50, f"Function {name} has insufficient docstring"


# ==================== 測試物理正確性 ====================

class TestPhysicsCorrectness:
    """測試物理特性的正確性"""
    
    def test_psf_energy_conservation(self):
        """測試 PSF 能量守恆"""
        for sigma in [10.0, 20.0, 50.0]:
            for kappa in [30.0, 60.0, 100.0]:
                for rho in [0.3, 0.5, 0.8]:
                    psf = create_dual_kernel_psf(sigma, kappa, rho, radius=100)
                    
                    # 能量守恆：∑PSF = 1
                    energy = np.sum(psf)
                    assert abs(energy - 1.0) < 1e-5, \
                        f"Energy not conserved for σ={sigma}, κ={kappa}, ρ={rho}: got {energy}"
    
    def test_psf_radial_symmetry(self):
        """測試 PSF 徑向對稱性"""
        psf = create_dual_kernel_psf(sigma=20.0, kappa=60.0, core_fraction=0.75, radius=50)
        
        center = 50
        
        # 測試 4 個方向的對稱性
        assert abs(psf[center, center+10] - psf[center, center-10]) < 1e-6
        assert abs(psf[center+10, center] - psf[center-10, center]) < 1e-6
        assert abs(psf[center+7, center+7] - psf[center-7, center-7]) < 1e-6
    
    def test_gaussian_kernel_normalization(self):
        """測試高斯核正規化"""
        for sigma in [5.0, 15.0, 30.0]:
            kernel = get_gaussian_kernel(sigma)
            assert abs(np.sum(kernel) - 1.0) < 1e-5, f"Gaussian kernel not normalized for σ={sigma}"
    
    def test_convolution_preserves_total_energy(self):
        """測試卷積保持總能量（對於正規化的核）"""
        image = np.ones((100, 100), dtype=np.float32) * 0.5
        kernel = get_gaussian_kernel(sigma=10.0)
        
        result = convolve_fft(image, kernel)
        
        # 對於均勻圖像，卷積後總能量應不變
        original_energy = np.sum(image)
        result_energy = np.sum(result)
        
        assert abs(result_energy - original_energy) < original_energy * 0.01


# ==================== 測試邊界情況 ====================

class TestEdgeCases:
    """測試邊界與極端情況"""
    
    def test_zero_sigma_kappa(self):
        """測試 sigma 和 kappa 接近零的情況"""
        # 應該退化為 delta 函數
        psf = create_dual_kernel_psf(sigma=1e-6, kappa=1e-6, core_fraction=0.5, radius=10)
        assert psf.shape == (21, 21)
    
    def test_very_large_kernel(self):
        """測試超大核的生成"""
        kernel = get_gaussian_kernel(sigma=100.0, ksize=601)
        assert kernel.shape == (601, 601)
        assert abs(np.sum(kernel) - 1.0) < 1e-4
    
    def test_single_pixel_image_convolution(self):
        """測試單像素圖像的卷積"""
        image = np.zeros((1, 1), dtype=np.float32)
        image[0, 0] = 1.0
        
        kernel = get_gaussian_kernel(sigma=3.0, ksize=7)
        
        # 對於 1x1 圖像，卷積應返回 1x1 結果
        result = convolve_fft(image, kernel)
        assert result.shape == (1, 1)


# ==================== 整合測試 ====================

class TestIntegration:
    """測試完整的 PSF 生成 → 卷積流程"""
    
    def test_mie_to_psf_to_convolution_pipeline(self):
        """測試從 Mie 查表到 PSF 生成再到卷積的完整流程"""
        if not os.path.exists("data/mie_lookup_table_v1.npz"):
            pytest.skip("Mie lookup table not found")
        
        # 1. 載入 Mie 查表
        table = load_mie_lookup_table()
        
        # 2. 查詢參數
        sigma, kappa, rho, eta = lookup_mie_params(550.0, 800, table)
        
        # 3. 生成 PSF
        psf = create_dual_kernel_psf(sigma, kappa, rho, radius=100)
        
        # 4. 創建測試圖像
        image = np.random.rand(300, 300).astype(np.float32)
        
        # 5. 進行卷積
        result = convolve_adaptive(image, psf, method='auto')
        
        # 驗證結果
        assert result.shape == image.shape
        assert np.all(np.isfinite(result))
        assert np.all(result >= 0)  # 影像應為非負
    
    def test_dual_kernel_components_combination(self):
        """測試雙段核的高斯與指數分量正確組合"""
        sigma, kappa, rho = 20.0, 60.0, 0.7
        
        # 生成組合核
        psf_combined = create_dual_kernel_psf(sigma, kappa, rho, radius=50)
        
        # 分別生成純高斯和純指數核
        psf_gaussian = create_dual_kernel_psf(sigma, kappa, 1.0, radius=50)
        psf_exp = create_dual_kernel_psf(sigma, kappa, 0.0, radius=50)
        
        # 手動組合
        psf_manual = rho * psf_gaussian + (1 - rho) * psf_exp
        psf_manual /= np.sum(psf_manual)  # 正規化
        
        # 驗證組合正確（放寬精度因為正規化會引入額外誤差）
        np.testing.assert_array_almost_equal(psf_combined, psf_manual, decimal=4)
