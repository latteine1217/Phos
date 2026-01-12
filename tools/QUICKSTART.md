# 光譜校正快速入門指南

## 🚀 5分鐘上手

### 1. 運行完整驗證（推薦）

一鍵運行所有測試，獲得完整報告：

```bash
python tools/run_all_calibration_tests.py
```

**輸出**：
- 物理理論驗證報告（13款膠片）
- 光譜響應校正報告（8款彩色膠片）
- 完整摘要與狀態
- `calibration_test_results.json` - JSON格式測試結果

---

### 2. 驗證單個膠片

快速檢查特定膠片的物理正確性：

```bash
python tools/physics_validator.py --film Portra400
```

**範例輸出**：
```
================================================================================
  物理理論驗證：Portra400
================================================================================

✓ Energy Conservation: deviation=0.0010
✓ Row Normalization (Red Layer): Row sum = 0.9990
✓ Row Normalization (Green Layer): Row sum = 1.0000
✓ Row Normalization (Blue Layer): Row sum = 1.0000
✓ Diagonal Dominance: ratio = 5.01
✓ Monotonicity: All channels monotonic
✓ Linearity: error = 0.000000

測試總數: 21
通過測試: 21 (100.0%)
✓ 所有測試通過！
```

---

### 3. 校正並導出代碼

為所有膠片執行校正並生成可用代碼：

```bash
python tools/comprehensive_calibration_tool.py --all --strategy 3 --export
```

**輸出檔案**：
```
calibrated_coefficients.txt
```

**內容範例**：
```python
# Portra400
# 灰階偏差: 0.000100
# 改善: 98.8%

# Red Layer
r_response_weight=0.801000,
g_response_weight=0.079000,
b_response_weight=0.119000,

# Green Layer
r_response_weight=0.045000,
g_response_weight=0.806000,
b_response_weight=0.149000,

# Blue Layer
r_response_weight=0.041000,
g_response_weight=0.066000,
b_response_weight=0.893000,
```

---

### 4. 生成視覺化報告

為所有彩色膠片生成對比圖表：

```bash
# 需要先安裝 matplotlib
pip install matplotlib

# 生成報告
python tools/calibration_visualizer.py --all
```

**輸出目錄**：
```
calibration_reports/
├── Portra400_calibration_report.png
├── Ektar100_calibration_report.png
├── Velvia50_calibration_report.png
├── NC200_calibration_report.png
├── Cinestill800T_calibration_report.png
├── Gold200_calibration_report.png
├── ProImage100_calibration_report.png
└── Superia400_calibration_report.png
```

**圖表內容**：
- 原始 vs 校正後矩陣熱力圖
- 行和比較（能量守恆）
- 灰階響應曲線
- 色偏分析
- 對角線主導性
- 性能指標摘要表

---

### 5. 運行 Pytest 測試

整合到專案測試流程中：

```bash
# 運行所有校正測試
pytest tests_refactored/test_calibration_suite.py -v

# 快速檢查（僅物理驗證）
pytest tests_refactored/test_calibration_suite.py -m physics -v

# 完整測試（含性能基準）
pytest tests_refactored/test_calibration_suite.py --benchmark-only
```

---

## 📊 理解測試結果

### 物理驗證指標

| 指標 | 閾值 | 含義 |
|------|------|------|
| **灰階偏差** | < 0.002 | 純白輸入的 RGB 通道最大偏差 |
| **行不平衡** | < 0.02 | 各層總響應的不均衡程度 |
| **對角主導** | > 5.0 | 對角線元素 / 非對角線元素的比值 |
| **單調性** | 0 逆轉 | 輸入增加時輸出是否單調增加 |
| **線性誤差** | < 0.05 | 違反線性疊加原理的最大誤差 |

### 校正效果評估

**優秀** ✓
- 灰階偏差 < 0.002 (< 0.2%)
- 改善程度 > 90%

**良好** ✓
- 灰階偏差 < 0.01 (< 1%)
- 改善程度 > 50%

**需改進** ⚠
- 灰階偏差 >= 0.01
- 改善程度 < 50%

---

## 🎯 常見工作流程

### 工作流程 A: 新膠片開發

當添加新膠片配置時：

1. **初步驗證**
   ```bash
   python tools/physics_validator.py --film NewFilm400
   ```

2. **發現問題** → 查看具體失敗的測試項

3. **執行校正**
   ```bash
   python tools/comprehensive_calibration_tool.py --film NewFilm400 --compare-strategies
   ```

4. **選擇最佳策略** → 生成代碼

5. **更新 film_models.py** → 手動複製係數

6. **再次驗證**
   ```bash
   python tools/physics_validator.py --film NewFilm400
   ```

7. **生成視覺化** (可選)
   ```bash
   python tools/calibration_visualizer.py --film NewFilm400
   ```

---

### 工作流程 B: 批次驗證現有膠片

定期檢查所有膠片的物理正確性：

1. **運行完整測試套件**
   ```bash
   python tools/run_all_calibration_tests.py --visualize
   ```

