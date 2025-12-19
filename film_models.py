"""
Phos - 胶片模型定義模組

包含胶片參數的數據結構定義和配置

Version: 0.2.1 (Physical Improvements)
- 新增物理模式支援（PhysicsMode）
- 新增 H&D 曲線參數（HDCurveParams）
- 新增 Bloom 參數分離（BloomParams）
- 新增顆粒參數擴展（GrainParams）
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple
from enum import Enum


# ==================== 枚舉定義 ====================

class PhysicsMode(str, Enum):
    """
    物理模式枚舉
    
    - ARTISTIC: 藝術模式（預設，保留現有視覺效果）
    - PHYSICAL: 物理模式（能量守恆、H&D 曲線、Poisson 噪聲）
    - HYBRID: 混合模式（可調整混合比例，實驗性）
    """
    ARTISTIC = "artistic"
    PHYSICAL = "physical"
    HYBRID = "hybrid"


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
class HDCurveParams:
    """
    H&D 曲線參數（Hurter-Driffield Characteristic Curve）
    
    描述膠片的非線性響應特性：曝光量 (H) → 光學密度 (D)
    公式（線性區段）：D = gamma * log10(H) + D_fog
    
    注意：膠片 gamma ≠ 顯示 gamma (2.2)
    - 負片典型值：gamma = 0.6-0.7（低對比度，留給後製空間）
    - 正片典型值：gamma = 1.5-2.0（高對比度，直接觀看）
    """
    enabled: bool = False  # 是否啟用 H&D 曲線（預設關閉，保持向後相容）
    gamma: float = 0.65    # 膠片對比度（負片: 0.6-0.7, 正片: 1.5-2.0）
    D_min: float = 0.1     # 最小密度（基底+霧度，Dmin）
    D_max: float = 3.0     # 最大密度（動態範圍上限，Dmax）
    
    # Toe（趾部，陰影區域的壓縮）
    toe_enabled: bool = True
    toe_end: float = 0.2    # 趾部結束點（相對曝光量，log10 scale）
    toe_strength: float = 0.3  # 趾部彎曲強度（0-1，越大越彎曲）
    
    # Shoulder（肩部，高光區域的壓縮）
    shoulder_enabled: bool = True
    shoulder_start: float = 2.5  # 肩部開始點（相對曝光量，log10 scale）
    shoulder_strength: float = 0.2  # 肩部彎曲強度（0-1，越大越彎曲）


@dataclass
class HalationParams:
    """
    Halation（背層反射）參數
    
    物理機制：光穿透乳劑層與片基，到達背層或相機背板反射後回到乳劑，產生大範圍光暈。
    與 Bloom（乳劑內前向散射）分離建模。
    
    遵循 Beer-Lambert 定律：T(λ) = exp(-α(λ)L)
    """
    enabled: bool = True  # 是否啟用 Halation
    
    # Beer-Lambert 透過率參數（雙程往返）
    # f_h(λ) = k · T_e(λ) · T_b(λ) · T_AH(λ) · R_bp · T_AH(λ) · T_b(λ) · T_e(λ)
    # 簡化為：f_h(λ) = k · exp(-α_eff(λ) · L_eff)
    transmittance_r: float = 0.7  # 紅光透過率（0-1，透過力強）
    transmittance_g: float = 0.5  # 綠光透過率
    transmittance_b: float = 0.3  # 藍光透過率（易被吸收）
    
    # Anti-Halation 層吸收率（0 = 完全反射，1 = 完全吸收）
    ah_absorption: float = 0.95  # 標準膠片：95% 吸收（僅 5% 反射）
    
    # 背板反射率（相機內部/壓片板）
    backplate_reflectance: float = 0.3  # 0-0.9，取決於相機設計
    
    # PSF 參數（長尾分布）
    psf_radius: int = 100  # 像素，遠大於 Bloom（20-80 px）
    psf_type: str = "exponential"  # exponential/lorentzian（長拖尾）
    psf_decay_rate: float = 0.05  # 指數衰減率（越小拖尾越長）
    
    # 能量比例（總體縮放）
    energy_fraction: float = 0.05  # Halation 占總能量比例（5%）


@dataclass
class BloomParams:
    """
    Bloom（乳劑內散射）效果參數
    
    物理機制：光在乳劑內部的前向散射（Mie 散射），短距離擴散。
    
    - Artistic 模式：現有行為（純加法，視覺導向）
    - Physical 模式：能量守恆（高光散射，總能量不變）
    """
    mode: str = "artistic"  # "artistic" 或 "physical"
    
    # 共用參數
    sensitivity: float = 1.0      # 敏感度（控制效果強度）
    radius: int = 20              # 擴散半徑（像素）
    
    # Artistic 模式專用
    artistic_strength: float = 1.0  # 藝術模式強度
    artistic_base: float = 0.05     # 基礎擴散強度
    
    # Physical 模式專用
    threshold: float = 0.8          # 高光閾值（超過此值才散射，0-1）
    scattering_ratio: float = 0.08  # 散射比例（Bloom，8%）
    psf_type: str = "gaussian"      # PSF 類型（gaussian 為主）
    energy_conservation: bool = True  # 強制能量守恆


@dataclass
class WavelengthBloomParams:
    """
    波長依賴散射參數（Phase 1）
    
    遵循物理審查建議：
    - 散射能量權重 η(λ) ∝ λ^-p（p≈3-4）
    - PSF 寬度 σ(λ) ∝ (λ_ref/λ)^q（q≈0.5-1.0）
    - η 與 σ 解耦避免不可辨識性
    """
    enabled: bool = False  # 預設關閉（向後相容）
    
    # 能量權重參數
    wavelength_power: float = 3.5  # p 值（3-4），控制 η(λ) ∝ λ^-p
    
    # PSF 寬度標度參數
    radius_power: float = 0.8  # q 值（0.5-1.0），控制 σ(λ) ∝ (λ_ref/λ)^q
    reference_wavelength: float = 550.0  # 參考波長（nm），綠光
    
    # RGB 中心波長（nm）
    lambda_r: float = 650.0
    lambda_g: float = 550.0
    lambda_b: float = 450.0
    
    # 雙段核參數（核心 + 拖尾）
    core_fraction_r: float = 0.7  # 紅光核心占比（高斯部分）
    core_fraction_g: float = 0.75
    core_fraction_b: float = 0.8  # 藍光更多能量在核心
    
    tail_decay_rate: float = 0.1  # 拖尾衰減率（exponential）


@dataclass
class GrainParams:
    """
    顆粒噪聲參數
    
    - Artistic 模式：現有行為（加權正態分布）
    - Poisson 模式：物理導向（光子計數統計 + 銀鹽顆粒）
    """
    mode: str = "artistic"  # "artistic" 或 "poisson"
    intensity: float = 0.18  # 顆粒強度（0-1）
    
    # Poisson 模式專用
    exposure_level: float = 1000.0  # 假設的光子計數基線（用於 Poisson 分布）
    grain_size: float = 1.0         # 銀鹽顆粒大小（微米，相對值）
    grain_density: float = 1.0      # 顆粒密度（相對值，1.0 = 標準）


@dataclass
class EmulsionLayer:
    """
    模擬胶片中的單一感光乳劑層，包含光譜響應和成像特性
    """
    r_response_weight: float  # 紅光響應權重 (0-1)
    g_response_weight: float  # 綠光響應權重 (0-1)
    b_response_weight: float  # 藍光響應權重 (0-1)
    diffuse_weight: float  # 散射光權重係數（模擬光在胶片中的擴散）
    direct_weight: float  # 直射光權重係數（未擴散的直接響應）
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
    
    Version 0.2.1 新增：
    - physics_mode: 物理模式選擇
    - hd_curve_params: H&D 曲線參數
    - bloom_params: Bloom 效果參數
    - grain_params: 顆粒效果參數
    
    向後相容：新增欄位均有預設值，可正常載入舊版配置
    """
    name: str  # 胶片名稱
    color_type: str  # "color" 或 "single" (黑白)
    sensitivity_factor: float  # 高光敏感係數
    
    # 各感光層（彩色胶片有 RGB + 全色層，黑白胶片只有全色層）
    red_layer: Optional[EmulsionLayer]
    green_layer: Optional[EmulsionLayer]
    blue_layer: Optional[EmulsionLayer]
    panchromatic_layer: EmulsionLayer  # 全色感光層
    
    # Tone mapping 參數（顯示端，與 H&D 曲線分離）
    tone_params: ToneMappingParams
    
    # === v0.2.1 新增欄位（向後相容）===
    physics_mode: PhysicsMode = PhysicsMode.ARTISTIC
    hd_curve_params: Optional[HDCurveParams] = None
    bloom_params: Optional[BloomParams] = None
    grain_params: Optional[GrainParams] = None
    
    # === v0.3.0 中等物理升級（TASK-003）===
    halation_params: Optional[HalationParams] = None
    wavelength_bloom_params: Optional[WavelengthBloomParams] = None
    
    def __post_init__(self):
        """初始化預設值（確保向後相容）"""
        # 如果未設置 H&D 曲線參數，使用預設值
        if self.hd_curve_params is None:
            self.hd_curve_params = HDCurveParams()
        
        # 如果未設置 Bloom 參數，從 sensitivity_factor 推斷
        if self.bloom_params is None:
            self.bloom_params = BloomParams(
                sensitivity=self.sensitivity_factor,
                mode="artistic"
            )
        
        # 如果未設置顆粒參數，從 panchromatic_layer 推斷
        if self.grain_params is None:
            self.grain_params = GrainParams(
                intensity=self.panchromatic_layer.grain_intensity,
                mode="artistic"
            )
        
        # v0.3.0: 中等物理升級參數初始化
        if self.halation_params is None:
            self.halation_params = HalationParams()
        
        if self.wavelength_bloom_params is None:
            self.wavelength_bloom_params = WavelengthBloomParams()
    
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
                self.red_layer.r_response_weight, self.red_layer.g_response_weight, self.red_layer.b_response_weight,
                self.green_layer.r_response_weight, self.green_layer.g_response_weight, self.green_layer.b_response_weight,
                self.blue_layer.r_response_weight, self.blue_layer.g_response_weight, self.blue_layer.b_response_weight,
                self.panchromatic_layer.r_response_weight, self.panchromatic_layer.g_response_weight, self.panchromatic_layer.b_response_weight
            )
        else:
            return (
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                self.panchromatic_layer.r_response_weight, self.panchromatic_layer.g_response_weight, self.panchromatic_layer.b_response_weight
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
            r_response_weight=0.77, g_response_weight=0.12, b_response_weight=0.18,
            diffuse_weight=1.48, direct_weight=0.95, response_curve=1.18, grain_intensity=0.18
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.08, g_response_weight=0.85, b_response_weight=0.23,
            diffuse_weight=1.02, direct_weight=0.80, response_curve=1.02, grain_intensity=0.18
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.08, g_response_weight=0.09, b_response_weight=0.92,
            diffuse_weight=1.02, direct_weight=0.88, response_curve=0.78, grain_intensity=0.18
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.25, g_response_weight=0.35, b_response_weight=0.35,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.08
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
            r_response_weight=0.15, g_response_weight=0.35, b_response_weight=0.45,
            diffuse_weight=2.33, direct_weight=0.85, response_curve=1.15, grain_intensity=0.20
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
            r_response_weight=0.30, g_response_weight=0.12, b_response_weight=0.45,
            diffuse_weight=1.0, direct_weight=1.05, response_curve=1.25, grain_intensity=0.10
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
            r_response_weight=0.82, g_response_weight=0.10, b_response_weight=0.15,
            diffuse_weight=1.25, direct_weight=1.00, response_curve=1.12, grain_intensity=0.12
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.06, g_response_weight=0.88, b_response_weight=0.20,
            diffuse_weight=0.95, direct_weight=0.90, response_curve=1.05, grain_intensity=0.12
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.05, g_response_weight=0.08, b_response_weight=0.90,
            diffuse_weight=0.90, direct_weight=0.92, response_curve=0.85, grain_intensity=0.12
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.28, g_response_weight=0.40, b_response_weight=0.30,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.06
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
            r_response_weight=0.85, g_response_weight=0.08, b_response_weight=0.12,
            diffuse_weight=1.15, direct_weight=1.10, response_curve=1.25, grain_intensity=0.08
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.05, g_response_weight=0.90, b_response_weight=0.18,
            diffuse_weight=0.88, direct_weight=0.95, response_curve=1.15, grain_intensity=0.08
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.04, g_response_weight=0.06, b_response_weight=0.95,
            diffuse_weight=0.85, direct_weight=1.00, response_curve=0.90, grain_intensity=0.08
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.30, g_response_weight=0.38, b_response_weight=0.32,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.04
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
            r_response_weight=0.28, g_response_weight=0.32, b_response_weight=0.38,
            diffuse_weight=1.35, direct_weight=0.98, response_curve=1.18, grain_intensity=0.22
        ),
        tone_params=ToneMappingParams(
            gamma=2.1, shoulder_strength=0.16, linear_strength=0.48,
            linear_angle=0.22, toe_strength=0.30, toe_numerator=0.025, toe_denominator=0.33
        )
    )
    
    # Cinestill800T - 電影感（靈感來自 CineStill 800T）
    # 特色：移除 Anti-Halation 層，產生極端紅色光暈
    profiles["Cinestill800T"] = FilmProfile(
        name="Cinestill800T",
        color_type="color",
        sensitivity_factor=1.55,
        red_layer=EmulsionLayer(
            r_response_weight=0.80, g_response_weight=0.15, b_response_weight=0.20,
            diffuse_weight=1.65, direct_weight=0.90, response_curve=1.10, grain_intensity=0.25
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.10, g_response_weight=0.82, b_response_weight=0.28,
            diffuse_weight=1.18, direct_weight=0.75, response_curve=0.95, grain_intensity=0.25
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.12, g_response_weight=0.15, b_response_weight=0.88,
            diffuse_weight=1.35, direct_weight=0.82, response_curve=0.70, grain_intensity=0.25
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.22, g_response_weight=0.30, b_response_weight=0.42,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.15
        ),
        tone_params=ToneMappingParams(
            gamma=2.0, shoulder_strength=0.14, linear_strength=0.48,
            linear_angle=0.08, toe_strength=0.25, toe_numerator=0.03, toe_denominator=0.28
        ),
        # CineStill 特殊設定：無 AH 層 → 極端 Halation
        halation_params=HalationParams(
            enabled=True,
            transmittance_r=0.95,  # 紅光幾乎全穿透
            transmittance_g=0.90,
            transmittance_b=0.85,
            ah_absorption=0.0,  # 無 AH 層（完全反射）
            backplate_reflectance=0.8,  # 高反射
            psf_radius=200,  # 極大光暈（2x 標準）
            energy_fraction=0.15  # 3x 標準能量
        )
    )
    
    # === Phase 1: 經典底片新增 (2025-12-19) ===
    
    # Velvia50 - 風景之王（靈感來自 Fujifilm Velvia 50）
    profiles["Velvia50"] = FilmProfile(
        name="Velvia50",
        color_type="color",
        sensitivity_factor=0.95,  # 低感光度，光暈較少
        red_layer=EmulsionLayer(
            r_response_weight=0.88, g_response_weight=0.05, b_response_weight=0.10,
            diffuse_weight=0.75, direct_weight=1.15, response_curve=1.45, grain_intensity=0.05
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.03, g_response_weight=0.92, b_response_weight=0.15,
            diffuse_weight=0.70, direct_weight=1.10, response_curve=1.40, grain_intensity=0.05
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.02, g_response_weight=0.04, b_response_weight=0.98,
            diffuse_weight=0.65, direct_weight=1.20, response_curve=1.50, grain_intensity=0.05
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.25, g_response_weight=0.40, b_response_weight=0.35,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.03
        ),
        tone_params=ToneMappingParams(
            gamma=2.25, shoulder_strength=0.22, linear_strength=0.58,
            linear_angle=0.18, toe_strength=0.28, toe_numerator=0.01, toe_denominator=0.35
        )
    )
    
    # Gold200 - 陽光金黃（靈感來自 Kodak Gold 200）
    profiles["Gold200"] = FilmProfile(
        name="Gold200",
        color_type="color",
        sensitivity_factor=1.25,
        red_layer=EmulsionLayer(
            r_response_weight=0.83, g_response_weight=0.14, b_response_weight=0.12,
            diffuse_weight=1.35, direct_weight=0.98, response_curve=1.15, grain_intensity=0.16
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.12, g_response_weight=0.84, b_response_weight=0.18,
            diffuse_weight=1.05, direct_weight=0.85, response_curve=1.00, grain_intensity=0.16
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.10, g_response_weight=0.12, b_response_weight=0.88,
            diffuse_weight=0.95, direct_weight=0.85, response_curve=0.75, grain_intensity=0.16
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.32, g_response_weight=0.38, b_response_weight=0.28,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.09
        ),
        tone_params=ToneMappingParams(
            gamma=2.00, shoulder_strength=0.13, linear_strength=0.52,
            linear_angle=0.12, toe_strength=0.16, toe_numerator=0.02, toe_denominator=0.27
        )
    )
    
    # TriX400 - 街拍傳奇（靈感來自 Kodak Tri-X 400）
    profiles["TriX400"] = FilmProfile(
        name="TriX400",
        color_type="single",
        sensitivity_factor=1.48,
        red_layer=None,
        green_layer=None,
        blue_layer=None,
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.35, g_response_weight=0.30, b_response_weight=0.32,
            diffuse_weight=1.45, direct_weight=0.95, response_curve=1.28, grain_intensity=0.28
        ),
        tone_params=ToneMappingParams(
            gamma=2.35, shoulder_strength=0.20, linear_strength=0.45,
            linear_angle=0.28, toe_strength=0.38, toe_numerator=0.03, toe_denominator=0.36
        )
    )
    
    # === Phase 2: 日常經典底片 (2025-12-19) ===
    
    # ProImage100 - 日常柯達（靈感來自 Kodak ProImage 100）
    profiles["ProImage100"] = FilmProfile(
        name="ProImage100",
        color_type="color",
        sensitivity_factor=1.05,
        red_layer=EmulsionLayer(
            r_response_weight=0.80, g_response_weight=0.12, b_response_weight=0.14,
            diffuse_weight=1.20, direct_weight=1.02, response_curve=1.08, grain_intensity=0.14
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.08, g_response_weight=0.86, b_response_weight=0.20,
            diffuse_weight=0.98, direct_weight=0.88, response_curve=1.00, grain_intensity=0.14
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.08, g_response_weight=0.10, b_response_weight=0.90,
            diffuse_weight=0.92, direct_weight=0.90, response_curve=0.80, grain_intensity=0.14
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.30, g_response_weight=0.38, b_response_weight=0.30,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.07
        ),
        tone_params=ToneMappingParams(
            gamma=2.08, shoulder_strength=0.14, linear_strength=0.53,
            linear_angle=0.14, toe_strength=0.18, toe_numerator=0.015, toe_denominator=0.29
        )
    )
    
    # Superia400 - 富士日常（靈感來自 Fujifilm Superia 400）
    profiles["Superia400"] = FilmProfile(
        name="Superia400",
        color_type="color",
        sensitivity_factor=1.38,
        red_layer=EmulsionLayer(
            r_response_weight=0.76, g_response_weight=0.14, b_response_weight=0.18,
            diffuse_weight=1.30, direct_weight=0.92, response_curve=1.10, grain_intensity=0.20
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.10, g_response_weight=0.88, b_response_weight=0.25,
            diffuse_weight=1.10, direct_weight=0.82, response_curve=1.08, grain_intensity=0.20
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.10, g_response_weight=0.12, b_response_weight=0.90,
            diffuse_weight=1.00, direct_weight=0.86, response_curve=0.78, grain_intensity=0.20
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.24, g_response_weight=0.38, b_response_weight=0.36,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.10
        ),
        tone_params=ToneMappingParams(
            gamma=2.02, shoulder_strength=0.14, linear_strength=0.51,
            linear_angle=0.11, toe_strength=0.19, toe_numerator=0.02, toe_denominator=0.29
        )
    )
    
    # FP4Plus125 - 細膩灰階（靈感來自 Ilford FP4 Plus 125）
    profiles["FP4Plus125"] = FilmProfile(
        name="FP4Plus125",
        color_type="single",
        sensitivity_factor=1.15,
        red_layer=None,
        green_layer=None,
        blue_layer=None,
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.26, g_response_weight=0.36, b_response_weight=0.36,
            diffuse_weight=0.95, direct_weight=1.08, response_curve=1.22, grain_intensity=0.12
        ),
        tone_params=ToneMappingParams(
            gamma=2.05, shoulder_strength=0.14, linear_strength=0.52,
            linear_angle=0.20, toe_strength=0.32, toe_numerator=0.018, toe_denominator=0.34
        )
    )
    
    # === TASK-003: 中等物理測試配置 (2025-12-19) ===
    
    # CineStill 800T - 中等物理模式（測試配置）
    # 用途：驗證 Bloom + Halation 分離建模
    profiles["Cinestill800T_MediumPhysics"] = FilmProfile(
        name="Cinestill800T_MediumPhysics",
        color_type="color",
        sensitivity_factor=1.55,
        # 乳劑層配置（複製自 Cinestill800T）
        red_layer=EmulsionLayer(
            r_response_weight=0.80, g_response_weight=0.15, b_response_weight=0.20,
            diffuse_weight=1.65, direct_weight=0.90, response_curve=1.10, grain_intensity=0.25
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.10, g_response_weight=0.82, b_response_weight=0.28,
            diffuse_weight=1.18, direct_weight=0.75, response_curve=0.95, grain_intensity=0.25
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.12, g_response_weight=0.15, b_response_weight=0.88,
            diffuse_weight=1.35, direct_weight=0.82, response_curve=0.70, grain_intensity=0.25
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.22, g_response_weight=0.30, b_response_weight=0.42,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.15
        ),
        tone_params=ToneMappingParams(
            gamma=2.0, shoulder_strength=0.14, linear_strength=0.48,
            linear_angle=0.08, toe_strength=0.25, toe_numerator=0.03, toe_denominator=0.28
        ),
        # === 關鍵：啟用中等物理模式 ===
        physics_mode=PhysicsMode.PHYSICAL,
        bloom_params=BloomParams(
            mode="physical",           # 物理模式 Bloom（乳劑內散射）
            threshold=0.8,
            scattering_ratio=0.08,     # 8% 能量散射
            psf_type="gaussian",
            energy_conservation=True
        ),
        halation_params=HalationParams(
            enabled=True,
            transmittance_r=0.95,      # CineStill 極端特性：紅光幾乎全穿透
            transmittance_g=0.90,
            transmittance_b=0.85,
            ah_absorption=0.0,         # 無 AH 層（完全反射）
            backplate_reflectance=0.8, # 高反射（0.8）
            psf_radius=200,            # 極大光暈半徑（2x 標準）
            psf_type="exponential",    # 指數拖尾
            energy_fraction=0.15       # 15% 能量（3x 標準）
        )
    )
    
    # Portra400 - 中等物理模式（測試配置）
    # 用途：驗證標準膠片的 AH 層效果
    profiles["Portra400_MediumPhysics"] = FilmProfile(
        name="Portra400_MediumPhysics",
        color_type="color",
        sensitivity_factor=1.35,
        # 乳劑層配置（複製自 Portra400）
        red_layer=EmulsionLayer(
            r_response_weight=0.82, g_response_weight=0.10, b_response_weight=0.15,
            diffuse_weight=1.25, direct_weight=1.00, response_curve=1.12, grain_intensity=0.12
        ),
        green_layer=EmulsionLayer(
            r_response_weight=0.06, g_response_weight=0.88, b_response_weight=0.20,
            diffuse_weight=0.95, direct_weight=0.90, response_curve=1.05, grain_intensity=0.12
        ),
        blue_layer=EmulsionLayer(
            r_response_weight=0.05, g_response_weight=0.08, b_response_weight=0.90,
            diffuse_weight=0.90, direct_weight=0.92, response_curve=0.85, grain_intensity=0.12
        ),
        panchromatic_layer=EmulsionLayer(
            r_response_weight=0.28, g_response_weight=0.40, b_response_weight=0.30,
            diffuse_weight=0.0, direct_weight=0.0, response_curve=0.0, grain_intensity=0.06
        ),
        tone_params=ToneMappingParams(
            gamma=1.95, shoulder_strength=0.12, linear_strength=0.55,
            linear_angle=0.15, toe_strength=0.18, toe_numerator=0.01, toe_denominator=0.28
        ),
        # === 啟用中等物理模式 ===
        physics_mode=PhysicsMode.PHYSICAL,
        bloom_params=BloomParams(
            mode="physical",           # 物理模式 Bloom
            threshold=0.8,
            scattering_ratio=0.08,     # 標準 8% 能量
            psf_type="gaussian",
            energy_conservation=True
        ),
        halation_params=HalationParams(
            enabled=True,
            transmittance_r=0.7,       # 標準膠片透過率（波長依賴）
            transmittance_g=0.5,
            transmittance_b=0.3,       # 藍光易被吸收
            ah_absorption=0.95,        # 有 AH 層（95% 吸收）
            backplate_reflectance=0.3, # 標準反射率
            psf_radius=100,            # 標準光暈半徑
            psf_type="exponential",
            energy_fraction=0.05       # 標準 5% 能量
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
