import json
import os
import socket
from datetime import date, time
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FortuneError(Exception):
    pass


SECTION_ORDER = [
    "BaZi",
    "Western Astrology",
    "Numerologi",
    "Intinya",
]

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
DEFAULT_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "")
DEFAULT_OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
DEFAULT_OPENAI_RETRY_COUNT = int(os.getenv("OPENAI_RETRY_COUNT", "3"))
DEFAULT_OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "400"))
SYSTEM_PROMPT = """Anda adalah peramal profesional multidisiplin yang menggabungkan tiga sistem ramalan:
BaZi
Western Astrology
Numerologi

Gunakan input pengguna berikut:
* Nama
* Tanggal lahir
* Tahun lahir
* Jam lahir
* Tempat lahir
* Periode ramalan yang dipilih pengguna:
  * Hari ini
  * Minggu ini
  * Tahun ini

Tujuan Anda adalah menghasilkan ramalan singkat, mudah dipahami, dan terasa hidup berdasarkan tiga sistem ramalan tersebut.

TUGAS
Buat ramalan sesuai periode yang dipilih pengguna.
Setiap sistem ramalan harus memberikan perspektif yang berbeda dan relevan dengan periode yang dipilih.
Ramalan harus terasa praktis, ringan, dan sedikit playful, sesuai karakter aplikasi.
Jangan menulis teori, proses perhitungan, atau penjelasan teknis.

KONTEKS PENTING
Gunakan hanya data mentah yang diberikan pengguna di prompt.
Jika ingin melakukan normalisasi, asumsi, atau konversi kalender/zona waktu, lakukan sendiri secara internal.
Jangan mengandalkan adanya hasil konversi atau perhitungan tambahan dari sistem.
Jika jam lahir tidak diketahui, jangan mengarang detail yang terlalu presisi.

ADAPTASI PERIODE RAMALAN
Sesuaikan fokus ramalan berdasarkan periode yang dipilih pengguna.
Hari ini
Fokus pada:
* keputusan cepat
* interaksi sosial
* mood dan energi
* hal praktis yang bisa dilakukan hari ini
Minggu ini
Fokus pada:
* momentum
* relasi
* progres pekerjaan
* peluang jangka pendek
Tahun ini
Fokus pada:
* arah besar
* perubahan utama
* peluang jangka panjang
* fase kehidupan
Semua bagian harus merujuk pada periode yang sama.

ATURAN KONTEN
Gunakan aturan berikut:
* Gunakan bahasa Indonesia yang tidak terlalu formal dan cocok untuk generasi millenial dan gen z
* Gunakan gaya ringkas, jelas, mudah dipahami
* Maksimal 50 kata per bagian
* Gunakan tone ringan dan sedikit playful
* Hindari istilah teknis kompleks
* Hindari jargon astrologi atau metafisika
* Hindari pengulangan kalimat antar sistem

BATASAN KEAMANAN
Hindari membuat ramalan atau pernyataan eksplisit tentang:
- kematian
- penyakit serius
- kecelakaan besar
- bencana
- diagnosis medis
- kepastian masa depan
- klaim supranatural yang absolut
Jika topik tersebut relevan dalam interpretasi, sampaikan secara tidak langsung dengan bahasa yang umum, halus, dan tidak spesifik.
Fokus pada kewaspadaan atau perhatian, bukan pada prediksi kejadian.

ATURAN OUTPUT
Keluarkan tepat empat bagian:
* BaZi
* Western Astrology
* Numerologi
* Intinya
Tiga bagian pertama boleh punya sudut pandang yang berbeda dan tidak harus sepenuhnya selaras.
Bagian "Intinya" wajib terasa seperti rangkuman yang menyatukan semuanya secara saling melengkapi.
"""


