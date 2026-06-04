# pyright: reportGeneralTypeIssues=false
# pyright: ignore
"""
Phos 核心處理模組

What:
    提供與 UI 無關的膠片模擬處理流程與相容 API。

Why:
    原本 `Phos.py` 直接承載 Streamlit 介面，導致核心演算法難以被桌面 UI、
    測試與打包流程重用。此版本將 `Phos.py` 收斂為純處理模組，保留既有函數名，
    同時完全移除 Streamlit 依賴。
"""

import time
import warnings
from copy import deepcopy
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any, BinaryIO, Optional, Tuple

import cv2
import numpy as np

from bloom_strategies import apply_bloom
import film_models
from film_models import (
    BASE_DIFFUSION_FACTOR,
    BLOOM_RADIUS_FACTOR,
    BLOOM_RADIUS_MAX,
    BLOOM_RADIUS_MIN,
    BLOOM_STRENGTH_FACTOR,
    BloomParams,
    FILMIC_EXPOSURE_SCALE,
    FilmProfile,
    GRAIN_BLUR_KERNEL,
    GRAIN_BLUR_SIGMA,
    GRAIN_SENS_MAX,
    GRAIN_SENS_MIN,
    GRAIN_WEIGHT_MAX,
    GRAIN_WEIGHT_MIN,
    GrainParams,
    PhysicsMode,
    REINHARD_GAMMA_ADJUSTMENT,
    SENSITIVITY_BASE,
    SENSITIVITY_MAX,
    SENSITIVITY_MIN,
    SENSITIVITY_SCALE,
    get_film_profile,
)
from grain_strategies import generate_grain
from modules.image_processing import apply_hd_curve, combine_layers_for_channel
from modules.optical_core import average_response, linear_to_srgb, spectral_response, standardize
from modules.psf_utils import convolve_adaptive, get_exponential_kernel_approximation, get_gaussian_kernel
from modules.tone_mapping import apply_filmic, apply_reinhard
from modules.wavelength_effects import apply_halation, apply_optical_effects_separated, apply_wavelength_bloom

__all__ = []


def deprecated(reason: str, replacement: Optional[str] = None, remove_in: Optional[str] = None):
    """
    What:
        標記函數為過時。

    Why:
        保留舊 API 但清楚告知遷移方向，避免 silent breakage。
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            message = f"{func.__name__} is deprecated. {reason}"
            if replacement:
                message += f" Use {replacement} instead."
            if remove_in:
                message += f" Will be removed in {remove_in}."
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator


@lru_cache(maxsize=None)
def get_cached_film_profile(film_type: str) -> FilmProfile:
    """
    What:
        快取膠片配置模板。

    Why:
        膠片配置建立成本不高但會被頻繁重用；快取模板後再複製，可同時兼顧效能與狀態隔離。
    """
    return get_film_profile(film_type)


def apply_grain(
    response_r: Optional[np.ndarray],
    response_g: Optional[np.ndarray],
    response_b: Optional[np.ndarray],
    response_total: np.ndarray,
    film: FilmProfile,
    sens: float,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    What:
        根據膠片設定生成彩色或黑白顆粒噪聲。

    Why:
        顆粒策略已抽至 `grain_strategies.py`，此函數保留主流程需要的通道協調與向後相容 API。
    """
    use_poisson = (
        hasattr(film, "grain_params")
        and film.grain_params is not None
        and film.grain_params.mode == "poisson"
    )

    if film.color_type == "color" and all(channel is not None for channel in [response_r, response_g, response_b]):
        if use_poisson:
            weighted_noise_r = generate_grain(response_r, film.grain_params)
            weighted_noise_g = generate_grain(response_g, film.grain_params)
            weighted_noise_b = generate_grain(response_b, film.grain_params)
        else:
            weighted_noise_r = generate_grain(response_r, film.grain_params, sens=sens)
            weighted_noise_g = generate_grain(response_g, film.grain_params, sens=sens)
            weighted_noise_b = generate_grain(response_b, film.grain_params, sens=sens)
        weighted_noise_total = None
    else:
        if use_poisson:
            weighted_noise_total = generate_grain(response_total, film.grain_params)
        else:
            weighted_noise_total = generate_grain(response_total, film.grain_params, sens=sens)
        weighted_noise_r = None
        weighted_noise_g = None
        weighted_noise_b = None

    return weighted_noise_r, weighted_noise_g, weighted_noise_b, weighted_noise_total


