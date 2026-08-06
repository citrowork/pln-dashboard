import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import bot_hioki
from streamlit_option_menu import option_menu

# Set the webpage to wide mode
st.set_page_config(layout="wide", page_title="Mantra MOA", page_icon="⚡")

# --- CSS TO REDUCE TOP PADDING ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
        }
    </style>
""", unsafe_allow_html=True)
# ---------------------------------

st.markdown("---")

# --- LOADING DATABASE DAN INPUT VARIABLE (INFO_DATA & RAW_MEA) ---
@st.cache_data(ttl=60)
def load_data():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    gc = gspread.authorize(credentials)   
    sh = gc.open("DATA TRAFO")

    raw_mea_data = sh.worksheet("RAW_MEA").get_all_records()
    df_raw = pd.DataFrame(raw_mea_data)

    info_data = sh.worksheet("INFO_DATA").get_all_records()
    df_info = pd.DataFrame(info_data)

    if not df_raw.empty:
        df_raw['Parsed_Date_Temp'] = pd.to_datetime(df_raw['Date'].astype(str) + ' ' + df_raw['Time'].astype(str), errors='coerce')
        df_raw = df_raw.sort_values(by='Parsed_Date_Temp', ascending=True)
        df_raw = df_raw.drop_duplicates(subset=['TF_Code'], keep='last')
        df_raw = df_raw.drop(columns=['Parsed_Date_Temp'])

    if not df_raw.empty and not df_info.empty:
        df = pd.merge(df_raw, df_info, on="TF_Code", how="right")
    else:
        df = df_raw
        
    df = df.dropna(subset=['TF_Name'])
    
    current_columns = [
        'A_R_P', 'A_S_P', 'A_T_P', 
        'A_R_1', 'A_S_1', 'A_T_1', 
        'A_R_2', 'A_S_2', 'A_T_2', 
        'A_R_3', 'A_S_3', 'A_T_3'
    ]
    
    for col in current_columns:
        ala_col = f"ALA_{col[2:]}"
        if col in df.columns and ala_col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) + pd.to_numeric(df[ala_col], errors='coerce').fillna(0)
        elif col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'TF_Coordinate' in df.columns:
        coords = df['TF_Coordinate'].str.split(',', expand=True)
        df['latitude'] = pd.to_numeric(coords[0], errors='coerce')
        df['longitude'] = pd.to_numeric(coords[1], errors='coerce')
        
    if all(col in df.columns for col in ['A_R_P', 'A_S_P', 'A_T_P']):
        df['Avg_Current'] = (df['A_R_P'] + df['A_S_P'] + df['A_T_P']) / 3
        df['Dev_R'] = abs(df['A_R_P'] - df['Avg_Current'])
        df['Dev_S'] = abs(df['A_S_P'] - df['Avg_Current'])
        df['Dev_T'] = abs(df['A_T_P'] - df['Avg_Current'])
        df['Max_Dev'] = df[['Dev_R', 'Dev_S', 'Dev_T']].max(axis=1)
        df['Unbalance (%)'] = np.where(df['Avg_Current'] == 0, 0, (df['Max_Dev'] / df['Avg_Current']) * 100)
        df['Unbalance (%)'] = df['Unbalance (%)'].round(2)

    cols_to_numeric = ['V_RN', 'V_SN', 'V_TN', 'A_R_P', 'A_S_P', 'A_T_P']
    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if all(col in df.columns for col in ['A_R_P', 'A_S_P', 'A_T_P', 'V_RN', 'V_SN', 'V_TN']):
        df['Current Load'] = ((df['V_RN'] * df['A_R_P']) + 
                              (df['V_SN'] * df['A_S_P']) + 
                              (df['V_TN'] * df['A_T_P'])) / 1000
        df['Current Load'] = df['Current Load'].round(1)
        
    if 'TF_MLoad' in df.columns:
        df['TF_MLoad'] = pd.to_numeric(df['TF_MLoad'], errors='coerce')

    if 'Current Load' in df.columns and 'TF_MLoad' in df.columns:
        df['Load Percentage'] = np.where(
            df['TF_MLoad'] > 0, 
            (df['Current Load'] / df['TF_MLoad']) * 100, 
            0
        )
        df['Load Percentage'] = df['Load Percentage'].round(1)
    # Perhitungan Health Trafo
    cols_to_check = ['THD_R_P', 'H1_R_P', 'THD_S_P', 'H1_S_P', 'THD_T_P', 'H1_T_P']
    for col in cols_to_check:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if all(col in df.columns for col in cols_to_check):

        df['H1_Total'] = df['H1_R_P'] + df['H1_S_P'] + df['H1_T_P']
        df['Weighted_THD'] = np.where(
            df['H1_Total'] > 0,
            ((df['THD_R_P'] * df['H1_R_P']) + 
            (df['THD_S_P'] * df['H1_S_P']) + 
            (df['THD_T_P'] * df['H1_T_P'])) / df['H1_Total'],
            0
    )
        calculated_health = 100 - ((df['Weighted_THD'] - 5).clip(lower=0) * 1.5)
        df['Health Score'] = np.clip(calculated_health, 0, 100).fillna(100).astype(int)

    else:
        df['Health Score'] = 100 

    front_cols = [
        'TF_Code', 
        'TF_Name', 
        'TF_Coordinate', 
        'TF_MLoad', 
        'TF_Phase', 
        'TF_Construction', 
        'Date', 
        'Time'
    ]
    
    # Pastikan kolom utama ada di dataframe (mencegah error jika data kosong)
    front_cols = [col for col in front_cols if col in df.columns]
    
    # 2. Ambil seluruh sisa kolom lainnya (data pengukuran, ALA, dsb.)
    remaining_cols = [col for col in df.columns if col not in front_cols]
    
    # 3. Terapkan urutan baru ke dataframe
    df = df[front_cols + remaining_cols]

    return df

df = load_data()

# ==========================================
# SIDEBAR NAVIGATION MENU
# ==========================================
with st.sidebar:
    st.markdown("""
        <h1 style='font-size: 30px; font-weight: 900; margin-bottom: 20px;'>⚡ Menu Utama</h1>
    """, unsafe_allow_html=True)

    menu_selection = option_menu(
        menu_title=None, 
        options=[
            "📊 Dashboard Utama", 
            "🔌 Simulasi Yanbung", 
            "📥 Input Pengukuran Gardu",
            "📈 Riwayat Trafo",
            "✏️ Edit Data Trafo",
            "📋 Data Semua Trafo"
        ],
        icons=['', '', '', '', ''],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"display": "none"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "4px 0px",
                "padding": "12px 15px",
                "border-radius": "8px",
                "--hover-color": "rgba(255, 255, 255, 0.05)"
            },
            "nav-link-selected": {
                "background-color": "#ff4b4b",
                "color": "white",
                "font-weight": "bold"
            }
        }
    )

# ==========================================
# PAGE 1: MAIN DASHBOARD
# ==========================================
if menu_selection == "📊 Dashboard Utama":
    
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        st.markdown(f"""
            <h3 style='margin-bottom: 0px;'>📦 Total Trafo</h3>
            <h1 style='font-size: 170px; font-weight: bold; margin-top: -60px; margin-bottom: 0px; color: #2e353e;'>{len(df)}</h1>
        """, unsafe_allow_html=True)

    with col2:
            st.markdown("<h3 style='margin-bottom: -30px;'>🔔 Pengukuran Trafo</h3>", unsafe_allow_html=True)
            if 'Date' in df.columns:
                df['Parsed_Date'] = pd.to_datetime(df['Date'], errors='coerce')
                batas_waktu = pd.to_datetime('today') - pd.DateOffset(months=6)

                unmeasured_df = df[df['Parsed_Date'].isna() | (df['Parsed_Date'] < batas_waktu)].copy()
                unmeasured_df = unmeasured_df.sort_values(by='Parsed_Date', ascending=True, na_position='first')
                
                st.metric(
                    label=" ",
                    value=len(unmeasured_df),
                    delta="Trafo Belum Diukur" if len(unmeasured_df) > 0 else "Aman",
                    delta_color="inverse"
                )
                
                with st.expander("⏳ List Trafo Belum/Lewat Ukur"):
                    if len(unmeasured_df) > 0:
                        display_df = unmeasured_df[['TF_Code', 'TF_Name', 'Date']].copy()
                        display_df['Date'] = display_df['Date'].fillna('Belum Pernah Diukur')
                        st.dataframe(display_df, hide_index=True)
                    else:
                        st.success("Semua trafo telah diukur dalam 6 bulan terakhir!")
            else:
                st.metric(label="Trafo Belum Diukur", value="N/A")

    with col3:
        st.subheader("📍 Peta Lokasi Trafo")
        if 'latitude' in df.columns and 'longitude' in df.columns:
            st.map(df[['latitude', 'longitude']], height=250) 

    st.markdown("---")

    col4, col5, col6 = st.columns(3)

    with col4:
        st.subheader("📊 Trafo Tidak Seimbang")
        if 'Unbalance (%)' in df.columns and 'TF_Name' in df.columns:
            unbalanced_df = df.sort_values(by='Unbalance (%)', ascending=False).head(10)
            fig_unbalance = px.bar(
                unbalanced_df, 
                x='TF_Name', 
                y='Unbalance (%)',
                color='Unbalance (%)',
                color_continuous_scale='Reds'
            )
            fig_unbalance.update_xaxes(title_text="", tickangle=-45)
            fig_unbalance.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_unbalance, use_container_width=True)

    with col5:
        st.subheader("📉 Beban Trafo")
        if 'Load Percentage' in df.columns and 'TF_Name' in df.columns:
            capacity_df = df.sort_values(by='Load Percentage', ascending=False).head(10)
            fig_capacity = px.bar(
                capacity_df,
                x='TF_Name',
                y='Load Percentage',
                color='Load Percentage',
                color_continuous_scale='Blues',
                labels={'Load Percentage': 'Kapasitas Terpakai (%)'}
            )
            fig_capacity.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Batas Aman (80%)", annotation_position="top right")
            max_load = capacity_df['Load Percentage'].max()
            y_max = max(100, max_load + 10) if pd.notna(max_load) else 100
            fig_capacity.update_yaxes(range=[0, y_max])
            fig_capacity.update_xaxes(title_text="", tickangle=-45)
            fig_capacity.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_capacity, use_container_width=True)

    with col6:
        st.subheader("🏥 Kesehatan Trafo")
        if 'Health Score' in df.columns:
            bins = [0, 20, 40, 60, 80, 100]
            labels = ['0-20', '21-40', '41-60', '61-80', '81-100']
            df['Health Segment'] = pd.cut(df['Health Score'], bins=bins, labels=labels, include_lowest=True)
            segment_counts = df['Health Segment'].value_counts().reset_index()
            segment_counts.columns = ['Segment', 'Count']
            
            fig_health = px.pie(segment_counts, names='Segment', values='Count', hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
            fig_health.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_health, use_container_width=True)

# ==========================================
# PAGE 2: YANBUNG SIMULATOR
# ==========================================
elif menu_selection == "🔌 Simulasi Yanbung":
    
    st.markdown("""
        <h2 style='font-size: 32px; margin-top: 0px; margin-bottom: 0px;'>🔌 Simulasi Beban & Keseimbangan Pasang Baru</h2>
        <hr style='margin-top: 10px; margin-bottom: 15px; border: none; border-top: 1px solid rgba(128, 128, 128, 0.4);'>
    """, unsafe_allow_html=True)
    
    st.info("Masukkan koordinat hasil survei lapangan untuk merekomendasikan 3 trafo terdekat, atau pilih langsung secara manual.")

    col_coord1, col_coord2 = st.columns(2)
    with col_coord1:
        survei_lat = st.number_input("Latitude Titik Survei", value=-8.150000, format="%.6f")
    with col_coord2:
        survei_lon = st.number_input("Longitude Titik Survei", value=127.790000, format="%.6f")

    if 'latitude' in df.columns and 'longitude' in df.columns:
        valid_loc_df = df.dropna(subset=['latitude', 'longitude', 'TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code']).copy()

        lat1, lon1 = np.radians(survei_lat), np.radians(survei_lon)
        lat2, lon2 = np.radians(valid_loc_df['latitude']), np.radians(valid_loc_df['longitude'])

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        r = 6371
        
        valid_loc_df['Jarak_KM'] = c * r
        valid_loc_df['Jarak_Meter'] = (valid_loc_df['Jarak_KM'] * 1000).round(1)
        
        # Urutkan berdasarkan jarak terdekat dan ambil 3 teratas
        nearest_traframes = valid_loc_df.sort_values(by='Jarak_KM').head(3)
        
        st.markdown("#### 📍 Rekomendasi 3 Trafo Terdekat dari Lokasi Survei:")
        rec_cols = st.columns(3)
        for idx, (_, row) in enumerate(nearest_traframes.iterrows()):
            with rec_cols[idx]:
                st.metric(
                    label=f"{row['TF_Name']} ({row['TF_Code']})",
                    value=f"{row['Jarak_Meter']} meter",
                    delta="Terdekat" if idx == 0 else None,
                    delta_color="normal"
                )
    
    st.markdown("---")
    
    col_input1, col_input2, col_input3, col_input4 = st.columns(4)
    
    with col_input1:
        valid_df = df.dropna(subset=['TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code'])
        trafo_mapping = dict(zip(valid_df['TF_Code'], valid_df['TF_Name']))
        
        def format_trafo(code):
            return f"{trafo_mapping[code]} ({code})"
            
        selected_code = st.selectbox("Pilih Transformator (atau sesuaikan rekomendasi)", options=list(trafo_mapping.keys()), format_func=format_trafo)
        
    with col_input2:
        new_power_va = st.selectbox("Daya Pelanggan Baru (VA)", [450, 900, 1300, 2200, 3500, 4400, 5500, 6600, 7700])
        
    with col_input3:
        target_phase = st.radio("Sambungkan ke Fasa", ["R", "S", "T"], horizontal=True)

    with col_input4:
        target_jalur = st.radio("Pilih Jalur JTR", ["1", "2", "3"], horizontal=True)

    # Mengambil data menggunakan TF_Code
    trafo_data = df[df['TF_Code'] == selected_code].iloc[0]
    selected_trafo = trafo_data.get('TF_Name', 'Unknown') 
    
    if all(col in trafo_data for col in ['A_R_P', 'A_S_P', 'A_T_P', 'Current Load']):
        pangkal_col = f"A_{target_phase}_P"
        jalur_col = f"A_{target_phase}_{target_jalur}"
        
        raw_jalur_val = trafo_data.get(jalur_col, 0.0)
        current_jalur_amp = float(raw_jalur_val) if pd.notna(raw_jalur_val) and str(raw_jalur_val).strip() != '' else 0.0
        
        raw_r = trafo_data.get('A_R_P', 0.0)
        r_amp = float(raw_r) if pd.notna(raw_r) and str(raw_r).strip() != '' else 0.0
        
        raw_s = trafo_data.get('A_S_P', 0.0)
        s_amp = float(raw_s) if pd.notna(raw_s) and str(raw_s).strip() != '' else 0.0
        
        raw_t = trafo_data.get('A_T_P', 0.0)
        t_amp = float(raw_t) if pd.notna(raw_t) and str(raw_t).strip() != '' else 0.0
        
        st.info(f"⚡ **Kondisi Eksisting (Termasuk Akumulasi Yanbung Sebelumnya):** Arus pada jalur **{jalur_col}** saat ini adalah **{current_jalur_amp:.2f} A**.")
        
        voltage_estimate = 230 
        demand_factor = 0.60  
        added_ampere = (new_power_va * demand_factor) / voltage_estimate
        added_kva = (new_power_va * demand_factor) / 1000
        
        new_jalur = current_jalur_amp + added_ampere
        new_r_amp = r_amp + added_ampere if target_phase == "R" else r_amp
        new_s_amp = s_amp + added_ampere if target_phase == "S" else s_amp
        new_t_amp = t_amp + added_ampere if target_phase == "T" else t_amp
        new_pangkal = new_r_amp if target_phase == "R" else (new_s_amp if target_phase == "S" else new_t_amp)
        
        new_avg = (new_r_amp + new_s_amp + new_t_amp) / 3
        new_max_dev = max(abs(new_r_amp - new_avg), abs(new_s_amp - new_avg), abs(new_t_amp - new_avg))
        predicted_unbalance = 0 if new_avg == 0 else round((new_max_dev / new_avg) * 100, 2)
        
        base_load = trafo_data.get('Current Load', 0.0)
        base_load_val = float(base_load) if pd.notna(base_load) and str(base_load).strip() != '' else 0.0
        predicted_load = round(base_load_val + added_kva, 1)
        
        st.markdown("### Hasil Prediksi")
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric(label="Prediksi Total Load (kVA)", value=f"{predicted_load} kVA", delta=f"+{round(added_kva, 2)} kVA", delta_color="inverse")
        with res_col2:
            current_unbalance = trafo_data.get('Unbalance (%)', 0.0)
            current_unbalance_val = float(current_unbalance) if pd.notna(current_unbalance) and str(current_unbalance).strip() != '' else 0.0
            unbalance_diff = round(predicted_unbalance - current_unbalance_val, 2)
            st.metric(label="Prediksi Unbalance Fasa (%)", value=f"{predicted_unbalance}%", delta=f"{unbalance_diff}%", delta_color="inverse")
            
        st.markdown(f"#### Detail Perubahan Arus (Asumsi Beban {int(demand_factor*100)}%)")
        amp_df = pd.DataFrame({
            "Titik Pengukuran": [
                "Pangkal R (A_R_P)", 
                "Pangkal S (A_S_P)", 
                "Pangkal T (A_T_P)", 
                f"Jalur Pilihan ({jalur_col})"
            ],
            "Sebelum (Ampere)": [r_amp, s_amp, t_amp, current_jalur_amp],
            "Sesudah Prediksi (Ampere)": [new_r_amp, new_s_amp, new_t_amp, new_jalur]
        }).round(2)
        
        def highlight_jalur(s):
            return ['background-color: rgba(46, 204, 113, 0.2)' if i == 3 else '' for i in range(len(s))]
            
        st.table(amp_df.style.apply(highlight_jalur, axis=0))
        
        # --- TOMBOL SAVE KE RAW_MEA (MENGUPDATE KOLOM ALA) ---
        st.markdown("---")
        if st.button("💾 Simpan Prediksi", type="primary", use_container_width=True):
            with st.spinner("Menyimpan penambahan beban ke database..."):
                try:
                    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
                    gc = gspread.authorize(credentials)
                    
                    sh = gc.open("DATA TRAFO")
                    sheet_raw = sh.worksheet("RAW_MEA")
                    
                    tf_code = trafo_data.get('TF_Code')
                    
                    all_raw_records = sheet_raw.get_all_records()
                    headers = sheet_raw.row_values(1)
                    
                    target_row_idx = None
                    for idx, row in enumerate(all_raw_records):
                        if str(row.get('TF_Code')) == str(tf_code):
                            target_row_idx = idx + 2
                            
                    if target_row_idx:
                        ala_col_name_pangkal = f"ALA_{target_phase}_P" 
                        ala_col_name_jalur = f"ALA_{target_phase}_{target_jalur}"
                        
                        if ala_col_name_pangkal in headers and ala_col_name_jalur in headers:
                            idx_ala_pangkal = headers.index(ala_col_name_pangkal) + 1
                            idx_ala_jalur = headers.index(ala_col_name_jalur) + 1
                            
                            current_ala_pangkal = float(sheet_raw.cell(target_row_idx, idx_ala_pangkal).value or 0)
                            current_ala_jalur = float(sheet_raw.cell(target_row_idx, idx_ala_jalur).value or 0)
                            
                            delta_ampere = added_ampere
                            
                            new_ala_pangkal = current_ala_pangkal + delta_ampere
                            new_ala_jalur = current_ala_jalur + delta_ampere
                            
                            sheet_raw.update_cell(target_row_idx, idx_ala_pangkal, round(new_ala_pangkal, 2))
                            sheet_raw.update_cell(target_row_idx, idx_ala_jalur, round(new_ala_jalur, 2))
                            
                            load_data.clear()
                            st.success(f"✅ Berhasil! Penambahan arus sebesar {delta_ampere:.2f}A telah diakumulasikan ke kolom ALA pada baris pengukuran terbaru gardu {selected_trafo}.")
                        else:
                            st.error(f"❌ Gagal: Kolom ALA '{ala_col_name_pangkal}' atau '{ala_col_name_jalur}' tidak ditemukan di header RAW_MEA.")
                    else:
                        st.error(f"❌ Gagal: Riwayat pengukuran untuk Trafo '{selected_trafo}' tidak ditemukan di RAW_MEA.")
                        
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat menyambung ke Google Sheets: {e}")
    st.markdown("---")

# ==========================================
# PAGE 3: DATA SEMUA TRAFO
# ==========================================
elif menu_selection == "📋 Data Semua Trafo":
    
    st.markdown("""
        <h2 style='font-size: 32px; margin-top: 0px; margin-bottom: 0px;'>📋 Data Keseluruhan Trafo</h2>
        <hr style='margin-top: 10px; margin-bottom: 15px; border: none; border-top: 1px solid rgba(128, 128, 128, 0.4);'>
    """, unsafe_allow_html=True)
    
    st.info("Menampilkan seluruh data gabungan. 💡 Klik pada baris mana saja untuk menyorot (highlight) data tersebut.")
    
    # Tambahkan parameter selection_mode dan on_select untuk mengaktifkan highlight
    st.dataframe(
        df,  
        use_container_width=True,
        selection_mode="single-row", # Mengaktifkan mode seleksi baris (ubah ke "multi-row" jika ingin bisa klik banyak baris)
        on_select="rerun"           # "ignore" berarti kita hanya butuh efek visualnya saja tanpa men-trigger fungsi Python lain
    )
    st.markdown("---")

# ==========================================
# PAGE 4: EDIT DATA TRAFO (INFO_DATA)
# ==========================================
elif menu_selection == "✏️ Edit Data Trafo":
    
    st.markdown("""
        <h2 style='font-size: 32px; margin-top: 0px; margin-bottom: 0px;'>✏️ Edit Profil Gardu</h2>
        <hr style='margin-top: 10px; margin-bottom: 15px; border: none; border-top: 1px solid rgba(128, 128, 128, 0.4);'>
    """, unsafe_allow_html=True)
    
    st.info("Cari gardu berdasarkan **Nomor (TF_Code)** atau **Nama (TF_Name)** untuk memperbarui data master pada database.")
    
    # 1. PEMILIHAN GARDU
    valid_df = df.dropna(subset=['TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code'])
    trafo_mapping = dict(zip(valid_df['TF_Code'], valid_df['TF_Name']))
    
    def format_trafo(code):
        if code == "-- Pilih Gardu --":
            return code
        return f"{trafo_mapping[code]} ({code})"
        
    selected_code_from_dropdown = st.selectbox(
        "🔍 Cari dan Pilih Gardu:", 
        options=["-- Pilih Gardu --"] + list(trafo_mapping.keys()), 
        format_func=format_trafo
    )
    
    selected_code = None
    if selected_code_from_dropdown != "-- Pilih Gardu --":
        selected_code = selected_code_from_dropdown
        current_data = df[df['TF_Code'] == selected_code].iloc[0]
    
    if selected_code:
        with st.form("form_edit_trafo"):
            st.markdown(f"### Detail Profil: {current_data.get('TF_Name', '')} ({selected_code})")
            
            col_form_top1, col_form_top2 = st.columns(2)
            with col_form_top1:
                st.text_input("Nomor Gardu (TF_Code - Primary Key)", value=selected_code, disabled=True)
            with col_form_top2:
                curr_name = current_data.get('TF_Name', '')
                new_name = st.text_input("Nama Gardu (TF_Name)", value="" if pd.isna(curr_name) else curr_name)
            
            col_form1, col_form2 = st.columns(2)
            with col_form1:
                curr_max = current_data.get('TF_MLoad', 0)
                curr_max = 0.0 if pd.isna(curr_max) else float(curr_max)
                new_max_load = st.number_input("Maximal Load (kVA)", value=curr_max, step=25.0)
                
                curr_phase = current_data.get('TF_Phase', 3)
                curr_phase = 3 if pd.isna(curr_phase) else int(curr_phase)
                new_phase = st.selectbox("Tipe Fasa", [1, 3], index=0 if curr_phase == 1 else 1)
                
            with col_form2:
                curr_coord = current_data.get('TF_Coordinate', '')
                curr_coord = "" if pd.isna(curr_coord) else curr_coord
                new_coord = st.text_input("Koordinat (Latitude, Longitude)", value=curr_coord)
                
                curr_const = current_data.get('TF_Construction', 'Cantol')
                curr_const = "Cantol" if pd.isna(curr_const) else str(curr_const)
                const_options = ["Cantol", "Portal"]
                const_index = const_options.index(curr_const) if curr_const in const_options else 0
                new_construction = st.selectbox("Jenis Konstruksi (TF_Construction)", const_options, index=const_index)
            
            submit_edit = st.form_submit_button("💾 Simpan Pembaruan Master Data", type="primary")
            
        if submit_edit:
            with st.spinner("Menyimpan ke database..."):
                try:
                    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
                    gc = gspread.authorize(credentials)
                    
                    sheet_info = gc.open("DATA TRAFO").worksheet("INFO_DATA")
                    cell = sheet_info.find(str(selected_code), in_column=1)
                    
                    if cell:
                        row_idx = cell.row
                        sheet_info.update_cell(row_idx, 2, new_name)
                        sheet_info.update_cell(row_idx, 3, new_coord)
                        sheet_info.update_cell(row_idx, 4, new_max_load)
                        sheet_info.update_cell(row_idx, 5, new_phase)
                        sheet_info.update_cell(row_idx, 6, new_construction)
                        
                        load_data.clear()
                        st.success(f"✅ Profil Gardu '{new_name}' (Kode: {selected_code}) berhasil diperbarui di INFO_DATA!")
                    else:
                        st.error(f"❌ Gagal: Kode '{selected_code}' tidak ditemukan di sheet INFO_DATA.")
                        
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat menyambung ke database: {e}")
    else:
        st.info("👆 Silakan pilih salah satu gardu melalui kotak pencarian **Nomor (TF_Code)** atau **Nama (TF_Name)** di atas untuk mulai mengedit.")
    st.markdown("---")

# ==========================================
# PAGE 5: INPUT PENGUKURAN GARDU (UPLOAD PDF)
# ==========================================
elif menu_selection == "📥 Input Pengukuran Gardu":
    import bot_hioki # Pastikan modul ini ter-import
    from datetime import timedelta # Pastikan ini ada jika menggunakan timedelta, atau pakai step=1800
    
    st.markdown("""
        <h2 style='font-size: 32px; margin-top: 0px; margin-bottom: 0px;'>📥 Input Laporan Pengukuran</h2>
        <hr style='margin-top: 10px; margin-bottom: 15px; border: none; border-top: 1px solid rgba(128, 128, 128, 0.4);'>
    """, unsafe_allow_html=True)
    
    st.info("Pilih gardu, tentukan waktu pengukuran, dan unggah file PDF Hioki. File akan diekstrak oleh AI dan otomatis terkirim di database.")
    
# 1. PEMILIHAN GARDU
    valid_df = df.dropna(subset=['TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code'])
    trafo_mapping = dict(zip(valid_df['TF_Code'], valid_df['TF_Name']))
    
    def format_trafo(code):
        if code == "-- Pilih Gardu --":
            return code
        return f"{trafo_mapping[code]} ({code})"
        
    selected_code_from_dropdown = st.selectbox(
        "🔍 Cari dan Pilih Gardu:", 
        options=["-- Pilih Gardu --"] + list(trafo_mapping.keys()), 
        format_func=format_trafo
    )
    
    selected_code = None
    if selected_code_from_dropdown != "-- Pilih Gardu --":
        selected_code = selected_code_from_dropdown
        current_data = df[df['TF_Code'] == selected_code].iloc[0]
        
    # 2. INPUT WAKTU & FORM UPLOAD
    if selected_code:
        st.markdown(f"### 📄 Upload Dokumen untuk: **{current_data.get('TF_Name', '')} ({selected_code})**")
        
        # Penambahan Input Manual Tanggal dan Waktu
        col_waktu1, col_waktu2 = st.columns(2)
        with col_waktu1:
            input_tanggal = st.date_input("Tanggal Pengukuran di Lapangan")
        with col_waktu2:
            input_waktu = st.time_input("Jam Pengukuran di Lapangan", step=1800)

        uploaded_file = st.file_uploader("Unggah Laporan PDF Hioki", type=["pdf"])
        
        if uploaded_file is not None:
            if st.button("📤 Ekstrak & Proses Laporan", type="primary"):
                with st.spinner("Membaca file PDF dan menjalankan AI..."):
                    try:
                        # Kita langsung by-pass Google Drive Upload dan langsung mengekstrak data!
                        status_ok, pesan = bot_hioki.proses_pdf_ke_sheets(
                            file_bytes=uploaded_file.getvalue(), 
                            tf_code=selected_code, 
                            tanggal=input_tanggal.strftime("%Y-%m-%d"), 
                            waktu=input_waktu.strftime("%H:%M:%S")
                        )
                        
                        if status_ok:
                            st.success(f"✅ Selesai! {pesan}")
                            load_data.clear() # Segarkan cache dashboard
                        else:
                            st.error(f"❌ Ekstraksi Gagal: {pesan}")
                            
                    except Exception as e:
                        st.error(f"❌ Terjadi kesalahan sistem: {e}")
    else:
        st.info("👆 Silakan pilih salah satu gardu terlebih dahulu.")
    st.markdown("---")

# ==========================================
# PAGE 6: RIWAYAT PENGUKURAN TRAFO
# ==========================================
elif menu_selection == "📈 Riwayat Trafo":
    
    st.markdown("""
        <h2 style='font-size: 32px; margin-top: 0px; margin-bottom: 0px;'>📈 Riwayat Pengukuran Gardu</h2>
        <hr style='margin-top: 10px; margin-bottom: 15px; border: none; border-top: 1px solid rgba(128, 128, 128, 0.4);'>
    """, unsafe_allow_html=True)
    
    st.info("Pilih gardu untuk melacak lokasi, kapasitas, tren grafik pengukuran, dan riwayat tabel secara lengkap.")

    # 1. Bikin Cache Data Khusus Riwayat (Tanpa Drop Duplicates)
    @st.cache_data(ttl=60)
    def load_history_data():
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(credentials)   
        sh = gc.open("DATA TRAFO")
        
        raw_mea = pd.DataFrame(sh.worksheet("RAW_MEA").get_all_records())
        info_data = pd.DataFrame(sh.worksheet("INFO_DATA").get_all_records())
        
        df_hist = pd.merge(raw_mea, info_data, on="TF_Code", how="right")
        df_hist = df_hist.dropna(subset=['TF_Name'])
        return df_hist

    with st.spinner("Memuat data riwayat..."):
        df_history = load_history_data()

    # 2. Selector Gardu
    valid_df = df_history.dropna(subset=['TF_Code', 'TF_Name']).drop_duplicates(subset=['TF_Code'])
    trafo_mapping = dict(zip(valid_df['TF_Code'], valid_df['TF_Name']))
    
    def format_trafo(code):
        return f"{trafo_mapping[code]} ({code})"
        
    selected_code = st.selectbox("🔍 Pilih Transformator:", ["-- Pilih Gardu --"] + list(trafo_mapping.keys()), format_func=lambda x: format_trafo(x) if x != "-- Pilih Gardu --" else x)

    if selected_code != "-- Pilih Gardu --":
        # 3. Filter & Kalkulasi Ulang KHUSUS untuk trafo yang dipilih (agar web tetap ringan)
        hist_trafo = df_history[df_history['TF_Code'] == selected_code].copy()
        hist_trafo = hist_trafo.dropna(subset=['Date']) # Buang baris jika belum pernah diukur
        
        if hist_trafo.empty:
            st.warning("⚠️ Gardu ini belum memiliki riwayat pengukuran di lapangan.")
        else:
            # Urutkan secara kronologis
            hist_trafo['Parsed_Date_Temp'] = pd.to_datetime(hist_trafo['Date'].astype(str) + ' ' + hist_trafo['Time'].astype(str), errors='coerce')
            hist_trafo = hist_trafo.sort_values(by='Parsed_Date_Temp', ascending=True)
            hist_trafo['Tanggal & Waktu'] = hist_trafo['Date'].astype(str) + " | " + hist_trafo['Time'].astype(str)

            # Ekstrak Koordinat
            if 'TF_Coordinate' in hist_trafo.columns:
                coords = hist_trafo['TF_Coordinate'].str.split(',', expand=True)
                hist_trafo['latitude'] = pd.to_numeric(coords[0], errors='coerce')
                hist_trafo['longitude'] = pd.to_numeric(coords[1], errors='coerce')
                
            # Konversi tipe data
            cols_num = ['A_R_P', 'A_S_P', 'A_T_P', 'V_RN', 'V_SN', 'V_TN', 'TF_MLoad', 'THD_R_P', 'H1_R_P', 'THD_S_P', 'H1_S_P', 'THD_T_P', 'H1_T_P']
            for c in cols_num:
                if c in hist_trafo.columns:
                    hist_trafo[c] = pd.to_numeric(hist_trafo[c], errors='coerce').fillna(0)

            # Kalkulasi Unbalance
            hist_trafo['Avg_Current'] = (hist_trafo['A_R_P'] + hist_trafo['A_S_P'] + hist_trafo['A_T_P']) / 3
            hist_trafo['Max_Dev'] = hist_trafo[['A_R_P', 'A_S_P', 'A_T_P']].sub(hist_trafo['Avg_Current'], axis=0).abs().max(axis=1)
            hist_trafo['Unbalance (%)'] = np.where(hist_trafo['Avg_Current'] == 0, 0, (hist_trafo['Max_Dev'] / hist_trafo['Avg_Current']) * 100).round(2)
            
            # Kalkulasi Load
            hist_trafo['Current Load'] = ((hist_trafo['V_RN'] * hist_trafo['A_R_P']) + (hist_trafo['V_SN'] * hist_trafo['A_S_P']) + (hist_trafo['V_TN'] * hist_trafo['A_T_P'])) / 1000
            hist_trafo['Current Load'] = hist_trafo['Current Load'].round(1)
            hist_trafo['Load Percentage'] = np.where(hist_trafo['TF_MLoad'] > 0, (hist_trafo['Current Load'] / hist_trafo['TF_MLoad']) * 100, 0).round(1)

            # Kalkulasi Health
            hist_trafo['H1_Total'] = hist_trafo['H1_R_P'] + hist_trafo['H1_S_P'] + hist_trafo['H1_T_P']
            hist_trafo['Weighted_THD'] = np.where(
                hist_trafo['H1_Total'] > 0,
                ((hist_trafo['THD_R_P'] * hist_trafo['H1_R_P']) + (hist_trafo['THD_S_P'] * hist_trafo['H1_S_P']) + (hist_trafo['THD_T_P'] * hist_trafo['H1_T_P'])) / hist_trafo['H1_Total'], 0)
            calculated_health = 100 - ((hist_trafo['Weighted_THD'] - 5).clip(lower=0) * 1.5)
            hist_trafo['Health Score'] = np.clip(calculated_health, 0, 100).fillna(100).astype(int)

            # --- 4. TAMPILAN MAP & INFO GARDU ---
            col_info1, col_info2 = st.columns([1, 2])
            with col_info1:
                st.markdown(f"### ℹ️ Info Dasar")
                st.metric("Nama Gardu", hist_trafo.iloc[0].get('TF_Name', '-'))
                st.metric("Kapasitas (Max Load)", f"{hist_trafo.iloc[0].get('TF_MLoad', 0)} kVA")
                st.metric("Total Kunjungan Ukur", f"{len(hist_trafo)} Kali")
            with col_info2:
                st.markdown(f"### 📍 Lokasi Gardu")
                if 'latitude' in hist_trafo.columns and 'longitude' in hist_trafo.columns:
                    map_df = hist_trafo[['latitude', 'longitude']].dropna().head(1)
                    st.map(map_df, height=230)
                    
            st.markdown("---")

            # --- 5. TAMPILAN GRAFIK (CHART) ---
            st.markdown("### 📈 Grafik Tren Riwayat")
            chart_type = st.radio("Pilih parameter yang ingin dianalisis:", 
                                  ["⚡ Beban Trafo (Load %)", "⚖️ Ketidakseimbangan (Unbalance %)", "🏥 Kesehatan (Health Score)"], 
                                  horizontal=True)
            
            if chart_type == "⚡ Beban Trafo (Load %)":
                fig = px.line(hist_trafo, x='Tanggal & Waktu', y='Load Percentage', markers=True, text='Load Percentage')
                fig.update_traces(line_color='#FF4B4B', textposition="top center")
                fig.update_layout(yaxis_title="Persentase Beban (%)")
            elif chart_type == "⚖️ Ketidakseimbangan (Unbalance %)":
                fig = px.line(hist_trafo, x='Tanggal & Waktu', y='Unbalance (%)', markers=True, text='Unbalance (%)')
                fig.update_traces(line_color='#FFA500', textposition="top center")
                fig.update_layout(yaxis_title="Unbalance Fasa (%)")
            else:
                fig = px.line(hist_trafo, x='Tanggal & Waktu', y='Health Score', markers=True, text='Health Score')
                fig.update_traces(line_color='#2ECC71', textposition="top center")
                fig.update_layout(yaxis_title="Skor Kesehatan (0-100)", yaxis=dict(range=[0, 110]))
                
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            
            # --- 6. TAMPILAN TABEL ---
            st.markdown("### 📋 Tabel Detail Pengukuran Historis")
            display_cols = ['Tanggal & Waktu', 'Current Load', 'Load Percentage', 'Unbalance (%)', 'Health Score', 'V_RN', 'V_SN', 'V_TN', 'A_R_P', 'A_S_P', 'A_T_P']
            
            # Filter hanya kolom yang benar-benar ada di dataframe untuk mencegah error
            display_cols = [c for c in display_cols if c in hist_trafo.columns]
            
            # Tampilkan dari yang paling baru ke yang paling lama
            st.dataframe(hist_trafo[display_cols].sort_values(by='Tanggal & Waktu', ascending=False), use_container_width=True, hide_index=True)
    st.markdown("---")