import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_session import Session
from scraper import run_proxyless_scraping, run_proxy_scraping, load_proxies_from_file
from scraper import save_sites_to_file, display_sites, DORKS
import tempfile

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
Session(app)

# Global variables untuk menyimpan status scraping
scraping_status = {
    'is_running': False,
    'progress': 0,
    'sites_found': 0,
    'searches_performed': 0,
    'current_mode': None,
    'start_time': None,
    'results_file': None
}

scraping_thread = None
stop_event = threading.Event()

@app.route('/')
def index():
    """Halaman utama"""
    return render_template('index.html', dorks=DORKS[:20])

@app.route('/start-scraping', methods=['POST'])
def start_scraping():
    """Mulai proses scraping"""
    global scraping_thread, scraping_status, stop_event
    
    if scraping_status['is_running']:
        return jsonify({'error': 'Scraping sudah berjalan'}), 400
    
    # Reset stop event
    stop_event.clear()
    
    # Ambil parameter dari form
    mode = request.form.get('mode', 'proxyless')
    duration = int(request.form.get('duration', 30))
    workers = int(request.form.get('workers', 20))
    proxy_file = request.files.get('proxy_file')
    
    # Update status
    scraping_status.update({
        'is_running': True,
        'progress': 0,
        'sites_found': 0,
        'searches_performed': 0,
        'current_mode': mode,
        'start_time': datetime.now().isoformat(),
        'results_file': None
    })
    
    # Jalankan scraping di thread terpisah
    def scraping_task():
        try:
            if mode == 'proxyless':
                sites = run_proxyless_scraping(
                    num_workers=workers,
                    duration_minutes=duration
                )
            else:
                if proxy_file:
                    # Simpan file proxy sementara
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                        proxy_content = proxy_file.read().decode('utf-8')
                        f.write(proxy_content)
                        proxy_path = f.name
                    
                    proxies = load_proxies_from_file(proxy_path)
                    sites = run_proxy_scraping(
                        proxies=proxies,
                        num_workers=workers,
                        duration_minutes=duration
                    )
                    
                    # Hapus file sementara
                    os.unlink(proxy_path)
                else:
                    sites = []
            
            # Simpan hasil
            if sites:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"shopify_sites_{len(sites)}_{timestamp}.json"
                filepath = os.path.join(tempfile.gettempdir(), filename)
                
                save_sites_to_file(sites, filepath.replace('.json', ''), 'json')
                scraping_status['results_file'] = filepath
            
        except Exception as e:
            print(f"Error in scraping: {e}")
        finally:
            scraping_status['is_running'] = False
    
    scraping_thread = threading.Thread(target=scraping_task)
    scraping_thread.daemon = True
    scraping_thread.start()
    
    return jsonify({'message': 'Scraping dimulai', 'status': scraping_status})

@app.route('/stop-scraping', methods=['POST'])
def stop_scraping():
    """Hentikan scraping"""
    global stop_event
    stop_event.set()
    
    # Di scraper.py, Anda perlu menambahkan pengecekan stop_event
    # stop_flag.set() di scraper.py akan dipanggil
    
    scraping_status['is_running'] = False
    return jsonify({'message': 'Scraping dihentikan'})

@app.route('/status')
def get_status():
    """Ambil status scraping saat ini"""
    return jsonify(scraping_status)

@app.route('/results')
def get_results():
    """Download hasil scraping"""
    if not scraping_status['results_file']:
        return jsonify({'error': 'Tidak ada hasil'}), 404
    
    try:
        with open(scraping_status['results_file'], 'r') as f:
            results = json.load(f)
        return jsonify({'sites': results, 'count': len(results)})
    except:
        return jsonify({'error': 'Gagal membaca hasil'}), 500

@app.route('/download/<format>')
def download_results(format):
    """Download hasil dalam berbagai format"""
    if not scraping_status['results_file']:
        return jsonify({'error': 'Tidak ada hasil'}), 404
    
    base_path = scraping_status['results_file'].replace('.json', '')
    
    if format == 'json':
        return send_file(scraping_status['results_file'], 
                        as_attachment=True,
                        download_name=f'shopify_sites_{datetime.now().strftime("%Y%m%d")}.json')
    
    elif format == 'txt':
        txt_file = base_path + '.txt'
        if not os.path.exists(txt_file):
            with open(scraping_status['results_file'], 'r') as f:
                sites = json.load(f)
            with open(txt_file, 'w') as f:
                for site in sites:
                    f.write(site + '\n')
        
        return send_file(txt_file,
                        as_attachment=True,
                        download_name=f'shopify_sites_{datetime.now().strftime("%Y%m%d")}.txt')
    
    elif format == 'csv':
        csv_file = base_path + '.csv'
        if not os.path.exists(csv_file):
            with open(scraping_status['results_file'], 'r') as f:
                sites = json.load(f)
            import csv
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['URL', 'Domain'])
                for site in sites:
                    domain = site.replace('https://', '').replace('http://', '')
                    writer.writerow([site, domain])
        
        return send_file(csv_file,
                        as_attachment=True,
                        download_name=f'shopify_sites_{datetime.now().strftime("%Y%m%d")}.csv')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
