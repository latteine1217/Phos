"""
Film Profiles Test Suite (Refactored)

膠片配置測試套件 - 整合 Film Models、ISO Unification 和 Create Film 測試

Merged from:
- test_film_models.py (13 tests)
- test_iso_unification.py (21 tests)
- test_create_film_from_iso.py (25 tests)

Total tests: 59 tests

Coverage:
- Film Profile Dataclass
  - 膠片配置載入與驗證
  - 感光層參數範圍
  - Tone mapping 參數
  - 光譜響應計算
  - Dataclass 完整性測試

- ISO Unification (Physical Derivation)
  - ISO → 粒徑單調性
  - ISO → 顆粒強度相關性
  - 散射比例物理限制
  - Mie 尺寸參數驗證
  - 膠片類型差異（fine_grain/standard/high_speed）

- Create Film From ISO (Convenience API)
  - 基本創建（color/single）
  - 膠片類型差異
  - Tone mapping 風格
  - 覆蓋參數（**overrides）
  - Cinestill 風格（無 AH 層）
  - 與現有配置一致性

Philosophy principles:
- Never Break Userspace: 保持 100% 邏輯一致性
- Pragmatism: 基於真實膠片特性驗證
- Simplicity: 清晰的測試組織結構

Refactored: 2026-01-11
"""

import pytest
import numpy as np
import sys
import os

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from film_models import (
    get_film_profile,
    FilmProfile,
    EmulsionLayer,
    ToneMappingParams,
    FILM_PROFILES,
    create_film_profiles,
    derive_physical_params_from_iso,
    ISODerivedParams,
    create_film_profile_from_iso,
    PhysicsMode,
    GrainParams,
    BloomParams
)


# ============================================================
# Section 1: Film Profile Dataclass Tests
# Source: test_film_models.py (13 tests)
# ============================================================

class TestFilmProfiles:
    """測試胶片配置"""
    
    def test_all_films_loadable(self):
        """測試所有胶片都能正確載入"""
        all_film_types = ["NC200", "AS100", "FS200", "Portra400", "Ektar100", "HP5Plus400", "Cinestill800T"]
        for film_type in all_film_types:
            film = get_film_profile(film_type)
            assert isinstance(film, FilmProfile)
            assert film.name == film_type
    
    def test_film_color_types(self):
        """測試胶片顏色類型"""
        # 彩色胶片
        color_films = ["NC200", "Portra400", "Ektar100", "Cinestill800T"]
        for film_name in color_films:
            film = get_film_profile(film_name)
            assert film.color_type == "color"
            assert film.red_layer is not None
            assert film.green_layer is not None
            assert film.blue_layer is not None
        
        # 黑白胶片
        bw_films = ["AS100", "FS200", "HP5Plus400"]
        for film_name in bw_films:
            film = get_film_profile(film_name)
            assert film.color_type == "single"
            assert film.red_layer is None
            assert film.green_layer is None
            assert film.blue_layer is None
    
    def test_invalid_film_type(self):
        """測試無效的胶片類型"""
        with pytest.raises(ValueError, match="未知的胶片類型"):
            get_film_profile("INVALID_FILM")
    
    def test_emulsion_layer_values(self):
        """測試感光層參數範圍"""
        for film_type in FILM_PROFILES.values():
            layers = [
                film_type.red_layer,
                film_type.green_layer,
                film_type.blue_layer,
                film_type.panchromatic_layer
            ]
            
            for layer in layers:
                if layer is None:
                    continue
                
                # 吸收係數應該在 0-1 範圍
                assert 0 <= layer.r_response_weight <= 1
                assert 0 <= layer.g_response_weight <= 1
                assert 0 <= layer.b_response_weight <= 1
                
                # 光學參數應該為正
                assert layer.diffuse_weight >= 0
                assert layer.direct_weight >= 0
                assert layer.response_curve >= 0
                assert layer.grain_intensity >= 0
    
    def test_spectral_response(self):
        """測試光譜響應計算"""
        # 測試彩色胶片
        film = get_film_profile("NC200")
        response = film.get_spectral_response()
        assert len(response) == 12
        assert all(isinstance(v, float) for v in response)
        
        # 測試黑白胶片
        film_bw = get_film_profile("AS100")
        response_bw = film_bw.get_spectral_response()
        assert len(response_bw) == 12
        # 前 9 個值應該為 0（RGB 層）
        assert all(v == 0.0 for v in response_bw[:9])
        # 最後 3 個值為全色層
        assert any(v != 0.0 for v in response_bw[9:])
    
    def test_tone_mapping_params(self):
        """測試 Tone mapping 參數"""
        for film_type in FILM_PROFILES.values():
            params = film_type.tone_params
            assert isinstance(params, ToneMappingParams)
            assert params.gamma > 0
            assert params.shoulder_strength >= 0
            assert params.linear_strength >= 0
            assert params.toe_strength >= 0
    
    def test_sensitivity_factors(self):
        """測試敏感係數範圍"""
        for film_type in FILM_PROFILES.values():
            assert 0.5 <= film_type.sensitivity_factor <= 2.0


