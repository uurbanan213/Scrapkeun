#!/usr/bin/env python3
"""
Shopify Scraper V6.0 - Console Version
Scrapes Shopify sites using multiple search engines without Telegram bot
"""

import random
import time
import re
import threading
import requests
import urllib3
import queue
import os
import sys
import urllib.parse
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import signal
import csv

# Suppress warnings
urllib3.disable_warnings()

# ============================================================================
# CONFIGURATION
# ============================================================================

# User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/121.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) Chrome/121.0.0.0",
]

# Search engines for proxy mode
SEARCH_ENGINES = [
    {
        'name': 'Yahoo',
        'url': 'https://search.yahoo.com/search',
        'param': 'p',
        'weight': 0.35
    },
    {
        'name': 'DuckDuckGo',
        'url': 'https://html.duckduckgo.com/html/',
        'param': 'q',
        'weight': 0.25
    },
    {
        'name': 'Brave',
        'url': 'https://search.brave.com/search',
        'param': 'q',
        'weight': 0.20
    },
    {
        'name': 'SearX-1',
        'url': 'https://searx.be/search',
        'param': 'q',
        'weight': 0.10
    },
    {
        'name': 'SearX-2',
        'url': 'https://search.sapti.me/search',
        'param': 'q',
        'weight': 0.10
    }
]

# Proxyless search engines
PROXYLESS_ENGINES = [
    # Yahoo - most reliable
    {
        'name': 'Yahoo',
        'url': 'https://search.yahoo.com/search',
        'param': 'p',
    },
    # Brave Search - excellent for Shopify
    {
        'name': 'Brave',
        'url': 'https://search.brave.com/search',
        'param': 'q',
        'headers': {'Accept-Encoding': 'gzip, deflate'},
    },
    # SearX instances
    {
        'name': 'SearX-1',
        'url': 'https://searx.be/search',
        'param': 'q',
    },
    {
        'name': 'SearX-2',
        'url': 'https://search.sapti.me/search',
        'param': 'q',
    },
    {
        'name': 'SearX-3',
        'url': 'https://searx.tiekoetter.com/search',
        'param': 'q',
    },
    {
        'name': 'SearX-6',
        'url': 'https://search.ononoki.org/search',
        'param': 'q',
    },
    {
        'name': 'SearX-7',
        'url': 'https://searx.nixnet.services/search',
        'param': 'q',
    },
    {
        'name': 'SearX-9',
        'url': 'https://search.mdosch.de/search',
        'param': 'q',
    },
    {
        'name': 'SearX-13',
        'url': 'https://priv.au/search',
        'param': 'q',
    },
    {
        'name': 'SearX-15',
        'url': 'https://etsi.me/search',
        'param': 'q',
    },
    # Alternative engines
    {
        'name': 'Yandex',
        'url': 'https://yandex.com/search/',
        'param': 'text',
    },
    {
        'name': 'Qwant',
        'url': 'https://www.qwant.com/',
        'param': 'q',
    },
]

