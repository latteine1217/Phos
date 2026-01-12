"""
光譜校正視覺化工具

功能：
1. 生成校正前後的對比圖表
2. 可視化光譜響應矩陣
3. 色偏分析圖
4. 灰階響應曲線

依賴：matplotlib
安裝：pip install matplotlib
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # 無GUI環境
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import sys
import os
from typing import Dict, List, Tuple, Optional

# 添加專案根目錄
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from film_models import get_film_profile
from tools.comprehensive_calibration_tool import ComprehensiveCalibrator


class CalibrationVisualizer:
    """校正視覺化器"""
    
    def __init__(self, dpi: int = 150):
        """
        初始化
        
        Args:
            dpi: 圖片解析度
        """
        self.dpi = dpi
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
    
    def plot_matrix_heatmap(self, matrix: np.ndarray, title: str, ax: plt.Axes):
        """
        繪製矩陣熱力圖
        
        Args:
            matrix: 3x3 矩陣
            title: 圖表標題
            ax: matplotlib axes
        """
        im = ax.imshow(matrix, cmap='YlOrRd', vmin=0, vmax=1)
        
        # 設置標籤
        ax.set_xticks([0, 1, 2])
        ax.set_yticks([0, 1, 2])
        ax.set_xticklabels(['R input', 'G input', 'B input'])
        ax.set_yticklabels(['R layer', 'G layer', 'B layer'])
        
        # 顯示數值
        for i in range(3):
            for j in range(3):
                color = 'white' if matrix[i, j] > 0.5 else 'black'
                ax.text(j, i, f'{matrix[i, j]:.3f}', 
                       ha='center', va='center', color=color, fontsize=9)
        
        ax.set_title(title, fontsize=11, fontweight='bold')
        
        # 添加colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Response', rotation=270, labelpad=15)
    
    def plot_row_sums(self, original_matrix: np.ndarray, 
                     calibrated_matrix: np.ndarray, ax: plt.Axes):
        """
        繪製行和比較圖
        
        Args:
            original_matrix: 原始矩陣
            calibrated_matrix: 校正後矩陣
            ax: matplotlib axes
        """
        layers = ['Red', 'Green', 'Blue']
        x = np.arange(len(layers))
        width = 0.35
        
        original_sums = original_matrix.sum(axis=1)
        calibrated_sums = calibrated_matrix.sum(axis=1)
        
        bars1 = ax.bar(x - width/2, original_sums, width, label='Original', alpha=0.8)
        bars2 = ax.bar(x + width/2, calibrated_sums, width, label='Calibrated', alpha=0.8)
        
        # 添加理想值線
        ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1, label='Target (1.0)', alpha=0.7)
        
        ax.set_ylabel('Row Sum (Total Response)')
        ax.set_title('Energy Conservation - Row Sums', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(layers)
        ax.legend(loc='upper right')
        ax.grid(axis='y', alpha=0.3)
        
        # 添加數值標籤
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.3f}', ha='center', va='bottom', fontsize=8)
    
    def plot_grayscale_response(self, original_matrix: np.ndarray,
                               calibrated_matrix: np.ndarray, ax: plt.Axes):
        """
        繪製灰階響應曲線
        
        Args:
            original_matrix: 原始矩陣
            calibrated_matrix: 校正後矩陣
            ax: matplotlib axes
        """
        gray_levels = np.linspace(0, 1, 21)
        
        # 計算響應
        original_r, original_g, original_b = [], [], []
        calibrated_r, calibrated_g, calibrated_b = [], [], []
        
        for level in gray_levels:
            input_vec = np.array([level, level, level])
            
            orig_out = original_matrix @ input_vec
            original_r.append(orig_out[0])
            original_g.append(orig_out[1])
            original_b.append(orig_out[2])
            
            cal_out = calibrated_matrix @ input_vec
            calibrated_r.append(cal_out[0])
            calibrated_g.append(cal_out[1])
            calibrated_b.append(cal_out[2])
        
        # 繪製原始響應
        ax.plot(gray_levels, original_r, 'r--', alpha=0.5, label='Original R')
        ax.plot(gray_levels, original_g, 'g--', alpha=0.5, label='Original G')
        ax.plot(gray_levels, original_b, 'b--', alpha=0.5, label='Original B')
        
        # 繪製校正後響應
        ax.plot(gray_levels, calibrated_r, 'r-', linewidth=2, label='Calibrated R')
        ax.plot(gray_levels, calibrated_g, 'g-', linewidth=2, label='Calibrated G')
        ax.plot(gray_levels, calibrated_b, 'b-', linewidth=2, label='Calibrated B')
        
        # 添加理想線（完美灰階）
        ax.plot(gray_levels, gray_levels, 'k:', linewidth=1, label='Ideal (neutral)')
        
        ax.set_xlabel('Input Gray Level')
        ax.set_ylabel('Output Response')
        ax.set_title('Grayscale Response Curve', fontweight='bold')
        ax.legend(loc='upper left', fontsize=8, ncol=2)
        ax.grid(alpha=0.3)
    
    def plot_color_deviation(self, original_matrix: np.ndarray,
                            calibrated_matrix: np.ndarray, ax: plt.Axes):
        """
        繪製色偏分析圖
        
        Args:
            original_matrix: 原始矩陣
            calibrated_matrix: 校正後矩陣
            ax: matplotlib axes
        """
        gray_levels = np.linspace(0, 1, 21)
        
        original_deviations = []
        calibrated_deviations = []
        
        for level in gray_levels:
            input_vec = np.array([level, level, level])
            
            orig_out = original_matrix @ input_vec
            orig_dev = orig_out.max() - orig_out.min()
            original_deviations.append(orig_dev)
            
            cal_out = calibrated_matrix @ input_vec
            cal_dev = cal_out.max() - cal_out.min()
            calibrated_deviations.append(cal_dev)
        
        ax.plot(gray_levels, original_deviations, 'o-', label='Original', alpha=0.7)
        ax.plot(gray_levels, calibrated_deviations, 's-', label='Calibrated', alpha=0.7)
        
        ax.set_xlabel('Input Gray Level')
        ax.set_ylabel('Color Deviation (max - min)')
        ax.set_title('Color Cast Analysis', fontweight='bold')
        ax.legend()
        ax.grid(alpha=0.3)
        
        # 添加零線
        ax.axhline(y=0, color='green', linestyle='--', linewidth=1, alpha=0.5)
    
    def plot_diagonal_vs_offdiagonal(self, original_matrix: np.ndarray,
                                    calibrated_matrix: np.ndarray, ax: plt.Axes):
        """
        繪製對角線 vs 非對角線比較
        
        Args:
            original_matrix: 原始矩陣
            calibrated_matrix: 校正後矩陣
            ax: matplotlib axes
        """
        layers = ['Red', 'Green', 'Blue']
        x = np.arange(len(layers))
        width = 0.2
        
        # 計算對角線和非對角線值
        original_diag = original_matrix.diagonal()
        original_offdiag = [(original_matrix[i].sum() - original_matrix[i, i])/2 for i in range(3)]
        
        calibrated_diag = calibrated_matrix.diagonal()
        calibrated_offdiag = [(calibrated_matrix[i].sum() - calibrated_matrix[i, i])/2 for i in range(3)]
        
        # 繪製條形圖
        ax.bar(x - 1.5*width, original_diag, width, label='Original Diagonal', alpha=0.8)
        ax.bar(x - 0.5*width, original_offdiag, width, label='Original Off-diag (avg)', alpha=0.8)
        ax.bar(x + 0.5*width, calibrated_diag, width, label='Calibrated Diagonal', alpha=0.8)
        ax.bar(x + 1.5*width, calibrated_offdiag, width, label='Calibrated Off-diag (avg)', alpha=0.8)
        
        ax.set_ylabel('Response Coefficient')
        ax.set_title('Diagonal Dominance', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(layers)
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3)
    
    def visualize_calibration(self, film_name: str, strategy_id: int = 3,
                             output_path: Optional[str] = None):
        """
        生成完整的校正視覺化報告
        
        Args:
            film_name: 膠片名稱
            strategy_id: 校正策略ID
            output_path: 輸出路徑（None = 自動生成）
        """
        # 執行校正
        calibrator = ComprehensiveCalibrator(verbose=False)
        result = calibrator.calibrate_film(film_name, strategy_id)
        
        if result.get("is_bw"):
            print(f"⚠ {film_name} 是黑白膠片，無法生成光譜校正視覺化")
            return
        
        original_matrix = result['original_matrix']
        calibrated_matrix = result['calibrated_matrix']
        
        # 創建圖表
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # 主標題
        strategy_name = calibrator.calibrate_film.__globals__['STRATEGIES'][strategy_id].name
        fig.suptitle(f'Spectral Calibration Report: {film_name}\nStrategy: {strategy_name}',
                    fontsize=16, fontweight='bold')
        
        # 1. 原始矩陣熱力圖
        ax1 = fig.add_subplot(gs[0, 0])
        self.plot_matrix_heatmap(original_matrix, 'Original Matrix', ax1)
        
        # 2. 校正後矩陣熱力圖
        ax2 = fig.add_subplot(gs[0, 1])
        self.plot_matrix_heatmap(calibrated_matrix, 'Calibrated Matrix', ax2)
        
        # 3. 差異矩陣
        ax3 = fig.add_subplot(gs[0, 2])
        diff_matrix = calibrated_matrix - original_matrix
        self.plot_matrix_heatmap(diff_matrix, 'Difference (Calibrated - Original)', ax3)
        
        # 4. 行和比較
        ax4 = fig.add_subplot(gs[1, 0])
        self.plot_row_sums(original_matrix, calibrated_matrix, ax4)
        
        # 5. 灰階響應曲線
        ax5 = fig.add_subplot(gs[1, 1])
        self.plot_grayscale_response(original_matrix, calibrated_matrix, ax5)
        
        # 6. 色偏分析
        ax6 = fig.add_subplot(gs[1, 2])
        self.plot_color_deviation(original_matrix, calibrated_matrix, ax6)
        
        # 7. 對角線主導性
        ax7 = fig.add_subplot(gs[2, 0])
        self.plot_diagonal_vs_offdiagonal(original_matrix, calibrated_matrix, ax7)
        
        # 8. 數值摘要表
        ax8 = fig.add_subplot(gs[2, 1:])
        ax8.axis('off')
        
        # 構建摘要表格
        orig_eval = result['original_eval']
        cal_eval = result['calibrated_eval']
        
        summary_text = f"""
        Performance Metrics:
        
        ┌────────────────────────┬─────────────┬─────────────┬──────────┐
        │ Metric                 │ Original    │ Calibrated  │ Improve  │
        ├────────────────────────┼─────────────┼─────────────┼──────────┤
        │ Gray Deviation         │ {orig_eval['gray_deviation']:11.6f} │ {cal_eval['gray_deviation']:11.6f} │ {result['improvement']['gray_deviation']*100:7.1f}% │
        │ Row Imbalance          │ {orig_eval['row_imbalance']:11.6f} │ {cal_eval['row_imbalance']:11.6f} │ {result['improvement']['row_imbalance']*100:7.1f}% │
        │ Diagonal Dominance     │ {orig_eval['diagonal_dominance']:11.2f} │ {cal_eval['diagonal_dominance']:11.2f} │ {((cal_eval['diagonal_dominance']/orig_eval['diagonal_dominance'])-1)*100:7.1f}% │
        └────────────────────────┴─────────────┴─────────────┴──────────┘
        
        White Output (R, G, B):
        Original:   ({orig_eval['white_output'][0]:.4f}, {orig_eval['white_output'][1]:.4f}, {orig_eval['white_output'][2]:.4f})
        Calibrated: ({cal_eval['white_output'][0]:.4f}, {cal_eval['white_output'][1]:.4f}, {cal_eval['white_output'][2]:.4f})
        Ideal:      (1.0000, 1.0000, 1.0000)
        
        Status: {"✓ PASS - Excellent color neutrality" if cal_eval['gray_deviation'] < 0.002 else "⚠ CHECK - Some color cast remains"}
        """
        
        ax8.text(0.1, 0.5, summary_text, fontfamily='monospace', fontsize=10,
                verticalalignment='center')
        
        # 保存圖表
        if output_path is None:
            output_path = f"calibration_report_{film_name}_strategy{strategy_id}.png"
        
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 視覺化報告已生成: {output_path}")
        return output_path
    
    def visualize_all_films(self, strategy_id: int = 3, output_dir: str = "calibration_reports"):
        """
        為所有彩色膠片生成視覺化報告
        
        Args:
            strategy_id: 校正策略ID
            output_dir: 輸出目錄
        """
        os.makedirs(output_dir, exist_ok=True)
        
        color_films = [
            "Portra400", "Ektar100", "Velvia50", "NC200",
            "Cinestill800T", "Gold200", "ProImage100", "Superia400"
        ]
        
        print(f"\n生成視覺化報告...")
        print(f"輸出目錄: {output_dir}\n")
        
        for film_name in color_films:
            output_path = os.path.join(output_dir, f"{film_name}_calibration_report.png")
            try:
                self.visualize_calibration(film_name, strategy_id, output_path)
            except Exception as e:
                print(f"✗ {film_name} 生成失敗: {e}")
        
        print(f"\n✓ 所有報告生成完畢！")
        print(f"  目錄: {output_dir}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="光譜校正視覺化工具")
    parser.add_argument("--film", type=str, help="指定膠片名稱")
    parser.add_argument("--all", action="store_true", help="生成所有膠片的報告")
    parser.add_argument("--strategy", type=int, default=3, choices=[1,2,3,4,5],
                       help="校正策略 (1-5, 預設=3)")
    parser.add_argument("--output", type=str, help="輸出檔案路徑")
    parser.add_argument("--output-dir", type=str, default="calibration_reports",
                       help="輸出目錄（用於 --all）")
    parser.add_argument("--dpi", type=int, default=150, help="圖片解析度")
    
    args = parser.parse_args()
    
    visualizer = CalibrationVisualizer(dpi=args.dpi)
    
    if args.all:
        visualizer.visualize_all_films(args.strategy, args.output_dir)
    elif args.film:
        visualizer.visualize_calibration(args.film, args.strategy, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
