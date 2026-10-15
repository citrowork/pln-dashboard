import os
import shutil
import zipfile
import time

PROJECT_DIR = r"c:\Users\Dragon\Documents\Project\PLN_Dashboard"
PORTABLE_DIR = r"c:\Users\Dragon\Documents\Project\PLN_Dashboard_Portable"
SOURCE_PYTHON_PORTABLE = r"c:\Users\Dragon\Documents\Project\Dashboard_SmaPro_Portable\python_portable"
ZIP_OUTPUT = r"c:\Users\Dragon\Documents\Project\PLN_Dashboard_Portable.zip"

print("=" * 65)
print("  BUILD & UPDATE PORTABLE PACKAGE: PLN DASHBOARD ULP MOA")
print("=" * 65)

# 1. Buat folder target
os.makedirs(PORTABLE_DIR, exist_ok=True)
os.makedirs(os.path.join(PORTABLE_DIR, ".streamlit"), exist_ok=True)

# 2. Salin kode aplikasi utama
print("[1/6] Menyalin app.py dan bot_hioki.py (versi terbaru anti-overwrite)...")
shutil.copy2(os.path.join(PROJECT_DIR, "app.py"), os.path.join(PORTABLE_DIR, "app.py"))
shutil.copy2(os.path.join(PROJECT_DIR, "bot_hioki.py"), os.path.join(PORTABLE_DIR, "bot_hioki.py"))

# 3. Salin kredensial, logo, dan file pendukung
print("[2/6] Menyalin credentials.json, logo_pln.png, dan database Maximo...")
for fname in ["credentials.json", "logo_pln.png", "requirements.txt",
              "DATA_TRAFO_ENRICHED_FROM_MAXIMO.xlsx",
              "DATA_TRAFO_ENRICHED_FROM_MAXIMO_UPDATED.xlsx",
              "gardu_maximo.xlsx"]:
    src = os.path.join(PROJECT_DIR, fname)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(PORTABLE_DIR, fname))

# 4. Salin konfigurasi .streamlit
print("[3/6] Menyalin konfigurasi .streamlit (config.toml & secrets.toml)...")
for cfg in ["config.toml", "secrets.toml"]:
    src = os.path.join(PROJECT_DIR, ".streamlit", cfg)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(PORTABLE_DIR, ".streamlit", cfg))

# 5. Salin / Perbarui python_portable
target_py = os.path.join(PORTABLE_DIR, "python_portable")
if not os.path.exists(target_py):
    print("[4/6] Menyalin Python Portable runtime mandiri (mohon tunggu)...")
    shutil.copytree(SOURCE_PYTHON_PORTABLE, target_py)
else:
    print("[4/6] Memperbarui file python_portable yang sudah ada...")
    # Update site-packages
    src_sp = os.path.join(SOURCE_PYTHON_PORTABLE, "Lib", "site-packages")
    dst_sp = os.path.join(target_py, "Lib", "site-packages")
    if os.path.exists(src_sp) and os.path.exists(dst_sp):
        for pkg in ["gspread", "openpyxl", "pdfplumber", "pdfminer", "pypdfium2", "google"]:
            for item in os.listdir(src_sp):
                if any(k in item.lower() for k in ["gspread", "openpyxl", "pdfplumber", "pdfminer", "pypdfium2"]):
                    s_item = os.path.join(src_sp, item)
                    d_item = os.path.join(dst_sp, item)
                    if os.path.isdir(s_item):
                        if os.path.exists(d_item):
                            shutil.rmtree(d_item, ignore_errors=True)
                        shutil.copytree(s_item, d_item)
                    else:
                        shutil.copy2(s_item, d_item)

