import os
import io
import base64
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu
import bot_hioki

def get_pln_logo_src():
    local_path = os.path.join(os.path.dirname(__file__), "logo_pln.png")
    if os.path.exists(local_path):
        try:
            with open(local_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{b64}"
        except Exception:
            pass
    return "https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Logo_PLN.png/500px-Logo_PLN.png"

# ==========================================
# 1. PAGE CONFIGURATION & CORPORATE BRANDING
# ==========================================
st.set_page_config(
    page_title="Management Trafo ULP MOA",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. CUSTOM ENTERPRISE CSS THEME (PLN STYLE)
# ==========================================
st.markdown("""
    <style>
        /* Force Mandatory Light Mode Across All Browsers & Devices */
        :root {
            color-scheme: light !important;
        }

        [data-testid="stAppViewContainer"],
        .stApp {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
        }

        [data-testid="stSidebar"] {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
        }

        /* Base Container Settings - Reduced top padding to eliminate blank space */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }

        /* 1. Eliminate the top white header bar completely */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            background: transparent !important;
            border-bottom: none !important;
            box-shadow: none !important;
            height: 3.5rem !important;
            pointer-events: none !important; /* Allow clicks to pass through empty transparent area */
            z-index: 99999 !important;
        }

        /* 2. Re-enable pointer events for interactive elements in the header */
        header[data-testid="stHeader"] * {
            pointer-events: auto !important;
        }

        /* 3. Keep toolbar transparent and active so stExpandSidebarButton works */
        [data-testid="stToolbar"] {
            background: transparent !important;
            background-color: transparent !important;
            display: flex !important;
            visibility: visible !important;
            pointer-events: auto !important;
        }

        /* 4. Hide ONLY Deploy button, hamburger menu, and status widget */
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"],
        [data-testid="stStatusWidget"],
        .stAppDeployButton,
        #MainMenu {
            display: none !important;
            visibility: hidden !important;
        }

        /* 5. Hide the top colored decoration line */
        [data-testid="stDecoration"] {
            display: none !important;
            height: 0px !important;
        }

        /* 6. Ensure the button to hide and unhide the left menu is ALWAYS visible and functional */
        [data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="collapsedControl"] {
            display: inline-flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 9999999 !important;
        }

        /* Prominent styled button when the left menu is collapsed (unhide button) */
        [data-testid="stExpandSidebarButton"] {
            position: fixed !important;
            top: 0.6rem !important;
            left: 0.8rem !important;
            background: #FFFFFF !important;
            border: 1.5px solid #0072BC !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 12px rgba(0, 114, 188, 0.25) !important;
            padding: 2px 4px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }

        [data-testid="stExpandSidebarButton"]:hover {
            background: #0072BC !important;
            box-shadow: 0 6px 16px rgba(0, 114, 188, 0.4) !important;
            transform: scale(1.05) !important;
        }

        [data-testid="stExpandSidebarButton"] button {
            background: transparent !important;
            border: none !important;
            color: #0072BC !important;
            padding: 4px !important;
        }

        [data-testid="stExpandSidebarButton"]:hover button {
            color: #FFFFFF !important;
        }

        [data-testid="stExpandSidebarButton"] svg,
        [data-testid="stSidebarCollapseButton"] svg {
            fill: currentColor !important;
            color: inherit !important;
        }

        /* Collapse button inside sidebar */
        [data-testid="stSidebarCollapseButton"] button {
            color: #0072BC !important;
            border-radius: 6px !important;
        }

        [data-testid="stSidebarCollapseButton"] button:hover {
            background-color: rgba(0, 114, 188, 0.1) !important;
        }
        
        /* Corporate Color Palette Constants */
        :root {
            --pln-blue-primary: #0072BC;
            --pln-blue-dark: #0A3D62;
            --pln-cyan: #00A2E8;
            --pln-yellow: #FDB913;
            --pln-yellow-glow: #FFEAA7;
            --pln-red: #E74C3C;
            --pln-green: #2ECC71;
            --pln-slate-bg: #F8FAFC;
            --pln-card-border: #E2E8F0;
        }

        /* Top Header Banner */
        .pln-header-container {
            background: linear-gradient(135deg, #0A3D62 0%, #0072BC 70%, #00A2E8 100%);
            border-radius: 14px;
            padding: 22px 28px;
            color: white;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(10, 61, 98, 0.15);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .pln-header-title {
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .pln-header-subtitle {
            font-size: 13px;
            font-weight: 400;
            opacity: 0.88;
            margin-top: 4px;
            letter-spacing: 0.2px;
        }
        .pln-badge-status {
            background-color: rgba(255, 255, 255, 0.16);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.25);
            color: #FFFFFF;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        /* Modern Metric Card */
        .kpi-card {
            background: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            border-left: 5px solid #0072BC;
            padding: 16px 20px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
            margin-bottom: 12px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
        }
        .kpi-card-danger { border-left-color: #EF4444; }
        .kpi-card-warning { border-left-color: #F59E0B; }
        .kpi-card-success { border-left-color: #10B981; }
        .kpi-card-info { border-left-color: #3B82F6; }
        
        .kpi-title {
            font-size: 13px;
            font-weight: 600;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }
        .kpi-value {
            font-size: 30px;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.1;
        }
        .kpi-desc {
            font-size: 12px;
            color: #64748B;
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Asset Information Card */
        .asset-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.03);
            margin-bottom: 16px;
        }

        /* Status Pills */
        .status-pill {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
            text-align: center;
        }
        .pill-success { background-color: #DCFCE7; color: #15803D; }
        .pill-warning { background-color: #FEF3C7; color: #B45309; }
        .pill-danger { background-color: #FEE2E2; color: #B91C1C; }
        .pill-muted { background-color: #F1F5F9; color: #475569; }

        /* Clean Section Headers */
        .section-header {
            font-size: 20px;
            font-weight: 700;
            color: #0F172A;
            margin-top: 10px;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Custom Table & Dataframe tweaks */
        .stDataFrame {
            border-radius: 8px;
            overflow: hidden;
        }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 3. GOOGLE SHEETS AUTHENTICATION & DATA ENGINE
# ==========================================
def get_google_credentials():
    """Retrieve Google credentials from Streamlit Secrets or local credentials.json."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" in st.secrets:
        return Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    elif os.path.exists("credentials.json"):
        return Credentials.from_service_account_file("credentials.json", scopes=scopes)
    else:
        raise FileNotFoundError("Google credentials not found in st.secrets or credentials.json.")

@st.cache_data(ttl=120)
def load_all_transformer_data():
    """
    Load and blend RAW_MEA (measurements) and INFO_DATA (static database) from Google Sheets.
    Applies complete electrical engineering calculations (Unbalance %, Load %, Health Score, ALA adders).
    """
    try:
        credentials = get_google_credentials()
        gc = gspread.authorize(credentials)
        sh = gc.open("DATA TRAFO")

        # 1. Fetch RAW_MEA (Hioki Measurements)
        raw_ws = sh.worksheet("RAW_MEA")
        raw_records = raw_ws.get_all_records()
        df_raw = pd.DataFrame(raw_records)

        # 2. Fetch INFO_DATA (Static Database)
        info_ws = sh.worksheet("INFO_DATA")
        info_records = info_ws.get_all_records()
        df_info = pd.DataFrame(info_records)

        if df_info.empty:
            st.error("Sheet INFO_DATA kosong atau tidak dapat diakses.")
            return pd.DataFrame(), pd.DataFrame()

        # Clean TF_Code
        df_info['TF_Code'] = df_info['TF_Code'].astype(str).str.strip()

        # Deduplicate RAW_MEA to isolate the latest measurement per transformer
        if not df_raw.empty:
            df_raw['TF_Code'] = df_raw['TF_Code'].astype(str).str.strip()
            df_raw['Parsed_Timestamp'] = pd.to_datetime(
                df_raw['Date'].astype(str) + ' ' + df_raw['Time'].astype(str),
                errors='coerce'
            )
            df_raw_sorted = df_raw.sort_values(by='Parsed_Timestamp', ascending=True)
            df_raw_latest = df_raw_sorted.drop_duplicates(subset=['TF_Code'], keep='last').copy()
        else:
            df_raw_latest = pd.DataFrame()

        # Merge Static info with latest measurements
        df = pd.merge(df_info, df_raw_latest, on="TF_Code", how="left")
        df = df.dropna(subset=['TF_Name']).copy()

        # Parse and clean coordinates
        if 'TF_Coordinate' in df.columns:
            coords = df['TF_Coordinate'].astype(str).str.split(',', expand=True)
            df['latitude'] = pd.to_numeric(coords[0].str.strip(), errors='coerce')
            df['longitude'] = pd.to_numeric(coords[1].str.strip(), errors='coerce')
        else:
            df['latitude'] = np.nan
            df['longitude'] = np.nan

        # Parse measurement date and status
        df['Parsed_Date'] = pd.to_datetime(df['Date'], errors='coerce')
        today = pd.to_datetime('today')
        six_months_ago = today - pd.DateOffset(months=6)

        df['Is_Measured'] = df['Date'].notna() & (df['Date'].astype(str).str.strip() != '')
        df['Days_Since_Measurement'] = (today - df['Parsed_Date']).dt.days
        df['Months_Since_Measurement'] = (df['Days_Since_Measurement'] / 30.4375).round(1)

        df['Measurement_Status'] = np.where(
            ~df['Is_Measured'],
            'Belum Diukur',
            np.where(df['Parsed_Date'] < six_months_ago, 'Perlu Ukur Ulang', 'Terkini')
        )

        # Apply ALA (Arus Lebih Awal / Akumulasi Yanbung) to Current columns
        current_columns = [
            'A_R_P', 'A_S_P', 'A_T_P', 'A_N_P',
            'A_R_1', 'A_S_1', 'A_T_1', 'A_N_1',
            'A_R_2', 'A_S_2', 'A_T_2', 'A_N_2',
            'A_R_3', 'A_S_3', 'A_T_3', 'A_N_3'
        ]
        for col in current_columns:
            ala_col = f"ALA_{col[2:]}" if len(col) > 2 else ""
            if col in df.columns and ala_col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) + pd.to_numeric(df[ala_col], errors='coerce').fillna(0)
            elif col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Standardize voltage columns
        voltage_cols = ['V_RN', 'V_SN', 'V_TN', 'V_RS', 'V_RT', 'V_ST']
        for col in voltage_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Standardize transformer capacity and phase
        df['TF_MLoad'] = pd.to_numeric(df['TF_MLoad'], errors='coerce').fillna(0)
        df['TF_Phase'] = pd.to_numeric(df['TF_Phase'], errors='coerce').fillna(3).astype(int)

        # -------------------------------------------------------------
        # 3. ELECTRICAL CALCULATIONS (Standard PLN & IEEE)
        # -------------------------------------------------------------
        # Load (kVA)
        # S (kVA) = (V_RN * I_R + V_SN * I_S + V_TN * I_T) / 1000
        # If Phase-to-Neutral voltages are missing, fallback to 230V standard.
        df['Current Load'] = np.where(
            df['Is_Measured'],
            (((df['V_RN'].fillna(230) * df['A_R_P']) + 
              (df['V_SN'].fillna(230) * df['A_S_P']) + 
              (df['V_TN'].fillna(230) * df['A_T_P'])) / 1000).round(2),
            np.nan
        )

        df['Load Percentage'] = np.where(
            df['Is_Measured'] & (df['TF_MLoad'] > 0),
            ((df['Current Load'] / df['TF_MLoad']) * 100).round(1),
            np.nan
        )

        df['Load_Status'] = np.where(
            ~df['Is_Measured'],
            'Belum Diukur',
            np.where(
                df['Load Percentage'] > 80,
                'Overload (>80%)',
                np.where(df['Load Percentage'] >= 40, 'Normal (40-80%)', 'Underload (<40%)')
            )
        )

        # Phase Unbalance (%)
        # IEEE/PLN Formula: Max_Deviation_from_Average / Average_Current * 100
        # Only applicable for 3-Phase units
        df['Avg_Current'] = np.where(
            df['Is_Measured'],
            (df['A_R_P'] + df['A_S_P'] + df['A_T_P']) / 3,
            np.nan
        )
        df['Dev_R'] = abs(df['A_R_P'] - df['Avg_Current'])
        df['Dev_S'] = abs(df['A_S_P'] - df['Avg_Current'])
        df['Dev_T'] = abs(df['A_T_P'] - df['Avg_Current'])
        df['Max_Dev'] = df[['Dev_R', 'Dev_S', 'Dev_T']].max(axis=1)

        df['Unbalance (%)'] = np.where(
            df['Is_Measured'] & (df['TF_Phase'] != 1) & (df['Avg_Current'] > 0),
            ((df['Max_Dev'] / df['Avg_Current']) * 100).round(2),
            np.nan
        )

        df['Unbalance_Status'] = np.where(
            ~df['Is_Measured'],
            'Belum Diukur',
            np.where(
                df['TF_Phase'] == 1,
                '1-Fasa (N/A)',
                np.where(
                    df['Unbalance (%)'] > 20,
                    'Kritis (>20%)',
                    np.where(df['Unbalance (%)'] >= 10, 'Perhatian (10-20%)', 'Seimbang (<10%)')
                )
            )
        )

        # Harmonics & Health Score
        harm_cols = ['THD_R_P', 'H1_R_P', 'THD_S_P', 'H1_S_P', 'THD_T_P', 'H1_T_P']
        for col in harm_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df['H1_Total'] = df['H1_R_P'] + df['H1_S_P'] + df['H1_T_P']
        df['Weighted_THD'] = np.where(
            df['H1_Total'] > 0,
            ((df['THD_R_P'] * df['H1_R_P']) + (df['THD_S_P'] * df['H1_S_P']) + (df['THD_T_P'] * df['H1_T_P'])) / df['H1_Total'],
            0.0
        ).round(2)

        health_calc = 100 - ((df['Weighted_THD'] - 5).clip(lower=0) * 1.5)
        df['Health Score'] = np.where(
            df['Is_Measured'],
            np.clip(health_calc, 0, 100).fillna(100).astype(int),
            np.nan
        )

        # Order key columns in front
        priority_cols = [
            'TF_Code', 'TF_Name', 'TF_MLoad', 'TF_Phase', 'TF_Construction',
            'Measurement_Status', 'Load_Status', 'Load Percentage', 'Current Load',
            'Unbalance_Status', 'Unbalance (%)', 'Health Score', 'Date', 'Time',
            'A_R_P', 'A_S_P', 'A_T_P', 'A_N_P', 'V_RN', 'V_SN', 'V_TN', 'TF_Coordinate'
        ]
        priority_cols = [c for c in priority_cols if c in df.columns]
        other_cols = [c for c in df.columns if c not in priority_cols]
        df = df[priority_cols + other_cols]

        return df, df_raw

    except Exception as err:
        st.error(f"Gagal memuat data dari Google Sheets: {err}")
        return pd.DataFrame(), pd.DataFrame()

# Load data into session
df, df_raw_full = load_all_transformer_data()

# ==========================================
# 4. SIDEBAR NAVIGATION & SYSTEM MONITOR
# ==========================================
with st.sidebar:
    logo_src = get_pln_logo_src()
    st.markdown(f"""
        <div style='text-align: center; padding: 10px 0 14px 0;'>
            <div style='display: flex; justify-content: center; align-items: center; margin-bottom: 6px;'>
                <img src='{logo_src}' style='width: 58px; height: auto; object-fit: contain; filter: drop-shadow(0px 2px 5px rgba(0, 0, 0, 0.12));' alt='Logo PLN'>
            </div>
            <h2 style='margin: 4px 0 0 0; font-size: 19px; font-weight: 800; color: #0F172A;'>MANTRA MOA</h2>
            <div style='font-size: 11px; font-weight: 600; color: #0072BC; letter-spacing: 0.5px;'>PLN ULP MOA • UP3 SAUMLAKI</div>
            <div style='font-size: 10px; color: #64748B;'>Distribution Transformer Asset System</div>
        </div>
        <hr style='margin: 6px 0 16px 0; border: none; border-top: 1px solid #E2E8F0;'>
    """, unsafe_allow_html=True)

    menu_selection = option_menu(
        menu_title=None,
        options=[
            "📊 Dashboard Utama",
            "🔌 Simulasi Yanbung",
            "📥 Input Pengukuran Gardu",
            "📈 Riwayat & Dossier Trafo",
            "📋 Data Semua Trafo",
            "✏️ Edit Data Trafo"
        ],
        icons=None,
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"display": "none"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "4px 0px",
                "padding": "10px 14px",
                "border-radius": "8px",
                "font-weight": "500",
                "color": "#334155",
                "--hover-color": "#F1F5F9"
            },
            "nav-link-selected": {
                "background-color": "#0072BC",
                "color": "white",
                "font-weight": "700"
            }
        }
    )

    st.markdown("<hr style='margin: 20px 0 12px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    # Live Database Connection Card & Refresh Button
    st.markdown("""
        <div style='background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-bottom: 12px;'>
            <div style='font-size: 11px; font-weight: 700; color: #15803D; display: flex; align-items: center; gap: 6px;'>
                <span>●</span> Google Sheets Terhubung
            </div>
            <div style='font-size: 11px; color: #64748B; margin-top: 4px;'>
                <b>Master:</b> INFO_DATA<br>
                <b>Pengukuran:</b> RAW_MEA
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 Sinkronkan Data", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.rerun()

    st.caption("MANTRA MOA v2.5 Enterprise • PT PLN (Persero)")

if df.empty:
    st.warning("⚠️ Data gardu tidak tersedia. Silakan periksa kredensial atau koneksi internet Anda.")
    st.stop()


# ==========================================
# PAGE 1: DASHBOARD UTAMA
# ==========================================
if menu_selection == "📊 Dashboard Utama":

    # Top Executive Banner (Dashboard Utama only)
    st.markdown(f"""
        <div class='pln-header-container'>
            <div>
                <h1 class='pln-header-title'>⚡ MANTRA MOA</h1>
                <div class='pln-header-subtitle'>Monitoring & Analytics Network Transformer Assessment — PT PLN (Persero) ULP Moa</div>
            </div>
            <div class='pln-badge-status'>
                <span>📍 Wilayah Kerja Moa</span> • <span>{len(df)} Gardu Terdata</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Metric Pre-Calculations
    total_trafo = len(df)
    measured_df = df[df['Is_Measured']].copy()
    total_measured = len(measured_df)
    
    # SPLN Standard (6-Month Measurement Cycle) Calculations
    overdue_df = df[df['Measurement_Status'] == 'Perlu Ukur Ulang'].copy()
    overdue_count = len(overdue_df)
    unmeasured_df = df[df['Measurement_Status'] == 'Belum Diukur'].copy()
    unmeasured_count = len(unmeasured_df)
    need_measurement_df = df[df['Measurement_Status'] != 'Terkini'].copy()
    need_measurement_count = len(need_measurement_df)
    valid_spln_df = df[df['Measurement_Status'] == 'Terkini'].copy()
    valid_spln_count = len(valid_spln_df)
    
    overload_df = measured_df[measured_df['Load Percentage'] > 80]
    overload_count = len(overload_df)
    
    unbalanced_df = measured_df[measured_df['Unbalance (%)'] > 20]
    unbalanced_count = len(unbalanced_df)
    
    avg_load = measured_df['Load Percentage'].mean() if not measured_df.empty else 0.0
    avg_health = measured_df['Health Score'].mean() if not measured_df.empty else 100.0

    # Executive KPI Metric Cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    
    with kpi_col1:
        st.markdown(f"""
            <div class='kpi-card kpi-card-info'>
                <div class='kpi-title'>Total Gardu</div>
                <div class='kpi-value'>{total_trafo}</div>
                <div class='kpi-desc'>
                    <span>Portal: <b>{(df['TF_Construction'] == 'Portal').sum()}</b></span> • 
                    <span>Cantol: <b>{(df['TF_Construction'] == 'Cantol').sum()}</b></span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        st.markdown(f"""
            <div class='kpi-card kpi-card-danger'>
                <div class='kpi-title'>🔔 Pengukuran Trafo (SPLN)</div>
                <div class='kpi-value'>{need_measurement_count} <span style='font-size:13px; font-weight:700; color:#DC2626;'>Perlu Ukur</span></div>
                <div class='kpi-desc'>
                    <span style='color: #8B5CF6; font-weight:700;'>⏳ {overdue_count} Lewat 6 Bln</span> • 
                    <span style='color: #EF4444; font-weight:700;'>🔴 {unmeasured_count} Belum Diukur</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with kpi_col3:
        st.markdown(f"""
            <div class='kpi-card kpi-card-danger'>
                <div class='kpi-title'>Overload (>80%)</div>
                <div class='kpi-value'>{overload_count}</div>
                <div class='kpi-desc'>
                    <span style='color: #DC2626; font-weight:600;'>{round((overload_count/total_measured*100), 1) if total_measured else 0}% Gardu Terukur</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with kpi_col4:
        st.markdown(f"""
            <div class='kpi-card kpi-card-warning'>
                <div class='kpi-title'>Unbalance Kritis (>20%)</div>
                <div class='kpi-value'>{unbalanced_count}</div>
                <div class='kpi-desc'>
                    <span>Potensi Arus Netral Tinggi</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with kpi_col5:
        st.markdown(f"""
            <div class='kpi-card kpi-card-success'>
                <div class='kpi-title'>Rata-rata Pembebanan</div>
                <div class='kpi-value'>{avg_load:.1f}%</div>
                <div class='kpi-desc'>
                    <span>Skor Kesehatan: <b>{avg_health:.0f}/100</b></span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # GEOSPATIAL MAP SECTION
    # -------------------------------------------------------------
    col_map_hdr, col_map_flt, col_map_scope = st.columns([2, 1.3, 1])
    with col_map_hdr:
        st.markdown("<div class='section-header'>📍 Pemetaan Geografis Trafo Distribusi</div>", unsafe_allow_html=True)
    with col_map_flt:
        pilihan_filter_peta = st.selectbox(
            "Filter Status Peta:",
            [
                "Semua Kondisi Gardu",
                f"🔴 Belum Diukur ({unmeasured_count})",
                f"⏳ Lewat 6 Bulan SPLN ({overdue_count})",
                f"🚨 Overload & Kritis ({overload_count + unbalanced_count})",
                f"🟢 Terkini & Patuh SPLN ({valid_spln_count})"
            ],
            index=0
        )
    with col_map_scope:
        pilihan_fokus = st.selectbox(
            "Fokus Wilayah:",
            ["Pulau Moa (Pusat)", "Semua Wilayah MBD", "Pulau Kisar", "Pulau Wetar"],
            index=0
        )

    map_df = df.dropna(subset=['latitude', 'longitude']).copy()
    if not map_df.empty:
        # Define marker color based on condition (Red for unmeasured as prioritized risk)
        def get_map_status(row):
            if not row['Is_Measured']:
                return '🔴 Belum Diukur'
            elif row['Load Percentage'] > 80:
                return '🚨 Overload (>80%)'
            elif row['Measurement_Status'] == 'Perlu Ukur Ulang':
                return '🟣 Lewat 6 Bulan (>6 Bln SPLN)'
            elif row['Unbalance (%)'] > 20:
                return '🟠 Unbalance Kritis (>20%)'
            else:
                return '🟢 Terkini & Normal'

        map_df['Map_Status'] = map_df.apply(get_map_status, axis=1)

        # Apply Map Status Filter
        if "Lewat 6 Bulan SPLN" in pilihan_filter_peta:
            map_df = map_df[map_df['Measurement_Status'] == 'Perlu Ukur Ulang']
        elif "Belum Diukur" in pilihan_filter_peta:
            map_df = map_df[~map_df['Is_Measured']]
        elif "Overload & Kritis" in pilihan_filter_peta:
            map_df = map_df[(map_df['Load Percentage'] > 80) | (map_df['Unbalance (%)'] > 20)]
        elif "Terkini & Patuh SPLN" in pilihan_filter_peta:
            map_df = map_df[map_df['Measurement_Status'] == 'Terkini']

        # Interactive Plotly Mapbox Color Map
        color_map = {
            '🔴 Belum Diukur': '#EF4444',
            '🚨 Overload (>80%)': '#991B1B',
            '🟣 Lewat 6 Bulan (>6 Bln SPLN)': '#8B5CF6',
            '🟠 Unbalance Kritis (>20%)': '#F59E0B',
            '🟢 Terkini & Normal': '#10B981'
        }

        # Determine center and zoom coordinates based on chosen focus
        if pilihan_fokus == "Pulau Moa (Pusat)":
            map_center = dict(lat=-8.161, lon=127.847)
            map_zoom = 10.5
        elif pilihan_fokus == "Pulau Kisar":
            map_center = dict(lat=-8.055, lon=127.185)
            map_zoom = 11.2
        elif pilihan_fokus == "Pulau Wetar":
            map_center = dict(lat=-7.750, lon=126.350)
            map_zoom = 9.8
        else: # Semua Wilayah MBD
            map_center = dict(lat=-8.032, lon=127.950)
            map_zoom = 7.5

        try:
            hover_dict = {
                'TF_Code': True,
                'TF_MLoad': True,
                'Load Percentage': True,
                'Unbalance (%)': True,
                'Map_Status': True,
                'Date': True,
                'Months_Since_Measurement': True,
                'latitude': False,
                'longitude': False
            }

            if hasattr(px, 'scatter_map'):
                fig_map = px.scatter_map(
                    map_df,
                    lat='latitude',
                    lon='longitude',
                    hover_name='TF_Name',
                    hover_data=hover_dict,
                    color='Map_Status',
                    color_discrete_map=color_map,
                    center=map_center,
                    zoom=map_zoom,
                    map_style="open-street-map",
                    height=450
                )
                fig_map.update_traces(marker=dict(size=9, opacity=0.9))
                fig_map.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    map=dict(
                        center=map_center,
                        zoom=map_zoom,
                        style="open-street-map"
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=0.02,
                        xanchor="center",
                        x=0.5,
                        bgcolor="rgba(255, 255, 255, 0.9)"
                    )
                )
            else:
                fig_map = px.scatter_mapbox(
                    map_df,
                    lat='latitude',
                    lon='longitude',
                    hover_name='TF_Name',
                    hover_data=hover_dict,
                    color='Map_Status',
                    color_discrete_map=color_map,
                    center=map_center,
                    zoom=map_zoom,
                    mapbox_style="open-street-map",
                    height=450
                )
                fig_map.update_traces(marker=dict(size=9, opacity=0.9))
                fig_map.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    mapbox=dict(
                        center=map_center,
                        zoom=map_zoom,
                        style="open-street-map"
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=0.02,
                        xanchor="center",
                        x=0.5,
                        bgcolor="rgba(255, 255, 255, 0.9)"
                    )
                )
            st.plotly_chart(
                fig_map,
                use_container_width=True,
                config={'scrollZoom': True, 'displayModeBar': False}
            )
        except Exception as map_err:
            st.warning(f"⚠️ Peta tidak dapat dimuat: {map_err}")
    else:
        st.info("Koordinat gardu tidak valid untuk ditampilkan pada peta.")

    # -------------------------------------------------------------
    # DEEP ANALYTICS TABS
    # -------------------------------------------------------------
    st.markdown("<div class='section-header'>📊 Analisis Teknis & Operasional</div>", unsafe_allow_html=True)

    tab_load, tab_unbalance, tab_health, tab_priority = st.tabs([
        "⚡ Analisis Pembebanan (Load %)",
        "⚖️ Keseimbangan Fasa (Unbalance %)",
        "🏥 Kesehatan & Harmonisa (THD)",
        f"🚨 Kepatuhan Siklus SPLN ({need_measurement_count})"
    ])

    # TAB 1: PEMBEBANAN TRAFO
    with tab_load:
        col_t1_left, col_t1_right = st.columns([3, 2])
        
        with col_t1_left:
            st.markdown("##### 🏆 Top 10 Gardu dengan Pembebanan Tertinggi")
            if not measured_df.empty:
                top_load = measured_df.sort_values(by='Load Percentage', ascending=False).head(10)
                fig_bar_load = px.bar(
                    top_load,
                    x='TF_Name',
                    y='Load Percentage',
                    color='Load Percentage',
                    color_continuous_scale=['#10B981', '#F59E0B', '#EF4444'],
                    text='Load Percentage',
                    labels={'Load Percentage': 'Kapasitas Terpakai (%)', 'TF_Name': 'Nama Gardu'}
                )
                fig_bar_load.add_hline(
                    y=80, line_dash="dash", line_color="#DC2626",
                    annotation_text="Batas Aman PLN (80%)",
                    annotation_position="top right"
                )
                fig_bar_load.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                y_max = max(100, top_load['Load Percentage'].max() + 15)
                fig_bar_load.update_yaxes(range=[0, y_max])
                fig_bar_load.update_layout(
                    height=360,
                    margin=dict(l=10, r=10, t=30, b=10),
                    xaxis_tickangle=-30
                )
                st.plotly_chart(fig_bar_load, use_container_width=True)
            else:
                st.info("Belum ada data pengukuran pembebanan.")

        with col_t1_right:
            st.markdown("##### 📈 Distribusi Kategori Pembebanan")
            load_dist = measured_df['Load_Status'].value_counts().reset_index()
            load_dist.columns = ['Status', 'Jumlah']
            fig_pie_load = px.pie(
                load_dist,
                names='Status',
                values='Jumlah',
                hole=0.45,
                color='Status',
                color_discrete_map={
                    'Overload (>80%)': '#EF4444',
                    'Normal (40-80%)': '#10B981',
                    'Underload (<40%)': '#3B82F6',
                    'Belum Diukur': '#94A3B8'
                }
            )
            fig_pie_load.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation="h", yanchor="top", y=-0.1)
            )
            st.plotly_chart(fig_pie_load, use_container_width=True)

    # TAB 2: KESEIMBANGAN FASA
    with tab_unbalance:
        col_t2_left, col_t2_right = st.columns([3, 2])
        
        with col_t2_left:
            st.markdown("##### ⚖️ Top 10 Gardu Paling Tidak Seimbang (Unbalance %)")
            valid_unb = measured_df.dropna(subset=['Unbalance (%)']).sort_values(by='Unbalance (%)', ascending=False).head(10)
            if not valid_unb.empty:
                fig_unb = px.bar(
                    valid_unb,
                    x='TF_Name',
                    y='Unbalance (%)',
                    color='Unbalance (%)',
                    color_continuous_scale='Reds',
                    text='Unbalance (%)',
                    labels={'Unbalance (%)': 'Ketidakseimbangan (%)', 'TF_Name': 'Nama Gardu'}
                )
                fig_unb.add_hline(
                    y=20, line_dash="dash", line_color="#DC2626",
                    annotation_text="Batas Kritis PLN (20%)",
                    annotation_position="top right"
                )
                fig_unb.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_unb.update_layout(
                    height=360,
                    margin=dict(l=10, r=10, t=30, b=10),
                    xaxis_tickangle=-30
                )
                st.plotly_chart(fig_unb, use_container_width=True)
            else:
                st.info("Belum ada data unbalance.")

        with col_t2_right:
            st.markdown("##### 🔌 Distribusi Keseimbangan Fasa")
            unb_dist = measured_df['Unbalance_Status'].value_counts().reset_index()
            unb_dist.columns = ['Status', 'Jumlah']
            fig_pie_unb = px.pie(
                unb_dist,
                names='Status',
                values='Jumlah',
                hole=0.45,
                color='Status',
                color_discrete_map={
                    'Kritis (>20%)': '#EF4444',
                    'Perhatian (10-20%)': '#F59E0B',
                    'Seimbang (<10%)': '#10B981',
                    '1-Fasa (N/A)': '#94A3B8'
                }
            )
            fig_pie_unb.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation="h", yanchor="top", y=-0.1)
            )
            st.plotly_chart(fig_pie_unb, use_container_width=True)

    # TAB 3: KESEHATAN & HARMONISA
    with tab_health:
        col_t3_left, col_t3_right = st.columns(2)
        
        with col_t3_left:
            st.markdown("##### 🏥 Distribusi Skor Kesehatan Trafo (Health Score 0-100)")
            if not measured_df.empty:
                bins = [0, 40, 60, 80, 100]
                labels = ['Buruk (0-40)', 'Cukup (41-60)', 'Baik (61-80)', 'Sangat Baik (81-100)']
                measured_df['Health_Category'] = pd.cut(measured_df['Health Score'], bins=bins, labels=labels, include_lowest=True)
                health_counts = measured_df['Health_Category'].value_counts().reset_index()
                health_counts.columns = ['Kategori', 'Jumlah']

                fig_health = px.pie(
                    health_counts,
                    names='Kategori',
                    values='Jumlah',
                    hole=0.45,
                    color='Kategori',
                    color_discrete_map={
                        'Sangat Baik (81-100)': '#10B981',
                        'Baik (61-80)': '#3B82F6',
                        'Cukup (41-60)': '#F59E0B',
                        'Buruk (0-40)': '#EF4444'
                    }
                )
                fig_health.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig_health, use_container_width=True)

        with col_t3_right:
            st.markdown("##### 📉 Korelasi Pembebanan vs Distorsi Harmonisa (THD)")
            if not measured_df.empty:
                fig_scatter = px.scatter(
                    measured_df,
                    x='Load Percentage',
                    y='Weighted_THD',
                    color='Health Score',
                    hover_name='TF_Name',
                    color_continuous_scale='Viridis',
                    labels={'Load Percentage': 'Beban (%)', 'Weighted_THD': 'THD Rata-rata (%)'}
                )
                fig_scatter.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig_scatter, use_container_width=True)

    # TAB 4: PRIORITAS PENGUKURAN
    with tab_priority:
        st.markdown("##### 🚨 Antrean Kepatuhan Siklus Pengukuran SPLN (Maksimal 6 Bulan)")
        st.markdown("""
            <div style='background:#EFF6FF; border:1px solid #BFDBFE; border-radius:8px; padding:10px 14px; margin-bottom:12px; font-size:12px; color:#1E40AF; line-height:1.5;'>
                📋 <b>Ketentuan Standar PLN (SPLN)</b>: Pengukuran berkala beban gardu trafo wajib dilaksanakan minimal <b>1 kali setiap 6 bulan</b>. Gardu yang belum pernah diukur atau pengukuran terakhirnya telah melewati batas 6 bulan wajib dijadwalkan ulang oleh regu pemeliharaan ULP Moa.
            </div>
        """, unsafe_allow_html=True)
        
        col_tab_f1, col_tab_f2 = st.columns([2.5, 1])
        with col_tab_f1:
            tab_spln_flt = st.radio(
                "Filter Kategori:",
                [f"Semua Perlu Ukur ({need_measurement_count})", f"🟣 Lewat 6 Bulan SPLN ({overdue_count} Unit)", f"🔴 Belum Pernah Diukur ({unmeasured_count} Unit)"],
                horizontal=True,
                key="tab_spln_flt_radio"
            )
        with col_tab_f2:
            st.metric("Total Antrean Ukur", f"{need_measurement_count} Gardu", delta=f"{overdue_count} Kadaluarsa", delta_color="inverse")
        
        if "Lewat 6 Bulan" in tab_spln_flt:
            tab_queue = overdue_df.copy().sort_values(by='Parsed_Date', ascending=True)
        elif "Belum Pernah Diukur" in tab_spln_flt:
            tab_queue = unmeasured_df.copy()
        else:
            tab_queue = pd.concat([
                overdue_df.sort_values(by='Parsed_Date', ascending=True),
                unmeasured_df
            ])

        display_queue = pd.DataFrame({
            'Kode Gardu': tab_queue['TF_Code'],
            'Nama Gardu': tab_queue['TF_Name'],
            'Kapasitas': tab_queue['TF_MLoad'].apply(lambda x: f"{x:.0f} kVA"),
            'Fasa / Konstruksi': tab_queue['TF_Phase'].astype(str) + " Fasa • " + tab_queue['TF_Construction'].fillna('-'),
            'Tanggal Ukur Terakhir': tab_queue['Date'].fillna('Belum Pernah Diukur'),
            'Usia Pengukuran': tab_queue.apply(
                lambda r: f"🟣 {r['Months_Since_Measurement']:.1f} bln lalu (Lewat {(r['Months_Since_Measurement']-6):.1f} bln)" 
                if r['Measurement_Status'] == 'Perlu Ukur Ulang' and pd.notna(r['Months_Since_Measurement']) 
                else "🔴 Belum Pernah Diukur", axis=1
            ),
            'Status SPLN': tab_queue['Measurement_Status'].map({
                'Perlu Ukur Ulang': '🟣 Lewat 6 Bulan (Wajib Ukur)',
                'Belum Diukur': '🔴 Belum Pernah Diukur (Wajib Diawasi)'
            })
        })

        st.dataframe(display_queue, use_container_width=True, hide_index=True)
        
        csv_queue = display_queue.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Unduh Daftar Rencana Pengukuran Lapangan (CSV)",
            data=csv_queue,
            file_name=f"rencana_ukur_trafo_spln_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="btn_download_tab_queue"
        )


# ==========================================
# PAGE 2: SIMULASI YANBUNG (PASANG BARU)
# ==========================================
elif menu_selection == "🔌 Simulasi Yanbung":

    st.markdown("""
        <div style='background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 24px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
            <div>
                <h2 style='margin: 0 0 6px 0; font-size: 22px; color: #0F172A; font-weight: 800; display: flex; align-items: center; gap: 8px;'>
                    <span>🔌</span> Konsol Simulasi Beban & Keseimbangan Fasa (Yanbung)
                </h2>
                <div style='font-size: 13px; color: #64748B;'>
                    Engineering decision support system untuk simulasi pasang baru, penyeimbangan beban fasa otomatis, dan rekomendasi teknis PLN.
                </div>
            </div>
            <div style='background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 700; color: #1E40AF; white-space: nowrap;'>
                ⚡ Standar PLN: Kapasitas Maks 80% • Unbalance &lt; 20%
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2-COLUMN BALANCED SPLIT CONSOLE
    col_input_panel, col_result_panel = st.columns([1, 1.25], gap="large")

    with col_input_panel:
        st.markdown("<div style='font-size: 15px; font-weight: 800; color: #0F172A; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;'>⚙️ Parameter Alokasi Beban</div>", unsafe_allow_html=True)

        # 1. SELEKSI GARDU
        mode_pilih = st.radio("Metode Penentuan Gardu:", ["🔍 Pilih Langsung", "📍 Cari via GPS Survei"], horizontal=True)

        valid_trafo_list = df.dropna(subset=['TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code'])
        trafo_options = dict(zip(valid_trafo_list['TF_Code'], valid_trafo_list['TF_Name']))
        default_tf_code = list(trafo_options.keys())[0]

        if mode_pilih == "📍 Cari via GPS Survei":
            col_gps1, col_gps2 = st.columns(2)
            with col_gps1:
                survei_lat = st.number_input("Latitude Survei", value=-8.150000, format="%.6f")
            with col_gps2:
                survei_lon = st.number_input("Longitude Survei", value=127.790000, format="%.6f")

            valid_coords = df.dropna(subset=['latitude', 'longitude', 'TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code']).copy()
            if not valid_coords.empty:
                lat1, lon1 = np.radians(survei_lat), np.radians(survei_lon)
                lat2, lon2 = np.radians(valid_coords['latitude']), np.radians(valid_coords['longitude'])
                dlat, dlon = lat2 - lat1, lon2 - lon1
                a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
                valid_coords['Jarak_M'] = (2 * np.arcsin(np.sqrt(a)) * 6371 * 1000).round(1)
                nearest_3 = valid_coords.sort_values(by='Jarak_M').head(3)

                st.markdown("<div style='font-size:11px; font-weight:700; color:#0072BC; margin: 4px 0;'>3 Gardu Terdekat:</div>", unsafe_allow_html=True)
                for idx, (_, r_n) in enumerate(nearest_3.iterrows()):
                    load_info = f"{r_n['Load Percentage']}%" if pd.notna(r_n['Load Percentage']) else "N/A"
                    st.markdown(f"<div style='background:#F1F5F9; border-radius:5px; padding:4px 8px; margin-bottom:3px; font-size:11px; display:flex; justify-content:space-between;'><span><b>{idx+1}. {r_n['TF_Name']}</b></span><span>📏 <b>{r_n['Jarak_M']} m</b> • Beban: {load_info}</span></div>", unsafe_allow_html=True)
                default_tf_code = nearest_3.iloc[0]['TF_Code']

        selected_code = st.selectbox(
            "Pilih Transformator Distribusi:",
            options=list(trafo_options.keys()),
            index=list(trafo_options.keys()).index(default_tf_code) if default_tf_code in trafo_options else 0,
            format_func=lambda x: f"{trafo_options[x]} ({x})"
        )

        # Selected Trafo Data Processing
        trafo_row = df[df['TF_Code'] == selected_code].iloc[0]
        tf_mload = float(trafo_row.get('TF_MLoad', 50) or 50)
        tf_cur_load = float(trafo_row.get('Current Load', 0) or 0)
        tf_load_pct = float(trafo_row.get('Load Percentage', 0) or 0)
        tf_unb = float(trafo_row.get('Unbalance (%)', 0) or 0)

        st.markdown(f"""
            <div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:6px 10px; margin-top:2px; margin-bottom:14px; font-size:11px; display:flex; justify-content:space-between;'>
                <span>Kapasitas: <b>{tf_mload:.0f} kVA</b></span>
                <span>Beban Saat Ini: <b>{tf_load_pct:.1f}%</b></span>
                <span>Unbalance: <b>{tf_unb:.1f}%</b></span>
            </div>
        """, unsafe_allow_html=True)

        # 2. PARAMETER PELANGGAN & REKOMENDASI FASA
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            power_opts = [450, 900, 1300, 2200, 3500, 4400, 5500, 6600, 7700, 10600, 13200, 16500, 23000, 33000, 41500, 53000]
            new_power_va = st.selectbox("Daya Pelanggan (VA)", power_opts, index=1)
        with col_p2:
            demand_factor = st.selectbox("Faktor Kebutuhan (DF)", [0.40, 0.50, 0.60, 0.70, 0.80, 1.00], index=2, format_func=lambda x: f"{int(x*100)}% (DF={x:.2f})")

        # Calculation of added load
        added_ampere = (new_power_va * demand_factor) / 230.0
        added_kva = (new_power_va * demand_factor) / 1000.0

        r_amp = float(trafo_row.get('A_R_P', 0) or 0)
        s_amp = float(trafo_row.get('A_S_P', 0) or 0)
        t_amp = float(trafo_row.get('A_T_P', 0) or 0)

        phase_amps = {'R': r_amp, 'S': s_amp, 'T': t_amp}
        rec_phase = min(phase_amps, key=phase_amps.get)
        min_val = phase_amps[rec_phase]

        # Calculation of hypothetical unbalance
        def sim_unb(p_target):
            nr = r_amp + (added_ampere if p_target == 'R' else 0)
            ns = s_amp + (added_ampere if p_target == 'S' else 0)
            nt = t_amp + (added_ampere if p_target == 'T' else 0)
            navg = (nr + ns + nt) / 3
            ndev = max(abs(nr - navg), abs(ns - navg), abs(nt - navg))
            return round((ndev / navg) * 100, 2) if navg > 0 else 0.0

        rec_unb = sim_unb(rec_phase)
        unb_change = rec_unb - tf_unb

        # SMART ENGINEERING RECOMMENDATION BOX
        st.markdown(f"""
            <div style='background: #EFF6FF; border: 1.5px solid #93C5FD; border-radius: 8px; padding: 10px 12px; margin: 10px 0;'>
                <div style='font-size: 11px; font-weight: 800; color: #1E40AF; text-transform: uppercase; display: flex; align-items: center; gap: 6px;'>
                    <span>💡</span> REKOMENDASI SISTEM PENYEIMBANGAN
                </div>
                <div style='font-size: 12px; color: #1E3A8A; margin-top: 4px; line-height: 1.4;'>
                    Sambungkan ke <b>Fasa {rec_phase}</b> (arus eksisting terendah: <b>{min_val:.1f} A</b>).<br>
                    Penambahan <b>+{added_ampere:.2f} A</b> pada fasa ini diprediksi {f'menurunkan unbalance menjadi <b>{rec_unb:.1f}%</b> ({unb_change:.1f}%)' if unb_change <= 0 else f'menghasilkan unbalance <b>{rec_unb:.1f}%</b>'}.
                </div>
            </div>
        """, unsafe_allow_html=True)

        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            target_phase = st.radio("Sambungkan ke Fasa:", ["R", "S", "T"], index=["R", "S", "T"].index(rec_phase), horizontal=True)
        with col_sel2:
            target_jalur = st.radio("Pilih Jurusan JTR:", ["1", "2", "3"], index=0, horizontal=True)

        # ACTION BUTTON (CLEAN PLN BLUE)
        btn_save = st.button("💾 Simpan Penambahan Beban ke Database", type="primary", use_container_width=True)
        if btn_save:
            with st.spinner("Menyimpan akumulasi beban ke Google Sheets (RAW_MEA)..."):
                try:
                    creds = get_google_credentials()
                    gc = gspread.authorize(creds)
                    sh = gc.open("DATA TRAFO")
                    sheet_raw = sh.worksheet("RAW_MEA")
                    all_records = sheet_raw.get_all_records()
                    headers = sheet_raw.row_values(1)

                    target_row_idx = None
                    for idx, row in enumerate(all_records):
                        if str(row.get('TF_Code')).strip() == str(selected_code).strip():
                            target_row_idx = idx + 2

                    if target_row_idx:
                        ala_pangkal = f"ALA_{target_phase}_P"
                        ala_jalur = f"ALA_{target_phase}_{target_jalur}"

                        if ala_pangkal in headers and ala_jalur in headers:
                            idx_p = headers.index(ala_pangkal) + 1
                            idx_j = headers.index(ala_jalur) + 1

                            cur_val_p = float(sheet_raw.cell(target_row_idx, idx_p).value or 0)
                            cur_val_j = float(sheet_raw.cell(target_row_idx, idx_j).value or 0)

                            sheet_raw.update_cell(target_row_idx, idx_p, round(cur_val_p + added_ampere, 2))
                            sheet_raw.update_cell(target_row_idx, idx_j, round(cur_val_j + added_ampere, 2))

                            st.cache_data.clear()
                            st.success(f"✅ Berhasil! Penambahan arus {added_ampere:.2f}A dicatat pada {ala_pangkal} dan {ala_jalur} untuk {trafo_row['TF_Name']}.")
                        else:
                            st.error(f"Kolom {ala_pangkal} atau {ala_jalur} tidak ditemukan di header RAW_MEA.")
                    else:
                        st.error(f"Riwayat pengukuran untuk gardu {trafo_row['TF_Name']} ({selected_code}) tidak ditemukan di RAW_MEA.")
                except Exception as e:
                    st.error(f"Gagal menyimpan ke database: {e}")

    with col_result_panel:
        st.markdown("<div style='font-size: 14px; font-weight: 800; color: #0F172A; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;'>📊 Analisis Dampak Beban & Keseimbangan</div>", unsafe_allow_html=True)

        # Calculate live simulation metrics
        new_r = r_amp + (added_ampere if target_phase == 'R' else 0)
        new_s = s_amp + (added_ampere if target_phase == 'S' else 0)
        new_t = t_amp + (added_ampere if target_phase == 'T' else 0)

        new_avg = (new_r + new_s + new_t) / 3
        new_max_dev = max(abs(new_r - new_avg), abs(new_s - new_avg), abs(new_t - new_avg))
        pred_unbalance = round((new_max_dev / new_avg) * 100, 2) if new_avg > 0 else 0.0

        pred_load_kva = round(tf_cur_load + added_kva, 2)
        pred_load_pct = round((pred_load_kva / tf_mload) * 100, 1) if tf_mload > 0 else 0.0

        # TOP 3 COMPACT IMPACT KPI CARDS
        kpi_s1, kpi_s2, kpi_s3 = st.columns(3)

        with kpi_s1:
            is_over = pred_load_pct > 80
            st.markdown(f"""
                <div class='kpi-card {"kpi-card-danger" if is_over else "kpi-card-success"}' style='padding:12px 14px; margin-bottom:10px;'>
                    <div class='kpi-title'>Prediksi Beban Total</div>
                    <div class='kpi-value' style='font-size:22px;'>{pred_load_kva} <span style='font-size:13px;'>kVA</span></div>
                    <div class='kpi-desc'><b>{pred_load_pct}%</b> (+{added_kva:.2f} kVA)</div>
                </div>
            """, unsafe_allow_html=True)

        with kpi_s2:
            unb_diff = pred_unbalance - tf_unb
            is_good = unb_diff <= 0
            st.markdown(f"""
                <div class='kpi-card {"kpi-card-success" if is_good else "kpi-card-warning"}' style='padding:12px 14px; margin-bottom:10px;'>
                    <div class='kpi-title'>Ketidakseimbangan</div>
                    <div class='kpi-value' style='font-size:22px;'>{pred_unbalance}%</div>
                    <div class='kpi-desc'><span style='color:{"#15803D" if is_good else "#B45309"}; font-weight:700;'>{f"Turun {abs(unb_diff):.2f}%" if is_good else f"Naik +{unb_diff:.2f}%"}</span></div>
                </div>
            """, unsafe_allow_html=True)

        with kpi_s3:
            st.markdown(f"""
                <div class='kpi-card kpi-card-info' style='padding:12px 14px; margin-bottom:10px;'>
                    <div class='kpi-title'>Arus Tambahan (Fasa {target_phase})</div>
                    <div class='kpi-value' style='font-size:22px;'>+{added_ampere:.2f} <span style='font-size:13px;'>A</span></div>
                    <div class='kpi-desc'>Total Fasa {target_phase}: <b>{(phase_amps[target_phase] + added_ampere):.1f} A</b></div>
                </div>
            """, unsafe_allow_html=True)

        # BAR CHART: COMPARATIVE PHASE CURRENTS
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name='Arus Eksisting (A)',
            x=['Fasa R', 'Fasa S', 'Fasa T'],
            y=[r_amp, s_amp, t_amp],
            marker_color='#94A3B8',
            text=[f"{r_amp:.1f} A", f"{s_amp:.1f} A", f"{t_amp:.1f} A"],
            textposition='outside',
            textfont=dict(size=11, color='#475569')
        ))
        fig_comp.add_trace(go.Bar(
            name='Prediksi Pasang Baru (A)',
            x=['Fasa R', 'Fasa S', 'Fasa T'],
            y=[new_r, new_s, new_t],
            marker_color='#0072BC',
            text=[f"{new_r:.1f} A", f"{new_s:.1f} A", f"{new_t:.1f} A"],
            textposition='outside',
            textfont=dict(size=11, color='#0072BC')
        ))
        y_max = max(new_r, new_s, new_t, r_amp, s_amp, t_amp, 10) * 1.25
        fig_comp.update_yaxes(range=[0, y_max], title_text="Arus (Ampere)")
        fig_comp.update_layout(
            barmode='group',
            height=280,
            margin=dict(l=10, r=10, t=25, b=10),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=11)
            )
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # DETAILED COMPARISON TABLE
        raw_jalur_val = trafo_row.get(f"A_{target_phase}_{target_jalur}", 0.0)
        cur_jalur_amp = float(raw_jalur_val) if pd.notna(raw_jalur_val) and str(raw_jalur_val).strip() != '' else 0.0
        new_jalur_amp = cur_jalur_amp + added_ampere

        comp_data = pd.DataFrame({
            "Titik Arus Trafo": ["Fasa R (Pangkal)", "Fasa S (Pangkal)", "Fasa T (Pangkal)", f"Jurusan {target_jalur} Fasa {target_phase}"],
            "Eksisting (A)": [f"{r_amp:.2f} A", f"{s_amp:.2f} A", f"{t_amp:.2f} A", f"{cur_jalur_amp:.2f} A"],
            "Prediksi Baru (A)": [f"{new_r:.2f} A", f"{new_s:.2f} A", f"{new_t:.2f} A", f"{new_jalur_amp:.2f} A"],
            "Dampak Arus": [
                f"+{added_ampere:.2f} A" if target_phase == 'R' else "-",
                f"+{added_ampere:.2f} A" if target_phase == 'S' else "-",
                f"+{added_ampere:.2f} A" if target_phase == 'T' else "-",
                f"+{added_ampere:.2f} A (Pilihan)"
            ]
        })

        st.dataframe(comp_data, use_container_width=True, hide_index=True)


# ==========================================
# PAGE 3: RIWAYAT & DOSSIER TRAFO
# ==========================================
elif menu_selection == "📈 Riwayat & Dossier Trafo":

    st.markdown("""
        <div style='background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-bottom: 20px;'>
            <h2 style='margin: 0 0 6px 0; font-size: 22px; color: #0F172A; font-weight: 800;'>
                📈 Dossier & Riwayat Pengukuran Gardu
            </h2>
            <div style='font-size: 13px; color: #64748B;'>
                Pelacakan performa historis, stabilitas voltase, ketidakseimbangan fasa, dan harmonisa per unit gardu transformator.
            </div>
        </div>
    """, unsafe_allow_html=True)

    valid_trafo_list = df.dropna(subset=['TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code'])
    trafo_options = dict(zip(valid_trafo_list['TF_Code'], valid_trafo_list['TF_Name']))

    selected_code = st.selectbox(
        "🔍 Cari dan Pilih Gardu Transformator:",
        options=list(trafo_options.keys()),
        format_func=lambda x: f"{trafo_options[x]} ({x})"
    )

    if selected_code:
        # Filter all measurements for this trafo from RAW_MEA
        hist_raw = df_raw_full[df_raw_full['TF_Code'].astype(str).str.strip() == str(selected_code).strip()].copy()
        static_info = df[df['TF_Code'] == selected_code].iloc[0]

        # Asset Passport Header Card
        col_pass1, col_pass2 = st.columns([2, 1])

        with col_pass1:
            st.markdown(f"""
                <div class='asset-card'>
                    <div style='font-size: 11px; font-weight: 700; color: #0072BC; text-transform: uppercase;'>PASPOR ASET TRANSFORMATOR</div>
                    <div style='font-size: 24px; font-weight: 800; color: #0F172A; margin: 4px 0 12px 0;'>
                        {static_info['TF_Name']} <span style='font-size:16px; color:#64748B;'>({selected_code})</span>
                    </div>
                    <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; font-size: 13px;'>
                        <div><b>Kapasitas:</b> {static_info['TF_MLoad']} kVA</div>
                        <div><b>Tipe Fasa:</b> {static_info['TF_Phase']} Fasa</div>
                        <div><b>Konstruksi:</b> {static_info['TF_Construction']}</div>
                        <div><b>Beban Terakhir:</b> {static_info.get('Load Percentage', '-')}%</div>
                        <div><b>Unbalance:</b> {static_info.get('Unbalance (%)', '-')}%</div>
                        <div><b>Skor Kesehatan:</b> {static_info.get('Health Score', '-')}/100</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_pass2:
            if pd.notna(static_info.get('latitude')) and pd.notna(static_info.get('longitude')):
                lat = static_info['latitude']
                lon = static_info['longitude']
                st.markdown(f"""
                    <div class='asset-card' style='text-align:center;'>
                        <div style='font-size: 12px; color: #64748B;'>Koordinat Lokasi GPS</div>
                        <div style='font-size: 14px; font-weight:700; color:#0F172A; margin: 6px 0;'>{lat:.6f}, {lon:.6f}</div>
                        <a href='https://www.google.com/maps/search/?api=1&query={lat},{lon}' target='_blank' style='display:inline-block; background:#0072BC; color:white; padding:6px 14px; border-radius:6px; font-size:12px; font-weight:600; text-decoration:none;'>
                            🗺️ Buka di Google Maps
                        </a>
                    </div>
                """, unsafe_allow_html=True)

        if hist_raw.empty:
            st.warning("⚠️ Gardu ini belum memiliki catatan riwayat pengukuran di sheet RAW_MEA.")
        else:
            # Process history data
            hist_raw['Parsed_Time'] = pd.to_datetime(
                hist_raw['Date'].astype(str) + ' ' + hist_raw['Time'].astype(str),
                errors='coerce'
            )
            hist_raw = hist_raw.sort_values(by='Parsed_Time', ascending=True)
            hist_raw['Timestamp_Str'] = hist_raw['Date'].astype(str) + ' ' + hist_raw['Time'].astype(str)

            for c in ['A_R_P', 'A_S_P', 'A_T_P', 'A_N_P', 'V_RN', 'V_SN', 'V_TN', 'THD_R_P', 'THD_S_P', 'THD_T_P']:
                if c in hist_raw.columns:
                    hist_raw[c] = pd.to_numeric(hist_raw[c], errors='coerce').fillna(0)

            hist_raw['Hist_Load_kVA'] = (((hist_raw['V_RN'].replace(0, 230) * hist_raw['A_R_P']) +
                                          (hist_raw['V_SN'].replace(0, 230) * hist_raw['A_S_P']) +
                                          (hist_raw['V_TN'].replace(0, 230) * hist_raw['A_T_P'])) / 1000).round(2)
            max_mload = float(static_info['TF_MLoad'] or 50.0)
            hist_raw['Hist_Load_Pct'] = ((hist_raw['Hist_Load_kVA'] / max_mload) * 100).round(1) if max_mload > 0 else 0.0

            hist_raw['Hist_Avg_I'] = (hist_raw['A_R_P'] + hist_raw['A_S_P'] + hist_raw['A_T_P']) / 3
            hist_raw['Hist_Max_Dev'] = hist_raw[['A_R_P', 'A_S_P', 'A_T_P']].sub(hist_raw['Hist_Avg_I'], axis=0).abs().max(axis=1)
            hist_raw['Hist_Unbalance'] = np.where(hist_raw['Hist_Avg_I'] > 0, (hist_raw['Hist_Max_Dev'] / hist_raw['Hist_Avg_I']) * 100, 0.0).round(2)

            # Trend Selector
            st.markdown("<div class='section-header'>📈 Grafik Tren Parameter Historis</div>", unsafe_allow_html=True)
            trend_choice = st.radio(
                "Pilih Analisis Tren:",
                ["⚡ Beban Trafo (kVA & %)", "⚖️ Ketidakseimbangan Fasa (%)", "🔌 Profil Arus Fasa (R, S, T, N)", "⚡ Profil Tegangan (V_RN, V_SN, V_TN)", "🏥 Harmonisa (THD R, S, T)"],
                horizontal=True
            )

            fig_trend = go.Figure()

            if trend_choice == "⚡ Beban Trafo (kVA & %)":
                fig_trend.add_trace(go.Scatter(
                    x=hist_raw['Timestamp_Str'], y=hist_raw['Hist_Load_Pct'],
                    mode='lines+markers+text', name='Beban (%)',
                    line=dict(color='#0072BC', width=3), text=hist_raw['Hist_Load_Pct'].apply(lambda x: f"{x}%"),
                    textposition='top center'
                ))
                fig_trend.add_hline(y=80, line_dash="dash", line_color="#DC2626", annotation_text="Batas Beban Aman (80%)")
                fig_trend.update_layout(yaxis_title="Persentase Pembebanan (%)")

            elif trend_choice == "⚖️ Ketidakseimbangan Fasa (%)":
                fig_trend.add_trace(go.Scatter(
                    x=hist_raw['Timestamp_Str'], y=hist_raw['Hist_Unbalance'],
                    mode='lines+markers+text', name='Unbalance (%)',
                    line=dict(color='#F59E0B', width=3), text=hist_raw['Hist_Unbalance'].apply(lambda x: f"{x}%"),
                    textposition='top center'
                ))
                fig_trend.add_hline(y=20, line_dash="dash", line_color="#DC2626", annotation_text="Batas Kritis (20%)")
                fig_trend.update_layout(yaxis_title="Ketidakseimbangan Fasa (%)")

            elif trend_choice == "🔌 Profil Arus Fasa (R, S, T, N)":
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['A_R_P'], name='Arus R (A)', line=dict(color='#EF4444', width=2)))
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['A_S_P'], name='Arus S (A)', line=dict(color='#F59E0B', width=2)))
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['A_T_P'], name='Arus T (A)', line=dict(color='#10B981', width=2)))
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['A_N_P'], name='Arus Netral N (A)', line=dict(color='#64748B', width=2, dash='dot')))
                fig_trend.update_layout(yaxis_title="Arus (Ampere)")

            elif trend_choice == "⚡ Profil Tegangan (V_RN, V_SN, V_TN)":
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['V_RN'], name='Voltase RN (V)', line=dict(color='#EF4444', width=2)))
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['V_SN'], name='Voltase SN (V)', line=dict(color='#F59E0B', width=2)))
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['V_TN'], name='Voltase TN (V)', line=dict(color='#10B981', width=2)))
                fig_trend.add_hline(y=230, line_dash="dash", line_color="#3B82F6", annotation_text="Nominal 230V")
                fig_trend.update_layout(yaxis_title="Tegangan Fasa-Netral (Volt)")

            else:
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['THD_R_P'], name='THD R (%)', line=dict(color='#EF4444', width=2)))
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['THD_S_P'], name='THD S (%)', line=dict(color='#F59E0B', width=2)))
                fig_trend.add_trace(go.Scatter(x=hist_raw['Timestamp_Str'], y=hist_raw['THD_T_P'], name='THD T (%)', line=dict(color='#10B981', width=2)))
                fig_trend.add_hline(y=5, line_dash="dash", line_color="#DC2626", annotation_text="Batas IEEE THD 5%")
                fig_trend.update_layout(yaxis_title="Distorsi Harmonisa THD (%)")

            fig_trend.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=10))
            st.plotly_chart(fig_trend, use_container_width=True)

            # Historical Data Table
            st.markdown("<div class='section-header'>📋 Rekapitulasi Data Pengukuran Historis</div>", unsafe_allow_html=True)
            hist_display_cols = [
                'Date', 'Time', 'Hist_Load_kVA', 'Hist_Load_Pct', 'Hist_Unbalance',
                'A_R_P', 'A_S_P', 'A_T_P', 'A_N_P', 'V_RN', 'V_SN', 'V_TN',
                'THD_R_P', 'THD_S_P', 'THD_T_P'
            ]
            hist_display_cols = [c for c in hist_display_cols if c in hist_raw.columns]
            st.dataframe(
                hist_raw[hist_display_cols].sort_values(by='Date', ascending=False),
                use_container_width=True,
                hide_index=True
            )


# ==========================================
# PAGE 4: DATA SEMUA TRAFO
# ==========================================
elif menu_selection == "📋 Data Semua Trafo":

    st.markdown("""
        <div style='background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-bottom: 20px;'>
            <h2 style='margin: 0 0 6px 0; font-size: 22px; color: #0F172A; font-weight: 800;'>
                📋 Data Master & Pengukuran Keseluruhan Trafo
            </h2>
            <div style='font-size: 13px; color: #64748B;'>
                Tabel master 218 gardu transformator terpadu antara database statis (INFO_DATA) dan status pengukuran terkini (RAW_MEA).
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Multi-Filter Controls
    with st.expander("🔍 Filter Data & Pencarian Lanjutan", expanded=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            search_query = st.text_input("Cari Kode / Nama Gardu", placeholder="Contoh: MOA001 atau PASAR")
        with col_f2:
            const_choices = ["Semua"] + list(df['TF_Construction'].dropna().unique())
            sel_const = st.selectbox("Jenis Konstruksi", const_choices)
        with col_f3:
            load_choices = ["Semua", "Overload (>80%)", "Normal (40-80%)", "Underload (<40%)", "Belum Diukur"]
            sel_load = st.selectbox("Status Beban", load_choices)
        with col_f4:
            mea_choices = ["Semua", "Terkini", "Perlu Ukur Ulang", "Belum Diukur"]
            sel_mea = st.selectbox("Status Pengukuran", mea_choices)

    # Apply Filters
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df['TF_Code'].str.contains(search_query, case=False, na=False) |
            filtered_df['TF_Name'].str.contains(search_query, case=False, na=False)
        ]
    if sel_const != "Semua":
        filtered_df = filtered_df[filtered_df['TF_Construction'] == sel_const]
    if sel_load != "Semua":
        filtered_df = filtered_df[filtered_df['Load_Status'] == sel_load]
    if sel_mea != "Semua":
        filtered_df = filtered_df[filtered_df['Measurement_Status'] == sel_mea]

    # Filter Summary Bar
    st.markdown(f"""
        <div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 16px; margin-bottom:14px; font-size:13px; display:flex; gap:20px;'>
            <span>Ditemukan: <b>{len(filtered_df)}</b> Gardu</span>
            <span>Total Kapasitas Terpasang: <b>{filtered_df['TF_MLoad'].sum():,.0f} kVA</b></span>
            <span>Gardu Terukur: <b>{filtered_df['Is_Measured'].sum()}</b></span>
            <span>Gardu Overload: <b>{(filtered_df['Load Percentage'] > 80).sum()}</b></span>
        </div>
    """, unsafe_allow_html=True)

    # Format Columns for Display
    show_cols = [
        'TF_Code', 'TF_Name', 'TF_MLoad', 'TF_Phase', 'TF_Construction',
        'Measurement_Status', 'Load Percentage', 'Current Load', 'Unbalance (%)',
        'Health Score', 'Date', 'A_R_P', 'A_S_P', 'A_T_P', 'TF_Coordinate'
    ]
    show_cols = [c for c in show_cols if c in filtered_df.columns]

    st.dataframe(
        filtered_df[show_cols],
        use_container_width=True,
        hide_index=True
    )

    # CSV Download
    csv_data = filtered_df[show_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Unduh Data Terfilter (CSV)",
        data=csv_data,
        file_name=f"data_trafo_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )


# ==========================================
# PAGE 5: INPUT PENGUKURAN (HIOKI PDF)
# ==========================================
elif menu_selection == "📥 Input Pengukuran Gardu":

    st.markdown("""
        <div style='background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 24px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
            <div>
                <h2 style='margin: 0 0 6px 0; font-size: 22px; color: #0F172A; font-weight: 800; display: flex; align-items: center; gap: 8px;'>
                    <span>📥</span> Pencatatan & Input Pengukuran Gardu
                </h2>
                <div style='font-size: 13px; color: #64748B;'>
                    Pilih metode input sesuai peralatan lapangan: formulir manual untuk Avometer / Tang Ampere, atau unggah laporan PDF untuk alat Hioki PQA.
                </div>
            </div>
            <div style='background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 700; color: #1E40AF; white-space: nowrap;'>
                ⚡ Standar SPLN: Siklus Wajib 6 Bulan
            </div>
        </div>
    """, unsafe_allow_html=True)

    valid_trafo_list = df.dropna(subset=['TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code'])
    trafo_options = dict(zip(valid_trafo_list['TF_Code'], valid_trafo_list['TF_Name']))

    selected_code = st.selectbox(
        "🔍 1. Cari & Pilih Gardu Transformator:",
        options=["-- Pilih Gardu --"] + list(trafo_options.keys()),
        format_func=lambda x: f"{trafo_options[x]} ({x})" if x != "-- Pilih Gardu --" else x
    )

    if selected_code != "-- Pilih Gardu --":
        curr_trafo = df[df['TF_Code'] == selected_code].iloc[0]
        tf_mload = float(curr_trafo.get('TF_MLoad', 50) or 50)
        tf_phase = int(curr_trafo.get('TF_Phase', 3) or 3)
        tf_const = str(curr_trafo.get('TF_Construction', 'Cantol'))
        last_date = str(curr_trafo.get('Date', 'Belum Pernah Diukur'))
        mea_stat = str(curr_trafo.get('Measurement_Status', 'Belum Diukur'))

        # Quick info badge of the selected transformer
        st.markdown(f"""
            <div style='background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;'>
                <div>
                    <span style='font-size: 11px; font-weight: 700; color: #0072BC; text-transform: uppercase;'>GARDU TERPILIH</span>
                    <div style='font-size: 16px; font-weight: 800; color: #0F172A;'>{curr_trafo['TF_Name']} <span style='font-size: 13px; color: #64748B;'>({selected_code})</span></div>
                </div>
                <div style='display: flex; gap: 14px; font-size: 12px;'>
                    <span>Kapasitas: <b>{tf_mload:.0f} kVA</b></span>
                    <span>Tipe: <b>{tf_phase} Fasa</b></span>
                    <span>Konstruksi: <b>{tf_const}</b></span>
                    <span>Status: <b>{mea_stat}</b> ({last_date})</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # TAB SELECTION: MANUAL INPUT vs HIOKI PDF
        tab_manual, tab_hioki = st.tabs([
            "✍️ Input Manual (Avometer / Tang Ampere)",
            "📄 Upload Laporan PDF Hioki (AI Assisted)"
        ])

        # ---------------------------------------------------------
        # TAB 1: INPUT MANUAL (AVOMETER / CLAMP METER)
        # ---------------------------------------------------------
        with tab_manual:
            col_m_in, col_m_prev = st.columns([1.1, 1], gap="large")

            with col_m_in:
                st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 8px;'>📅 1. Waktu Pengukuran Lapangan</div>", unsafe_allow_html=True)
                col_dt1, col_dt2 = st.columns(2)
                with col_dt1:
                    m_tanggal = st.date_input("Tanggal Ukur", value=datetime.today(), key="man_tgl")
                with col_dt2:
                    m_waktu = st.time_input("Jam Ukur", value=datetime.now().time(), key="man_jam")

                st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin: 12px 0 8px 0;'>⚡ 2. Tegangan Pengukuran (Volt)</div>", unsafe_allow_html=True)
                if tf_phase == 1:
                    m_vrn = st.number_input("Tegangan Fasa - Netral (V_RN)", value=230.0, step=1.0, key="man_vrn_1p")
                    m_vsn = 0.0
                    m_vtn = 0.0
                    m_vrs = 0.0
                    m_vrt = 0.0
                    m_vst = 0.0
                else:
                    col_v1, col_v2, col_v3 = st.columns(3)
                    with col_v1:
                        m_vrn = st.number_input("Voltase R-N (V)", value=230.0, step=1.0, key="man_vrn")
                    with col_v2:
                        m_vsn = st.number_input("Voltase S-N (V)", value=230.0, step=1.0, key="man_vsn")
                    with col_v3:
                        m_vtn = st.number_input("Voltase T-N (V)", value=230.0, step=1.0, key="man_vtn")

                    m_vrs = round(m_vrn * 1.732, 1)
                    m_vrt = round(m_vtn * 1.732, 1)
                    m_vst = round(m_vsn * 1.732, 1)

                st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin: 12px 0 8px 0;'>🔌 3. Arus Beban Pangkal Trafo (Ampere)</div>", unsafe_allow_html=True)
                if tf_phase == 1:
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        m_arp = st.number_input("Arus Fasa R (Ampere)", value=0.0, min_value=0.0, step=0.5, key="man_arp_1p")
                    with col_a2:
                        m_anp = st.number_input("Arus Netral N (Ampere)", value=0.0, min_value=0.0, step=0.5, key="man_anp_1p")
                    m_asp = 0.0
                    m_atp = 0.0
                else:
                    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                    with col_a1:
                        m_arp = st.number_input("Arus Fasa R (A)", value=0.0, min_value=0.0, step=0.5, key="man_arp")
                    with col_a2:
                        m_asp = st.number_input("Arus Fasa S (A)", value=0.0, min_value=0.0, step=0.5, key="man_asp")
                    with col_a3:
                        m_atp = st.number_input("Arus Fasa T (A)", value=0.0, min_value=0.0, step=0.5, key="man_atp")
                    with col_a4:
                        m_anp = st.number_input("Arus Netral N (A)", value=0.0, min_value=0.0, step=0.5, key="man_anp")

                # Optional Jurusan
                with st.expander("➕ Rincian Arus Jurusan JTR (Opsional / Multi-Jurusan)", expanded=False):
                    st.caption("Jika tidak diisi, arus Jurusan 1 otomatis disamakan dengan Arus Pangkal.")
                    col_j1_r, col_j1_s, col_j1_t, col_j1_n = st.columns(4)
                    with col_j1_r:
                        m_ar1 = st.number_input("Jurusan 1 R (A)", value=m_arp, min_value=0.0, step=0.5, key="man_ar1")
                    with col_j1_s:
                        m_as1 = st.number_input("Jurusan 1 S (A)", value=m_asp, min_value=0.0, step=0.5, key="man_as1")
                    with col_j1_t:
                        m_at1 = st.number_input("Jurusan 1 T (A)", value=m_atp, min_value=0.0, step=0.5, key="man_at1")
                    with col_j1_n:
                        m_an1 = st.number_input("Jurusan 1 N (A)", value=m_anp, min_value=0.0, step=0.5, key="man_an1")

                    col_j2_r, col_j2_s, col_j2_t, col_j2_n = st.columns(4)
                    with col_j2_r:
                        m_ar2 = st.number_input("Jurusan 2 R (A)", value=0.0, min_value=0.0, step=0.5, key="man_ar2")
                    with col_j2_s:
                        m_as2 = st.number_input("Jurusan 2 S (A)", value=0.0, min_value=0.0, step=0.5, key="man_as2")
                    with col_j2_t:
                        m_at2 = st.number_input("Jurusan 2 T (A)", value=0.0, min_value=0.0, step=0.5, key="man_at2")
                    with col_j2_n:
                        m_an2 = st.number_input("Jurusan 2 N (A)", value=0.0, min_value=0.0, step=0.5, key="man_an2")

                    col_j3_r, col_j3_s, col_j3_t, col_j3_n = st.columns(4)
                    with col_j3_r:
                        m_ar3 = st.number_input("Jurusan 3 R (A)", value=0.0, min_value=0.0, step=0.5, key="man_ar3")
                    with col_j3_s:
                        m_as3 = st.number_input("Jurusan 3 S (A)", value=0.0, min_value=0.0, step=0.5, key="man_as3")
                    with col_j3_t:
                        m_at3 = st.number_input("Jurusan 3 T (A)", value=0.0, min_value=0.0, step=0.5, key="man_at3")
                    with col_j3_n:
                        m_an3 = st.number_input("Jurusan 3 N (A)", value=0.0, min_value=0.0, step=0.5, key="man_an3")

            with col_m_prev:
                st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 8px;'>📊 Live Preview Hasil Perhitungan</div>", unsafe_allow_html=True)
                
                # Live Calculations
                if tf_phase == 1:
                    calc_load_kva = round((m_vrn * m_arp) / 1000.0, 2)
                    calc_load_pct = round((calc_load_kva / tf_mload) * 100, 1) if tf_mload > 0 else 0.0
                    calc_unbalance = 0.0
                else:
                    calc_load_kva = round(((m_vrn * m_arp) + (m_vsn * m_asp) + (m_vtn * m_atp)) / 1000.0, 2)
                    calc_load_pct = round((calc_load_kva / tf_mload) * 100, 1) if tf_mload > 0 else 0.0
                    
                    avg_i = (m_arp + m_asp + m_atp) / 3.0
                    if avg_i > 0:
                        max_dev = max(abs(m_arp - avg_i), abs(m_asp - avg_i), abs(m_atp - avg_i))
                        calc_unbalance = round((max_dev / avg_i) * 100.0, 2)
                    else:
                        calc_unbalance = 0.0

                # Metric Cards
                col_cp1, col_cp2 = st.columns(2)
                with col_cp1:
                    is_ov = calc_load_pct > 80
                    st.markdown(f"""
                        <div class='kpi-card {"kpi-card-danger" if is_ov else "kpi-card-success"}' style='padding: 12px; margin-bottom: 8px;'>
                            <div class='kpi-title'>Total Beban</div>
                            <div class='kpi-value' style='font-size: 20px;'>{calc_load_kva} <span style='font-size: 12px;'>kVA</span></div>
                            <div class='kpi-desc'><b>{calc_load_pct}%</b> dari {tf_mload:.0f} kVA</div>
                        </div>
                    """, unsafe_allow_html=True)

                with col_cp2:
                    is_unb_crit = calc_unbalance > 20
                    is_unb_warn = 10 <= calc_unbalance <= 20
                    card_cls = "kpi-card-danger" if is_unb_crit else ("kpi-card-warning" if is_unb_warn else "kpi-card-success")
                    st.markdown(f"""
                        <div class='kpi-card {card_cls}' style='padding: 12px; margin-bottom: 8px;'>
                            <div class='kpi-title'>Ketidakseimbangan</div>
                            <div class='kpi-value' style='font-size: 20px;'>{calc_unbalance:.1f}%</div>
                            <div class='kpi-desc'>{"🔴 Kritis (>20%)" if is_unb_crit else ("🟠 Perhatian" if is_unb_warn else "🟢 Seimbang (<10%)")}</div>
                        </div>
                    """, unsafe_allow_html=True)

                # Comparative Phase Bar Preview
                if tf_phase != 1 and (m_arp > 0 or m_asp > 0 or m_atp > 0):
                    fig_prev = go.Figure()
                    fig_prev.add_trace(go.Bar(
                        x=['Fasa R', 'Fasa S', 'Fasa T', 'Netral N'],
                        y=[m_arp, m_asp, m_atp, m_anp],
                        marker_color=['#EF4444', '#F59E0B', '#10B981', '#64748B'],
                        text=[f"{m_arp:.1f}A", f"{m_asp:.1f}A", f"{m_atp:.1f}A", f"{m_anp:.1f}A"],
                        textposition='outside'
                    ))
                    fig_prev.update_layout(
                        height=200,
                        margin=dict(l=10, r=10, t=20, b=10),
                        yaxis_title="Arus (A)"
                    )
                    st.plotly_chart(fig_prev, use_container_width=True)

                # Action button
                btn_simpan_manual = st.button("💾 Simpan Pengukuran Manual ke Google Sheets", type="primary", use_container_width=True)
                if btn_simpan_manual:
                    with st.spinner("Menyimpan baris pengukuran ke RAW_MEA..."):
                        try:
                            creds = get_google_credentials()
                            gc = gspread.authorize(creds)
                            sheet_raw = gc.open("DATA TRAFO").worksheet("RAW_MEA")

                            # Build 77-column row
                            row_manual = [
                                str(m_tanggal),
                                str(m_waktu),
                                str(selected_code),
                                m_vrn, m_vsn, m_vtn,
                                m_vrs, m_vrt, m_vst,
                                m_arp, m_asp, m_atp, m_anp,
                                m_ar1 if 'm_ar1' in locals() else m_arp,
                                m_as1 if 'm_as1' in locals() else m_asp,
                                m_at1 if 'm_at1' in locals() else m_atp,
                                m_an1 if 'm_an1' in locals() else m_anp,
                                m_ar2 if 'm_ar2' in locals() else 0,
                                m_as2 if 'm_as2' in locals() else 0,
                                m_at2 if 'm_at2' in locals() else 0,
                                m_an2 if 'm_an2' in locals() else 0,
                                m_ar3 if 'm_ar3' in locals() else 0,
                                m_as3 if 'm_as3' in locals() else 0,
                                m_at3 if 'm_at3' in locals() else 0,
                                m_an3 if 'm_an3' in locals() else 0,
                                # Peaks
                                m_arp, m_asp, m_atp, m_anp,
                                m_ar1 if 'm_ar1' in locals() else m_arp,
                                m_as1 if 'm_as1' in locals() else m_asp,
                                m_at1 if 'm_at1' in locals() else m_atp,
                                m_an1 if 'm_an1' in locals() else m_anp,
                                m_ar2 if 'm_ar2' in locals() else 0,
                                m_as2 if 'm_as2' in locals() else 0,
                                m_at2 if 'm_at2' in locals() else 0,
                                m_an2 if 'm_an2' in locals() else 0,
                                m_ar3 if 'm_ar3' in locals() else 0,
                                m_as3 if 'm_as3' in locals() else 0,
                                m_at3 if 'm_at3' in locals() else 0,
                                m_an3 if 'm_an3' in locals() else 0,
                                # THD & H1 (24 zeros)
                                0, 0, 0, 0, 0, 0,
                                0, 0, 0, 0, 0, 0,
                                0, 0, 0, 0, 0, 0,
                                0, 0, 0, 0, 0, 0,
                                # ALA (12 zeros)
                                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                            ]

                            sheet_raw.append_row(row_manual)
                            st.cache_data.clear()
                            st.success(f"✅ Berhasil! Pengukuran manual untuk gardu {curr_trafo['TF_Name']} ({selected_code}) telah dicatat di Google Sheets (RAW_MEA). Status SPLN kini terbarui.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menyimpan pengukuran manual: {e}")

        # ---------------------------------------------------------
        # TAB 2: UPLOAD HIOKI PDF
        # ---------------------------------------------------------
        with tab_hioki:
            st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 8px;'>📄 Ekstraksi Otomatis Dokumen PDF Hioki PQA</div>", unsafe_allow_html=True)
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                input_tanggal = st.date_input("Tanggal Pengukuran Lapangan", value=datetime.today(), key="hioki_tgl")
            with col_w2:
                input_waktu = st.time_input("Waktu Pengukuran Lapangan", value=datetime.now().time(), key="hioki_jam")

            uploaded_file = st.file_uploader("Unggah File PDF Laporan Hioki", type=["pdf"], key="hioki_pdf")

            if uploaded_file is not None:
                st.info(f"File siap diproses: **{uploaded_file.name}** ({round(len(uploaded_file.getvalue())/1024, 1)} KB)")

                if st.button("📤 Ekstrak Data & Simpan ke Database Google Sheets", type="primary", use_container_width=True, key="btn_hioki_save"):
                    with st.spinner("Sedang membaca PDF dan menjalankan ekstraksi AI Gemini..."):
                        try:
                            status_ok, pesan = bot_hioki.proses_pdf_ke_sheets(
                                file_bytes=uploaded_file.getvalue(),
                                tf_code=selected_code,
                                tanggal=input_tanggal.strftime("%Y-%m-%d"),
                                waktu=input_waktu.strftime("%H:%M:%S")
                            )

                            if status_ok:
                                st.success(f"✅ Selesai! {pesan}")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ Ekstraksi Gagal: {pesan}")

                        except Exception as e:
                            st.error(f"Terjadi kesalahan sistem: {e}")
    else:
        st.info("👆 Silakan pilih salah satu gardu terlebih dahulu.")


# ==========================================
# PAGE 6: EDIT DATA TRAFO (INFO_DATA)
# ==========================================
elif menu_selection == "✏️ Edit Data Trafo":

    st.markdown("""
        <div style='background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-bottom: 20px;'>
            <h2 style='margin: 0 0 6px 0; font-size: 22px; color: #0F172A; font-weight: 800;'>
                ✏️ Pembaruan Master Data Gardu (INFO_DATA)
            </h2>
            <div style='font-size: 13px; color: #64748B;'>
                Perbarui data statis transformator: Nama, Koordinat GPS, Kapasitas Pengenal (kVA), Tipe Fasa, dan Konstruksi tiang.
            </div>
        </div>
    """, unsafe_allow_html=True)

    valid_trafo_list = df.dropna(subset=['TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code'])
    trafo_options = dict(zip(valid_trafo_list['TF_Code'], valid_trafo_list['TF_Name']))

    selected_code = st.selectbox(
        "🔍 Cari dan Pilih Gardu yang Ingin Diedit:",
        options=["-- Pilih Gardu --"] + list(trafo_options.keys()),
        format_func=lambda x: f"{trafo_options[x]} ({x})" if x != "-- Pilih Gardu --" else x
    )

    if selected_code != "-- Pilih Gardu --":
        curr_data = df[df['TF_Code'] == selected_code].iloc[0]

        with st.form("form_edit_master_trafo"):
            st.markdown(f"### Detail Master: {curr_data['TF_Name']} ({selected_code})")

            col_edit1, col_edit2 = st.columns(2)

            with col_edit1:
                st.text_input("Nomor / Kode Gardu (TF_Code)", value=selected_code, disabled=True)
                new_name = st.text_input("Nama Gardu (TF_Name)", value=curr_data.get('TF_Name', ''))
                curr_cap = float(curr_data.get('TF_MLoad', 50) or 50)
                new_capacity = st.number_input("Kapasitas Pengenal / Max Load (kVA)", value=curr_cap, step=25.0)

            with col_edit2:
                curr_coord = str(curr_data.get('TF_Coordinate', ''))
                new_coordinate = st.text_input("Koordinat (Latitude, Longitude)", value=curr_coord)
                
                curr_phase = int(curr_data.get('TF_Phase', 3) or 3)
                new_phase = st.selectbox("Tipe Fasa", [1, 3], index=0 if curr_phase == 1 else 1)

                curr_const = str(curr_data.get('TF_Construction', 'Cantol'))
                const_opts = ["Cantol", "Portal", "BETON"]
                const_idx = const_opts.index(curr_const) if curr_const in const_opts else 0
                new_construction = st.selectbox("Jenis Konstruksi", const_opts, index=const_idx)

            submit_save = st.form_submit_button("💾 Simpan Pembaruan Profil ke Google Sheets", type="primary", use_container_width=True)

        if submit_save:
            with st.spinner("Memperbarui data master pada sheet INFO_DATA..."):
                try:
                    creds = get_google_credentials()
                    gc = gspread.authorize(creds)
                    sheet_info = gc.open("DATA TRAFO").worksheet("INFO_DATA")

                    cell = sheet_info.find(str(selected_code), in_column=1)

                    if cell:
                        row_idx = cell.row
                        sheet_info.update_cell(row_idx, 2, new_name)
                        sheet_info.update_cell(row_idx, 3, new_coordinate)
                        sheet_info.update_cell(row_idx, 4, new_capacity)
                        sheet_info.update_cell(row_idx, 5, new_phase)
                        sheet_info.update_cell(row_idx, 6, new_construction)

                        st.cache_data.clear()
                        st.success(f"✅ Profil Gardu '{new_name}' ({selected_code}) berhasil diperbarui!")
                    else:
                        st.error(f"❌ Kode gardu {selected_code} tidak ditemukan di INFO_DATA.")

                except Exception as e:
                    st.error(f"Terjadi kesalahan saat menyambung ke database: {e}")
    else:
        st.info("👆 Silakan pilih salah satu gardu di atas untuk mengedit profilnya.")