#!/usr/bin/env python3
"""
一鍵運行所有校正驗證測試

功能：
1. 物理理論驗證（所有13款膠片）
2. 光譜響應校正（8款彩色膠片）
3. 生成完整報告
4. 可選：生成視覺化圖表

使用方式：
    python tools/run_all_calibration_tests.py
    python tools/run_all_calibration_tests.py --visualize
    python tools/run_all_calibration_tests.py --strategy 3 --export
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List

# 添加專案根目錄
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.physics_validator import validate_all_films, validate_film
from tools.comprehensive_calibration_tool import ComprehensiveCalibrator
try:
    from tools.calibration_visualizer import CalibrationVisualizer
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠ matplotlib 未安裝，視覺化功能不可用")
    print("  安裝方式: pip install matplotlib")


class CombinedTestSuite:
    """綜合測試套件"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "physics_validation": {},
            "calibration": {},
            "summary": {}
        }
    
    def run_physics_validation(self) -> Dict:
        """運行物理理論驗證"""
        if self.verbose:
            print("\n" + "="*80)
            print(" " * 25 + "階段 1: 物理理論驗證")
            print("="*80)
        
        results = validate_all_films(verbose=self.verbose)
        self.test_results["physics_validation"] = results
        
        return results
    
    def run_calibration_test(self, strategy_id: int = 3) -> Dict:
        """運行光譜校正測試"""
        if self.verbose:
            print("\n" + "="*80)
            print(" " * 25 + "階段 2: 光譜響應校正")
            print("="*80)
        
        calibrator = ComprehensiveCalibrator(verbose=self.verbose)
        results = calibrator.calibrate_all_films(strategy_id)
        
        self.test_results["calibration"] = {
            "strategy_id": strategy_id,
            "results": results
        }
        
        return results
    
    def generate_visualizations(self, strategy_id: int = 3, 
                               output_dir: str = "calibration_reports"):
        """生成視覺化報告"""
        if not HAS_MATPLOTLIB:
            print("\n⚠ 跳過視覺化生成（matplotlib 未安裝）")
            return
        
        if self.verbose:
            print("\n" + "="*80)
            print(" " * 25 + "階段 3: 生成視覺化報告")
            print("="*80)
        
        visualizer = CalibrationVisualizer()
        visualizer.visualize_all_films(strategy_id, output_dir)
    
    def generate_final_report(self) -> str:
        """生成最終報告"""
        if self.verbose:
            print("\n" + "="*80)
            print(" " * 25 + "最終報告")
            print("="*80 + "\n")
        
        # 統計物理驗證結果
        physics_results = self.test_results["physics_validation"]
        total_films = len(physics_results)
        physics_passed = sum(1 for r in physics_results.values() if r["all_passed"])
        
        # 統計校正結果
        calibration_results = self.test_results["calibration"]["results"]
        color_films = [f for f, r in calibration_results.items() if not r.get("is_bw")]
        bw_films = [f for f, r in calibration_results.items() if r.get("is_bw")]
        
        calibration_passed = sum(
            1 for f in color_films 
            if calibration_results[f]["calibrated_eval"]["gray_deviation"] < 0.002
        )
        
        # 構建報告
        report_lines = []
        report_lines.append("╔" + "="*78 + "╗")
        report_lines.append("║" + " "*20 + "Phos 光譜校正完整驗證報告" + " "*31 + "║")
        report_lines.append("╠" + "="*78 + "╣")
        report_lines.append("║ 測試時間: " + self.test_results["timestamp"][:19] + " "*46 + "║")
        report_lines.append("╚" + "="*78 + "╝")
        report_lines.append("")
        
        report_lines.append("┌─ 階段 1: 物理理論驗證 ─────────────────────────────────────────┐")
        report_lines.append("│                                                                │")
        report_lines.append(f"│  總測試膠片數: {total_films:<2d}                                                  │")
        report_lines.append(f"│  通過膠片數:   {physics_passed:<2d} ({physics_passed/total_films*100:.1f}%)                                           │")
        report_lines.append("│                                                                │")
        
        # 列出失敗的膠片
        failed_films = [name for name, r in physics_results.items() if not r["all_passed"]]
        if failed_films:
            report_lines.append("│  ✗ 失敗膠片:                                                   │")
            for film in failed_films:
                error_count = physics_results[film]["errors"]
                warning_count = physics_results[film]["warnings"]
                report_lines.append(f"│    - {film:<20s} (錯誤: {error_count}, 警告: {warning_count})               │")
        else:
            report_lines.append("│  ✓ 所有膠片通過物理驗證！                                      │")
        
        report_lines.append("│                                                                │")
        report_lines.append("└────────────────────────────────────────────────────────────────┘")
        report_lines.append("")
        
        report_lines.append("┌─ 階段 2: 光譜響應校正 ─────────────────────────────────────────┐")
        report_lines.append("│                                                                │")
        report_lines.append(f"│  彩色膠片: {len(color_films):<2d}                                                    │")
        report_lines.append(f"│  黑白膠片: {len(bw_films):<2d} (跳過)                                             │")
        report_lines.append(f"│  通過校正: {calibration_passed:<2d}/{len(color_films)} (灰階偏差 < 0.002)                                │")
        report_lines.append("│                                                                │")
        
        # 詳細校正結果
        report_lines.append("│  校正效果:                                                      │")
        for film_name in color_films:
            result = calibration_results[film_name]
            gray_dev = result["calibrated_eval"]["gray_deviation"]
            improvement = result["improvement"]["gray_deviation"] * 100
            status = "✓" if gray_dev < 0.002 else "⚠"
            
            report_lines.append(f"│    {status} {film_name:<15s} 偏差: {gray_dev:.6f}  改善: {improvement:5.1f}%      │")
        
        report_lines.append("│                                                                │")
        report_lines.append("└────────────────────────────────────────────────────────────────┘")
        report_lines.append("")
        
        # 總結
        overall_pass = physics_passed == total_films and calibration_passed == len(color_films)
        
        report_lines.append("╔" + "="*78 + "╗")
        if overall_pass:
            report_lines.append("║" + " "*15 + "✓ 所有測試通過！物理理論正確且無色偏" + " "*20 + "║")
        else:
            issues = []
            if physics_passed < total_films:
                issues.append(f"{total_films - physics_passed} 膠片物理驗證失敗")
            if calibration_passed < len(color_films):
                issues.append(f"{len(color_films) - calibration_passed} 膠片仍有色偏")
            
            report_lines.append("║" + " "*15 + "⚠ 存在問題，需要進一步調整" + " "*25 + "║")
            for issue in issues:
                report_lines.append("║  - " + issue + " "*(70 - len(issue)) + "║")
        
        report_lines.append("╚" + "="*78 + "╝")
        report_lines.append("")
        
        report = "\n".join(report_lines)
        
        if self.verbose:
            print(report)
        
        # 保存摘要
        self.test_results["summary"] = {
            "overall_pass": overall_pass,
            "physics_validation": {
                "total": total_films,
                "passed": physics_passed,
                "failed": len(failed_films)
            },
            "calibration": {
                "color_films": len(color_films),
                "passed": calibration_passed,
                "bw_films_skipped": len(bw_films)
            }
        }
        
        return report
    
    def save_results(self, output_file: str = "calibration_test_results.json"):
        """保存測試結果到JSON"""
        # 簡化結果（移除無法序列化的對象）
        simplified_results = {
            "timestamp": self.test_results["timestamp"],
            "summary": self.test_results["summary"],
            "physics_validation_summary": {
                name: {
                    "total_tests": r["total_tests"],
                    "passed": r["passed"],
                    "errors": r["errors"],
                    "warnings": r["warnings"],
                    "all_passed": r["all_passed"]
                }
                for name, r in self.test_results["physics_validation"].items()
            },
            "calibration_summary": {
                name: {
                    "is_bw": r.get("is_bw", False),
                    "gray_deviation": r.get("calibrated_eval", {}).get("gray_deviation"),
                    "improvement_pct": r.get("improvement", {}).get("gray_deviation", 0) * 100
                }
                for name, r in self.test_results["calibration"]["results"].items()
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(simplified_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 測試結果已保存: {output_file}")
    
    def run_all(self, strategy_id: int = 3, visualize: bool = False,
               export_code: bool = False, save_json: bool = True):
        """
        運行所有測試
        
        Args:
            strategy_id: 校正策略ID
            visualize: 是否生成視覺化
            export_code: 是否導出校正後的代碼
            save_json: 是否保存JSON結果
        """
        print("\n╔" + "="*78 + "╗")
        print("║" + " "*15 + "Phos 光譜校正完整驗證測試套件" + " "*25 + "║")
        print("╚" + "="*78 + "╝\n")
        
        # 階段 1: 物理驗證
        self.run_physics_validation()
        
        # 階段 2: 光譜校正
        calibration_results = self.run_calibration_test(strategy_id)
        
        # 階段 3: 視覺化（可選）
        if visualize:
            self.generate_visualizations(strategy_id)
        
        # 階段 4: 導出代碼（可選）
        if export_code:
            calibrator = ComprehensiveCalibrator(verbose=False)
            calibrator.calibration_results = calibration_results
            calibrator.export_code(calibration_results, "calibrated_coefficients.txt")
        
        # 生成最終報告
        self.generate_final_report()
        
        # 保存結果
        if save_json:
            self.save_results()
        
        print("\n✓ 所有測試完成！\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="運行所有光譜校正驗證測試",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 運行所有測試（使用策略3）
  python tools/run_all_calibration_tests.py
  
  # 運行測試並生成視覺化報告
  python tools/run_all_calibration_tests.py --visualize
  
  # 使用策略4並導出代碼
  python tools/run_all_calibration_tests.py --strategy 4 --export
  
  # 完整測試（所有功能）
  python tools/run_all_calibration_tests.py --strategy 3 --visualize --export
        """
    )
    
    parser.add_argument("--strategy", type=int, default=3, choices=[1,2,3,4,5],
                       help="校正策略 (1-5, 預設=3)")
    parser.add_argument("--visualize", action="store_true",
                       help="生成視覺化報告（需要 matplotlib）")
    parser.add_argument("--export", action="store_true",
                       help="導出校正後的代碼")
    parser.add_argument("--no-json", action="store_true",
                       help="不保存JSON結果")
    parser.add_argument("--quiet", action="store_true",
                       help="安靜模式（僅顯示摘要）")
    
    args = parser.parse_args()
    
    suite = CombinedTestSuite(verbose=not args.quiet)
    suite.run_all(
        strategy_id=args.strategy,
        visualize=args.visualize,
        export_code=args.export,
        save_json=not args.no_json
    )


if __name__ == "__main__":
    main()
