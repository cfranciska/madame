import base64
from datetime import date, datetime, time
from html import escape
from pathlib import Path

import streamlit as st

import fortune_engine


st.set_page_config(
    page_title="madame, help!",
    page_icon="🔮",
    layout="centered",
)


CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Borel&family=Poppins:wght@400;500;600;700&display=swap');

    :root {
        --bg: #fff7f0;
        --ink: #222222;
        --muted: #645b66;
        --card: rgba(255, 247, 240, 0.84);
        --line: rgba(34, 34, 34, 0.10);
        --accent: #ff2e93;
        --accent-2: #7b2ff7;
        --accent-3: #ff8a00;
        --shadow: 0 18px 50px rgba(123, 47, 247, 0.12);
    }

    html, body, [class*="css"], [data-testid="stAppViewContainer"], .stApp, .stMarkdown, p, span, label, input, textarea, button, select, li, div {
        font-family: 'Poppins', sans-serif !important;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(255, 46, 147, 0.15), transparent 30%),
            radial-gradient(circle at top right, rgba(123, 47, 247, 0.14), transparent 28%),
            radial-gradient(circle at bottom center, rgba(255, 138, 0, 0.10), transparent 34%),
            linear-gradient(180deg, #fff9f4 0%, var(--bg) 100%);
        color: var(--ink);
    }

    .block-container {
        max-width: 840px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        font-family: 'Poppins', sans-serif;
        color: var(--ink);
        letter-spacing: -0.03em;
    }

    .hero {
        padding: 1.8rem 1.6rem 1.35rem;
        border: 1px solid var(--line);
        border-radius: 28px;
        background: linear-gradient(145deg, rgba(255, 249, 244, 0.96), rgba(255, 240, 249, 0.9));
        box-shadow: var(--shadow);
        margin-bottom: 1.3rem;
        text-align: center;
    }

    .hero-kicker {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: var(--accent-2);
        margin-bottom: 0.72rem;
        font-weight: 700;
        position: relative;
        z-index: 2;
    }

    .hero-title {
        font-family: 'Borel', cursive !important;
        font-size: clamp(1.85rem, 3.6vw, 2.8rem) !important;
        line-height: 0.9 !important;
        margin: 0 auto 0.05rem;
        padding-top: 0.55rem;
        color: #ff2e93 !important;
        font-weight: 400 !important;
        max-width: 100%;
        position: relative;
        z-index: 1;
    }

    .hero-image {
        width: min(290px, 58vw);
        display: block;
        margin: 0.05rem auto 0.8rem;
        filter: drop-shadow(0 10px 20px rgba(24, 33, 38, 0.08));
    }

    .hero-subtitle {
        margin: 0.8rem auto 0;
        color: #ff2e93;
        max-width: 34rem;
        text-align: center;
        display: block;
        font-weight: 500;
        line-height: 1.55;
    }

    .hero-subtitle-wrap {
        width: 100%;
        display: flex;
        justify-content: center;
    }

    div[data-testid="stForm"] {
        padding: 1.1rem;
        border: 1px solid var(--line);
        border-radius: 24px;
        background: linear-gradient(180deg, rgba(255, 248, 243, 0.92), rgba(255, 241, 249, 0.82));
        box-shadow: var(--shadow);
    }

    .section-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: var(--accent-2);
        font-weight: 700;
        margin-bottom: 0.3rem;
    }

    label[data-testid="stWidgetLabel"] p,
    div[data-testid="stWidgetLabel"] p {
        color: var(--accent-2);
        font-weight: 700;
        opacity: 1;
    }

    .result-card {
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 1.1rem 1.15rem;
        background: var(--card);
        box-shadow: var(--shadow);
        backdrop-filter: blur(10px);
    }

    .result-title {
        margin: 0 0 0.4rem;
        font-size: 1.05rem;
        font-weight: 700;
    }

    .result-copy {
        margin: 0;
        color: var(--ink);
        line-height: 1.55;
        font-size: 0.98rem;
    }

    .footnote {
        color: var(--muted);
        font-size: 0.9rem;
        margin-top: 1rem;
    }

    div[data-baseweb="notification"] {
        border-radius: 18px;
        border: 1px solid rgba(255, 46, 147, 0.16);
    }

    div[data-baseweb="notification"] div[role="alert"] {
        color: #8f1553;
        font-weight: 600;
    }

    div[data-baseweb="notification"] p {
        color: #8f1553;
    }

    div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-3) 100%);
        color: #fff7f0;
        border: none;
        border-radius: 16px;
        min-height: 3.2rem;
        font-weight: 700;
        font-size: 1rem;
        letter-spacing: 0.01em;
        box-shadow: 0 12px 28px rgba(255, 46, 147, 0.24);
    }

    div[data-testid="stFormSubmitButton"] button:hover {
        background: linear-gradient(135deg, #e52684 0%, #f47d00 100%);
        color: #fffaf5;
    }

    div[data-testid="stFormSubmitButton"] button p {
        color: inherit;
    }

    div[data-testid="stFormSubmitButton"] button:disabled,
    div[data-testid="stFormSubmitButton"] button[disabled] {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-3) 100%);
        color: #fff7f0 !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #fff7f0;
        filter: none !important;
    }

    div[data-testid="stFormSubmitButton"] button:disabled *,
    div[data-testid="stFormSubmitButton"] button[disabled] * {
        color: #fff7f0 !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #fff7f0;
        fill: #fff7f0 !important;
        filter: none !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
    }

    @media (max-width: 640px) {
        .hero {
            padding: 1.45rem 1rem 1.05rem;
        }

        .hero-kicker {
            font-size: 0.68rem;
            letter-spacing: 0.14em;
            margin-bottom: 0.5rem;
        }

        .hero-title {
            font-size: clamp(1.7rem, 7.4vw, 2.2rem) !important;
            line-height: 0.92 !important;
            margin: 0 auto 0.02rem;
            padding-top: 0.35rem;
        }

        .hero-image {
            width: min(280px, 72vw);
            margin: 0.02rem auto 0.75rem;
        }

        .hero-subtitle {
            margin-top: 0.55rem;
            max-width: 18rem;
        }
    }
