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

`madame, help!` adalah app ramalan ringan berbahasa Indonesia untuk Hugging Face Spaces dengan `Docker + Streamlit`.

- BaZi
- Western Astrology
- Zi Wei Dou Shu
- Numerologi
- Vedic Astrology
- Intinya

## Input

- Tanggal lahir
- Jam lahir, termasuk opsi `Tidak Tahu`
- Tempat lahir
- Periode ramalan: `Hari ini`, `Minggu ini`, `Tahun ini`
- Fokus pertanyaan: `Umum`, `Keuangan`, `Karir`, `Asmara`, `Kesehatan`

## Secret di Hugging Face Space

Tambahkan secret berikut di Hugging Face Space:

- `OPENAI_API_KEY` wajib
- `OPENAI_MODEL` opsional, default `gpt-5-mini`
- `OPENAI_REASONING_EFFORT` opsional, default `minimal`
- `OPENAI_BASE_URL` opsional untuk endpoint OpenAI-compatible

Isi value secret dengan nilai mentah saja. Contoh yang benar untuk `OPENAI_API_KEY`:

```text
sk-xxxx
```

Jangan isi seperti ini:

```text
OPENAI_API_KEY="sk-xxxx"
EVOLINK_API_KEY="sk-yyyy"
```

Jika butuh lebih dari satu secret, buat masing-masing di field secret terpisah di Hugging Face Space.

## Local Run

```bash
docker build -t madame-damn .
docker run --rm -p 7860:7860 \
  -e OPENAI_API_KEY=your_key_here \
  -e OPENAI_MODEL=gpt-5-mini \
  madame-damn
```

Lalu buka `http://localhost:7860`.

## Upload ke Hugging Face Space

Upload file-file ini:

- `app.py`
- `fortune_engine.py`
- `Dockerfile`
- `requirements.txt`
- `README.md`
- `header.png`

Jangan upload `.streamlit/secrets.toml`. Secret itu hanya untuk local run.

## Catatan

- Tempat lahir dicoba di-normalisasi ke zona waktu dengan geocoding. Jika gagal, app memakai fallback estimasi yang konsisten.
- Jika jam lahir `Tidak Tahu`, engine akan memperlakukan jam lahir sebagai `unknown`, bukan memaksakan `12:00`.
- Output ditampilkan dalam enam bagian tetap, sesuai urutan UI.
