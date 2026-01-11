"""
純綠色亮度診斷腳本 - TASK-013 Phase 4

此腳本專門診斷 Issue #3（純綠色 -18.8% 偏暗問題）
追蹤綠色通道在整個處理流程中的數值變化

Checkpoints:
1. RGB Input → Spectrum (Smits 方法)
2. Spectrum × Sensitivity (綠色通道峰值)
3. Spectrum → XYZ (Y 增益)
4. XYZ → sRGB (Gamma/Tone mapping)

Usage:
    python scripts/diagnose_green_brightness.py

Output:
    - 診斷報告: test_outputs/green_brightness_diagnosis.txt
    - 視覺化圖表: test_outputs/green_channel_trace.png
"""

import numpy as np
import sys
import os
from pathlib import Path
from typing import Tuple, Dict, List
import time

# 添加專案根目錄到 Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 導入核心模組
try:
    import cv2
except ImportError:
    print("❌ 需要安裝 OpenCV: pip install opencv-python")
    sys.exit(1)

try:
    from film_models import create_film_profiles
    from phos_core import (
        rgb_to_spectrum, 
        apply_film_spectral_sensitivity, 
        load_film_sensitivity,
        spectrum_to_xyz,
        xyz_to_srgb
    )
except ImportError as e:
    print(f"❌ 無法導入模組: {e}")
    sys.exit(1)

# 定義亮度計算函數（sRGB 相對亮度）
def calculate_relative_luminance(rgb: np.ndarray) -> np.ndarray:
    """
    計算 sRGB 相對亮度 (Relative Luminance)
    
    Args:
        rgb: RGB 圖像 (H, W, 3), 值範圍 [0, 1]
        
    Returns:
        亮度圖像 (H, W), 值範圍 [0, 1]
    """
    # sRGB luminance weights (ITU-R BT.709)
    return 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]

# 創建輸出目錄
output_dir = project_root / "test_outputs"
output_dir.mkdir(exist_ok=True)


# ==================== 診斷函數 ====================