def generate_fortune(
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    base_url: str | None = None,
    name: str,
    birth_date: date,
    birth_time: time | None,
    is_birth_time_known: bool,
    birth_place: str,
    period_label: str,
    period_key: str,
    question_focus: str,
    debug_log=None,
) -> dict[str, str]:
    if debug_log:
        debug_log("generate_fortune:start")

    user_prompt = build_user_prompt(
        name=name,
        birth_date=birth_date,
        birth_time=birth_time,
        is_birth_time_known=is_birth_time_known,
        birth_place=birth_place,
        period_label=period_label,
        period_key=period_key,
        question_focus=question_focus,
    )

    if debug_log:
        debug_log(f"generate_fortune:client_ready model={model}")
        debug_log("generate_fortune:requesting_completion")

    content = request_fortune_completion(
        api_key=api_key,
        base_url=base_url,
        model=model,
        reasoning_effort=reasoning_effort,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        debug_log=debug_log,
    )

    if debug_log:
        debug_log("generate_fortune:completion_received")
    if not content:
        raise FortuneError("Model tidak mengembalikan isi ramalan.")
    if debug_log:
        debug_log(f"generate_fortune:content_received chars={len(content)}")

    try:
        payload = json.loads(clean_json_payload(content))
    except json.JSONDecodeError as exc:
        raise FortuneError("Respons model tidak berbentuk JSON yang valid.") from exc

    if debug_log:
        debug_log(f"generate_fortune:json_parsed keys={sorted(payload.keys())}")

    result: dict[str, str] = {}
    for section in SECTION_ORDER:
        text = str(payload.get(section, "")).strip()
        if not text:
            raise FortuneError(f"Bagian `{section}` kosong pada respons model.")
        result[section] = trim_words(text, limit=50)

    if debug_log:
        debug_log("generate_fortune:result_ready")
    return result


def generate_fallback_fortune(
    *,
    name: str,
    birth_date: date,
    birth_time: time | None,
    is_birth_time_known: bool,
    birth_place: str,
    period_label: str,
    period_key: str,
    question_focus: str,
) -> dict[str, str]:
    period_map = {
        "today": "hari ini",
        "week": "minggu ini",
        "year": "tahun ini",
    }
    focus_map = {
        "Umum": "arah hidup secara umum",
        "Keuangan": "uang, prioritas, dan keputusan belanja",
        "Karir": "arah kerja, posisi, dan langkah profesional",
        "Asmara": "rasa, batas, dan chemistry",
        "Kesehatan": "energi, tempo, dan pola istirahat",
    }

    period_phrase = period_map.get(period_key, period_label.lower())
    focus_label = focus_map.get(question_focus, question_focus.lower())
    birth_time_label = birth_time.strftime("%H:%M") if is_birth_time_known and birth_time is not None else "tidak diketahui"
    place_label = birth_place.strip() or "tempat lahir yang kamu isi"
    name_label = name.strip() or "kamu"

    sections = {
        "BaZi": (
            f"Untuk {period_phrase}, {name_label}, bacaan BaZi kamu paling kuat saat fokusmu nggak pecah ke terlalu banyak arah. "
            f"Pakai pertanyaan soal {focus_label} sebagai kompas utama, dan biarkan detail lain menyusul pelan-pelan."
        ),
        "Western Astrology": (
            f"Dari vibe kelahiran {birth_date.isoformat()} di {place_label}, energi {period_phrase} kebaca lebih hidup kalau kamu jujur soal maumu. "
            f"Jangan terlalu sibuk bikin semuanya kelihatan aman dulu."
        ),
        "Numerologi": (
            f"Jam lahir {birth_time_label} di sini lebih jadi penanda ritme daripada jawaban final. "
            f"Untuk urusan {focus_label}, langkah kecil yang konsisten sekarang lebih kepakai daripada keputusan yang kelihatan dramatis."
        ),
        "Intinya": (
            f"Benang merahnya: {period_phrase} paling enak dipakai buat beresin fokus, pilih yang penting dulu, lalu gerak secukupnya tapi jelas, {name_label}. "
            f"Nggak harus heboh, yang penting terasa pas buat kamu."
        ),
    }
    return {section: trim_words(text, limit=50) for section, text in sections.items()}