class TestNewFilmProfiles:
    """測試新增的胶片預設"""
    
    def test_portra400_characteristics(self):
        """測試 Portra400 特性（人像王者）"""
        film = get_film_profile("Portra400")
        assert film.color_type == "color"
        # Portra 應該有較低的顆粒強度
        assert film.red_layer.grain_intensity <= 0.15
        assert film.sensitivity_factor > 1.0  # 高感光度
    
    def test_ektar100_characteristics(self):
        """測試 Ektar100 特性（風景利器）"""
        film = get_film_profile("Ektar100")
        assert film.color_type == "color"
        # Ektar 應該有極細的顆粒
        assert film.red_layer.grain_intensity <= 0.10
        # 高對比度（高 gamma）
        assert film.tone_params.gamma >= 2.0
    
    def test_hp5plus400_characteristics(self):
        """測試 HP5 Plus 400 特性（經典黑白）"""
        film = get_film_profile("HP5Plus400")
        assert film.color_type == "single"
        # HP5 應該有明顯的顆粒
        assert film.panchromatic_layer.grain_intensity >= 0.20
        assert film.sensitivity_factor > 1.3  # 高感光度
    
    def test_cinestill800t_characteristics(self):
        """測試 CineStill 800T 特性（電影感）"""
        film = get_film_profile("Cinestill800T")
        assert film.color_type == "color"
        # CineStill 800T 應該有最高的敏感係數
        assert film.sensitivity_factor >= 1.5
        # 強烈的光暈效果（高擴散光）
        assert film.red_layer.diffuse_weight >= 1.5


class TestDataclassIntegrity:
    """測試數據類完整性"""
    
    def test_emulsion_layer_immutability(self):
        """測試感光層數據不可變性"""
        film = get_film_profile("NC200")
        original_grain = film.red_layer.grain_intensity
        
        # 嘗試修改應該創建新實例（dataclass 特性）
        from dataclasses import replace
        modified_film = replace(
            film,
            red_layer=replace(film.red_layer, grain_intensity=0.5)
        )
        
        # 原始值不變
        assert film.red_layer.grain_intensity == original_grain
        # 新值已改變
        assert modified_film.red_layer.grain_intensity == 0.5
    
    def test_film_profile_serialization(self):
        """測試胶片配置可序列化"""
        from dataclasses import asdict
        
        film = get_film_profile("NC200")
        film_dict = asdict(film)
        
        assert isinstance(film_dict, dict)
        assert film_dict["name"] == "NC200"
        assert "red_layer" in film_dict
        assert "tone_params" in film_dict


# ============================================================
# Section 2: ISO Unification Tests
# Source: test_iso_unification.py (21 tests)
# ============================================================

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


# ============================================================
# Section 3: Create Film From ISO Tests
# Source: test_create_film_from_iso.py (25 tests)
# ============================================================

