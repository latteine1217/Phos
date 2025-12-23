"""
視覺化膠片光譜敏感度曲線

生成所有膠片的光譜敏感度曲線圖，用於驗證和文檔。

Usage:
    python3 scripts/visualize_film_sensitivity.py

Output:
    docs/film_sensitivity_curves.png
    
Version: 0.4.0
Date: 2025-12-22
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # 無 GUI 後端
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# 添加父目錄到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phos_core import load_film_sensitivity


def visualize_all_films():
    """視覺化所有膠片的光譜敏感度曲線"""
    
    films = ['Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400']
    film_names = {
        'Portra400': 'Kodak Portra 400 (Color Negative)',
        'Velvia50': 'Fuji Velvia 50 (Color Reversal)',
        'Cinestill800T': 'CineStill 800T (Tungsten Balanced)',
        'HP5Plus400': 'Ilford HP5 Plus 400 (B&W Panchromatic)'
    }
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    for i, film in enumerate(films):
        curves = load_film_sensitivity(film)
        wavelengths = curves['wavelengths']
        
        ax = axes[i]
        
        # 繪製 R/G/B 曲線
        ax.plot(wavelengths, curves['red'], 'r-', label='Red Layer', linewidth=2.5, alpha=0.8)
        ax.plot(wavelengths, curves['green'], 'g-', label='Green Layer', linewidth=2.5, alpha=0.8)
        ax.plot(wavelengths, curves['blue'], 'b-', label='Blue Layer', linewidth=2.5, alpha=0.8)
        
        # 標註峰值
        for name, curve, color in [('Red', curves['red'], 'red'), 
                                     ('Green', curves['green'], 'green'), 
                                     ('Blue', curves['blue'], 'blue')]:
            peak_idx = np.argmax(curve)
            peak_wl = wavelengths[peak_idx]
            peak_val = curve[peak_idx]
            ax.plot(peak_wl, peak_val, 'o', color=color, markersize=8, alpha=0.6)
            ax.text(peak_wl, peak_val + 0.05, f'{peak_wl:.0f}nm', 
                   ha='center', va='bottom', fontsize=9, color=color, weight='bold')
        
        # 設定樣式
        ax.set_xlabel('Wavelength (nm)', fontsize=12, weight='bold')
        ax.set_ylabel('Spectral Sensitivity', fontsize=12, weight='bold')
        ax.set_title(f'{film_names[film]}', fontsize=13, weight='bold', pad=10)
        ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(380, 770)
        ax.set_ylim(-0.05, 1.15)
        
        # 添加波段標記
        ax.axvspan(380, 450, alpha=0.1, color='blue', label='Blue Region')
        ax.axvspan(500, 570, alpha=0.1, color='green')
        ax.axvspan(620, 770, alpha=0.1, color='red')
        
        # 膠片類型標記
        film_type = curves['type'].replace('_', ' ').title()
        ax.text(0.02, 0.98, f'Type: {film_type}', 
               transform=ax.transAxes, fontsize=9, 
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle('Film Spectral Sensitivity Curves (Phase 4 Milestone 3)', 
                fontsize=16, weight='bold', y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    # 保存
    output_path = Path(__file__).parent.parent / 'docs' / 'film_sensitivity_curves.png'
    output_path.parent.mkdir(exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Saved to: {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
    
    plt.close()


def generate_comparison_plot():
    """生成膠片比較圖（同一光譜不同響應）"""
    
    from phos_core import rgb_to_spectrum, apply_film_spectral_sensitivity
    
    # 測試色彩：暖色、冷色、中性色
    test_colors = {
        'Warm (Sunset)': np.array([0.9, 0.6, 0.3]),
        'Cool (Sky)': np.array([0.3, 0.6, 0.9]),
        'Neutral (Gray)': np.array([0.5, 0.5, 0.5])
    }
    
    films = ['Portra400', 'Velvia50', 'Cinestill800T']
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    for i, (color_name, rgb_in) in enumerate(test_colors.items()):
        ax = axes[i]
        
        # 生成光譜
        spectrum = rgb_to_spectrum(rgb_in)
        
        # 各膠片響應
        film_responses = {}
        for film in films:
            curves = load_film_sensitivity(film)
            film_rgb = apply_film_spectral_sensitivity(spectrum, curves)
            film_responses[film] = film_rgb
        
        # 繪製色塊
        x = np.arange(len(films) + 1)
        width = 0.8
        
        # 原始色彩
        ax.bar(0, 1, width, color=rgb_in, edgecolor='black', linewidth=2, label='Original')
        ax.text(0, -0.1, 'Original\nRGB', ha='center', va='top', fontsize=10, weight='bold')
        
        # 各膠片響應
        for j, film in enumerate(films):
            film_rgb = film_responses[film]
            ax.bar(j + 1, 1, width, color=film_rgb, edgecolor='black', linewidth=2)
            ax.text(j + 1, -0.1, film.replace('400', '\n400').replace('50', '\n50').replace('800T', '\n800T'), 
                   ha='center', va='top', fontsize=9)
            
            # 顯示 RGB 值
            ax.text(j + 1, 1.05, f'R:{film_rgb[0]:.2f}\nG:{film_rgb[1]:.2f}\nB:{film_rgb[2]:.2f}', 
                   ha='center', va='bottom', fontsize=7, family='monospace')
        
        ax.set_title(f'{color_name}\nOriginal RGB: ({rgb_in[0]:.2f}, {rgb_in[1]:.2f}, {rgb_in[2]:.2f})', 
                    fontsize=12, weight='bold')
        ax.set_ylim(-0.15, 1.4)
        ax.set_xlim(-0.5, len(films) + 0.5)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
    
    plt.suptitle('Film Color Response Comparison', fontsize=14, weight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    
    output_path = Path(__file__).parent.parent / 'docs' / 'film_color_comparison.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Saved to: {output_path}")
    plt.close()


if __name__ == '__main__':
    print("="*70)
    print("視覺化膠片光譜敏感度曲線")
    print("="*70)
    
    print("\n1. 生成光譜敏感度曲線...")
    visualize_all_films()
    
    print("\n2. 生成色彩響應比較圖...")
    generate_comparison_plot()
    
    print("\n" + "="*70)
    print("✅ 所有圖表生成完成")
    print("="*70)