# Dorks list (truncated for brevity - you can expand this)
DORKS = [
    'site:myshopify.com',
    'site:myshopify.com store',
    'site:myshopify.com shop',
    'site:myshopify.com buy',
    'site:myshopify.com products',
    'site:myshopify.com collection',
    'site:myshopify.com cart',
    'site:myshopify.com checkout',
    'site:myshopify.com new',
    'site:myshopify.com sale',
    'site:myshopify.com deals',
    'site:myshopify.com best seller',
    'site:myshopify.com trending',
    'site:myshopify.com popular',
    'site:myshopify.com gift',
    'site:myshopify.com bundle',
    'site:myshopify.com makeup',
    'site:myshopify.com cosmetics',
    'site:myshopify.com beauty products',
    'site:myshopify.com clothing',
    'site:myshopify.com fashion',
    'site:myshopify.com apparel',
    'site:myshopify.com shoes',
    'site:myshopify.com accessories',
    'site:myshopify.com jewelry',
    'site:myshopify.com electronics',
    'site:myshopify.com gadgets',
    'site:myshopify.com home decor',
    'site:myshopify.com furniture',
    'site:myshopify.com pet supplies',
    'site:myshopify.com toys',
    'site:myshopify.com games',
    'site:myshopify.com books',
    'site:myshopify.com stationery',
    'site:myshopify.com office',
    'site:myshopify.com garden',
    'site:myshopify.com plant',
    'site:myshopify.com food',
    'site:myshopify.com gourmet',
    'site:myshopify.com coffee',
    'site:myshopify.com tea',
    'site:myshopify.com chocolate',
    'site:myshopify.com snack',
    'site:myshopify.com organic',
    'site:myshopify.com vegan',
    'site:myshopify.com natural',
    'site:myshopify.com eco',
    'site:myshopify.com sustainable',
    'site:myshopify.com green',
    'site:myshopify.com wellness',
    'site:myshopify.com health',
    'site:myshopify.com vitamin',
    'site:myshopify.com supplement',
    'site:myshopify.com fitness',
    'site:myshopify.com sports',
    'site:myshopify.com outdoor',
    'site:myshopify.com camping',
    'site:myshopify.com hiking',
    'site:myshopify.com yoga',
    'site:myshopify.com gym',
    'site:myshopify.com car',
    'site:myshopify.com auto',
    'site:myshopify.com motorcycle',
    'site:myshopify.com bike',
    'site:myshopify.com travel',
    'site:myshopify.com luggage',
    'site:myshopify.com photography',
    'site:myshopify.com camera',
    'site:myshopify.com music',
    'site:myshopify.com instrument',
    'site:myshopify.com audio',
    'site:myshopify.com headphone',
    'site:myshopify.com speaker',
    'site:myshopify.com art',
    'site:myshopify.com craft',
    'site:myshopify.com handmade',
    'site:myshopify.com vintage',
    'site:myshopify.com antique',
    'site:myshopify.com collectible',
]

# Regex patterns for Shopify URLs
MYSHOPIFY_RE = re.compile(r"https?://([a-z0-9\-]+)\.myshopify\.com", re.IGNORECASE)
MYSHOPIFY_RE_ALT1 = re.compile(r"([a-z0-9\-]+)\.myshopify\.com", re.IGNORECASE)
MYSHOPIFY_RE_ALT2 = re.compile(r"myshopify\.com/([a-z0-9\-]+)", re.IGNORECASE)
MYSHOPIFY_RE_FULL = re.compile(r"https?://([a-z0-9\-]+)\.myshopify\.com[^\s<>\"']*", re.IGNORECASE)

# Global variables
MAX_PROXY_WORKERS = 800
MAX_SCRAPE_WORKERS = 500
stop_flag = threading.Event()
found_sites = set()
sites_lock = threading.Lock()
stats = {
    'found': 0,
    'searches': 0,
    'start_time': None,
    'working_proxies': 0,
    'failed_proxies': 0
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                SHOPIFY SCRAPER v6.0 - CONSOLE                ║
║            Multi-Engine Search & Proxyless Mode              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_stats():
    """Print current statistics"""
    elapsed = time.time() - stats['start_time'] if stats['start_time'] else 0
    sites_per_min = (stats['found'] / max(1, elapsed)) * 60 if elapsed > 0 else 0
    success_rate = stats['found'] / max(1, stats['searches']) * 100 if stats['searches'] > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"📊 STATISTICS")
    print(f"{'='*80}")
    print(f"🎯 Sites Found: {stats['found']:,}")
    print(f"🔍 Searches Performed: {stats['searches']:,}")
    print(f"✅ Success Rate: {success_rate:.2f}%")
    print(f"⚡ Speed: {sites_per_min:.1f} sites/minute")
    print(f"⏱️  Time Elapsed: {elapsed:.0f} seconds")
    if stats['working_proxies'] > 0:
        print(f"🌐 Working Proxies: {stats['working_proxies']:,}")
    print(f"{'='*80}\n")