def calculate_bloom_params(avg_response: float, sens_factor: float) -> Tuple[float, int, float, float]:
    """
    What:
        由平均亮度推導藝術模式 Bloom 參數。

    Why:
        保留既有視覺調校行為，避免舊膠片配置與測試結果漂移。
    """
    avg_response_perceptual = np.power(avg_response, 1.0 / 2.2)
    sens = float((1.0 - avg_response_perceptual) * SENSITIVITY_SCALE + SENSITIVITY_BASE)
    sens = float(np.clip(sens, SENSITIVITY_MIN, SENSITIVITY_MAX))

    strength = float(BLOOM_STRENGTH_FACTOR * (sens ** 2) * sens_factor)
    radius = int(BLOOM_RADIUS_FACTOR * (sens ** 2) * sens_factor)
    radius = int(np.clip(radius, BLOOM_RADIUS_MIN, BLOOM_RADIUS_MAX))
    base = float(BASE_DIFFUSION_FACTOR * sens_factor)

    return sens, radius, strength, base


@deprecated(
    reason="This function has been refactored into bloom_strategies.MieCorrectedBloomStrategy",
    replacement="apply_bloom(lux, bloom_params) with mode='mie_corrected'",
    remove_in="v0.7.0",
)
def apply_bloom_mie_corrected(
    lux: np.ndarray,
    bloom_params: BloomParams,
    wavelength: float = 550.0,
) -> np.ndarray:
    """
    What:
        應用 Mie 散射修正 Bloom。

    Why:
        舊文檔與部分外部代碼仍可能引用此函數，因此保留一層兼容包裝。
    """
    if bloom_params.mode != "mie_corrected":
        return apply_bloom(lux, bloom_params)

    lambda_ref = bloom_params.reference_wavelength
    eta_lambda = bloom_params.base_scattering_ratio * (lambda_ref / wavelength) ** bloom_params.energy_wavelength_exponent
    sigma_core = bloom_params.base_sigma_core * (lambda_ref / wavelength) ** bloom_params.psf_width_exponent
    kappa_tail = bloom_params.base_kappa_tail * (lambda_ref / wavelength) ** bloom_params.psf_tail_exponent

    if wavelength <= 450:
        rho = bloom_params.psf_core_ratio_b
    elif wavelength >= 650:
        rho = bloom_params.psf_core_ratio_r
    elif wavelength < 550:
        ratio = (wavelength - 450) / 100
        rho = (1 - ratio) * bloom_params.psf_core_ratio_b + ratio * bloom_params.psf_core_ratio_g
    else:
        ratio = (wavelength - 550) / 100
        rho = (1 - ratio) * bloom_params.psf_core_ratio_g + ratio * bloom_params.psf_core_ratio_r

    highlights = np.maximum(lux - bloom_params.threshold, 0)
    scattered_energy = highlights * eta_lambda

    if bloom_params.psf_dual_segment:
        ksize_core = int(sigma_core * 6) | 1
        kernel_core = get_gaussian_kernel(sigma_core, ksize_core)
        core_component = convolve_adaptive(scattered_energy, kernel_core, method="spatial")

        ksize_tail = int(kappa_tail * 5) | 1
        kernel_tail = get_exponential_kernel_approximation(kappa_tail, ksize_tail)
        tail_component = convolve_adaptive(scattered_energy, kernel_tail, method="fft")
        bloom_layer = rho * core_component + (1 - rho) * tail_component
    else:
        ksize = int(sigma_core * 6) | 1
        kernel = get_gaussian_kernel(sigma_core, ksize)
        bloom_layer = convolve_adaptive(scattered_energy, kernel, method="auto")

    if bloom_params.energy_conservation:
        total_in = np.sum(scattered_energy)
        total_out = np.sum(bloom_layer)
        if total_out > 1e-6:
            bloom_layer = bloom_layer * (total_in / total_out)

    result = lux - scattered_energy + bloom_layer
    return np.clip(result, 0, 1)


