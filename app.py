import datetime
import re
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


# =========================================================
# US Equity Signal Intelligence
#
# 핵심 변경
# 1) 공통 포커스 티커 1개로 전체 탭 연동
# 2) 1번 탭: S&P500/Nasdaq100 동적 후보군 실패 시에도 대체 후보군으로 조사 가능
# 3) 2번 탭: 단타에 바로 쓰기 쉬운 매수/매도/손절 행동지침 추가
# 4) 기존 3번 과거 검증 탭 제거
# 5) 3번 탭: AI 종합 투자 의견 + 1년 예상 주가 시나리오 + 발표 일정 + 뉴스 영향 통계 판단
# 6) 앱 접속 시 데이터 자동 조사 없음
#
# 실행:
# py -m streamlit run us_equity_signal_intelligence.py
#
# 필요 패키지:
# py -m pip install streamlit pandas numpy yfinance plotly lxml
# =========================================================


# -----------------------------
# 페이지 설정
# -----------------------------
st.set_page_config(
    page_title="US Equity Signal Intelligence",
    layout="wide",
)

KST = ZoneInfo("Asia/Seoul")
NY = ZoneInfo("America/New_York")
TODAY_KST = datetime.datetime.now(KST).date()
TODAY_NY = datetime.datetime.now(NY).date()


