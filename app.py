import pickle
import streamlit as st
import pandas as pd
import requests
from requests.exceptions import RequestException
import time
from urllib.parse import quote

# Load data
movies_dict = pickle.load(open(r'C:\Users\91897\Desktop\Movie R system\movie_dict.pkl', 'rb'))
movies = pd.DataFrame(movies_dict)
similarity = pickle.load(open(r'C:\Users\91897\Desktop\Movie R system\similarity.pkl', 'rb'))


def fetch_poster_from_tmdb(movie_id, retries=2):
    """Try to fetch poster from TMDb API with retry logic"""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=fcba1227ed076f69ec8af8de53de0512&language=en-US"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            poster_path = data.get('poster_path')
            
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
            else:
                return None
                
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.5)  # Quick retry
                continue
            else:
                print(f"TMDb error for movie_id {movie_id}: {e}")
                return None
    
    return None


def fetch_poster_from_omdb(movie_title):
    """Fallback: Try to fetch poster from OMDb API"""
    # Get your free key from: http://www.omdbapi.com/apikey.aspx
    url = f"http://www.omdbapi.com/?t={quote(movie_title)}&apikey=3e3e2d33"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('Response') == 'True' and data.get('Poster') != 'N/A':
            return data['Poster']
    except Exception as e:
        print(f"OMDb error for {movie_title}: {e}")
    
    return None


def fetch_poster(movie_id, movie_title):
    """Try TMDb first, then OMDb as fallback"""
    # Try TMDb first
    poster_url = fetch_poster_from_tmdb(movie_id)
    if poster_url:
        return poster_url
    
    # If TMDb fails, try OMDb with movie title
    print(f"TMDb failed for {movie_title}, trying OMDb...")
    poster_url = fetch_poster_from_omdb(movie_title)
    if poster_url:
        return poster_url
    
    # If both fail, return placeholder
    return "https://via.placeholder.com/500x750/2C3E50/ECF0F1?text=No+Poster"


def recommend(movie):
    """Get movie recommendations based on similarity"""
    index = movies[movies['title'] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    recommended_movie_names = []
    recommended_movie_posters = []
    
    for i in distances[1:6]:
        movie_id = movies.iloc[i[0]].movie_id
        movie_title = movies.iloc[i[0]].title
        
        poster_url = fetch_poster(movie_id, movie_title)
        
        recommended_movie_names.append(movie_title)
        recommended_movie_posters.append(poster_url)

    return recommended_movie_names, recommended_movie_posters


# Streamlit UI
st.header('Movie Recommender System')

selected_movie = st.selectbox(
    'Type or select a movie from the dropdown',
    movies['title'].values
)

if st.button('Show Recommendation'):
    recommended_movie_names, recommended_movie_posters = recommend(selected_movie)
    col1, col2, col3, col4, col5 = st.columns(5)

    columns = [col1, col2, col3, col4, col5]
    
    for idx, col in enumerate(columns):
        with col:
            st.text(recommended_movie_names[idx])
            st.image(recommended_movie_posters[idx])
