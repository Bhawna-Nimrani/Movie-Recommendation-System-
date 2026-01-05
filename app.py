import pickle
import streamlit as st
import pandas as pd
import requests
import os
from urllib.parse import quote
import time

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="CineMatch",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# DATA LOADERS
# =========================================================
@st.cache_data
def load_hollywood():
    movies_dict = pickle.load(open(os.path.join(BASE_DIR, "movie_dict.pkl"), "rb"))
    movies = pd.DataFrame(movies_dict)
    similarity = pickle.load(open(os.path.join(BASE_DIR, "similarity.pkl"), "rb"))
    return movies, similarity

@st.cache_data
def load_bollywood():
    try:
        movies_dict = pickle.load(open(os.path.join(BASE_DIR, "bollywood_movie_dict.pkl"), "rb"))
        movies = pd.DataFrame(movies_dict)
        similarity = pickle.load(open(os.path.join(BASE_DIR, "bollywood_similarity.pkl"), "rb"))
        return movies, similarity
    except Exception as e:
        return None, None

hollywood_movies, hollywood_similarity = load_hollywood()
bollywood_movies, bollywood_similarity = load_bollywood()

# =========================================================
# ENHANCED POSTER + RATING FETCH WITH RETRY LOGIC
# =========================================================
TMDB_KEY = "fcba1227ed076f69ec8af8de53de0512"
OMDB_KEY = "ba297405"

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_movie_details(movie_id, movie_title, release_year=None):
    """Enhanced fetch with better error handling and retry logic"""
    
    def safe_request(url, max_retries=2):
        """Helper function for safe API requests with retry"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                continue
            except requests.exceptions.RequestException:
                return None
        return None
    
    # STEP 1: TMDb search by title + year
    if release_year:
        search_url = (
            f"https://api.themoviedb.org/3/search/movie"
            f"?api_key={TMDB_KEY}&query={quote(movie_title)}"
            f"&year={release_year}&language=en-US"
        )
        data = safe_request(search_url)
        
        if data and data.get("results"):
            first = data["results"][0]
            poster_path = first.get("poster_path")
            rating = first.get("vote_average")
            if poster_path:
                return {
                    "poster": f"https://image.tmdb.org/t/p/w500{poster_path}",
                    "rating": round(rating, 1) if isinstance(rating, (float, int)) and rating > 0 else None,
                }
    
    # STEP 2: TMDb search without year
    search_url = (
        f"https://api.themoviedb.org/3/search/movie"
        f"?api_key={TMDB_KEY}&query={quote(movie_title)}&language=en-US"
    )
    data = safe_request(search_url)
    
    if data and data.get("results"):
        first = data["results"][0]
        poster_path = first.get("poster_path")
        rating = first.get("vote_average")
        if poster_path:
            return {
                "poster": f"https://image.tmdb.org/t/p/w500{poster_path}",
                "rating": round(rating, 1) if isinstance(rating, (float, int)) and rating > 0 else None,
            }
    
    # STEP 3: TMDb by ID
    tmdb_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_KEY}&language=en-US"
    data = safe_request(tmdb_url)
    
    if data:
        poster_path = data.get("poster_path")
        rating = data.get("vote_average")
        if poster_path:
            return {
                "poster": f"https://image.tmdb.org/t/p/w500{poster_path}",
                "rating": round(rating, 1) if isinstance(rating, (float, int)) and rating > 0 else None,
            }
    
    # STEP 4: OMDb by title
    year_param = f"&y={release_year}" if release_year else ""
    omdb_url = f"http://www.omdbapi.com/?t={quote(movie_title)}{year_param}&apikey={OMDB_KEY}"
    data = safe_request(omdb_url)
    
    if data and data.get("Response") == "True":
        poster = data.get("Poster")
        imdb_rating = data.get("imdbRating")
        
        poster_url = poster if poster and poster != "N/A" else None
        rating = None
        if imdb_rating and imdb_rating != "N/A":
            try:
                rating = float(imdb_rating)
            except ValueError:
                pass
        
        if poster_url:
            return {
                "poster": poster_url,
                "rating": rating,
            }
    
    # STEP 5: Fallback placeholder
    return {
        "poster": f"https://via.placeholder.com/300x450/1a1a2e/808080?text={quote(movie_title[:15])}",
        "rating": None,
    }

# =========================================================
# RECOMMENDATION LOGIC
# =========================================================
def recommend_hollywood(movie):
    try:
        index = hollywood_movies[hollywood_movies["title"] == movie].index[0]
        distances = sorted(
            list(enumerate(hollywood_similarity[index])),
            reverse=True,
            key=lambda x: x[1],
        )

        recommendations = []
        for i in distances[1:6]:
            movie_data = hollywood_movies.iloc[i[0]]
            details = fetch_movie_details(movie_data.movie_id, movie_data.title)

            recommendations.append({
                "title": movie_data.title,
                "poster": details["poster"],
                "rating": details["rating"],
                "year": None,
                "genres": [],
            })
        return recommendations
    except Exception as e:
        st.error(f"Error generating recommendations: {str(e)}")
        return []

def recommend_bollywood(movie, filter_genre=None, year_filter="off", language_filter="all"):
    if bollywood_movies is None or bollywood_similarity is None:
        return []
    if movie not in bollywood_movies["title"].values:
        return []

    try:
        index = bollywood_movies[bollywood_movies["title"] == movie].index[0]
        base_year = bollywood_movies.loc[index].get("release_year", None)
        base_genres = set(bollywood_movies.loc[index].get("genres", []))
        base_lang = bollywood_movies.loc[index].get("language", "hindi")

        scores = list(enumerate(bollywood_similarity[index]))
        boosted_scores = []

        for movie_idx, score in scores:
            if movie_idx == index:
                continue

            movie_row = bollywood_movies.iloc[movie_idx]
            movie_genres = set(movie_row.get("genres", []))
            movie_year = movie_row.get("release_year", None)
            movie_lang = movie_row.get("language", "hindi")

            if language_filter != "all" and movie_lang != language_filter:
                continue
            if filter_genre and filter_genre != "All" and filter_genre not in movie_genres:
                continue

            boost = 0.0

            if movie_genres and base_genres:
                common_genres = base_genres.intersection(movie_genres)
                if len(common_genres) > 0:
                    boost += 0.5 * len(common_genres)
                else:
                    boost -= 0.2

            if year_filter != "off" and base_year and movie_year:
                year_diff = abs(base_year - movie_year)
                if year_filter == "strict" and year_diff <= 2:
                    boost += 0.3
                elif year_filter == "same_era" and year_diff <= 5:
                    boost += 0.2
                elif year_filter == "same_decade":
                    if (base_year // 10) * 10 == (movie_year // 10) * 10:
                        boost += 0.3

            if base_lang == movie_lang:
                boost += 0.15

            boosted_scores.append((movie_idx, score + boost))

        boosted_scores = sorted(boosted_scores, key=lambda x: x[1], reverse=True)[:5]

        recommendations = []
        for movie_idx, score in boosted_scores:
            movie_row = bollywood_movies.iloc[movie_idx]
            movie_year = movie_row.get("release_year", None)
            details = fetch_movie_details(movie_row["movie_id"], movie_row["title"], movie_year)

            recommendations.append({
                "title": movie_row["title"],
                "poster": details["poster"],
                "rating": details["rating"],
                "year": movie_year,
                "genres": movie_row.get("genres", []),
            })

        return recommendations
    except Exception as e:
        st.error(f"Error generating recommendations: {str(e)}")
        return []

# =========================================================
# IMPROVED CSS
# =========================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: #141414; }
    .main .block-container {
        padding: 0.7rem 1.2rem;
        max-width: 1300px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .app-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #e50914;
        margin-bottom: 2px;
        letter-spacing: -0.5px;
    }
    .app-subtitle {
        color: #808080;
        font-size: 0.8rem;
        margin-bottom: 8px;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: transparent;
        border-bottom: 1px solid #333;
        padding: 0;
        margin-bottom: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #808080;
        border: none;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 0.9rem;
        border-bottom: 3px solid transparent;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #ffffff; }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        border-bottom: 3px solid #e50914 !important;
    }
    
    h3 {
        color: #ffffff;
        font-weight: 700;
        font-size: 1.05rem;
        margin: 6px 0;
    }
    
    .stSelectbox label {
        color: #ffffff !important;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .stSelectbox > div > div {
        background: #2a2a2a;
        border: 1px solid #404040;
        border-radius: 4px;
        color: white;
        padding: 4px 8px;
        font-size: 0.85rem;
        min-height: 34px;
    }
    
    .stButton > button {
        width: 100%;
        background: #e50914;
        color: white;
        font-weight: 700;
        border: none;
        padding: 6px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        transition: all 0.2s;
        min-height: 34px;
    }
    .stButton > button:hover { background: #f40612; }
    
    .stSuccess {
        background: rgba(229,9,20,0.1);
        border-left: 3px solid #e50914;
        border-radius: 4px;
        color: #ffffff;
        font-weight: 600;
        padding: 6px 9px;
        margin: 8px 0;
        font-size: 0.8rem;
    }
    .stWarning {
        background: rgba(255,193,7,0.1);
        border-left: 3px solid #ffc107;
        border-radius: 4px;
        padding: 6px 9px;
        font-size: 0.8rem;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .app-title { font-size: 1.3rem; text-align: center; }
        .app-subtitle { font-size: 0.7rem; text-align: center; }
        .main .block-container { padding: 0.5rem 0.6rem; }
        .stTabs [data-baseweb="tab"] { font-size: 0.7rem; padding: 5px 8px; }
        h3 { font-size: 0.85rem; }
        
        /* Better mobile card layout */
        [data-testid="column"] {
            min-width: 45% !important;
            max-width: 48% !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="unified-header">
        <div class="app-title">🎬 CineMatch</div>
        <div class="app-subtitle">AI-Powered Movie Recommendations</div>
    </div>
""", unsafe_allow_html=True)

