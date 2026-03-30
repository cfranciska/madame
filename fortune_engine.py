import json
import os
from dataclasses import dataclass
from datetime import date, datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo

from geopy.geocoders import Nominatim
from openai import OpenAI
from timezonefinder import TimezoneFinder

try:
    from lunardate import LunarDate
except ImportError:  # pragma: no cover
    LunarDate = None


class FortuneError(Exception):
    pass


SECTION_ORDER = [
    "BaZi",
    "Western Astrology",
    "Zi Wei Dou Shu",
    "Numerologi",
    "Vedic Astrology",
    "Intinya",
]

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
DEFAULT_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "minimal")
DEFAULT_OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "45"))
SYSTEM_PROMPT = """Anda adalah peramal profesional multidisiplin yang menggabungkan lima sistem ramalan klasik:
BaZi
Western Astrology
Zi Wei Dou Shu
Numerologi
Vedic Astrology

Gunakan input pengguna berikut:
* Tanggal lahir
* Tahun lahir
* Jam lahir
* Tempat lahir
* Periode ramalan yang dipilih pengguna:
  * Hari ini
  * Minggu ini
  * Tahun ini

Tujuan Anda adalah menghasilkan ramalan singkat, konsisten, dan mudah dipahami berdasarkan lima sistem ramalan tersebut.

TUGAS
Buat ramalan sesuai periode yang dipilih pengguna.
Setiap sistem ramalan harus memberikan perspektif yang berbeda dan relevan dengan periode yang dipilih.
Ramalan harus terasa praktis, ringan, dan sedikit playful, sesuai karakter aplikasi.
Jangan menulis teori, proses perhitungan, atau penjelasan teknis.

CALENDAR AND TIME CONVERSION (WAJIB)
Sebelum membuat ramalan, lakukan normalisasi waktu dan konversi kalender sesuai sistem masing-masing.
Gunakan aturan berikut:
BaZi
Konversi tanggal dan jam lahir dari kalender Gregorian ke kalender Cina lunisolar.
Gunakan empat pilar: tahun, bulan, hari, dan jam.
Zi Wei Dou Shu
Gunakan kalender Cina lunisolar dan jam lokal untuk menentukan struktur chart.
Vedic Astrology
Gunakan sistem zodiak sidereal dan sesuaikan dengan zona waktu tempat lahir.
Western Astrology
Gunakan kalender Gregorian dan sistem zodiak tropical.
Numerologi
Gunakan tanggal lahir Gregorian tanpa konversi kalender.
Jika perhitungan presisi tidak tersedia, gunakan pendekatan estimasi yang konsisten.
Jangan menampilkan detail perhitungan kepada pengguna.

TIME AND LOCATION NORMALIZATION
Gunakan aturan berikut:
* Gunakan zona waktu berdasarkan tempat lahir
* Gunakan jam lahir sebagai waktu lokal
* Perhitungkan perbedaan zona waktu secara logis
* Jika jam lahir tidak tersedia, gunakan default 12:00 siang

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
* Gunakan bahasa Indonesia
* Gunakan gaya ringkas, jelas, dan mudah dipahami
* Maksimal 50 kata per bagian
* Gunakan tone ringan dan sedikit playful
* Fokus pada arah atau peluang
* Hindari istilah teknis kompleks
* Hindari jargon astrologi atau metafisika
* Hindari pengulangan kalimat antar sistem
* Hindari kontradiksi antar sistem

BATASAN KEAMANAN
Jangan membuat prediksi tentang:
* kematian
* penyakit serius
* kecelakaan
* bencana
* diagnosis medis
* kepastian masa depan
* klaim supranatural absolut
Gunakan bahasa yang bersifat kemungkinan, arah, atau kecenderungan.

KONSISTENSI OUTPUT
Semua ramalan harus:
* relevan dengan periode yang dipilih
* tidak saling bertentangan
* tidak generik
* tidak berulang
Setiap sistem harus terasa unik dalam sudut pandang, bukan sekadar variasi kata.
"""