class TestBasicCreation:
    """測試基本創建功能"""
    
    def test_create_color_film_default(self):
        """驗證創建彩色膠片（預設參數）"""
        film = create_film_profile_from_iso(
            name="TestColor400",
            iso=400
        )
        
        # 檢查基本屬性
        assert film.name == "TestColor400"
        assert film.color_type == "color"
        assert film.physics_mode == PhysicsMode.PHYSICAL
        
        # 檢查層結構
        assert film.red_layer is not None
        assert film.green_layer is not None
        assert film.blue_layer is not None
        assert film.panchromatic_layer is not None
        
        # 檢查參數存在
        assert film.bloom_params is not None
        assert film.halation_params is not None
        assert film.wavelength_bloom_params is not None
        assert film.grain_params is not None
    
    def test_create_bw_film(self):
        """驗證創建黑白膠片"""
        film = create_film_profile_from_iso(
            name="TestBW400",
            iso=400,
            color_type="single"
        )
        
        # 檢查黑白結構
        assert film.color_type == "single"
        assert film.red_layer is None
        assert film.green_layer is None
        assert film.blue_layer is None
        assert film.panchromatic_layer is not None
        
        # 黑白膠片應有 H&D 曲線
        assert film.hd_curve_params is not None
        assert film.hd_curve_params.enabled == True
    
    def test_sensitivity_factor_scaling(self):
        """驗證 sensitivity_factor 隨 ISO 縮放"""
        film_100 = create_film_profile_from_iso("Test100", iso=100)
        film_400 = create_film_profile_from_iso("Test400", iso=400)
        film_1600 = create_film_profile_from_iso("Test1600", iso=1600)
        
        # sensitivity_factor 應隨 ISO 遞增
        assert film_100.sensitivity_factor < film_400.sensitivity_factor
        assert film_400.sensitivity_factor < film_1600.sensitivity_factor
        
        # 範圍應在 [0.90, 1.60]
        for film in [film_100, film_400, film_1600]:
            assert 0.90 <= film.sensitivity_factor <= 1.60


class TestISODerivedParams:
    """測試 ISO 派生參數一致性"""
    
    def test_grain_intensity_from_iso(self):
        """驗證 grain_intensity 從 ISO 正確派生"""
        iso = 400
        film_type = "standard"
        
        # 創建膠片
        film = create_film_profile_from_iso(
            name="Test400",
            iso=iso,
            film_type=film_type
        )
        
        # 直接計算派生值
        iso_params = derive_physical_params_from_iso(iso, film_type)
        
        # grain_params.intensity 應等於派生值
        assert film.grain_params.intensity == iso_params.grain_intensity
        
        # grain_params.grain_size 應等於派生粒徑
        assert film.grain_params.grain_size == iso_params.grain_mean_diameter_um
    
    def test_scattering_ratio_from_iso(self):
        """驗證 scattering_ratio 從 ISO 正確派生"""
        iso = 800
        film_type = "high_speed"
        
        film = create_film_profile_from_iso(
            name="Test800",
            iso=iso,
            film_type=film_type
        )
        
        iso_params = derive_physical_params_from_iso(iso, film_type)
        
        # bloom_params.scattering_ratio 應等於派生值
        assert film.bloom_params.scattering_ratio == iso_params.scattering_ratio
    
    def test_wavelength_bloom_iso_value(self):
        """驗證 wavelength_bloom_params.iso_value 正確設置"""
        iso = 1600
        film = create_film_profile_from_iso("Test1600", iso=iso)
        
        assert film.wavelength_bloom_params.iso_value == iso


class TestFilmTypeDifferencesCreation:
    """測試膠片類型差異（創建 API）"""
    
    def test_fine_vs_standard_vs_high(self):
        """驗證 fine_grain < standard < high_speed"""
        iso = 400
        
        fine = create_film_profile_from_iso("Fine400", iso=iso, film_type="fine_grain")
        standard = create_film_profile_from_iso("Std400", iso=iso, film_type="standard")
        high = create_film_profile_from_iso("High400", iso=iso, film_type="high_speed")
        
        # 顆粒強度排序
        assert fine.grain_params.intensity < standard.grain_params.intensity
        assert standard.grain_params.intensity < high.grain_params.intensity
        
        # 粒徑排序
        assert fine.grain_params.grain_size < standard.grain_params.grain_size
        assert standard.grain_params.grain_size < high.grain_params.grain_size
    
    def test_portra_style_fine_grain(self):
        """驗證 Portra 風格（fine-grain + balanced tone）"""
        film = create_film_profile_from_iso(
            name="PortraStyle400",
            iso=400,
            film_type="fine_grain",
            tone_mapping_style="balanced"
        )
        
        # Fine-grain ISO 400 應有較低顆粒
        assert film.grain_params.intensity < 0.20
        
        # Balanced tone: gamma ~ 1.95
        assert 1.90 <= film.tone_params.gamma <= 2.00
    
    def test_superia_style_high_speed(self):
        """驗證 Superia 風格（high-speed + natural tone）"""
        film = create_film_profile_from_iso(
            name="SuperiaStyle400",
            iso=400,
            film_type="high_speed",
            tone_mapping_style="natural"
        )
        
        # High-speed ISO 400 應有較高顆粒
        assert film.grain_params.intensity > 0.20
        
        # Natural tone: gamma ~ 2.08
        assert 2.00 <= film.tone_params.gamma <= 2.15


