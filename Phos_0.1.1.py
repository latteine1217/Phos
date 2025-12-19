"""
"No LUTs, we calculate LUX."

你说的对，但是 Phos. 是基于「计算光学」概念的胶片模拟。
通过计算光在底片上的行为，复现自然、柔美、立体的胶片质感。

这是一个原理验证demo，图像处理部分基于opencv，交互基于
streamlit平台制作，部分代码使用了AI辅助生成。

如果您发现了项目中的问题，或是有更好的想法想要分享，还请
通过邮箱 lyco_p@163.com 与我联系，我将不胜感激。

Hello! Phos. is a film simulation app based on 
the idea of "Computational optical imaging“. 
By calculating the optical effects on the film,
we could recurrent the natural, soft, and elegant
tone of these classical films.

This is a demo for idea testing. The image processing
part is based on OpenCV, and the interaction is built
on the Streamlit. Some pieces of the code was generated 
with the assistance of AI.

If you find any issues in the project or have better
ideas you would like to share, please contact me via
email at lyco_p@163.com. I would be very grateful.

——————————————————————————————————————————————————————

在0.1.1版本中，调整了Tone mapping的实现方式（从Reinhard到
filmic),调整了彩色胶片的颗粒实现方式（考虑了颗粒的明度属性）

In the update of version 0.1.1, we adjusted the method 
of Tone mapping, from Reinhard to filimc. We also 
adjusted the method of effcting the grain effects
in the color films, taking the brightness effect into
consideration.
"""

import streamlit as st

# 设置页面配置 
st.set_page_config(
    page_title="Phos. 胶片模拟",
    page_icon="🎞️",
    layout="wide",
    initial_sidebar_state="expanded"
)

#赛博请神
import cv2
import numpy as np
import time
from PIL import Image
import io
from dataclasses import dataclass
from typing import Optional, Tuple

# ==================== 常數定義 ====================
# 圖像處理常數
STANDARD_IMAGE_SIZE = 3000  # 標準化後的短邊尺寸
ENSURE_EVEN_SIZE = True  # 確保尺寸為偶數

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
    """感光層參數"""
    r_absorption: float  # 吸收紅光的比例
    g_absorption: float  # 吸收綠光的比例
    b_absorption: float  # 吸收藍光的比例
    diffuse_light: float  # 散射光係數
    direct_light: float  # 直射光係數
    response_curve: float  # 響應曲線指數
    grain_intensity: float  # 顆粒強度


@dataclass
class ToneMappingParams:
    """Tone mapping 參數"""
    gamma: float
    shoulder_strength: float  # A - 肩部強度
    linear_strength: float  # B - 線性段強度
    linear_angle: float  # C - 線性段平整度
    toe_strength: float  # D - 趾部強度
    toe_numerator: float  # E - 趾部硬度
    toe_denominator: float  # F - 趾部軟度


@dataclass
class FilmProfile:
    """胶片配置文件"""
    name: str
    color_type: str  # "color" 或 "single"
    sensitivity_factor: float  # 高光敏感係數
    
    # 各感光層（彩色胶片有 RGB + 全色層，黑白胶片只有全色層）
    red_layer: Optional[EmulsionLayer]
    green_layer: Optional[EmulsionLayer]
    blue_layer: Optional[EmulsionLayer]
    panchromatic_layer: EmulsionLayer
    
    # Tone mapping 參數
    tone_params: ToneMappingParams
    
    def get_spectral_response(self) -> Tuple:
        """獲取光譜響應係數"""
        if self.color_type == "color" and self.red_layer and self.green_layer and self.blue_layer:
            return (
                self.red_layer.r_absorption, self.red_layer.g_absorption, self.red_layer.b_absorption,
                self.green_layer.r_absorption, self.green_layer.g_absorption, self.green_layer.b_absorption,
                self.blue_layer.r_absorption, self.blue_layer.g_absorption, self.blue_layer.b_absorption,
                self.panchromatic_layer.r_absorption, self.panchromatic_layer.g_absorption, self.panchromatic_layer.b_absorption
            )
        else:
            return (
                0, 0, 0, 0, 0, 0, 0, 0, 0,
                self.panchromatic_layer.r_absorption, self.panchromatic_layer.g_absorption, self.panchromatic_layer.b_absorption
            )