@dataclass
class BirthContext:
    birth_local_iso: str
    birth_utc_iso: str
    birth_time_source: str
    timezone_name: str
    timezone_source: str
    birth_place: str
    coordinates: str
    lunar_date: str
    western_sign: str
    vedic_sign_estimate: str
    life_path_number: int
    personal_year_number: int
    bazi_estimate: str
    zi_wei_estimate: str


def generate_fortune(
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    base_url: str | None = None,
    birth_date: date,
    birth_time: time | None,
    is_birth_time_known: bool,
    birth_place: str,
    period_label: str,
    period_key: str,
    question_focus: str,
) -> dict[str, str]:
    context = build_birth_context(
        birth_date=birth_date,
        birth_time=birth_time,
        is_birth_time_known=is_birth_time_known,
        birth_place=birth_place,
    )
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
        max_retries=1,
    )
    user_prompt = build_user_prompt(
        context=context,
        period_label=period_label,
        period_key=period_key,
        question_focus=question_focus,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    response = request_fortune_completion(
        client=client,
        model=model,
        reasoning_effort=reasoning_effort,
        messages=messages,
    )

    content = extract_response_text(response)
    if not content:
        raise FortuneError("Model tidak mengembalikan isi ramalan.")

    try:
        payload = json.loads(clean_json_payload(content))
    except json.JSONDecodeError as exc:
        raise FortuneError("Respons model tidak berbentuk JSON yang valid.") from exc

    result: dict[str, str] = {}
    for section in SECTION_ORDER:
        text = str(payload.get(section, "")).strip()
        if not text:
            raise FortuneError(f"Bagian `{section}` kosong pada respons model.")
        result[section] = trim_words(text, limit=50)
    return result


def request_fortune_completion(
    *,
    client: OpenAI,
    model: str,
    reasoning_effort: str,
    messages: list[dict[str, str]],
):
    attempts = [
        {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "fortune_sections",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "BaZi": {"type": "string"},
                            "Western Astrology": {"type": "string"},
                            "Zi Wei Dou Shu": {"type": "string"},
                            "Numerologi": {"type": "string"},
                            "Vedic Astrology": {"type": "string"},
                            "Intinya": {"type": "string"},
                        },
                        "required": SECTION_ORDER,
                        "additionalProperties": False,
                    },
                },
            },
            "include_reasoning_effort": True,
        },
        {
            "response_format": {"type": "json_object"},
            "include_reasoning_effort": True,
        },
        {
            "response_format": None,
            "include_reasoning_effort": False,
        },
    ]
    last_error: Exception | None = None

    for attempt in attempts:
        kwargs = {
            "model": model,
            "messages": messages,
        }
        if attempt["response_format"] is not None:
            kwargs["response_format"] = attempt["response_format"]
        if attempt["include_reasoning_effort"] and reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort

        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            last_error = exc

    raise FortuneError(f"Gagal meminta respons ke model: {last_error}")


def extract_response_text(response) -> str:
    message = response.choices[0].message
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    texts.append(str(text))
                continue
            text = getattr(item, "text", None)
            if text:
                texts.append(str(text))
        return "\n".join(texts).strip()
    parsed = getattr(message, "parsed", None)
    if parsed is not None:
        return json.dumps(parsed, ensure_ascii=False)
    return ""


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


