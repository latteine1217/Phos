"""
Phos - 胶片模型定義模組

包含胶片參數的數據結構定義和配置
"""

from dataclasses import dataclass
from typing import Optional, Tuple


# ==================== 常數定義 ====================

# 圖像處理常數
STANDARD_IMAGE_SIZE = 3000  # 標準化後的短邊尺寸

# 光學效果常數
SENSITIVITY_MIN = 0.10
SENSITIVITY_MAX = 0.70
SENSITIVITY_SCALE = 0.75
SENSITIVITY_BASE = 0.10
BLOOM_STRENGTH_FACTOR = 23
BLOOM_RADIUS_FACTOR = 20
BLOOM_RADIUS_MIN = 1
BLOOM_RADIUS_MAX = 50
BASE_DIFFUSION_FACTOR = 0.05

# 顆粒效果常數
GRAIN_WEIGHT_MIN = 0.05
GRAIN_WEIGHT_MAX = 0.90
GRAIN_SENS_MIN = 0.4
GRAIN_SENS_MAX = 0.6
GRAIN_BLUR_KERNEL = (3, 3)
GRAIN_BLUR_SIGMA = 1

# Tone mapping 常數
REINHARD_GAMMA_ADJUSTMENT = 1.05
FILMIC_EXPOSURE_SCALE = 10


# ==================== 數據類定義 ====================

@dataclass
class EmulsionLayer:
    """
    感光層參數
    
    模擬胶片中的單一感光乳劑層，包含光譜響應和成像特性
    """
    r_absorption: float  # 吸收紅光的比例 (0-1)
    g_absorption: float  # 吸收綠光的比例 (0-1)
    b_absorption: float  # 吸收藍光的比例 (0-1)
    diffuse_light: float  # 散射光係數（模擬光在胶片中的擴散）
    direct_light: float  # 直射光係數（未擴散的直接響應）
    response_curve: float  # 響應曲線指數（非線性特性）
    grain_intensity: float  # 顆粒強度 (0-1)


@dataclass
class ToneMappingParams:
    """
    Tone mapping 參數
    
    控制 HDR 到 LDR 的映射曲線，模擬胶片的特性曲線
    """
    gamma: float  # Gamma 值
    shoulder_strength: float  # A - 肩部強度（高光過渡）
    linear_strength: float  # B - 線性段強度
    linear_angle: float  # C - 線性段平整度
    toe_strength: float  # D - 趾部強度（陰影過渡）
    toe_numerator: float  # E - 趾部硬度
    toe_denominator: float  # F - 趾部軟度


@dataclass
class FilmProfile:
    """
    胶片配置文件
    
    完整描述一種胶片的所有物理和成像特性
    """
    name: str  # 胶片名稱
    color_type: str  # "color" 或 "single" (黑白)
    sensitivity_factor: float  # 高光敏感係數
    
    # 各感光層（彩色胶片有 RGB + 全色層，黑白胶片只有全色層）
    red_layer: Optional[EmulsionLayer]
    green_layer: Optional[EmulsionLayer]
    blue_layer: Optional[EmulsionLayer]
    panchromatic_layer: EmulsionLayer  # 全色感光層
    
    # Tone mapping 參數
    tone_params: ToneMappingParams
    
    def get_spectral_response(self) -> Tuple[float, ...]:
        """
        獲取光譜響應係數
        
        Returns:
            包含 12 個元素的 tuple: (r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b)
        """
        if (self.color_type == "color" and 
            self.red_layer is not None and 
            self.green_layer is not None and 
            self.blue_layer is not None):
            return (
                self.red_layer.r_absorption, self.red_layer.g_absorption, self.red_layer.b_absorption,
                self.green_layer.r_absorption, self.green_layer.g_absorption, self.green_layer.b_absorption,
                self.blue_layer.r_absorption, self.blue_layer.g_absorption, self.blue_layer.b_absorption,
                self.panchromatic_layer.r_absorption, self.panchromatic_layer.g_absorption, self.panchromatic_layer.b_absorption
            )
        else:
            return (
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                self.panchromatic_layer.r_absorption, self.panchromatic_layer.g_absorption, self.panchromatic_layer.b_absorption
            )


# ==================== 胶片配置數據庫 ====================