def save_sites_to_file(sites, filename=None, format='txt'):
    """Save found sites to file"""
    if not sites:
        print("❌ No sites to save!")
        return None
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shopify_sites_{len(sites)}_{timestamp}"
    
    if format == 'txt':
        filename = f"{filename}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for site in sorted(sites):
                f.write(f"{site}\n")
        print(f"✅ Saved {len(sites):,} sites to {filename}")
    
    elif format == 'csv':
        filename = f"{filename}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Domain'])
            for site in sorted(sites):
                domain = site.replace('https://', '').replace('http://', '')
                writer.writerow([site, domain])
        print(f"✅ Saved {len(sites):,} sites to {filename} (CSV format)")
    
    elif format == 'json':
        filename = f"{filename}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(sorted(sites), f, indent=2)
        print(f"✅ Saved {len(sites):,} sites to {filename} (JSON format)")
    
    return filename

def display_sites(sites, limit=50):
    """Display found sites in console"""
    if not sites:
        print("❌ No sites to display!")
        return
    
    print(f"\n{'='*80}")
    print(f"🎯 FOUND {len(sites):,} SHOPIFY SITES")
    print(f"{'='*80}")
    
    for i, site in enumerate(sorted(sites)[:limit], 1):
        print(f"{i:3d}. {site}")
    
    if len(sites) > limit:
        print(f"\n📁 ... and {len(sites) - limit:,} more sites")
    
    print(f"{'='*80}")

