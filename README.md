---
title: madame, help!
emoji: 🔮
colorFrom: pink
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# madame, help!

`madame, help!` adalah app ramalan ringan berbahasa Indonesia untuk `Streamlit`.

- BaZi
- Western Astrology
- Numerologi
- Intinya

## Input

- Tanggal lahir
- Jam lahir, termasuk opsi `Tidak Tahu`
- Tempat lahir
- Periode ramalan: `Hari ini`, `Minggu ini`, `Tahun ini`
- Fokus pertanyaan: `Umum`, `Keuangan`, `Karir`, `Asmara`, `Kesehatan`

## Secret di Streamlit Community Cloud

Tambahkan secret berikut di menu app `Settings > Secrets`:

- `OPENAI_API_KEY` wajib
- `OPENAI_ENABLED` opsional, default `false`
- `OPENAI_MODEL` opsional, default `gpt-5.4-mini`
- `OPENAI_REASONING_EFFORT` opsional, default `minimal`
- `OPENAI_BASE_URL` opsional untuk endpoint OpenAI-compatible

Saat ini jalur submit memakai engine lokal agar hasil stabil di Streamlit Community Cloud. Secret `OPENAI_*` boleh tetap disimpan untuk eksperimen, tapi tidak dipakai di alur utama sampai integrasi remote dibuat lebih andal.

Isi value secret dengan nilai mentah saja. Contoh yang benar untuk `OPENAI_API_KEY`:

```text
sk-xxxx
```

Jangan isi seperti ini:

```text
OPENAI_API_KEY="sk-xxxx"
EVOLINK_API_KEY="sk-yyyy"
```

Jika butuh lebih dari satu secret, buat masing-masing di field secret terpisah.

## Local Run

```bash
streamlit run app.py
```

## Deploy ke Streamlit Community Cloud

Pastikan repo berisi file-file ini:

- `app.py`
- `fortune_engine.py`
- `requirements.txt`
- `runtime.txt`
- `README.md`
- `header.png`

Lalu set `Main file path` ke `app.py`.

Jangan commit `.streamlit/secrets.toml`. Secret itu hanya untuk local run.

Minimal isi secret seperti ini:

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-5.4-mini"
OPENAI_REASONING_EFFORT = ""
# OPENAI_BASE_URL = "https://api.openai.com/v1"
```

## Catatan

- `fortune_engine.py` sekarang meneruskan input mentah pengguna langsung ke LLM tanpa geocoding atau konversi lokal.
- `OPENAI_API_KEY` sekarang wajib tersedia di `.streamlit/secrets.toml`. App akan berhenti kalau secret ini belum ada.
- Jika jam lahir `Tidak Tahu`, prompt akan menandainya sebagai tidak diketahui agar model tidak terlalu presisi.
- Output tetap ditampilkan dalam empat bagian tetap, sesuai urutan UI.
