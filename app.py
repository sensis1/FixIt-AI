import os
import io
import PIL.Image
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai 

app = Flask(__name__)
CORS(app)

# Secure API Key Fetch
API_KEY = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FixIt AI | Pro Diagnostic Suite</title>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            :root {
                --accent-blue: #38bdf8;
                --accent-purple: #a855f7;
                --sidebar-bg: #0f172a;
                --chat-bg: #1e1b4b;
                --text-main: #f1f5f9;
            }
            * { box-sizing: border-box; }
            body { 
                font-family: 'Inter', -apple-system, sans-serif; 
                margin: 0; background: #020617; color: var(--text-main);
                display: flex; flex-direction: column; height: 100vh; overflow: hidden;
            }

            /* TOP NAVIGATION BAR */
            .navbar {
                height: 65px; background: rgba(15, 23, 42, 0.8);
                backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255,255,255,0.1);
                display: flex; align-items: center; padding: 0 30px; position: sticky; top: 0; z-index: 1000;
            }
            .nav-logo { font-size: 1.6rem; font-weight: 900; background: linear-gradient(to right, var(--accent-blue), var(--accent-purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

            .view-container { display: flex; flex: 1; overflow: hidden; }

            /* SIDEBAR HISTORY */
            .sidebar {
                width: 280px; background: var(--sidebar-bg); border-right: 1px solid rgba(255,255,255,0.05);
                display: flex; flex-direction: column; transition: 0.3s;
            }
            .sidebar-title { padding: 25px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; color: #64748b; font-weight: 700; }
            .history-list { flex: 1; overflow-y: auto; padding: 10px; }
            .history-item { 
                padding: 12px; margin-bottom: 8px; border-radius: 10px; cursor: pointer;
                background: rgba(255,255,255,0.03); font-size: 0.85rem; border: 1px solid transparent;
                transition: 0.2s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            }
            .history-item:hover { background: rgba(56, 189, 248, 0.1); border-color: var(--accent-blue); }

            /* MAIN CHAT WINDOW */
            .chat-window { flex: 1; display: flex; flex-direction: column; background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #020617 100%); }
            .chat-scroll { flex: 1; overflow-y: auto; padding: 40px; display: flex; flex-direction: column; gap: 25px; }
            
            .bubble { max-width: 80%; padding: 18px 24px; border-radius: 20px; line-height: 1.7; font-size: 0.98rem; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
            .user-bubble { align-self: flex-end; background: linear-gradient(135deg, #4f46e5, #9333ea); color: white; border-bottom-right-radius: 4px; }
            .ai-bubble { align-self: flex-start; background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.1); border-bottom-left-radius: 4px; }

            /* INPUT DOCK */
            .input-dock { padding: 30px; background: rgba(2, 6, 23, 0.9); border-top: 1px solid rgba(255,255,255,0.05); }
            .input-box { max-width: 900px; margin: 0 auto; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 18px; padding: 10px; }
            textarea {
                width: 100%; background: transparent; border: none; color: white; padding: 15px;
                font-size: 1rem; resize: none; outline: none; font-family: inherit;
            }
            .toolbar { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-top: 1px solid rgba(255,255,255,0.05); }
            
            .file-btn { color: #94a3b8; font-size: 0.85rem; cursor: pointer; }
            .send-btn { 
                background: var(--accent-blue); color: #020617; border: none; padding: 10px 24px; 
                border-radius: 10px; font-weight: 800; cursor: pointer; transition: 0.2s;
            }
            .send-btn:hover { background: white; transform: scale(1.05); }
        </style>
    </head>
    <body>
        <div class="navbar">
            <div class="nav-logo">FIXIT AI PRO 🛠️</div>
        </div>

        <div class="view-container">
            <aside class="sidebar">
                <div class="sidebar-title">Recent Reports</div>
                <div id="historyList" class="history-list">
                    </div>
                <div style="padding: 20px;">
                    <button onclick="window.location.reload()" style="width:100%; padding:10px; border-radius:8px; background:rgba(255,255,255,0.05); color:white; border:1px solid rgba(255,255,255,0.1); cursor:pointer;">+ New Session</button>
                </div>
            </aside>

            <main class="chat-window">
                <div id="chatScroll" class="chat-scroll">
                    <div class="ai-bubble bubble">
                        <strong>System Online.</strong> Upload a vehicle component image or describe a mechanical symptom to begin diagnostic protocols.
                    </div>
                </div>

                <div class="input-dock">
                    <div class="input-box">
                        <textarea id="userInput" rows="2" placeholder="Analyze engine noise..."></textarea>
                        <div class="toolbar">
                            <input type="file" id="imageInput" accept="image/*" class="file-btn">
                            <button class="send-btn" onclick="submitDiagnostic()">ANALYZE</button>
                        </div>
                    </div>
                </div>
            </main>
        </div>

        <script>
            let memory = [];

            async function submitDiagnostic() {
                const textInput = document.getElementById('userInput');
                const fileInput = document.getElementById('imageInput');
                const scroll = document.getElementById('chatScroll');

                if (!textInput.value && !fileInput.files[0]) return;

                // Render User Message
                const uMsg = document.createElement('div');
                uMsg.className = 'bubble user-bubble';
                uMsg.innerText = textInput.value || "Image Analysis Request";
                scroll.appendChild(uMsg);
                
                const query = textInput.value;
                textInput.value = "";
                scroll.scrollTop = scroll.scrollHeight;

                // Placeholder for AI
                const aiMsg = document.createElement('div');
                aiMsg.className = 'bubble ai-bubble';
                aiMsg.innerText = "Running diagnostic scans...";
                scroll.appendChild(aiMsg);

                const formData = new FormData();
                if (fileInput.files[0]) formData.append("image", fileInput.files[0]);
                formData.append("prompt", query);
                formData.append("history", JSON.stringify(memory));

                try {
                    const response = await fetch(`${window.location.origin}/analyze`, {
                        method: "POST",
                        body: formData
                    });
                    const data = await response.json();
                    
                    // Use marked.js to render beautiful Markdown
                    aiMsg.innerHTML = marked.parse(data.result);
                    
                    memory.push({role: "user", text: query});
                    memory.push({role: "model", text: data.result});
                    scroll.scrollTop = scroll.scrollHeight;
                    
                    // Update Sidebar Title
                    updateSidebar(query || "Visual Scan");

                } catch (e) { aiMsg.innerText = "Diagnostic Failed: Offline."; }
            }

            function updateSidebar(text) {
                const list = document.getElementById('historyList');
                const item = document.createElement('div');
                item.className = 'history-item';
                item.innerText = text.substring(0, 25) + "...";
                list.prepend(item);
            }
        </script>
    </body>
    </html>
    """

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        user_text = request.form.get('prompt', '')
        history = json.loads(request.form.get('history', '[]'))

        # THE "MASTER" SYSTEM INSTRUCTION
        system_rules = (
            "SYSTEM ROLE: You are FixIt AI, a Master Mechanic with 40 years of experience. "
            "INSTRUCTIONS: For every response, you must be technically precise and detailed. "
            "Use Markdown formatting (bolding, lists, headers). "
            "REQUIRED STRUCTURE: "
            "### 🛠️ Diagnostic Report "
            "- **Primary Issue**: [Technical Name] "
            "- **Confidence Score**: [0-100%] "
            "- **Severity**: [Critical/Moderate/Minor] "
            "- **Est. Repair Cost**: [Range in USD] "
            "### 🔍 Detailed Analysis "
            "[Provide a step-by-step mechanical explanation here] "
            "### 👨‍🔧 DIY Instructions "
            "- **Difficulty**: [1-10] "
            "- **Tools Needed**: [List] "
            "- **Warning**: [Safety disclaimer]"
        )

        contents = [system_rules]
        for m in history: contents.append(m['text'])
        
        if 'image' in request.files:
            img = PIL.Image.open(io.BytesIO(request.files['image'].read()))
            contents.append(img)
        
        contents.append(f"CURRENT QUERY: {user_text}")

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=contents
        )
        
        return jsonify({"result": response.text})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