2. **檢查 JSON 結果**
   ```bash
   cat calibration_test_results.json
   ```

3. **查看視覺化報告**
   ```bash
   open calibration_reports/*.png
   ```

4. **針對失敗項進行修正**

---

### 工作流程 C: CI/CD 整合

在持續整合流程中自動驗證：

```yaml
# .github/workflows/calibration-tests.yml
name: Calibration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.13
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-benchmark
      
      - name: Run calibration tests
        run: |
          pytest tests_refactored/test_calibration_suite.py -v
      
      - name: Run full validation
        run: |
          python tools/run_all_calibration_tests.py --quiet
```

---

## 🔧 進階用法

### 自訂校正策略

編輯 `tools/comprehensive_calibration_tool.py`：

```python
STRATEGIES[6] = CalibrationStrategy(
    name="Ultra Conservative",
    description="極保守策略：最小化改動",
    normalize_rows=True,
    enhance_diagonal=0.05,  # 僅 5% 對角增強
    target_row_sum=1.0
)
```

運行：
```bash
python tools/comprehensive_calibration_tool.py --film Portra400 --strategy 6
```

---

### 自訂物理驗證閾值

編輯 `tools/physics_validator.py`：

```python
# 在 PhysicsValidator 類中
def run_all_validations(self):
    # 調整閾值
    self.validate_energy_conservation(tolerance=0.001)  # 更嚴格：0.1%
    self.validate_row_normalization(tolerance=0.01)     # 更嚴格：1%
    self.validate_diagonal_dominance(min_ratio=8.0)     # 更嚴格：8.0
    # ...
```

---

### 批次處理特定膠片組

創建自訂腳本：

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.physics_validator import validate_film
from tools.comprehensive_calibration_tool import ComprehensiveCalibrator

# 定義目標膠片
target_films = ["Portra400", "Ektar100", "Velvia50"]

# 驗證
print("\n=== 物理驗證 ===")
for film in target_films:
    validate_film(film, verbose=True)

# 校正
print("\n=== 光譜校正 ===")
calibrator = ComprehensiveCalibrator(verbose=True)
for film in target_films:
    calibrator.calibrate_film(film, strategy_id=3)
```

---

## 💡 提示與技巧

### 1. 快速檢查色偏
```bash
# 僅顯示灰階偏差
python tools/physics_validator.py --film Portra400 --quiet | grep deviation
```

### 2. 比較不同策略
```bash
# 生成所有策略的對比報告
for i in {1..5}; do
  python tools/comprehensive_calibration_tool.py --film Velvia50 --strategy $i >> strategy_comparison.txt
done
```

### 3. 自動化報告郵件
```bash
# 生成報告並郵寄
python tools/run_all_calibration_tests.py > report.txt
mail -s "Calibration Test Report" admin@example.com < report.txt
```

### 4. 監控校正品質趨勢
```bash
# 定期運行並記錄結果
date >> calibration_history.log
python tools/run_all_calibration_tests.py --quiet >> calibration_history.log
```

---

## 🐛 故障排除

### 問題：ImportError: No module named 'matplotlib'
**解決**：安裝 matplotlib
```bash
pip install matplotlib
```

### 問題：ModuleNotFoundError: No module named 'film_models'
**解決**：確保在專案根目錄運行
```bash
cd /path/to/Phos
python tools/physics_validator.py
```

### 問題：測試失敗 - "gray_deviation too high"
**解決**：膠片需要校正
```bash
# 1. 查看詳細報告
python tools/physics_validator.py --film YourFilm

# 2. 執行校正
python tools/comprehensive_calibration_tool.py --film YourFilm --export

# 3. 手動更新 film_models.py
# 4. 重新測試
```

### 問題：視覺化報告無法生成
**解決**：檢查依賴與權限
```bash
# 檢查 matplotlib 版本
python -c "import matplotlib; print(matplotlib.__version__)"

# 確保輸出目錄可寫
mkdir -p calibration_reports
chmod 755 calibration_reports
```

---

## 📚 延伸閱讀

- **完整文檔**：`tools/README.md`
- **物理理論**：`docs/COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md`
- **Pytest 測試**：`tests_refactored/test_calibration_suite.py`
- **舊版工具**：`archive/calibration_tools/` (參考用)

---

## ✅ 檢查清單

使用此清單確保校正工作完整：

- [ ] 運行物理驗證 (`physics_validator.py`)
- [ ] 檢查所有測試通過
- [ ] 執行光譜校正 (`comprehensive_calibration_tool.py`)
- [ ] 比較不同策略效果
- [ ] 生成視覺化報告 (`calibration_visualizer.py`)
- [ ] 導出校正後的代碼
- [ ] 更新 `film_models.py`
- [ ] 運行 pytest 測試套件
- [ ] 提交 git commit
- [ ] 更新文檔（如有新膠片）

---

**最後更新**: 2025-01-12  
**版本**: v1.0  
**作者**: Phos 開發團隊