# ==================== 胶片配置定義 ====================
def create_film_profiles():
    """創建所有胶片配置"""
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
        raise ValueError(f"未知的胶片類型: {film_type}. 可用類型: {list(FILM_PROFILES.keys())}")
    return FILM_PROFILES[film_type]

def standardize(image):
    """标准化图像尺寸"""
    
    #确定短边尺寸
    min_size=3000

    # 获取原始尺寸
    height, width = image.shape[:2]
    # 确定缩放比例
    if height < width:
        # 竖图 - 高度为短边
        scale_factor = min_size / height
        new_height = min_size
        new_width = int(width * scale_factor)
    else:
        # 横图 - 宽度为短边
        scale_factor = min_size / width
        new_width = min_size
        new_height = int(height * scale_factor)
    
    # 确保新尺寸为偶数（避免某些处理问题）
    new_width = new_width + 1 if new_width % 2 != 0 else new_width
    new_height = new_height + 1 if new_height % 2 != 0 else new_height
    interpolation = cv2.INTER_AREA if scale_factor < 1 else cv2.INTER_LANCZOS4
    resized_image = cv2.resize(image, (new_width, new_height), interpolation=interpolation)

    return resized_image
    #统一尺寸

def luminance(image: np.ndarray, film: FilmProfile) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], np.ndarray]:
    """
    計算亮度圖像，模擬胶片感光層的光譜響應
    
    Args:
        image: 輸入圖像 (BGR 格式，0-255)
        film: 胶片配置對象
        
    Returns:
        (lux_r, lux_g, lux_b, lux_total): 各通道的光度響應 (0-1 範圍)
            - 彩色胶片: lux_r/g/b 為各層響應，lux_total 為全色層
            - 黑白胶片: 僅 lux_total 有值，其餘為 None
    """
    # 分離 RGB 通道
    b, g, r = cv2.split(image)
    
    # 轉換為浮點數 (0-1 範圍)
    b_float = b.astype(np.float32) / 255.0
    g_float = g.astype(np.float32) / 255.0
    r_float = r.astype(np.float32) / 255.0
    
    # 獲取光譜響應係數
    r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b = film.get_spectral_response()
    
    # 模擬不同乳劑層的吸收特性（光譜敏感度的線性組合）
    if film.color_type == "color":
        lux_r = r_r * r_float + r_g * g_float + r_b * b_float
        lux_g = g_r * r_float + g_g * g_float + g_b * b_float
        lux_b = b_r * r_float + b_g * g_float + b_b * b_float
        lux_total = t_r * r_float + t_g * g_float + t_b * b_float
    else:
        lux_total = t_r * r_float + t_g * g_float + t_b * b_float
        lux_r = None
        lux_g = None
        lux_b = None

    return lux_r, lux_g, lux_b, lux_total

def average(lux_total):
    """计算图像的平均亮度 (0-1)"""
    # 计算平均亮度
    avg_lux = np.mean(lux_total)
    avg_lux = np.clip(avg_lux,0,1)
    return avg_lux
    #计算平均亮度

def generate_grain_for_channel(lux_channel: np.ndarray, sens: float) -> np.ndarray:
    """
    為單個通道生成胶片顆粒噪聲
    
    Args:
        lux_channel: 光度通道數據 (0-1 範圍)
        sens: 敏感度參數
        
    Returns:
        加權噪聲 (-1 到 1 範圍)
    """
    # 創建正負噪聲（使用平方正態分佈產生更自然的顆粒）
    noise = np.random.normal(0, 1, lux_channel.shape).astype(np.float32)
    noise = noise ** 2
    noise = noise * (np.random.choice([-1, 1], lux_channel.shape))
    
    # 創建權重圖（中等亮度區域權重最高，模擬胶片顆粒在中間調最明顯的特性）
    weights = (0.5 - np.abs(lux_channel - 0.5)) * 2
    weights = np.clip(weights, GRAIN_WEIGHT_MIN, GRAIN_WEIGHT_MAX)
    
    # 應用權重和敏感度
    sens_grain = np.clip(sens, GRAIN_SENS_MIN, GRAIN_SENS_MAX)
    weighted_noise = noise * weights * sens_grain
    
    # 添加輕微模糊使顆粒更柔和
    weighted_noise = cv2.GaussianBlur(weighted_noise, GRAIN_BLUR_KERNEL, GRAIN_BLUR_SIGMA)
    
    return np.clip(weighted_noise, -1, 1)


