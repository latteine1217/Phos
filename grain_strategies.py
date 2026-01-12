"""
Grain Generation Strategies

使用策略模式實現不同的顆粒生成方法。

Strategies:
    - ArtisticGrainStrategy: 視覺導向（中間調顆粒最明顯）
    - PoissonGrainStrategy: 物理導向（光子計數統計 + 銀鹽顆粒）

Version: 0.6.4 (P1-2: Strategy Pattern Refactoring)
Philosophy: Good Taste + Simplicity (eliminate if-elif branching)
"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np
import cv2
from film_models import GrainParams

# Constants (從 film_models.py 導入)
from film_models import (
    GRAIN_WEIGHT_MIN,
    GRAIN_WEIGHT_MAX,
    GRAIN_SENS_MIN,
    GRAIN_SENS_MAX,
    GRAIN_BLUR_KERNEL,
    GRAIN_BLUR_SIGMA
)


class GrainStrategy(ABC):
    """
    顆粒生成策略抽象基類
    
    每個策略代表一種顆粒生成方法：
    - Artistic: 視覺導向（中間調最明顯）
    - Poisson: 物理導向（光子計數統計）
    
    Philosophy:
        - 策略類 = 可辯護的假設集合
        - 每個策略獨立可測試
        - 消除條件分支（Good Taste）
    """
    
    @abstractmethod
    def apply(
        self, 
        lux_channel: np.ndarray, 
        grain_params: GrainParams,
        sens: Optional[float] = None
    ) -> np.ndarray:
        """
        應用顆粒效果
        
        Args:
            lux_channel: 光度通道數據 (0-1 範圍，float32)
            grain_params: 顆粒參數（包含 intensity 等）
            sens: 敏感度參數（僅 artistic 模式使用）
            
        Returns:
            np.ndarray: 顆粒噪聲（標準化到 [-1, 1] 範圍）
            
        Raises:
            ValueError: 參數無效或缺失必要參數
        """
        pass


class ArtisticGrainStrategy(GrainStrategy):
    """
    藝術模式顆粒（視覺導向）
    
    物理假設（Artistic Assumptions）：
        1. 中間調顆粒最明顯（美學選擇，非物理）
        2. 正負噪聲對稱（視覺平衡）
        3. 權重函數：w(L) = 2(0.5 - |L - 0.5|)
        4. 輕微模糊：σ = 0.5px（柔和質感）
    
    物理意義：
        - 模擬傳統膠片的視覺印象（非真實物理）
        - 顆粒分布基於觀察者的主觀感受
        - 優先考慮美感而非物理準確性
    
    參數來源：
        - 權重函數：藝術選擇（保留 v0.1.0 美學）
        - 模糊 sigma：經驗值（2024-06 視覺測試）
        - sens 範圍：UI 限制（0.4-0.6 典型值）
    
    Ref: Phos.py generate_grain() artistic mode (lines 287-309)
    """
    
    def apply(
        self, 
        lux_channel: np.ndarray, 
        grain_params: GrainParams,
        sens: Optional[float] = None
    ) -> np.ndarray:
        """
        應用藝術模式顆粒
        
        Args:
            lux_channel: 光度通道 (0-1 範圍)
            grain_params: 顆粒參數（需要 intensity）
            sens: 敏感度參數（必須提供，否則拋出異常）
            
        Returns:
            顆粒噪聲 ([-1, 1] 範圍)
            
        Raises:
            ValueError: sens 參數缺失
        """
        if sens is None:
            raise ValueError("Artistic mode requires 'sens' parameter")
        
        # 1. 創建正負噪聲（使用平方正態分佈產生更自然的顆粒）
        noise = np.random.normal(0, 1, lux_channel.shape).astype(np.float32)
        noise = noise ** 2  # 平方增強顆粒質感
        # v0.8.2 HOTFIX: 標準化平方噪聲以避免極端值
        # Chi-squared(1) 分布的期望值是 1，標準差是 sqrt(2)
        noise = (noise - 1.0) / np.sqrt(2.0)  # 標準化到 mean=0, std=1
        noise = noise * np.random.choice([-1, 1], lux_channel.shape)  # 正負對稱
        
        # 2. 創建權重圖（中等亮度區域權重最高）
        # 模擬胶片顆粒在中間調最明顯的特性
        weights = (0.5 - np.abs(lux_channel - 0.5)) * 2
        weights = np.clip(weights, GRAIN_WEIGHT_MIN, GRAIN_WEIGHT_MAX)
        
        # 3. 應用權重和敏感度
        sens_grain = np.clip(sens, GRAIN_SENS_MIN, GRAIN_SENS_MAX)
        weighted_noise = noise * weights * sens_grain
        
        # 4. 添加輕微模糊使顆粒更柔和
        weighted_noise = cv2.GaussianBlur(
            weighted_noise, 
            GRAIN_BLUR_KERNEL, 
            GRAIN_BLUR_SIGMA
        )
        
        return np.clip(weighted_noise, -1, 1)


class PoissonGrainStrategy(GrainStrategy):
    """
    Poisson 模式顆粒（物理導向）
    
    物理假設（Physics-Based）：
        1. Poisson 統計：光子計數服從 Poisson(λ)
        2. 正態近似：λ > 20 時，Poisson(λ) ≈ Normal(λ, √λ)
        3. 相對噪聲：σ_rel = 1/√λ（暗部噪聲更明顯）
        4. 銀鹽顆粒：空間相關性（顆粒有物理尺寸）
    
    物理機制：
        - 感光乳劑中的光子計數統計噪聲
        - 暗部：光子少 → 相對噪聲大（σ/μ 大）
        - 亮部：光子多 → 相對噪聲小（σ/μ 小）
        - 顆粒尺寸：銀鹽晶體的物理尺寸（0.5-5μm）
    
    參數來源：
        - exposure_level: 假設基線光子計數（1000 = 典型值）
        - grain_size: 銀鹽晶體尺寸（1.0 = 標準，單位：微米）
        - grain_density: 顆粒密度（1.0 = 標準 ISO）
        - 3-sigma 標準化：99.7% 顆粒在 [-1, 1] 範圍內
    
    Literature:
        - Poisson 統計：James, T. H. (1977). "The Theory of the Photographic Process"
        - 銀鹽顆粒：Mees, C. E. K. (1942). "The Theory of the Photographic Process"
    
    Ref: Phos.py generate_grain() poisson mode (lines 311-354)
    """
    
    def apply(
        self, 
        lux_channel: np.ndarray, 
        grain_params: GrainParams,
        sens: Optional[float] = None
    ) -> np.ndarray:
        """
        應用 Poisson 模式顆粒
        
        Args:
            lux_channel: 光度通道 (0-1 範圍)
            grain_params: 顆粒參數（需要 exposure_level, grain_size, grain_density）
            sens: 敏感度參數（Poisson 模式忽略此參數）
            
        Returns:
            顆粒噪聲 ([-1, 1] 範圍)
            
        Note:
            sens 參數被忽略，因為 Poisson 模式基於物理統計，
            不需要主觀的敏感度調整
        """
        # 1. 將相對曝光量轉換為平均光子計數
        photon_count_mean = lux_channel * grain_params.exposure_level
        
        # 避免零或負值（添加小偏移）
        photon_count_mean = np.clip(photon_count_mean, 1.0, None)
        
        # 2. 根據 Poisson 分布生成實際光子計數
        # 使用正態近似（當 λ > 20 時，Poisson(λ) ≈ Normal(λ, √λ)）
        photon_count_actual = np.random.normal(
            loc=photon_count_mean, 
            scale=np.sqrt(photon_count_mean)
        ).astype(np.float32)
        
        # 確保非負
        photon_count_actual = np.maximum(photon_count_actual, 0)
        
        # 3. 計算相對噪聲：(實際計數 - 期望計數) / 期望計數
        relative_noise = (photon_count_actual - photon_count_mean) / (photon_count_mean + 1e-6)
        
        # 4. 銀鹽顆粒效應：空間相關性（顆粒有物理尺寸）
        grain_blur_sigma = grain_params.grain_size  # 微米 → 像素（簡化對應）
        if grain_blur_sigma > 0.5:
            kernel_size = int(grain_blur_sigma * 4) | 1  # 確保奇數
            kernel_size = max(3, min(kernel_size, 15))  # 限制範圍
            relative_noise = cv2.GaussianBlur(
                relative_noise, 
                (kernel_size, kernel_size), 
                grain_blur_sigma
            )
        
        # 5. 標準化 relative_noise 到基準範圍（3-sigma 原則）
        noise_std = np.std(relative_noise)
        if noise_std > 1e-6:
            relative_noise_normalized = relative_noise / (3 * noise_std)
        else:
            relative_noise_normalized = relative_noise
        
        # 6. 應用顆粒密度與強度調整
        grain_noise = (relative_noise_normalized * 
                      grain_params.grain_density * 
                      grain_params.intensity)
        
        return np.clip(grain_noise, -1, 1)


def get_grain_strategy(grain_params: GrainParams) -> GrainStrategy:
    """
    工廠函數：根據模式選擇策略
    
    消除條件分支（Good Taste 原則）
    
    Args:
        grain_params: 顆粒參數（包含 mode 屬性）
        
    Returns:
        對應的策略實例
        
    Raises:
        ValueError: 未知的顆粒模式
        
    Example:
        >>> grain_params = GrainParams(mode="artistic", intensity=0.18)
        >>> strategy = get_grain_strategy(grain_params)
        >>> isinstance(strategy, ArtisticGrainStrategy)
        True
    """
    mode = grain_params.mode
    
    if mode == "artistic":
        return ArtisticGrainStrategy()
    elif mode == "poisson":
        return PoissonGrainStrategy()
    else:
        raise ValueError(
            f"Unknown grain mode: {mode}. "
            f"Expected 'artistic' or 'poisson'."
        )


def generate_grain(
    lux_channel: np.ndarray,
    grain_params: GrainParams,
    sens: Optional[float] = None
) -> np.ndarray:
    """
    統一的顆粒生成介面（向後相容）
    
    委派給對應的策略類，消除主函數中的條件分支。
    
    物理機制：
        - Artistic 模式：視覺導向，中間調顆粒最明顯（保留現有美感）
        - Poisson 模式：物理導向，基於光子計數統計（暗部噪聲更明顯）
    
    Args:
        lux_channel: 光度通道數據 (0-1 範圍，float32)
        grain_params: GrainParams 對象（包含模式與所有參數）
        sens: 敏感度參數（僅 artistic 模式使用，poisson 模式忽略）
    
    Returns:
        np.ndarray: 顆粒噪聲（標準化到 [-1, 1] 範圍）
    
    Raises:
        ValueError: 
            - 未知的顆粒模式
            - Artistic 模式缺少 sens 參數
    
    Example:
        >>> # Artistic 模式（向後相容）
        >>> grain_params = GrainParams(mode="artistic", intensity=0.18)
        >>> noise = generate_grain(lux, grain_params, sens=0.5)
        
        >>> # Poisson 模式（物理準確）
        >>> grain_params = GrainParams(
        ...     mode="poisson",
        ...     intensity=0.15,
        ...     exposure_level=1000.0,
        ...     grain_size=1.0
        ... )
        >>> noise = generate_grain(lux, grain_params)
    
    Version: 0.6.4 (Strategy Pattern Refactoring)
    Ref: Phos.py original generate_grain() (lines 245-357)
    """
    strategy = get_grain_strategy(grain_params)
    return strategy.apply(lux_channel, grain_params, sens)