# =========================================================
# CARD DISPLAY
# =========================================================
def display_recommendations(recommendations):
    if not recommendations:
        st.warning("⚠️ No recommendations found. Try different filters.")
        return

    st.success(f"Top {len(recommendations)} Recommendations")
    cols = st.columns(5, gap="small")

    for idx, col in enumerate(cols):
        if idx >= len(recommendations):
            break

        rec = recommendations[idx]
        with col:
            st.markdown(f"""
                <div style="
                    background:#181818;
                    border-radius:6px;
                    overflow:hidden;
                    cursor:pointer;
                    transition:transform 0.18s ease, box-shadow 0.18s ease;
                    box-shadow:0 4px 10px rgba(0,0,0,0.5);
                " onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 8px 20px rgba(0,0,0,0.65)';"
                  onmouseout="this.style.transform='none';this.style.boxShadow='0 4px 10px rgba(0,0,0,0.5)';">
                    <div style="position:relative;">
                        <img src="{rec['poster']}" style="
                            width:100%;
                            display:block;
                            aspect-ratio: 2/3;
                            object-fit:cover;
                        " onerror="this.src='https://via.placeholder.com/300x450/1a1a2e/808080?text=No+Image'" />
                        <div style="
                            position:absolute;
                            top:6px;
                            left:6px;
                            background:rgba(0,0,0,0.85);
                            color:#e50914;
                            padding:3px 7px;
                            border-radius:3px;
                            font-weight:700;
                            font-size:0.6rem;
                        ">#{idx+1}</div>
                    </div>
                    <div style="padding:6px 7px 7px 7px;">
                        <div style="
                            color:#fff;
                            font-weight:600;
                            font-size:0.78rem;
                            line-height:1.25;
                            margin-bottom:3px;
                            max-height:30px;
                            display:-webkit-box;
                            -webkit-line-clamp:2;
                            -webkit-box-orient:vertical;
                            overflow:hidden;
                        ">{rec['title']}</div>
            """, unsafe_allow_html=True)

            meta = []
            if rec.get("year"):
                meta.append(f"<span style='color:#46d369;'>{rec['year']}</span>")
            if rec.get("genres"):
                meta.append(f"<span style='color:#808080;'>{rec['genres'][0]}</span>")

            if meta:
                st.markdown(f"<div style='font-size:0.65rem;margin-bottom:3px;'>{' • '.join(meta)}</div>", unsafe_allow_html=True)

            rating = rec.get("rating")
            if rating:
                color = "#46d369" if rating >= 8 else "#f59e0b" if rating >= 7 else "#f97316" if rating >= 6 else "#808080"
                st.markdown(f"""
                    <div style="
                        background:rgba(255,255,255,0.03);
                        border:1px solid {color};
                        color:{color};
                        padding:3px 5px;
                        border-radius:3px;
                        font-size:0.68rem;
                        font-weight:700;
                        text-align:center;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        gap:4px;
                    ">
                        <span>⭐</span><span>{rating}/10</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="
                        background:rgba(255,255,255,0.03);
                        border:1px solid #404040;
                        color:#808080;
                        padding:3px 5px;
                        border-radius:3px;
                        font-size:0.68rem;
                        font-weight:600;
                        text-align:center;
                    ">Not Rated</div>
                """, unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("### 📊 Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Hollywood", f"{len(hollywood_movies):,}")
    with col2:
        if bollywood_movies is not None:
            st.metric("Bollywood", f"{len(bollywood_movies):,}")

# =========================================================
# TABS
# =========================================================
if bollywood_movies is not None:
    tabs = st.tabs(["🎬 Hollywood", "🌟 All Bollywood", "🇮🇳 Hindi", "🌴 Tamil", "⭐ Telugu"])
else:
    tabs = st.tabs(["🎬 Hollywood"])

all_genres = []
if bollywood_movies is not None:
    all_genres_set = set()
    for _, row in bollywood_movies.iterrows():
        if isinstance(row["genres"], list):
            all_genres_set.update(row["genres"])
    all_genres = sorted(list(all_genres_set))

# =========================================================
# HOLLYWOOD TAB
# =========================================================
with tabs[0]:
    st.markdown("### 🎬 Hollywood")
    c1, c2 = st.columns([3, 1])
    with c1:
        selected = st.selectbox("Select a movie", hollywood_movies["title"].values, key="hw")
    with c2:
        st.markdown("<div style='height:23px;'></div>", unsafe_allow_html=True)
        btn = st.button("Get Recommendations", key="hw_btn")

    if btn:
        with st.spinner("Finding movies..."):
            recs = recommend_hollywood(selected)
        display_recommendations(recs)

# =========================================================
# BOLLYWOOD TABS
# =========================================================
if bollywood_movies is not None and len(tabs) > 1:
    def create_tab(idx, df, lang, name):
        with tabs[idx]:
            st.markdown(f"### {name}")

            c1, c2 = st.columns([3, 1])
            with c1:
                sel = st.selectbox("Movie", df["title"].values, key=f"{lang}_sel")
            with c2:
                st.markdown("<div style='height:23px;'></div>", unsafe_allow_html=True)
                click = st.button("Recommend", key=f"b_{lang}")

            f1, f2, f3 = st.columns(3)
            with f1:
                genre = st.selectbox("Genre", ["All"] + all_genres, key=f"g_{lang}")
            with f2:
                year = st.selectbox(
                    "Year",
                    ["off", "same_era", "same_decade", "strict"],
                    format_func=lambda x: {"off": "Any", "same_era": "Similar", "same_decade": "Decade", "strict": "Exact"}[x],
                    key=f"y_{lang}",
                )
            with f3:
                if lang == "all":
                    l = st.selectbox("Lang", ["all", "hindi", "tamil", "telugu"], key=f"l_{lang}")
                else:
                    l = lang
                    st.markdown(f"<p style='color:#808080;font-size:0.75rem;margin-top:1.4rem;'>Lang: {lang.title()}</p>", unsafe_allow_html=True)

            if click:
                with st.spinner("Finding movies..."):
                    recs = recommend_bollywood(sel, genre if genre != "All" else None, year, l if lang == "all" else lang)
                display_recommendations(recs)

    create_tab(1, bollywood_movies, "all", "🌟 All Bollywood")
    create_tab(2, bollywood_movies[bollywood_movies["language"] == "hindi"], "hindi", "🇮🇳 Hindi")
    create_tab(3, bollywood_movies[bollywood_movies["language"] == "tamil"], "tamil", "🌴 Tamil")
    create_tab(4, bollywood_movies[bollywood_movies["language"] == "telugu"], "telugu", "⭐ Telugu")

# =========================================================
# FOOTER
# =========================================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
    <div style="text-align: center; padding: 8px; border-top: 1px solid #2a2a2a; color: #808080; font-size: 0.8rem;">
        Made with ❤️ • Powered by TMDb & OMDb
    </div>
""", unsafe_allow_html=True)