# 6. Buat JALANKAN_DASHBOARD.bat
print("[5/6] Membuat script peluncur JALANKAN_DASHBOARD.bat...")
bat_content = """@echo off
title Dashboard Analisis & Pembebanan Gardu Trafo - PLN ULP MOA
color 0B
cls
echo ===================================================================
echo             PT PLN (PERSERO) - ULP MOA
echo   DASHBOARD ANALISIS PEMBEBANAN & KESEIMBANGAN TRAFO DISTRIBUSI
echo               PORTABLE STANDALONE EDITION
echo ===================================================================
echo.

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: 1. Deteksi Python Portable Terintegrasi
if exist "%BASE_DIR%python_portable\\python.exe" (
    echo [*] Menggunakan Runtime Python Portable Mandiri...
    set "PYTHON_EXE=%BASE_DIR%python_portable\\python.exe"
    set "PATH=%BASE_DIR%python_portable;%BASE_DIR%python_portable\\Scripts;%PATH%"
    set "STREAMLIT_CMD="%BASE_DIR%python_portable\\python.exe" -m streamlit run app.py --server.port=8501 --server.headless=true"
) else (
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] Python tidak terdeteksi!
        echo Pastikan folder python_portable berada di folder ini atau Python sistem terpasang.
        echo.
        pause
        exit /b
    )
    echo [*] Menggunakan Python Sistem...
    set "STREAMLIT_CMD=streamlit run app.py --server.port=8501 --server.headless=true"
)

echo [*] Menyalakan Dashboard Server (Port: 8501)...
echo [*] Membuka browser: http://localhost:8501
echo.
echo ===================================================================
echo CATATAN:
echo - Jangan tutup jendela hitam ini selama menggunakan Dashboard.
echo - Tekan Ctrl + C untuk mematikan dashboard jika selesai.
echo ===================================================================
echo.

start "" "http://localhost:8501"
%STREAMLIT_CMD%
pause
"""
with open(os.path.join(PORTABLE_DIR, "JALANKAN_DASHBOARD.bat"), "w", encoding="utf-8") as f:
    f.write(bat_content)

# 7. Buat PANDUAN_PENGGUNAAN_PORTABLE.txt
readme_text = """===================================================================
       PANDUAN PENGGUNAAN PLN DASHBOARD TRAFO PORTABLE
                 PT PLN (PERSERO) - ULP MOA
===================================================================

Aplikasi ini bersifat 100% PORTABLE & STANDALONE:
- TIDAK PERLU menginstall Python di laptop / PC kantor.
- TIDAK PERLU hak akses Administrator.
- TIDAK PERLU menginstall dependensi via terminal.
- Siap dijalankan langsung dari Flashdisk, folder Downloads, atau Desktop.

-------------------------------------------------------------------
FITUR & PEMBARUAN UTAMA:
-------------------------------------------------------------------
1. Sistem Penulisan Anti-Overwrite:
   Perekaman hasil ukur Hioki PDF maupun manual kini menggunakan
   metode deterministik tabel Google Sheets (RAW_MEA) sehingga
   dijamin aman dan tidak akan pernah menimpa baris lama.
2. Analisis Pembebanan & Ketidakseimbangan Fasa (SPLN 1987).
3. Rekomendasi Penyeimbangan Beban Otomatis (WBP & LWBP).
4. Integrasi Spasial GIS Pelanggan JTR & Estimasi Drop Tegangan.
5. Ekstraksi Otomatis Dokumen Laporan Hioki PQA berbasis AI Gemini.

-------------------------------------------------------------------
CARA MENJALANKAN:
-------------------------------------------------------------------
1. Ekstrak file "PLN_Dashboard_Portable.zip" ke laptop / PC kerja.
2. Buka foldernya, lalu klik ganda (double-click):
      👉 JALANKAN_DASHBOARD.bat
3. Browser (Chrome / Edge) akan otomatis terbuka dan menampilkan Dashboard:
      http://localhost:8501
4. Selesai! Dashboard siap digunakan untuk operasional.

-------------------------------------------------------------------
CARA AKSES DARI KOMPUTER / HP LAIN (DALAM 1 WI-FI / LAN PLN):
-------------------------------------------------------------------
1. Saat JALANKAN_DASHBOARD.bat berjalan, perhatikan alamat "Network URL"
   di layar hitam (contoh: http://192.168.x.x:8501).
2. Perangkat rekan lain cukup membuka alamat tersebut di browser masing-masing.

===================================================================
"""
with open(os.path.join(PORTABLE_DIR, "PANDUAN_PENGGUNAAN_PORTABLE.txt"), "w", encoding="utf-8") as f:
    f.write(readme_text)

# 8. Buat file arsip ZIP untuk distribusi
print("[6/6] Mengompresi paket menjadi PLN_Dashboard_Portable.zip...")
if os.path.exists(ZIP_OUTPUT):
    try:
        os.remove(ZIP_OUTPUT)
    except Exception as e:
        print(f"Warning: gagal hapus zip lama: {e}")

with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for root, dirs, files in os.walk(PORTABLE_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            # Skip cache / temp
            if "__pycache__" in file_path or file.endswith(".pyc"):
                continue
            arcname = os.path.join("PLN_Dashboard_Portable", os.path.relpath(file_path, PORTABLE_DIR))
            zf.write(file_path, arcname)

size_mb = os.path.getsize(ZIP_OUTPUT) / (1024 * 1024)
print("=" * 65)
print(f"  [BERHASIL] Paket Portable Selesai Dibuat!")
print(f"  Folder  : {PORTABLE_DIR}")
print(f"  Arsip   : {ZIP_OUTPUT} ({size_mb:.1f} MB)")
print("=" * 65)
