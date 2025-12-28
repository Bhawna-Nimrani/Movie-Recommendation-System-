# ============================================
# FAST BOLLYWOOD SYSTEM - 3000-5000 MOVIES IN 10-15 MINUTES
# ============================================
# Run: python fast_bollywood_pipeline.py
# ============================================

import requests
import pandas as pd
import pickle
import asyncio
import aiohttp
from aiohttp_retry import RetryClient, ExponentialRetry
from aiohttp import ClientTimeout
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

API_KEY = 'fcba1227ed076f69ec8af8de53de0512'
BASE_URL = 'https://api.themoviedb.org/3'

print("=" * 70)
print("🎬 FAST BOLLYWOOD SYSTEM - 3000-5000 MOVIES")
print("=" * 70)
print("⏱️  This will take 10-15 minutes total")
print("=" * 70)

# ============================================
# STEP 1: FETCH ALL MOVIES ASYNCHRONOUSLY
# ============================================

print("\n" + "=" * 70)
print("STEP 1: FETCHING MOVIES WITH FULL DETAILS (8-12 minutes)")
print("=" * 70)

async def fetch_page_with_details(session, language, page, language_name):
    """Fetch one page AND get details for all movies on that page"""
    try:
        # Get the page
        url = f"{BASE_URL}/discover/movie"
        params = {
            'api_key': API_KEY,
            'with_original_language': language,
            'sort_by': 'popularity.desc',
            'page': page,
            'vote_count.gte': 2
        }
        
        async with session.get(url, params=params, timeout=ClientTimeout(total=10)) as response:
            if response.status != 200:
                return []
            
            data = await response.json()
            movies_basic = data.get('results', [])
            
            # Now fetch details for each movie on this page
            detailed_movies = []
            for movie in movies_basic:
                movie_id = movie.get('id')
                if not movie_id:
                    continue
                
                # Fetch all details in parallel
                movie_detail, keywords_data, credits_data = await asyncio.gather(
                    fetch_movie_data(session, f"{BASE_URL}/movie/{movie_id}", {'api_key': API_KEY}),
                    fetch_movie_data(session, f"{BASE_URL}/movie/{movie_id}/keywords", {'api_key': API_KEY}),
                    fetch_movie_data(session, f"{BASE_URL}/movie/{movie_id}/credits", {'api_key': API_KEY}),
                    return_exceptions=True
                )
                
                # Process genres
                genres = []
                release_year = None
                if isinstance(movie_detail, dict):
                    genres = [g['name'] for g in movie_detail.get('genres', [])]
                    release_date = movie_detail.get('release_date', '')
                    if release_date and len(release_date) >= 4:
                        try:
                            release_year = int(release_date[:4])
                        except:
                            pass
                
                # Process keywords
                keywords = []
                if isinstance(keywords_data, dict):
                    keywords = [k['name'] for k in keywords_data.get('keywords', [])]
                
                # Process cast and crew
                cast, crew = [], []
                if isinstance(credits_data, dict):
                    cast = [actor['name'] for actor in credits_data.get('cast', [])[:10]]
                    crew = [person['name'] for person in credits_data.get('crew', []) 
                           if person.get('job') == 'Director'][:3]
                
                detailed_movies.append({
                    'movie_id': movie_id,
                    'title': movie.get('title', 'Unknown'),
                    'overview': movie.get('overview', ''),
                    'genres': genres,
                    'keywords': keywords,
                    'cast': cast,
                    'crew': crew,
                    'language': language_name,
                    'release_year': release_year
                })
            
            return detailed_movies
            
    except Exception as e:
        return []

async def fetch_movie_data(session, url, params):
    """Helper to fetch movie data"""
    try:
        async with session.get(url, params=params, timeout=ClientTimeout(total=8)) as response:
            if response.status == 200:
                return await response.json()
    except:
        pass
    return None

async def fetch_all_movies():
    """Fetch all movies with details in one go"""
    all_movies = []
    movie_ids_set = set()
    
    # Configuration: pages per language
    configs = [
        ('hi', 200, 'hindi'),   # 200 pages of Hindi
        ('ta', 75, 'tamil'),    # 75 pages of Tamil
        ('te', 75, 'telugu'),   # 75 pages of Telugu
    ]
    
    retry_options = ExponentialRetry(attempts=2, start_timeout=1)
    timeout = ClientTimeout(total=15)
    
    async with RetryClient(raise_for_status=False, retry_options=retry_options, timeout=timeout) as session:
        # Create all tasks
        tasks = []
        for language, max_pages, lang_name in configs:
            for page in range(1, max_pages + 1):
                tasks.append(fetch_page_with_details(session, language, page, lang_name))
        
        print(f"📡 Starting {len(tasks)} parallel requests...")
        
        # Process with high concurrency
        completed = 0
        total = len(tasks)
        
        # Process in batches to control memory
        batch_size = 100
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i+batch_size]
            results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    for movie in result:
                        movie_id = movie.get('movie_id')
                        if movie_id and movie_id not in movie_ids_set:
                            movie_ids_set.add(movie_id)
                            all_movies.append(movie)
                
                completed += 1
                if completed % 50 == 0:
                    progress = (completed / total) * 100
                    print(f"   ✓ {completed}/{total} pages ({progress:.1f}%) - {len(all_movies)} unique movies")
    
    return all_movies

print("\n🚀 Fetching movies with full details in parallel...")
all_movies = asyncio.run(fetch_all_movies())