def build_birth_context(
    *,
    birth_date: date,
    birth_time: time | None,
    is_birth_time_known: bool,
    birth_place: str,
) -> BirthContext:
    timezone_name, timezone_source, coordinates = resolve_timezone(birth_place)
    local_zone = ZoneInfo(timezone_name)
    local_dt = None
    utc_dt = None
    if birth_time is not None:
        local_dt = datetime.combine(birth_date, birth_time).replace(tzinfo=local_zone)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

    lunar_date = estimate_lunar_date(birth_date)
    western_sign = detect_western_sign(birth_date)
    vedic_sign_estimate = detect_vedic_sign_estimate(birth_date)
    life_path = calculate_life_path_number(birth_date)
    personal_year = calculate_personal_year_number(birth_date, date.today().year)
    bazi_estimate = estimate_bazi(birth_date=birth_date, local_dt=local_dt)
    zi_wei_estimate = estimate_zi_wei(local_dt=local_dt, lunar_date=lunar_date)

    return BirthContext(
        birth_local_iso=local_dt.isoformat() if local_dt else f"{birth_date.isoformat()}Tunknown",
        birth_utc_iso=utc_dt.isoformat() if utc_dt else "unknown",
        birth_time_source="input pengguna" if is_birth_time_known else "unknown / tidak diketahui",
        timezone_name=timezone_name,
        timezone_source=timezone_source,
        birth_place=birth_place,
        coordinates=coordinates,
        lunar_date=lunar_date,
        western_sign=western_sign,
        vedic_sign_estimate=vedic_sign_estimate,
        life_path_number=life_path,
        personal_year_number=personal_year,
        bazi_estimate=bazi_estimate,
        zi_wei_estimate=zi_wei_estimate,
    )


def build_user_prompt(*, context: BirthContext, period_label: str, period_key: str, question_focus: str) -> str:
    return f"""Berikut konteks yang sudah dinormalisasi untuk dipakai secara internal.

Input pengguna:
- Tanggal dan waktu lahir lokal: {context.birth_local_iso}
- Waktu UTC hasil normalisasi: {context.birth_utc_iso}
- Sumber jam lahir: {context.birth_time_source}
- Tempat lahir: {context.birth_place}
- Zona waktu: {context.timezone_name} ({context.timezone_source})
- Koordinat estimasi: {context.coordinates}
- Periode ramalan: {period_label} ({period_key})
- Fokus pertanyaan pengguna: {question_focus}

Konversi dan estimasi internal:
- Tanggal lunisolar estimasi: {context.lunar_date}
- BaZi estimasi: {context.bazi_estimate}
- Zi Wei Dou Shu estimasi: {context.zi_wei_estimate}
- Zodiak Western tropical: {context.western_sign}
- Zodiak Vedic sidereal estimasi: {context.vedic_sign_estimate}
- Life path numerologi: {context.life_path_number}
- Personal year numerologi untuk tahun berjalan: {context.personal_year_number}

Instruksi output:
- Keluarkan JSON object valid saja.
- Gunakan tepat enam key berikut:
  "BaZi", "Western Astrology", "Zi Wei Dou Shu", "Numerologi", "Vedic Astrology", "Intinya"
- Nilai tiap key berupa satu paragraf singkat berbahasa Indonesia.
- Maksimal 50 kata per bagian.
- Jangan tampilkan teori, perhitungan, atau disclaimer teknis.
- Semua bagian harus konsisten terhadap periode {period_label}.
- Semua bagian harus menyesuaikan fokus pertanyaan {question_focus}. Jika fokusnya "Umum", jaga tetap luas dan seimbang.
- Jika jam lahir tidak diketahui, jangan mengarang detail yang seolah sangat presisi dari posisi jam.
- Untuk key "Intinya", rangkum lima bagian sebelumnya dalam satu paragraf maksimal 50 kata, dengan tone sangat uplifting dan cheeky.
"""


def resolve_timezone(place: str) -> tuple[str, str, str]:
    return _resolve_timezone_cached(place.strip())


@lru_cache(maxsize=256)
def _resolve_timezone_cached(place: str) -> tuple[str, str, str]:
    geolocator = Nominatim(user_agent="madame-damn-space", timeout=8)
    tf = TimezoneFinder()

    try:
        location = geolocator.geocode(place)
        if location:
            timezone_name = tf.timezone_at(lng=location.longitude, lat=location.latitude)
            if timezone_name:
                coordinates = f"{location.latitude:.4f}, {location.longitude:.4f}"
                return timezone_name, "geocoded", coordinates
    except Exception:
        pass

    return "UTC", "fallback", "unknown"


def estimate_lunar_date(value: date) -> str:
    if LunarDate is None:
        return "estimasi tidak tersedia"

    try:
        lunar = LunarDate.fromSolarDate(value.year, value.month, value.day)
        return f"Tahun {lunar.year}, Bulan {lunar.month}, Hari {lunar.day}"
    except Exception:
        return "estimasi tidak tersedia"


