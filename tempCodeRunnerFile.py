import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from fuzzywuzzy import fuzz
from scholarly import scholarly

# Konfigurasi halaman
st.set_page_config(page_title="Pencarian Jurnal Ilmiah", page_icon="🔍", layout="centered")

# Gaya CSS untuk tampilan responsif
# ... (CSS tetap sama seperti sebelumnya)

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
                    "Year": paper['bib'].get('pub_year', 'N/A'),
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
                "Title": item.get("title", ["Unknown"])[0],
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
                                    for author in item.get("authors", {}).get("authors", [])]),
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
st.markdown("<h1 class='title'>🔍 Pencarian Referensi Jurnal Ilmiah</h1><hr>", unsafe_allow_html=True)

# Sidebar
st.sidebar.header("⚙️ Pengaturan Pencarian")
keyword = st.sidebar.text_input("Masukkan kata kunci pencarian:")
max_results = st.sidebar.slider("Jumlah hasil per sumber:", 1, 20, 5)
sd_key = st.sidebar.text_input("ScienceDirect API Key (opsional):", type="password")
ieee_key = st.sidebar.text_input("IEEE Xplore API Key (opsional):", type="password")

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

                