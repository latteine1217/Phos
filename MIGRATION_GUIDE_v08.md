# Phos v0.8.0 遷移指南

## ⚠️ Breaking Changes

v0.8.0 將移除從 `Phos.py` 直接導入模組化函數的功能。

**時間線**:
- v0.7.0: 函數模組化完成，舊導入方式仍可用
- v0.7.1: 標記舊導入為棄用（當前版本）
- **v0.8.0: 移除舊導入（Breaking Change）**⚠️

---

## 📋 需要遷移的函數（21 個）

### 1. Optical Core (3 functions)

#### ❌ 舊方式（v0.8.0 將移除）
```python
from Phos import standardize, spectral_response, average_response
```

#### ✅ 新方式
```python
from modules.optical_core import standardize, spectral_response, average_response
```

---

### 2. Tone Mapping (4 functions)

#### ❌ 舊方式（v0.8.0 將移除）
```python
from Phos import (
    apply_reinhard_to_channel,
    apply_reinhard,
    apply_filmic_to_channel,
    apply_filmic
)
```

#### ✅ 新方式
```python
from modules.tone_mapping import (
    apply_reinhard_to_channel,
    apply_reinhard,
    apply_filmic_to_channel,
    apply_filmic
)
```

---

### 3. PSF Utils (7 functions)

#### ❌ 舊方式（v0.8.0 將移除）
```python
from Phos import (
    create_dual_kernel_psf,
    load_mie_lookup_table,
    lookup_mie_params,
    convolve_fft,
    convolve_adaptive,
    get_gaussian_kernel,
    get_exponential_kernel_approximation
)
```

#### ✅ 新方式
```python
from modules.psf_utils import (
    create_dual_kernel_psf,
    load_mie_lookup_table,
    lookup_mie_params,
    convolve_fft,
    convolve_adaptive,
    get_gaussian_kernel,
    get_exponential_kernel_approximation
)
```

---

### 4. Wavelength Effects (4 functions)

#### ❌ 舊方式（v0.8.0 將移除）
```python
from Phos import (
    apply_bloom_with_psf,
    apply_wavelength_bloom,
    apply_halation,
    apply_optical_effects_separated
)
```

#### ✅ 新方式
```python
from modules.wavelength_effects import (
    apply_bloom_with_psf,
    apply_wavelength_bloom,
    apply_halation,
    apply_optical_effects_separated
)
```

---

### 5. Image Processing (2 functions)

#### ❌ 舊方式（v0.8.0 將移除）
```python
from Phos import apply_hd_curve, combine_layers_for_channel
```

#### ✅ 新方式
```python
from modules.image_processing import apply_hd_curve, combine_layers_for_channel
```

---

## 🔍 如何找到需要遷移的代碼

### 方法 1: 使用 grep/rg 搜索
```bash
# 搜索所有從 Phos 導入模組化函數的代碼
rg "from Phos import.*(standardize|apply_hd_curve|apply_reinhard|create_dual_kernel_psf)" --type py
```

### 方法 2: 運行代碼並查看警告
在 v0.7.1 中運行代碼會看到 `DeprecationWarning`:
```
DeprecationWarning: Importing 'apply_hd_curve' from Phos is deprecated in v0.7.1 
and will be removed in v0.8.0. Use 'from modules.image_processing import apply_hd_curve' instead.
```

### 方法 3: 使用靜態分析工具
```bash
# 使用 pylint 檢查棄用警告
pylint your_code.py
```

---

## 🛠️ 批量遷移腳本

使用以下 Python 腳本自動遷移代碼：

