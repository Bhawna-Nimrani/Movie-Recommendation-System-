
import pickle
import streamlit as st
import pandas as pd
import requests
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects

movies_dict = pickle.load(open(r'C:\Users\91897\Desktop\Movie R system\movie_dict.pkl', 'rb'))
movies= pd.DataFrame(movies_dict)
similarity = pickle.load(open(r'C:\Users\91897\Desktop\Movie R system\similarity.pkl','rb'))


def fetch_poster(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=fcba1227ed076f69ec8af8de53de0512&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error on bad status
        data = response.json()
        poster_path = data.get('poster_path', '')
        full_path = f"https://image.tmdb.org/t/p/w500/{poster_path}" if poster_path else ""
        return full_path
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(f"Error fetching poster: {e}")
        return ""
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return ""


def recommend(movie):
    index = movies[movies['title'] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    recommended_movie_names = []
    recommended_movie_posters = []
    for i in distances[1:6]:
        # fetch the movie poster
        movie_id = movies.iloc[i[0]].movie_id
        recommended_movie_posters.append(fetch_poster(movie_id))
        recommended_movie_names.append(movies.iloc[i[0]].title)

    return recommended_movie_names,recommended_movie_posters

st.header('Movie Recommender System')
selected_movie =st.selectbox(
    'Type or select a movie from the dropdown',
   movies['title'].values
)

if st.button('Show Recommendation'):
    recommended_movie_names, recommended_movie_posters = recommend(selected_movie)
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.text(recommended_movie_names[0])
        st.image(recommended_movie_posters[0])

    with col2:
        st.text(recommended_movie_names[1])
        st.image(recommended_movie_posters[1])

    with col3:
        st.text(recommended_movie_names[2])
        st.image(recommended_movie_posters[2])

    with col4:
        st.text(recommended_movie_names[3])
        st.image(recommended_movie_posters[3])

    with col5:
        st.text(recommended_movie_names[4])
        st.image(recommended_movie_posters[4])
