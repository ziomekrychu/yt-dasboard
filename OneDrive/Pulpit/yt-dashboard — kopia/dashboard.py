import streamlit as st
import pandas as pd
from youtube_fetch import fetch_shorts
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# Automatyczne odświeżanie co 10 minut (600 000 ms)
st_autorefresh(interval=600000, key="refresh")

st.set_page_config(layout="wide")
st.title("📺 YouTube Shorts Dashboard")

with open("channels.txt") as f:
    channel_ids = [line.strip() for line in f if line.strip()]

@st.cache_data(ttl=600)
def load_data():
    all_videos = []
    for cid in channel_ids:
        try:
            videos = fetch_shorts(cid)
            all_videos.extend(videos)
        except Exception as e:
            st.warning(f"Błąd kanału {cid}: {e}")
    return pd.DataFrame(all_videos)

df = load_data()
df['date'] = df['published_at'].dt.date

# Sidebar
st.sidebar.header("🔍 Filtry")
date_filter = st.sidebar.selectbox("Czas publikacji", ["Wszystko", "Ostatnie 24h", "Ostatni tydzień"])
if date_filter == "Ostatnie 24h":
    df = df[df["published_at"] > datetime.utcnow() - timedelta(days=1)]
elif date_filter == "Ostatni tydzień":
    df = df[df["published_at"] > datetime.utcnow() - timedelta(days=7)]

keywords = st.sidebar.text_input("🎯 Słowa kluczowe (oddziel przecinkiem)")
if keywords:
    keyword_list = [k.strip().lower() for k in keywords.split(",")]
    df = df[df["title"].str.lower().apply(lambda x: any(k in x for k in keyword_list))]

min_views = st.sidebar.number_input("📈 Minimum wyświetleń", min_value=0, value=0)
df = df[df["views"] >= min_views]

sort_by = st.sidebar.selectbox("Sortuj według", ["Data", "Nazwa kanału", "Długość tytułu", "Hot Score"])
ascending = st.sidebar.checkbox("Rosnąco", value=False)
sort_col_map = {
    "Data": "published_at",
    "Nazwa kanału": "channel_title",
    "Długość tytułu": "title_length",
    "Hot Score": "hot_score",
}
df = df.sort_values(by=sort_col_map[sort_by], ascending=ascending)

# Statystyki
today = datetime.utcnow().date()
yesterday = today - timedelta(days=1)
this_week = today - timedelta(days=7)

col1, col2, col3 = st.columns(3)
col1.metric("📅 Dzisiaj", df[df['date'] == today].shape[0])
col2.metric("📆 Wczoraj", df[df['date'] == yesterday].shape[0])
col3.metric("🗓️ Ostatnie 7 dni", df[df['date'] >= this_week].shape[0])

trend = df.groupby("date").size().reset_index(name="liczba filmów")
st.line_chart(trend.set_index("date"))

avg_len = df["title_length"].mean()
st.write(f"✏️ Średnia długość tytułów: **{avg_len:.1f}** znaków")

st.subheader("📋 Wyniki")
for _, row in df.iterrows():
    with st.container():
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px;">
            <img src="{row['thumbnail']}" width="120">
            <div>
                <a href="{row['url']}" target="_blank"><b>{row['title']}</b></a><br>
                👤 {row['channel_title']}<br>
                📆 {row['published_at'].strftime('%Y-%m-%d %H:%M')} | 👁️ {row['views']} | 🔥 {row['hot_score']}
            </div>
        </div>
        <hr style="margin:10px 0;">
        """, unsafe_allow_html=True)
