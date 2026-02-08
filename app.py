import time, csv, os, threading, datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# ================= 1. SETTINGS & PATH FIX =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_SOURCE = os.path.join(BASE_DIR, "lucky7_database.csv")

MY_IP = "192.168.0.103" 
START_TIME = time.time()

state = {
    "balance": 3000, 
    "pot": 0,           
    "laxmi_inn": 0,     
    "active_bet": "NONE", 
    "last_mid": "---", 
    "last_card": "WAITING...", 
    "sessions": [], 
    "skip_rounds": 0,
    "mode": "WARMUP (0/10)",
    "consecutive_loss": 0,
    "consecutive_wins": 0,
    "last_10_sides": [],
    "uptime": "00:00:00"
}

# ================= 2. AGGRESSIVE PATTERN LOGIC (NO CHANGES) =================
def predict_side_ai():
    if len(state["last_10_sides"]) < 10: return "NONE"
    recent_10 = state["last_10_sides"]
    l, h = recent_10.count("Low"), recent_10.count("High")
    
    if l == 5 and h == 5: 
        state["mode"] = "SKIP (5-5 NEUTRAL)"
        return "NONE"

    if l >= 6 and l <= 7: state["mode"] = "TREND LOW"; return "Low"
    if h >= 6 and h <= 7: state["mode"] = "TREND HIGH"; return "High"
    if l >= 8: state["mode"] = "REVERSAL HIGH"; return "High"
    if h >= 8: state["mode"] = "REVERSAL LOW"; return "Low"
    
    return "NONE"

# ================= 3. BOT WORKER (ONLY SL SYSTEM ADDED) =================
def bot_worker():
    global state
    last_processed_mid = None
    first_run = True 
    
    print(f"BOT LIVE! Reading CSV from: {DB_SOURCE}")

    while True:
        elapsed = int(time.time() - START_TIME)
        state["uptime"] = str(datetime.timedelta(seconds=elapsed))

        try:
            if os.path.exists(DB_SOURCE):
                with open(DB_SOURCE, 'r') as f:
                    reader = list(csv.reader(f))
                    if len(reader) < 2: continue
                    
                    latest_row = reader[-1]
                    ts, curr_mid, card_val, cat = latest_row[0], latest_row[1], latest_row[2], latest_row[3]

                    if first_run:
                        last_processed_mid = curr_mid
                        state["last_card"] = f"{card_val} ({cat})"
                        state["mode"] = "READY: WAITING FOR NEXT"
                        first_run = False
                        continue

                    if curr_mid != last_processed_mid:
                        
                        # --- 🛑 STOP LOSS SYSTEM (ONLY DEDUCTION & REFILL) ---
                        if state["balance"] < 200:
                            loss_to_cut = 3000 - state["balance"]
                            state["laxmi_inn"] -= loss_to_cut
                            state["balance"] = 3000
                            state["pot"] = 0
                            # Warmup reset ya last_10_sides clear nahi kiya
                            state["consecutive_loss"] = 0
                            state["consecutive_wins"] = 0
                            state["skip_rounds"] = 0
                            state["mode"] = f"SL REFILLED ₹{loss_to_cut}"
                            # Yahan se seedha loop skip karke agle data ka wait karega
                            last_processed_mid = curr_mid
                            continue

                        if state["skip_rounds"] > 0: state["skip_rounds"] -= 1

                        state["last_10_sides"].append(cat)
                        if len(state["last_10_sides"]) > 10: state["last_10_sides"].pop(0)
                        rounds_collected = len(state["last_10_sides"])

                        # Money Handling
                        if state["active_bet"] != "NONE":
                            if cat == "TIE":
                                state["balance"] -= 250 
                                state["pot"] -= 250
                                outcome = "TIE (50% LOSS)"
                            elif cat == state["active_bet"]:
                                state["balance"] += 500
                                state["pot"] += 500
                                state["consecutive_wins"] += 1
                                state["consecutive_loss"] = 0
                                outcome = "WIN ✅"
                            else:
                                state["balance"] -= 500
                                state["pot"] -= 500
                                state["consecutive_loss"] += 1
                                state["consecutive_wins"] = 0
                                outcome = "LOSS ❌"

                            # --- LAXMI INN PROFIT BOOKING ---
                            if state["pot"] >= 3000:
                                state["laxmi_inn"] += state["pot"]
                                state["pot"] = 0
                                state["balance"] = 3000
                                # Yahan bhi reset hata diya hai jaisa aapne pehle code me diya tha
                                state["mode"] = "PROFIT BOOKED!"

                            if state["consecutive_wins"] >= 2: state["skip_rounds"], state["consecutive_wins"] = 1, 0
                            elif state["consecutive_loss"] >= 2: state["skip_rounds"], state["consecutive_loss"] = 2, 0

                            state["sessions"].append({"time": ts, "mid": curr_mid, "bet": state["active_bet"], "card": card_val, "out": outcome})
                        
                        elif cat == "TIE":
                            state["sessions"].append({"time": ts, "mid": curr_mid, "bet": "NONE", "card": "7", "out": "TIE (SKIP)"})

                        if rounds_collected >= 10:
                            if state["skip_rounds"] == 0: state["active_bet"] = predict_side_ai()
                            else:
                                state["active_bet"] = "NONE"
                                state["mode"] = f"SKIPPING ({state['skip_rounds']} LEFT)"
                        else:
                            state["mode"] = f"WARMUP ({rounds_collected}/10)"

                        state["last_mid"] = curr_mid
                        state["last_card"] = f"{card_val} ({cat})"
                        last_processed_mid = curr_mid
            else:
                state["mode"] = "ERROR: CSV NOT FOUND"
            time.sleep(0.5)
        except Exception: time.sleep(1)