def request_fortune_completion(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    reasoning_effort: str,
    messages: list[dict[str, str]],
    debug_log=None,
) -> str:
    endpoint_base = (base_url or "https://api.openai.com/v1").rstrip("/")
    endpoint = endpoint_base if endpoint_base.endswith("/chat/completions") else f"{endpoint_base}/chat/completions"
    attempts = [
        {"response_format": {"type": "json_object"}},
        {"response_format": None},
    ]
    last_error: Exception | None = None

    for index, attempt in enumerate(attempts, start=1):
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": DEFAULT_OPENAI_MAX_TOKENS,
            "temperature": 0.7,
        }
        if attempt["response_format"] is not None:
            payload["response_format"] = attempt["response_format"]
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        try:
            if debug_log:
                debug_log(
                    "request_fortune_completion:attempt "
                    f"index={index}/{len(attempts)} "
                    f"response_format={attempt['response_format'] is not None}"
                )
            return post_chat_completion_via_urllib(
                endpoint=endpoint,
                api_key=api_key,
                payload=payload,
                debug_log=debug_log,
            )
        except FortuneError as exc:
            last_error = exc
            if debug_log:
                debug_log(
                    "request_fortune_completion:attempt_failed "
                    f"index={index}/{len(attempts)} error_type={type(exc).__name__} error={exc}"
                )

    raise FortuneError(f"Gagal meminta respons ke model: {last_error}")