def optical_processing(
    response_r: Optional[np.ndarray],
    response_g: Optional[np.ndarray],
    response_b: Optional[np.ndarray],
    response_total: np.ndarray,
    film: FilmProfile,
    grain_style: str,
    tone_style: str,
    use_film_spectra: bool = False,
    film_spectra_name: str = "Portra400",
    film_illuminant: str = "flat",
    exposure_time: float = 1.0,
) -> np.ndarray:
    """
    What:
        執行完整膠片光學處理鏈。

    Why:
        這是 UI 無關的核心流程，桌面版與測試都必須共用同一條管線，才能避免結果分叉。
    """
    if (
        hasattr(film, "reciprocity_params")
        and film.reciprocity_params is not None
        and film.reciprocity_params.enabled
        and exposure_time != 1.0
    ):
        try:
            from reciprocity_failure import apply_reciprocity_failure

            if film.color_type == "color" and all(channel is not None for channel in [response_r, response_g, response_b]):
                rgb_stack = np.stack([response_r, response_g, response_b], axis=2)
                rgb_stack = apply_reciprocity_failure(rgb_stack, exposure_time, film.reciprocity_params)
                response_r = rgb_stack[:, :, 0]
                response_g = rgb_stack[:, :, 1]
                response_b = rgb_stack[:, :, 2]
            else:
                response_total = apply_reciprocity_failure(
                    response_total[:, :, np.newaxis],
                    exposure_time,
                    film.reciprocity_params,
                )[:, :, 0]
        except ImportError:
            warnings.warn("reciprocity_failure 模組未找到，跳過互易律失效處理")
        except Exception as exc:
            warnings.warn(f"互易律失效處理失敗，跳過: {exc}")

    avg = average_response(response_total)
    sens, radius, strength, base = calculate_bloom_params(avg, film.sensitivity_factor)

    use_grain = grain_style != "不使用"
    if use_grain:
        grain_r, grain_g, grain_b, grain_total_noise = apply_grain(
            response_r, response_g, response_b, response_total, film, sens
        )
    else:
        grain_r = grain_g = grain_b = grain_total_noise = None

    use_physical_bloom = hasattr(film, "bloom_params") and film.bloom_params.mode == "physical"

    if film.color_type == "color" and all(channel is not None for channel in [response_r, response_g, response_b]):
        use_medium_physics = (
            use_physical_bloom
            and hasattr(film, "halation_params")
            and film.halation_params.enabled
        )
        use_wavelength_bloom = (
            use_medium_physics
            and hasattr(film, "wavelength_bloom_params")
            and film.wavelength_bloom_params is not None
            and film.wavelength_bloom_params.enabled
        )

        if use_wavelength_bloom:
            bloom_r, bloom_g, bloom_b = apply_wavelength_bloom(
                response_r,
                response_g,
                response_b,
                film.wavelength_bloom_params,
                film.bloom_params,
            )
            bloom_r = apply_halation(bloom_r, film.halation_params, wavelength=650.0)
            bloom_g = apply_halation(bloom_g, film.halation_params, wavelength=550.0)
            bloom_b = apply_halation(bloom_b, film.halation_params, wavelength=450.0)
        elif use_medium_physics:
            bloom_r, bloom_g, bloom_b = apply_optical_effects_separated(
                response_r,
                response_g,
                response_b,
                film.bloom_params,
                film.halation_params,
                blur_scale_r=3,
                blur_scale_g=2,
                blur_scale_b=1,
            )
        elif use_physical_bloom:
            bloom_r = apply_bloom(response_r, film.bloom_params)
            bloom_g = apply_bloom(response_g, film.bloom_params)
            bloom_b = apply_bloom(response_b, film.bloom_params)
        else:
            artistic_params = BloomParams(
                mode="artistic",
                sensitivity=sens,
                radius=radius,
                artistic_strength=strength,
                artistic_base=base,
            )
            bloom_r = apply_bloom(response_r, artistic_params)
            bloom_g = apply_bloom(response_g, artistic_params)
            bloom_b = apply_bloom(response_b, artistic_params)

        response_r_final = combine_layers_for_channel(
            bloom_r,
            response_r,
            film.red_layer,
            grain_r,
            grain_g,
            grain_b,
            film.panchromatic_layer.grain_intensity,
            use_grain,
        )
        response_g_final = combine_layers_for_channel(
            bloom_g,
            response_g,
            film.green_layer,
            grain_r,
            grain_g,
            grain_b,
            film.panchromatic_layer.grain_intensity,
            use_grain,
        )
        response_b_final = combine_layers_for_channel(
            bloom_b,
            response_b,
            film.blue_layer,
            grain_r,
            grain_g,
            grain_b,
            film.panchromatic_layer.grain_intensity,
            use_grain,
        )

        use_hd_curve = hasattr(film, "hd_curve_params") and film.hd_curve_params.enabled
        if use_hd_curve:
            response_r_final = apply_hd_curve(response_r_final, film.hd_curve_params)
            response_g_final = apply_hd_curve(response_g_final, film.hd_curve_params)
            response_b_final = apply_hd_curve(response_b_final, film.hd_curve_params)

        if tone_style == "filmic":
            result_r, result_g, result_b, _ = apply_filmic(
                response_r_final, response_g_final, response_b_final, response_total, film
            )
        else:
            result_r, result_g, result_b, _ = apply_reinhard(
                response_r_final, response_g_final, response_b_final, response_total, film
            )

        if use_film_spectra:
            try:
                from phos_core import (
                    apply_film_spectral_sensitivity,
                    get_illuminant_d65,
                    load_film_sensitivity,
                    rgb_to_spectrum,
                )

                lux_combined = np.stack([result_r, result_g, result_b], axis=2)
                spectrum = rgb_to_spectrum(lux_combined, use_tiling=True, tile_size=512)
                film_curves = load_film_sensitivity(film_spectra_name)
                illuminant_spd = get_illuminant_d65() if film_illuminant == "D65" else None
                rgb_with_film = apply_film_spectral_sensitivity(
                    spectrum,
                    film_curves,
                    normalize=True,
                    illuminant_spd=illuminant_spd,
                )
                result_r = rgb_with_film[:, :, 0]
                result_g = rgb_with_film[:, :, 1]
                result_b = rgb_with_film[:, :, 2]
            except Exception as exc:
                warnings.warn(f"膠片光譜處理失敗，使用原始結果: {exc}")

        result_r_srgb = linear_to_srgb(result_r)
        result_g_srgb = linear_to_srgb(result_g)
        result_b_srgb = linear_to_srgb(result_b)
        combined_r = (result_r_srgb * 255).astype(np.uint8)
        combined_g = (result_g_srgb * 255).astype(np.uint8)
        combined_b = (result_b_srgb * 255).astype(np.uint8)
        return cv2.merge([combined_b, combined_g, combined_r])

    artistic_params = BloomParams(
        mode="artistic",
        sensitivity=sens,
        radius=radius,
        artistic_strength=strength,
        artistic_base=base,
    )
    bloom = apply_bloom(response_total, artistic_params)

    if use_grain and grain_total_noise is not None:
        lux_final = (
            bloom * film.panchromatic_layer.diffuse_weight
            + response_total * film.panchromatic_layer.direct_weight
            + grain_total_noise * film.panchromatic_layer.grain_intensity
        )
    else:
        lux_final = (
            bloom * film.panchromatic_layer.diffuse_weight
            + response_total * film.panchromatic_layer.direct_weight
        )

    use_hd_curve = hasattr(film, "hd_curve_params") and film.hd_curve_params.enabled
    if use_hd_curve:
        lux_final = apply_hd_curve(lux_final, film.hd_curve_params)

    if tone_style == "filmic":
        _, _, _, result_total = apply_filmic(None, None, None, lux_final, film)
    else:
        _, _, _, result_total = apply_reinhard(None, None, None, lux_final, film)

    result_total_srgb = linear_to_srgb(result_total)
    return (result_total_srgb * 255).astype(np.uint8)


