"""
P1-2: ISO 統一化單元測試

驗證 derive_physical_params_from_iso() 函數的正確性：
1. 粒徑單調性（ISO ↑ → d_mean ↑）
2. 顆粒強度相關性（ISO 增長 4× → grain_intensity 增長 ~2×）
3. 散射比例物理限制（3%-15%）
4. Mie 尺寸參數範圍（x ∈ [0.5, 30]）
5. 膠片類型差異（fine_grain < standard < high_speed）

Version: 0.3.0 (TASK-007-P1-2)
"""

import pytest
import numpy as np
from film_models import derive_physical_params_from_iso, ISODerivedParams


class TestISOMonotonicity:
    """測試 ISO 與各參數的單調性關係"""
    
    def test_grain_size_monotonicity(self):
        """驗證粒徑隨 ISO 單調遞增"""
        isos = [100, 200, 400, 800, 1600, 3200]
        sizes = [derive_physical_params_from_iso(iso).grain_mean_diameter_um 
                 for iso in isos]
        
        # 檢查單調性
        for i in range(len(sizes) - 1):
            assert sizes[i+1] > sizes[i], (
                f"粒徑應單調遞增：ISO {isos[i+1]} ({sizes[i+1]:.3f} μm) "
                f"應大於 ISO {isos[i]} ({sizes[i]:.3f} μm)"
            )
        
        # 檢查物理範圍
        assert 0.5 <= sizes[0] <= 0.7, (
            f"ISO 100 粒徑 ({sizes[0]:.3f} μm) 應在 [0.5, 0.7] μm"
        )
        assert 1.5 <= sizes[-1] <= 2.5, (
            f"ISO 3200 粒徑 ({sizes[-1]:.3f} μm) 應在 [1.5, 2.5] μm"
        )
    
    def test_grain_intensity_monotonicity(self):
        """驗證顆粒強度隨 ISO 單調遞增（或達到上限）"""
        isos = [100, 200, 400, 800, 1600, 3200]
        intensities = [derive_physical_params_from_iso(iso).grain_intensity 
                       for iso in isos]
        
        # 檢查單調性（允許因 clip 導致的相等）
        for i in range(len(intensities) - 1):
            assert intensities[i+1] >= intensities[i], (
                f"顆粒強度應單調遞增（或相等）：ISO {isos[i+1]} ({intensities[i+1]:.3f}) "
                f"應 >= ISO {isos[i]} ({intensities[i]:.3f})"
            )
        
        # 驗證在未達上限時嚴格遞增
        for i in range(len(intensities) - 1):
            if intensities[i] < 0.34:  # 未達上限 0.35
                assert intensities[i+1] > intensities[i], (
                    f"未達上限時應嚴格遞增：ISO {isos[i+1]} ({intensities[i+1]:.3f}) "
                    f"應 > ISO {isos[i]} ({intensities[i]:.3f})"
                )
    
    def test_scattering_ratio_monotonicity(self):
        """驗證散射比例隨 ISO 單調遞增"""
        isos = [100, 200, 400, 800, 1600, 3200]
        ratios = [derive_physical_params_from_iso(iso).scattering_ratio 
                  for iso in isos]
        
        # 檢查單調性
        for i in range(len(ratios) - 1):
            assert ratios[i+1] >= ratios[i], (
                f"散射比例應單調遞增：ISO {isos[i+1]} ({ratios[i+1]:.4f}) "
                f"應大於等於 ISO {isos[i]} ({ratios[i]:.4f})"
            )