def grain(lux_r: Optional[np.ndarray], lux_g: Optional[np.ndarray], 
          lux_b: Optional[np.ndarray], lux_total: np.ndarray, 
          color_type: str, sens: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    生成胶片顆粒效果
    
    Args:
        lux_r, lux_g, lux_b: RGB 通道的光度數據（彩色胶片）
        lux_total: 全色通道的光度數據
        color_type: 胶片類型 ("color" 或 "single")
        sens: 敏感度參數
        
    Returns:
        (weighted_noise_r, weighted_noise_g, weighted_noise_b, weighted_noise_total): 各通道的顆粒噪聲
    """
    if color_type == "color" and lux_r is not None and lux_g is not None and lux_b is not None:
        # 彩色胶片：為每個通道生成獨立的顆粒
        weighted_noise_r = generate_grain_for_channel(lux_r, sens)
        weighted_noise_g = generate_grain_for_channel(lux_g, sens)
        weighted_noise_b = generate_grain_for_channel(lux_b, sens)
        weighted_noise_total = None
    else:
        # 黑白胶片：僅生成全色通道的顆粒
        weighted_noise_total = generate_grain_for_channel(lux_total, sens)
        weighted_noise_r = None
        weighted_noise_g = None
        weighted_noise_b = None
    
    return weighted_noise_r, weighted_noise_g, weighted_noise_b, weighted_noise_total

def apply_reinhard_to_channel(lux: np.ndarray, gamma: float, color_mode: bool = False) -> np.ndarray:
    """
    對單個通道應用 Reinhard tone mapping
    
    Args:
        lux: 輸入光度數據
        gamma: Gamma 值
        color_mode: 是否為彩色模式（影響 gamma 調整）
        
    Returns:
        映射後的結果 (0-1 範圍)
    """
    # Reinhard tone mapping: L' = L * L / (1 + L)
    mapped = lux * (lux / (1.0 + lux))
    
    # 應用 gamma 校正
    gamma_adj = REINHARD_GAMMA_ADJUSTMENT if color_mode else 1.0
    mapped = np.power(np.maximum(mapped, 0), gamma_adj / gamma)
    
    return np.clip(mapped, 0, 1)


def reinhard(lux_r: Optional[np.ndarray], lux_g: Optional[np.ndarray], 
             lux_b: Optional[np.ndarray], lux_total: np.ndarray, 
             color_type: str, gamma: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Reinhard tone mapping 算法
    
    Args:
        lux_r, lux_g, lux_b: RGB 通道的光度數據
        lux_total: 全色通道的光度數據
        color_type: 胶片類型
        gamma: Gamma 值
        
    Returns:
        (result_r, result_g, result_b, result_total): 映射後的各通道數據
    """
    if color_type == "color" and lux_r is not None and lux_g is not None and lux_b is not None:
        result_r = apply_reinhard_to_channel(lux_r, gamma, color_mode=True)
        result_g = apply_reinhard_to_channel(lux_g, gamma, color_mode=True)
        result_b = apply_reinhard_to_channel(lux_b, gamma, color_mode=True)
        result_total = None
    else:
        result_total = apply_reinhard_to_channel(lux_total, gamma, color_mode=False)
        result_r = None
        result_g = None
        result_b = None

    return result_r, result_g, result_b, result_total

def apply_filmic_to_channel(lux: np.ndarray, params: ToneMappingParams) -> np.ndarray:
    """
    對單個通道應用 Filmic tone mapping
    
    Args:
        lux: 輸入光度數據
        params: Tone mapping 參數對象
        
    Returns:
        映射後的結果
        
    Note:
        使用分段曲線模擬胶片的特性曲線（characteristic curve）
        - Shoulder: 控制高光過渡
        - Linear: 控制中間調響應
        - Toe: 控制陰影過渡
    """
    # 確保非負值
    lux = np.maximum(lux, 0)
    
    # 應用曝光和 gamma
    x = FILMIC_EXPOSURE_SCALE * (lux ** params.gamma)
    
    # Filmic curve: 分段曲線公式
    # numerator = x * (A*x + C*B) + D*E
    # denominator = x * (A*x + B) + D*F
    A, B, C, D, E, F = (params.shoulder_strength, params.linear_strength, 
                        params.linear_angle, params.toe_strength, 
                        params.toe_numerator, params.toe_denominator)
    
    numerator = x * (A * x + C * B) + D * E
    denominator = x * (A * x + B) + D * F
    
    # 避免除零
    result = np.divide(numerator, denominator, out=np.zeros_like(x), where=denominator!=0) - E/F
    
    return result


def filmic(lux_r: Optional[np.ndarray], lux_g: Optional[np.ndarray], 
           lux_b: Optional[np.ndarray], lux_total: np.ndarray, 
           film: FilmProfile) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Filmic tone mapping 算法
    
    Args:
        lux_r, lux_g, lux_b: RGB 通道的光度數據
        lux_total: 全色通道的光度數據
        film: 胶片配置對象
        
    Returns:
        (result_r, result_g, result_b, result_total): 映射後的各通道數據
    """
    if film.color_type == "color" and lux_r is not None and lux_g is not None and lux_b is not None:
        result_r = apply_filmic_to_channel(lux_r, film.tone_params)
        result_g = apply_filmic_to_channel(lux_g, film.tone_params)
        result_b = apply_filmic_to_channel(lux_b, film.tone_params)
        result_total = None
    else:
        result_total = apply_filmic_to_channel(lux_total, film.tone_params)
        result_r = None
        result_g = None
        result_b = None
    
    return result_r, result_g, result_b, result_total

def opt(lux_r,lux_g,lux_b,lux_total,color_type, sens_factor, d_r, l_r, x_r, n_r, d_g, l_g, x_g, n_g, d_b, l_b, x_b, n_b, d_l, l_l, x_l, n_l,grain_style,gamma,A,B,C,D,E,F,Tone_style):
    #opt 光学扩散函数

    avrl = average(lux_total)
    # 根据平均亮度计算敏感度
    sens = (1.0 - avrl) * 0.75 + 0.10
    # 将敏感度限制在0-1范围内
    sens = np.clip(sens,0.10,0.7) #sens -- 高光敏感度
    strg = 23 * sens**2 * sens_factor #strg -- 光晕强度
    rads = np.clip(int(20 * sens**2 * sens_factor),1,50) #rads -- 光晕扩散半径
    base = 0.05 * sens_factor #base -- 基础扩散强度

    ksize = rads * 2 + 1
    ksize = ksize if ksize % 2 == 1 else ksize + 1
    # 确保核大小为奇数

    if color_type == ("color"):
        weights = (base + lux_r**2) * sens 
        weights = np.clip(weights,0,1)
        #创建光晕层
        bloom_layer = cv2.GaussianBlur(lux_r * weights, (ksize * 3 , ksize * 3),sens * 55)
        #开始高斯模糊
        bloom_effect = bloom_layer * weights * strg
        bloom_effect = (bloom_effect/ (1.0 + bloom_effect))
        bloom_effect_r = bloom_effect
        #应用光晕
    
        weights = (base + lux_g**2 ) * sens
        weights = np.clip(weights,0,1)
        bloom_layer = cv2.GaussianBlur(lux_g * weights, (ksize * 2 +1 , ksize * 2 +1 ),sens * 35)
        #开始高斯模糊
        bloom_effect = bloom_layer * weights * strg
        bloom_effect = (bloom_effect/ (1.0 + bloom_effect))
        bloom_effect_g = bloom_effect
        #应用光晕
    
        weights = (base + lux_b**2 ) * sens
        weights = np.clip(weights,0,1)
        #创建光晕层
        bloom_layer = cv2.GaussianBlur(lux_b * weights, (ksize, ksize),sens * 15)
        #开始高斯模糊
        bloom_effect = bloom_layer * weights * strg
        bloom_effect = (bloom_effect/ (1.0 + bloom_effect))
        bloom_effect_b = bloom_effect
        #应用光晕
        
        if grain_style == ("不使用"):
            lux_r = bloom_effect_r * d_r + (lux_r**x_r) * l_r
            lux_g = bloom_effect_g * d_g + (lux_g**x_g) * l_g
            lux_b = bloom_effect_b * d_b + (lux_b**x_b) * l_b
        else:    
            (weighted_noise_r,weighted_noise_g,weighted_noise_b,weighted_noise_total) = grain(lux_r,lux_g,lux_b,lux_total,color_type,sens)
            #应用颗粒
            lux_r = bloom_effect_r * d_r + (lux_r**x_r) * l_r + weighted_noise_r *n_r + weighted_noise_g *n_l+ weighted_noise_b *n_l
            lux_g = bloom_effect_g * d_g + (lux_g**x_g) * l_g + weighted_noise_r *n_l + weighted_noise_g *n_g+ weighted_noise_b *n_l
            lux_b = bloom_effect_b * d_b + (lux_b**x_b) * l_b + weighted_noise_r *n_l + weighted_noise_g *n_l + weighted_noise_b *n_b
        
        #拼合光层
        if Tone_style == "filmic":
            (result_r,result_g,result_b,result_total) = filmic(lux_r,lux_g,lux_b,lux_total,color_type,gamma,A,B,C,D,E,F)
            #应用flimic映射
        else:
            (result_r,result_g,result_b,result_total) = reinhard(lux_r,lux_g,lux_b,lux_total,color_type,gamma)
            #应用映射

        combined_b = (result_b * 255).astype(np.uint8)
        combined_g = (result_g * 255).astype(np.uint8)
        combined_r = (result_r * 255).astype(np.uint8)
        film = cv2.merge([combined_r, combined_g, combined_b])
    else:
        weights = (base + lux_total**2) * sens 
        weights = np.clip(weights,0,1)
        #创建光晕层
        bloom_layer = cv2.GaussianBlur(lux_total * weights, (ksize * 3 , ksize * 3),sens * 55)
        #开始高斯模糊
        bloom_effect = bloom_layer * weights * strg
        bloom_effect = (bloom_effect/ (1.0 + bloom_effect))
        #应用光晕
        if grain_style == ("不使用"):
            lux_total = bloom_effect * d_l + (lux_total**x_l) * l_l
        else:
            (weighted_noise_r,weighted_noise_g,weighted_noise_b,weighted_noise_total) = grain(lux_r,lux_g,lux_b,lux_total,color_type,sens)
            #应用颗粒
            lux_total = bloom_effect * d_l + (lux_total**x_l) * l_l + weighted_noise_total *n_l
        
        #拼合光层
        
        if Tone_style == "filmic":
            (result_r,result_g,result_b,result_total) = filmic(lux_r,lux_g,lux_b,lux_total,color_type,gamma,A,B,C,D,E,F)
            #应用flimic映射
        else:
            (result_r,result_g,result_b,result_total) = reinhard(lux_r,lux_g,lux_b,lux_total,color_type,gamma)
            #应用reinhard映射

        film = (result_total * 255).astype(np.uint8)

    return film
    #返回渲染后的光度
    #进行底片成像
    #准备暗房工具

def process(uploaded_image,film_type,grain_style,Tone_style):
    
    start_time = time.time()

    # 读取上传的文件
    file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    # 获取胶片参数
    (r_r,r_g,r_b,g_r,g_g,g_b,b_r,b_g,b_b,t_r,t_g,t_b,color_type,sens_factor,d_r,l_r,x_r,n_r,d_g,l_g,x_g,n_g,d_b,l_b,x_b,n_b,d_l,l_l,x_l,n_l,gamma,A,B,C,D,E,F) = film_choose(film_type)
    
    if grain_style == ("默认"):
        n_r = n_r * 1.0
        n_g = n_g * 1.0
        n_b = n_b * 1.0
        n_l = n_l * 1.0
    elif grain_style == ("柔和"):
        n_r = n_r * 0.5
        n_g = n_g * 0.5
        n_b = n_b * 0.5
        n_l = n_l * 0.5
    elif grain_style == ("较粗"):
        n_r = n_r * 1.5
        n_g = n_g * 1.5
        n_b = n_b * 1.5
        n_l = n_l * 1.5
    elif grain_style == ("不使用"):
        n_r = n_r * 0
        n_g = n_g * 0
        n_b = n_b * 0
        n_l = n_l * 0


    # 调整尺寸
    image = standardize(image)

    (lux_r,lux_g,lux_b,lux_total) = luminance(image,color_type,r_r,r_g,r_b,g_r,g_g,g_b,b_r,b_g,b_b,t_r,t_g,t_b)
    #重建光线
    film = opt(lux_r,lux_g,lux_b,lux_total,color_type, sens_factor, d_r, l_r, x_r, n_r, d_g, l_g, x_g, n_g, d_b, l_b, x_b, n_b, d_l, l_l, x_l, n_l,grain_style,gamma,A,B,C,D,E,F,Tone_style)
    #冲洗底片
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = f"phos_{timestamp}.jpg"
    process_time = time.time() - start_time

    return film,process_time,output_path
    #执行胶片模拟处理

# 创建侧边栏
with st.sidebar:
    st.header("Phos. 胶片模拟")
    st.subheader("基于计算光学的胶片模拟")
    st.text("")
    st.text("原理验证demo")
    st.text("ver_0.1.1")
    st.text("")
    st.text("🎞️ 胶片设置")
    # 胶片类型选择
    film_type = st.selectbox(
        "请选择胶片:",
        ["NC200","AS100","FS200"],
        index=0,
        help='''选择要模拟的胶片类型:

        NC200:灵感来自富士C200彩色负片和扫描仪
        SP3000，旨在模仿经典的“富士色调”，通过
        还原“记忆色”，唤起对胶片的情感。

        AS100：灵感来自富士ACROS系列黑白胶片，
        为正全色黑白胶片，对蓝色最敏感，红色次
        之，绿色最弱，成片灰阶细腻，颗粒柔和，
        画面锐利，对光影有很好的还原力。

        FS200：高对比度黑白正片⌈光⌋，在开发初期
        作为原理验证模型所使用，对蓝色较敏感，对
        红色较不敏感，对比鲜明，颗粒适中。
        '''
    )

    grain_style = st.selectbox(
        "胶片颗粒度：",
        ["默认","柔和","较粗","不使用"],
        index = 0,
        help="选择胶片的颗粒度",
    )
    
    Tone_style = st.selectbox(
        "曲线映射：",
        ["filmic","reinhard"],
        index = 0,
        help = '''选择Tone mapping方式:
        
        目前版本下Reinhard模型似乎表现出更好的动态范围，
        filmic模型尚不够完善,但对肩部趾部有更符合目标的刻画''',
    )

    st.success(f"已选择胶片: {film_type}") 
    # 文件上传器
    uploaded_image = None
    uploaded_image = st.file_uploader(
    "选择一张照片来开始冲洗",
    type=["jpg", "jpeg", "png"],
    help="上传一张照片冲洗试试看吧"
    )

if uploaded_image is not None:
    (film,process_time,output_path) = process(uploaded_image,film_type,grain_style,Tone_style)
    st.image(film, width="stretch")
    st.success(f"底片显影好了，用时 {process_time:.2f}秒") 
    
    # 添加下载按钮
    film_pil = Image.fromarray(film)
    buf = io.BytesIO()
    film_pil.save(buf, format="JPEG", quality=100)
    byte_im = buf.getvalue()
    
    # 创建字节缓冲区
    buf = io.BytesIO()
    film_pil.save(buf, format="JPEG")
    byte_im = buf.getvalue()
    st.download_button(
        label="📥 下载高清图像",
        data=byte_im,
        file_name=output_path,
        mime="image/jpeg"
    )
    uploaded_image = None
