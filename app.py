from flask import Flask, render_template, request, jsonify
import socket
import requests
from concurrent.futures import ThreadPoolExecutor
import os

app = Flask(__name__)

VERBOSE_LOG_FILE = 'verbose_log.txt'

def find_ip(subdomain, domain, verbose=False):
    try:
        full_domain = f"{subdomain}.{domain}"
        ip_address = socket.gethostbyname(full_domain)
        if verbose:
            with open(VERBOSE_LOG_FILE, 'a') as f:
                f.write(f"[INFO] {full_domain} -> {ip_address}\n")
        return full_domain, ip_address
    except socket.gaierror:
        if verbose:
            with open(VERBOSE_LOG_FILE, 'a') as f:
                f.write(f"[ERROR] {full_domain} bulunamadı.\n")
        return None

def check_http_status(subdomain, ip, verbose=False):
    try:
        response = requests.get(f"http://{subdomain}", timeout=3)
        if verbose:
            with open(VERBOSE_LOG_FILE, 'a') as f:
                f.write(f"[INFO] {subdomain} ({ip}) -> HTTP {response.status_code}\n")
        return subdomain, ip, response.status_code
    except requests.RequestException:
        if verbose:
            with open(VERBOSE_LOG_FILE, 'a') as f:
                f.write(f"[ERROR] {subdomain} ({ip}) -> Yanıt alınamadı.\n")
        return subdomain, ip, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-scan', methods=['POST'])
def start_scan():
    results = {}
    verbose_output = []

    if os.path.exists(VERBOSE_LOG_FILE):
        os.remove(VERBOSE_LOG_FILE)
    
    domains = request.form['domains'].splitlines()
    subdomains = request.form['subdomains'].splitlines()
    verbose = 'verbose' in request.form

    for domain in domains:
        domain_results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(find_ip, subdomain, domain, verbose) for subdomain in subdomains]
            domain_ips = [f.result() for f in futures if f.result() is not None]
            
        for subdomain, ip in domain_ips:
            if ip:  # IP bulunmuşsa
                status_result = check_http_status(subdomain, ip, verbose)
                subdomain, ip, status_code = status_result
                domain_results.append((subdomain, ip, status_code))

        if domain_results:
            results[domain] = domain_results

    if verbose:
        with open(VERBOSE_LOG_FILE, 'r') as f:
            verbose_output = f.readlines()

    return jsonify(results=results, verbose_output=verbose_output)

@app.route('/verbose-output', methods=['GET'])
def verbose_output():
    if os.path.exists(VERBOSE_LOG_FILE):
        with open(VERBOSE_LOG_FILE, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    return jsonify(verbose_output=lines)

if __name__ == '__main__':
    app.run(debug=True)