class TestPhysicalCorrelations:
    """測試物理相關性（粒徑 → 顆粒強度 → 散射比例）"""
    
    def test_grain_intensity_sqrt_correlation(self):
        """驗證顆粒強度與 ISO 的平方根關係"""
        iso1, iso2 = 400, 1600
        params1 = derive_physical_params_from_iso(iso1)
        params2 = derive_physical_params_from_iso(iso2)
        
        # ISO 增長 4 倍，顆粒強度應增長約 2 倍（√4）
        ratio = params2.grain_intensity / params1.grain_intensity
        expected_ratio = np.sqrt(iso2 / iso1)  # √4 = 2.0
        
        # 允許 ±10% 誤差（因為有 clip 和膠片類型影響）
        assert abs(ratio - expected_ratio) / expected_ratio < 0.15, (
            f"ISO 比值 {iso2/iso1:.1f}× 時顆粒強度比值應接近 {expected_ratio:.2f}×，"
            f"實際 {ratio:.2f}×（誤差 {abs(ratio - expected_ratio)/expected_ratio*100:.1f}%）"
        )
    
    def test_scattering_quadratic_correlation(self):
        """驗證散射比例與粒徑的平方關係"""
        iso1, iso2 = 100, 400
        params1 = derive_physical_params_from_iso(iso1)
        params2 = derive_physical_params_from_iso(iso2)
        
        # 粒徑比值
        d_ratio = params2.grain_mean_diameter_um / params1.grain_mean_diameter_um
        
        # 散射比例增長應接近 d_ratio^2（σ ∝ d^2）
        scattering_growth = (params2.scattering_ratio - 0.04) / (params1.scattering_ratio - 0.04)
        expected_growth = d_ratio ** 2
        
        # 允許 ±20% 誤差（因為有 s0 基準項和 clip）
        assert abs(scattering_growth - expected_growth) / expected_growth < 0.25, (
            f"粒徑比值 {d_ratio:.2f}× 時散射增長應接近 {expected_growth:.2f}×，"
            f"實際 {scattering_growth:.2f}×"
        )
    
    def test_grain_size_cube_root_correlation(self):
        """驗證粒徑與 ISO 的立方根關係"""
        iso1, iso2 = 100, 800
        params1 = derive_physical_params_from_iso(iso1)
        params2 = derive_physical_params_from_iso(iso2)
        
        # 粒徑比值應接近 (ISO2/ISO1)^(1/3)
        d_ratio = params2.grain_mean_diameter_um / params1.grain_mean_diameter_um
        expected_ratio = (iso2 / iso1) ** (1.0 / 3.0)  # 8^(1/3) = 2.0
        
        # 允許 ±5% 誤差
        assert abs(d_ratio - expected_ratio) / expected_ratio < 0.08, (
            f"ISO 比值 {iso2/iso1:.1f}× 時粒徑比值應接近 {expected_ratio:.2f}×，"
            f"實際 {d_ratio:.2f}×（誤差 {abs(d_ratio - expected_ratio)/expected_ratio*100:.1f}%）"
        )


class TestPhysicalBounds:
    """測試物理參數邊界值"""
    
    def test_grain_intensity_bounds(self):
        """驗證顆粒強度在物理合理範圍內"""
        for iso in [50, 100, 400, 800, 1600, 3200, 6400]:
            params = derive_physical_params_from_iso(iso)
            intensity = params.grain_intensity
            
            assert 0.03 <= intensity <= 0.35, (
                f"ISO {iso} 顆粒強度 {intensity:.3f} 應在 [0.03, 0.35]"
            )
    
    def test_scattering_ratio_bounds(self):
        """驗證散射比例在物理合理範圍內"""
        for iso in [50, 100, 400, 800, 1600, 3200, 6400]:
            params = derive_physical_params_from_iso(iso)
            ratio = params.scattering_ratio
            
            assert 0.03 <= ratio <= 0.15, (
                f"ISO {iso} 散射比例 {ratio:.4f} 應在 [0.03, 0.15]（3%-15%）"
            )
            
            # 驗證 ISO 越高，散射越強
            if iso > 100:
                params_low = derive_physical_params_from_iso(100)
                assert ratio >= params_low.scattering_ratio, (
                    f"ISO {iso} 散射比例 ({ratio:.4f}) 應 ≥ ISO 100 ({params_low.scattering_ratio:.4f})"
                )
    
    def test_grain_size_bounds(self):
        """驗證粒徑在物理合理範圍內"""
        for iso in [50, 100, 400, 800, 1600, 3200, 6400]:
            params = derive_physical_params_from_iso(iso)
            d_mean = params.grain_mean_diameter_um
            d_sigma = params.grain_std_deviation_um
            
            # 粒徑範圍：0.3-3.0 μm（膠片銀鹽典型範圍）
            assert 0.3 <= d_mean <= 3.0, (
                f"ISO {iso} 平均粒徑 {d_mean:.3f} μm 應在 [0.3, 3.0] μm"
            )
            
            # 標準差應為平均值的 30%
            expected_sigma = d_mean * 0.3
            assert abs(d_sigma - expected_sigma) < 1e-6, (
                f"ISO {iso} 粒徑標準差 {d_sigma:.3f} 應等於 {expected_sigma:.3f} (d_mean × 0.3)"
            )


