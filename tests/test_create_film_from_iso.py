"""
P1-2: create_film_profile_from_iso() 功能測試

驗證便利函數的正確性：
1. 基本創建（color/single）
2. 膠片類型差異（fine_grain/standard/high_speed）
3. ISO 派生參數一致性
4. Tone mapping 風格
5. 覆蓋參數（**overrides）
6. 光譜響應自定義
7. Cinestill 風格（無 AH 層）

Version: 0.3.0 (TASK-007-P1-2)
"""

import pytest
from film_models import (
    create_film_profile_from_iso,
    derive_physical_params_from_iso,
    FilmProfile,
    PhysicsMode,
    GrainParams,
    BloomParams
)


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


class TestFilmTypeDifferences:
    """測試膠片類型差異"""
    
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


# ==================== 測試執行 ====================

if __name__ == "__main__":
    # 執行所有測試
    pytest.main([__file__, "-v", "--tb=short"])
