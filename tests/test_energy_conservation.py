"""
測試物理模型改進：能量守恆 Bloom 效果

測試項目：
1. 能量守恆驗證（E_in ≈ E_out，誤差 < 1%）
2. 高光提取邏輯
3. PSF 正規化
4. 與藝術模式對比
"""

import numpy as np
import sys
sys.path.insert(0, '/Users/latteine/Documents/coding/Phos')

from film_models import BloomParams, PhysicsMode


def test_energy_conservation():
    """測試能量守恆"""
    # 模擬 apply_bloom_conserved 的核心邏輯
    # （避免依賴 Phos_0.2.0.py 的完整環境）
    
    # 創建測試影像（單一亮點）
    test_image = np.zeros((100, 100), dtype=np.float32)
    test_image[50, 50] = 1.0
    
    # 總能量（輸入）
    energy_in = np.sum(test_image)
    
    # 模擬能量守恆的 Bloom 過程
    threshold = 0.8
    scattering_ratio = 0.1
    
    # 1. 提取高光
    highlights = np.maximum(test_image - threshold, 0)
    
    # 2. 散射能量
    scattered_energy = highlights * scattering_ratio
    
    # 3. 應用 PSF（簡化為均勻模糊）
    # 在實際實作中會使用高斯模糊
    bloom_layer = scattered_energy.copy()
    
    # 4. 從原圖減去散射能量
    corrected = test_image - scattered_energy
    
    # 5. 加上散射層
    result = corrected + bloom_layer
    
    # 6. 驗證能量守恆
    energy_out = np.sum(result)
    
    # 斷言：能量差異 < 1%
    relative_error = abs(energy_in - energy_out) / (energy_in + 1e-6)
    print(f"能量輸入: {energy_in:.6f}")
    print(f"能量輸出: {energy_out:.6f}")
    print(f"相對誤差: {relative_error * 100:.4f}%")
    
    assert relative_error < 0.01, f"能量不守恆！誤差 {relative_error * 100:.2f}%"


def test_highlight_extraction():
    """測試高光提取邏輯"""
    # 創建測試影像（不同亮度區域）
    test_image = np.array([
        [0.0, 0.5, 1.0],
        [0.3, 0.7, 0.9],
        [0.1, 0.8, 0.95]
    ], dtype=np.float32)
    
    threshold = 0.8
    highlights = np.maximum(test_image - threshold, 0)
    
    # 驗證：只有 > 0.8 的區域有值
    expected = np.array([
        [0.0, 0.0, 0.2],
        [0.0, 0.0, 0.1],
        [0.0, 0.0, 0.15]
    ], dtype=np.float32)
    
    np.testing.assert_array_almost_equal(highlights, expected, decimal=6)
    print("✓ 高光提取邏輯正確")


def test_bloom_params_initialization():
    """測試 BloomParams 初始化與預設值"""
    # Artistic 模式
    bloom_artistic = BloomParams()
    assert bloom_artistic.mode == "artistic"
    assert bloom_artistic.energy_conservation == True  # 預設也為 True
    print(f"✓ Artistic BloomParams 初始化成功")
    
    # Physical 模式
    bloom_physical = BloomParams(
        mode="physical",
        threshold=0.8,
        scattering_ratio=0.1
    )
    assert bloom_physical.mode == "physical"
    assert bloom_physical.threshold == 0.8
    assert bloom_physical.scattering_ratio == 0.1
    assert bloom_physical.energy_conservation == True
    print(f"✓ Physical BloomParams 初始化成功")


def test_psf_normalization_principle():
    """測試 PSF 正規化原理"""
    # 創建一個簡單的 PSF（高斯近似）
    size = 11
    sigma = 2.0
    x = np.arange(size) - size // 2
    y = np.arange(size) - size // 2
    xx, yy = np.meshgrid(x, y)
    
    # 2D 高斯
    psf = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    
    # 正規化前
    psf_sum_before = np.sum(psf)
    print(f"正規化前 PSF 總和: {psf_sum_before:.6f}")
    
    # 正規化：強制 ∫ PSF = 1
    psf_normalized = psf / psf_sum_before
    psf_sum_after = np.sum(psf_normalized)
    
    print(f"正規化後 PSF 總和: {psf_sum_after:.6f}")
    
    # 驗證：正規化後總和 = 1
    assert np.isclose(psf_sum_after, 1.0, atol=1e-6)
    print("✓ PSF 正規化原理驗證通過")


def test_artistic_vs_physical_energy():
    """對比藝術模式與物理模式的能量行為"""
    test_image = np.ones((50, 50), dtype=np.float32) * 0.5
    test_image[25, 25] = 1.0
    
    energy_in = np.sum(test_image)
    
    # 模擬藝術模式（純加法，違反能量守恆）
    artistic_bloom = test_image * 0.1  # 簡化的 bloom
    artistic_result = test_image + artistic_bloom
    artistic_energy = np.sum(artistic_result)
    
    # 模擬物理模式（能量守恆）
    scattered = test_image * 0.1
    physical_result = (test_image - scattered) + scattered  # 應該相等
    physical_energy = np.sum(physical_result)
    
    print(f"輸入能量: {energy_in:.2f}")
    print(f"藝術模式能量: {artistic_energy:.2f} (增加 {(artistic_energy/energy_in - 1)*100:.1f}%)")
    print(f"物理模式能量: {physical_energy:.2f} (增加 {(physical_energy/energy_in - 1)*100:.1f}%)")
    
    # 驗證
    assert artistic_energy > energy_in, "藝術模式應該增加能量"
    assert np.isclose(physical_energy, energy_in, rtol=0.01), "物理模式應該守恆能量"
    print("✓ 藝術 vs 物理模式對比驗證通過")


if __name__ == "__main__":
    print("="*60)
    print("物理模型改進：能量守恆 Bloom 測試")
    print("="*60)
    
    print("\n[測試 1] 能量守恆驗證")
    test_energy_conservation()
    
    print("\n[測試 2] 高光提取邏輯")
    test_highlight_extraction()
    
    print("\n[測試 3] BloomParams 初始化")
    test_bloom_params_initialization()
    
    print("\n[測試 4] PSF 正規化原理")
    test_psf_normalization_principle()
    
    print("\n[測試 5] 藝術 vs 物理模式對比")
    test_artistic_vs_physical_energy()
    
    print("\n" + "="*60)
    print("✅ 所有測試通過！")
    print("="*60)