```python
#!/usr/bin/env python3
"""
自動遷移 Phos v0.7.x 導入到 v0.8.0 格式
"""
import re
import sys
from pathlib import Path

# 函數到模組的映射
FUNCTION_TO_MODULE = {
    # optical_core
    'standardize': 'modules.optical_core',
    'spectral_response': 'modules.optical_core',
    'average_response': 'modules.optical_core',
    
    # tone_mapping
    'apply_reinhard_to_channel': 'modules.tone_mapping',
    'apply_reinhard': 'modules.tone_mapping',
    'apply_filmic_to_channel': 'modules.tone_mapping',
    'apply_filmic': 'modules.tone_mapping',
    
    # psf_utils
    'create_dual_kernel_psf': 'modules.psf_utils',
    'load_mie_lookup_table': 'modules.psf_utils',
    'lookup_mie_params': 'modules.psf_utils',
    'convolve_fft': 'modules.psf_utils',
    'convolve_adaptive': 'modules.psf_utils',
    'get_gaussian_kernel': 'modules.psf_utils',
    'get_exponential_kernel_approximation': 'modules.psf_utils',
    
    # wavelength_effects
    'apply_bloom_with_psf': 'modules.wavelength_effects',
    'apply_wavelength_bloom': 'modules.wavelength_effects',
    'apply_halation': 'modules.wavelength_effects',
    'apply_optical_effects_separated': 'modules.wavelength_effects',
    
    # image_processing
    'apply_hd_curve': 'modules.image_processing',
    'combine_layers_for_channel': 'modules.image_processing',
}

def migrate_file(filepath: Path):
    """遷移單個文件的導入"""
    content = filepath.read_text(encoding='utf-8')
    original = content
    
    # 按模組分組函數
    module_imports = {}
    for func, module in FUNCTION_TO_MODULE.items():
        if module not in module_imports:
            module_imports[module] = []
        module_imports[module].append(func)
    
    # 替換導入語句
    for module, funcs in module_imports.items():
        pattern = r'from Phos import\s+(?:\()?([^)]+)(?:\))?'
        
        def replace_import(match):
            imports = match.group(1)
            imported_funcs = [f.strip() for f in imports.split(',')]
            
            # 分離需要遷移的和不需要的
            to_migrate = [f for f in imported_funcs if f in funcs]
            others = [f for f in imported_funcs if f not in funcs]
            
            if not to_migrate:
                return match.group(0)  # 不替換
            
            result = []
            if to_migrate:
                result.append(f"from {module} import {', '.join(to_migrate)}")
            if others:
                result.append(f"from Phos import {', '.join(others)}")
            
            return '\n'.join(result)
        
        content = re.sub(pattern, replace_import, content)
    
    # 如果有變更，寫回文件
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        print(f"✅ Migrated: {filepath}")
        return True
    return False

def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("Usage: python migrate_imports.py <file_or_directory>")
        sys.exit(1)
    
    target = Path(sys.argv[1])
    
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = list(target.rglob("*.py"))
    else:
        print(f"❌ Error: {target} is not a file or directory")
        sys.exit(1)
    
    migrated_count = 0
    for file in files:
        if migrate_file(file):
            migrated_count += 1
    
    print(f"\n✅ Migration complete! {migrated_count} file(s) migrated.")

if __name__ == "__main__":
    main()
```

**使用方法**:
```bash
# 遷移單個文件
python migrate_imports.py your_script.py

# 遷移整個目錄
python migrate_imports.py your_project/
```

---

## 📅 遷移時間表

| 版本 | 狀態 | 行動 |
|------|------|------|
| v0.7.0 | ✅ 完成 | 模組化完成，舊導入仍可用 |
| v0.7.1 | 🔄 當前 | 添加棄用警告，建議用戶遷移 |
| v0.7.5 | 📢 計劃 | 最後警告，v0.8.0 即將發布 |
| v0.8.0 | ⚠️ 未來 | **移除舊導入（Breaking Change）** |

---

## ❓ 常見問題

### Q1: 為什麼要移除舊導入？
**A**: 遵循 "Good Taste" 原則，避免多個導入路徑導致混亂。明確的模組邊界有助於代碼維護。

### Q2: 如果我不想遷移怎麼辦？
**A**: 你可以繼續使用 v0.7.x，但建議遷移以獲得未來的功能和 bug 修復。

### Q3: 遷移後需要修改函數調用嗎？
**A**: 不需要！只需修改導入語句，函數調用保持不變。

### Q4: modules 包向後相容嗎？
**A**: 是的！從 `modules` 導入的函數與從 `Phos` 導入的功能完全相同。

---

## 🔗 相關資源

- [v0.7.0 Release Notes](README.md#v070)
- [Modularization Architecture](modules/README.md)
- [API Documentation](docs/API.md)

---

## 📞 需要幫助？

如果在遷移過程中遇到問題，請：

1. 查看完整的錯誤訊息和 deprecation warnings
2. 參閱本指南的範例代碼
3. 提交 Issue: https://github.com/latteine1217/Phos/issues
4. 聯繫郵箱: lyco_p@163.com

---

**遷移愉快！** 🚀