def adjust_grain_intensity(film: FilmProfile, grain_style: str) -> FilmProfile:
    """
    What:
        根據 UI 風格倍率調整顆粒強度。

    Why:
        保留既有「柔和 / 較粗 / 不使用」使用者語意，而不直接改寫底層模型預設。
    """
    multipliers = {
        "默認": 1.0,
        "柔和": 0.5,
        "較粗": 1.5,
        "不使用": 0.0,
    }
    multiplier = multipliers.get(grain_style, 1.0)

    from dataclasses import replace

    if film.color_type == "color" and film.red_layer and film.green_layer and film.blue_layer:
        return replace(
            film,
            red_layer=replace(film.red_layer, grain_intensity=film.red_layer.grain_intensity * multiplier),
            green_layer=replace(film.green_layer, grain_intensity=film.green_layer.grain_intensity * multiplier),
            blue_layer=replace(film.blue_layer, grain_intensity=film.blue_layer.grain_intensity * multiplier),
            panchromatic_layer=replace(
                film.panchromatic_layer,
                grain_intensity=film.panchromatic_layer.grain_intensity * multiplier,
            ),
        )

    return replace(
        film,
        panchromatic_layer=replace(
            film.panchromatic_layer,
            grain_intensity=film.panchromatic_layer.grain_intensity * multiplier,
        ),
    )