# Count by language
hindi_count = len([m for m in all_movies if m.get('language') == 'hindi'])
tamil_count = len([m for m in all_movies if m.get('language') == 'tamil'])
telugu_count = len([m for m in all_movies if m.get('language') == 'telugu'])

print(f"\n✅ STEP 1 COMPLETE!")
print(f"   Total Movies: {len(all_movies)}")
print(f"   Hindi: {hindi_count}")
print(f"   Tamil: {tamil_count}")
print(f"   Telugu: {telugu_count}")

# ============================================
# STEP 2: BUILD SIMILARITY MATRIX
# ============================================

print("\n" + "=" * 70)
print("STEP 2: BUILDING SIMILARITY MATRIX (2-3 minutes)")
print("=" * 70)

bollywood_df = pd.DataFrame(all_movies)

def clean_text(text):
    if pd.isna(text) or text == '' or str(text).lower() == 'nan':
        return ''
    return str(text).lower().strip()

def create_smart_content(row):
    content_parts = []
    
    # Overview: 5x weight
    overview = clean_text(row.get('overview', ''))
    if overview:
        content_parts.extend([overview] * 5)
    
    # Genres: 4x weight
    genres = row.get('genres', [])
    if isinstance(genres, list):
        for genre in genres:
            clean_genre = clean_text(genre)
            if clean_genre:
                content_parts.extend([clean_genre] * 4)
    
    # Keywords: 3x weight
    keywords = row.get('keywords', [])
    if isinstance(keywords, list):
        for kw in keywords:
            clean_kw = clean_text(kw)
            if clean_kw:
                content_parts.extend([clean_kw] * 3)
    
    # Cast: 1x weight (top 3)
    cast = row.get('cast', [])
    if isinstance(cast, list):
        for actor in cast[:3]:
            clean_actor = clean_text(actor)
            if clean_actor:
                content_parts.append(clean_actor)
    
    # Director: 1x weight
    crew = row.get('crew', [])
    if isinstance(crew, list):
        for person in crew[:1]:
            clean_person = clean_text(person)
            if clean_person:
                content_parts.append(clean_person)
    
    return ' '.join(content_parts)

print("🍲 Creating content features...")
bollywood_df['smart_content'] = bollywood_df.apply(create_smart_content, axis=1)

print("🧮 Building TF-IDF matrix...")
tfidf = TfidfVectorizer(
    max_features=8000,
    stop_words='english',
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.7,
    sublinear_tf=True
)

tfidf_matrix = tfidf.fit_transform(bollywood_df['smart_content'])
print(f"   ✅ Matrix shape: {tfidf_matrix.shape}")

print("📊 Calculating cosine similarity...")
similarity_matrix = cosine_similarity(tfidf_matrix)
print(f"   ✅ Similarity matrix: {similarity_matrix.shape}")

print("🎭 Adding genre boost (vectorized)...")
# Fast vectorized genre similarity
def get_genre_set(genres):
    if isinstance(genres, list):
        return set(genres)
    return set()

genre_sets = [get_genre_set(bollywood_df.iloc[i]['genres']) for i in range(len(bollywood_df))]

# Vectorized genre similarity calculation
print("   Computing genre similarities...")
genre_similarity = np.zeros((len(bollywood_df), len(bollywood_df)))

# Only compute upper triangle (it's symmetric)
for i in range(len(bollywood_df)):
    if (i + 1) % 500 == 0:
        print(f"   Progress: {((i+1)/len(bollywood_df)*100):.1f}%")
    
    for j in range(i+1, len(bollywood_df)):
        if len(genre_sets[i]) > 0 and len(genre_sets[j]) > 0:
            common = len(genre_sets[i].intersection(genre_sets[j]))
            total = len(genre_sets[i].union(genre_sets[j]))
            genre_sim = common / total if total > 0 else 0
            genre_similarity[i][j] = genre_sim
            genre_similarity[j][i] = genre_sim

# Combine: 70% content + 30% genre
final_similarity = similarity_matrix * 0.7 + genre_similarity * 0.3
print(f"   ✅ Final similarity: {final_similarity.shape}")

print("\n✅ STEP 2 COMPLETE!")

# ============================================
# STEP 3: SAVE FILES
# ============================================

print("\n" + "=" * 70)
print("STEP 3: SAVING FILES")
print("=" * 70)

save_path = r'C:\Users\91897\Desktop\Movie R system'

bollywood_dict = bollywood_df.to_dict()
pickle.dump(bollywood_dict, open(f'{save_path}\\bollywood_movie_dict.pkl', 'wb'))
print(f"   ✅ bollywood_movie_dict.pkl saved")

pickle.dump(final_similarity, open(f'{save_path}\\bollywood_similarity.pkl', 'wb'))
print(f"   ✅ bollywood_similarity.pkl saved")

bollywood_df.to_csv(f'{save_path}\\bollywood_movies.csv', index=False)
print(f"   ✅ bollywood_movies.csv saved")

# ============================================
# FINAL SUMMARY
# ============================================

print("\n" + "=" * 70)
print("🎉 FAST BOLLYWOOD SYSTEM COMPLETE!")
print("=" * 70)
print(f"\n📊 Final Statistics:")
print(f"   Total Movies: {len(bollywood_df)}")
print(f"   Hindi: {len(bollywood_df[bollywood_df['language']=='hindi'])}")
print(f"   Tamil: {len(bollywood_df[bollywood_df['language']=='tamil'])}")
print(f"   Telugu: {len(bollywood_df[bollywood_df['language']=='telugu'])}")
print(f"\n✅ Files saved to: {save_path}")
print(f"\n👉 Now run: streamlit run app.py")
print("=" * 70)