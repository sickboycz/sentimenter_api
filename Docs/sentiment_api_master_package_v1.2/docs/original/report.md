# Intelligent News‑Sentiment Research System for Market Impact

## Overview

Modern trading systems increasingly rely on *news awareness* rather than solely on price‑time series.  Instead of reading hundreds of articles manually, a program can ingest news from many sources, summarise the articles, store the information in a **vector‑searchable memory**, and compute **sentiment and impact measures**.  The goal is to build a local research system—similar to the *paperscraper* architecture used for scientific papers—which collects major and minor economic news and geopolitical events, summarises them, determines their sentiment and estimated market impact, stores the results in a vector database for retrieval via the OpenAI API, and serves them through an API for integration into an IBKR dashboard.

The following plan synthesises ideas from news‑sentiment services such as Moodix and Mood Metrics:

- Moodix’s sentiment index API returns time‑series records (date, open/high/low/close values of the index) plus moving averages and a qualitative sentiment label (RiskOn/RiskOff/Neutral) along with intraday and weekly news‑volume statistics【474122156689753†L112-L146】.  Subscribers call an endpoint like `https://app.moodix.market/api/sp-sentiment/?api_key=...` to retrieve JSON data for back‑testing【392341600627232†L114-L120】.
- Mood Metrics offers a REST API where clients submit text for sentiment analysis.  It can be run synchronously or asynchronously, returns a sentiment label with confidence scores, and allows a `FINANCIAL_NEWS` domain that provides polarity only【529439579172485†L75-L93】.  The API can group texts by `feedId` to track sentiment over time【529439579172485†L94-L99】.
- Finnhub’s news‑sentiment endpoint returns company‑level news statistics (buzz, news score) and provides percentages of bullish and bearish news in the last week【566890399068218†L2046-L2144】.
- The GDELT project is a free, open database that monitors news coverage worldwide, machine translates articles in 65 languages, and stores events along with emotional tone values; it provides open APIs and BigQuery tables enabling users to query 215+ years of global news【861300015915137†L19-L31】.

Using these references, we outline a system that implements comprehensive news scraping, summarisation, sentiment classification, impact scoring and correlation analysis.

## System Architecture

### 1. Data Acquisition Layer

1. **News Sources:**
   - **Major and minor economic news websites:** Reuters, Bloomberg, Financial Times, Economist, CNBC, local newspapers and central‑bank websites.  RSS feeds or official APIs (e.g., NewsAPI, GDELT’s Doc 2.0 search API【843444089958153†L21-L39】) will be used to ingest breaking news.  For local languages we rely on GDELT’s machine‑translated feeds【843444089958153†L52-L62】.
   - **Geopolitical and macroeconomic datasets:** Government announcements, IMF/OECD releases, FRED economic calendar, and news from multilateral agencies (World Bank, UN).  These are scraped via official feeds.
   - **Historical price data:** SPY ETF price history, accessible via Yahoo Finance or `yfinance` library for correlation analysis.
   - **Optional alternative data:** Social media sentiment, transcripts and press releases via providers like Finnhub and GDELT for additional context.

2. **Scraping Framework:**
   - Use a *crawler service* that monitors feeds and websites at regular intervals (e.g., hourly).  Each article is fetched and pre‑processed (HTML cleaned, boilerplate removed, language identified).
   - For heavy scraping (e.g., GDELT or large websites), implement a backoff schedule to respect rate limits and terms of service.

### 2. Processing Layer

1. **Chunking & Embedding:**
   - Articles are divided into chunks of ~512–1024 tokens.  For each chunk, compute embeddings via **OpenAI’s embeddings API** (or a local embedding model if privacy is required).  These embeddings are stored in a **vector database** (e.g., FAISS, Qdrant, Milvus) along with metadata (source, timestamp, categories, sentiment, impact score).
   - A *local memory store* (e.g., PostgreSQL or SQLite) keeps full article text and summarisation results for referencing and correlation analysis.

2. **Summarisation & Classification:**
   - For each article or chunk, call **OpenAI’s GPT** to generate a concise summary similar to paperscraper’s method (embedding search → summarise relevant passages).  Summaries include: a headline, a key‑points bullet list, and context on macroeconomic or geopolitical themes.
   - Apply **sentiment analysis** using a two‑stage approach:
     1. **Financial sentiment classifier:** Use an open‑source FinBERT model fine‑tuned for financial news.  This yields a sentiment polarity (positive, neutral, negative) and intensity.  Optionally integrate Mood Metrics for a secondary sentiment label, or design a simple API similar to Mood Metrics: submit text, receive `sentimentLabel` and `sentimentScore`【529439579172485†L75-L93】.
     2. **Competitiveness (market impact) classifier:** Build a rule‑based and machine learning model that assigns an *impact level* (High, Medium, Low) based on the news topic and historical evidence.  We derive features such as:
        - **Category weighting:** Central‑bank announcements, inflation/GDP releases and war/peace deals typically have high impact, whereas company earnings have medium, and local political stories have low impact.
        - **Coverage volume:** Number of articles (news volume intraday, weekly) similar to Moodix’s `news_volume_intraday` and `news_volatility_intraday` fields【474122156689753†L132-L136】.
        - **Tone strength:** Magnitude of positive/negative sentiment (e.g., FinBERT probability).  Moodix uses a `sentiment_wave` computed from moving averages of the index【474122156689753†L124-L129】; we can borrow the idea to derive our *impact wave*.
        - **Historical correlation:** For each category, compute the correlation between event‑level sentiment and SPY returns to calibrate the impact weighting.  A high positive correlation means positive news tends to push the market up; a negative correlation suggests risk‑off.
   - The classifier outputs (sentiment, impact score, category) are stored in the database.

