"""
Phos UI Components - Streamlit 界面組件

將 UI 邏輯從主程式分離，提高可維護性。

包含：
- CSS 樣式
- 側邊欄渲染
- 結果顯示（單張/批量）
- 歡迎頁面
"""

import streamlit as st  # type: ignore
import cv2  # type: ignore
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
        
        /* 主背景 - 深色漸層 + 動態網格 */
        .stApp {
            background: 
                radial-gradient(circle at 20% 30%, rgba(255, 107, 107, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(66, 165, 245, 0.06) 0%, transparent 50%),
                linear-gradient(135deg, #0F1419 0%, #1A1F2E 100%);
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
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        
        .stButton > button:hover {
            background: rgba(255, 107, 107, 0.2) !important;
            border-color: rgba(255, 107, 107, 0.5) !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 107, 107, 0.2) !important;
        }
        
        .stButton > button:active {
            transform: translateY(0);
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #FF6B6B, #FF8E8E) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 16px rgba(255, 107, 107, 0.3) !important;
            animation: pulse-glow 2s ease-in-out infinite;
        }
        
        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 6px 24px rgba(255, 107, 107, 0.45) !important;
            transform: translateY(-2px);
        }
        
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 4px 16px rgba(255, 107, 107, 0.3); }
            50% { box-shadow: 0 4px 24px rgba(255, 107, 107, 0.5); }
        }
        
        /* ===== 下載按鈕 ===== */
        .stDownloadButton > button {
            width: 100%;
            background: rgba(102, 187, 106, 0.1) !important;
            color: #66BB6A !important;
            border: 1px solid rgba(102, 187, 106, 0.3) !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        
        .stDownloadButton > button:hover {
            background: rgba(102, 187, 106, 0.2) !important;
            border-color: rgba(102, 187, 106, 0.5) !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 187, 106, 0.25) !important;
        }
        
        /* ===== 選擇框樣式 ===== */
        .stSelectbox label, .stRadio label {
            color: #E8E8E8 !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
        }
        
        .stSelectbox > div > div {
            background: rgba(26, 31, 46, 0.8) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            color: #E8E8E8 !important;
            transition: all 0.3s ease !important;
        }
        
        .stSelectbox > div > div:hover {
            border-color: rgba(255, 107, 107, 0.3) !important;
            background: rgba(26, 31, 46, 0.9) !important;
        }
        
        .stSelectbox > div > div:focus-within {
            border-color: rgba(255, 107, 107, 0.6) !important;
            box-shadow: 0 0 0 2px rgba(255, 107, 107, 0.2) !important;
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
        
        /* ===== 警告框與訊息框 ===== */
        .stAlert {
            background: rgba(26, 31, 46, 0.9) !important;
            border-radius: 10px !important;
            border-left: 4px solid !important;
            padding: 1rem 1.25rem !important;
            backdrop-filter: blur(10px);
            animation: fadeIn 0.3s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Success 樣式 */
        [data-baseweb="notification"][kind="success"] {
            background: rgba(102, 187, 106, 0.15) !important;
            border-left-color: #66BB6A !important;
        }
        
        /* Info 樣式 */
        [data-baseweb="notification"][kind="info"] {
            background: rgba(66, 165, 245, 0.15) !important;
            border-left-color: #42A5F5 !important;
        }
        
        /* Warning 樣式 */
        [data-baseweb="notification"][kind="warning"] {
            background: rgba(255, 183, 77, 0.15) !important;
            border-left-color: #FFB74D !important;
        }
        
        /* Error 樣式 */
        [data-baseweb="notification"][kind="error"] {
            background: rgba(239, 83, 80, 0.15) !important;
            border-left-color: #EF5350 !important;
        }
        
        div[data-baseweb="notification"] {
            background: rgba(26, 31, 46, 0.9) !important;
            border-radius: 10px !important;
            backdrop-filter: blur(10px);
        }
        
        /* ===== 圖片容器 ===== */
        [data-testid="stImage"] {
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
            transition: transform 0.3s ease, box-shadow 0.3s ease !important;
        }
        
        [data-testid="stImage"]:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5) !important;
        }
        
        /* ===== 圖片對比容器樣式 ===== */
        [data-testid="column"] > div > div > div > h3 {
            text-align: center !important;
            padding: 0.875rem 0 !important;
            margin-bottom: 1.25rem !important;
            background: linear-gradient(135deg, rgba(26, 31, 46, 0.8), rgba(26, 31, 46, 0.6)) !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
            backdrop-filter: blur(10px);
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
        st.markdown("#### 🚀 v0.8.3 · Enhanced UI/UX")
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
        
        # 快速預設模式
        with st.expander("💡 快速預設（推薦新手）", expanded=False):
            st.markdown("""
            <p style='color: #B8B8B8; font-size: 0.875rem; margin-bottom: 0.75rem;'>
                選擇拍攝場景，自動配置最佳參數組合
            </p>
            """, unsafe_allow_html=True)
            
            preset_choice = st.radio(
                "選擇場景預設",
                ["自定義", "👤 人像模式", "🏞️ 風景模式", "🚶 街拍模式", "🎬 電影風格"],
                index=0,
                help=(
                    "**人像模式**: Portra400 + 柔和顆粒 + 自然膚色\n\n"
                    "**風景模式**: Velvia50 + 無顆粒 + 高飽和度\n\n"
                    "**街拍模式**: TriX400 + 默認顆粒 + 高對比黑白\n\n"
                    "**電影風格**: Cinestill800T + 較粗顆粒 + 藝術光暈"
                ),
                key="preset_choice"
            )
            
            # 預設配置對照表（稍後會用到）
            preset_configs = {
                "👤 人像模式": {
                    "film_type": "Portra400_MediumPhysics_Mie",
                    "processing_quality": "物理模式（快速）",
                    "grain_style": "柔和",
                    "tone_style": "filmic",
                    "bloom_mode": "physical",
                    "bloom_threshold": 0.85
                },
                "🏞️ 風景模式": {
                    "film_type": "Velvia50_Mie",
                    "processing_quality": "物理模式（快速）",
                    "grain_style": "不使用",
                    "tone_style": "filmic",
                    "bloom_mode": "physical",
                    "bloom_threshold": 0.80
                },
                "🚶 街拍模式": {
                    "film_type": "TriX400",
                    "processing_quality": "經驗公式（快速）",
                    "grain_style": "默認",
                    "tone_style": "reinhard",
                    "bloom_mode": "artistic",
                    "bloom_threshold": 0.75
                },
                "🎬 電影風格": {
                    "film_type": "Cinestill800T_Mie",
                    "processing_quality": "物理模式（快速）",
                    "grain_style": "較粗",
                    "tone_style": "filmic",
                    "bloom_mode": "artistic",
                    "bloom_threshold": 0.70
                }
            }
            
            # 如果選擇了預設，顯示配置
            if preset_choice != "自定義":
                config = preset_configs[preset_choice]
                st.success(f"""
**已套用預設**: {preset_choice}
- 底片: {config['film_type']}
- 處理模式: {config['processing_quality']}
- 顆粒: {config['grain_style']}
- 曲線: {config['tone_style']}
                """)
        
        # 處理模式選擇（三選項）
        # 根據快速預設決定預設值
        preset_configs = {
            "👤 人像模式": {
                "film_type": "Portra400_MediumPhysics_Mie",
                "processing_quality": "物理模式（快速）",
                "grain_style": "柔和",
                "tone_style": "filmic",
                "bloom_mode": "physical",
                "bloom_threshold": 0.85
            },
            "🏞️ 風景模式": {
                "film_type": "Velvia50_Mie",
                "processing_quality": "物理模式（快速）",
                "grain_style": "不使用",
                "tone_style": "filmic",
                "bloom_mode": "physical",
                "bloom_threshold": 0.80
            },
            "🚶 街拍模式": {
                "film_type": "TriX400",
                "processing_quality": "經驗公式（快速）",
                "grain_style": "默認",
                "tone_style": "reinhard",
                "bloom_mode": "artistic",
                "bloom_threshold": 0.75
            },
            "🎬 電影風格": {
                "film_type": "Cinestill800T_Mie",
                "processing_quality": "物理模式（快速）",
                "grain_style": "較粗",
                "tone_style": "filmic",
                "bloom_mode": "artistic",
                "bloom_threshold": 0.70
            }
        }
        
        # 從 session_state 讀取預設配置（如果存在）
        active_preset = st.session_state.get('preset_choice', '自定義')
        preset_config = preset_configs.get(active_preset, {})
        
        # 設定預設索引
        if preset_config and 'processing_quality' in preset_config:
            quality_options = ["經驗公式（快速）", "物理模式（快速）", "物理完整（光譜）"]
            default_quality_index = quality_options.index(preset_config['processing_quality']) if preset_config['processing_quality'] in quality_options else 0
        else:
            default_quality_index = 0
        
        processing_quality = st.selectbox(
            "處理模式:",
            ["經驗公式（快速）", "物理模式（快速）", "物理完整（光譜）"],
            index=default_quality_index,
            help=(
                "**經驗公式（快速）**: 基於經驗公式的快速處理，速度最快（~1-2秒）\n\n"
                "**物理模式（快速）**: 物理準確 + Mie 散射，速度較快（~2-5秒）\n\n"
                "**物理完整（光譜）**: 31 通道光譜 + 膠片敏感度曲線，最準確（~5-10秒）"
            )
        )
        
        # 根據處理模式顯示對應的底片清單
        if processing_quality == "經驗公式（快速）":
            # 經驗公式模式：基礎底片（不含後綴）
            film_options = [
                "NC200", "Portra400", "Ektar100", "Gold200", "ProImage100", "Superia400",
                "AS100", "HP5Plus400", "TriX400", "FP4Plus125", "FS200",
                "Velvia50", "Provia100F", "Cinestill800T"
            ]
            film_help_text = (
                "🎨 經驗公式模式\n"
                "• 3×3 矩陣色彩轉換\n"
                "• 經驗光學效果公式\n"
                "• 處理速度：~1-2 秒\n"
                "• 適合：快速預覽、批量處理"
            )
        elif processing_quality == "物理模式（快速）":
            # 物理快速模式：帶 _Mie 或 _MediumPhysics 後綴
            film_options = [
                "NC200_Mie", "Portra400_MediumPhysics_Mie", "Ektar100_Mie", 
                "Gold200_Mie", "ProImage100_Mie", "Superia400_Mie",
                "Cinestill800T_Mie", "Velvia50_Mie"
            ]
            film_help_text = (
                "🔬 物理模式（快速）\n"
                "• Mie 散射理論（查表優化）\n"
                "• 波長依賴光學效果\n"
                "• 處理速度：~2-5 秒\n"
                "• 適合：高品質輸出、專業用途"
            )
        else:  # 物理完整（光譜）
            # 光譜模式：與快速版相同底片，但啟用光譜處理
            film_options = [
                "NC200", "Portra400", "Ektar100", "Gold200", "ProImage100", "Superia400",
                "C400", "UltraMax400", "Business100",
                "AS100", "HP5Plus400", "TriX400", "FP4Plus125", "FS200",
                "Velvia50", "Provia100F", "Cinestill800T"
            ]
            film_help_text = (
                "🌈 物理完整（光譜）\n"
                "• 31 通道光譜重建（380-770nm）\n"
                "• 真實膠片敏感度曲線\n"
                "• 處理速度：~5-10 秒\n"
                "• 適合：極致色彩準確度、研究用途"
            )
        
        # 胶片類型選擇（根據預設決定 index）
        default_film_index = 0
        if preset_config and 'film_type' in preset_config:
            try:
                default_film_index = film_options.index(preset_config['film_type'])
            except ValueError:
                default_film_index = 0
        
        film_type = st.selectbox(
            "請選擇膠片:",
            film_options,
            index=default_film_index,
            help=film_help_text
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
            <div style='background: linear-gradient(135deg, rgba(26, 31, 46, 0.8), rgba(26, 31, 46, 0.5)); 
                        padding: 1.25rem; 
                        border-radius: 12px; 
                        border-left: 4px solid #FF6B6B;
                        margin-top: 0.75rem;
                        margin-bottom: 1.25rem;
                        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
                        transition: all 0.3s ease;'
                        onmouseover="this.style.borderLeftColor='#FF8E8E'; this.style.boxShadow='0 6px 20px rgba(255, 107, 107, 0.2)';"
                        onmouseout="this.style.borderLeftColor='#FF6B6B'; this.style.boxShadow='0 4px 16px rgba(0, 0, 0, 0.3)';">
                <p style='color: #FF8E8E; font-weight: 700; font-size: 1.1rem; margin: 0 0 0.35rem 0; letter-spacing: 0.5px;'>
                    {display_name}
                </p>
                <p style='color: #B8B8B8; font-size: 0.875rem; margin: 0 0 1rem 0; display: flex; align-items: center; gap: 0.5rem;'>
                    <span style='background: rgba(255, 107, 107, 0.2); padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 500;'>{brand}</span>
                    <span>·</span>
                    <span>{film_type_label}</span>
                    <span>·</span>
                    <span style='font-weight: 600; color: #FFB74D;'>{iso}</span>
                </p>
                <p style='color: #E8E8E8; font-size: 0.925rem; line-height: 1.6; margin: 0 0 1rem 0;'>
                    {description}
                </p>
                <div style='display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.75rem;'>
                    {''.join([f"<span style='background: rgba(255, 107, 107, 0.2); color: #FFB4B4; padding: 0.35rem 0.65rem; border-radius: 6px; font-size: 0.8rem; font-weight: 500; border: 1px solid rgba(255, 107, 107, 0.3);'>{feature}</span>" for feature in features])}
                </div>
                <p style='color: #999; font-size: 0.825rem; margin: 0; display: flex; align-items: center; gap: 0.35rem;'>
                    <span style='font-size: 1rem;'>💡</span> 適用場景：<span style='color: #B8B8B8; font-weight: 500;'>{best_for}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)

        # 光譜模式專屬設定（僅在選擇「物理完整」時顯示）
        illuminant_choice = None  # 預設值
        if processing_quality == "物理完整（光譜）":
            st.markdown("#### 🌈 光譜處理設定")
            
            # 光源選擇
            illuminant_choice = st.selectbox(
                "光源類型",
                ["平坦光源（Flat）", "D65 標準日光"],
                index=0,
                help=(
                    "**平坦光源**: 所有波長均勻，適合一般用途\n\n"
                    "**D65 日光**: CIE 標準日光（6504K），適合戶外日光拍攝"
                ),
                key="spectrum_illuminant"
            )
            
            st.info(f"""
📐 **處理流程**: RGB → 31-ch Spectrum (380-770nm) → Film Sensitivity → RGB

⏱️ **預計時間**: 5-10 秒（取決於影像大小）

✅ **物理正確**: 往返誤差 <3%、能量守恆 <0.01%
            """)

        # 顆粒度選擇（根據預設決定 index）
        grain_options = ["不使用", "柔和", "默認", "較粗"]
        default_grain_index = 0
        if preset_config and 'grain_style' in preset_config:
            try:
                default_grain_index = grain_options.index(preset_config['grain_style'])
            except ValueError:
                default_grain_index = 0
        
        grain_style = st.selectbox(
            "胶片顆粒度：",
            grain_options,
            index=default_grain_index,
            help="選擇胶片的顆粒度",
        )
        
        # 曲線映射選擇（根據預設決定 index）
        tone_options = ["filmic", "reinhard"]
        default_tone_index = 0
        if preset_config and 'tone_style' in preset_config:
            try:
                default_tone_index = tone_options.index(preset_config['tone_style'])
            except ValueError:
                default_tone_index = 0
        
        tone_style = st.selectbox(
            "曲線映射：",
            tone_options,
            index=default_tone_index,
            help='''選擇Tone mapping方式:
            
            目前版本下Reinhard模型似乎表現出更好的動態範圍，
            filmic模型尚不夠完善,但對肩部趾部有更符合目標的刻畫'''
        )

        st.success(f"已選擇胶片: {film_type}")
        
        # 一鍵重置按鈕
        col_reset1, col_reset2 = st.columns([1, 1])
        with col_reset1:
            if st.button("🔄 重置所有參數", use_container_width=True, help="恢復所有參數到預設值"):
                # 清除 session_state 中的預設選擇
                if 'preset_choice' in st.session_state:
                    del st.session_state['preset_choice']
                st.rerun()
        with col_reset2:
            if st.button("ℹ️ 查看當前配置", use_container_width=True, help="顯示當前所有參數設定"):
                st.session_state['show_config_summary'] = True
        
        # 顯示配置摘要（如果使用者點擊了按鈕）
        if st.session_state.get('show_config_summary', False):
            with st.expander("📋 當前配置摘要", expanded=True):
                st.markdown(f"""
                **底片設定**:
                - 處理模式: {processing_quality}
                - 底片類型: {film_type}
                - 顆粒度: {grain_style}
                - 曲線映射: {tone_style}
                
                **快速預設**: {st.session_state.get('preset_choice', '自定義')}
                """)
                if st.button("關閉", key="close_config"):
                    st.session_state['show_config_summary'] = False
                    st.rerun()
        
        st.divider()
        
        # 物理模式設定（傳入 processing_quality、film_type 和 illuminant_choice）
        physics_mode, physics_params = _render_physics_settings(processing_quality, film_type, illuminant_choice)
        
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


def _render_physics_settings(processing_quality: str, film_type: str, illuminant_choice: Optional[str] = None) -> Tuple[PhysicsMode, Dict[str, Any]]:
    """
    渲染物理模式設定區塊（v0.7.0: 固定使用 PHYSICAL 模式）
    
    Args:
        processing_quality: 處理模式選擇（"經驗公式（快速）", "物理模式（快速）", "物理完整（光譜）"）
        film_type: 膠片類型
        illuminant_choice: 光源選擇（僅光譜模式使用）
    """
    st.markdown("### ⚙️ 物理參數")
    
    # v0.7.0: 固定使用 PHYSICAL 模式
    physics_mode = PhysicsMode.PHYSICAL
    st.info("🔬 **物理模式**: 能量守恆、H&D曲線、泊松顆粒")
    
    # 進階物理參數
    physics_params = {}
    
    # 從 session_state 讀取預設配置（如果存在）
    active_preset = st.session_state.get('preset_choice', '自定義')
    preset_configs = {
        "👤 人像模式": {"bloom_mode": "physical", "bloom_threshold": 0.85},
        "🏞️ 風景模式": {"bloom_mode": "physical", "bloom_threshold": 0.80},
        "🚶 街拍模式": {"bloom_mode": "artistic", "bloom_threshold": 0.75},
        "🎬 電影風格": {"bloom_mode": "artistic", "bloom_threshold": 0.70}
    }
    preset_config = preset_configs.get(active_preset, {})
    
    st.markdown("---")
    
    # Bloom 參數（套用預設值）
    with st.expander("📊 Bloom（光暈）參數", expanded=False):
        default_bloom_mode_index = 1  # 預設 physical
        if preset_config and 'bloom_mode' in preset_config:
            default_bloom_mode_index = 0 if preset_config['bloom_mode'] == 'artistic' else 1
        
        bloom_mode = st.radio(
            "Bloom 模式",
            ["artistic", "physical"],
            index=default_bloom_mode_index,
            help="artistic: 可增加能量（視覺導向）\nphysical: 能量守恆（物理準確）",
            key="bloom_mode"
        )
        
        default_bloom_threshold = preset_config.get('bloom_threshold', 0.8)
        bloom_threshold = st.slider(
            "高光閾值 (Threshold)",
            min_value=0.5,
            max_value=0.95,
            value=default_bloom_threshold,
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
            index=1,  # 預設 poisson (物理模式)
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
    
    # 根據處理模式自動配置光譜參數
    if processing_quality == "物理完整（光譜）":
        # 啟用光譜模式
        physics_params['use_film_spectra'] = True
        
        # 膠片光譜名稱映射（移除後綴）
        film_base_name = film_type.replace("_Mie", "").replace("_MediumPhysics", "")
        
        # 映射到支援的光譜膠片（如果不支援則使用預設）
        spectra_mapping = {
            "Portra400": "Portra400",
            "Velvia50": "Velvia50",
            "Cinestill800T": "Cinestill800T",
            "HP5Plus400": "HP5Plus400",
        }
        physics_params['film_spectra_name'] = spectra_mapping.get(film_base_name, "Portra400")
        
        # 光源配置
        physics_params['film_illuminant'] = "D65" if illuminant_choice and "D65" in illuminant_choice else "flat"
    else:
        # 非光譜模式：禁用光譜處理
        physics_params['use_film_spectra'] = False
        physics_params['film_spectra_name'] = 'Portra400'
        physics_params['film_illuminant'] = 'flat'
    
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
                               physics_mode: PhysicsMode, output_path: str, 
                               original_image: np.ndarray = None):
    """
    顯示單張圖片處理結果（左右對比顯示 + 詳細統計）
    
    Args:
        film_image: 處理後的圖像（BGR 格式）
        process_time: 處理時間（秒）
        physics_mode: 使用的物理模式
        output_path: 輸出檔案名稱
        original_image: 原始圖像（BGR 格式，可選）
    """
    # 轉換 BGR 到 RGB
    film_rgb = cv2.cvtColor(film_image, cv2.COLOR_BGR2RGB)
    
    # 如果有原始圖片，顯示左右對比
    if original_image is not None:
        original_rgb = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
        
        # 創建兩列布局
        col1, col2 = st.columns(2, gap="medium")
        
        with col1:
            st.markdown("### 📸 原始照片")
            st.image(original_rgb, channels="RGB", width="stretch")
            
            # 原始圖像統計
            orig_h, orig_w = original_rgb.shape[:2]
            orig_size_mb = (original_rgb.nbytes / 1024 / 1024)
            with st.expander("📊 原始圖像資訊", expanded=False):
                st.markdown(f"""
                - **解析度**: {orig_w} × {orig_h} px
                - **總像素**: {orig_w * orig_h:,} px
                - **記憶體大小**: {orig_size_mb:.2f} MB
                - **平均亮度**: {original_rgb.mean():.1f} / 255
                """)
        
        with col2:
            st.markdown("### 🎞️ 底片效果")
            st.image(film_rgb, channels="RGB", width="stretch")
            
            # 處理後圖像統計
            film_h, film_w = film_rgb.shape[:2]
            film_size_mb = (film_rgb.nbytes / 1024 / 1024)
            with st.expander("📊 處理後圖像資訊", expanded=False):
                st.markdown(f"""
                - **解析度**: {film_w} × {film_h} px
                - **總像素**: {film_w * film_h:,} px
                - **記憶體大小**: {film_size_mb:.2f} MB
                - **平均亮度**: {film_rgb.mean():.1f} / 255
                - **亮度變化**: {((film_rgb.mean() - original_rgb.mean()) / original_rgb.mean() * 100):+.1f}%
                """)
    else:
        # 無原始圖片時，單獨顯示結果（向後相容）
        st.image(film_rgb, channels="RGB", width=800)
    
    # 顯示處理統計（美化版本）
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(102, 187, 106, 0.15), rgba(102, 187, 106, 0.08)); 
                padding: 1.25rem; 
                border-radius: 12px; 
                border-left: 4px solid #66BB6A;
                margin: 1.5rem 0;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);'>
        <p style='color: #66BB6A; font-weight: 700; font-size: 1.15rem; margin: 0 0 0.75rem 0; display: flex; align-items: center; gap: 0.5rem;'>
            ✨ 底片顯影完成！
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 處理統計資訊（用卡片呈現）
    stat_col1, stat_col2, stat_col3 = st.columns(3, gap="small")
    
    with stat_col1:
        st.markdown(f"""
        <div style='background: rgba(26, 31, 46, 0.8); padding: 1rem; border-radius: 10px; text-align: center; border: 1px solid rgba(255, 107, 107, 0.2);'>
            <p style='color: #FFB74D; font-size: 0.8rem; margin: 0 0 0.25rem 0; font-weight: 600;'>⏱️ 處理時間</p>
            <p style='color: #FFF; font-size: 1.5rem; font-weight: 700; margin: 0;'>{process_time:.2f}s</p>
        </div>
        """, unsafe_allow_html=True)
    
    with stat_col2:
        st.markdown(f"""
        <div style='background: rgba(26, 31, 46, 0.8); padding: 1rem; border-radius: 10px; text-align: center; border: 1px solid rgba(66, 165, 245, 0.2);'>
            <p style='color: #42A5F5; font-size: 0.8rem; margin: 0 0 0.25rem 0; font-weight: 600;'>🔬 物理模式</p>
            <p style='color: #FFF; font-size: 1.2rem; font-weight: 700; margin: 0;'>{physics_mode.name}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with stat_col3:
        if original_image is not None:
            file_size_kb = len(cv2.imencode('.jpg', film_image, [cv2.IMWRITE_JPEG_QUALITY, 95])[1]) / 1024
            st.markdown(f"""
            <div style='background: rgba(26, 31, 46, 0.8); padding: 1rem; border-radius: 10px; text-align: center; border: 1px solid rgba(102, 187, 106, 0.2);'>
                <p style='color: #66BB6A; font-size: 0.8rem; margin: 0 0 0.25rem 0; font-weight: 600;'>💾 檔案大小</p>
                <p style='color: #FFF; font-size: 1.3rem; font-weight: 700; margin: 0;'>{file_size_kb:.1f} KB</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: rgba(26, 31, 46, 0.8); padding: 1rem; border-radius: 10px; text-align: center; border: 1px solid rgba(102, 187, 106, 0.2);'>
                <p style='color: #66BB6A; font-size: 0.8rem; margin: 0 0 0.25rem 0; font-weight: 600;'>💾 品質</p>
                <p style='color: #FFF; font-size: 1.3rem; font-weight: 700; margin: 0;'>JPEG 95</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 下載按鈕
    film_pil = Image.fromarray(film_rgb)
    buf = io.BytesIO()
    film_pil.save(buf, format="JPEG", quality=95)
    byte_im = buf.getvalue()
    
    st.download_button(
        label="📥 下載高清圖像",
        data=byte_im,
        file_name=output_path,
        mime="image/jpeg",
        use_container_width=True
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
                    film_illuminant=proc_settings.get('film_illuminant', 'flat'),
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
                # 美化版成功訊息
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, rgba(102, 187, 106, 0.2), rgba(102, 187, 106, 0.1)); 
                            padding: 1.5rem; 
                            border-radius: 12px; 
                            border-left: 4px solid #66BB6A;
                            margin: 1.5rem 0;
                            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);'>
                    <p style='color: #66BB6A; font-weight: 700; font-size: 1.2rem; margin: 0 0 0.5rem 0;'>
                        ✅ 批量處理完成！
                    </p>
                    <p style='color: #E8E8E8; font-size: 1rem; margin: 0;'>
                        成功處理 <strong style='color: #66BB6A;'>{success_count}</strong> / {len(results)} 張照片
                        · 總用時 <strong style='color: #FFB74D;'>{total_time:.2f}</strong> 秒
                        · 平均 <strong style='color: #42A5F5;'>{total_time/success_count:.2f}</strong> 秒/張
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
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