# ================= 4. DASHBOARD (NO CHANGES) =================
HTML_UI = """
<!DOCTYPE html><html><head><title>SAUMYA 10.9 PRO</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>:root { --bg: #010409; --accent: #ff58a6; } body { background: var(--bg); color: #c9d1d9; font-family: 'Segoe UI', sans-serif; } .stat-card { background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 20px; position:relative; } .value { font-size: 1.8rem; font-weight: bold; color: var(--accent); } </style></head>
<body class="p-4"><div class="container">
<div class="d-flex justify-content-between align-items-center mb-4"><h3>SAUMYA 10.9 <span style="color:var(--accent)">PRO (SL SYSTEM)</span></h3><div class="badge bg-dark border border-secondary p-2">UPTIME: <span id="uptime">00:00:00</span></div></div>
<div class="row g-3 mb-3">
    <div class="col-md-2"><div class="stat-card">BALANCE<div id="balance" class="value">0</div></div></div>
    <div class="col-md-2"><div class="stat-card">POT<div id="pot" class="value text-info">0</div></div></div>
    <div class="col-md-3"><div class="stat-card" style="border-color:gold">LAXMI INN<div id="laxmi_inn" class="value text-success">0</div></div></div>
    <div class="col-md-3"><div class="stat-card">MODE<div id="mode" class="value" style="font-size:0.9rem">...</div></div></div>
    <div class="col-md-2"><div class="stat-card">SKIP<div id="skips" class="value text-warning">0</div></div></div>
</div>
<div class="row g-3"><div class="col-md-6 text-center"><div class="stat-card">AI SIGNAL<div id="bet" class="value text-white">NONE</div></div></div><div class="col-md-6 text-center"><div class="stat-card">LAST CARD<div id="card" class="value" style="color:#d29922">...</div></div></div></div>
<div class="stat-card mt-4 p-0 overflow-hidden"><table class="table table-dark m-0"><thead><tr><th>Time</th><th>Match</th><th>Bet</th><th>Card</th><th>Result</th></tr></thead><tbody id="history"></tbody></table></div></div>
<script>function update(){fetch('/api/status').then(r=>r.json()).then(data=>{document.getElementById('balance').innerText='₹'+data.balance;document.getElementById('pot').innerText='₹'+data.pot;
let inn = document.getElementById('laxmi_inn'); inn.innerText='₹'+data.laxmi_inn; inn.style.color = (data.laxmi_inn < 0) ? '#ff4b4b' : '#00ff00';
document.getElementById('mode').innerText=data.mode;document.getElementById('bet').innerText=data.active_bet;document.getElementById('card').innerText=data.last_card;document.getElementById('skips').innerText=data.skip_rounds;document.getElementById('uptime').innerText=data.uptime;let rows='';data.sessions.slice().reverse().forEach(s=>{let resClass=s.out.includes('WIN')?'text-success':(s.out.includes('TIE')?'text-warning':'text-danger');rows+=`<tr><td>${s.time}</td><td>${s.mid}</td><td>${s.bet}</td><td>${s.card}</td><td class="${resClass} fw-bold">${s.out}</td></tr>`;});document.getElementById('history').innerHTML=rows;});}setInterval(update, 1000);</script></body></html>
"""

@app.route('/api/status')
def api_status(): return jsonify(state)
@app.route('/')
def home(): return render_template_string(HTML_UI)

if __name__ == '__main__':
    threading.Thread(target=bot_worker, daemon=True).start()
    app.run(host='0.0.0.0', port=5010)
