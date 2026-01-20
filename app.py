import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import threading
import json
import tempfile
import os
import sys
import subprocess
import io
import asyncio
from contextlib import redirect_stdout, redirect_stderr
import queue
import re

# Import scraper modules
sys.path.append('.')
try:
    # Import fungsi dari scraper.py
    import scraper
    from scraper import (
        run_proxyless_scraping,
        run_proxy_scraping,
        load_proxies_from_file,
        save_sites_to_file,
        DORKS,
        SEARCH_ENGINES,
        PROXYLESS_ENGINES,
        print_stats,
        stats as scraper_stats,
        found_sites,
        stop_flag
    )
    IMPORT_SUCCESS = True
except Exception as e:
    st.error(f"Error importing scraper: {str(e)}")
    IMPORT_SUCCESS = False

# Konfigurasi halaman
st.set_page_config(
    page_title="Shopify Scraper v6.0",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS kustom
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF6B6B;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4ECDC4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 1rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .progress-container {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .result-box {
        border: 2px solid #4ECDC4;
        border-radius: 10px;
        padding: 1rem;
        background-color: #f8f9fa;
    }
    .download-btn {
        background-color: #4ECDC4 !important;
        color: white !important;
        border: none !important;
    }
    .stop-btn {
        background-color: #FF6B6B !important;
        color: white !important;
        border: none !important;
    }
    .dataframe {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# State management
if 'scraping_active' not in st.session_state:
    st.session_state.scraping_active = False
if 'results' not in st.session_state:
    st.session_state.results = []
if 'status_updates' not in st.session_state:
    st.session_state.status_updates = []
if 'scraping_thread' not in st.session_state:
    st.session_state.scraping_thread = None
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

def run_scraper_in_thread(mode, duration, workers, proxy_file=None):
    """Jalankan scraper di thread terpisah"""
    try:
        if mode == "proxyless":
            st.session_state.results = run_proxyless_scraping(
                num_workers=workers,
                duration_minutes=duration
            )
        else:
            if proxy_file:
                # Simpan file proxy sementara
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                    f.write(proxy_file.getvalue().decode('utf-8'))
                    proxy_path = f.name
                
                proxies = load_proxies_from_file(proxy_path)
                if proxies:
                    st.session_state.results = run_proxy_scraping(
                        proxies=proxies,
                        num_workers=workers,
                        duration_minutes=duration
                    )
                else:
                    st.session_state.error = "No valid proxies found"
                
                # Cleanup
                os.unlink(proxy_path)
            else:
                st.session_state.error = "Proxy file required for proxy mode"
    
    except Exception as e:
        st.session_state.error = str(e)
    finally:
        st.session_state.scraping_active = False

def start_scraping(mode, duration, workers, proxy_file=None):
    """Mulai proses scraping"""
    if not IMPORT_SUCCESS:
        st.error("Scraper module not available")
        return
    
    st.session_state.scraping_active = True
    st.session_state.start_time = datetime.now()
    st.session_state.results = []
    st.session_state.error = None
    
    # Reset scraper global variables
    scraper.stop_flag.clear()
    scraper.found_sites.clear()
    scraper.stats.update({
        'found': 0,
        'searches': 0,
        'start_time': time.time(),
        'working_proxies': 0,
        'failed_proxies': 0
    })
    
    # Jalankan di thread
    thread = threading.Thread(
        target=run_scraper_in_thread,
        args=(mode, duration, workers, proxy_file)
    )
    thread.daemon = True
    thread.start()
    st.session_state.scraping_thread = thread

def stop_scraping():
    """Hentikan scraping"""
    if IMPORT_SUCCESS:
        scraper.stop_flag.set()
    st.session_state.scraping_active = False

def get_scraping_status():
    """Dapatkan status scraping saat ini"""
    if not IMPORT_SUCCESS:
        return {"active": False, "error": "Module not available"}
    
    status = {
        "active": st.session_state.scraping_active,
        "found": len(scraper.found_sites),
        "searches": scraper.stats.get('searches', 0),
        "working_proxies": scraper.stats.get('working_proxies', 0),
        "start_time": st.session_state.start_time
    }
    
    if st.session_state.start_time:
        elapsed = (datetime.now() - st.session_state.start_time).total_seconds()
        status["elapsed"] = elapsed
        if scraper.stats.get('searches', 0) > 0:
            status["sites_per_minute"] = (len(scraper.found_sites) / max(1, elapsed)) * 60
    
    return status

def save_results(format='txt'):
    """Simpan hasil scraping"""
    if not st.session_state.results:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == 'csv':
        df = pd.DataFrame({'URL': st.session_state.results})
        csv = df.to_csv(index=False)
        return csv, f"shopify_sites_{timestamp}.csv"
    
    elif format == 'json':
        json_data = json.dumps(st.session_state.results, indent=2)
        return json_data, f"shopify_sites_{timestamp}.json"
    
    else:  # txt
        txt = "\n".join(st.session_state.results)
        return txt, f"shopify_sites_{timestamp}.txt"

# Sidebar
with st.sidebar:
    st.image("https://cdn.worldvectorlogo.com/logos/shopify.svg", width=100)
    st.title("⚙️ Settings")
    
    mode = st.radio(
        "Scraping Mode",
        ["proxyless", "proxy"],
        format_func=lambda x: "🌐 Proxyless" if x == "proxyless" else "🔒 Proxy"
    )
    
    duration = st.slider(
        "Duration (minutes)",
        min_value=1,
        max_value=120,
        value=30,
        help="How long to run the scraper"
    )
    
    workers = st.slider(
        "Number of Workers",
        min_value=1,
        max_value=100,
        value=20,
        help="More workers = faster but more resource intensive"
    )
    
    if mode == "proxy":
        proxy_file = st.file_uploader(
            "Upload Proxy File",
            type=['txt'],
            help="Text file with one proxy per line"
        )
    else:
        proxy_file = None
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        start_disabled = st.session_state.scraping_active or not IMPORT_SUCCESS
        if st.button(
            "🚀 Start Scraping",
            type="primary",
            use_container_width=True,
            disabled=start_disabled
        ):
            start_scraping(mode, duration, workers, proxy_file)
            st.rerun()
    
    with col2:
        stop_disabled = not st.session_state.scraping_active
        if st.button(
            "⏹️ Stop",
            type="secondary",
            use_container_width=True,
            disabled=stop_disabled
        ):
            stop_scraping()
            st.rerun()
    
    st.markdown("---")
    
    # System Info
    st.subheader("ℹ️ System Info")
    st.info(f"Scraper Module: {'✅ Loaded' if IMPORT_SUCCESS else '❌ Failed'}")
    
    if IMPORT_SUCCESS:
        st.metric("Available Dorks", len(DORKS))
        st.metric("Search Engines", len(PROXYLESS_ENGINES))

# Header utama
st.markdown('<h1 class="main-header">🛍️ Shopify Scraper v6.0</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Advanced Shopify Store Discovery Tool</p>', unsafe_allow_html=True)

# Dashboard utama
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔍 Live Scraping", "📁 Results", "⚙️ Configuration"])

with tab1:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status = get_scraping_status()
        
        if status["active"]:
            st.markdown('<div class="stats-card">', unsafe_allow_html=True)
            st.metric("Status", "🟢 ACTIVE", delta="Running")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="stats-card">', unsafe_allow_html=True)
            st.metric("Status", "⚪ IDLE", delta="Ready")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stats-card">', unsafe_allow_html=True)
        st.metric("Sites Found", status.get("found", 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="stats-card">', unsafe_allow_html=True)
        searches = status.get("searches", 0)
        st.metric("Searches Made", searches)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Progress dan charts
    if status["active"] and status.get("elapsed"):
        progress_col, chart_col = st.columns([1, 2])
        
        with progress_col:
            st.subheader("Progress")
            
            # Estimate progress based on duration
            elapsed_minutes = status["elapsed"] / 60
            progress_pct = min(100, (elapsed_minutes / duration) * 100)
            
            st.progress(progress_pct / 100)
            st.caption(f"{elapsed_minutes:.1f} / {duration} minutes")
            
            if status.get("sites_per_minute"):
                st.metric("Speed", f"{status['sites_per_minute']:.1f} sites/min")
        
        with chart_col:
            # Simple chart
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=status["found"],
                title={"text": "Sites Found"},
                gauge={
                    'axis': {'range': [None, max(100, status["found"] * 2)]},
                    'bar': {'color': "#4ECDC4"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 100], 'color': "gray"}
                    ]
                }
            ))
            fig.update_layout(height=200)
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Live Scraping Monitor")
    
    if st.session_state.scraping_active:
        status_placeholder = st.empty()
        results_placeholder = st.empty()
        log_placeholder = st.empty()
        
        # Auto-refresh setiap 2 detik
        if st.button("🔄 Manual Refresh"):
            st.rerun()
        
        # Status update loop
        while st.session_state.scraping_active:
            status = get_scraping_status()
            
            with status_placeholder.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Elapsed Time", f"{status.get('elapsed', 0):.0f}s")
                with col2:
                    st.metric("Current Sites", status.get("found", 0))
                with col3:
                    st.metric("Searches", status.get("searches", 0))
            
            # Show latest results
            current_sites = list(scraper.found_sites)[-10:]  # Last 10 sites
            if current_sites:
                with results_placeholder.container():
                    st.subheader("Recently Found Sites")
                    for site in current_sites:
                        st.code(site)
            
            time.sleep(2)
            st.rerun()
    else:
        st.info("Scraping is not active. Start scraping from the sidebar.")

with tab3:
    st.subheader("Scraping Results")
    
    if st.session_state.results:
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.success(f"✅ Found {len(st.session_state.results)} Shopify sites")
        
        with col2:
            export_format = st.selectbox(
                "Export Format",
                ["txt", "csv", "json"],
                index=0
            )
        
        with col3:
            data, filename = save_results(export_format)
            st.download_button(
                label=f"📥 Download {export_format.upper()}",
                data=data,
                file_name=filename,
                mime={
                    "txt": "text/plain",
                    "csv": "text/csv",
                    "json": "application/json"
                }[export_format],
                use_container_width=True
            )
        
        # Display results in dataframe
        st.subheader("Site List")
        df = pd.DataFrame(st.session_state.results, columns=['URL'])
        df['Domain'] = df['URL'].str.replace('https://', '').str.replace('http://', '')
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "URL": st.column_config.LinkColumn("URL"),
                "Domain": st.column_config.TextColumn("Domain")
            }
        )
        
        # Stats chart
        if len(st.session_state.results) > 1:
            st.subheader("Results Analysis")
            
            # Extract domain patterns
            domains = [re.sub(r'^https?://', '', url).split('.')[0] for url in st.session_state.results]
            domain_counts = pd.Series(domains).value_counts().head(10)
            
            fig = px.bar(
                x=domain_counts.index,
                y=domain_counts.values,
                title="Top 10 Domain Patterns",
                labels={'x': 'Domain Prefix', 'y': 'Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    elif st.session_state.scraping_active:
        st.info("Scraping in progress... Results will appear here when complete.")
    else:
        st.info("No results yet. Start scraping to find Shopify sites.")

with tab4:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Search Configuration")
        
        st.write("**Available Search Engines:**")
        engines_df = pd.DataFrame(PROXYLESS_ENGINES)
        st.dataframe(
            engines_df[['name', 'url']],
            use_container_width=True,
            hide_index=True
        )
        
        st.write("**Proxy-based Engines:**")
        proxy_engines_df = pd.DataFrame(SEARCH_ENGINES)
        st.dataframe(
            proxy_engines_df[['name', 'url', 'weight']],
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        st.subheader("Dork Configuration")
        
        # Dork management
        dork_search = st.text_input("Search dorks", "")
        
        if dork_search:
            filtered_dorks = [d for d in DORKS if dork_search.lower() in d.lower()]
        else:
            filtered_dorks = DORKS[:50]  # Show first 50
        
        st.write(f"Showing {len(filtered_dorks)} of {len(DORKS)} dorks")
        
        # Dork list with checkboxes
        selected_dorks = []
        for dork in filtered_dorks:
            if st.checkbox(dork, value=True, key=f"dork_{dork}"):
                selected_dorks.append(dork)
        
        if st.button("🔄 Update Dorks Selection"):
            st.success(f"Selected {len(selected_dorks)} dorks for scraping")

# Footer
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)
with footer_col1:
    st.caption("**Version:** 6.0 Web UI")
with footer_col2:
    st.caption("**Engine Count:** " + str(len(PROXYLESS_ENGINES) if IMPORT_SUCCESS else "N/A"))
with footer_col3:
    st.caption("**Last Updated:** " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Auto-refresh jika scraping aktif
if st.session_state.scraping_active:
    time.sleep(2)
    st.rerun()
