"""
Phos UI Components - Streamlit 界面組件

將 UI 邏輯從主程式分離，提高可維護性。

包含：
- CSS 樣式
- 側邊欄渲染
- 結果顯示（單張/批量）
- 歡迎頁面
"""

import streamlit as st
import cv2
import time
import io
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

import film_models
from film_models import PhysicsMode
from phos_batch import (
    BatchProcessor,
    BatchResult,
    create_zip_archive,
    generate_zip_filename,
    validate_batch_size,
    estimate_processing_time
)


# ==================== CSS 樣式 ====================

def apply_custom_styles():
    """應用自定義 CSS 樣式到 Streamlit 應用"""
    st.markdown("""
    <style>
        /* 全局字體與基礎樣式 */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* 主背景 - 深色漸層 */
        .stApp {
            background: linear-gradient(135deg, #0F1419 0%, #1A1F2E 100%);
            background-attachment: fixed;
        }
        
        /* ===== 側邊欄樣式 ===== */
        [data-testid="stSidebar"] {
            background: rgba(26, 31, 46, 0.85) !important;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255, 107, 107, 0.15);
        }
        
        [data-testid="stSidebar"] h1 {
            color: #FF6B6B !important;
            font-size: 2rem !important;
            font-weight: 700 !important;
            margin-bottom: 0.25rem !important;
        }
        
        [data-testid="stSidebar"] h2 {
            color: #B8B8B8 !important;
            font-size: 0.9rem !important;
            font-weight: 400 !important;
            margin-bottom: 2rem !important;
        }
        
        [data-testid="stSidebar"] h3 {
            color: #E8E8E8 !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            margin-top: 1.5rem !important;
            margin-bottom: 1rem !important;
        }
        
        [data-testid="stSidebar"] .stMarkdown {
            color: #B8B8B8 !important;
        }
        
        /* ===== 按鈕樣式 ===== */
        .stButton > button {
            width: 100%;
            background: rgba(255, 107, 107, 0.1) !important;
            color: #FF6B6B !important;
            border: 1px solid rgba(255, 107, 107, 0.3) !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        
        .stButton > button:hover {
            background: rgba(255, 107, 107, 0.2) !important;
            border-color: rgba(255, 107, 107, 0.5) !important;
            transform: translateY(-1px);
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #FF6B6B, #FF8E8E) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(255, 107, 107, 0.25) !important;
        }
        
        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 6px 16px rgba(255, 107, 107, 0.35) !important;
        }
        
        /* ===== 下載按鈕 ===== */
        .stDownloadButton > button {
            width: 100%;
            background: rgba(76, 175, 80, 0.1) !important;
            color: #66BB6A !important;
            border: 1px solid rgba(76, 175, 80, 0.3) !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
        }
        
        .stDownloadButton > button:hover {
            background: rgba(76, 175, 80, 0.2) !important;
            border-color: rgba(76, 175, 80, 0.5) !important;
        }
        
        /* ===== 選擇框樣式 ===== */
        .stSelectbox label, .stRadio label {
            color: #E8E8E8 !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
        }
        
        .stSelectbox > div > div {
            background: rgba(26, 31, 46, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            color: #E8E8E8 !important;
        }
        
        .stSelectbox > div > div:focus-within {
            border-color: rgba(255, 107, 107, 0.5) !important;
            box-shadow: 0 0 0 1px rgba(255, 107, 107, 0.2) !important;
        }
        
        /* ===== 單選按鈕 ===== */
        .stRadio > div {
            background: transparent !important;
            gap: 0.5rem;
        }
        
        .stRadio > div > label > div {
            background: rgba(26, 31, 46, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            padding: 0.75rem 1rem !important;
        }
        
        .stRadio > div > label > div:hover {
            border-color: rgba(255, 107, 107, 0.3) !important;
        }
        
        /* ===== 文件上傳器 ===== */
        [data-testid="stFileUploader"] {
            background: rgba(26, 31, 46, 0.4) !important;
            border: 2px dashed rgba(255, 107, 107, 0.3) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
        }
        
        [data-testid="stFileUploader"]:hover {
            border-color: rgba(255, 107, 107, 0.5) !important;
            background: rgba(26, 31, 46, 0.6) !important;
        }
        
        [data-testid="stFileUploader"] label {
            color: #E8E8E8 !important;
            font-weight: 500 !important;
        }
        
        /* ===== 進度條 ===== */
        .stProgress > div > div > div {
            background: linear-gradient(90deg, #FF6B6B, #FFB4B4) !important;
        }
        
        .stProgress > div > div {
            background: rgba(26, 31, 46, 0.6) !important;
            border-radius: 8px !important;
        }
        
        /* ===== 警告框 ===== */
        .stAlert {
            background: rgba(26, 31, 46, 0.8) !important;
            border-radius: 8px !important;
            border-left: 3px solid !important;
            padding: 0.75rem 1rem !important;
        }
        
        div[data-baseweb="notification"] {
            background: rgba(26, 31, 46, 0.8) !important;
            border-radius: 8px !important;
        }
        
        /* ===== 圖片容器 ===== */
        [data-testid="stImage"] {
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        }
        
        /* ===== 分隔線 ===== */
        hr {
            border: none !important;
            height: 1px !important;
            background: rgba(255, 107, 107, 0.2) !important;
            margin: 1.5rem 0 !important;
        }
        
        /* ===== 標題樣式 ===== */
        h1 {
            color: #FF6B6B !important;
            font-weight: 700 !important;
        }
        
        h2, h3 {
            color: #E8E8E8 !important;
            font-weight: 600 !important;
        }
        
        p, li {
            color: #B8B8B8 !important;
            line-height: 1.6 !important;
        }
        
        /* ===== 滾動條 ===== */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(26, 31, 46, 0.3);
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 107, 107, 0.3);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 107, 107, 0.5);
        }
        
        /* ===== 隱藏元素 ===== */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* ===== 容器間距 ===== */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        
        [data-testid="column"] {
            padding: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)


# ==================== 側邊欄渲染 ====================

def render_sidebar() -> Dict[str, Any]:
    """
    渲染側邊欄 UI，返回用戶選擇的所有參數
    
    Returns:
        dict: 包含所有用戶選擇的參數
            - processing_mode: str
            - film_type: str
            - grain_style: str
            - tone_style: str
            - physics_mode: PhysicsMode
            - physics_params: dict
            - uploaded_image: UploadedFile | None
            - uploaded_images: List[UploadedFile] | None
    """
    with st.sidebar:
        # 應用標題
        st.markdown("# Phos.")
        st.markdown("## 計算光學胶片模拟")
        st.markdown("---")
        st.markdown("#### 🚀 v0.2.0 · Batch Processing")
        st.markdown("")
        
        # 處理模式選擇
        st.markdown("### 📷 處理模式")
        processing_mode = st.radio(
            "選擇處理模式",
            ["單張處理", "批量處理"],
            index=0,
            help="單張處理: 處理一張照片\n批量處理: 同時處理多張照片",
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### 🎞️ 胶片設定")
        
        # 胶片類型選擇
        film_type = st.selectbox(
            "請選擇膠片:",
            [
                # === 彩色負片 (Color Negative) ===
                "NC200", "Portra400", "Ektar100", "Gold200", "ProImage100", "Superia400",
                
                # === 黑白負片 (B&W) ===
                "AS100", "HP5Plus400", "TriX400", "FP4Plus125", "FS200",
                
                # === 反轉片/正片 (Slide/Reversal) ===
                "Velvia50",
                
                # === 電影感/特殊 (Cinematic/Special) ===
                "Cinestill800T", "Cinestill800T_MediumPhysics",
                
                # === Mie 散射查表版本 (v2 lookup table, Phase 5.5) ===
                "NC200_Mie", "Portra400_MediumPhysics_Mie", "Ektar100_Mie", 
                "Gold200_Mie", "ProImage100_Mie", "Superia400_Mie",
                "Cinestill800T_Mie", "Velvia50_Mie"
            ],
            index=0,
            help=(
                "選擇要模擬的膠片類型，下方會顯示詳細資訊\n\n"
                "📍 所有彩色底片已啟用 Medium Physics（波長依賴散射 + 獨立 Halation 模型）\n"
                "🔬 _Mie 後綴：使用 Mie 散射理論查表（v2, 200 點網格，η 誤差 2.16%）\n"
                "🎨 標準版：使用經驗公式（λ^-3.5 標度律）"
            )
        )
        
        # 顯示選中底片的詳細資訊
        film_profiles = film_models.create_film_profiles()
        film_profile = film_profiles.get(film_type)
        if film_profile:
            display_name = film_profile.display_name or film_profile.name
            brand = film_profile.brand or "Unknown"
            film_type_label = film_profile.film_type or ("🎨 彩色負片" if film_profile.color_type == "color" else "⚫ 黑白負片")
            iso = film_profile.iso_rating or "ISO 400"
            description = film_profile.description or "No description available."
            features = film_profile.features or []
            best_for = film_profile.best_for or "General photography"
            
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, rgba(26, 31, 46, 0.6), rgba(26, 31, 46, 0.4)); 
                        padding: 1rem; 
                        border-radius: 8px; 
                        border-left: 3px solid #FF6B6B;
                        margin-top: 0.5rem;
                        margin-bottom: 1rem;'>
                <p style='color: #FF6B6B; font-weight: 600; font-size: 1.05rem; margin: 0 0 0.25rem 0;'>
                    {display_name}
                </p>
                <p style='color: #B8B8B8; font-size: 0.85rem; margin: 0 0 0.75rem 0;'>
                    {brand} · {film_type_label} · {iso}
                </p>
                <p style='color: #E8E8E8; font-size: 0.9rem; line-height: 1.5; margin: 0 0 0.75rem 0;'>
                    {description}
                </p>
                <div style='display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.5rem;'>
                    {''.join([f"<span style='background: rgba(255, 107, 107, 0.15); color: #FFB4B4; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;'>{feature}</span>" for feature in features])}
                </div>
                <p style='color: #888; font-size: 0.8rem; margin: 0;'>
                    💡 適用場景：{best_for}
                </p>
            </div>
            """, unsafe_allow_html=True)

        grain_style = st.selectbox(
            "胶片顆粒度：",
            ["默認", "柔和", "較粗", "不使用"],
            index=0,
            help="選擇胶片的顆粒度",
        )
        
        tone_style = st.selectbox(
            "曲線映射：",
            ["filmic", "reinhard"],
            index=0,
            help='''選擇Tone mapping方式:
            
            目前版本下Reinhard模型似乎表現出更好的動態範圍，
            filmic模型尚不夠完善,但對肩部趾部有更符合目標的刻畫'''
        )

        st.success(f"已選擇胶片: {film_type}")
        
        st.divider()
        
        # 物理模式設定
        physics_mode, physics_params = _render_physics_settings()
        
        st.divider()
        
        # 文件上傳器
        uploaded_image, uploaded_images = _render_file_uploaders(processing_mode)
        
    return {
        'processing_mode': processing_mode,
        'film_type': film_type,
        'grain_style': grain_style,
        'tone_style': tone_style,
        'physics_mode': physics_mode,
        'physics_params': physics_params,
        'uploaded_image': uploaded_image,
        'uploaded_images': uploaded_images
    }


