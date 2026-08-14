import pdfplumber
import google.generativeai as genai
import json
import gspread
import io
import streamlit as st
from google.oauth2.service_account import Credentials

# ==========================================
# 1. PENGATURAN API & KREDENSIAL
# ==========================================
# Kredensial Gemini API (Sebaiknya gunakan st.secrets di produksi)
genai.configure(api_key=st.secrets["gemini_api_key"])
model = genai.GenerativeModel('gemini-3.1-flash-lite')

def proses_pdf_ke_sheets(file_bytes, tf_code, tanggal, waktu):
    """
    Fungsi untuk mengekstrak data dari PDF Hioki dan menyimpannya ke sheet RAW_MEA.
    Dipanggil langsung dari app.py (Streamlit).
    """
    try:
        # A. Setup Google Sheets Autentikasi
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(creds)
        
        # Buka RAW_MEA
        sheet = gc.open("DATA TRAFO").worksheet("RAW_MEA")
        
        # B. Ekstrak Teks dari PDF Bytes
        teks_laporan = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                teks_laporan += page.extract_text() + " "
                
        teks_laporan = teks_laporan.replace('"', "'").replace('\n', ' ').strip()
        
        # C. Kirim ke Gemini dengan Prompt yang Disesuaikan
        prompt = f"""You are an electrical engineering data extraction assistant. Extract transformer data from the text. Return STRICTLY a single, flat JSON array with one object. CRITICAL RULES:
1. Strip all units (V, A, %, Hz). Return raw numbers only.
2. Current/Peak Extraction: Map 'RP/SP/TP/NP/INDUK' to P; 'R1/S1/T1/N1/LINE A' to 1; 'R2/S2/T2/N2/LINE B' to 2; 'R3/S3/T3/N3/ LINE C' to 3.
3. Look for specific section headers: 'ARUS INDUK', 'ARUS LINE A', 'ARUS LINE B', 'THD INDUK', 'THD LINE A', 'THD LINE B', 'VOLT INDUK'.
4. FALLBACK RULE: If data for Jalur 1 (current or harmonic) is missing, you MUST copy the corresponding Pangkal (P) value into that Jalur 1 key. If segments 2 or 3 are missing, return null.
5. VOLTAGE FALLBACK: If Phase-to-Neutral voltages (V_RN, V_SN, V_TN) are not found or missing in the text, you MUST output 230 for each. If Phase-to-Phase voltages (V_RS, V_RT, V_ST) are missing, you MUST output 400 for each.
6. HARMONIC EXTRACTION: Look for the 'Level Harmonik' column. Extract ONLY the absolute Current value (in Amperes). You MUST IGNORE the 'Kandungan Harmonik' column (the percentage values like '100.00%').
7. JSON FORMATTING: All measurement values MUST be returned as raw numerical JSON data types (e.g., 227.4). Do NOT wrap measurement numbers in quotes. If a value is missing, return null.

SCHEMA: V_RN, V_SN, V_TN, V_RS, V_RT, V_ST, A_R_P, A_S_P, A_T_P, A_N_P, A_R_1, A_S_1, A_T_1, A_N_1, A_R_2, A_S_2, A_T_2, A_N_2, A_R_3, A_S_3, A_T_3, A_N_3, PEAK_R_P, PEAK_S_P, PEAK_T_P, PEAK_N_P, PEAK_R_1, PEAK_S_1, PEAK_T_1, PEAK_N_1, PEAK_R_2, PEAK_S_2, PEAK_T_2, PEAK_N_2, PEAK_R_3, PEAK_S_3, PEAK_T_3, PEAK_N_3, THD_R_P, H1_R_P, THD_S_P, H1_S_P, THD_T_P, H1_T_P, THD_R_1, H1_R_1, THD_S_1, H1_S_1, THD_T_1, H1_T_1, THD_R_2, H1_R_2, THD_S_2, H1_S_2, THD_T_2, H1_T_2, THD_R_3, H1_R_3, THD_S_3, H1_S_3, THD_T_3, H1_T_3. 
No markdown, no prose. Output ONLY the raw JSON array. 
Text to extract: {teks_laporan}
"""
        response = model.generate_content(prompt)
        json_bersih = response.text.replace("```json", "").replace("```", "").strip()
        data_json = json.loads(json_bersih)
        
        data = data_json[0] if isinstance(data_json, list) else data_json

        # D. Menyiapkan Array untuk Google Sheets
        # Format kolom RAW_MEA: Date, Time, TF_Code, [Data Voltase, Arus, THD...], [Kolom ALA_RP dst...]
        row_ke_sheets = [
            str(tanggal),
            str(waktu),
            str(tf_code),
            data.get("V_RN", ""), data.get("V_SN", ""), data.get("V_TN", ""),
            data.get("V_RS", ""), data.get("V_RT", ""), data.get("V_ST", ""),
            data.get("A_R_P", ""), data.get("A_S_P", ""), data.get("A_T_P", ""), data.get("A_N_P", ""),
            data.get("A_R_1", ""), data.get("A_S_1", ""), data.get("A_T_1", ""), data.get("A_N_1", ""),
            data.get("A_R_2", ""), data.get("A_S_2", ""), data.get("A_T_2", ""), data.get("A_N_2", ""),
            data.get("A_R_3", ""), data.get("A_S_3", ""), data.get("A_T_3", ""), data.get("A_N_3", ""),
            data.get("PEAK_R_P", ""), data.get("PEAK_S_P", ""), data.get("PEAK_T_P", ""), data.get("PEAK_N_P", ""),
            data.get("PEAK_R_1", ""), data.get("PEAK_S_1", ""), data.get("PEAK_T_1", ""), data.get("PEAK_N_1", ""),
            data.get("PEAK_R_2", ""), data.get("PEAK_S_2", ""), data.get("PEAK_T_2", ""), data.get("PEAK_N_2", ""),
            data.get("PEAK_R_3", ""), data.get("PEAK_S_3", ""), data.get("PEAK_T_3", ""), data.get("PEAK_N_3", ""),
            data.get("THD_R_P", ""), data.get("H1_R_P", ""), data.get("THD_S_P", ""), data.get("H1_S_P", ""), data.get("THD_T_P", ""), data.get("H1_T_P", ""),
            data.get("THD_R_1", ""), data.get("H1_R_1", ""), data.get("THD_S_1", ""), data.get("H1_S_1", ""), data.get("THD_T_1", ""), data.get("H1_T_1", ""),
            data.get("THD_R_2", ""), data.get("H1_R_2", ""), data.get("THD_S_2", ""), data.get("H1_S_2", ""), data.get("THD_T_2", ""), data.get("H1_T_2", ""),
            data.get("THD_R_3", ""), data.get("H1_R_3", ""), data.get("THD_S_3", ""), data.get("H1_S_3", ""), data.get("THD_T_3", ""), data.get("H1_T_3", ""),
            # Kolom ALA secara default diisi 0 untuk pengukuran baru
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        ]
        
        # E. Append ke Google Sheets
        sheet.append_row(row_ke_sheets)
        return True, "Data berhasil diekstrak dan disimpan ke databases."
        
    except Exception as e:
        return False, f"Error pada pemrosesan PDF: {e}"