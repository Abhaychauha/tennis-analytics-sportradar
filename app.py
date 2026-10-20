"""Tennis Analytics Explorer – Streamlit front end for the PostgreSQL data.

Run:  streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()
st.set_page_config(page_title="Tennis Analytics Explorer",
                   page_icon="🎾", layout="wide")
PAGE_SIZE = 25


@st.cache_resource
def get_engine():
    """Create one shared SQLAlchemy engine."""
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", ""),
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        database=os.getenv("PG_DATABASE", "tennis_db"),
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=300)
def run_query(sql, params=None):
    """Run a SELECT and return a DataFrame (empty on error)."""
    try:
        with get_engine().connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except Exception as exc:  # show DB problems in the UI, don't crash
        st.error(f"Database error: {exc}")
        return pd.DataFrame()


def options(sql):
    df = run_query(sql)
    return ["All"] + df.iloc[:, 0].dropna().tolist() if not df.empty else ["All"]


def none_if_all(value):
    return None if value == "All" else value


# ------------------------------ pages ------------------------------
def page_home():
    st.header("Homepage Dashboard")
    stats = run_query("""
        SELECT COUNT(*) AS competitors,
               COUNT(DISTINCT country) AS countries,
               MAX(points) AS top_points
        FROM v_latest_rankings""")
    if stats.empty:
        st.info("No data yet – run sportradar_etl.py first.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Total competitors", int(stats.competitors[0]))
    c2.metric("Countries represented", int(stats.countries[0]))
    c3.metric("Highest points", int(stats.top_points[0] or 0))

    left, right = st.columns(2)
    with left:
        st.subheader("Competitions per category")
        df = run_query("""SELECT cat.category_name, COUNT(*) AS total
                          FROM competitions c JOIN categories cat
                          ON cat.category_id = c.category_id
                          GROUP BY 1 ORDER BY 2 DESC LIMIT 15""")
        st.bar_chart(df.set_index("category_name"))
    with right:
        st.subheader("Competition types")
        df = run_query("SELECT type, COUNT(*) AS total FROM competitions "
                       "GROUP BY 1 ORDER BY 2 DESC")
        st.bar_chart(df.set_index("type"))


def page_competitions():
    st.header("Competition Explorer")
    f1, f2, f3, f4, f5 = st.columns(5)
    ctype = f1.selectbox("Type", options("SELECT DISTINCT type FROM competitions ORDER BY 1"))
    gender = f2.selectbox("Gender", options("SELECT DISTINCT gender FROM competitions ORDER BY 1"))
    cat = f3.selectbox("Category", options("SELECT category_name FROM categories ORDER BY 1"))
    level = f4.selectbox("Level", options(
        "SELECT DISTINCT level FROM competitions WHERE level IS NOT NULL ORDER BY 1"))
    hier = f5.selectbox("Hierarchy", ["All", "Top-level (no parent)", "Sub-competitions"])

    where = """WHERE (CAST(:t AS TEXT) IS NULL OR c.type = :t)
               AND (CAST(:g AS TEXT) IS NULL OR c.gender = :g)
               AND (CAST(:cat AS TEXT) IS NULL OR cat.category_name = :cat)
               AND (CAST(:lvl AS TEXT) IS NULL OR c.level = :lvl)"""
    if hier.startswith("Top"):
        where += " AND (c.parent_id IS NULL OR c.parent_id = '')"
    elif hier.startswith("Sub"):
        where += " AND c.parent_id IS NOT NULL AND c.parent_id <> ''"
    params = {"t": none_if_all(ctype), "g": none_if_all(gender), "cat": none_if_all(cat),
              "lvl": none_if_all(level)}

    total = run_query(f"""SELECT COUNT(*) AS n FROM competitions c
                          LEFT JOIN categories cat ON cat.category_id = c.category_id
                          {where}""", params)
    n = int(total.n[0]) if not total.empty else 0
    pages = max(1, -(-n // PAGE_SIZE))
    page = st.number_input("Page", 1, pages, 1)
    st.caption(f"{n} competitions")
    df = run_query(f"""SELECT c.competition_id, c.competition_name, c.type,
                              c.gender, c.level, cat.category_name, c.parent_id
                       FROM competitions c
                       LEFT JOIN categories cat ON cat.category_id = c.category_id
                       {where} ORDER BY c.competition_name
                       LIMIT :lim OFFSET :off""",
                    {**params, "lim": PAGE_SIZE, "off": (page - 1) * PAGE_SIZE})
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("Parent → sub-competitions"):
        st.dataframe(run_query("""
            SELECT p.competition_name AS parent, ch.competition_name AS child
            FROM competitions ch JOIN competitions p
              ON p.competition_id = ch.parent_id
            ORDER BY 1, 2 LIMIT 500"""), use_container_width=True, hide_index=True)


def page_venues():
    st.header("Venues & Complexes")
    f1, f2 = st.columns(2)
    country = f1.selectbox("Country", options("SELECT DISTINCT country_name FROM venues ORDER BY 1"))
    complex_ = f2.selectbox("Complex", options("SELECT complex_name FROM complexes ORDER BY 1"))
    df = run_query("""
        SELECT v.venue_name, v.city_name, v.country_name, v.timezone, cx.complex_name
        FROM venues v JOIN complexes cx ON cx.complex_id = v.complex_id
        WHERE (CAST(:c AS TEXT) IS NULL OR v.country_name = :c)
          AND (CAST(:x AS TEXT) IS NULL OR cx.complex_name = :x)
        ORDER BY cx.complex_name, v.venue_name""",
                    {"c": none_if_all(country), "x": none_if_all(complex_)})
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.subheader("Venues per country")
    st.bar_chart(run_query("""SELECT country_name, COUNT(*) AS venues FROM venues
                              GROUP BY 1 ORDER BY 2 DESC LIMIT 20""").set_index("country_name"))


def page_search():
    st.header("Search & Filter Competitors")
    st.sidebar.subheader("Filters")
    gender = st.sidebar.selectbox("Gender", options(
        "SELECT DISTINCT gender FROM v_latest_rankings ORDER BY 1"))
    rank_lo, rank_hi = st.sidebar.slider("Rank range", 1, 500, (1, 100))
    min_points = st.sidebar.number_input("Minimum points", 0, 100000, 0, step=100)
    country = st.sidebar.selectbox("Country", options(
        "SELECT DISTINCT country FROM v_latest_rankings ORDER BY 1"))
    name = st.text_input("Search by name")

    params = {"g": none_if_all(gender), "lo": rank_lo, "hi": rank_hi,
              "pts": min_points, "c": none_if_all(country), "n": f"%{name}%"}
    df = run_query("""
        SELECT "rank", name, country, points, movement, competitions_played,
               gender, ranking_year, ranking_week
        FROM v_latest_rankings
        WHERE (CAST(:g AS TEXT) IS NULL OR gender = :g)
          AND "rank" BETWEEN :lo AND :hi AND points >= :pts
          AND (CAST(:c AS TEXT) IS NULL OR country = :c)
          AND name ILIKE :n
        ORDER BY "rank" LIMIT 500""", params)
    st.caption(f"{len(df)} results")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("Competitor details")
    if not df.empty:
        pick = st.selectbox("Select a competitor", df["name"].unique())
        row = df[df["name"] == pick].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rank", int(row["rank"]), int(-row.movement))  # up = positive
        c2.metric("Points", int(row.points))
        c3.metric("Competitions played", int(row.competitions_played))
        c4.metric("Country", row.country)
        hist = run_query("""
            SELECT ranking_year * 100 + ranking_week AS year_week, "rank"
            FROM competitor_rankings r JOIN competitors c USING (competitor_id)
            WHERE c.name = :n ORDER BY 1""", {"n": pick})
        if len(hist) > 1:
            st.line_chart(hist.set_index("year_week"))


def page_countries():
    st.header("Country-Wise Analysis")
    df = run_query("""
        SELECT country, COUNT(*) AS competitors,
               SUM(points) AS total_points,
               ROUND(AVG(points), 1) AS avg_points
        FROM v_latest_rankings GROUP BY country ORDER BY competitors DESC""")
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.bar_chart(df.head(15).set_index("country")["competitors"])


def page_leaderboards():
    st.header("Leaderboards")
    gender = st.selectbox("Gender", options(
        "SELECT DISTINCT gender FROM v_latest_rankings ORDER BY 1"))
    n = st.slider("Show top", 5, 50, 10)
    p = {"g": none_if_all(gender), "n": n}
    base = """SELECT "rank", name, country, points, movement
              FROM v_latest_rankings WHERE (CAST(:g AS TEXT) IS NULL OR gender = :g)"""
    a, b = st.columns(2)
    a.subheader("Top-ranked")
    a.dataframe(run_query(base + ' ORDER BY "rank" LIMIT :n', p),
                use_container_width=True, hide_index=True)
    b.subheader("Highest points")
    b.dataframe(run_query(base + " ORDER BY points DESC LIMIT :n", p),
                use_container_width=True, hide_index=True)


PAGES = {
    "🏠 Home": page_home,
    "🏆 Competitions": page_competitions,
    "🏟️ Venues & Complexes": page_venues,
    "🔎 Search Competitors": page_search,
    "🌍 Country Analysis": page_countries,
    "📊 Leaderboards": page_leaderboards,
}

st.title("🎾 Tennis Analytics Explorer")
choice = st.sidebar.radio("Navigate", list(PAGES))
PAGES[choice]()
