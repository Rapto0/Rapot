"""
Otonom Analiz - Streamlit Dashboard
Sinyaller, trade'ler ve bot istatistiklerini görselleştirir.

Kullanım:
    streamlit run dashboard.py
"""

import pandas as pd
import requests
import streamlit as st

# Sayfa yapılandırması
st.set_page_config(
    page_title="Otonom Analiz",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API URL
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Custom CSS
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .signal-buy {
        background-color: #28a745;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
    }
    .signal-sell {
        background-color: #dc3545;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Session State Başlatma
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None


def fetch_api(endpoint: str, params: dict = None, method: str = "GET", data: dict = None):
    """API'den veri çeker."""
    try:
        headers = {}
        if st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"

        if method == "GET":
            response = requests.get(
                f"{API_URL}{endpoint}", params=params, headers=headers, timeout=10
            )
        elif method == "POST":
            response = requests.post(
                f"{API_URL}{endpoint}",
                params=params,
                json=data,
                headers=headers,
                timeout=10,
            )

        # 401 Unauthorized ise çıkış yap
        if response.status_code == 401:
            st.session_state.token = None
            st.session_state.user = None
            st.error("Oturum süresi doldu, lütfen tekrar giriş yapın.")
            return None

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        # Hata mesajını sessiz geçiştirme, ancak login hatalarını gösterme
        if "401" not in str(e):
            st.error(f"API Hatası: {e}")
        return None


def fetch_from_db():
    """Doğrudan veritabanından veri çeker (API çalışmıyorsa)."""
    try:
        from db_session import get_session
        from models import Signal, Trade

        with get_session() as session:
            signals = session.query(Signal).order_by(Signal.created_at.desc()).limit(100).all()
            trades = session.query(Trade).order_by(Trade.created_at.desc()).limit(100).all()

            signals_data = [s.to_dict() for s in signals]
            trades_data = [t.to_dict() for t in trades]

            return signals_data, trades_data
    except Exception as e:
        st.error(f"Veritabanı Hatası: {e}")
        return [], []


def login_user(username, password):
    """Kullanıcı girişi yapar."""
    try:
        response = requests.post(
            f"{API_URL}/auth/token",
            json={"username": username, "password": password},
            timeout=5,
        )
        if response.ok:
            token_data = response.json()
            st.session_state.token = token_data["access_token"]

            # Kullanıcı bilgilerini al
            user_response = requests.get(
                f"{API_URL}/auth/me",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            if user_response.ok:
                st.session_state.user = user_response.json()
                st.success(f"Hoşgeldin {username}!")
                st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı")
    except Exception as e:
        st.error(f"Giriş hatası: {e}")


def logout_user():
    """Çıkış yapar."""
    st.session_state.token = None
    st.session_state.user = None
    st.rerun()


# ==================== SIDEBAR ====================

st.sidebar.title("🤖 Otonom Analiz")
st.sidebar.markdown("---")

# Login Durumu
if st.session_state.token:
    username = (
        st.session_state.user.get("username", "Kullanıcı") if st.session_state.user else "Kullanıcı"
    )
    is_admin = st.session_state.user.get("is_admin", False) if st.session_state.user else False
    role_icon = "👮‍♂️" if is_admin else "👤"

    st.sidebar.success(f"{role_icon} {username}")
    if st.sidebar.button("Çıkış Yap"):
        logout_user()
else:
    with st.sidebar.expander("🔑 Giriş Yap", expanded=True):
        username_input = st.text_input("Kullanıcı Adı")
        password_input = st.text_input("Şifre", type="password")
        if st.button("Giriş"):
            login_user(username_input, password_input)

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Sayfa",
    ["📊 Dashboard", "📈 Sinyaller", "💰 Trade'ler", "🔍 Analiz", "⚙️ Ayarlar"],
)

# Veri kaynağı seçimi
data_source = st.sidebar.radio("Veri Kaynağı", ["API", "Veritabanı"])

st.sidebar.markdown("---")
st.sidebar.info("🚀 Bot durumunu ve sinyalleri takip edin")


# ==================== DASHBOARD ====================

if page == "📊 Dashboard":
    st.markdown('<p class="main-header">📊 Dashboard</p>', unsafe_allow_html=True)

    # Metrikler
    col1, col2, col3, col4 = st.columns(4)

    if data_source == "API":
        stats = fetch_api("/stats")
        health = fetch_api("/health")
    else:
        signals_data, trades_data = fetch_from_db()
        stats = {
            "total_signals": len(signals_data),
            "total_trades": len(trades_data),
            "open_trades": len([t for t in trades_data if t.get("status") == "OPEN"]),
            "total_pnl": sum(t.get("pnl", 0) for t in trades_data),
            "win_rate": 0,
        }
        health = {"status": "healthy", "uptime_seconds": 0, "database": "connected"}

    if stats and health:
        with col1:
            st.metric(
                "Durum",
                "✅ Aktif" if health.get("status") == "healthy" else "❌ Hata",
            )

        with col2:
            st.metric("Toplam Sinyal", stats.get("total_signals", 0))

        with col3:
            st.metric("Açık Trade", stats.get("open_trades", 0))

        with col4:
            pnl = stats.get("total_pnl", 0)
            st.metric(
                "Toplam PnL",
                f"₺{pnl:,.2f}" if pnl else "₺0.00",
                delta=f"{pnl:+,.2f}" if pnl else None,
            )

    st.markdown("---")

    # Son sinyaller
    st.subheader("📈 Son Sinyaller")

    if data_source == "API":
        signals = fetch_api("/signals", {"limit": 10})
    else:
        signals_data, _ = fetch_from_db()
        signals = signals_data[:10]

    if signals:
        df = pd.DataFrame(signals)
        if not df.empty:
            # Renklendirme
            def color_signal(val):
                if val == "AL":
                    return "background-color: #28a745; color: white"
                elif val == "SAT":
                    return "background-color: #dc3545; color: white"
                return ""

            display_cols = ["symbol", "strategy", "signal_type", "timeframe", "price", "created_at"]
            available_cols = [c for c in display_cols if c in df.columns]

            styled_df = df[available_cols].style.applymap(
                color_signal, subset=["signal_type"] if "signal_type" in available_cols else []
            )
            st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("Henüz sinyal yok")


# ==================== SİNYALLER ====================

elif page == "📈 Sinyaller":
    st.markdown('<p class="main-header">📈 Sinyaller</p>', unsafe_allow_html=True)

    # Filtreler
    col1, col2, col3 = st.columns(3)

    with col1:
        symbol_filter = st.text_input("Sembol", placeholder="Örn: THYAO")

    with col2:
        strategy_filter = st.selectbox("Strateji", ["Tümü", "COMBO", "HUNTER"])

    with col3:
        signal_type_filter = st.selectbox("Sinyal Türü", ["Tümü", "AL", "SAT"])

    # Sinyal listesi
    params = {"limit": 100}
    if symbol_filter:
        params["symbol"] = symbol_filter.upper()
    if strategy_filter != "Tümü":
        params["strategy"] = strategy_filter
    if signal_type_filter != "Tümü":
        params["signal_type"] = signal_type_filter

    if data_source == "API":
        signals = fetch_api("/signals", params)
    else:
        signals_data, _ = fetch_from_db()
        signals = signals_data

        # Manuel filtreleme
        if symbol_filter:
            signals = [s for s in signals if s.get("symbol") == symbol_filter.upper()]
        if strategy_filter != "Tümü":
            signals = [s for s in signals if s.get("strategy") == strategy_filter]
        if signal_type_filter != "Tümü":
            signals = [s for s in signals if s.get("signal_type") == signal_type_filter]

    if signals:
        df = pd.DataFrame(signals)
        st.dataframe(df, use_container_width=True)

        # İstatistikler
        st.markdown("---")
        st.subheader("📊 Sinyal İstatistikleri")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam", len(signals))
        with col2:
            buy_count = len([s for s in signals if s.get("signal_type") == "AL"])
            st.metric("AL Sinyali", buy_count)
        with col3:
            sell_count = len([s for s in signals if s.get("signal_type") == "SAT"])
            st.metric("SAT Sinyali", sell_count)
    else:
        st.info("Sinyal bulunamadı")


# ==================== TRADE'LER ====================

elif page == "💰 Trade'ler":
    st.markdown('<p class="main-header">💰 Trade\'ler</p>', unsafe_allow_html=True)

    # Filtreler
    col1, col2 = st.columns(2)

    with col1:
        trade_symbol = st.text_input("Sembol", placeholder="Örn: BTCUSDT")

    with col2:
        status_filter = st.selectbox("Durum", ["Tümü", "OPEN", "CLOSED"])

    # Trade listesi
    params = {"limit": 100}
    if trade_symbol:
        params["symbol"] = trade_symbol.upper()
    if status_filter != "Tümü":
        params["status"] = status_filter

    if data_source == "API":
        trades = fetch_api("/trades", params)
    else:
        _, trades_data = fetch_from_db()
        trades = trades_data

        # Manuel filtreleme
        if trade_symbol:
            trades = [t for t in trades if t.get("symbol") == trade_symbol.upper()]
        if status_filter != "Tümü":
            trades = [t for t in trades if t.get("status") == status_filter]

    if trades:
        df = pd.DataFrame(trades)

        # PnL renklendirme
        def color_pnl(val):
            try:
                if float(val) > 0:
                    return "color: green"
                elif float(val) < 0:
                    return "color: red"
            except (ValueError, TypeError):
                pass
            return ""

        if "pnl" in df.columns:
            styled_df = df.style.applymap(color_pnl, subset=["pnl"])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Trade bulunamadı")


# ==================== ANALİZ ====================

elif page == "🔍 Analiz":
    st.markdown('<p class="main-header">🔍 Manuel Analiz</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])

    with col1:
        symbol = st.text_input("Sembol girin", placeholder="THYAO, BTCUSDT, vb.")

    with col2:
        market_type = st.selectbox("Piyasa", ["BIST", "Kripto"])

    if st.button("🔍 Analiz Başlat", type="primary"):
        if symbol:
            with st.spinner(f"{symbol.upper()} analiz ediliyor..."):
                if data_source == "API":
                    try:
                        response = requests.post(
                            f"{API_URL}/analyze/{symbol.upper()}",
                            params={"market_type": market_type},
                            timeout=30,
                        )
                        if response.ok:
                            st.success(f"✅ {symbol.upper()} analizi başlatıldı!")
                        else:
                            st.error(f"❌ Hata: {response.text}")
                    except Exception as e:
                        st.error(f"❌ API hatası: {e}")
                else:
                    st.warning("Analiz için API gerekli. Lütfen API'yi başlatın.")
        else:
            st.warning("Lütfen bir sembol girin")

    st.markdown("---")

    # Sembol listeleri
    st.subheader("📋 Mevcut Semboller")

    tab1, tab2 = st.tabs(["🏢 BIST", "₿ Kripto"])

    with tab1:
        if data_source == "API":
            bist = fetch_api("/symbols/bist")
            if bist:
                st.write(f"Toplam: {bist.get('count', 0)} sembol")
                st.text_area("BIST Sembolleri", ", ".join(bist.get("symbols", [])[:50]) + "...")
        else:
            try:
                from data_loader import get_all_bist_symbols

                symbols = get_all_bist_symbols()
                st.write(f"Toplam: {len(symbols)} sembol")
                st.text_area("BIST Sembolleri", ", ".join(symbols[:50]) + "...")
            except Exception:
                st.info("Semboller yüklenemedi")

    with tab2:
        if data_source == "API":
            crypto = fetch_api("/symbols/crypto")
            if crypto:
                st.write(f"Toplam: {crypto.get('count', 0)} çift")
                symbols = crypto.get("symbols", [])[:50]
                st.text_area(
                    "Kripto Çiftleri",
                    ", ".join(symbols) + "..." if symbols else "Binance API key gerekli",
                )
        else:
            st.info("Kripto sembolleri için API gerekli")


# ==================== AYARLAR ====================

elif page == "⚙️ Ayarlar":
    st.markdown('<p class="main-header">⚙️ Ayarlar</p>', unsafe_allow_html=True)

    st.subheader("🔗 API Bağlantısı")
    new_api_url = st.text_input("API URL", value=API_URL)

    if st.button("Bağlantıyı Test Et"):
        try:
            response = requests.get(f"{new_api_url}/health", timeout=5)
            if response.ok:
                st.success("✅ API bağlantısı başarılı!")
                st.json(response.json())
            else:
                st.error(f"❌ API yanıt vermedi: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Bağlantı hatası: {e}")

    st.markdown("---")

    st.subheader("📊 Veritabanı Durumu")
    if st.button("Tablo İstatistiklerini Göster"):
        try:
            from db_session import get_table_stats

            stats = get_table_stats()
            for table, count in stats.items():
                st.write(f"**{table}**: {count} kayıt")
        except Exception as e:
            st.error(f"Hata: {e}")


# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666;">
        Otonom Analiz Dashboard v1.0.0 |
        <a href="http://localhost:8000/docs" target="_blank">API Docs</a>
    </div>
    """,
    unsafe_allow_html=True,
)
