# 🎬 CineMatch – AI-Powered Movie Recommendation System

A **content-based movie recommendation web application** built using **machine learning and NLP**, designed to help users discover movies similar to their interests. CineMatch supports **Hollywood and Bollywood cinema**, including **Hindi, Tamil, and Telugu** movies, and is deployed as a live Streamlit application.

🌐 **Live Demo:** [https://cinematch-ai-powered-movie-recommender.streamlit.app/](https://cinematch-ai-powered-movie-recommender.streamlit.app/)

---

## 🚀 Features

### 🎯 Core Functionality

* **Multi-Industry Support**: Hollywood, Hindi, Tamil, and Telugu movies
* **Smart Movie Recommendations**: Suggestions based on genres, cast, crew, keywords, and plot overview
* **Content-Based Filtering**: Uses NLP and similarity metrics to match movies
* **Intelligent Search**: Select a movie and instantly get similar recommendations
* **Real-Time Poster Fetching**: Movie posters fetched dynamically via APIs
* **Ratings Integration**: IMDb / TMDb ratings for better decision-making

### 🎨 User Experience

* **Netflix-Inspired Dark UI**
* **Tabbed Navigation** for Hollywood and Bollywood sections
* **Interactive & Responsive Interface** built with Streamlit
* **Fast Autocomplete Dropdown** for movie selection

---

## 🛠 Tech Stack

### Backend & ML

* **Python**
* **Pandas** – Data manipulation
* **Scikit-learn** – Count Vectorizer, TF-IDF, cosine similarity
* **NLTK** – Text preprocessing and NLP
* **NumPy** – Numerical operations
* **Pickle** – Model serialization

### Frontend

* **Streamlit** – Web application framework
* **Custom CSS** – Enhanced UI/UX

### APIs & Data

* **TMDb API** – Movie metadata & posters
* **OMDb API** – Ratings and additional movie details

---

## 📂 Project Structure

```
Movie-Recommendation-System-/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── packages.txt                    # System-level dependencies
├── .streamlit/
│   └── config.toml                # Streamlit configuration
├── movie_dict.pkl                 # Hollywood movie dataset
├── similarity.pkl                 # Hollywood similarity matrix
├── bollywood_movie_dict.pkl       # Bollywood movie dataset
├── bollywood_similarity.pkl       # Bollywood similarity matrix
├── complete_bollywood_pipeline.py # Bollywood data processing script
└── README.md                      # Project documentation
```

---

## 📈 How It Works

### 1️⃣ Data Preprocessing

* Movie datasets are cleaned and processed using **NLP techniques**
* Important features extracted:

  * Genres
  * Cast
  * Crew (Director)
  * Keywords
  * Plot Overview

### 2️⃣ Feature Engineering

* Text features are combined into a **single smart content column**
* Vectorization performed using **Count Vectorizer / TF-IDF**
* Feature weighting applied to prioritize genres and keywords

### 3️⃣ Similarity Computation

* **Cosine Similarity** is used to calculate movie-to-movie similarity
* Separate similarity matrices for Hollywood and Bollywood datasets

### 4️⃣ Recommendation Engine

* User selects a movie
* Top similar movies are retrieved based on similarity scores
* Posters and ratings fetched in real-time using APIs

---

## 🌟 Getting Started

### Prerequisites

* Python 3.11+
* Git
* pip

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/Bhawna-Nimrani/Movie-Recommendation-System-.git
cd Movie-Recommendation-System-
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Run the application**

```bash
streamlit run app.py
```

4. **Open in browser**

* App will run at `http://localhost:8501`

---

## 📝 Future Enhancements

* User Authentication & Profiles
* Watchlist and Favorites Feature
* Advanced Filters (Actor, Director, Year)
* Hybrid Recommendation System
* Trailer Integration
* Feedback-Based Model Improvement

---

## 📊 Dataset & References

* **Dataset**: TMDb Movie Metadata (Kaggle)
  [https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata)

* **Reference Tutorial**:
  [https://www.youtube.com/watch?v=1xtrIEwY_zY&t=2s](https://www.youtube.com/watch?v=1xtrIEwY_zY&t=2s)

---

## 👤 Author

**Bhawna Nimrani**
GitHub: [https://github.com/Bhawna-Nimrani](https://github.com/Bhawna-Nimrani)

---

⭐ *If you like this project, don’t forget to star the repository!*
Made with ❤️ using Python, Machine Learning, and Streamlit