### 3. Analytics & Correlation Layer

1. **Aggregated Sentiment Index:**
   - Each day, compute aggregated sentiment scores across all news items.  We can produce multiple indices: **Market Sentiment Index** (similar to Moodix’s `moodix_index`【474122156689753†L124-L132】), **Economic Sentiment Index**, and **Geopolitical Risk Index**.  Moving averages (5‑day and 10‑day) and a *sentiment wave* (difference between moving averages) indicate momentum and risk‑on/off status.
   - Additional metrics: news volume, news volatility, ratio of bullish to bearish headlines.

2. **Historical Correlation with SPY:**
   - Using historical SPY price data (adjusted close), compute daily returns and align them with aggregated sentiment indices.  Calculate **Pearson correlation coefficients** and **lagged correlations** (e.g., sentiment leads returns by 1–3 days) to identify predictive patterns.  Use cross‑correlation or Granger causality tests to quantify directional influence.
   - Train simple **regression models** (linear regression or random forest) where independent variables are aggregated sentiment metrics and dependent variable is next‑day SPY return.  Evaluate out‑of‑sample performance and record significance.  This step informs the impact classifier and provides research insights but does not directly trade.

### 4. API & Integration Layer (sentiment_api)

1. **REST API Design:**
   - The API is inspired by Mood Metrics and Moodix.  Key endpoints:
     - `POST /analysis`: Submit raw news text or a URL for analysis.  Accepts parameters like `domain` (`GENERAL` or `FINANCIAL`), `feed_id` (to group news by watchlist), and `category` (optional).  Returns sentiment label, score, impact level and summary.
     - `GET /analysis/{id}`: Retrieve a completed analysis.  Response includes summary, sentiment, impact, timestamp and category.
     - `GET /index`: Returns current aggregated indices and moving averages (similar to Moodix’s `moodix_index` fields)【474122156689753†L124-L132】 along with news volume statistics【474122156689753†L132-L146】.
     - `GET /history`: Retrieve historical index values between two dates, enabling correlation studies.
     - `GET /search`: Query the vector database with a natural‑language question.  Performs similarity search across stored summaries and returns top‑k relevant articles with references.
   - Authentication is managed with API keys (similar to Moodix: `?api_key=...`【392341600627232†L114-L120】).  Rate limiting is applied to protect resources.

2. **Data Flow:**
   - When the scraper ingests a new article, it triggers the summarisation and classification pipeline and stores results in the vector store.  It also updates aggregated sentiment indices.  Clients can subscribe to WebSocket or SSE streams to receive updates in real time.
   - A scheduler recomputes moving averages and correlation metrics daily.

3. **IBKR Integration:**
   - Instead of embedding a local LLM inside the Interactive Brokers environment (which was problematic), the IBKR dashboard interacts with `sentiment_api` via HTTP.  The dashboard can display the current sentiment indices, historical charts and relevant news summaries with impact scores.  It can also call the search endpoint to answer questions about how similar events affected the market in the past.

### 5. Storage & Memory Strategy

- **Local Memory:** A relational database stores raw articles, summaries, classification results and SPY returns.  This ensures reproducibility and enables statistical analysis.
- **Vector Memory:** A vector store indexes the embeddings of all news chunks and summaries.  When a question is asked through the API, the system retrieves relevant summaries via similarity search and provides them to the LLM to answer queries or generate context‑rich summaries.
- **Archival & Retention:** Use sliding windows (e.g., last 3 months) for high‑frequency retrieval to manage storage, while older data is archived to slower storage but accessible for back‑tests.

## Implementation Considerations

1. **Language & Frameworks:**  Python provides strong libraries for scraping (BeautifulSoup, Scrapy), natural language processing (transformers, spaCy), embeddings (openai API or sentence-transformers) and vector databases (faiss, chromadb).  A microservice architecture (e.g., FastAPI for the API) ensures scalability.
2. **Ethical & Legal:**  Respect the terms of service of each news source and abide by *fair use* policies.  Some premium APIs require paid subscriptions (Finnhub’s news sentiment is premium【566890399068218†L2046-L2144】).  For broad news coverage, use open sources such as GDELT and government press releases.
3. **Performance:**  Ingesting thousands of articles per day may be resource‑intensive.  Use asynchronous pipelines and concurrency (e.g., Celery or asyncio) to process in parallel.  For long articles, summarise incrementally to reduce API calls.
4. **Calibration & Evaluation:**  Impact scoring and correlation models should be continuously validated against actual market movements.  Overfitting must be avoided; these metrics are for research and should not directly trigger trades without human oversight.

## Conclusion

This architecture builds a local knowledge and sentiment engine akin to the paperscraper framework but adapted for global economic and geopolitical news.  By combining high‑quality scraping, summarisation, vector search, sentiment and impact modelling, and historical correlation analysis, the system provides actionable insights without embedding a local LLM.  The API design draws inspiration from Moodix’s sentiment index fields and Mood Metrics’ analysis endpoints【474122156689753†L112-L146】【529439579172485†L75-L93】, while the use of GDELT ensures broad coverage【861300015915137†L19-L31】.  Integrating the output into the IBKR dashboard via simple API calls delivers real‑time awareness of market‑moving news with quantified impact.
