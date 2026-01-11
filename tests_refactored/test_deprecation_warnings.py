"""
測試 deprecated 函數的警告機制

驗證 v0.5.0 引入的 deprecation warnings 正確運作
"""

import warnings
import numpy as np
import pytest


def test_generate_grain_for_channel_deprecation():
    """測試 generate_grain_for_channel() 發出 DeprecationWarning"""
    from Phos import generate_grain_for_channel
    
    test_data = np.random.rand(100, 100).astype(np.float32)
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = generate_grain_for_channel(test_data, 0.5)
        
        # 檢查警告
        assert len(w) == 1, f"Expected 1 warning, got {len(w)}"
        assert issubclass(w[0].category, DeprecationWarning)
        assert "v0.5.0" in str(w[0].message)
        assert "v0.6.0" in str(w[0].message)
        assert "generate_grain" in str(w[0].message)
        
        # 檢查函數仍正常運作
        assert result is not None
        assert result.shape == test_data.shape


def test_generate_poisson_grain_deprecation():
    """測試 generate_poisson_grain() 發出 DeprecationWarning"""
    from Phos import generate_poisson_grain
    from film_models import GrainParams
    
    test_data = np.random.rand(100, 100).astype(np.float32) * 100  # Poisson needs higher values
    params = GrainParams(mode="poisson", intensity=0.5)
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = generate_poisson_grain(test_data, params)
        
        # 檢查警告
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "v0.5.0" in str(w[0].message)
        assert "generate_grain" in str(w[0].message)
        
        # 檢查函數仍正常運作
        assert result is not None
        assert result.shape == test_data.shape


def test_apply_bloom_to_channel_deprecation():
    """測試 apply_bloom_to_channel() 發出 DeprecationWarning"""
    from Phos import apply_bloom_to_channel
    
    test_data = np.random.rand(100, 100).astype(np.float32)
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = apply_bloom_to_channel(
            lux=test_data,
            sens=0.5,
            rads=10,
            strg=0.3,
            base=0.05,
            blur_scale=1,
            blur_sigma_scale=1.0
        )
        
        # 檢查警告
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "v0.5.0" in str(w[0].message)
        assert "apply_bloom" in str(w[0].message)
        
        # 檢查函數仍正常運作
        assert result is not None
        assert result.shape == test_data.shape


def test_apply_bloom_conserved_deprecation():
    """測試 apply_bloom_conserved() 發出 DeprecationWarning"""
    from Phos import apply_bloom_conserved
    from film_models import BloomParams
    
    test_data = np.random.rand(100, 100).astype(np.float32)
    params = BloomParams(mode="physical", sensitivity=0.5)
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = apply_bloom_conserved(test_data, params, blur_scale=1, blur_sigma_scale=15.0)
        
        # 檢查警告
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "v0.5.0" in str(w[0].message)
        assert "apply_bloom" in str(w[0].message)
        
        # 檢查函數仍正常運作
        assert result is not None
        assert result.shape == test_data.shape


def test_deprecated_functions_still_work():
    """
    整合測試：確認所有 deprecated 函數仍然能正常工作
    
    雖然這些函數已標記為 deprecated，但在 v0.6.0 之前必須保持功能正常
    """
    from Phos import (
        generate_grain_for_channel,
        generate_poisson_grain,
        apply_bloom_to_channel,
        apply_bloom_conserved
    )
    from film_models import GrainParams, BloomParams
    
    test_img = np.random.rand(50, 50).astype(np.float32)
    
    # 抑制警告以測試功能
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        
        # Test grain functions
        grain1 = generate_grain_for_channel(test_img, 0.5)
        assert grain1.shape == test_img.shape
        
        grain_params = GrainParams(mode="poisson", intensity=0.5)
        grain2 = generate_poisson_grain(test_img * 100, grain_params)
        assert grain2.shape == test_img.shape
        
        # Test bloom functions
        bloom1 = apply_bloom_to_channel(test_img, 0.5, 10, 0.3, 0.05, 1, 1.0)
        assert bloom1.shape == test_img.shape
        
        bloom_params = BloomParams(mode="physical", sensitivity=0.5)
        bloom2 = apply_bloom_conserved(test_img, bloom_params, 1, 15.0)
        assert bloom2.shape == test_img.shape


def test_deprecation_stacklevel():
    """
    測試 deprecation warning 的 stacklevel 參數設置正確
    
    stacklevel=2 確保警告指向調用者，而不是函數內部
    """
    from Phos import generate_grain_for_channel
    
    test_data = np.random.rand(10, 10).astype(np.float32)
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _ = generate_grain_for_channel(test_data, 0.5)
        
        # 檢查警告來源（應指向本測試檔案，而非 Phos.py 內部）
        assert len(w) == 1
        assert w[0].filename == __file__, \
            f"Warning should point to caller (this file), not Phos.py. Got: {w[0].filename}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