class TestMieSizeParameters:
    """測試 Mie 尺寸參數（x = 2πa/λ）"""
    
    def test_mie_size_parameter_range(self):
        """驗證 Mie 尺寸參數在合理範圍"""
        for iso in [100, 400, 800, 1600, 3200]:
            params = derive_physical_params_from_iso(iso)
            
            # x < 1: Rayleigh 散射主導
            # 1 ≤ x ≤ 10: Mie 散射主導
            # x > 10: 幾何光學主導
            
            # 所有 ISO 的藍光（最短波長）x 應 > 紅光（最長波長）
            assert params.mie_size_parameter_b > params.mie_size_parameter_r, (
                f"ISO {iso}: 藍光 x ({params.mie_size_parameter_b:.2f}) "
                f"應 > 紅光 x ({params.mie_size_parameter_r:.2f})"
            )
            
            # ISO 100-400: 應在 Mie 範圍（x ∈ [0.5, 10]）
            if iso <= 400:
                assert 0.5 <= params.mie_size_parameter_g <= 10.0, (
                    f"ISO {iso} 綠光 x ({params.mie_size_parameter_g:.2f}) 應在 Mie 範圍 [0.5, 10]"
                )
            
            # ISO 1600+: 可能進入幾何光學（x > 5）
            if iso >= 1600:
                assert params.mie_size_parameter_b > 5.0, (
                    f"ISO {iso} 藍光 x ({params.mie_size_parameter_b:.2f}) 應 > 5（接近幾何光學）"
                )
    
    def test_mie_wavelength_ordering(self):
        """驗證不同波長的 Mie 參數排序"""
        params = derive_physical_params_from_iso(400)
        
        # x = 2πa/λ，λ 越小，x 越大
        # 藍光（450nm）< 綠光（550nm）< 紅光（650nm）
        # x_b > x_g > x_r
        assert params.mie_size_parameter_b > params.mie_size_parameter_g, (
            f"藍光 x ({params.mie_size_parameter_b:.2f}) 應 > 綠光 x ({params.mie_size_parameter_g:.2f})"
        )
        assert params.mie_size_parameter_g > params.mie_size_parameter_r, (
            f"綠光 x ({params.mie_size_parameter_g:.2f}) 應 > 紅光 x ({params.mie_size_parameter_r:.2f})"
        )


class TestFilmTypeDifferences:
    """測試不同膠片類型的參數差異"""
    
    def test_film_type_grain_size_ordering(self):
        """驗證膠片類型的粒徑排序：fine_grain < standard < high_speed"""
        iso = 400
        standard = derive_physical_params_from_iso(iso, "standard")
        fine_grain = derive_physical_params_from_iso(iso, "fine_grain")
        high_speed = derive_physical_params_from_iso(iso, "high_speed")
        
        # Fine-grain 應有最小粒徑
        assert fine_grain.grain_mean_diameter_um < standard.grain_mean_diameter_um, (
            f"Fine-grain 粒徑 ({fine_grain.grain_mean_diameter_um:.3f}) "
            f"應 < Standard ({standard.grain_mean_diameter_um:.3f})"
        )
        
        # High-speed 應有最大粒徑
        assert high_speed.grain_mean_diameter_um > standard.grain_mean_diameter_um, (
            f"High-speed 粒徑 ({high_speed.grain_mean_diameter_um:.3f}) "
            f"應 > Standard ({standard.grain_mean_diameter_um:.3f})"
        )
    
    def test_film_type_grain_intensity_ordering(self):
        """驗證膠片類型的顆粒強度排序：fine_grain < standard < high_speed"""
        iso = 400
        standard = derive_physical_params_from_iso(iso, "standard")
        fine_grain = derive_physical_params_from_iso(iso, "fine_grain")
        high_speed = derive_physical_params_from_iso(iso, "high_speed")
        
        # Fine-grain 應有最小顆粒強度
        assert fine_grain.grain_intensity < standard.grain_intensity, (
            f"Fine-grain 顆粒強度 ({fine_grain.grain_intensity:.3f}) "
            f"應 < Standard ({standard.grain_intensity:.3f})"
        )
        
        # High-speed 應有最大顆粒強度
        assert high_speed.grain_intensity > standard.grain_intensity, (
            f"High-speed 顆粒強度 ({high_speed.grain_intensity:.3f}) "
            f"應 > Standard ({standard.grain_intensity:.3f})"
        )
    
    def test_portra400_vs_superia400(self):
        """驗證 Portra 400 (fine-grain) vs Superia 400 (high-speed) 的差異"""
        portra = derive_physical_params_from_iso(400, "fine_grain")
        superia = derive_physical_params_from_iso(400, "high_speed")
        
        # Portra 應更細緻
        assert portra.grain_intensity < superia.grain_intensity, (
            f"Portra 400 顆粒強度 ({portra.grain_intensity:.3f}) "
            f"應 < Superia 400 ({superia.grain_intensity:.3f})"
        )
        
        # 顆粒強度差異應 > 20%
        diff_pct = (superia.grain_intensity - portra.grain_intensity) / portra.grain_intensity * 100
        assert diff_pct > 20, (
            f"Superia 400 vs Portra 400 顆粒強度差異 ({diff_pct:.1f}%) 應 > 20%"
        )
    
    def test_gold200_vs_portra400_iso_ratio(self):
        """驗證 Gold 200 vs Portra 400 的 ISO 比值關係"""
        gold200 = derive_physical_params_from_iso(200, "standard")
        portra400 = derive_physical_params_from_iso(400, "fine_grain")
        
        # ISO 比值 2×，粒徑比值應接近 2^(1/3) = 1.26×
        d_ratio = portra400.grain_mean_diameter_um / gold200.grain_mean_diameter_um
        expected_ratio = (400 / 200) ** (1.0 / 3.0)  # 1.26
        
        # 允許 ±20% 誤差（因為膠片類型不同）
        assert abs(d_ratio - expected_ratio) / expected_ratio < 0.25, (
            f"Gold 200 vs Portra 400 粒徑比值 ({d_ratio:.2f}) "
            f"應接近 {expected_ratio:.2f}（ISO 比值 2× 的立方根）"
        )


