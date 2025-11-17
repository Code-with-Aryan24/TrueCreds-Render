from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import hashlib 
import time    
import os 
import requests 
import json 
import sys # Added for deployment readiness

# --- INITIALIZATION ---
# Flask will look for the PORT environment variable set by Render.
PORT = int(os.environ.get("PORT", 5000))
HOST = '0.0.0.0'

app = Flask(__name__)
CORS(app) 

# --- MOCK LEDGER (In-Memory Database for Demo) ---
# NOTE: This resets every time the Render service restarts.
MOCK_LEDGER = {} 

# --- UTILITY: ML Scoring Logic ---
def calculate_ml_score(ml_features):
    peer_reviews = ml_features.get('peer_reviews', 0)
    project_complexity = ml_features.get('project_complexity', 0)
    
    # Simple linear model: Weighted sum of inputs (60/40 split)
    score = (peer_reviews * 6) + (project_complexity * 4)
    final_score = max(10, min(100, int(score))) 
    
    return f"{final_score}/100"

# --- UTILITY: IPFS HASHING (Simulated Immutability) ---
def upload_to_ipfs(credential_data):
    data_string = json.dumps(credential_data, sort_keys=True)
    stable_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
    ipfs_cid = f"Qm{stable_hash[:40]}" 
    print(f"DEBUG: IPFS Logic COMPLETE. CID: {ipfs_cid}")
    return ipfs_cid

# --- UTILITY: KASPA ANCHORING (Conceptual DLT Integration) ---
def mint_on_kaspa(ipfs_cid, ml_score):
    # Uses environment variable (which Render can set for you)
    kaspa_api_url = os.environ.get("KASPA_REST_API", "https://api-tn11.kaspa.org")
    
    try:
        # Check connectivity to the public Kaspa Testnet endpoint.
        response = requests.get(f"{kaspa_api_url}/info/blockdag", timeout=5)
        response.raise_for_status() 
        
        # Simulate a successful Kaspa Transaction ID (TX ID).
        tx_id_hash = hashlib.sha256((ipfs_cid + ml_score + str(time.time())).encode()).hexdigest()[:30]
        print("DEBUG: Kaspa Connectivity SUCCESS.")
        return f"kaspatest_tx_{tx_id_hash}"
    
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Kaspa API connectivity failed: {e}. Simulating TX ID.")
        tx_id_hash = hashlib.sha256((ipfs_cid + ml_score + str(time.time()) + "fallback").encode()).hexdigest()[:30]
        return f"kaspatest_tx_{tx_id_hash}_FALLBACK"

# =========================================================
# 2. CORE FLASK ROUTES (The Server Logic)
# =========================================================

# ROUTE 1: HOMEPAGE (Serves the HTML file)
@app.route('/')
def home():
    # Render looks for the file in the 'templates' folder
    return render_template('index.html')

# API ENDPOINT 1: ISSUE CREDENTIAL (Minting)
@app.route('/issue_credential', methods=['POST'])
def issue_credential():
    data = request.json
    
    # 1. Prepare data
    skill_name = data.get('skill_name', 'Unknown Skill')
    ml_features = data.get('ml_features', {})

    # 2. ML Scoring & Hashing
    ml_score = calculate_ml_score(ml_features)
    
    # Package data for hashing
    credential_for_hashing = {
        # Includes all the fields provided by the frontend
        **data, # Use dictionary unpacking for all fields
        "ml_score": ml_score,
        "timestamp": time.time(),
    }
    cert_hash = upload_to_ipfs(credential_for_hashing)
    
    # 3. BlockDAG Minting
    kaspa_tx_id = mint_on_kaspa(cert_hash, ml_score) 

    # Store the complete credential data in our MOCK_LEDGER
    full_credential_record = {
        **credential_for_hashing, # Includes all form data
        "cert_hash": cert_hash,
        "kaspa_tx_id": kaspa_tx_id,
        "revocation_status": "Active",
    }
    MOCK_LEDGER[kaspa_tx_id] = full_credential_record
    
    return jsonify({
        "status": "Success (BlockDAG ID Issued)", 
        "kaspa_tx_id": kaspa_tx_id,
        "ipfs_cid": cert_hash,
        "ml_score": ml_score,
        "skill_name": skill_name
    }), 201

# API ENDPOINT 2: VERIFY CREDENTIAL (Retrieval)
@app.route('/verify_credential/<tx_id>', methods=['GET'])
def verify_credential(tx_id):
    if tx_id in MOCK_LEDGER:
        record = MOCK_LEDGER[tx_id]
        return jsonify({
            "status": "Verified",
            "message": "Credential found on TrueCreds Mock Ledger.",
            "data": record
        }), 200
    else:
        return jsonify({
            "status": "Failed", 
            "message": "Credential not found on TrueCreds Mock Ledger or Kaspa BlockDAG.",
            "data": None
        }), 404

# =========================================================
# FINAL RUN COMMAND
# =========================================================
if __name__ == '__main__':
    # When deploying to Render, the 'start' command usually runs a WSGI server 
    # (like Gunicorn). For simple local testing, we use this Flask run command.
    print(f"Server starting on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)