def _decode_image_source(image_source: Any) -> np.ndarray:
    """
    What:
        將路徑、位元組、檔案物件或陣列轉成 OpenCV 影像。

    Why:
        桌面 UI 與測試環境的輸入型態不同，統一入口後才能共用同一條處理管線。
    """
    if isinstance(image_source, np.ndarray):
        image = image_source.copy()
    elif isinstance(image_source, (str, Path)):
        image = cv2.imread(str(image_source), cv2.IMREAD_COLOR)
    elif isinstance(image_source, (bytes, bytearray, memoryview)):
        file_bytes = np.frombuffer(bytes(image_source), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    elif hasattr(image_source, "read"):
        file_bytes = np.asarray(bytearray(image_source.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    else:
        raise TypeError(f"不支援的圖像輸入類型: {type(image_source)!r}")

    if image is None:
        raise ValueError("無法讀取圖像文件，請確認輸入格式有效")

    if image.ndim == 2:
        return image

    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)

    return image


def _build_output_name(film_type: str, physics_params: Optional[dict]) -> str:
    """
    What:
        生成輸出檔名。

    Why:
        單張與批次模式需要一致且可追蹤的命名規則。
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    physics_mode = None if not physics_params else physics_params.get("physics_mode")
    if isinstance(physics_mode, PhysicsMode):
        mode_suffix = physics_mode.name.lower()
    elif physics_mode:
        mode_suffix = str(physics_mode).lower()
    else:
        mode_suffix = "physical"
    return f"phos_{film_type.lower()}_{mode_suffix}_{timestamp}.jpg"


def _resize_processed_image_to_original(final_image: np.ndarray, original_image: np.ndarray) -> np.ndarray:
    """
    What:
        將處理結果縮放回原始解析度。

    Why:
        膠片模擬內部可以用標準化尺寸計算，但對外輸出必須保持與輸入一致，
        否則預覽、比較與存檔都會出現尺寸不一致的使用者問題。
    """
    original_height, original_width = original_image.shape[:2]
    final_height, final_width = final_image.shape[:2]

    if (final_height, final_width) == (original_height, original_width):
        return final_image

    interpolation = cv2.INTER_AREA
    if original_width > final_width or original_height > final_height:
        interpolation = cv2.INTER_CUBIC

    return cv2.resize(final_image, (original_width, original_height), interpolation=interpolation)


def process_image(
    uploaded_image: Any,
    film_type: str,
    grain_style: str,
    tone_style: str,
    physics_params: Optional[dict] = None,
    use_film_spectra: bool = False,
    film_spectra_name: str = "Portra400",
    film_illuminant: str = "flat",
) -> Tuple[np.ndarray, float, str, np.ndarray]:
    """
    What:
        處理單張圖像並回傳結果、耗時、輸出名稱與原圖。

    Why:
        維持既有對外 API，同時允許桌面版直接傳入檔案路徑或記憶體資料。
    """
    start_time = time.time()
    params = dict(physics_params or {})

    try:
        image = _decode_image_source(uploaded_image)
        original_image = image.copy()

        film_template = get_cached_film_profile(film_type)
        film = deepcopy(film_template)

        if params:
            film.bloom_params.mode = params.get("bloom_mode", film.bloom_params.mode)
            film.bloom_params.threshold = params.get("bloom_threshold", film.bloom_params.threshold)
            film.bloom_params.scattering_ratio = params.get(
                "bloom_scattering_ratio",
                film.bloom_params.scattering_ratio,
            )

            film.hd_curve_params.enabled = params.get("hd_enabled", film.hd_curve_params.enabled)
            if film.hd_curve_params.enabled:
                film.hd_curve_params.gamma = params.get("hd_gamma", film.hd_curve_params.gamma)
                film.hd_curve_params.toe_strength = params.get(
                    "hd_toe_strength",
                    film.hd_curve_params.toe_strength,
                )
                film.hd_curve_params.shoulder_strength = params.get(
                    "hd_shoulder_strength",
                    film.hd_curve_params.shoulder_strength,
                )

            film.grain_params.mode = params.get("grain_mode", film.grain_params.mode)
            film.grain_params.grain_size = params.get("grain_size", film.grain_params.grain_size)
            film.grain_params.intensity = params.get("grain_intensity", film.grain_params.intensity)

            if "reciprocity_enabled" in params:
                film.reciprocity_params.enabled = params.get("reciprocity_enabled", False)

        film = adjust_grain_intensity(film, grain_style)
        standardized = standardize(image)
        response_r, response_g, response_b, response_total = spectral_response(standardized, film)
        final_image = optical_processing(
            response_r,
            response_g,
            response_b,
            response_total,
            film,
            grain_style,
            tone_style,
            use_film_spectra=use_film_spectra,
            film_spectra_name=film_spectra_name,
            film_illuminant=film_illuminant,
            exposure_time=params.get("exposure_time", 1.0),
        )
        final_image = _resize_processed_image_to_original(final_image, original_image)

        process_time = time.time() - start_time
        output_path = _build_output_name(film_type, params)
        return final_image, process_time, output_path, original_image

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"處理圖像時發生錯誤: {exc}") from exc