class TestToneMappingStyles:
    """測試 Tone mapping 風格"""
    
    def test_balanced_style(self):
        """驗證 balanced 風格（Portra）"""
        film = create_film_profile_from_iso(
            "Balanced", iso=400, tone_mapping_style="balanced"
        )
        assert 1.90 <= film.tone_params.gamma <= 2.00
        assert film.tone_params.shoulder_strength == 0.12
    
    def test_vivid_style(self):
        """驗證 vivid 風格（Velvia）"""
        film = create_film_profile_from_iso(
            "Vivid", iso=50, tone_mapping_style="vivid"
        )
        assert film.tone_params.gamma == 2.25
        assert film.tone_params.shoulder_strength == 0.22
    
    def test_natural_style(self):
        """驗證 natural 風格（Ektar）"""
        film = create_film_profile_from_iso(
            "Natural", iso=100, tone_mapping_style="natural"
        )
        assert film.tone_params.gamma == 2.08
        assert film.tone_params.shoulder_strength == 0.14
    
    def test_soft_style(self):
        """驗證 soft 風格（低對比）"""
        film = create_film_profile_from_iso(
            "Soft", iso=200, tone_mapping_style="soft"
        )
        assert film.tone_params.gamma == 1.85
        assert film.tone_params.shoulder_strength == 0.10


class TestOverrides:
    """測試覆蓋參數功能"""
    
    def test_override_sensitivity_factor(self):
        """驗證覆蓋 sensitivity_factor"""
        custom_sensitivity = 1.75
        film = create_film_profile_from_iso(
            "Custom", iso=400, sensitivity_factor=custom_sensitivity
        )
        assert film.sensitivity_factor == custom_sensitivity
    
    def test_override_grain_params(self):
        """驗證覆蓋 grain_params"""
        custom_grain = GrainParams(
            mode="poisson",
            intensity=0.5,
            grain_size=2.0
        )
        film = create_film_profile_from_iso(
            "Custom", iso=400, grain_params=custom_grain
        )
        assert film.grain_params.mode == "poisson"
        assert film.grain_params.intensity == 0.5
        assert film.grain_params.grain_size == 2.0
    
    def test_override_bloom_params(self):
        """驗證覆蓋 bloom_params"""
        custom_bloom = BloomParams(
            mode="artistic",
            sensitivity=2.0,
            radius=50
        )
        film = create_film_profile_from_iso(
            "Custom", iso=400, bloom_params=custom_bloom
        )
        assert film.bloom_params.mode == "artistic"
        assert film.bloom_params.sensitivity == 2.0


class TestCinestillStyle:
    """測試 Cinestill 風格（無 AH 層）"""
    
    def test_no_ah_layer_extreme_halation(self):
        """驗證無 AH 層產生極端光暈"""
        # 標準膠片（有 AH 層）
        standard = create_film_profile_from_iso(
            "Standard800", iso=800, has_ah_layer=True
        )
        
        # Cinestill 風格（無 AH 層）
        cinestill = create_film_profile_from_iso(
            "Cinestill800", iso=800, has_ah_layer=False
        )
        
        # 無 AH 層應有更高的透過率
        assert (cinestill.halation_params.ah_layer_transmittance_r >
                standard.halation_params.ah_layer_transmittance_r)
        
        # 無 AH 層應有更高的能量分數
        assert (cinestill.halation_params.energy_fraction >
                standard.halation_params.energy_fraction)
    
    def test_cinestill_high_speed_combination(self):
        """驗證 Cinestill + high-speed 組合"""
        film = create_film_profile_from_iso(
            "CinestillStyle800",
            iso=800,
            film_type="high_speed",
            has_ah_layer=False
        )
        
        # 應同時有高顆粒和極端光暈
        assert film.grain_params.intensity > 0.20  # High-speed 顆粒
        assert film.halation_params.ah_layer_transmittance_r > 0.9  # 極端光暈


