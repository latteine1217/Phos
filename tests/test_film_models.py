"""
測試 film_models 模組
"""

import pytest
import numpy as np
from film_models import (
    get_film_profile,
    FilmProfile,
    EmulsionLayer,
    ToneMappingParams,
    FILM_PROFILES,
    create_film_profiles
)


class TestFilmProfiles:
    """測試胶片配置"""
    
    def test_all_films_loadable(self, all_film_types):
        """測試所有胶片都能正確載入"""
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