def _render_physics_settings() -> Tuple[PhysicsMode, Dict[str, Any]]:
    """渲染物理模式設定區塊"""
    st.markdown("### ✨ 渲染模式")
    
    physics_mode_choice = st.radio(
        "選擇渲染模式",
        ["Artistic（藝術）", "Physical（物理）", "Hybrid（混合）"],
        index=0,
        help="""選擇影像渲染方式:
        
        **Artistic**: 視覺優先，討喜色彩（預設）
        **Physical**: 物理準確，能量守恆，H&D曲線
        **Hybrid**: 自由混合藝術與物理特性
        
        詳見 PHYSICAL_MODE_GUIDE.md""",
        label_visibility="collapsed"
    )
    
    # 映射選擇到 PhysicsMode enum
    physics_mode_map = {
        "Artistic（藝術）": PhysicsMode.ARTISTIC,
        "Physical（物理）": PhysicsMode.PHYSICAL,
        "Hybrid（混合）": PhysicsMode.HYBRID
    }
    physics_mode = physics_mode_map[physics_mode_choice]
    
    # 顯示模式說明
    if physics_mode == PhysicsMode.ARTISTIC:
        st.info("🎨 **藝術模式**: 視覺導向，中調顆粒，鮮艷色彩")
    elif physics_mode == PhysicsMode.PHYSICAL:
        st.info("🔬 **物理模式**: 能量守恆、H&D曲線、泊松顆粒")
    else:  # HYBRID
        st.info("⚙️ **混合模式**: 可自訂各項參數（展開下方設定）")
    
    # 進階物理參數
    physics_params = {}
    
    if physics_mode in [PhysicsMode.PHYSICAL, PhysicsMode.HYBRID]:
        st.markdown("---")
        st.markdown("### ⚙️ 物理參數")
        
        # Bloom 參數
        with st.expander("📊 Bloom（光暈）參數", expanded=False):
            bloom_mode = st.radio(
                "Bloom 模式",
                ["artistic", "physical"],
                index=1 if physics_mode == PhysicsMode.PHYSICAL else 0,
                help="artistic: 可增加能量（視覺導向）\nphysical: 能量守恆（物理準確）",
                key="bloom_mode"
            )
            
            bloom_threshold = st.slider(
                "高光閾值 (Threshold)",
                min_value=0.5,
                max_value=0.95,
                value=0.8,
                step=0.05,
                help="控制哪些像素參與散射。較低值 → 更多高光 → 光暈明顯",
                key="bloom_threshold"
            )
            
            if bloom_mode == "physical":
                bloom_scattering_ratio = st.slider(
                    "散射能量比例",
                    min_value=0.05,
                    max_value=0.30,
                    value=0.10,
                    step=0.05,
                    help="控制多少高光能量參與散射。真實膠片約 5-15%",
                    key="bloom_scattering"
                )
            else:
                bloom_scattering_ratio = 0.1
            
            st.caption(f"當前設定: {bloom_mode.upper()} 模式, 閾值 {bloom_threshold}, 散射 {bloom_scattering_ratio}")
        
        physics_params['bloom_mode'] = bloom_mode
        physics_params['bloom_threshold'] = bloom_threshold
        physics_params['bloom_scattering_ratio'] = bloom_scattering_ratio
        
        # H&D 曲線參數
        with st.expander("📈 H&D 曲線參數", expanded=False):
            hd_enabled = st.checkbox(
                "啟用 H&D 特性曲線",
                value=False,
                help="⚠️ 實驗性功能：模擬真實膠片的對數響應與動態範圍壓縮\n目前可能導致色彩偏移，建議保持關閉",
                key="hd_enabled"
            )
            
            if hd_enabled:
                hd_gamma = st.slider(
                    "Gamma（對比度）",
                    min_value=0.50,
                    max_value=2.00,
                    value=0.65,
                    step=0.05,
                    help="負片: 0.6-0.7（低對比）\n正片: 1.5-2.0（高對比）",
                    key="hd_gamma"
                )
                
                hd_toe_strength = st.slider(
                    "Toe 強度（陰影壓縮）",
                    min_value=0.5,
                    max_value=5.0,
                    value=2.0,
                    step=0.5,
                    help="較高值 → 陰影更柔和、細節更豐富",
                    key="hd_toe"
                )
                
                hd_shoulder_strength = st.slider(
                    "Shoulder 強度（高光壓縮）",
                    min_value=0.5,
                    max_value=3.0,
                    value=1.5,
                    step=0.5,
                    help="較高值 → 高光渐進飽和、細節保留",
                    key="hd_shoulder"
                )
                
                st.caption(f"Gamma={hd_gamma}, Toe={hd_toe_strength}, Shoulder={hd_shoulder_strength}")
            else:
                hd_gamma = 0.65
                hd_toe_strength = 2.0
                hd_shoulder_strength = 1.5
        
        physics_params['hd_enabled'] = hd_enabled
        physics_params['hd_gamma'] = hd_gamma
        physics_params['hd_toe_strength'] = hd_toe_strength
        physics_params['hd_shoulder_strength'] = hd_shoulder_strength
        
        # 顆粒參數
        with st.expander("🎲 顆粒參數", expanded=False):
            grain_mode = st.radio(
                "顆粒模式",
                ["artistic", "poisson"],
                index=1 if physics_mode == PhysicsMode.PHYSICAL else 0,
                help="artistic: 中調峰值（視覺導向）\npoisson: 暗部峰值（光子統計）",
                key="grain_mode"
            )
            
            grain_size = st.slider(
                "顆粒尺寸 (μm)",
                min_value=0.5,
                max_value=3.5,
                value=1.5,
                step=0.5,
                help="ISO 100: 0.5-1.0\nISO 400: 1.0-2.0\nISO 1600+: 2.0-3.5",
                key="grain_size"
            )
            
            grain_intensity = st.slider(
                "顆粒強度",
                min_value=0.0,
                max_value=2.0,
                value=0.8,
                step=0.1,
                help="0.3: 輕微\n0.8: 適中\n1.5: 強烈",
                key="grain_intensity"
            )
            
            st.caption(f"{grain_mode.upper()} 模式, 尺寸 {grain_size}μm, 強度 {grain_intensity}")
        
        physics_params['grain_mode'] = grain_mode
        physics_params['grain_size'] = grain_size
        physics_params['grain_intensity'] = grain_intensity
        
        # 膠片光譜處理參數
        with st.expander("🎨 膠片光譜模擬（實驗性）", expanded=False):
            use_film_spectra = st.checkbox(
                "啟用光譜膠片模擬",
                value=False,
                help="""基於物理的31通道光譜處理：
                
**原理**：
• RGB → 31通道光譜 (Smits 1999)
• 光譜 × 膠片敏感度曲線 → RGB
• 真實重現膠片色彩特性

**效能** (6MP 影像):
• RGB→Spectrum: ~3.3s (3.5x 優化)
• 完整處理: ~4.2s
• 記憶體: 31 MB (tile-based)

⚠️ 實驗功能，處理時間約 5-10 秒""",
                key="use_film_spectra"
            )
            
            if use_film_spectra:
                film_spectra_name = st.selectbox(
                    "選擇膠片光譜",
                    ["Portra400", "Velvia50", "Cinestill800T", "HP5Plus400"],
                    index=0,
                    help="""選擇膠片的光譜響應曲線：
                    
**Portra400**: 柔和人像，寬容度高 (人像/日常)
**Velvia50**: 極致飽和，對比強烈 (風景/藍天)
**Cinestill800T**: 電影質感，鎢絲燈優化 (夜景/室內)
**HP5Plus400**: 黑白全色，經典顆粒 (街拍/人文)""",
                    key="film_spectra_name"
                )
                
                st.info(f"""
**當前膠片**: {film_spectra_name}

📐 **處理流程**: 
RGB → 31-ch Spectrum (380-770nm) → Film Response → RGB

✅ **物理正確**: 
• 往返誤差 <3%
• 能量守恆 <0.01%
• 色彩關係保持

⏱️ **預計時間**: 4-10 秒 (取決於影像大小)
                """)
            else:
                film_spectra_name = 'Portra400'
        
        physics_params['use_film_spectra'] = use_film_spectra
        physics_params['film_spectra_name'] = film_spectra_name
        
        # 互易律失效參數
        with st.expander("⏱️ 互易律失效 (Reciprocity Failure)", expanded=False):
            reciprocity_enabled = st.checkbox(
                "啟用互易律失效效應",
                value=False,
                help="""模擬長曝光時的膠片非線性響應
                
**原理**：
• Schwarzschild 定律: E = I·t^p (p < 1)
• 長曝光時膠片感光效率降低
• 不同色層反應不同 → 色偏

**效果**：
• 曝光時間 > 1s: 影像變暗
• 曝光時間 >> 1s: 顯著偏紅-黃色調
• 真實重現膠片物理特性

⚠️ 實驗功能，需要設定正確的曝光時間""",
                key="reciprocity_enabled"
            )
            
            if reciprocity_enabled:
                exposure_time_log = st.slider(
                    "曝光時間（對數尺度）",
                    min_value=-4.0,
                    max_value=2.5,
                    value=0.0,
                    step=0.1,
                    help="拖動滑桿調整曝光時間\n左: 快速快門\n中: 1秒（無效應）\n右: 長曝光",
                    key="exposure_time_log"
                )
                exposure_time = 10 ** exposure_time_log
                
                if exposure_time < 1.0:
                    time_display = f"{exposure_time:.4f} s ({1/exposure_time:.0f} fps)"
                else:
                    time_display = f"{exposure_time:.2f} s"
                
                st.caption(f"**實際曝光時間**: {time_display}")
                
                if exposure_time > 1.0:
                    try:
                        from reciprocity_failure import calculate_exposure_compensation
                        from film_models import ReciprocityFailureParams
                        
                        temp_params = ReciprocityFailureParams(enabled=True)
                        comp_ev = calculate_exposure_compensation(exposure_time, temp_params)
                        intensity_loss = (1 - 2**(-comp_ev)) * 100
                        
                        st.info(f"""
💡 **預估效果** (基於 Portra 400):
• 曝光補償需求: **+{comp_ev:.2f} EV**
• 亮度損失: **{intensity_loss:.1f}%**
• 色調變化: 偏紅-黃（長曝光）
                        """)
                    except:
                        pass
                else:
                    st.caption("曝光時間 ≤ 1s：無顯著互易律失效效應")
            else:
                exposure_time = 1.0
        
        physics_params['reciprocity_enabled'] = reciprocity_enabled
        physics_params['exposure_time'] = exposure_time
        
    else:
        # Artistic 模式：使用預設值
        physics_params = {
            'bloom_mode': "artistic",
            'bloom_threshold': 0.8,
            'bloom_scattering_ratio': 0.1,
            'hd_enabled': False,
            'hd_gamma': 0.65,
            'hd_toe_strength': 2.0,
            'hd_shoulder_strength': 1.5,
            'grain_mode': "artistic",
            'grain_size': 1.5,
            'grain_intensity': 0.8,
            'use_film_spectra': False,
            'film_spectra_name': 'Portra400',
            'reciprocity_enabled': False,
            'exposure_time': 1.0
        }
    
    # 統一添加 physics_mode 到返回的參數中
    physics_params['physics_mode'] = physics_mode
    
    return physics_mode, physics_params


