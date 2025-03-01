import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from fuzzywuzzy import fuzz
from scholarly import scholarly

# Konfigurasi halaman
st.set_page_config(page_title="Pencarian Jurnal Ilmiah", page_icon="🔍", layout="centered")

# Gaya CSS untuk tampilan responsif
st.markdown("""
    <style>
        :root {
            --primary: #6a11ff;
            --secondary: #2575fc;
            --accent: #ff2d55;
            --background: linear-gradient(45deg, #f3f7ff 0%, #f9fbfd 100%);
            --text: #2c3e50;
            --card-bg: rgba(255, 255, 255, 0.95);
            --shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
        }

        @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
            100% { transform: translateY(0px); }
        }

        .title {
            text-align: center;
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5rem;
            font-weight: 800;
            margin: 1.5rem 0;
            letter-spacing: -1px;
            animation: float 4s ease-in-out infinite;
        }

        .result-card {
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: var(--shadow);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid rgba(255, 255, 255, 0.18);
            position: relative;
            overflow: hidden;
        }

        .result-card:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 12px 40px rgba(31, 38, 135, 0.25);
        }

        .result-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.4),
                transparent
            );
            transition: 0.5s;
        }

        .result-card:hover::before {
            left: 100%;
        }

        .result-card h4 {
            color: var(--primary);
            margin-bottom: 0.8rem;
            font-size: 1.3rem;
            font-weight: 700;
        }

        .result-card p {
            margin: 0.4rem 0;
            color: var(--text);
            font-size: 0.95rem;
        }

        .result-card a {
            position: relative;
            display: inline-block;
            margin-top: 1rem;
            padding: 0.6rem 1.5rem;
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            color: white !important;
            border-radius: 8px;
            overflow: hidden;
            transition: 0.4s;
            border: none;
            font-weight: 600;
            text-decoration: none !important;
        }

        .result-card a::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.4),
                transparent
            );
            transition: 0.5s;
        }

        .result-card a:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(var(--primary), 0.3);
        }

        .result-card a:hover::before {
            left: 100%;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .title {
                font-size: 2rem;
            }
            
            .result-card {
                margin: 0.8rem 0;
                padding: 1.2rem;
            }
            
            .result-card h4 {
                font-size: 1.1rem;
            }
        }

        /* Loading Animation */
        .loading-spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 2rem auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Dark Mode Support */
        @media (prefers-color-scheme: dark) {
            :root {
                --background: linear-gradient(45deg, #1a1a1a 0%, #2d2d2d 100%);
                --text: #ffffff;
                --card-bg: rgba(40, 40, 40, 0.95);
                --shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            
            .result-card {
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        .loading-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100px; /* Bisa disesuaikan */
        }

        .blinking {
            animation: blink 1.5s infinite;
            font-size: 24px;
            font-weight: bold;
            color: #3498db; /* Warna biru */
        }

        @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>

    <div class="loading-container">
        <h3 class="blinking">🔄 pengetahuan di jari mu - bintang</h3>
    </div>
""", unsafe_allow_html=True)


# ... (CSS tetap sama seperti sebelumnya)

# Ganti fungsi fuzzy_match dengan:
def fuzzy_match(title1, title2):
    return fuzz.ratio(title1.lower(), title2.lower()) if title1 and title2 else 0


# Fungsi untuk mengecek koneksi
def check_connection(url):
    try:
        requests.head(url, timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Fungsi pencarian di berbagai sumber
def search_google_scholar(keyword, max_results):
    try:
        results = []
        search_query = scholarly.search_pubs(keyword)
        for _ in range(max_results):
            try:
                paper = next(search_query)
                results.append({
                    "Title": paper['bib'].get('title', 'Unknown'),
                    "Authors": ", ".join(paper['bib'].get('author', [])),
                    "Journal": paper['bib'].get('venue', 'Unknown'),
                    "Year": paper['bib'].get('year', 'N/A'),  # Diperbaiki di sini
                    "Link": paper.get('pub_url', 'N/A'),
                    "Source": "Google Scholar"
                })
            except StopIteration:
                break
        return results
    except Exception as e:
        st.error(f"Error Google Scholar: {str(e)}")
        return []
def search_crossref(keyword, max_results):
    try:
        url = f"https://api.crossref.org/works?query={keyword}&rows={max_results}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return [{
               "Title": item.get("title", [""])[0] if item.get("title") else "Unknown",
                "Authors": ", ".join([f"{author.get('given', '')} {author.get('family', '')}" 
                                    for author in item.get("author", [])]),
                "Journal": item.get("container-title", ["Unknown"])[0],
                "Year": item.get("published-print", {}).get("date-parts", [[None]])[0][0],
                "Link": f"https://doi.org/{item.get('DOI', 'N/A')}",
                "Source": "CrossRef"
            } for item in data.get('message', {}).get('items', [])]
        return []
    except Exception as e:
        st.error(f"Error Crossref: {str(e)}")
        return []

def search_semantic_scholar(keyword, max_results):
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={keyword}&limit={max_results}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return [{
                "Title": item.get("title", "Unknown"),
                "Authors": ", ".join([a.get("name", "Unknown") for a in item.get("authors", [])]),
                "Journal": item.get("venue", "Unknown"),
                "Year": item.get("year", "N/A"),
                "Link": f"https://www.semanticscholar.org/paper/{item.get('paperId', 'N/A')}",
                "Source": "Semantic Scholar"
            } for item in data.get('data', [])]
        return []
    except Exception as e:
        st.error(f"Error Semantic Scholar: {str(e)}")
        return []