# -----------------------------
# Toss-like UI 스타일
# -----------------------------
st.markdown(
    """
    <style>
    :root {
        --bg: #f7f8fa;
        --card: #ffffff;
        --text: #191f28;
        --sub: #6b7684;
        --blue: #3182f6;
        --red: #f04452;
        --green: #00b894;
        --yellow: #f59f00;
        --border: #e5e8eb;
        --soft-blue: #eef6ff;
        --soft-red: #fff1f2;
        --soft-green: #effcf6;
        --soft-yellow: #fff8e1;
    }

    .stApp {
        background: var(--bg);
        color: var(--text);
    }

    section.main > div {
        padding-top: 1.2rem;
    }

    h1, h2, h3 {
        color: var(--text);
        letter-spacing: -0.035em;
        font-weight: 850;
    }

    p, label, span, div {
        letter-spacing: -0.015em;
    }

    div[data-testid="stMetric"] {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 18px 20px;
        box-shadow: 0 8px 24px rgba(25, 31, 40, 0.04);
    }

    div[data-testid="stMetricLabel"] {
        color: var(--sub);
        font-size: 0.9rem;
    }

    div[data-testid="stMetricValue"] {
        color: var(--text);
        font-weight: 850;
        font-size: 1.55rem;
    }

    .stButton > button {
        border-radius: 16px;
        border: 0;
        background: white;
        color: var(--text);
        font-weight: 800;
        padding: 0.65rem 1rem;
        box-shadow: 0 6px 18px rgba(25, 31, 40, 0.05);
    }

    .stButton > button[kind="primary"] {
        background: var(--blue);
        color: white;
    }

    button[data-baseweb="tab"] {
        border-radius: 999px;
        padding: 8px 16px;
        background: white;
        border: 1px solid var(--border);
        color: var(--sub);
        font-weight: 800;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: var(--blue);
        color: white;
        border-color: var(--blue);
    }

    div[data-testid="stAlert"] {
        border-radius: 18px;
        border: 1px solid var(--border);
        box-shadow: 0 8px 24px rgba(25, 31, 40, 0.04);
    }

    div[data-testid="stDataFrame"] {
        background: var(--card);
        border-radius: 22px;
        overflow: hidden;
        box-shadow: 0 8px 24px rgba(25, 31, 40, 0.04);
    }

    div[data-testid="stPlotlyChart"] {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 12px;
        box-shadow: 0 8px 24px rgba(25, 31, 40, 0.04);
    }

    .hero {
        background: linear-gradient(135deg, #ffffff 0%, #eef6ff 100%);
        border: 1px solid var(--border);
        border-radius: 30px;
        padding: 26px 28px;
        margin-bottom: 18px;
        box-shadow: 0 12px 32px rgba(25, 31, 40, 0.06);
    }

    .hero-title {
        font-size: 1.7rem;
        line-height: 1.25;
        font-weight: 900;
        color: var(--text);
        margin-bottom: 8px;
    }

    .hero-sub {
        font-size: 1.02rem;
        line-height: 1.6;
        color: var(--sub);
    }

    .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 20px 22px;
        margin: 14px 0;
        box-shadow: 0 8px 24px rgba(25, 31, 40, 0.04);
    }

    .card-title {
        font-size: 1.12rem;
        font-weight: 850;
        color: var(--text);
        margin-bottom: 6px;
    }

    .card-sub {
        font-size: 0.96rem;
        color: var(--sub);
        line-height: 1.55;
    }

    .badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: var(--soft-blue);
        color: var(--blue);
        font-weight: 850;
        font-size: 0.84rem;
        margin-right: 6px;
    }

    .signal-buy {
        background: var(--soft-green);
        border: 1px solid #c7f3df;
    }

    .signal-wait {
        background: var(--soft-yellow);
        border: 1px solid #ffe7a3;
    }

    .signal-risk {
        background: var(--soft-red);
        border: 1px solid #ffd1d6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-title">{title}</div>
            <div class="hero-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(title: str, subtitle: str, badge: str | None = None, css_class: str = "") -> None:
    badge_html = f'<span class="badge">{badge}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="card {css_class}">
            <div class="card-title">{badge_html}{title}</div>
            <div class="card-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# 세션 상태 초기화
# -----------------------------
DEFAULT_STATE = {
    "global_ticker": "",
    "focus_nonce": 0,
    "market_scan_df": pd.DataFrame(),
    "market_scan_done": False,
    "scanner_refresh_token": 0,
    "scalp_refresh_token": 0,
    "scalp_result": {},
    "scalp_result_done": False,
    "ai_refresh_token": 0,
    "ai_result": {},
    "ai_result_done": False,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# 호재 키워드/분류
# =========================================================
CATALYST_KEYWORDS = {
    "실적/가이던스": [
        "earnings", "revenue", "profit", "eps", "guidance", "forecast",
        "beats estimates", "raises outlook", "record sales", "margin",
    ],
    "계약/수주": [
        "contract", "deal", "order", "partnership", "strategic partnership",
        "supplier", "customer win", "award", "agreement", "license",
    ],
    "AI/기술": [
        "ai", "artificial intelligence", "chip", "semiconductor", "data center",
        "cloud", "gpu", "software", "platform", "launch", "innovation",
        "model", "agent", "robot", "automation",
    ],
    "인수합병/투자": [
        "acquisition", "merger", "takeover", "buyout", "stake", "investment",
        "joint venture", "spin off", "spinoff",
    ],
    "규제/승인": [
        "approval", "fda", "clearance", "authorized", "regulatory", "patent",
        "court", "settlement", "lawsuit", "antitrust",
    ],
    "주주환원": [
        "buyback", "repurchase", "dividend", "split", "stock split",
        "capital return",
    ],
    "월가평가": [
        "upgrade", "downgrade", "price target", "initiates", "analyst",
        "rating", "buy rating", "outperform",
    ],
    "발표/컨퍼런스": [
        "conference", "investor day", "presentation", "webcast", "summit",
        "to present", "event", "launch event", "product event", "demo",
    ],
}


# 대체 후보군: Wikipedia/lxml/인터넷 실패 시 사용.
# 고정 관심종목이 아니라, 앱이 깨지지 않도록 넣은 넓은 시장 대표 후보군.
FALLBACK_US_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "AMD",
    "NFLX", "ADBE", "CRM", "ORCL", "CSCO", "QCOM", "INTC", "TXN", "MU", "AMAT",
    "LRCX", "KLAC", "PANW", "CRWD", "SNOW", "NET", "DDOG", "MDB", "PLTR", "SOUN",
    "COIN", "MSTR", "HOOD", "SQ", "PYPL", "SHOP", "UBER", "ABNB", "RBLX", "ROKU",
    "LLY", "NVO", "UNH", "JNJ", "MRK", "ABBV", "PFE", "MRNA", "AMGN", "GILD",
    "VRTX", "REGN", "ISRG", "TMO", "DHR", "GEHC", "ELV", "CI", "CVS", "HUM",
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "V", "MA", "BLK",
    "XOM", "CVX", "COP", "SLB", "EOG", "OXY", "MPC", "PSX", "VLO", "HAL",
    "FCX", "NEM", "AA", "CLF", "X", "CAT", "DE", "GE", "BA", "RTX",
    "LMT", "NOC", "HON", "ETN", "EMR", "PH", "MMM", "UPS", "FDX", "DAL",
    "UAL", "AAL", "LUV", "NKE", "SBUX", "MCD", "CMG", "COST", "WMT", "TGT",
    "HD", "LOW", "TJX", "LULU", "CELH", "PEP", "KO", "MNST", "PG", "EL",
    "RIVN", "LCID", "NIO", "LI", "XPEV", "F", "GM", "TM", "TSM", "ASML",
]


# =========================================================
# 공통 유틸
# =========================================================
def normalize_ticker(value: str, default: str = "") -> str:
    if value is None:
        return default
    value = str(value).strip().upper().replace(".", "-")
    return value if value else default


def safe_float(value, default=np.nan) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def price_text(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"${value:,.2f}"


def percent_text(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{digits}f}%"


def number_text(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:,.{digits}f}"


def clean_display_text(value, default: str = "-") -> str:
    """화면에 표시하기 어려운 None/nan/숫자코드/빈 리스트를 정리한다."""
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except Exception:
        pass

    if isinstance(value, (list, tuple, set)):
        value = [clean_display_text(v, "") for v in value]
        value = [v for v in value if v]
        return ", ".join(value) if value else default

    if isinstance(value, dict):
        return default

    # 60000000 같은 숫자 코드성 값은 일정표에 그대로 노출하지 않는다.
    if isinstance(value, (int, float, np.integer, np.floating)):
        if abs(float(value)) > 100000:
            return default
        return str(value)

    txt = str(value).strip()
    bad_values = {"", "none", "nan", "nat", "null", "[]", "{}", "-"}
    if txt.lower() in bad_values:
        return default

    # 지나치게 긴 list/array 표현 정리
    txt = txt.replace("Timestamp(", "").replace("datetime.date(", "")
    txt = re.sub(r"\s+", " ", txt)
    return txt[:220] if txt else default


def parse_clean_date(value) -> str | None:
    """yfinance calendar의 다양한 날짜/리스트 값을 YYYY-MM-DD로 정리한다."""
    if value is None:
        return None

    if isinstance(value, (list, tuple, set)):
        for v in value:
            parsed = parse_clean_date(v)
            if parsed:
                return parsed
        return None

    if isinstance(value, dict):
        return None

    # 숫자만 있는 값은 날짜가 아니라 재무 수치일 가능성이 높아 제외
    if isinstance(value, (int, float, np.integer, np.floating)):
        return None

    txt = clean_display_text(value, "")
    if not txt:
        return None

    try:
        dt = pd.to_datetime(txt, errors="coerce", utc=False)
        if pd.isna(dt):
            return None
        if hasattr(dt, "date"):
            d = dt.date()
        else:
            return None

        # 너무 과거/먼 미래 값은 일정표에서 제외
        if d < TODAY_NY - datetime.timedelta(days=45):
            return None
        if d > TODAY_NY + datetime.timedelta(days=730):
            return None
        return d.strftime("%Y-%m-%d")
    except Exception:
        return None


def classify_event_importance(event_type: str, content: str = "") -> tuple[str, str]:
    txt = f"{event_type} {content}".lower()

    if any(k in txt for k in ["earnings", "실적", "guidance", "fda", "approval", "investor day", "product", "launch", "program"]):
        return "높음", "실적·가이던스·제품/프로그램 발표는 중장기 밸류에이션과 단기 변동성을 동시에 바꿀 수 있습니다."
    if any(k in txt for k in ["conference", "presentation", "webcast", "summit", "컨퍼런스", "발표"]):
        return "중간", "컨퍼런스/발표는 신제품·수주·가이던스 힌트가 나올 수 있어 일정 전후 변동성이 커질 수 있습니다."
    return "낮음", "직접적인 실적 영향은 제한적일 수 있지만, 일정 전후 주가 반응은 확인할 가치가 있습니다."


def make_beginner_importance(row: pd.Series) -> tuple[str, str, str]:
    score = safe_float(row.get("가격/거래량 점수", 0), 0)
    news_score = safe_float(row.get("뉴스 영향 점수", 0), 0)
    ret1 = safe_float(row.get("1일 수익률(%)", np.nan))
    volx = safe_float(row.get("거래량 배율", np.nan))

    total = score + news_score

    if total >= 25 or (not pd.isna(ret1) and ret1 >= 5 and not pd.isna(volx) and volx >= 1.5):
        importance = "높음"
        why = "가격 상승과 거래량 증가가 같이 나타나 시장이 실제로 반응했을 가능성이 큽니다."
        beginner = "초보자는 바로 추격매수하지 말고, 2번 탭에서 매수 대기 구간을 확인하세요."
    elif total >= 12 or (not pd.isna(ret1) and ret1 >= 2):
        importance = "중간"
        why = "상승 반응은 있지만 뉴스/거래량 확인이 더 필요합니다."
        beginner = "관심 후보로 저장하고, 당일 고점 근처에서는 신규 진입을 피하세요."
    else:
        importance = "낮음"
        why = "아직 주가에 강하게 반영된 호재라고 보기 어렵습니다."
        beginner = "초보자는 우선 관망하고 더 강한 후보를 보는 편이 좋습니다."

    return importance, why, beginner


def summarize_recent_news(news_df: pd.DataFrame, news_impact: dict | None = None) -> dict:
    """최근 뉴스 테이블을 장기투자 관점의 한국어 요약으로 바꾼다."""
    summary = {
        "핵심 요약": "최근 뉴스를 불러오지 못했습니다.",
        "주가 영향 판단": "뉴스 데이터가 부족해 판단을 보류합니다.",
        "장기 투자 포인트": "실적, 가이던스, 제품 출시, 수주, 규제 이슈를 추가 확인하세요.",
        "주의할 점": "무료 뉴스 데이터는 누락될 수 있습니다.",
    }

    if news_df is None or news_df.empty:
        return summary

    titles = news_df.get("제목", pd.Series(dtype=str)).dropna().astype(str).head(8).tolist()
    tags = []
    if "호재 태그" in news_df.columns:
        for val in news_df["호재 태그"].dropna().astype(str).tolist():
            if val and val != "-":
                tags.extend([x.strip() for x in val.split(",") if x.strip()])

    tag_text = ", ".join(pd.Series(tags).value_counts().head(3).index.tolist()) if tags else "뚜렷한 호재 태그 없음"
    joined = " ".join(titles).lower()

    positive_terms = ["beat", "raises", "upgrade", "launch", "contract", "partnership", "approval", "growth", "surge", "record"]
    negative_terms = ["miss", "cut", "downgrade", "lawsuit", "probe", "falls", "drop", "recall", "warn"]
    pos = sum(1 for t in positive_terms if t in joined)
    neg = sum(1 for t in negative_terms if t in joined)

    if pos > neg:
        tone = "긍정 우위"
        impact = "최근 뉴스 흐름은 주가에 긍정적으로 작용할 가능성이 상대적으로 높습니다."
    elif neg > pos:
        tone = "리스크 우위"
        impact = "최근 뉴스에 리스크성 표현이 많아 단기 변동성과 하방 리스크를 조심해야 합니다."
    else:
        tone = "중립"
        impact = "최근 뉴스만으로는 방향성이 뚜렷하지 않아 가격·거래량 확인이 필요합니다."

    if news_impact:
        prob = news_impact.get("impact_probability", np.nan)
        avg5 = news_impact.get("avg_next_5d", np.nan)
        if not pd.isna(prob):
            impact += f" 과거 유사 충격 이후 5거래일 상승 확률은 {percent_text(prob)}이며, 평균 5거래일 수익률은 {percent_text(avg5)}입니다."

    summary["핵심 요약"] = f"최근 뉴스 톤은 '{tone}'입니다. 주요 테마는 {tag_text}입니다."
    summary["주가 영향 판단"] = impact
    summary["장기 투자 포인트"] = "실적 성장, 가이던스 상향, 제품/프로그램 발표, 대형 계약 여부가 장기 추세를 바꿀 핵심 변수입니다."
    summary["주의할 점"] = "뉴스가 좋아도 이미 주가가 급등했다면 단기 차익실현이 나올 수 있으므로, 1년 전망의 하단 시나리오도 함께 봐야 합니다."
    return summary


def make_long_term_strategy(metrics: dict, opinion: dict, projection_df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    current = safe_float(metrics.get("current_price", np.nan))
    score = safe_float(opinion.get("score", 50), 50)
    vol = safe_float(metrics.get("vol_20d", np.nan), np.nan)

    if pd.isna(current) or current <= 0:
        return pd.DataFrame()

    if score >= 70:
        stance = "분할 매수 가능"
        buy_zone = f"{price_text(current * 0.92)} ~ {price_text(current * 0.98)}"
    elif score >= 50:
        stance = "관찰 후 눌림목 매수"
        buy_zone = f"{price_text(current * 0.88)} ~ {price_text(current * 0.95)}"
    else:
        stance = "보수적 관망"
        buy_zone = f"{price_text(current * 0.80)} ~ {price_text(current * 0.90)}"

    event_count = 0 if events_df is None else len(events_df)
    risk = "높음" if (not pd.isna(vol) and vol >= 65) else "중간" if (not pd.isna(vol) and vol >= 40) else "낮음"

    return pd.DataFrame({
        "구분": ["AI 장기 의견", "분할 매수 관심 구간", "리스크 수준", "확인해야 할 이벤트", "초보자 행동"],
        "내용": [
            stance,
            buy_zone,
            risk,
            f"향후 확인 가능한 이벤트 {event_count}개. 실적 발표와 제품/컨퍼런스 일정 전후 변동성 확대 가능",
            "한 번에 매수하지 말고 3~5회 분할, 이벤트 전후 급등 시 추격보다 눌림목 확인",
        ],
    })

def build_yahoo_quote_link(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{ticker}"


def build_yahoo_news_link(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{ticker}/news"


def tokenize_direct_tickers(text: str) -> list[str]:
    if not text:
        return []
    candidates = re.split(r"[\s,;/]+", text)
    out = []
    for c in candidates:
        t = normalize_ticker(c)
        if t and t not in out:
            out.append(t)
    return out


def normalize_history_df(df: pd.DataFrame, ticker: str = "") -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if isinstance(out.columns, pd.MultiIndex):
        level0 = list(out.columns.get_level_values(0))
        level1 = list(out.columns.get_level_values(1))
        if "Close" in level0:
            out.columns = out.columns.get_level_values(0)
        elif "Close" in level1:
            if ticker and ticker in level0:
                try:
                    out = out.xs(ticker, axis=1, level=0)
                except Exception:
                    out.columns = out.columns.get_level_values(1)
            else:
                out.columns = out.columns.get_level_values(1)

    out = out.loc[:, ~out.columns.duplicated()].copy()
    return out


def extract_bulk_field(raw: pd.DataFrame, field: str) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        level0 = list(raw.columns.get_level_values(0))
        level1 = list(raw.columns.get_level_values(1))
        if field in level0:
            df = raw[field].copy()
            df.columns = [str(c).upper() for c in df.columns]
            return df
        if field in level1:
            df = raw.xs(field, axis=1, level=1).copy()
            df.columns = [str(c).upper() for c in df.columns]
            return df

    if field in raw.columns:
        return raw[[field]].copy()

    return pd.DataFrame()


def ensure_ny_timezone(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    try:
        if out.index.tz is None:
            out.index = out.index.tz_localize("UTC").tz_convert(NY)
        else:
            out.index = out.index.tz_convert(NY)
    except Exception:
        pass
    return out


def filter_by_ny_date(df: pd.DataFrame, target_date: datetime.date) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = ensure_ny_timezone(df)
    try:
        return out[out.index.date == target_date].copy()
    except Exception:
        return out.copy()


def convert_time_to_kst_label(ts) -> str:
    try:
        if getattr(ts, "tzinfo", None) is None:
            ts = ts.replace(tzinfo=NY)
        return ts.astimezone(KST).strftime("%m/%d %H:%M")
    except Exception:
        return "-"


def infer_case(selected_date: datetime.date) -> str:
    now_ny = datetime.datetime.now(NY)
    ny_today = now_ny.date()
    current_time = now_ny.time()

    if selected_date < ny_today:
        return "Case1. 과거: 예측치 vs 실제값"
    if selected_date > ny_today:
        return "Case2. 장 시작 전: 예측치 vs 프리마켓/확장시간"
    if current_time < datetime.time(9, 30):
        return "Case2. 장 시작 전: 예측치 vs 프리마켓/확장시간"
    if datetime.time(9, 30) <= current_time <= datetime.time(16, 0):
        return "Case3. 정규장 중: 예측치 vs 정규장 실제 변화"
    return "Case1. 과거: 예측치 vs 실제값"


def case_code(case_label: str) -> str:
    if case_label.startswith("Case1"):
        return "case1"
    if case_label.startswith("Case2"):
        return "case2"
    if case_label.startswith("Case3"):
        return "case3"
    return "case1"


def make_regular_time_grid(selected_date: datetime.date, freq_min: int = 5) -> pd.DatetimeIndex:
    start = datetime.datetime.combine(selected_date, datetime.time(9, 30), tzinfo=NY)
    end = datetime.datetime.combine(selected_date, datetime.time(16, 0), tzinfo=NY)
    return pd.date_range(start=start, end=end, freq=f"{freq_min}min")


def nearest_series_value(series: pd.Series, timestamp) -> float:
    if series is None or series.empty:
        return np.nan
    try:
        idx = series.index.get_indexer([timestamp], method="nearest")[0]
        if idx >= 0:
            return safe_float(series.iloc[idx])
    except Exception:
        pass
    return np.nan


def split_us_sessions(intraday_df: pd.DataFrame) -> dict:
    empty = pd.DataFrame()
    if intraday_df is None or intraday_df.empty:
        return {"premarket": empty, "regular": empty, "afterhours": empty, "all": empty}

    df = ensure_ny_timezone(intraday_df)
    times = pd.Series(df.index.time, index=df.index)

    pre = df[(times >= datetime.time(4, 0)) & (times <= datetime.time(9, 29))].copy()
    reg = df[(times >= datetime.time(9, 30)) & (times <= datetime.time(16, 0))].copy()
    aft = df[(times >= datetime.time(16, 1)) & (times <= datetime.time(20, 0))].copy()

    return {"premarket": pre, "regular": reg, "afterhours": aft, "all": df}


# =========================================================
# 후보군 동적 수집
# =========================================================
@st.cache_data(ttl=86400, show_spinner=False)
def discover_sp500_tickers() -> list[str]:
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        df = tables[0]
        if "Symbol" not in df.columns:
            return []
        tickers = [normalize_ticker(x) for x in df["Symbol"].dropna().astype(str).tolist()]
        return sorted(list(dict.fromkeys([t for t in tickers if t])))
    except Exception:
        return []


@st.cache_data(ttl=86400, show_spinner=False)
def discover_nasdaq100_tickers() -> list[str]:
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        for df in tables:
            possible_cols = [c for c in df.columns if str(c).lower() in ["ticker", "symbol"]]
            if possible_cols:
                col = possible_cols[0]
                tickers = [normalize_ticker(x) for x in df[col].dropna().astype(str).tolist()]
                tickers = [t for t in tickers if t and len(t) <= 8]
                if len(tickers) >= 50:
                    return sorted(list(dict.fromkeys(tickers)))
        return []
    except Exception:
        return []


def build_dynamic_universe(source_mode: str, direct_tickers: str = "", max_symbols: int = 250) -> tuple[list[str], str]:
    tickers = []
    source_note = ""

    if source_mode in ["S&P500 + Nasdaq100", "S&P500"]:
        tickers.extend(discover_sp500_tickers())

    if source_mode in ["S&P500 + Nasdaq100", "Nasdaq100"]:
        tickers.extend(discover_nasdaq100_tickers())

    if source_mode == "직접 입력":
        tickers.extend(tokenize_direct_tickers(direct_tickers))

    tickers = [normalize_ticker(t) for t in tickers]
    tickers = [t for t in tickers if t]
    tickers = list(dict.fromkeys(tickers))

    if not tickers and source_mode != "직접 입력":
        tickers = FALLBACK_US_UNIVERSE.copy()
        source_note = "Wikipedia/lxml 또는 인터넷 연결 문제로 동적 후보군을 가져오지 못해 대체 시장 후보군을 사용했습니다."
    elif not tickers and source_mode == "직접 입력":
        source_note = "직접 입력된 티커가 없습니다."
    else:
        source_note = "동적 후보군을 정상적으로 확보했습니다."

    if max_symbols and len(tickers) > max_symbols:
        tickers = tickers[:max_symbols]

    return tickers, source_note


# =========================================================
# 데이터 로딩
# =========================================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_bulk_market_data(tickers: tuple, period: str, refresh_token: int = 0) -> dict:
    del refresh_token
    if not tickers:
        return {"Close": pd.DataFrame(), "Volume": pd.DataFrame(), "Open": pd.DataFrame()}

    try:
        raw = yf.download(
            list(tickers),
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
            group_by="column",
        )
    except Exception:
        try:
            raw = yf.download(list(tickers), period=period, interval="1d", progress=False)
        except Exception:
            raw = pd.DataFrame()

    return {
        "Close": extract_bulk_field(raw, "Close"),
        "Volume": extract_bulk_field(raw, "Volume"),
        "Open": extract_bulk_field(raw, "Open"),
    }


@st.cache_data(ttl=300, show_spinner=False)
def fetch_daily_history_until(ticker: str, selected_date: datetime.date, lookback_days: int = 365, refresh_token: int = 0) -> pd.DataFrame:
    del refresh_token
    ticker = normalize_ticker(ticker)
    if not ticker:
        return pd.DataFrame()

    start_date = selected_date - datetime.timedelta(days=lookback_days)
    end_date = selected_date + datetime.timedelta(days=2)

    try:
        raw = yf.download(
            ticker,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        return normalize_history_df(raw, ticker=ticker)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_intraday_for_date(ticker: str, selected_date: datetime.date, refresh_token: int = 0) -> tuple[pd.DataFrame, str]:
    del refresh_token
    ticker = normalize_ticker(ticker)
    if not ticker:
        return pd.DataFrame(), ""

    start_date = selected_date.strftime("%Y-%m-%d")
    end_date = (selected_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    for interval in ["1m", "2m", "5m", "15m", "30m", "60m"]:
        try:
            raw = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval=interval,
                prepost=True,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            df = normalize_history_df(raw, ticker=ticker)
            df = ensure_ny_timezone(df)
            df = filter_by_ny_date(df, selected_date)
            if not df.empty and "Close" in df.columns:
                return df, interval
        except Exception:
            continue

    return pd.DataFrame(), ""


@st.cache_data(ttl=300, show_spinner=False)
def fetch_single_profile(ticker: str, refresh_token: int = 0) -> dict:
    del refresh_token
    ticker = normalize_ticker(ticker)

    fallback = {
        "ticker": ticker,
        "shortName": ticker,
        "longName": ticker,
        "sector": "-",
        "industry": "-",
        "currency": "USD",
        "currentPrice": np.nan,
        "regularMarketPrice": np.nan,
        "targetMeanPrice": np.nan,
        "targetHighPrice": np.nan,
        "targetLowPrice": np.nan,
        "recommendationKey": "-",
        "marketCap": np.nan,
        "trailingPE": np.nan,
        "forwardPE": np.nan,
    }

    if not ticker:
        return fallback

    try:
        info = yf.Ticker(ticker).get_info() or {}
        for key in fallback.keys():
            if key in info and info.get(key) is not None:
                fallback[key] = info.get(key)
        fallback["shortName"] = info.get("shortName") or info.get("longName") or ticker
        fallback["longName"] = info.get("longName") or fallback["shortName"] or ticker
        fallback["sector"] = info.get("sector") or "-"
        fallback["industry"] = info.get("industry") or "-"
        fallback["currency"] = info.get("currency") or "USD"
        return fallback
    except Exception:
        return fallback


@st.cache_data(ttl=600, show_spinner=False)
def fetch_ticker_news(ticker: str, refresh_token: int = 0) -> pd.DataFrame:
    del refresh_token
    ticker = normalize_ticker(ticker)
    rows = []

    if not ticker:
        return pd.DataFrame()

    try:
        news_items = yf.Ticker(ticker).news or []
        for item in news_items[:15]:
            content = item.get("content", {}) if isinstance(item, dict) else {}

            title = item.get("title") or content.get("title") or ""
            publisher = (
                item.get("publisher")
                or content.get("provider", {}).get("displayName")
                or content.get("provider", {}).get("name")
                or ""
            )
            link = (
                item.get("link")
                or item.get("clickThroughUrl", {}).get("url")
                or content.get("clickThroughUrl", {}).get("url")
                or content.get("canonicalUrl", {}).get("url")
                or ""
            )
            summary = item.get("summary") or content.get("summary") or content.get("description") or ""
            published = "-"

            provider_time = item.get("providerPublishTime")
            if provider_time:
                try:
                    published = datetime.datetime.fromtimestamp(
                        int(provider_time),
                        tz=datetime.timezone.utc,
                    ).astimezone(KST).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    published = "-"

            if published == "-":
                pub_date = content.get("pubDate") or item.get("pubDate")
                if pub_date:
                    try:
                        published = pd.to_datetime(pub_date).tz_convert(KST).strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        published = str(pub_date)

            impact_score, tags = score_news_catalyst(str(title), str(summary))

            rows.append({
                "티커": ticker,
                "일시(KST)": published,
                "매체": publisher,
                "제목": title,
                "호재 태그": tags,
                "키워드 점수": impact_score,
                "링크": link,
            })
    except Exception:
        pass

    return pd.DataFrame(rows)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_event_calendar(ticker: str, refresh_token: int = 0) -> pd.DataFrame:
    """
    무료 데이터 기반 일정 수집.
    None, 숫자 코드, 영문 원시 필드명을 그대로 노출하지 않고 장기투자 관점으로 정리한다.
    """
    del refresh_token
    ticker = normalize_ticker(ticker)
    rows = []

    if not ticker:
        return pd.DataFrame()

    try:
        obj = yf.Ticker(ticker)

        # 1) 실적 발표 일정
        try:
            earnings = obj.get_earnings_dates(limit=12)
            if isinstance(earnings, pd.DataFrame) and not earnings.empty:
                tmp = earnings.copy().reset_index()
                tmp.columns = [str(c) for c in tmp.columns]
                date_col = tmp.columns[0]
                for _, row in tmp.iterrows():
                    dt_str = parse_clean_date(row.get(date_col))
                    if not dt_str:
                        continue
                    importance, meaning = classify_event_importance("실적 발표", "earnings")
                    rows.append({
                        "예정일": dt_str,
                        "일정 유형": "실적 발표",
                        "중요도": importance,
                        "장기투자 관점": meaning,
                        "내용": f"{ticker} 실적 발표 예상일",
                        "출처": "Yahoo Finance",
                    })
        except Exception:
            pass

        # 2) Calendar 원시값 정리. 날짜로 해석 가능한 값만 사용.
        try:
            cal = obj.calendar
            if isinstance(cal, dict):
                for k, v in cal.items():
                    dt_str = parse_clean_date(v)
                    if not dt_str:
                        continue
                    k_txt = clean_display_text(k)
                    importance, meaning = classify_event_importance(k_txt, clean_display_text(v))
                    rows.append({
                        "예정일": dt_str,
                        "일정 유형": "기업 일정",
                        "중요도": importance,
                        "장기투자 관점": meaning,
                        "내용": k_txt,
                        "출처": "Yahoo Finance Calendar",
                    })
            elif isinstance(cal, pd.DataFrame) and not cal.empty:
                cal_df = cal.reset_index()
                for _, row in cal_df.iterrows():
                    item = clean_display_text(row.iloc[0]) if len(row) > 0 else "기업 일정"
                    raw_val = row.iloc[1] if len(row) > 1 else None
                    dt_str = parse_clean_date(raw_val)
                    if not dt_str:
                        continue
                    importance, meaning = classify_event_importance(item, clean_display_text(raw_val))
                    rows.append({
                        "예정일": dt_str,
                        "일정 유형": "기업 일정",
                        "중요도": importance,
                        "장기투자 관점": meaning,
                        "내용": item,
                        "출처": "Yahoo Finance Calendar",
                    })
        except Exception:
            pass

    except Exception:
        pass

    # 3) 뉴스 제목에서 발표/컨퍼런스성 일정 포착
    try:
        news_df = fetch_ticker_news(ticker, refresh_token=refresh_token)
        if news_df is not None and not news_df.empty:
            mask = news_df["제목"].astype(str).str.lower().str.contains(
                "conference|presentation|investor day|webcast|summit|to present|event|launch|program|demo|earnings",
                regex=True,
                na=False,
            )
            for _, row in news_df[mask].head(8).iterrows():
                dt_str = parse_clean_date(row.get("일시(KST)")) or clean_display_text(row.get("일시(KST)"), "최근")
                title = clean_display_text(row.get("제목"))
                if title == "-":
                    continue
                importance, meaning = classify_event_importance("발표/컨퍼런스", title)
                rows.append({
                    "예정일": dt_str,
                    "일정 유형": "발표/컨퍼런스 관련 뉴스",
                    "중요도": importance,
                    "장기투자 관점": meaning,
                    "내용": title,
                    "출처": clean_display_text(row.get("매체"), "Yahoo News"),
                })
    except Exception:
        pass

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.replace({None: "-", "None": "-", "nan": "-", "NaN": "-"})
    df = df[df["예정일"].astype(str).str.lower().ne("none")]
    df = df[df["내용"].astype(str).str.lower().ne("none")]
    df = df.drop_duplicates(subset=["예정일", "일정 유형", "내용"]).reset_index(drop=True)
    return df[["예정일", "일정 유형", "중요도", "장기투자 관점", "내용", "출처"]]


# =========================================================
# 분석 함수
# =========================================================
def score_news_catalyst(title: str, summary: str = "") -> tuple[int, str]:
    text = f"{title} {summary}".lower()
    matched_tags = []
    score = 0

    for tag, keywords in CATALYST_KEYWORDS.items():
        hit_count = sum(1 for kw in keywords if kw.lower() in text)
        if hit_count > 0:
            matched_tags.append(tag)
            score += min(hit_count, 3) * 3

    positive_terms = [
        "surge", "soar", "rally", "jump", "rise", "gain", "record high",
        "breakout", "strong demand", "better than expected", "wins", "launches",
    ]
    negative_terms = [
        "miss", "falls", "drops", "lawsuit", "probe", "investigation",
        "downgrade", "cuts", "warns", "recall",
    ]

    for term in positive_terms:
        if term in text:
            score += 2

    for term in negative_terms:
        if term in text:
            score -= 2

    score = int(np.clip(score, -20, 35))
    tag_text = ", ".join(matched_tags) if matched_tags else "-"

    return score, tag_text


def calculate_price_event_candidates(market_data: dict) -> pd.DataFrame:
    close = market_data.get("Close", pd.DataFrame())
    volume = market_data.get("Volume", pd.DataFrame())
    open_df = market_data.get("Open", pd.DataFrame())

    if close is None or close.empty:
        return pd.DataFrame()

    rows = []

    for ticker in close.columns:
        c = close[ticker].dropna()
        if len(c) < 22:
            continue

        current = safe_float(c.iloc[-1])
        prev_1 = safe_float(c.iloc[-2]) if len(c) >= 2 else np.nan
        prev_5 = safe_float(c.iloc[-6]) if len(c) >= 6 else np.nan
        prev_20 = safe_float(c.iloc[-21]) if len(c) >= 21 else np.nan

        if pd.isna(current) or current <= 0:
            continue

        ret_1d = ((current / prev_1) - 1) * 100 if not pd.isna(prev_1) and prev_1 > 0 else np.nan
        ret_5d = ((current / prev_5) - 1) * 100 if not pd.isna(prev_5) and prev_5 > 0 else np.nan
        ret_20d = ((current / prev_20) - 1) * 100 if not pd.isna(prev_20) and prev_20 > 0 else np.nan

        daily_ret = c.pct_change().dropna()
        vol_20d_price = daily_ret.tail(20).std() * np.sqrt(252) * 100 if len(daily_ret) >= 5 else np.nan

        volume_surge = np.nan
        if volume is not None and not volume.empty and ticker in volume.columns:
            v = volume[ticker].dropna()
            if len(v) >= 21:
                latest_v = safe_float(v.iloc[-1])
                avg20_v = safe_float(v.iloc[-21:-1].mean())
                if not pd.isna(avg20_v) and avg20_v > 0:
                    volume_surge = latest_v / avg20_v

        gap_pct = np.nan
        if open_df is not None and not open_df.empty and ticker in open_df.columns:
            o = open_df[ticker].dropna()
            if len(o) >= 1 and not pd.isna(prev_1) and prev_1 > 0:
                latest_open = safe_float(o.iloc[-1])
                if not pd.isna(latest_open):
                    gap_pct = ((latest_open / prev_1) - 1) * 100

        ret_1d_s = np.nan_to_num(ret_1d, nan=0.0)
        ret_5d_s = np.nan_to_num(ret_5d, nan=0.0)
        ret_20d_s = np.nan_to_num(ret_20d, nan=0.0)
        volume_s = np.nan_to_num(volume_surge, nan=1.0)
        gap_s = np.nan_to_num(gap_pct, nan=0.0)

        price_score = 0.0
        price_score += np.clip(ret_1d_s, -10, 15) * 1.6
        price_score += np.clip(ret_5d_s, -15, 25) * 0.7
        price_score += np.clip(ret_20d_s, -20, 40) * 0.25
        price_score += max(volume_s - 1.0, 0) * 7
        price_score += max(gap_s, 0) * 0.9
        if not pd.isna(vol_20d_price):
            price_score -= max(vol_20d_price - 80, 0) * 0.04

        if ret_1d_s >= 5 and volume_s >= 1.5:
            reaction = "강한 호재 반응 후보"
        elif ret_5d_s >= 8 and volume_s >= 1.2:
            reaction = "누적 매수세 후보"
        elif ret_1d_s >= 2 or ret_5d_s >= 4:
            reaction = "상승 반응 관찰"
        else:
            reaction = "약한 반응"

        try:
            reaction_date = pd.to_datetime(c.index[-1]).strftime("%Y-%m-%d")
        except Exception:
            reaction_date = "-"

        temp_row = pd.Series({
            "가격/거래량 점수": price_score,
            "뉴스 영향 점수": 0,
            "1일 수익률(%)": ret_1d,
            "거래량 배율": volume_surge,
        })
        importance, why_important, beginner_view = make_beginner_importance(temp_row)

        rows.append({
            "티커": ticker,
            "호재 포착일": reaction_date,
            "중요도": importance,
            "초보자 해석": beginner_view,
            "왜 중요한가": why_important,
            "현재가": current,
            "1일 수익률(%)": ret_1d,
            "5일 수익률(%)": ret_5d,
            "20일 수익률(%)": ret_20d,
            "거래량 배율": volume_surge,
            "시가 갭(%)": gap_pct,
            "20일 변동성(%)": vol_20d_price,
            "가격/거래량 점수": price_score,
            "시장 반응": reaction,
            "뉴스 링크": build_yahoo_news_link(ticker),
            "종목 링크": build_yahoo_quote_link(ticker),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    return df.sort_values(by="가격/거래량 점수", ascending=False).reset_index(drop=True)


def enrich_candidates_with_news(candidate_df: pd.DataFrame, news_scan_count: int, refresh_token: int = 0) -> pd.DataFrame:
    if candidate_df is None or candidate_df.empty:
        return pd.DataFrame()

    out = candidate_df.copy()
    out["최근 뉴스 제목"] = "-"
    out["호재 태그"] = "-"
    out["뉴스 영향 점수"] = 0
    out["호재 임팩트 점수"] = out["가격/거래량 점수"]

    scan_tickers = out["티커"].head(news_scan_count).tolist()
    progress = st.progress(0)
    status = st.empty()

    for idx, ticker in enumerate(scan_tickers):
        status.caption(f"뉴스/호재 영향 판단 중: {ticker} ({idx + 1}/{len(scan_tickers)})")
        news_df = fetch_ticker_news(ticker, refresh_token=refresh_token)

        if not news_df.empty:
            best = news_df.sort_values(by="키워드 점수", ascending=False).iloc[0]
            score = safe_float(best.get("키워드 점수", 0), default=0)
            mask = out["티커"] == ticker
            out.loc[mask, "최근 뉴스 제목"] = str(best.get("제목", "-"))
            out.loc[mask, "호재 태그"] = str(best.get("호재 태그", "-"))
            out.loc[mask, "뉴스 영향 점수"] = score
            out.loc[mask, "호재 임팩트 점수"] = out.loc[mask, "가격/거래량 점수"] + score

            news_date = parse_clean_date(best.get("일시(KST)", ""))
            if news_date:
                out.loc[mask, "호재 포착일"] = news_date

            # 뉴스 반영 후 중요도/초보자 해석 재계산
            for ridx in out[mask].index:
                importance, why_important, beginner_view = make_beginner_importance(out.loc[ridx])
                out.loc[ridx, "중요도"] = importance
                out.loc[ridx, "왜 중요한가"] = why_important
                out.loc[ridx, "초보자 해석"] = beginner_view

        progress.progress((idx + 1) / max(len(scan_tickers), 1))

    progress.empty()
    status.empty()

    return out.sort_values(by="호재 임팩트 점수", ascending=False).reset_index(drop=True)


def calculate_daily_features(daily_df: pd.DataFrame, selected_date: datetime.date) -> dict:
    features = {
        "prev_close": np.nan,
        "atr20_pct": np.nan,
        "ret5_pct": np.nan,
        "ret20_pct": np.nan,
        "vol20_pct": np.nan,
        "volume_surge": np.nan,
    }

    if daily_df is None or daily_df.empty or "Close" not in daily_df.columns:
        return features

    df = daily_df.copy()
    try:
        df.index = pd.to_datetime(df.index)
        prior = df[df.index.date < selected_date].copy()
    except Exception:
        prior = df.copy()

    if prior.empty:
        return features

    close = prior["Close"].dropna()
    if close.empty:
        return features

    prev_close = safe_float(close.iloc[-1])
    features["prev_close"] = prev_close

    if len(close) >= 6:
        features["ret5_pct"] = ((prev_close / safe_float(close.iloc[-6])) - 1) * 100
    if len(close) >= 21:
        features["ret20_pct"] = ((prev_close / safe_float(close.iloc[-21])) - 1) * 100

    returns = close.pct_change().dropna()
    if len(returns) >= 10:
        features["vol20_pct"] = returns.tail(20).std() * np.sqrt(252) * 100

    if {"High", "Low", "Close"}.issubset(set(prior.columns)) and len(prior) >= 21:
        high = prior["High"]
        low = prior["Low"]
        close_prev = prior["Close"].shift(1)
        tr = pd.concat(
            [high - low, (high - close_prev).abs(), (low - close_prev).abs()],
            axis=1,
        ).max(axis=1)
        atr20 = safe_float(tr.tail(20).mean())
        if not pd.isna(atr20) and prev_close > 0:
            features["atr20_pct"] = atr20 / prev_close * 100

    if "Volume" in prior.columns and len(prior["Volume"].dropna()) >= 21:
        v = prior["Volume"].dropna()
        latest_v = safe_float(v.iloc[-1])
        avg_v = safe_float(v.iloc[-21:-1].mean())
        if avg_v > 0:
            features["volume_surge"] = latest_v / avg_v

    return features


def build_scalping_prediction(
    ticker: str,
    selected_date: datetime.date,
    case_label: str,
    daily_features: dict,
    intraday_df: pd.DataFrame,
    freq_min: int = 5,
) -> dict:
    code = case_code(case_label)
    sessions = split_us_sessions(intraday_df)
    pre = sessions["premarket"]
    reg = sessions["regular"]
    aft = sessions["afterhours"]
    all_session = sessions["all"]

    grid = make_regular_time_grid(selected_date, freq_min=freq_min)

    prev_close = safe_float(daily_features.get("prev_close", np.nan))
    ret5_pct = np.nan_to_num(daily_features.get("ret5_pct", np.nan), nan=0.0)
    ret20_pct = np.nan_to_num(daily_features.get("ret20_pct", np.nan), nan=0.0)
    atr20_pct = np.nan_to_num(daily_features.get("atr20_pct", np.nan), nan=3.0)
    vol20_pct = np.nan_to_num(daily_features.get("vol20_pct", np.nan), nan=45.0)

    if pd.isna(prev_close) or prev_close <= 0:
        if not all_session.empty and "Close" in all_session.columns:
            prev_close = safe_float(all_session["Close"].dropna().iloc[0])
        else:
            return {"prediction_df": pd.DataFrame(), "extended_df": pd.DataFrame(), "summary": {}, "case_code": code}

    pre_last = np.nan
    pre_high = np.nan
    pre_low = np.nan
    pre_change_pct = 0.0
    pre_range_pct = 0.0

    if pre is not None and not pre.empty and "Close" in pre.columns:
        pre_close = pre["Close"].dropna()
        if not pre_close.empty:
            pre_last = safe_float(pre_close.iloc[-1])
            pre_high = safe_float(pre["High"].dropna().max()) if "High" in pre.columns and not pre["High"].dropna().empty else safe_float(pre_close.max())
            pre_low = safe_float(pre["Low"].dropna().min()) if "Low" in pre.columns and not pre["Low"].dropna().empty else safe_float(pre_close.min())
            if prev_close > 0:
                pre_change_pct = (pre_last / prev_close - 1) * 100
            if prev_close > 0 and not pd.isna(pre_high) and not pd.isna(pre_low):
                pre_range_pct = (pre_high - pre_low) / prev_close * 100

    reg_last = np.nan
    reg_open = np.nan
    if reg is not None and not reg.empty and "Close" in reg.columns:
        reg_close = reg["Close"].dropna()
        if not reg_close.empty:
            reg_last = safe_float(reg_close.iloc[-1])
        if "Open" in reg.columns and not reg["Open"].dropna().empty:
            reg_open = safe_float(reg["Open"].dropna().iloc[0])
        elif not reg_close.empty:
            reg_open = safe_float(reg_close.iloc[0])

    if code == "case3" and not pd.isna(reg_last) and reg_last > 0:
        anchor_price = reg_last
    elif not pd.isna(pre_last) and pre_last > 0:
        anchor_price = pre_last
    elif not pd.isna(reg_open) and reg_open > 0:
        anchor_price = reg_open
    else:
        anchor_price = prev_close

    gap_pct = ((anchor_price / prev_close) - 1) * 100 if prev_close > 0 else 0.0
    trend_pct = ret5_pct * 0.15 + ret20_pct * 0.05

    # 갭이 큰 경우 평균회귀 가능성을 반영
    if gap_pct > 4:
        reversion_pct = -gap_pct * 0.22
    elif gap_pct < -4:
        reversion_pct = -gap_pct * 0.18
    else:
        reversion_pct = -gap_pct * 0.08

    drift_total_pct = float(np.clip(gap_pct * 0.28 + trend_pct + reversion_pct, -6.0, 6.0))

    base_range_pct = max(
        atr20_pct * 0.55,
        (vol20_pct / np.sqrt(252)) * 0.95,
        abs(gap_pct) * 0.55,
        pre_range_pct * 0.90,
        1.0,
    )
    base_range_pct = float(np.clip(base_range_pct, 0.7, 10.0))

    rows = []
    n = len(grid)

    for i, ts in enumerate(grid):
        t = i / max(n - 1, 1)
        u_shape = 0.75 + 0.25 * abs(2 * t - 1)
        opening_shock = (gap_pct / 100) * np.exp(-3.2 * t) * 0.25
        center = anchor_price * (1 + (drift_total_pct / 100) * t + opening_shock)

        if code == "case3" and reg is not None and not reg.empty and "Close" in reg.columns and ts <= reg.index[-1]:
            actual_near = nearest_series_value(reg["Close"].dropna(), ts)
            if not pd.isna(actual_near):
                center = actual_near

        band_pct = (base_range_pct / 100) * u_shape
        buy_line = center * (1 - band_pct)
        sell_line = center * (1 + band_pct)

        actual_regular = np.nan
        if reg is not None and not reg.empty and "Close" in reg.columns:
            actual_regular = nearest_series_value(reg["Close"].dropna(), ts)

        rows.append({
            "시각": ts,
            "KST 시각": convert_time_to_kst_label(ts),
            "예측 중심선": center,
            "최저 매수 후보선": buy_line,
            "최고 매도 후보선": sell_line,
            "정규장 실제값": actual_regular,
        })

    pred_df = pd.DataFrame(rows)

    ext_rows = []
    for session_df, label in [(pre, "프리마켓"), (aft, "애프터마켓")]:
        if session_df is not None and not session_df.empty and "Close" in session_df.columns:
            for ts, row in session_df.iterrows():
                ext_rows.append({
                    "시각": ts,
                    "KST 시각": convert_time_to_kst_label(ts),
                    "확장시간 실제값": safe_float(row.get("Close", np.nan)),
                    "구분": label,
                })
    extended_df = pd.DataFrame(ext_rows)

    summary = {
        "ticker": ticker,
        "selected_date": selected_date.strftime("%Y-%m-%d"),
        "case_label": case_label,
        "prev_close": prev_close,
        "anchor_price": anchor_price,
        "gap_pct": gap_pct,
        "pre_last": pre_last,
        "pre_change_pct": pre_change_pct,
        "atr20_pct": atr20_pct,
        "base_range_pct": base_range_pct,
        "drift_total_pct": drift_total_pct,
        "pred_buy_price": np.nan,
        "pred_buy_time": "-",
        "pred_sell_price": np.nan,
        "pred_sell_time": "-",
        "actual_low": np.nan,
        "actual_low_time": "-",
        "actual_high": np.nan,
        "actual_high_time": "-",
        "low_error_pct": np.nan,
        "high_error_pct": np.nan,
    }

    if not pred_df.empty:
        buy_idx = pred_df["최저 매수 후보선"].idxmin()
        sell_idx = pred_df["최고 매도 후보선"].idxmax()
        summary["pred_buy_price"] = safe_float(pred_df.loc[buy_idx, "최저 매수 후보선"])
        summary["pred_buy_time"] = pred_df.loc[buy_idx, "KST 시각"]
        summary["pred_sell_price"] = safe_float(pred_df.loc[sell_idx, "최고 매도 후보선"])
        summary["pred_sell_time"] = pred_df.loc[sell_idx, "KST 시각"]

    if reg is not None and not reg.empty and "Close" in reg.columns:
        if "Low" in reg.columns and not reg["Low"].dropna().empty:
            low_idx = reg["Low"].idxmin()
            actual_low = safe_float(reg.loc[low_idx, "Low"])
        else:
            low_idx = reg["Close"].idxmin()
            actual_low = safe_float(reg.loc[low_idx, "Close"])

        if "High" in reg.columns and not reg["High"].dropna().empty:
            high_idx = reg["High"].idxmax()
            actual_high = safe_float(reg.loc[high_idx, "High"])
        else:
            high_idx = reg["Close"].idxmax()
            actual_high = safe_float(reg.loc[high_idx, "Close"])

        summary["actual_low"] = actual_low
        summary["actual_low_time"] = convert_time_to_kst_label(low_idx)
        summary["actual_high"] = actual_high
        summary["actual_high_time"] = convert_time_to_kst_label(high_idx)

        if not pd.isna(summary["pred_buy_price"]) and actual_low > 0:
            summary["low_error_pct"] = (summary["pred_buy_price"] / actual_low - 1) * 100
        if not pd.isna(summary["pred_sell_price"]) and actual_high > 0:
            summary["high_error_pct"] = (summary["pred_sell_price"] / actual_high - 1) * 100

    trading_plan = build_scalping_trade_plan(summary, code)

    return {
        "prediction_df": pred_df,
        "extended_df": extended_df,
        "summary": summary,
        "trading_plan": trading_plan,
        "case_code": code,
    }


def build_scalping_trade_plan(summary: dict, code: str) -> dict:
    buy_price = safe_float(summary.get("pred_buy_price", np.nan))
    sell_price = safe_float(summary.get("pred_sell_price", np.nan))
    anchor = safe_float(summary.get("anchor_price", np.nan))
    gap_pct = safe_float(summary.get("gap_pct", np.nan))
    range_pct = safe_float(summary.get("base_range_pct", np.nan))

    if pd.isna(anchor) or anchor <= 0 or pd.isna(buy_price) or pd.isna(sell_price):
        return {
            "signal": "분석 불가",
            "reason": "기준 가격 또는 예측 밴드가 부족합니다.",
            "entry_zone": "-",
            "stop_loss": "-",
            "take_profit_1": "-",
            "take_profit_2": "-",
            "rules": [],
        }

    # 진입 구간은 매수 후보선보다 약간 위에 잡아 체결 가능성 반영
    entry_low = buy_price
    entry_high = buy_price * 1.004

    stop_loss = buy_price * (1 - max(min(range_pct, 6), 1.2) / 100 * 0.35)
    take_profit_1 = anchor
    take_profit_2 = sell_price

    if gap_pct > 5:
        signal = "갭 급등 주의: 눌림 확인 후 진입"
        css = "signal-wait"
        reason = "프리마켓/기준가 갭이 커서 개장 직후 되돌림 가능성이 큽니다."
    elif gap_pct < -5:
        signal = "급락 반등 후보: 소액 분할만"
        css = "signal-risk"
        reason = "하방 갭이 커서 반등 가능성은 있지만 변동성 리스크가 큽니다."
    elif code == "case3":
        signal = "실제 가격이 매수 후보선 접근 시만 진입"
        css = "signal-buy"
        reason = "정규장 실제 흐름과 예측 밴드를 함께 확인하는 구간입니다."
    else:
        signal = "대기 후 지정가 접근"
        css = "signal-wait"
        reason = "장 시작 전에는 예측 밴드가 기준이므로 추격매수보다 지정가 접근이 유리합니다."

    rules = [
        "개장 직후 5~15분은 체결강도와 거래량을 확인하고 무리한 시장가 진입을 피합니다.",
        "현재가가 최고 매도 후보선 근처라면 신규 진입보다 관망합니다.",
        "매수 후보선 접근 + 거래량 증가 + 직전 저점 이탈 실패가 동시에 보이면 분할 진입합니다.",
        "손절선 이탈 시 재진입 판단 없이 우선 청산합니다.",
        "1차 목표에서 절반 이상 익절하고, 나머지는 최고 매도 후보선 또는 추세 이탈까지 보유합니다.",
    ]

    return {
        "signal": signal,
        "css": css,
        "reason": reason,
        "entry_zone": f"{price_text(entry_low)} ~ {price_text(entry_high)}",
        "stop_loss": price_text(stop_loss),
        "take_profit_1": price_text(take_profit_1),
        "take_profit_2": price_text(take_profit_2),
        "rules": rules,
    }


def calculate_single_metrics(daily_df: pd.DataFrame, profile: dict, selected_date: datetime.date) -> dict:
    metrics = {
        "current_price": np.nan,
        "ret_5d": np.nan,
        "ret_20d": np.nan,
        "ret_60d": np.nan,
        "vol_20d": np.nan,
        "target_mean": np.nan,
        "target_high": np.nan,
        "target_low": np.nan,
        "target_upside": np.nan,
        "quant_score": 50.0,
        "action": "관망",
    }

    if daily_df is None or daily_df.empty or "Close" not in daily_df.columns:
        return metrics

    df = daily_df.copy()
    try:
        df.index = pd.to_datetime(df.index)
        df = df[df.index.date <= selected_date].copy()
    except Exception:
        pass

    close = df["Close"].dropna()
    if close.empty:
        return metrics

    current_price = safe_float(close.iloc[-1])
    profile_price = safe_float(profile.get("currentPrice", np.nan), default=np.nan)
    regular_price = safe_float(profile.get("regularMarketPrice", np.nan), default=np.nan)

    if pd.isna(current_price) or current_price <= 0:
        if not pd.isna(profile_price) and profile_price > 0:
            current_price = profile_price
        elif not pd.isna(regular_price) and regular_price > 0:
            current_price = regular_price

    prev_5 = safe_float(close.iloc[-6]) if len(close) >= 6 else np.nan
    prev_20 = safe_float(close.iloc[-21]) if len(close) >= 21 else np.nan
    prev_60 = safe_float(close.iloc[-61]) if len(close) >= 61 else np.nan

    ret_5d = ((current_price / prev_5) - 1) * 100 if not pd.isna(prev_5) and prev_5 > 0 else np.nan
    ret_20d = ((current_price / prev_20) - 1) * 100 if not pd.isna(prev_20) and prev_20 > 0 else np.nan
    ret_60d = ((current_price / prev_60) - 1) * 100 if not pd.isna(prev_60) and prev_60 > 0 else np.nan

    daily_ret = close.pct_change().dropna()
    vol_20d = daily_ret.tail(20).std() * np.sqrt(252) * 100 if len(daily_ret) >= 5 else np.nan

    target_mean = safe_float(profile.get("targetMeanPrice", np.nan))
    target_high = safe_float(profile.get("targetHighPrice", np.nan))
    target_low = safe_float(profile.get("targetLowPrice", np.nan))

    if pd.isna(target_mean) or target_mean <= 0:
        target_mean = np.nan
    if pd.isna(target_high) or target_high <= 0:
        target_high = np.nan
    if pd.isna(target_low) or target_low <= 0:
        target_low = np.nan

    target_upside = ((target_mean / current_price) - 1) * 100 if not pd.isna(target_mean) and current_price > 0 else np.nan

    score = 50.0
    if not pd.isna(target_upside):
        score += np.clip(target_upside, -30, 40) * 0.45
    if not pd.isna(ret_20d):
        score += np.clip(ret_20d, -25, 25) * 0.65
    if not pd.isna(ret_5d):
        score += np.clip(ret_5d, -15, 15) * 0.25
    if not pd.isna(vol_20d):
        score -= max(vol_20d - 45, 0) * 0.12

    score = float(np.clip(score, 0, 100))
    if score >= 75:
        action = "강한 분할 매수 우위"
    elif score >= 60:
        action = "눌림목 매수 우위"
    elif score >= 45:
        action = "중립/관망"
    else:
        action = "리스크 우위"

    metrics.update({
        "current_price": current_price,
        "ret_5d": ret_5d,
        "ret_20d": ret_20d,
        "ret_60d": ret_60d,
        "vol_20d": vol_20d,
        "target_mean": target_mean,
        "target_high": target_high,
        "target_low": target_low,
        "target_upside": target_upside,
        "quant_score": score,
        "action": action,
    })
    return metrics


def compute_news_statistical_impact(daily_df: pd.DataFrame, news_df: pd.DataFrame) -> dict:
    """
    현재 뉴스가 주가에 영향을 줄 가능성을 통계적으로 판단하기 위한 대체 모델.
    무료 yfinance는 과거 뉴스 전문 DB가 없으므로, 과거의 가격/거래량 이벤트일을 프록시로 사용한다.
    """
    result = {
        "impact_probability": np.nan,
        "avg_next_1d": np.nan,
        "avg_next_5d": np.nan,
        "sample_count": 0,
        "dominant_tag": "-",
        "interpretation": "데이터 부족",
    }

    if daily_df is None or daily_df.empty or "Close" not in daily_df.columns:
        return result

    df = daily_df.copy()
    if len(df) < 80:
        return result

    close = df["Close"].astype(float)
    ret = close.pct_change()
    volume_ratio = pd.Series(np.nan, index=df.index)
    if "Volume" in df.columns:
        vol = df["Volume"].astype(float)
        volume_ratio = vol / vol.rolling(20).mean()

    shock = pd.DataFrame({
        "ret": ret,
        "abs_ret": ret.abs(),
        "volume_ratio": volume_ratio,
        "next_1d": close.shift(-1) / close - 1,
        "next_5d": close.shift(-5) / close - 1,
    }).dropna()

    if shock.empty:
        return result

    threshold = shock["abs_ret"].quantile(0.75)
    candidates = shock[
        (shock["abs_ret"] >= threshold)
        | (shock["volume_ratio"] >= 1.5)
    ].copy()

    if candidates.empty:
        return result

    if news_df is not None and not news_df.empty:
        tags = []
        for val in news_df["호재 태그"].dropna().astype(str).tolist():
            if val != "-":
                tags.extend([x.strip() for x in val.split(",") if x.strip()])
        if tags:
            result["dominant_tag"] = pd.Series(tags).value_counts().index[0]

    avg_1d = candidates["next_1d"].mean() * 100
    avg_5d = candidates["next_5d"].mean() * 100
    prob_pos = (candidates["next_5d"] > 0).mean() * 100

    result["impact_probability"] = prob_pos
    result["avg_next_1d"] = avg_1d
    result["avg_next_5d"] = avg_5d
    result["sample_count"] = int(len(candidates))

    if prob_pos >= 62 and avg_5d > 0:
        result["interpretation"] = "최근 뉴스/이벤트가 주가에 긍정적으로 반영될 통계적 가능성이 비교적 높음"
    elif prob_pos >= 50:
        result["interpretation"] = "방향성은 중립 이상이나 변동성 확인 필요"
    else:
        result["interpretation"] = "과거 유사 충격 이후 후속 수익률이 약해 보수적 접근 필요"

    return result


def build_one_year_projection(daily_df: pd.DataFrame, metrics: dict, events_df: pd.DataFrame) -> pd.DataFrame:
    current_price = safe_float(metrics.get("current_price", np.nan))
    if pd.isna(current_price) or current_price <= 0:
        return pd.DataFrame()

    ret_60 = np.nan_to_num(metrics.get("ret_60d", np.nan), nan=0.0) / 100
    ret_20 = np.nan_to_num(metrics.get("ret_20d", np.nan), nan=0.0) / 100
    vol_20 = np.nan_to_num(metrics.get("vol_20d", np.nan), nan=40.0) / 100
    target_upside = np.nan_to_num(metrics.get("target_upside", np.nan), nan=0.0) / 100

    weeks = pd.date_range(
        start=datetime.datetime.combine(TODAY_NY, datetime.time(0, 0)),
        periods=53,
        freq="W",
    )

    t = np.linspace(0, 1, len(weeks))

    trend = np.clip(ret_60 * 0.35 + ret_20 * 0.65, -0.30, 0.45)
    target_component = np.clip(target_upside, -0.35, 0.65) * 0.45
    expected_return = float(np.clip(trend + target_component, -0.45, 0.85))

    # 이벤트 주간에는 변동폭 확대
    event_boost = np.zeros(len(weeks))
    if events_df is not None and not events_df.empty and "예정일" in events_df.columns:
        for _, row in events_df.iterrows():
            dt = pd.to_datetime(row.get("예정일"), errors="coerce")
            if pd.isna(dt):
                continue
            if dt.date() < TODAY_NY:
                continue
            idx = int(np.argmin(np.abs((weeks.date - dt.date()).astype("timedelta64[D]").astype(int))))
            if 0 <= idx < len(event_boost):
                event_boost[idx] += 0.04
                if idx + 1 < len(event_boost):
                    event_boost[idx + 1] += 0.025

    base = current_price * (1 + expected_return * t)
    uncertainty = vol_20 * np.sqrt(np.maximum(t, 0.02)) * 0.55 + event_boost

    bull = base * (1 + uncertainty + max(target_component, 0) * t)
    bear = base * (1 - uncertainty - max(-trend, 0) * 0.25 * t)

    df = pd.DataFrame({
        "날짜": [d.strftime("%Y-%m-%d") for d in weeks],
        "기본 예상": base,
        "상단 예상": bull,
        "하단 예상": bear,
        "이벤트 변동 확대": event_boost,
    })

    return df


def summarize_projection_returns(projection_df: pd.DataFrame, current_price: float) -> dict:
    if projection_df is None or projection_df.empty or pd.isna(current_price) or current_price <= 0:
        return {"base": np.nan, "bull": np.nan, "bear": np.nan, "base_price": np.nan, "bull_price": np.nan, "bear_price": np.nan}

    last = projection_df.iloc[-1]
    base_price = safe_float(last.get("기본 예상", np.nan))
    bull_price = safe_float(last.get("상단 예상", np.nan))
    bear_price = safe_float(last.get("하단 예상", np.nan))

    return {
        "base": (base_price / current_price - 1) * 100 if not pd.isna(base_price) else np.nan,
        "bull": (bull_price / current_price - 1) * 100 if not pd.isna(bull_price) else np.nan,
        "bear": (bear_price / current_price - 1) * 100 if not pd.isna(bear_price) else np.nan,
        "base_price": base_price,
        "bull_price": bull_price,
        "bear_price": bear_price,
    }


def make_ai_opinion(metrics: dict, news_impact: dict, events_df: pd.DataFrame) -> dict:
    quant = safe_float(metrics.get("quant_score", 50), default=50)
    impact_prob = safe_float(news_impact.get("impact_probability", np.nan), default=np.nan)
    avg_5d = safe_float(news_impact.get("avg_next_5d", np.nan), default=np.nan)
    vol = safe_float(metrics.get("vol_20d", np.nan), default=np.nan)
    target_upside = safe_float(metrics.get("target_upside", np.nan), default=np.nan)

    score = quant

    if not pd.isna(impact_prob):
        score += (impact_prob - 50) * 0.25
    if not pd.isna(avg_5d):
        score += np.clip(avg_5d, -5, 8) * 1.2
    if not pd.isna(target_upside):
        score += np.clip(target_upside, -20, 35) * 0.15
    if events_df is not None and not events_df.empty:
        score += min(len(events_df), 5) * 1.2
    if not pd.isna(vol) and vol > 70:
        score -= (vol - 70) * 0.08

    score = float(np.clip(score, 0, 100))

    if score >= 78:
        opinion = "공격적 분할 매수 우위"
        css = "signal-buy"
    elif score >= 63:
        opinion = "긍정적 관찰 / 눌림목 매수"
        css = "signal-buy"
    elif score >= 48:
        opinion = "중립 / 이벤트 확인 후 대응"
        css = "signal-wait"
    else:
        opinion = "리스크 우위 / 보수적 관망"
        css = "signal-risk"

    reasons = [
        f"퀀트 점수: {quant:.1f}/100",
        f"뉴스/이벤트 후속 상승 확률: {percent_text(impact_prob)}",
        f"과거 유사 충격 후 5거래일 평균: {percent_text(avg_5d)}",
        f"목표가 대비 상승여력: {percent_text(target_upside)}",
        f"예정 이벤트 수: {0 if events_df is None else len(events_df)}개",
    ]

    return {
        "score": score,
        "opinion": opinion,
        "css": css,
        "reasons": reasons,
    }


# =========================================================
# 앱 상단
# =========================================================
st.title("US Equity Signal Intelligence")

hero(
    "호재 후보, 단타 대응, 장기투자 판단을 한 화면에서 연결합니다",
    "앱 실행 시 자동 조사는 하지 않습니다. 1번 탭에서 시장 후보를 찾고, 2번 탭에서 단타 매수·매도 구간을 확인하며, 3번 탭에서 AI 종합 투자 의견과 1년 예상 경로를 봅니다."
)

top_col1, top_col2, top_col3 = st.columns([2, 2, 6])

with top_col1:
    focus_value = st.text_input(
        "공통 포커스 티커",
        value=st.session_state.get("global_ticker", ""),
        placeholder="예: NVDA",
        key=f"focus_input_{st.session_state['focus_nonce']}",
    )

with top_col2:
    if st.button("공통 티커 적용", use_container_width=True, type="primary"):
        st.session_state["global_ticker"] = normalize_ticker(focus_value)
        st.session_state["focus_nonce"] += 1
        st.rerun()

with top_col3:
    if st.session_state.get("global_ticker"):
        st.info(f"현재 공통 포커스 티커: **{st.session_state['global_ticker']}**")
    else:
        st.info("공통 포커스 티커가 없습니다. 직접 입력하거나 1번 탭 후보 종목을 선택하세요.")


tab1, tab2, tab3 = st.tabs([
    "1. 호재 후보 스캔",
    "2. 단타 매수·매도 전략",
    "3. AI 종합 투자 분석",
])


# =========================================================
# 1번 탭
# =========================================================
with tab1:
    st.subheader("시장 전체에서 호재 반응 후보 찾기")

    card(
        "후보군 오류 방지",
        "S&P500/Nasdaq100 동적 후보군을 가져오지 못하면 앱이 멈추지 않고 대체 시장 후보군으로 조사를 계속합니다. lxml 또는 인터넷 문제가 있어도 결과를 볼 수 있습니다.",
        badge="개선"
    )

    cfg1, cfg2, cfg3, cfg4 = st.columns([2, 2, 2, 2])

    with cfg1:
        source_mode = st.selectbox(
            "후보군 소스",
            ["S&P500 + Nasdaq100", "S&P500", "Nasdaq100", "직접 입력"],
            index=0,
            key="scan_source_mode",
        )

    with cfg2:
        max_symbols = st.slider(
            "최대 조사 종목 수",
            min_value=50,
            max_value=600,
            value=250,
            step=50,
            key="scan_max_symbols",
        )

    with cfg3:
        scan_period = st.selectbox(
            "가격 반응 기간",
            ["2mo", "3mo", "6mo"],
            index=1,
            key="scan_period",
        )

    with cfg4:
        news_scan_count = st.slider(
            "뉴스 영향 판단 종목 수",
            min_value=0,
            max_value=80,
            value=30,
            step=5,
            key="scan_news_count",
        )

    direct_tickers = ""
    if source_mode == "직접 입력":
        direct_tickers = st.text_area(
            "직접 조사할 티커 입력",
            placeholder="예: NVDA, TSLA, PLTR, AMD",
            height=90,
            key="scan_direct_tickers",
        )

    price_filter_col1, price_filter_col2, price_filter_col3 = st.columns([2, 2, 4])
    with price_filter_col1:
        min_price_filter = st.number_input(
            "최소 주가($)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="scan_min_price",
            help="예: 10달러 이상만 보고 싶으면 10 입력",
        )
    with price_filter_col2:
        max_price_filter = st.number_input(
            "최대 주가($)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="scan_max_price",
            help="0이면 상한 없음. 예: 50달러 이하만 보고 싶으면 50 입력",
        )
    with price_filter_col3:
        st.caption("주가 필터는 결과표 표시 단계에서 적용됩니다. 저가주·고가주를 나눠서 보기 좋습니다.")

    run_col1, run_col2, run_col3 = st.columns([2, 2, 6])

    with run_col1:
        run_market_scan = st.button("후보 스캔 실행", use_container_width=True, type="primary")

    with run_col2:
        if st.button("스캔 결과 지우기", use_container_width=True):
            st.session_state["market_scan_df"] = pd.DataFrame()
            st.session_state["market_scan_done"] = False
            st.rerun()

    with run_col3:
        st.caption("버튼을 누르기 전까지는 후보군 조회, 가격 다운로드, 뉴스 판단을 실행하지 않습니다.")

    if run_market_scan:
        st.session_state["scanner_refresh_token"] += 1

        with st.spinner("후보군을 준비하는 중입니다..."):
            universe, source_note = build_dynamic_universe(
                source_mode=source_mode,
                direct_tickers=direct_tickers,
                max_symbols=max_symbols,
            )

        if not universe:
            st.error("후보군이 비어 있습니다. 직접 입력 모드라면 티커를 입력해 주세요.")
        else:
            if "대체" in source_note:
                st.warning(source_note)
            else:
                st.success(source_note)

            st.info(f"조사 대상 {len(universe)}개를 확보했습니다.")

            with st.spinner("가격·거래량 반응을 계산하는 중입니다..."):
                market_data = fetch_bulk_market_data(
                    tuple(universe),
                    period=scan_period,
                    refresh_token=st.session_state["scanner_refresh_token"],
                )
                base_candidates = calculate_price_event_candidates(market_data)

            if base_candidates.empty:
                st.error("가격 데이터를 불러오지 못했거나 유효한 후보가 없습니다.")
            else:
                if news_scan_count > 0:
                    result_df = enrich_candidates_with_news(
                        base_candidates,
                        news_scan_count=news_scan_count,
                        refresh_token=st.session_state["scanner_refresh_token"],
                    )
                else:
                    result_df = base_candidates.copy()
                    result_df["최근 뉴스 제목"] = "-"
                    result_df["호재 태그"] = "-"
                    result_df["뉴스 영향 점수"] = 0
                    result_df["호재 임팩트 점수"] = result_df["가격/거래량 점수"]

                st.session_state["market_scan_df"] = result_df
                st.session_state["market_scan_done"] = True

    scan_df = st.session_state.get("market_scan_df", pd.DataFrame())

    if scan_df is None or scan_df.empty:
        st.info("아직 스캔을 실행하지 않았습니다.")
    else:
        st.write("---")
        st.subheader("호재 발표 영향 후보 랭킹")

        top_n = st.slider(
            "표시할 후보 수",
            min_value=10,
            max_value=min(100, len(scan_df)),
            value=min(30, len(scan_df)),
            step=5,
            key="scan_show_top_n",
        )

        filtered_scan_df = scan_df.copy()
        if min_price_filter > 0 and "현재가" in filtered_scan_df.columns:
            filtered_scan_df = filtered_scan_df[filtered_scan_df["현재가"] >= min_price_filter]
        if max_price_filter > 0 and "현재가" in filtered_scan_df.columns:
            filtered_scan_df = filtered_scan_df[filtered_scan_df["현재가"] <= max_price_filter]

        if filtered_scan_df.empty:
            st.warning("현재 가격 필터에 맞는 후보가 없습니다. 최소/최대 주가 조건을 완화해 보세요.")
            display_df = pd.DataFrame()
        else:
            st.caption(f"가격 필터 적용 후 {len(filtered_scan_df)}개 후보가 남았습니다.")
            display_df = filtered_scan_df.head(top_n).copy()

        format_cols = {
            "현재가": price_text,
            "1일 수익률(%)": lambda x: percent_text(x, 2),
            "5일 수익률(%)": lambda x: percent_text(x, 2),
            "20일 수익률(%)": lambda x: percent_text(x, 2),
            "거래량 배율": lambda x: number_text(x, 2),
            "시가 갭(%)": lambda x: percent_text(x, 2),
            "20일 변동성(%)": lambda x: percent_text(x, 2),
            "가격/거래량 점수": lambda x: number_text(x, 2),
            "호재 임팩트 점수": lambda x: number_text(x, 2),
        }

        for col, func in format_cols.items():
            if col in display_df.columns:
                display_df[col] = display_df[col].map(func)

        preferred_cols = [
            "티커", "호재 포착일", "중요도", "초보자 해석", "왜 중요한가",
            "시장 반응", "호재 임팩트 점수", "현재가",
            "1일 수익률(%)", "5일 수익률(%)", "거래량 배율", "시가 갭(%)",
            "호재 태그", "최근 뉴스 제목", "뉴스 링크", "종목 링크",
        ]
        existing_cols = [c for c in preferred_cols if c in display_df.columns]

        st.dataframe(
            display_df[existing_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "뉴스 링크": st.column_config.LinkColumn("뉴스", display_text="Yahoo News"),
                "종목 링크": st.column_config.LinkColumn("종목", display_text="Yahoo Quote"),
            },
        )

        st.write("---")
        st.subheader("후보 종목을 공통 포커스 티커로 지정")

        button_cols = st.columns(5)
        button_source_df = filtered_scan_df if "filtered_scan_df" in locals() and not filtered_scan_df.empty else scan_df
        for idx, row in button_source_df.head(15).iterrows():
            ticker = row["티커"]
            with button_cols[idx % 5]:
                if st.button(f"{ticker} 선택", key=f"select_{ticker}", use_container_width=True):
                    st.session_state["global_ticker"] = normalize_ticker(ticker)
                    st.session_state["focus_nonce"] += 1
                    st.rerun()


# =========================================================
# 2번 탭: 단타 전략
# =========================================================
with tab2:
    st.subheader("단타 매수·매도 전략")

    card(
        "그래프보다 행동 지침 중심",
        "예측 중심선만 보여주지 않고, 매수 대기 구간·진입 금지 조건·손절선·1차/2차 매도 목표를 함께 표시합니다. 시간은 한국시간 기준입니다.",
        badge="단타"
    )

    with st.expander("초보자용: 이 탭은 이렇게 보면 됩니다", expanded=True):
        st.write("1. **매수 대기 구간**은 싸게 잡아볼 수 있는 후보 가격입니다. 현재가가 그 근처에 올 때까지 기다리는 구간입니다.")
        st.write("2. **손절선**은 틀렸다고 인정하고 나와야 하는 가격입니다. 초보자는 손절선을 반드시 먼저 정해야 합니다.")
        st.write("3. **1차 목표**는 절반 정도 수익 실현을 고려하는 가격, **2차 목표**는 욕심을 줄이고 나머지를 정리할 후보 가격입니다.")
        st.write("4. 가격이 이미 최고 매도 후보선 근처라면 신규 매수보다 관망이 안전합니다.")

    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])

    with c1:
        scalp_ticker = st.text_input(
            "분석 티커",
            value=st.session_state.get("global_ticker", ""),
            placeholder="예: NVDA",
            key=f"scalp_ticker_{st.session_state['focus_nonce']}",
        )
        scalp_ticker = normalize_ticker(scalp_ticker)

    with c2:
        selected_date = st.date_input(
            "미국 거래일",
            value=TODAY_NY,
            key="scalp_selected_date",
            help="그래프 시간 표시는 한국시간입니다.",
        )

    auto_case = infer_case(selected_date)

    with c3:
        case_mode = st.selectbox(
            "분석 케이스",
            ["자동 판단", "Case1. 과거: 예측치 vs 실제값", "Case2. 장 시작 전: 예측치 vs 프리마켓/확장시간", "Case3. 정규장 중: 예측치 vs 정규장 실제 변화"],
            index=0,
            key="scalp_case_mode",
        )

    active_case = auto_case if case_mode == "자동 판단" else case_mode

    with c4:
        freq_min = st.selectbox(
            "예측 간격",
            [1, 2, 5, 10, 15],
            index=2,
            key="scalp_freq_min",
        )

    run_scalp = st.button("전략 계산", use_container_width=True, type="primary")

    st.caption(f"현재 NY 날짜: {TODAY_NY} / 자동 판단 케이스: {auto_case}")

    if run_scalp:
        if not scalp_ticker:
            st.error("분석할 티커를 입력하거나 1번 탭에서 후보를 선택해 주세요.")
        else:
            st.session_state["global_ticker"] = scalp_ticker
            st.session_state["scalp_refresh_token"] += 1

            with st.spinner(f"{scalp_ticker} 단타 데이터를 불러오는 중입니다..."):
                daily_df = fetch_daily_history_until(
                    scalp_ticker,
                    selected_date=selected_date,
                    lookback_days=240,
                    refresh_token=st.session_state["scalp_refresh_token"],
                )
                intraday_df, used_interval = fetch_intraday_for_date(
                    scalp_ticker,
                    selected_date=selected_date,
                    refresh_token=st.session_state["scalp_refresh_token"],
                )
                features = calculate_daily_features(daily_df, selected_date)
                result = build_scalping_prediction(
                    ticker=scalp_ticker,
                    selected_date=selected_date,
                    case_label=active_case,
                    daily_features=features,
                    intraday_df=intraday_df,
                    freq_min=int(freq_min),
                )

            result["ticker"] = scalp_ticker
            result["selected_date"] = selected_date
            result["case_label"] = active_case
            result["daily_df"] = daily_df
            result["intraday_df"] = intraday_df
            result["used_interval"] = used_interval
            result["features"] = features

            st.session_state["scalp_result"] = result
            st.session_state["scalp_result_done"] = True

    if not st.session_state.get("scalp_result_done"):
        st.info("공통 티커를 적용하거나 이 탭에서 티커를 입력한 뒤 '단타 전략 계산'을 누르세요.")
    else:
        result = st.session_state["scalp_result"]
        pred_df = result.get("prediction_df", pd.DataFrame())
        ext_df = result.get("extended_df", pd.DataFrame())
        summary = result.get("summary", {})
        plan = result.get("trading_plan", {})
        used_interval = result.get("used_interval", "")
        case_label = result.get("case_label", "")
        ticker = result.get("ticker", "")
        intraday_df = result.get("intraday_df", pd.DataFrame())

        st.write("---")
        st.subheader(f"{ticker} / {summary.get('selected_date', '')} / {case_label}")

        if pred_df.empty:
            st.error("예측선을 계산할 수 없습니다. 전일 종가 또는 일봉 데이터가 부족합니다.")
        else:
            actual_available = not (intraday_df is None or intraday_df.empty)
            if not actual_available:
                st.warning("선택 날짜의 분봉/확장시간 실제값은 아직 없습니다. 예측선과 단타 행동 지침만 먼저 표시합니다.")
            else:
                st.success("실제 분봉/확장시간 데이터를 불러왔습니다. 예측선과 실제 흐름을 함께 비교합니다.")

            card(
                plan.get("signal", "전략 없음"),
                plan.get("reason", "-"),
                badge="AI 단타 판단",
                css_class=plan.get("css", "signal-wait"),
            )

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("매수 대기 구간", plan.get("entry_zone", "-"))
            p2.metric("손절선", plan.get("stop_loss", "-"))
            p3.metric("1차 목표", plan.get("take_profit_1", "-"))
            p4.metric("2차 목표", plan.get("take_profit_2", "-"))

            beginner_action_df = pd.DataFrame({
                "상황": ["현재가가 매수 대기 구간보다 높다", "현재가가 매수 대기 구간에 들어왔다", "매수 후 손절선을 깼다", "1차 목표에 도달했다", "2차 목표에 도달했다"],
                "초보자 행동": ["추격하지 말고 기다림", "거래량 증가와 반등 확인 후 소액 분할", "미련 없이 손절", "절반 이상 익절", "남은 물량 정리 또는 추세선 이탈 시 정리"],
                "이유": ["비싸게 사면 손절 폭이 커짐", "하락 중 칼날 잡기 방지", "큰 손실 방지", "수익을 확정해야 심리가 안정됨", "단타는 욕심보다 확률 관리가 중요"],
            })
            st.dataframe(beginner_action_df, use_container_width=True, hide_index=True)

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("전일 종가", price_text(summary.get("prev_close", np.nan)))
            k2.metric("기준 가격", price_text(summary.get("anchor_price", np.nan)))
            k3.metric("갭/기준 변화", percent_text(summary.get("gap_pct", np.nan)))
            k4.metric("예상 장중 폭", percent_text(summary.get("base_range_pct", np.nan)))
            k5.metric("사용 분봉", used_interval if used_interval else "-")

            k6, k7, k8, k9 = st.columns(4)
            k6.metric("최저 매수 후보", f"{price_text(summary.get('pred_buy_price', np.nan))} / {summary.get('pred_buy_time', '-')}")
            k7.metric("최고 매도 후보", f"{price_text(summary.get('pred_sell_price', np.nan))} / {summary.get('pred_sell_time', '-')}")
            k8.metric("실제 저점", f"{price_text(summary.get('actual_low', np.nan))} / {summary.get('actual_low_time', '-')}")
            k9.metric("실제 고점", f"{price_text(summary.get('actual_high', np.nan))} / {summary.get('actual_high_time', '-')}")

            if plan.get("rules"):
                with st.expander("단타 실행 규칙 보기", expanded=True):
                    for idx, rule in enumerate(plan["rules"], start=1):
                        st.write(f"{idx}. {rule}")

            fig = go.Figure()

            if ext_df is not None and not ext_df.empty:
                fig.add_trace(go.Scatter(
                    x=ext_df["시각"],
                    y=ext_df["확장시간 실제값"],
                    name="프리/애프터 실제값",
                    mode="lines",
                    line=dict(dash="dot"),
                    customdata=ext_df[["KST 시각"]],
                    hovertemplate="KST %{customdata[0]}<br>가격 %{y:.2f}<extra></extra>",
                ))

            if "정규장 실제값" in pred_df.columns and pred_df["정규장 실제값"].notna().any():
                fig.add_trace(go.Scatter(
                    x=pred_df["시각"],
                    y=pred_df["정규장 실제값"],
                    name="정규장 실제값",
                    mode="lines+markers",
                    customdata=pred_df[["KST 시각"]],
                    hovertemplate="KST %{customdata[0]}<br>가격 %{y:.2f}<extra></extra>",
                ))

            for col, name, dash in [
                ("예측 중심선", "예측 중심선", None),
                ("최저 매수 후보선", "최저 매수 후보선", "dash"),
                ("최고 매도 후보선", "최고 매도 후보선", "dash"),
            ]:
                fig.add_trace(go.Scatter(
                    x=pred_df["시각"],
                    y=pred_df[col],
                    name=name,
                    mode="lines",
                    line=dict(dash=dash) if dash else None,
                    customdata=pred_df[["KST 시각"]],
                    hovertemplate="KST %{customdata[0]}<br>가격 %{y:.2f}<extra></extra>",
                ))

            fig.update_layout(
                height=620,
                xaxis_title="한국시간(KST)",
                yaxis_title="가격",
                hovermode="x unified",
                legend=dict(orientation="h"),
                template="plotly_white",
                margin=dict(l=20, r=20, t=30, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.write("---")
            st.subheader("예측/실제 비교 테이블")

            table_df = pred_df.copy()
            for col in ["예측 중심선", "최저 매수 후보선", "최고 매도 후보선", "정규장 실제값"]:
                if col in table_df.columns:
                    table_df[col] = table_df[col].map(price_text)

            st.dataframe(
                table_df[["KST 시각", "예측 중심선", "최저 매수 후보선", "최고 매도 후보선", "정규장 실제값"]],
                use_container_width=True,
                hide_index=True,
            )


# =========================================================
# 3번 탭: AI 종합 투자 분석
# =========================================================
with tab3:
    st.subheader("AI 종합 투자 분석")

    card(
        "장기투자 리포트",
        "1년 예상 수익률을 기본·상단·하단 퍼센트로 보여주고, 최근 뉴스 요약·발표 일정·장기 매수 전략을 함께 정리합니다.",
        badge="장기"
    )

    a1, a2, a3 = st.columns([2, 2, 4])

    with a1:
        ai_ticker = st.text_input(
            "AI 분석 티커",
            value=st.session_state.get("global_ticker", ""),
            placeholder="예: NVDA",
            key=f"ai_ticker_{st.session_state['focus_nonce']}",
        )
        ai_ticker = normalize_ticker(ai_ticker)

    with a2:
        run_ai = st.button("종합 분석 실행", use_container_width=True, type="primary")

    with a3:
        st.caption("발표 일정은 yfinance calendar/earnings/news 기반입니다. 제품 발표·컨퍼런스 일정은 뉴스 제목에서 키워드로 추정합니다.")

    if run_ai:
        if not ai_ticker:
            st.error("분석할 티커를 입력하거나 1번 탭에서 후보를 선택해 주세요.")
        else:
            st.session_state["global_ticker"] = ai_ticker
            st.session_state["ai_refresh_token"] += 1

            with st.spinner(f"{ai_ticker} AI 종합 분석 데이터를 불러오는 중입니다..."):
                daily_df = fetch_daily_history_until(
                    ai_ticker,
                    selected_date=TODAY_NY,
                    lookback_days=500,
                    refresh_token=st.session_state["ai_refresh_token"],
                )
                profile = fetch_single_profile(
                    ai_ticker,
                    refresh_token=st.session_state["ai_refresh_token"],
                )
                news_df = fetch_ticker_news(
                    ai_ticker,
                    refresh_token=st.session_state["ai_refresh_token"],
                )
                events_df = fetch_event_calendar(
                    ai_ticker,
                    refresh_token=st.session_state["ai_refresh_token"],
                )
                metrics = calculate_single_metrics(daily_df, profile, TODAY_NY)
                news_impact = compute_news_statistical_impact(daily_df, news_df)
                opinion = make_ai_opinion(metrics, news_impact, events_df)
                projection_df = build_one_year_projection(daily_df, metrics, events_df)
                news_summary = summarize_recent_news(news_df, news_impact)
                long_strategy_df = make_long_term_strategy(metrics, opinion, projection_df, events_df)

            st.session_state["ai_result"] = {
                "ticker": ai_ticker,
                "daily_df": daily_df,
                "profile": profile,
                "news_df": news_df,
                "events_df": events_df,
                "metrics": metrics,
                "news_impact": news_impact,
                "opinion": opinion,
                "projection_df": projection_df,
                "news_summary": news_summary,
                "long_strategy_df": long_strategy_df,
            }
            st.session_state["ai_result_done"] = True

    if not st.session_state.get("ai_result_done"):
        st.info("티커를 입력한 뒤 AI 종합 분석을 실행하세요.")
    else:
        result = st.session_state["ai_result"]
        ticker = result.get("ticker", "")
        daily_df = result.get("daily_df", pd.DataFrame())
        profile = result.get("profile", {})
        news_df = result.get("news_df", pd.DataFrame())
        events_df = result.get("events_df", pd.DataFrame())
        metrics = result.get("metrics", {})
        news_impact = result.get("news_impact", {})
        opinion = result.get("opinion", {})
        projection_df = result.get("projection_df", pd.DataFrame())
        news_summary = result.get("news_summary", {})
        long_strategy_df = result.get("long_strategy_df", pd.DataFrame())

        company_name = profile.get("shortName", ticker)
        sector = profile.get("sector", "-")
        industry = profile.get("industry", "-")

        st.markdown(f"### {company_name}")
        st.caption(f"티커: {ticker} / 섹터: {sector} / 산업: {industry}")

        card(
            opinion.get("opinion", "판단 없음"),
            " / ".join(opinion.get("reasons", [])),
            badge=f"AI 점수 {opinion.get('score', 0):.1f}/100",
            css_class=opinion.get("css", "signal-wait"),
        )

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("현재가", price_text(metrics.get("current_price", np.nan)))
        m2.metric("20거래일 수익률", percent_text(metrics.get("ret_20d", np.nan)))
        m3.metric("20일 변동성", percent_text(metrics.get("vol_20d", np.nan)))
        m4.metric("목표가 상승여력", percent_text(metrics.get("target_upside", np.nan)))
        m5.metric("뉴스 영향 확률", percent_text(news_impact.get("impact_probability", np.nan)))

        st.write("---")
        st.subheader("1년 주가 변동 예상 시나리오")

        if projection_df is None or projection_df.empty:
            st.warning("1년 예상 시나리오를 계산할 수 없습니다.")
        else:
            projection_returns = summarize_projection_returns(projection_df, metrics.get("current_price", np.nan))
            r1, r2, r3 = st.columns(3)
            r1.metric("기본 예상 1년 수익률", percent_text(projection_returns.get("base", np.nan)), price_text(projection_returns.get("base_price", np.nan)))
            r2.metric("상단 예상 1년 수익률", percent_text(projection_returns.get("bull", np.nan)), price_text(projection_returns.get("bull_price", np.nan)))
            r3.metric("하단 예상 1년 수익률", percent_text(projection_returns.get("bear", np.nan)), price_text(projection_returns.get("bear_price", np.nan)))

            fig_proj = go.Figure()
            fig_proj.add_trace(go.Scatter(
                x=projection_df["날짜"],
                y=projection_df["기본 예상"],
                name="기본 예상",
                mode="lines",
            ))
            fig_proj.add_trace(go.Scatter(
                x=projection_df["날짜"],
                y=projection_df["상단 예상"],
                name="상단 예상",
                mode="lines",
            ))
            fig_proj.add_trace(go.Scatter(
                x=projection_df["날짜"],
                y=projection_df["하단 예상"],
                name="하단 예상",
                mode="lines",
            ))

            # 이벤트 주간 마커
            event_weeks = projection_df[projection_df["이벤트 변동 확대"] > 0]
            if not event_weeks.empty:
                fig_proj.add_trace(go.Scatter(
                    x=event_weeks["날짜"],
                    y=event_weeks["상단 예상"],
                    name="이벤트 변동 확대 예상 구간",
                    mode="markers",
                    marker=dict(size=10, symbol="star"),
                ))

            fig_proj.update_layout(
                height=560,
                xaxis_title="날짜",
                yaxis_title="예상 가격",
                hovermode="x unified",
                legend=dict(orientation="h"),
                template="plotly_white",
                margin=dict(l=20, r=20, t=30, b=20),
            )
            st.plotly_chart(fig_proj, use_container_width=True)

            st.info("별표는 실적 발표·컨퍼런스·발표 관련 뉴스 등으로 인해 변동폭 확대가 예상되는 구간입니다.")

        st.write("---")
        st.subheader("장기 투자 전략")
        if long_strategy_df is not None and not long_strategy_df.empty:
            st.dataframe(long_strategy_df, use_container_width=True, hide_index=True)
        else:
            st.info("장기 전략을 계산할 데이터가 부족합니다.")

        st.write("---")
        st.subheader("최근 뉴스 요약")
        if news_summary:
            summary_df = pd.DataFrame({"항목": list(news_summary.keys()), "요약": list(news_summary.values())})
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        else:
            st.info("최근 뉴스 요약을 만들 수 없습니다.")

        st.write("---")
        st.subheader("발표 예정 / 이벤트 일정")

        if events_df is None or events_df.empty:
            st.info("무료 데이터에서 확인 가능한 발표 예정 일정이 없습니다. 이 경우 실적 발표일, IR 페이지, 기업 보도자료를 별도로 확인하는 것이 좋습니다.")
        else:
            clean_events_df = events_df.copy().replace({None: "-", "None": "-", "nan": "-", "NaN": "-"})
            st.dataframe(clean_events_df, use_container_width=True, hide_index=True)

        st.write("---")
        st.subheader("뉴스가 주가에 영향을 줄 가능성")
        st.caption("뉴스 제목 자체가 아니라, 이 티커가 과거에 큰 가격·거래량 충격을 보였던 날 이후 1~5거래일 성과를 기준으로 판단합니다.")

        impact_table = pd.DataFrame({
            "항목": [
                "대표 뉴스/이벤트 태그",
                "과거 유사 충격 표본 수",
                "후속 1거래일 평균",
                "후속 5거래일 평균",
                "후속 5거래일 상승 확률",
                "AI 해석",
            ],
            "값": [
                news_impact.get("dominant_tag", "-"),
                f"{news_impact.get('sample_count', 0)}개",
                percent_text(news_impact.get("avg_next_1d", np.nan)),
                percent_text(news_impact.get("avg_next_5d", np.nan)),
                percent_text(news_impact.get("impact_probability", np.nan)),
                news_impact.get("interpretation", "-"),
            ],
        })
        st.dataframe(impact_table, use_container_width=True, hide_index=True)

        if news_df is None or news_df.empty:
            st.info("최근 뉴스를 불러오지 못했습니다.")
        else:
            st.write("최근 뉴스")
            st.dataframe(
                news_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "링크": st.column_config.LinkColumn("원문", display_text="열기"),
                },
            )

        st.markdown(f"[Yahoo Finance에서 {ticker} 확인]({build_yahoo_quote_link(ticker)})")


# =========================================================
# 하단 안내
# =========================================================
st.write("---")
st.caption(
    "주의: 본 대시보드는 투자 판단 보조용입니다. yfinance 무료 데이터는 지연·누락될 수 있으며, "
    "정밀 단타에는 실시간 호가, 체결강도, 주문장, 뉴스 속보 API, SEC/FDA/IR 일정 API 연동이 필요합니다."
)