def get_headers():
    """Generate random headers for requests"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1'
    }

def parse_proxy(line, proxy_type="http"):
    """Parse proxy line with support for http, socks4, socks5"""
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    # Remove existing scheme
    for scheme in ['http://', 'https://', 'socks4://', 'socks5://', 'socks4a://', 'socks5h://']:
        if line.lower().startswith(scheme):
            line = line[len(scheme):]
            break
    
    try:
        if '@' in line:
            return f"{proxy_type}://{line}"
        elif ':' in line:
            parts = line.split(':')
            if len(parts) == 4:
                return f"{proxy_type}://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
            return f"{proxy_type}://{line}"
    except:
        pass
    return None

def load_proxies_from_file(filename, proxy_type="http"):
    """Load and parse proxies from file"""
    proxies = set()
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return proxies
    
    print(f"📥 Loading proxies from: {filename}")
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        for line in lines:
            proxy = parse_proxy(line, proxy_type)
            if proxy:
                proxies.add(proxy)
        
        print(f"✅ Loaded {len(proxies):,} unique proxies")
        return list(proxies)
    
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return []

def _normalize_shopify_url(url):
    """Normalize Shopify URL"""
    if not url:
        return None
    
    url = url.strip().strip('\'"')
    if not url:
        return None
    
    # Remove trailing punctuation
    url = re.sub(r'[\\\/]+$', '', url)
    url = url.rstrip('.,;!?)]}')
    
    if not url:
        return None
    
    if not url.lower().startswith(('http://', 'https://')):
        url = 'https://' + url.lstrip('/')
    
    url = url.replace('http://', 'https://', 1)
    if '#' in url:
        url = url.split('#', 1)[0]
    url = url.strip()
    
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc or parsed.path
    netloc = netloc.lower()
    
    if not netloc or '.myshopify.com' not in netloc:
        return None
    
    netloc = netloc.split('@', 1)[-1]
    netloc = netloc.split(':', 1)[0]
    
    return f"https://{netloc}"

def extract_shopify_urls(html):
    """Extract Shopify URLs from HTML content"""
    urls = set()
    
    def add_url(candidate):
        normalized = _normalize_shopify_url(candidate)
        if normalized:
            urls.add(normalized)
    
    # Try different patterns
    for match in MYSHOPIFY_RE.finditer(html):
        add_url(match.group(0))
    
    for match in MYSHOPIFY_RE_FULL.finditer(html):
        add_url(match.group(0))
    
    for match in MYSHOPIFY_RE_ALT1.finditer(html):
        domain = match.group(1)
        if domain and len(domain) > 3:
            add_url(f"https://{domain}.myshopify.com")
    
    for match in MYSHOPIFY_RE_ALT2.finditer(html):
        domain = match.group(1)
        if domain and len(domain) > 3:
            add_url(f"https://{domain}.myshopify.com")
    
    # Additional patterns
    href_pattern = re.compile(r'href=["\']([^"\']*\.myshopify\.com[^"\']*)["\']', re.IGNORECASE)
    for match in href_pattern.finditer(html):
        add_url(match.group(1))
    
    src_pattern = re.compile(r'src=["\']([^"\']*\.myshopify\.com[^"\']*)["\']', re.IGNORECASE)
    for match in src_pattern.finditer(html):
        add_url(match.group(1))
    
    return list(urls)

def test_proxy(proxy):
    """Test if a proxy is working"""
    try:
        response = requests.get(
            'https://httpbin.org/ip',
            proxies={'http': proxy, 'https': proxy},
            headers=get_headers(),
            timeout=10,
            verify=False
        )
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def test_proxy_with_search(proxy):
    """Test proxy with actual search query"""
    try:
        engine = random.choice(SEARCH_ENGINES)
        response = requests.get(
            engine['url'],
            params={engine['param']: 'site:myshopify.com test'},
            headers=get_headers(),
            proxies={'http': proxy, 'https': proxy},
            timeout=10,
            verify=False,
            allow_redirects=True
        )
        
        if 200 <= response.status_code < 400:
            return len(response.text) > 100
    except:
        pass
    return False

# ============================================================================
# PROXY MANAGEMENT
# ============================================================================

def test_proxies_batch(proxies, strict_test=False):
    """Test a batch of proxies"""
    working = []
    tested = 0
    total = len(proxies)
    lock = threading.Lock()
    q = queue.Queue()
    
    for proxy in proxies:
        q.put(proxy)
    
    print(f"\n🧪 Testing {total:,} proxies ({'STRICT' if strict_test else 'BASIC'} mode)")
    print(f"📊 Progress: 0/{total} (0.0%) | Working: 0")
    
    def worker():
        nonlocal tested
        while not q.empty() and not stop_flag.is_set():
            try:
                proxy = q.get_nowait()
                
                if strict_test:
                    is_working = test_proxy_with_search(proxy)
                else:
                    is_working = test_proxy(proxy)
                
                with lock:
                    if is_working:
                        working.append(proxy)
                    tested += 1
                    
                    if tested % 10 == 0 or tested == total:
                        pct = (tested / total) * 100
                        rate = len(working) / tested * 100 if tested > 0 else 0
                        print(f"\r📊 Progress: {tested:,}/{total:,} ({pct:.1f}%) | Working: {len(working)} ({rate:.1f}%)", end='')
                
                q.task_done()
            except queue.Empty:
                break
            except:
                with lock:
                    tested += 1
                q.task_done()
    
    workers = min(MAX_PROXY_WORKERS, total)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker) for _ in range(workers)]
        for future in as_completed(futures):
            pass
    
    print()
    print(f"✅ Testing complete: {len(working)}/{total} working proxies ({len(working)/total*100:.1f}%)")
    return working

# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================

def search_with_proxy(query, proxy, engine):
    """Search using proxy"""
    try:
        params = {engine['param']: query}
        
        if engine['name'] == 'DuckDuckGo':
            params['s'] = random.randint(0, 100)  # Random offset
        elif engine['name'] == 'Brave':
            params['offset'] = random.randint(0, 20)
        
        response = requests.get(
            engine['url'],
            params=params,
            headers=get_headers(),
            proxies={'http': proxy, 'https': proxy},
            timeout=15,
            verify=False,
            allow_redirects=True
        )
        
        if 200 <= response.status_code < 400:
            urls = extract_shopify_urls(response.text)
            return urls, True
        
        return [], False
    
    except Exception as e:
        return [], False

def search_proxyless(query, engine):
    """Search without proxy"""
    try:
        params = {engine['param']: query}
        
        # SearX specific params
        if 'SearX' in engine['name'] or 'searx' in engine['url'].lower():
            params['format'] = 'html'
            params['categories'] = 'general'
        
        headers = get_headers()
        if 'headers' in engine:
            headers.update(engine['headers'])
        
        response = requests.get(
            engine['url'],
            params=params,
            headers=headers,
            timeout=15,
            verify=False,
            allow_redirects=True
        )
        
        if 200 <= response.status_code < 400:
            urls = extract_shopify_urls(response.text)
            return urls, True
        
        return [], False
    
    except:
        return [], False

def proxy_scraper_worker(proxies, dorks, max_searches=1000):
    """Worker for proxy-based scraping"""
    local_found = 0
    
    for i in range(max_searches):
        if stop_flag.is_set():
            break
        
        try:
            query = random.choice(dorks)
            proxy = random.choice(proxies)
            engine = random.choice(SEARCH_ENGINES)
            
            urls, success = search_with_proxy(query, proxy, engine)
            
            with sites_lock:
                stats['searches'] += 1
                
                if urls:
                    new_sites = 0
                    for url in urls:
                        if url not in found_sites:
                            found_sites.add(url)
                            new_sites += 1
                    
                    if new_sites > 0:
                        stats['found'] = len(found_sites)
                        local_found += new_sites
                        print(f"✅ [{len(found_sites)}] {urls[0][:60]}..." if urls else "")
            
            # Delay between requests
            time.sleep(random.uniform(0.1, 0.5))
        
        except:
            time.sleep(0.5)
            continue
    
    return local_found

def proxyless_scraper_worker(dorks, max_searches=500):
    """Worker for proxyless scraping"""
    local_found = 0
    
    for i in range(max_searches):
        if stop_flag.is_set():
            break
        
        try:
            query = random.choice(dorks)
            engine = random.choice(PROXYLESS_ENGINES)
            
            urls, success = search_proxyless(query, engine)
            
            with sites_lock:
                stats['searches'] += 1
                
                if urls:
                    new_sites = 0
                    for url in urls:
                        if url not in found_sites:
                            found_sites.add(url)
                            new_sites += 1
                    
                    if new_sites > 0:
                        stats['found'] = len(found_sites)
                        local_found += new_sites
                        print(f"🌐 [{len(found_sites)}] {engine['name']}: {urls[0][:60]}..." if urls else "")
            
            # Longer delay for proxyless to avoid rate limiting
            delay = random.uniform(1.0, 3.0) if engine['name'] == 'Brave' else random.uniform(0.5, 1.5)
            time.sleep(delay)
        
        except:
            time.sleep(1.0)
            continue
    
    return local_found

# ============================================================================
# MAIN SCRAPING FUNCTIONS
# ============================================================================

def run_proxy_scraping(proxies, num_workers=50, duration_minutes=60):
    """Run proxy-based scraping"""
    print(f"\n🚀 Starting PROXY scraping")
    print(f"👥 Workers: {num_workers}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print(f"🌐 Proxies: {len(proxies):,}")
    print(f"🔍 Search Engines: {len(SEARCH_ENGINES)}")
    print(f"🔑 Dorks: {len(DORKS):,}")
    print(f"\nPress Ctrl+C to stop early and save results\n")
    
    stats['start_time'] = time.time()
    stats['working_proxies'] = len(proxies)
    stop_flag.clear()
    
    # Calculate searches per worker based on duration
    searches_per_minute = 20  # Estimated searches per minute per worker
    max_searches = searches_per_minute * duration_minutes
    
    def status_monitor():
        """Monitor and display status"""
        last_display = 0
        while not stop_flag.is_set():
            current = time.time()
            if current - last_display >= 5:  # Update every 5 seconds
                print_stats()
                last_display = current
            time.sleep(1)
    
    # Start status monitor in background
    monitor_thread = threading.Thread(target=status_monitor, daemon=True)
    monitor_thread.start()
    
    try:
        # Start workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(proxy_scraper_worker, proxies, DORKS, max_searches) 
                      for _ in range(num_workers)]
            
            # Wait for duration or until stopped
            start_time = time.time()
            while time.time() - start_time < duration_minutes * 60:
                if stop_flag.is_set():
                    break
                time.sleep(1)
            
            # Signal stop to workers
            stop_flag.set()
            
            # Wait for completion
            for future in as_completed(futures):
                pass
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        stop_flag.set()
    
    finally:
        print("\n" + "="*80)
        print("🎉 SCRAPING COMPLETE")
        print("="*80)
        print_stats()
        
        return list(found_sites)

def run_proxyless_scraping(num_workers=20, duration_minutes=60):
    """Run proxyless scraping"""
    print(f"\n🚀 Starting PROXYLESS scraping")
    print(f"👥 Workers: {num_workers}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print(f"🌐 Search Engines: {len(PROXYLESS_ENGINES)}")
    print(f"🔑 Dorks: {len(DORKS):,}")
    print(f"\nPress Ctrl+C to stop early and save results\n")
    
    stats['start_time'] = time.time()
    stop_flag.clear()
    
    # Fewer searches per worker for proxyless (to avoid rate limiting)
    searches_per_minute = 10
    max_searches = searches_per_minute * duration_minutes
    
    def status_monitor():
        """Monitor and display status"""
        last_display = 0
        while not stop_flag.is_set():
            current = time.time()
            if current - last_display >= 5:
                print_stats()
                last_display = current
            time.sleep(1)
    
    # Start status monitor
    monitor_thread = threading.Thread(target=status_monitor, daemon=True)
    monitor_thread.start()
    
    try:
        # Start workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(proxyless_scraper_worker, DORKS, max_searches) 
                      for _ in range(num_workers)]
            
            # Wait for duration
            start_time = time.time()
            while time.time() - start_time < duration_minutes * 60:
                if stop_flag.is_set():
                    break
                time.sleep(1)
            
            stop_flag.set()
            
            for future in as_completed(futures):
                pass
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        stop_flag.set()
    
    finally:
        print("\n" + "="*80)
        print("🎉 PROXYLESS SCRAPING COMPLETE")
        print("="*80)
        print_stats()
        
        return list(found_sites)

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Shopify Scraper v6.0 - Console Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --proxyless --duration 30 --workers 20
  %(prog)s --proxy-file proxies.txt --proxy-type http --duration 60
  %(prog)s --proxy-file proxies.txt --test-proxies --strict-test
  %(prog)s --load-sites saved_sites.txt --display --save-format json
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--proxyless', action='store_true', help='Use proxyless mode (no proxies needed)')
    mode_group.add_argument('--proxy-file', type=str, help='Path to proxy file for proxy mode')
    mode_group.add_argument('--load-sites', type=str, help='Load and display/save previously found sites')
    
    # Proxy options
    parser.add_argument('--proxy-type', choices=['http', 'socks4', 'socks5'], default='http',
                       help='Type of proxies in the file (default: http)')
    parser.add_argument('--test-proxies', action='store_true', help='Test proxies before scraping')
    parser.add_argument('--strict-test', action='store_true', help='Use strict testing (search query test)')
    
    # Scraping options
    parser.add_argument('--duration', type=int, default=30, help='Scraping duration in minutes (default: 30)')
    parser.add_argument('--workers', type=int, default=20, help='Number of worker threads (default: 20)')
    
    # Output options
    parser.add_argument('--display', action='store_true', help='Display found sites in console')
    parser.add_argument('--display-limit', type=int, default=50, help='Max sites to display (default: 50)')
    parser.add_argument('--save-format', choices=['txt', 'csv', 'json'], default='txt',
                       help='Format for saving sites (default: txt)')
    parser.add_argument('--output', type=str, help='Output filename (default: auto-generated)')
    parser.add_argument('--no-save', action='store_true', help='Don\'t save results to file')
    
    args = parser.parse_args()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\n🛑 Received Ctrl+C. Stopping...")
        stop_flag.set()
        time.sleep(1)
        print("\nPartial results have been saved.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Print banner
    print_banner()
    
    # Clear global variables
    global found_sites, stats
    found_sites.clear()
    stats = {'found': 0, 'searches': 0, 'start_time': None, 'working_proxies': 0, 'failed_proxies': 0}
    
    # Option 1: Load and display/save existing sites
    if args.load_sites:
        print(f"📁 Loading sites from: {args.load_sites}")
        
        try:
            if args.load_sites.endswith('.json'):
                with open(args.load_sites, 'r', encoding='utf-8') as f:
                    loaded_sites = json.load(f)
            else:
                # Assume text file
                with open(args.load_sites, 'r', encoding='utf-8') as f:
                    loaded_sites = [line.strip() for line in f if line.strip()]
            
            found_sites.update(loaded_sites)
            stats['found'] = len(found_sites)
            
            print(f"✅ Loaded {len(found_sites):,} sites")
            
            if args.display:
                display_sites(found_sites, args.display_limit)
            
            if not args.no_save:
                save_sites_to_file(found_sites, args.output, args.save_format)
            
            return
        
        except Exception as e:
            print(f"❌ Error loading file: {e}")
            return
    
    # Option 2: Proxyless scraping
    if args.proxyless:
        print("🌐 MODE: PROXYLESS SCRAPING")
        sites = run_proxyless_scraping(args.workers, args.duration)
    
    # Option 3: Proxy-based scraping
    elif args.proxy_file:
        print("🌐 MODE: PROXY-BASED SCRAPING")
        
        # Load proxies
        proxies = load_proxies_from_file(args.proxy_file, args.proxy_type)
        if not proxies:
            print("❌ No proxies loaded. Exiting.")
            return
        
        # Test proxies if requested
        if args.test_proxies:
            working_proxies = test_proxies_batch(proxies, args.strict_test)
            if not working_proxies:
                print("❌ No working proxies found. Exiting.")
                return
            
            # Save working proxies
            proxy_filename = save_sites_to_file(working_proxies, "working_proxies", 'txt')
            proxies = working_proxies
        
        sites = run_proxy_scraping(proxies, args.workers, args.duration)
    
    # Post-processing
    if sites:
        print(f"\n🎯 Total unique sites found: {len(sites):,}")
        
        if args.display:
            display_sites(sites, args.display_limit)
        
        if not args.no_save:
            saved_file = save_sites_to_file(sites, args.output, args.save_format)
            print(f"📁 Results saved to: {saved_file}")
    else:
        print("❌ No sites found. Try increasing duration or using different proxies.")

if __name__ == "__main__":
    main()
# ... kode asli Anda ...

# Variabel global untuk status update
web_status = {
    'sites_found': 0,
    'searches_performed': 0,
    'progress': 0
}

# Modifikasi fungsi run_proxyless_scraping dan run_proxy_scraping
# untuk update web_status

def update_web_status(found, searches, progress):
    """Update status untuk web UI"""
    web_status.update({
        'sites_found': found,
        'searches_performed': searches,
        'progress': progress
    })

# Contoh modifikasi di run_proxyless_scraping:
# Di dalam loop, tambahkan:
# update_web_status(len(found_sites), stats['searches'], progress_percentage)