def create_film_profiles() -> dict:
    """
    創建所有胶片配置
    
    Returns:
        包含所有可用胶片配置的字典
    """
    profiles = {}
    
    # NC200 - 彩色負片（靈感來自富士 C200）
    profiles["NC200"] = FilmProfile(
        name="NC200",
        color_type="color",
        sensitivity_factor=1.20,
        red_layer=EmulsionLayer(
            r_absorption=0.77, g_absorption=0.12, b_absorption=0.18,
            diffuse_light=1.48, direct_light=0.95, response_curve=1.18, grain_intensity=0.18
        ),
        green_layer=EmulsionLayer(
            r_absorption=0.08, g_absorption=0.85, b_absorption=0.23,
            diffuse_light=1.02, direct_light=0.80, response_curve=1.02, grain_intensity=0.18
        ),
        blue_layer=EmulsionLayer(
            r_absorption=0.08, g_absorption=0.09, b_absorption=0.92,
            diffuse_light=1.02, direct_light=0.88, response_curve=0.78, grain_intensity=0.18
        ),
        panchromatic_layer=EmulsionLayer(
            r_absorption=0.25, g_absorption=0.35, b_absorption=0.35,
            diffuse_light=0.0, direct_light=0.0, response_curve=0.0, grain_intensity=0.08
        ),
        tone_params=ToneMappingParams(
            gamma=2.05, shoulder_strength=0.15, linear_strength=0.50,
            linear_angle=0.10, toe_strength=0.20, toe_numerator=0.02, toe_denominator=0.30
        )
    )
    
    # FS200 - 黑白正片
    profiles["FS200"] = FilmProfile(
        name="FS200",
        color_type="single",
        sensitivity_factor=1.0,
        red_layer=None,
        green_layer=None,
        blue_layer=None,
        panchromatic_layer=EmulsionLayer(
            r_absorption=0.15, g_absorption=0.35, b_absorption=0.45,
            diffuse_light=2.33, direct_light=0.85, response_curve=1.15, grain_intensity=0.20
        ),
        tone_params=ToneMappingParams(
            gamma=2.2, shoulder_strength=0.15, linear_strength=0.50,
            linear_angle=0.10, toe_strength=0.20, toe_numerator=0.02, toe_denominator=0.30
        )
    )
    
    # AS100 - 黑白胶片（靈感來自富士 ACROS）
    profiles["AS100"] = FilmProfile(
        name="AS100",
        color_type="single",
        sensitivity_factor=1.28,
        red_layer=None,
        green_layer=None,
        blue_layer=None,
        panchromatic_layer=EmulsionLayer(
            r_absorption=0.30, g_absorption=0.12, b_absorption=0.45,
            diffuse_light=1.0, direct_light=1.05, response_curve=1.25, grain_intensity=0.10
        ),
        tone_params=ToneMappingParams(
            gamma=2.0, shoulder_strength=0.15, linear_strength=0.50,
            linear_angle=0.25, toe_strength=0.35, toe_numerator=0.02, toe_denominator=0.35
        )
    )
    
    # Portra400 - 人像王者（靈感來自 Kodak Portra 400）
    profiles["Portra400"] = FilmProfile(
        name="Portra400",
        color_type="color",
        sensitivity_factor=1.35,
        red_layer=EmulsionLayer(
            r_absorption=0.82, g_absorption=0.10, b_absorption=0.15,
            diffuse_light=1.25, direct_light=1.00, response_curve=1.12, grain_intensity=0.12
        ),
        green_layer=EmulsionLayer(
            r_absorption=0.06, g_absorption=0.88, b_absorption=0.20,
            diffuse_light=0.95, direct_light=0.90, response_curve=1.05, grain_intensity=0.12
        ),
        blue_layer=EmulsionLayer(
            r_absorption=0.05, g_absorption=0.08, b_absorption=0.90,
            diffuse_light=0.90, direct_light=0.92, response_curve=0.85, grain_intensity=0.12
        ),
        panchromatic_layer=EmulsionLayer(
            r_absorption=0.28, g_absorption=0.40, b_absorption=0.30,
            diffuse_light=0.0, direct_light=0.0, response_curve=0.0, grain_intensity=0.06
        ),
        tone_params=ToneMappingParams(
            gamma=1.95, shoulder_strength=0.12, linear_strength=0.55,
            linear_angle=0.15, toe_strength=0.18, toe_numerator=0.01, toe_denominator=0.28
        )
    )
    
    # Ektar100 - 風景利器（靈感來自 Kodak Ektar 100）
    profiles["Ektar100"] = FilmProfile(
        name="Ektar100",
        color_type="color",
        sensitivity_factor=1.10,
        red_layer=EmulsionLayer(
            r_absorption=0.85, g_absorption=0.08, b_absorption=0.12,
            diffuse_light=1.15, direct_light=1.10, response_curve=1.25, grain_intensity=0.08
        ),
        green_layer=EmulsionLayer(
            r_absorption=0.05, g_absorption=0.90, b_absorption=0.18,
            diffuse_light=0.88, direct_light=0.95, response_curve=1.15, grain_intensity=0.08
        ),
        blue_layer=EmulsionLayer(
            r_absorption=0.04, g_absorption=0.06, b_absorption=0.95,
            diffuse_light=0.85, direct_light=1.00, response_curve=0.90, grain_intensity=0.08
        ),
        panchromatic_layer=EmulsionLayer(
            r_absorption=0.30, g_absorption=0.38, b_absorption=0.32,
            diffuse_light=0.0, direct_light=0.0, response_curve=0.0, grain_intensity=0.04
        ),
        tone_params=ToneMappingParams(
            gamma=2.15, shoulder_strength=0.18, linear_strength=0.52,
            linear_angle=0.12, toe_strength=0.22, toe_numerator=0.015, toe_denominator=0.32
        )
    )
    
    # HP5Plus400 - 經典黑白（靈感來自 Ilford HP5 Plus 400）
    profiles["HP5Plus400"] = FilmProfile(
        name="HP5Plus400",
        color_type="single",
        sensitivity_factor=1.42,
        red_layer=None,
        green_layer=None,
        blue_layer=None,
        panchromatic_layer=EmulsionLayer(
            r_absorption=0.28, g_absorption=0.32, b_absorption=0.38,
            diffuse_light=1.35, direct_light=0.98, response_curve=1.18, grain_intensity=0.22
        ),
        tone_params=ToneMappingParams(
            gamma=2.1, shoulder_strength=0.16, linear_strength=0.48,
            linear_angle=0.22, toe_strength=0.30, toe_numerator=0.025, toe_denominator=0.33
        )
    )
    
    # Cinestill800T - 電影感（靈感來自 CineStill 800T）
    profiles["Cinestill800T"] = FilmProfile(
        name="Cinestill800T",
        color_type="color",
        sensitivity_factor=1.55,
        red_layer=EmulsionLayer(
            r_absorption=0.80, g_absorption=0.15, b_absorption=0.20,
            diffuse_light=1.65, direct_light=0.90, response_curve=1.10, grain_intensity=0.25
        ),
        green_layer=EmulsionLayer(
            r_absorption=0.10, g_absorption=0.82, b_absorption=0.28,
            diffuse_light=1.18, direct_light=0.75, response_curve=0.95, grain_intensity=0.25
        ),
        blue_layer=EmulsionLayer(
            r_absorption=0.12, g_absorption=0.15, b_absorption=0.88,
            diffuse_light=1.35, direct_light=0.82, response_curve=0.70, grain_intensity=0.25
        ),
        panchromatic_layer=EmulsionLayer(
            r_absorption=0.22, g_absorption=0.30, b_absorption=0.42,
            diffuse_light=0.0, direct_light=0.0, response_curve=0.0, grain_intensity=0.15
        ),
        tone_params=ToneMappingParams(
            gamma=2.0, shoulder_strength=0.14, linear_strength=0.48,
            linear_angle=0.08, toe_strength=0.25, toe_numerator=0.03, toe_denominator=0.28
        )
    )
    
    return profiles


# 創建全局胶片配置字典
FILM_PROFILES = create_film_profiles()


def get_film_profile(film_type: str) -> FilmProfile:
    """
    獲取指定胶片的配置
    
    Args:
        film_type: 胶片類型名稱 ("NC200", "FS200", "AS100")
        
    Returns:
        FilmProfile: 胶片配置對象
        
    Raises:
        ValueError: 如果胶片類型不存在
    """
    if film_type not in FILM_PROFILES:
        available = ", ".join(FILM_PROFILES.keys())
        raise ValueError(f"未知的胶片類型: {film_type}. 可用類型: {available}")
    return FILM_PROFILES[film_type]