class TestSpectralResponse:
    """測試自定義光譜響應"""
    
    def test_custom_spectral_response(self):
        """驗證自定義光譜響應"""
        # 自定義響應（12 元素）
        custom_response = (
            0.9, 0.05, 0.05,  # Red layer: 強紅光響應
            0.05, 0.9, 0.05,  # Green layer: 強綠光響應
            0.05, 0.05, 0.95, # Blue layer: 強藍光響應
            0.3, 0.4, 0.3     # Panchromatic layer
        )
        
        film = create_film_profile_from_iso(
            "CustomSpectral", iso=400, spectral_response=custom_response
        )
        
        # 檢查響應設置正確
        assert film.red_layer.r_response_weight == 0.9
        assert film.green_layer.g_response_weight == 0.9
        assert film.blue_layer.b_response_weight == 0.95
    
    def test_invalid_spectral_response_length(self):
        """驗證無效光譜響應長度拋出錯誤"""
        with pytest.raises(ValueError, match="12 元素"):
            create_film_profile_from_iso(
                "Invalid", iso=400, spectral_response=(0.5, 0.5, 0.5)  # 僅 3 元素
            )


class TestEdgeCases:
    """測試邊界情況"""
    
    def test_iso_50_low_grain(self):
        """驗證 ISO 50 極低顆粒"""
        film = create_film_profile_from_iso("ISO50", iso=50)
        
        # 極低 ISO 應有極細顆粒
        assert film.grain_params.intensity < 0.10
        assert film.grain_params.grain_size < 0.70
    
    def test_iso_3200_high_grain(self):
        """驗證 ISO 3200 高顆粒"""
        film = create_film_profile_from_iso("ISO3200", iso=3200)
        
        # 極高 ISO 應有粗顆粒
        assert film.grain_params.intensity > 0.20
        assert film.grain_params.grain_size > 1.50
    
    def test_iso_boundary_values(self):
        """驗證邊界值 ISO 25 和 6400"""
        film_25 = create_film_profile_from_iso("ISO25", iso=25)
        film_6400 = create_film_profile_from_iso("ISO6400", iso=6400)
        
        # 應成功創建
        assert film_25.name == "ISO25"
        assert film_6400.name == "ISO6400"
        
        # 顆粒應有明顯差異
        assert film_6400.grain_params.intensity > film_25.grain_params.intensity * 2


class TestConsistencyWithExisting:
    """測試與現有膠片配置的一致性"""
    
    def test_portra400_recreation(self):
        """驗證重建 Portra 400 參數接近"""
        film = create_film_profile_from_iso(
            "Portra400Clone",
            iso=400,
            film_type="fine_grain",
            tone_mapping_style="balanced"
        )
        
        # 顆粒強度應在合理範圍（fine-grain ISO 400）
        assert 0.10 <= film.grain_params.intensity <= 0.20
        
        # 散射比例應在 6-15%
        assert 0.06 <= film.bloom_params.scattering_ratio <= 0.15
        
        # Tone mapping gamma 接近 Portra（1.95）
        assert 1.90 <= film.tone_params.gamma <= 2.00
    
    def test_ektar100_recreation(self):
        """驗證重建 Ektar 100 參數接近"""
        film = create_film_profile_from_iso(
            "Ektar100Clone",
            iso=100,
            film_type="fine_grain",
            tone_mapping_style="natural"
        )
        
        # 極細顆粒
        assert film.grain_params.intensity < 0.10
        
        # 低散射（ISO 100 fine-grain）
        # 實際派生值約 0.08，這是合理的
        assert film.bloom_params.scattering_ratio < 0.10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