</style>
"""


PERIOD_OPTIONS = {
    "Hari ini": "today",
    "Minggu ini": "week",
    "Tahun ini": "year",
}

QUESTION_FOCUS_OPTIONS = [
    "Umum",
    "Keuangan",
    "Karir",
    "Asmara",
    "Kesehatan",
]

TIME_OPTIONS = ["Tidak Tahu"] + [f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30)]

SECTION_ORDER = [
    "BaZi",
    "Western Astrology",
    "Numerologi",
    "Intinya",
]

ERROR_MESSAGE = (
    "Madame lagi istirahat, tolong jangan diganggu. "
    "Silakan balik lagi besok, siapa tau toko udah buka lagi beb!"
)


def ensure_app_state() -> None:
    st.session_state.setdefault("forecast_result", None)
    st.session_state.setdefault("forecast_name", "")
    st.session_state.setdefault("forecast_birth_label", "")
    st.session_state.setdefault("forecast_place", "")
    st.session_state.setdefault("forecast_notice", None)
    st.session_state.setdefault("session_ready", False)

def get_openai_settings() -> tuple[str, str, str, str | None]:
    try:
        api_key = str(st.secrets["OPENAI_API_KEY"]).strip()
    except Exception:
        st.write(ERROR_MESSAGE)
        st.stop()

    if not api_key:
        st.write(ERROR_MESSAGE)
        st.stop()

    model = str(st.secrets.get("OPENAI_MODEL", "gpt-5.4-mini")).strip() or "gpt-5.4-mini"
    reasoning_effort = str(st.secrets.get("OPENAI_REASONING_EFFORT", "")).strip()
    base_url_value = str(st.secrets.get("OPENAI_BASE_URL", "")).strip()
    base_url = base_url_value or None
    return api_key, model, reasoning_effort, base_url


def encode_image(path: str) -> str:
    image_bytes = Path(path).read_bytes()
    return base64.b64encode(image_bytes).decode("utf-8")


def validate_inputs(
    *,
    name: str,
    birth_date: date | None,
    birth_place: str,
    period_label: str | None,
    question_focus: str | None,
) -> list[str]:
    missing_fields: list[str] = []
    if not name.strip():
        missing_fields.append("nama")
    if birth_date is None:
        missing_fields.append("tanggal lahir")
    if not birth_place.strip():
        missing_fields.append("tempat lahir")
    if not period_label:
        missing_fields.append("periode ramalan")
    if not question_focus:
        missing_fields.append("mau tanya apa")
    return missing_fields


def parse_birth_time(label: str) -> tuple[time | None, bool]:
    if label == "Tidak Tahu":
        return None, False
    return datetime.strptime(label, "%H:%M").time(), True

def main() -> None:
    ensure_app_state()
    header_image = encode_image("header.png")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <section class="hero">
            <div class="hero-kicker">Ramalan Multiserver</div>
            <div class="hero-title">Madame, help!</div>
            <img class="hero-image" src="data:image/png;base64,{header_image}" alt="madame, damn! header">
            <div class="hero-subtitle-wrap">
                <p class="hero-subtitle" style="font-size: 12px; line-height: 1.5; color: #ff2e93; font-weight: 500; margin-top: 0.55rem;">
                    Ringkas dan playful. Menghadirkan ramalan menurut BaZi, Western Astrology, dan Numerologi. Buruan cek tiap hari!
                </p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="section-label">SPILL SPILL SPILL!</div>', unsafe_allow_html=True)

        with st.form("fortune_form"):
            name = st.text_input(
                "Nama",
                placeholder="Tulis nama kamu",
            )
            col1, col2 = st.columns([1.2, 1])
            with col1:
                birth_date = st.date_input(
                    "Tanggal lahir",
                    value=date(1995, 6, 15),
                    min_value=date(1900, 1, 1),
                    max_value=date.today(),
                )
            with col2:
                birth_time_label = st.selectbox(
                    "Jam lahir",
                    options=TIME_OPTIONS,
                    index=TIME_OPTIONS.index("12:00"),
                )

            birth_place = st.text_input(
                "Tempat lahir",
                placeholder="Contoh: Jakarta, Indonesia",
            )
            period_label = st.selectbox(
                "Ramalan untuk",
                options=list(PERIOD_OPTIONS.keys()),
            )
            question_focus = st.selectbox(
                "Mau tanya apa?",
                options=QUESTION_FOCUS_OPTIONS,
                index=0,
            )

            submitted = st.form_submit_button("Buka ramalannya", use_container_width=True)

    if submitted:
        # guard: pastikan session sudah fully initialized
        if not st.session_state.get("session_ready"):
            st.session_state["session_ready"] = True
            st.rerun()

        st.session_state["forecast_notice"] = None
#        st.session_state["forecast_result"] = None
#        st.session_state["forecast_name"] = ""
#        st.session_state["forecast_birth_label"] = ""
#        st.session_state["forecast_place"] = ""
#        st.session_state["forecast_notice"] = None

        resolved_birth_place = birth_place.strip()

        missing_fields = validate_inputs(
            name=name,
            birth_date=birth_date,
            birth_place=resolved_birth_place,
            period_label=period_label,
            question_focus=question_focus,
        )
        if missing_fields:
            st.error(
                "Data kurang lengkap. Mohon lengkapi: "
                + ", ".join(missing_fields)
                + "."
            )
        else:
            cleaned_name = name.strip()
            birth_time, is_birth_time_known = parse_birth_time(birth_time_label)

            api_key, model, reasoning_effort, base_url = get_openai_settings()
            with st.spinner("Madame sedang menyusun arah energimu..."):
                forecast = None
                try:
                    forecast = fortune_engine.generate_fortune(
                        api_key=api_key,
                        model=model,
                        reasoning_effort=reasoning_effort,
                        base_url=base_url,
                        name=cleaned_name,
                        birth_date=birth_date,
                        birth_time=birth_time,
                        is_birth_time_known=is_birth_time_known,
                        birth_place=resolved_birth_place,
                        period_label=period_label,
                        period_key=PERIOD_OPTIONS[period_label],
                        question_focus=question_focus,
                    )
                    st.session_state["forecast_notice"] = None
                except Exception:
                    try:
                        forecast = fortune_engine.generate_fallback_fortune(
                            name=cleaned_name,
                            birth_date=birth_date,
                            birth_time=birth_time,
                            is_birth_time_known=is_birth_time_known,
                            birth_place=resolved_birth_place,
                            period_label=period_label,
                            period_key=PERIOD_OPTIONS[period_label],
                            question_focus=question_focus,
                        )
                    except Exception:
                        st.session_state["forecast_notice"] = ERROR_MESSAGE
                    else:
                        st.session_state["forecast_notice"] = None

                if forecast:
                    if birth_time is not None:
                        local_birth_label = datetime.combine(birth_date, birth_time).strftime("%d %b %Y %H:%M")
                    else:
                        local_birth_label = f"{birth_date.strftime('%d %b %Y')} (jam tidak diketahui)"

                    st.session_state["forecast_result"] = forecast
                    st.session_state["forecast_name"] = cleaned_name
                    st.session_state["forecast_birth_label"] = local_birth_label
                    st.session_state["forecast_place"] = resolved_birth_place

    forecast = st.session_state.get("forecast_result")
    notice = st.session_state.get("forecast_notice")
    forecast_name = st.session_state.get("forecast_name", "").strip()
    if not forecast:
        if notice:
            st.write(notice)
        return

    if notice:
        st.write(notice)

    st.markdown('<div class="section-label">RAHASIA AKAN TERUNGKAP!</div>', unsafe_allow_html=True)
    if forecast_name:
        st.markdown(
            f"<p class='footnote'>Ini ramalan buat <strong>{escape(forecast_name)}</strong>, obviously.</p>",
            unsafe_allow_html=True,
        )
    for section in SECTION_ORDER:
        content = escape(forecast.get(section, "").strip())
        if not content:
            content = "Arah energinya masih blur. Coba kirim ulang untuk pembacaan yang lebih rapi."
        st.markdown(
            f"""
            <section class="result-card">
                <h3 class="result-title">{escape(section)}</h3>
                <p class="result-copy">{content}</p>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.write("")

    st.markdown(
        (
            f"<p class='footnote'>Input yang dipakai: "
            f"{escape(st.session_state['forecast_birth_label'])} di {escape(st.session_state['forecast_place'])}.</p>"
        ),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