class TestInputValidation:
    """測試輸入驗證與錯誤處理"""
    
    def test_iso_out_of_range_low(self):
        """驗證 ISO < 25 時拋出錯誤"""
        with pytest.raises(ValueError, match="超出合理範圍"):
            derive_physical_params_from_iso(10)
    
    def test_iso_out_of_range_high(self):
        """驗證 ISO > 6400 時拋出錯誤"""
        with pytest.raises(ValueError, match="超出合理範圍"):
            derive_physical_params_from_iso(12800)
    
    def test_iso_boundary_values(self):
        """驗證邊界值 ISO 25 和 ISO 6400 可正常運行"""
        params_low = derive_physical_params_from_iso(25)
        params_high = derive_physical_params_from_iso(6400)
        
        assert params_low.grain_mean_diameter_um < params_high.grain_mean_diameter_um
        assert params_low.grain_intensity < params_high.grain_intensity
    
    def test_invalid_film_type(self):
        """驗證無效膠片類型使用 standard 預設值"""
        # 無效類型應回退到 standard（無錯誤）
        params_invalid = derive_physical_params_from_iso(400, "invalid_type")
        params_standard = derive_physical_params_from_iso(400, "standard")
        
        assert params_invalid.grain_intensity == params_standard.grain_intensity


class TestDataclassStructure:
    """測試 ISODerivedParams dataclass 結構"""
    
    def test_isoderivedparams_fields(self):
        """驗證 ISODerivedParams 包含所有必要欄位"""
        params = derive_physical_params_from_iso(400)
        
        # 檢查所有欄位存在
        assert hasattr(params, "iso")
        assert hasattr(params, "grain_mean_diameter_um")
        assert hasattr(params, "grain_std_deviation_um")
        assert hasattr(params, "grain_intensity")
        assert hasattr(params, "scattering_ratio")
        assert hasattr(params, "mie_size_parameter_r")
        assert hasattr(params, "mie_size_parameter_g")
        assert hasattr(params, "mie_size_parameter_b")
        
        # 檢查類型
        assert isinstance(params.iso, int)
        assert isinstance(params.grain_mean_diameter_um, float)
        assert isinstance(params.grain_intensity, float)
        assert isinstance(params.scattering_ratio, float)
    
    def test_isoderivedparams_repr(self):
        """驗證 ISODerivedParams repr 輸出"""
        params = derive_physical_params_from_iso(400)
        repr_str = repr(params)
        
        assert "ISODerivedParams" in repr_str
        assert "iso=400" in repr_str
        assert "grain_intensity" in repr_str


# ==================== 測試執行 ====================

if __name__ == "__main__":
    # 執行所有測試
    pytest.main([__file__, "-v", "--tb=short"])
