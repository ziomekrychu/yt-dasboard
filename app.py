import streamlit as st
import pandas as pd
from youtube_api import get_youtube_service
from cache_manager import update_cache_if_needed
from datetime import datetime
import json

st.set_page_config(page_title="YouTube HotScore Dashboard", layout="wide")
st.title("📈 YouTube HotScore Dashboard")

# 🔐 API KEY
api_key = None
try:
    api_key = st.secrets["youtube_api_key"]
except:
    api_key = st.text_input("🔑 Wklej YouTube API Key:")

if api_key:
    youtube = get_youtube_service(api_key)

    # 📂 Wczytanie kanałów
    try:
        with open("channels.txt", "r") as f:
            channel_ids = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        st.error("Nie znaleziono pliku channels.txt. Upewnij się, że istnieje w katalogu.")
        st.stop()

    # 🔄 Wczytaj dane z cache (lub aktualizuj jeśli potrzeba)
    video_dict = update_cache_if_needed(youtube, channel_ids)
    df = pd.DataFrame(video_dict.values())

    st.sidebar.write(f"🎬 Filmy w cache: {len(video_dict)}")

    if not df.empty:
        # Sidebar
        st.sidebar.header("🎛️ Filtry")

        sort_option = st.sidebar.selectbox("📊 Sortuj według:", ["hot_score", "views", "hours_since"])
        search_query = st.sidebar.text_input("🔎 Szukaj po tytule filmu:")
        min_views = st.sidebar.number_input("👀 Minimalna liczba wyświetleń", min_value=0, step=1000, value=0)
        hot_score_min, hot_score_max = st.sidebar.slider(
            "🔥 Zakres HotScore",
            min_value=int(df["hot_score"].min()),
            max_value=int(df["hot_score"].max()),
            value=(0, int(df["hot_score"].max()))
        )
        min_date = st.sidebar.date_input("📅 Minimalna data publikacji", value=datetime.today() - pd.Timedelta(days=21))
        max_date = st.sidebar.date_input("📅 Maksymalna data publikacji", value=datetime.today())

        # Filtrowanie
        df_sorted = df.sort_values(by=sort_option, ascending=(sort_option == "hours_since"))
        if search_query:
            df_sorted = df_sorted[df_sorted["title"].str.contains(search_query, case=False)]

        df_filtered = df_sorted[df_sorted["views"] >= min_views]
        df_filtered = df_filtered[(df_filtered["hot_score"] >= hot_score_min) & (df_filtered["hot_score"] <= hot_score_max)]
        df_filtered = df_filtered[df_filtered["published_at"].apply(
            lambda x: pd.to_datetime(min_date) <= pd.to_datetime(x) <= pd.to_datetime(max_date))]

        # 🔥 Wyświetlanie wyników + 💾 Zapis do pliku JSON
        with open("results.json", "w", encoding="utf-8") as f:
            json.dump(df_filtered.to_dict(orient="records"), f, ensure_ascii=False, indent=2, default=str)

        for _, row in df_filtered.iterrows():
            is_today = pd.to_datetime(row["published_at"]).date() == datetime.today().date()

            st.markdown(f"""
                <div style='background-color: black; padding: 12px; border-radius: 12px; margin-bottom: 16px; color: white;'>
                    <div style='display: flex; align-items: center; gap: 16px;'>
                        <img src='{row["thumbnail"]}' style='width: 120px; border-radius: 8px;'>
                        <div>
                            <p style='font-size: 18px; font-weight: bold; margin: 0 0 6px 0;'>
                                <a href='{row["video_url"]}' target='_blank' style='text-decoration: none; color: white;'>{row["title"]}</a>
                            </p>
                            <p style='margin: 4px 0;'>🕒 {row["published_at"]} | 👀 {row["views"]} wyświetleń</p>
                            <p style='margin: 4px 0;'>🔥 HotScore: <b>{row["hot_score"]}</b> | 📈 Wzrost: <b>{row.get("growth", 0)}%</b> | 📊 Śr. kanału: <b>{row.get("channel_avg", 0)}</b></p>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    else:
        st.info("Nie znaleziono żadnych filmów.")
else:
    st.warning("🔑 Wprowadź YouTube API Key, aby rozpocząć.")