def _render_file_uploaders(processing_mode: str) -> Tuple[Optional[Any], Optional[List[Any]]]:
    """渲染文件上傳器"""
    if processing_mode == "單張處理":
        uploaded_image = st.file_uploader(
            "選擇一張照片來開始沖洗",
            type=["jpg", "jpeg", "png"],
            help="上傳一張照片沖洗試試看吧"
        )
        uploaded_images = None
    else:  # 批量處理
        uploaded_images = st.file_uploader(
            "選擇多張照片進行批量處理",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="一次最多可處理 50 張照片"
        )
        uploaded_image = None
        
        if uploaded_images:
            num_files = len(uploaded_images)
            is_valid, error_msg = validate_batch_size(num_files, max_size=50)
            
            if not is_valid:
                st.error(error_msg)
                uploaded_images = None
            else:
                st.info(f"✅ 已上傳 {num_files} 張照片")
                est_time = estimate_processing_time(num_files, avg_time_per_image=2.0)
                st.info(f"⏱️ 預計處理時間: {est_time}")
    
    return uploaded_image, uploaded_images


# ==================== 結果顯示 ====================

def render_single_image_result(film_image: np.ndarray, process_time: float, 
                               physics_mode: PhysicsMode, output_path: str):
    """
    顯示單張圖片處理結果
    
    Args:
        film_image: 處理後的圖像（BGR 格式）
        process_time: 處理時間（秒）
        physics_mode: 使用的物理模式
        output_path: 輸出檔案名稱
    """
    # DEBUG 色彩診斷
    h, w = film_image.shape[:2]
    sample_pixel_bgr = film_image[h//2, w//2]
    st.write(f"🔍 DEBUG - 處理後圖像（BGR 格式）中心像素: B={sample_pixel_bgr[0]}, G={sample_pixel_bgr[1]}, R={sample_pixel_bgr[2]}")
    
    # 轉換 BGR 到 RGB
    film_rgb = cv2.cvtColor(film_image, cv2.COLOR_BGR2RGB)
    
    sample_pixel_rgb = film_rgb[h//2, w//2]
    st.write(f"🔍 DEBUG - 轉換後圖像（RGB 格式）中心像素: R={sample_pixel_rgb[0]}, G={sample_pixel_rgb[1]}, B={sample_pixel_rgb[2]}")
    st.write(f"🔍 DEBUG - 藍色通道平均: {film_image[..., 0].mean():.1f}, 紅色通道平均: {film_image[..., 2].mean():.1f}")
    
    # 顯示結果
    st.image(film_rgb, channels="RGB", width=800)
    st.success(f"✨ 底片顯影好了！用時 {process_time:.2f}秒 | 模式: {physics_mode.name}") 
    
    # 下載按鈕
    film_pil = Image.fromarray(film_rgb)
    buf = io.BytesIO()
    film_pil.save(buf, format="JPEG", quality=95)
    byte_im = buf.getvalue()
    
    st.download_button(
        label="📥 下載高清圖像",
        data=byte_im,
        file_name=output_path,
        mime="image/jpeg"
    )


def render_batch_processing_ui(uploaded_images: List[Any], film_type: str,
                               settings: Dict[str, Any], 
                               standardize_func, spectral_response_func,
                               optical_processing_func, get_cached_film_profile_func):
    """
    渲染批量處理 UI 並執行處理
    
    Args:
        uploaded_images: 上傳的圖片列表
        film_type: 底片類型
        settings: 處理設定
        standardize_func: 標準化函數
        spectral_response_func: 光譜響應函數
        optical_processing_func: 光學處理函數
        get_cached_film_profile_func: 獲取底片配置函數
    """
    st.header(f"📦 批量處理 - {len(uploaded_images)} 張照片")
    
    if st.button("🚀 開始批量處理", type="primary", use_container_width=True):
        try:
            # 初始化批量處理器
            batch_processor = BatchProcessor(max_workers=4)
            
            # 獲取胶片配置
            film = get_cached_film_profile_func(film_type)
            
            # 創建進度條
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 進度回調
            def update_progress(current, total, filename):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"處理中: {filename} ({current}/{total})")
            
            # 定義處理函數
            def batch_process_func(image_array, film_profile, proc_settings):
                image_std = standardize_func(image_array)
                response_r, response_g, response_b, response_total = spectral_response_func(image_std, film_profile)
                result = optical_processing_func(
                    response_r, response_g, response_b, response_total,
                    film_profile,
                    proc_settings['grain_style'],
                    proc_settings['tone_style'],
                    use_film_spectra=proc_settings.get('use_film_spectra', False),
                    film_spectra_name=proc_settings.get('film_spectra_name', 'Portra400'),
                    exposure_time=proc_settings.get('exposure_time', 1.0)
                )
                return result
            
            # 開始處理
            start_time = time.time()
            results = batch_processor.process_batch_sequential(
                uploaded_images,
                film,
                batch_process_func,
                settings,
                progress_callback=update_progress
            )
            total_time = time.time() - start_time
            
            # 顯示結果
            success_count = sum(1 for r in results if r.success)
            fail_count = len(results) - success_count
            
            progress_bar.empty()
            status_text.empty()
            
            if success_count > 0:
                st.success(f"✅ 處理完成！成功: {success_count}/{len(results)} 張，總用時: {total_time:.2f} 秒")
                
                # 保存結果
                st.session_state.batch_results = results
                
                # 顯示預覽
                st.subheader("📸 處理結果預覽")
                cols = st.columns(3)
                preview_count = min(6, success_count)
                preview_idx = 0
                
                for idx, result in enumerate(results):
                    if result.success and preview_idx < preview_count:
                        col = cols[preview_idx % 3]
                        with col:
                            result_rgb = cv2.cvtColor(result.image_data, cv2.COLOR_BGR2RGB)
                            st.image(result_rgb, caption=result.filename, width=200)
                            st.caption(f"⏱️ {result.processing_time:.2f}s")
                        preview_idx += 1
                
                if success_count > preview_count:
                    st.info(f"還有 {success_count - preview_count} 張照片未顯示，請下載 ZIP 查看全部")
                
                # ZIP 下載
                st.subheader("📦 下載處理結果")
                with st.spinner("正在生成 ZIP 檔案..."):
                    zip_data = create_zip_archive(results, film_name=film_type, output_format="jpg", quality=95)
                    zip_filename = generate_zip_filename(film_type)
                
                st.download_button(
                    label=f"📥 下載全部照片 (ZIP)",
                    data=zip_data,
                    file_name=zip_filename,
                    mime="application/zip",
                    use_container_width=True
                )
                
                # 失敗列表
                if fail_count > 0:
                    with st.expander(f"⚠️ {fail_count} 張照片處理失敗", expanded=False):
                        for result in results:
                            if not result.success:
                                st.error(f"❌ {result.filename}: {result.error_message}")
            else:
                st.error("❌ 所有照片處理失敗，請檢查圖像格式或胶片設定")
                
        except Exception as e:
            st.error(f"❌ 批量處理時發生錯誤: {str(e)}")
            import traceback
            st.error(traceback.format_exc())


def render_welcome_page():
    """渲染歡迎頁面"""
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0 3rem 0;'>
        <h1 style='font-size: 3.5rem; font-weight: 700; margin: 0 0 0.5rem 0;
                   color: #FF6B6B;'>
            Phos.
        </h1>
        <p style='font-size: 1.2rem; color: #B8B8B8; margin: 0 0 0.25rem 0;'>
            計算光學胶片模拟
        </p>
        <p style='font-size: 1rem; color: #888; font-style: italic; margin: 0;'>
            "No LUTs, we calculate LUX."
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 功能卡片
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        st.markdown("""
        <div style='padding: 1.5rem; background: rgba(26, 31, 46, 0.5); 
                    border-radius: 12px; border: 1px solid rgba(255, 107, 107, 0.2);
                    min-height: 200px;'>
            <h3 style='color: #FF6B6B; margin: 0 0 1rem 0; font-size: 1.1rem;'>🎞️ 單張處理</h3>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li>精準模擬 7 款經典胶片</li>
                <li>計算光學原理，非 LUT</li>
                <li>細膩顆粒與光暈效果</li>
                <li>高質量輸出 (JPEG 95)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='padding: 1.5rem; background: rgba(26, 31, 46, 0.5); 
                    border-radius: 12px; border: 1px solid rgba(255, 107, 107, 0.2);
                    min-height: 200px;'>
            <h3 style='color: #FF6B6B; margin: 0 0 1rem 0; font-size: 1.1rem;'>📦 批量處理</h3>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li>一次處理最多 50 張照片</li>
                <li>實時進度顯示</li>
                <li>智能時間預估</li>
                <li>一鍵 ZIP 批量下載</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 胶片列表
    st.markdown("### 🎬 可用胶片")
    
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        st.markdown("""
        <div style='background: rgba(26, 31, 46, 0.3); padding: 1rem; border-radius: 8px;'>
            <p style='color: #E8E8E8; font-weight: 600; margin: 0 0 0.75rem 0;'>彩色胶片 Color Films (8款)</p>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li><strong>NC200</strong> - 富士經典日常</li>
                <li><strong>Portra400</strong> - Kodak 人像王者</li>
                <li><strong>Ektar100</strong> - Kodak 風景利器</li>
                <li><strong>Velvia50</strong> ⭐ - 富士極致飽和</li>
                <li><strong>Gold200</strong> ⭐ - Kodak 陽光金黃</li>
                <li><strong>ProImage100</strong> ⭐ - Kodak 日常經典</li>
                <li><strong>Superia400</strong> ⭐ - 富士清新綠調</li>
                <li><strong>Cinestill800T</strong> - 電影鎢絲燈</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='background: rgba(26, 31, 46, 0.3); padding: 1rem; border-radius: 8px;'>
            <p style='color: #E8E8E8; font-weight: 600; margin: 0 0 0.75rem 0;'>黑白胶片 B&W Films (5款)</p>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li><strong>AS100</strong> - 富士 ACROS 細膩</li>
                <li><strong>HP5Plus400</strong> - Ilford 經典</li>
                <li><strong>TriX400</strong> ⭐ - Kodak 街拍傳奇</li>
                <li><strong>FP4Plus125</strong> ⭐ - Ilford 低速精細</li>
                <li><strong>FS200</strong> - 實驗性高對比</li>
            </ul>
            <p style='color: #888; font-size: 0.85rem; margin-top: 0.5rem;'>⭐ = 新增底片</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("👈 請在左側邊欄選擇處理模式並上傳照片開始使用")