def search_sciencedirect(keyword, max_results, api_key):
    if not api_key:
        return []
    try:
        url = f"https://api.elsevier.com/content/search/sciencedirect?query={keyword}&count={max_results}"
        headers = {"X-ELS-APIKey": api_key}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return [{
                "Title": item.get("dc:title", "Unknown"),
                "Authors": item.get("dc:creator", "Unknown"),
                "Journal": item.get("prism:publicationName", "Unknown"),
                "Year": item.get("prism:coverDate", "N/A")[:4],
                "Link": item.get("link", [{}])[0].get("@href", "N/A"),
                "Source": "ScienceDirect"
            } for item in data.get('search-results', {}).get('entry', [])]
        return []
    except Exception as e:
        st.error(f"Error ScienceDirect: {str(e)}")
        return []

def search_ieee_xplore(keyword, max_results, api_key):
    if not api_key:
        return []
    try:
        url = f"http://ieeexploreapi.ieee.org/api/v1/search/articles?querytext={keyword}&max_records={max_results}&apikey={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return [{
                "Title": item.get("title", "Unknown"),
                "Authors": ", ".join([author.get("full_name", "Unknown") 
                                    for author in item.get("authors", [])]),  # Diperbaiki di sini
                "Journal": item.get("publication_title", "Unknown"),
                "Year": item.get("publication_year", "N/A"),
                "Link": item.get("document_link", "N/A"),
                "Source": "IEEE Xplore"
            } for item in data.get('articles', [])]
        return []
    except Exception as e:
        st.error(f"Error IEEE Xplore: {str(e)}")
        return []

# Fungsi pencarian paralel
def parallel_search(keyword, max_results, sd_key, ieee_key):
    references = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(search_google_scholar, keyword, max_results),
            executor.submit(search_crossref, keyword, max_results),
            executor.submit(search_semantic_scholar, keyword, max_results),
            executor.submit(search_sciencedirect, keyword, max_results, sd_key),
            executor.submit(search_ieee_xplore, keyword, max_results, ieee_key)
        ]
        
        for future in futures:
            try:
                references.extend(future.result())
            except Exception as e:
                st.error(f"Error in search: {str(e)}")

    # Menghitung relevansi dan mengurutkan
    for ref in references:
        ref["Relevance"] = fuzz.token_sort_ratio(ref["Title"].lower(), keyword.lower())
    
    # Menghapus duplikat berdasarkan judul
    seen = set()
    unique_refs = []
    for ref in references:
        title = ref["Title"].lower()
        if title not in seen:
            seen.add(title)
            unique_refs.append(ref)
    
    return sorted(unique_refs, key=lambda x: x["Relevance"], reverse=True)[:max_results]

# Antarmuka pengguna
st.markdown("<h1 class='title'>🔍 Sistem Pencarian Referensi Jurnal Ilmiah Multi-Sumber dengan Integrasi Google Scholar, CrossRef, dan Semantic Scholar serta Peringkat Relevansi Berbasis Fuzzy Matching </h1><hr>", unsafe_allow_html=True)

# Sidebar
#import streamlit as st
st.sidebar.header("⚙️ Pengaturan Pencarian")
# Input kata kunci
keyword = st.sidebar.text_input("Masukkan kata kunci pencarian:")
# Input jumlah hasil dengan batasan yang fleksibel
max_results = st.sidebar.number_input("Jumlah hasil per sumber:", min_value=1, max_value=1000, value=5, step=1)
# Input API Key opsional untuk sumber tertentu
sd_key = st.sidebar.text_input("ScienceDirect API Key (opsional):", type="password")
ieee_key = st.sidebar.text_input("IEEE Xplore API Key (opsional):", type="password")

st.sidebar.info("🔑 API Key diperlukan untuk ScienceDirect & IEEE Xplore (opsional)")

if st.sidebar.button("🚀 Jalankan Pencarian"):
    if not keyword:
        st.warning("Silakan masukkan kata kunci pencarian!")
    else:
        with st.spinner("🕵️‍♂️ Mencari di berbagai database jurnal..."):
            results = parallel_search(keyword, max_results, sd_key, ieee_key)
            
            if results:
                st.success(f"🎉 Ditemukan {len(results)} hasil relevan!")
                df = pd.DataFrame(results)
                
                # Tampilkan tabel
                st.subheader("📊 Hasil Pencarian Terstruktur")
                st.dataframe(df[['Title', 'Authors', 'Journal', 'Year', 'Source', 'Relevance']])
                
                # Tampilkan kartu hasil
                st.subheader("📚 Tampilan Hasil Detail")
                for idx, row in df.iterrows():
                    st.markdown(f"""
                    <div class="result-card">
                        <h4>{row['Title']}</h4>
                        <p><b>Penulis:</b> {row['Authors']}</p>
                        <p><b>Jurnal:</b> {row['Journal']} ({row['Year']})</p>
                        <p><b>Sumber:</b> {row['Source']} | Relevansi: {row['Relevance']}%</p>
                        <a href="{row['Link']}" target="_blank">📖 Buka Artikel</a>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Ekspor hasil
                st.subheader("💾 Ekspor Hasil")
                st.download_button("Unduh sebagai CSV", df.to_csv(index=False), "hasil_pencarian.csv")
                st.download_button("Unduh sebagai JSON", df.to_json(indent=2), "hasil_pencarian.json")
            else:
                st.error("😞 Tidak ditemukan hasil yang sesuai")