def detect_western_sign(value: date) -> str:
    month_day = (value.month, value.day)
    boundaries = [
        ((1, 20), "Capricorn", "Aquarius"),
        ((2, 19), "Aquarius", "Pisces"),
        ((3, 21), "Pisces", "Aries"),
        ((4, 20), "Aries", "Taurus"),
        ((5, 21), "Taurus", "Gemini"),
        ((6, 21), "Gemini", "Cancer"),
        ((7, 23), "Cancer", "Leo"),
        ((8, 23), "Leo", "Virgo"),
        ((9, 23), "Virgo", "Libra"),
        ((10, 23), "Libra", "Scorpio"),
        ((11, 22), "Scorpio", "Sagittarius"),
        ((12, 22), "Sagittarius", "Capricorn"),
    ]
    for cutoff, before_sign, after_sign in boundaries:
        if month_day < cutoff:
            return before_sign
    return "Capricorn"


def detect_vedic_sign_estimate(value: date) -> str:
    shifted_ordinal = value.toordinal() - 24
    shifted = date.fromordinal(shifted_ordinal)
    month_day = (shifted.month, shifted.day)
    boundaries = [
        ((1, 20), "Capricorn", "Aquarius"),
        ((2, 19), "Aquarius", "Pisces"),
        ((3, 21), "Pisces", "Aries"),
        ((4, 20), "Aries", "Taurus"),
        ((5, 21), "Taurus", "Gemini"),
        ((6, 21), "Gemini", "Cancer"),
        ((7, 23), "Cancer", "Leo"),
        ((8, 23), "Leo", "Virgo"),
        ((9, 23), "Virgo", "Libra"),
        ((10, 23), "Libra", "Scorpio"),
        ((11, 22), "Scorpio", "Sagittarius"),
        ((12, 22), "Sagittarius", "Capricorn"),
    ]
    for cutoff, before_sign, after_sign in boundaries:
        if month_day < cutoff:
            return before_sign
    return "Capricorn"


def calculate_life_path_number(value: date) -> int:
    digits = [int(ch) for ch in value.strftime("%Y%m%d")]
    return reduce_number(sum(digits))


def calculate_personal_year_number(value: date, current_year: int) -> int:
    total = sum(int(ch) for ch in value.strftime("%m%d")) + sum(int(ch) for ch in str(current_year))
    return reduce_number(total)


def reduce_number(number: int) -> int:
    while number > 9 and number not in {11, 22, 33}:
        number = sum(int(ch) for ch in str(number))
    return number


def estimate_bazi(*, birth_date: date, local_dt: datetime | None) -> str:
    heavenly_stems = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
    earthly_branches = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]

    year_index = (birth_date.year - 4) % 60
    year_stem = heavenly_stems[year_index % 10]
    year_branch = earthly_branches[year_index % 12]
    month_branch = earthly_branches[(birth_date.month + 1) % 12]
    day_stem = heavenly_stems[(birth_date.toordinal() + 4) % 10]

    if local_dt is None:
        return (
            f"Tahun {year_stem}-{year_branch}, "
            f"Bulan cabang {month_branch}, "
            f"Hari batang {day_stem}, "
            "Jam tidak diketahui"
        )

    hour_branch = earthly_branches[((local_dt.hour + 1) // 2) % 12]
    return (
        f"Tahun {year_stem}-{year_branch}, "
        f"Bulan cabang {month_branch}, "
        f"Hari batang {day_stem}, "
        f"Jam cabang {hour_branch}"
    )


def estimate_zi_wei(*, local_dt: datetime | None, lunar_date: str) -> str:
    if local_dt is None:
        return f"Struktur estimasi dari {lunar_date} tanpa blok jam spesifik"
    hour_block = ((local_dt.hour + 1) // 2) % 12
    return f"Struktur estimasi dari {lunar_date} dengan blok jam ke-{hour_block}"


def trim_words(text: str, *, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(".,;:") + "..."
