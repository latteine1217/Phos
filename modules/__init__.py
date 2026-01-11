"""
Phos 核心模組

將 Phos.py 的核心功能拆分為可維護的模組。
保持 100% 向後相容。

設計原則：
    - Good Taste: 每個模組職責單一（< 500 行）
    - Never Break Userspace: 100% 向後相容
    - Pragmatism: 解決真問題（維護困難、測試耦合）
    - Simplicity: 降低複雜度（1916 行 → 5 個小模組）

Modules:
    - optical_core: 光度計算核心
        · spectral_response: 計算膠片感光層的光譜響應
        · average_response: 計算平均光譜響應
        · standardize: 標準化圖像尺寸
    
    - tone_mapping: Tone Mapping 策略
        · apply_reinhard: Reinhard tone mapping
        · apply_filmic: Filmic tone mapping
    
    - psf_utils: PSF 生成工具
        · create_dual_kernel_psf: 創建雙段核 PSF
        · get_gaussian_kernel: 獲取高斯核（帶快取）
        · get_exponential_kernel_approximation: 指數核近似
        · convolve_fft: FFT 卷積
        · convolve_adaptive: 自適應卷積
        · load_mie_lookup_table: Mie 散射查表載入
        · lookup_mie_params: Mie 參數插值
    
    - wavelength_effects: 波長依賴光學效果
        · apply_wavelength_bloom: 波長依賴 Bloom 散射
        · apply_bloom_with_psf: 使用自定義 PSF 的 Bloom
        · apply_halation: Beer-Lambert Halation 效果
        · apply_optical_effects_separated: 分離應用 Bloom + Halation
    
    - image_processing: 圖像處理
        · apply_hd_curve: 應用 H&D 特性曲線
        · combine_layers_for_channel: 組合散射光與直射光

Version: 0.7.0-dev (Modularization - PR #1)
Date: 2026-01-12

Note:
    此為 PR #1 版本，僅建立基礎結構。
    各子模組將在後續 PR 中逐步實作。
"""

__version__ = "0.7.0-dev"
__author__ = "Phos Team"
__status__ = "Development"

# ==================== PR #2: Optical Core ====================

from .optical_core import (
    spectral_response,
    average_response,
    standardize
)

# ==================== PR #3: Tone Mapping ====================

from .tone_mapping import (
    apply_reinhard_to_channel,
    apply_reinhard,
    apply_filmic_to_channel,
    apply_filmic
)

# ==================== PR #4: PSF Utils ====================

from .psf_utils import (
    create_dual_kernel_psf,
    load_mie_lookup_table,
    lookup_mie_params,
    convolve_fft,
    convolve_adaptive,
    get_gaussian_kernel,
    get_exponential_kernel_approximation
)

# ==================== PR #5: Wavelength Effects ====================

from .wavelength_effects import (
    apply_bloom_with_psf,
    apply_wavelength_bloom,
    apply_halation,
    apply_optical_effects_separated
)

# ==================== PR #6: Image Processing ====================

from .image_processing import (
    apply_hd_curve,
    combine_layers_for_channel
)

__all__ = [
    # PR #2: Optical Core
    'spectral_response',
    'average_response',
    'standardize',
    
    # PR #3: Tone Mapping
    'apply_reinhard_to_channel',
    'apply_reinhard',
    'apply_filmic_to_channel',
    'apply_filmic',
    
    # PR #4: PSF Utils
    'create_dual_kernel_psf',
    'load_mie_lookup_table',
    'lookup_mie_params',
    'convolve_fft',
    'convolve_adaptive',
    'get_gaussian_kernel',
    'get_exponential_kernel_approximation',
    
    # PR #5: Wavelength Effects
    'apply_bloom_with_psf',
    'apply_wavelength_bloom',
    'apply_halation',
    'apply_optical_effects_separated',
    
    # PR #6: Image Processing
    'apply_hd_curve',
    'combine_layers_for_channel',
]