def post_chat_completion_via_urllib(
    *,
    endpoint: str,
    api_key: str,
    payload: dict,
    debug_log=None,
) -> str:
    body = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None
    is_custom_endpoint = "api.openai.com" not in endpoint
    timeout_seconds = min(DEFAULT_OPENAI_TIMEOUT_SECONDS, 20.0) if is_custom_endpoint else DEFAULT_OPENAI_TIMEOUT_SECONDS
    retry_count = 1 if is_custom_endpoint else DEFAULT_OPENAI_RETRY_COUNT

    for attempt_index in range(1, retry_count + 1):
        request = Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        try:
            if debug_log:
                debug_log(
                    "post_chat_completion:open "
                    f"attempt={attempt_index}/{retry_count} "
                    f"url={endpoint} timeout={timeout_seconds}s body_chars={len(body)} "
                    f"custom_endpoint={is_custom_endpoint}"
                )
            with urlopen(request, timeout=timeout_seconds) as response:
                status_code = getattr(response, "status", None) or response.getcode()
                if debug_log:
                    debug_log(
                        "post_chat_completion:headers_received "
                        f"attempt={attempt_index}/{retry_count} "
                        f"status={status_code}"
                    )
                raw = response.read().decode("utf-8")
            if debug_log:
                debug_log(
                    "post_chat_completion:response_received "
                    f"attempt={attempt_index}/{retry_count} "
                    f"status={status_code} chars={len(raw)}"
                )
            break
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            if debug_log:
                debug_log(
                    "post_chat_completion:http_error "
                    f"attempt={attempt_index}/{retry_count} "
                    f"status={exc.code} reason={exc.reason} details={details[:200]}"
                )
            if exc.code in {408, 409, 429, 500, 502, 503, 504} and attempt_index < retry_count:
                backoff_seconds = attempt_index
                if debug_log:
                    debug_log(f"post_chat_completion:retrying_in seconds={backoff_seconds}")
                sleep(backoff_seconds)
                last_error = exc
                continue
            raise FortuneError(f"HTTP {exc.code} dari OpenAI: {details[:300]}") from exc
        except URLError as exc:
            if debug_log:
                debug_log(
                    "post_chat_completion:url_error "
                    f"attempt={attempt_index}/{retry_count} "
                    f"reason_type={type(exc.reason).__name__} reason={exc.reason}"
                )
            if attempt_index < retry_count:
                backoff_seconds = attempt_index
                if debug_log:
                    debug_log(f"post_chat_completion:retrying_in seconds={backoff_seconds}")
                sleep(backoff_seconds)
                last_error = exc
                continue
            raise FortuneError(f"Koneksi ke OpenAI gagal: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            if debug_log:
                debug_log(
                    "post_chat_completion:timeout "
                    f"attempt={attempt_index}/{retry_count} "
                    f"error_type={type(exc).__name__}"
                )
            if attempt_index < retry_count:
                backoff_seconds = attempt_index
                if debug_log:
                    debug_log(f"post_chat_completion:retrying_in seconds={backoff_seconds}")
                sleep(backoff_seconds)
                last_error = exc
                continue
            raise FortuneError("Request ke OpenAI timeout.") from exc
        except Exception as exc:
            if debug_log:
                debug_log(
                    "post_chat_completion:unexpected_exception "
                    f"attempt={attempt_index}/{retry_count} "
                    f"error_type={type(exc).__name__} error={exc}"
                )
            raise FortuneError(f"Request ke OpenAI gagal: {exc}") from exc
    else:
        raise FortuneError(f"Request ke OpenAI gagal setelah retry: {last_error}")

    try:
        response_payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        if debug_log:
            debug_log(f"post_chat_completion:invalid_json snippet={raw[:200]}")
        raise FortuneError("Respons OpenAI bukan JSON valid.") from exc

    if isinstance(response_payload, dict) and response_payload.get("error"):
        error_value = response_payload["error"]
        if isinstance(error_value, dict):
            error_message = str(error_value.get("message") or error_value)
        else:
            error_message = str(error_value)
        if debug_log:
            debug_log(f"post_chat_completion:error_payload error={error_message[:200]}")
        raise FortuneError(f"Provider mengembalikan error: {error_message[:300]}")

    try:
        message = response_payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        if debug_log:
            debug_log(
                "post_chat_completion:unexpected_response_shape "
                f"snippet={str(response_payload)[:200]}"
            )
        raise FortuneError(f"Format respons OpenAI tidak dikenali: {str(response_payload)[:300]}") from exc

    if isinstance(message, str):
        if debug_log:
            debug_log(f"post_chat_completion:message_ready type=str chars={len(message)}")
        return message.strip()
    if isinstance(message, list):
        texts: list[str] = []
        for item in message:
            if isinstance(item, dict) and item.get("text"):
                texts.append(str(item["text"]))
        if debug_log:
            debug_log(
                "post_chat_completion:message_ready "
                f"type=list text_parts={len(texts)} chars={len(''.join(texts))}"
            )
        return "\n".join(texts).strip()
    if debug_log:
        debug_log(f"post_chat_completion:message_ready type={type(message).__name__}")
    return str(message).strip()


def clean_json_payload(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def build_user_prompt(
    *,
    name: str,
    birth_date: date,
    birth_time: time | None,
    is_birth_time_known: bool,
    birth_place: str,
    period_label: str,
    period_key: str,
    question_focus: str,
) -> str:
    birth_time_label = birth_time.strftime("%H:%M") if is_birth_time_known and birth_time is not None else "Tidak diketahui"
    return f"""Berikut input pengguna mentah. Gunakan sebagai satu-satunya konteks input.

Input pengguna:
- Nama: {name}
- Tanggal lahir: {birth_date.isoformat()}
- Jam lahir: {birth_time_label}
- Tempat lahir: {birth_place}
- Periode ramalan: {period_label} ({period_key})
- Fokus pertanyaan pengguna: {question_focus}

Instruksi output:
- Keluarkan JSON object valid saja.
- Gunakan tepat empat key berikut:
  "BaZi", "Western Astrology", "Numerologi", "Intinya"
- Nilai tiap key berupa satu paragraf singkat berbahasa Indonesia.
- Maksimal 50 kata per bagian.
- Jangan tampilkan teori, perhitungan, atau disclaimer teknis.
- Semua bagian harus konsisten terhadap periode {period_label}.
- Semua bagian harus menyesuaikan fokus pertanyaan {question_focus}. Jika fokusnya "Umum", jaga tetap luas dan seimbang.
- Jika jam lahir tidak diketahui, jangan mengarang detail yang seolah sangat presisi dari posisi jam.
- Tiga bagian pertama boleh saling beda sudut pandang dan tidak harus terasa sepenuhnya harmonis.
- Untuk key "Intinya", rangkum tiga bagian sebelumnya dalam satu paragraf maksimal 50 kata, dengan tone sangat uplifting dan cheeky, terasa menyatukan semuanya.
"""


def trim_words(text: str, *, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(".,;:") + "..."