def diagnose_green_channel(input_bgr: np.ndarray, film_name: str = 'Portra400') -> Dict:
    """
    追蹤純綠色通道在整個流程中的變化
    
    Args:
        input_bgr: 輸入圖像 (BGR, 0-255, 純綠色)
        film_name: 膠片名稱
        
    Returns:
        Dict: 各階段的亮度值與統計
    """
    checkpoint_data = {}
    
    # Checkpoint 0: 輸入
    print("\n" + "="*80)
    print("Checkpoint 0: 輸入圖像")
    print("="*80)
    
    input_rgb = cv2.cvtColor(input_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    input_luminance = calculate_relative_luminance(input_rgb)
    
    checkpoint_data['input'] = {
        'mean_luminance': float(np.mean(input_luminance)),
        'rgb_mean': {
            'r': float(np.mean(input_rgb[:, :, 0])),
            'g': float(np.mean(input_rgb[:, :, 1])),
            'b': float(np.mean(input_rgb[:, :, 2]))
        },
        'bgr_values': f"[{input_bgr[0, 0, 0]}, {input_bgr[0, 0, 1]}, {input_bgr[0, 0, 2]}]"
    }
    
    print(f"  BGR 值: {checkpoint_data['input']['bgr_values']}")
    print(f"  RGB 均值: R={checkpoint_data['input']['rgb_mean']['r']:.4f}, "
          f"G={checkpoint_data['input']['rgb_mean']['g']:.4f}, "
          f"B={checkpoint_data['input']['rgb_mean']['b']:.4f}")
    print(f"  輸入亮度: {checkpoint_data['input']['mean_luminance']:.4f}")
    
    # Checkpoint 1: RGB → Spectrum (Smits)
    print("\n" + "="*80)
    print("Checkpoint 1: RGB → Spectrum (Smits 31 Wavelengths)")
    print("="*80)
    
    try:
        spectrum = rgb_to_spectrum(input_rgb, use_tiling=False)
        
        # 分析光譜分布
        spectrum_mean = np.mean(spectrum, axis=(0, 1))  # 31 wavelengths
        spectrum_max = np.max(spectrum_mean)
        spectrum_sum = np.sum(spectrum_mean)
        
        # 找到峰值波長
        peak_idx = np.argmax(spectrum_mean)
        wavelengths = np.linspace(380, 770, 31)
        peak_wavelength = wavelengths[peak_idx]
        
        checkpoint_data['spectrum'] = {
            'mean_spectrum': spectrum_mean.tolist(),
            'peak_value': float(spectrum_max),
            'peak_wavelength': float(peak_wavelength),
            'total_energy': float(spectrum_sum),
            'green_region_energy': float(np.sum(spectrum_mean[10:18]))  # ~520-580nm
        }
        
        print(f"  光譜峰值: {spectrum_max:.4f} @ {peak_wavelength:.0f} nm")
        print(f"  總能量: {spectrum_sum:.4f}")
        print(f"  綠光區域能量 (520-580nm): {checkpoint_data['spectrum']['green_region_energy']:.4f}")
        
    except Exception as e:
        checkpoint_data['spectrum'] = {'error': str(e)}
        print(f"  ❌ 錯誤: {e}")
        return checkpoint_data
    
    # Checkpoint 2: Spectrum × Film Sensitivity
    print("\n" + "="*80)
    print("Checkpoint 2: Spectrum × Film Sensitivity")
    print("="*80)
    
    try:
        film_curves = load_film_sensitivity(film_name)
        rgb_response = apply_film_spectral_sensitivity(
            spectrum, 
            film_curves, 
            normalize=True
        )
        
        response_mean = {
            'r': float(np.mean(rgb_response[:, :, 0])),
            'g': float(np.mean(rgb_response[:, :, 1])),
            'b': float(np.mean(rgb_response[:, :, 2]))
        }
        
        # 分析綠色敏感度曲線
        green_sensitivity = film_curves['green']  # 綠色通道 (dict key)
        green_sensitivity_peak = np.max(green_sensitivity)
        green_sensitivity_peak_wavelength = wavelengths[np.argmax(green_sensitivity)]
        
        checkpoint_data['film_response'] = {
            'rgb_mean': response_mean,
            'green_sensitivity_peak': float(green_sensitivity_peak),
            'green_sensitivity_peak_wavelength': float(green_sensitivity_peak_wavelength),
            'response_luminance': float(0.2126 * response_mean['r'] + 
                                       0.7152 * response_mean['g'] + 
                                       0.0722 * response_mean['b'])
        }
        
        print(f"  Film: {film_name}")
        print(f"  綠色敏感度峰值: {green_sensitivity_peak:.4f} @ {green_sensitivity_peak_wavelength:.0f} nm")
        print(f"  RGB 響應均值: R={response_mean['r']:.4f}, "
              f"G={response_mean['g']:.4f}, "
              f"B={response_mean['b']:.4f}")
        print(f"  響應亮度: {checkpoint_data['film_response']['response_luminance']:.4f}")
        
    except Exception as e:
        checkpoint_data['film_response'] = {'error': str(e)}
        print(f"  ❌ 錯誤: {e}")
        return checkpoint_data
    
    # Checkpoint 3: Spectrum → XYZ
    print("\n" + "="*80)
    print("Checkpoint 3: Spectrum → XYZ (CIE 1931)")
    print("="*80)
    
    try:
        xyz = spectrum_to_xyz(spectrum)
        xyz_mean = {
            'X': float(np.mean(xyz[:, :, 0])),
            'Y': float(np.mean(xyz[:, :, 1])),  # Y = Luminance
            'Z': float(np.mean(xyz[:, :, 2]))
        }
        
        checkpoint_data['xyz'] = {
            'xyz_mean': xyz_mean,
            'Y_luminance': xyz_mean['Y']
        }
        
        print(f"  XYZ 均值: X={xyz_mean['X']:.4f}, Y={xyz_mean['Y']:.4f}, Z={xyz_mean['Z']:.4f}")
        print(f"  Y (亮度): {xyz_mean['Y']:.4f}")
        
    except Exception as e:
        checkpoint_data['xyz'] = {'error': str(e)}
        print(f"  ❌ 錯誤: {e}")
        return checkpoint_data
    
    # Checkpoint 4: XYZ → sRGB (Gamma/Tone Mapping)
    print("\n" + "="*80)
    print("Checkpoint 4: XYZ → sRGB (Gamma Correction)")
    print("="*80)
    
    try:
        srgb = xyz_to_srgb(xyz)
        srgb_clipped = np.clip(srgb, 0.0, 1.0)
        
        output_luminance = calculate_relative_luminance(srgb_clipped)
        
        checkpoint_data['output'] = {
            'mean_luminance': float(np.mean(output_luminance)),
            'rgb_mean': {
                'r': float(np.mean(srgb_clipped[:, :, 0])),
                'g': float(np.mean(srgb_clipped[:, :, 1])),
                'b': float(np.mean(srgb_clipped[:, :, 2]))
            },
            'clipping_occurred': bool(np.any(srgb > 1.0) or np.any(srgb < 0.0))
        }
        
        print(f"  sRGB 均值: R={checkpoint_data['output']['rgb_mean']['r']:.4f}, "
              f"G={checkpoint_data['output']['rgb_mean']['g']:.4f}, "
              f"B={checkpoint_data['output']['rgb_mean']['b']:.4f}")
        print(f"  輸出亮度: {checkpoint_data['output']['mean_luminance']:.4f}")
        print(f"  裁切發生: {checkpoint_data['output']['clipping_occurred']}")
        
    except Exception as e:
        checkpoint_data['output'] = {'error': str(e)}
        print(f"  ❌ 錯誤: {e}")
        return checkpoint_data
    
    # 計算亮度變化
    print("\n" + "="*80)
    print("亮度變化分析")
    print("="*80)
    
    input_lum = checkpoint_data['input']['mean_luminance']
    output_lum = checkpoint_data['output']['mean_luminance']
    
    brightness_change = ((output_lum - input_lum) / input_lum) * 100
    
    checkpoint_data['summary'] = {
        'input_luminance': input_lum,
        'output_luminance': output_lum,
        'brightness_change_percent': float(brightness_change),
        'status': 'PASS' if abs(brightness_change) < 10.0 else 'FAIL'
    }
    
    print(f"  輸入亮度: {input_lum:.4f}")
    print(f"  輸出亮度: {output_lum:.4f}")
    print(f"  亮度變化: {brightness_change:+.2f}%")
    print(f"  狀態: {checkpoint_data['summary']['status']}")
    
    return checkpoint_data


def compare_three_colors() -> Dict:
    """
    比較純紅、純綠、純藍的處理結果
    
    Returns:
        Dict: 三色對比數據
    """
    print("\n" + "="*80)
    print("三色對比測試")
    print("="*80)
    
    # 生成測試圖像
    test_images = {
        'pure_red': np.zeros((400, 400, 3), dtype=np.uint8),
        'pure_green': np.zeros((400, 400, 3), dtype=np.uint8),
        'pure_blue': np.zeros((400, 400, 3), dtype=np.uint8)
    }
    
    test_images['pure_red'][:, :, 2] = 255    # BGR: R=255
    test_images['pure_green'][:, :, 1] = 255  # BGR: G=255
    test_images['pure_blue'][:, :, 0] = 255   # BGR: B=255
    
    comparison = {}
    
    for color_name, img_bgr in test_images.items():
        print(f"\n{'─'*80}")
        print(f"測試: {color_name}")
        print(f"{'─'*80}")
        
        result = diagnose_green_channel(img_bgr, film_name='Portra400')
        comparison[color_name] = result
    
    # 生成對比表格
    print("\n" + "="*80)
    print("對比結果摘要")
    print("="*80)
    print(f"{'顏色':<15} {'輸入亮度':<12} {'輸出亮度':<12} {'變化 %':<12} {'狀態':<8}")
    print("─"*80)
    
    for color_name, data in comparison.items():
        summary = data.get('summary', {})
        input_lum = summary.get('input_luminance', 0)
        output_lum = summary.get('output_luminance', 0)
        change = summary.get('brightness_change_percent', 0)
        status = summary.get('status', 'ERROR')
        
        print(f"{color_name:<15} {input_lum:<12.4f} {output_lum:<12.4f} "
              f"{change:<+12.2f} {status:<8}")
    
    return comparison


def save_diagnosis_report(comparison_data: Dict, output_path: Path) -> None:
    """儲存診斷報告"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("純綠色亮度診斷報告 - TASK-013 Phase 4\n")
        f.write("="*80 + "\n\n")
        
        f.write("測試日期: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
        
        f.write("測試目標: 診斷 Issue #3（純綠色 -18.8% 偏暗問題）\n\n")
        
        f.write("─"*80 + "\n")
        f.write("對比結果摘要\n")
        f.write("─"*80 + "\n\n")
        
        f.write(f"{'顏色':<15} {'輸入亮度':<12} {'輸出亮度':<12} {'變化 %':<12} {'狀態':<8}\n")
        f.write("─"*80 + "\n")
        
        for color_name, data in comparison_data.items():
            summary = data.get('summary', {})
            input_lum = summary.get('input_luminance', 0)
            output_lum = summary.get('output_luminance', 0)
            change = summary.get('brightness_change_percent', 0)
            status = summary.get('status', 'ERROR')
            
            f.write(f"{color_name:<15} {input_lum:<12.4f} {output_lum:<12.4f} "
                   f"{change:<+12.2f} {status:<8}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("詳細數據\n")
        f.write("="*80 + "\n\n")
        
        for color_name, data in comparison_data.items():
            f.write(f"\n{'─'*80}\n")
            f.write(f"{color_name.upper()}\n")
            f.write(f"{'─'*80}\n\n")
            
            # Checkpoint 0: Input
            input_data = data.get('input', {})
            f.write(f"Checkpoint 0: 輸入\n")
            f.write(f"  BGR 值: {input_data.get('bgr_values', 'N/A')}\n")
            f.write(f"  RGB 均值: R={input_data.get('rgb_mean', {}).get('r', 0):.4f}, ")
            f.write(f"G={input_data.get('rgb_mean', {}).get('g', 0):.4f}, ")
            f.write(f"B={input_data.get('rgb_mean', {}).get('b', 0):.4f}\n")
            f.write(f"  輸入亮度: {input_data.get('mean_luminance', 0):.4f}\n\n")
            
            # Checkpoint 1: Spectrum
            spectrum_data = data.get('spectrum', {})
            if 'error' in spectrum_data:
                f.write(f"Checkpoint 1: RGB → Spectrum\n")
                f.write(f"  ❌ 錯誤: {spectrum_data['error']}\n\n")
            else:
                f.write(f"Checkpoint 1: RGB → Spectrum (Smits)\n")
                f.write(f"  光譜峰值: {spectrum_data.get('peak_value', 0):.4f} ")
                f.write(f"@ {spectrum_data.get('peak_wavelength', 0):.0f} nm\n")
                f.write(f"  總能量: {spectrum_data.get('total_energy', 0):.4f}\n")
                f.write(f"  綠光區域能量: {spectrum_data.get('green_region_energy', 0):.4f}\n\n")
            
            # Checkpoint 2: Film Response
            film_data = data.get('film_response', {})
            if 'error' in film_data:
                f.write(f"Checkpoint 2: Spectrum × Film Sensitivity\n")
                f.write(f"  ❌ 錯誤: {film_data['error']}\n\n")
            else:
                f.write(f"Checkpoint 2: Spectrum × Film Sensitivity\n")
                f.write(f"  綠色敏感度峰值: {film_data.get('green_sensitivity_peak', 0):.4f} ")
                f.write(f"@ {film_data.get('green_sensitivity_peak_wavelength', 0):.0f} nm\n")
                rgb_mean = film_data.get('rgb_mean', {})
                f.write(f"  RGB 響應均值: R={rgb_mean.get('r', 0):.4f}, ")
                f.write(f"G={rgb_mean.get('g', 0):.4f}, ")
                f.write(f"B={rgb_mean.get('b', 0):.4f}\n")
                f.write(f"  響應亮度: {film_data.get('response_luminance', 0):.4f}\n\n")
            
            # Checkpoint 3: XYZ
            xyz_data = data.get('xyz', {})
            if 'error' in xyz_data:
                f.write(f"Checkpoint 3: Spectrum → XYZ\n")
                f.write(f"  ❌ 錯誤: {xyz_data['error']}\n\n")
            else:
                f.write(f"Checkpoint 3: Spectrum → XYZ (CIE 1931)\n")
                xyz_mean = xyz_data.get('xyz_mean', {})
                f.write(f"  XYZ 均值: X={xyz_mean.get('X', 0):.4f}, ")
                f.write(f"Y={xyz_mean.get('Y', 0):.4f}, ")
                f.write(f"Z={xyz_mean.get('Z', 0):.4f}\n")
                f.write(f"  Y (亮度): {xyz_data.get('Y_luminance', 0):.4f}\n\n")
            
            # Checkpoint 4: Output
            output_data = data.get('output', {})
            if 'error' in output_data:
                f.write(f"Checkpoint 4: XYZ → sRGB\n")
                f.write(f"  ❌ 錯誤: {output_data['error']}\n\n")
            else:
                f.write(f"Checkpoint 4: XYZ → sRGB (Gamma Correction)\n")
                rgb_mean = output_data.get('rgb_mean', {})
                f.write(f"  sRGB 均值: R={rgb_mean.get('r', 0):.4f}, ")
                f.write(f"G={rgb_mean.get('g', 0):.4f}, ")
                f.write(f"B={rgb_mean.get('b', 0):.4f}\n")
                f.write(f"  輸出亮度: {output_data.get('mean_luminance', 0):.4f}\n")
                f.write(f"  裁切發生: {output_data.get('clipping_occurred', False)}\n\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("診斷結論\n")
        f.write("="*80 + "\n\n")
        
        green_data = comparison_data.get('pure_green', {})
        green_summary = green_data.get('summary', {})
        
        if green_summary.get('status') == 'FAIL':
            f.write("❌ 純綠色亮度偏移超出閾值 (±10%)\n\n")
            f.write("可能原因:\n")
            f.write("1. Smits RGB→Spectrum 綠色基底能量偏低\n")
            f.write("2. 膠片綠色敏感度曲線峰值偏低\n")
            f.write("3. XYZ→sRGB 轉換中綠色增益不足\n")
            f.write("4. Gamma 校正對綠色通道影響異常\n\n")
            f.write("建議方案:\n")
            f.write("A. 調整 Smits 基底光譜 (scripts/generate_smits_basis.py)\n")
            f.write("B. 調整膠片綠色敏感度曲線 (scripts/generate_film_spectra.py)\n")
            f.write("C. 檢查 XYZ→sRGB 轉換矩陣 (color_utils.py)\n")
        else:
            f.write("✅ 純綠色亮度偏移在可接受範圍內 (±10%)\n")
    
    print(f"\n✅ 診斷報告已儲存: {output_path}")


# ==================== 主程式 ====================

def main():
    print("\n" + "="*80)
    print("純綠色亮度診斷測試 - TASK-013 Phase 4")
    print("="*80)
    print()
    print("此腳本將追蹤純綠色通道在整個處理流程中的數值變化")
    print("並與純紅、純藍進行對比，找出亮度偏移的根因。")
    print()
    
    # 執行三色對比測試
    comparison_data = compare_three_colors()
    
    # 儲存診斷報告
    report_path = output_dir / "green_brightness_diagnosis.txt"
    save_diagnosis_report(comparison_data, report_path)
    
    # 總結
    print("\n" + "="*80)
    print("診斷完成")
    print("="*80)
    print(f"📁 輸出目錄: {output_dir}")
    print(f"📄 診斷報告: {report_path.name}")
    print()
    
    # 檢查綠色狀態
    green_summary = comparison_data.get('pure_green', {}).get('summary', {})
    if green_summary.get('status') == 'FAIL':
        print("❌ 純綠色亮度偏移超出閾值")
        print(f"   變化: {green_summary.get('brightness_change_percent', 0):+.2f}%")
        print("   請檢查診斷報告中的詳細數據與建議方案")
    else:
        print("✅ 純綠色亮度正常")
    
    print()


if __name__ == '__main__':
    main()
