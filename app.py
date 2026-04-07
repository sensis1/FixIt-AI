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
        <title>FixIt AI | Diagnostic System</title>
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
                font-family: 'Inter', sans-serif; 
                margin: 0; background: #020617; color: var(--text-main);
                display: flex; flex-direction: column; height: 100vh; overflow: hidden;
            }

            /* CENTERED TOP NAVBAR */
            .navbar {
                height: 65px; background: #0f172a;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                display: flex; align-items: center; justify-content: center; z-index: 1000;
                position: relative;
            }
            .nav-logo { 
                font-size: 1.6rem; font-weight: 900; 
                background: linear-gradient(to right, var(--accent-blue), var(--accent-purple)); 
                -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                text-transform: uppercase; letter-spacing: 1px;
            }

            .view-container { display: flex; flex: 1; overflow: hidden; }

            /* SIDEBAR */
            .sidebar {
                width: 280px; background: var(--sidebar-bg); border-right: 1px solid rgba(255,255,255,0.05);
                display: flex; flex-direction: column;
            }
            .sidebar-title { padding: 25px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; color: #64748b; font-weight: 700; }
            .history-list { flex: 1; overflow-y: auto; padding: 10px; }
            .history-item { 
                padding: 12px; margin-bottom: 8px; border-radius: 10px; cursor: pointer;
                background: rgba(255,255,255,0.03); font-size: 0.85rem; transition: 0.2s;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            }
            .history-item:hover { background: rgba(56, 189, 248, 0.1); }

            /* MAIN CHAT */
            .chat-window { flex: 1; display: flex; flex-direction: column; background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #020617 100%); }
            .chat-scroll { flex: 1; overflow-y: auto; padding: 30px; display: flex; flex-direction: column; gap: 20px; }
            
            .bubble { max-width: 85%; padding: 18px; border-radius: 15px; line-height: 1.6; font-size: 0.95rem; }
            .user-bubble { align-self: flex-end; background: linear-gradient(135deg, #4f46e5, #9333ea); color: white; }
            .ai-bubble { align-self: flex-start; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255,255,255,0.1); }

            /* INPUT AREA */
            .input-dock { padding: 20px; background: #020617; border-top: 1px solid rgba(255,255,255,0.1); }
            .input-box { max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.05); border-radius: 15px; padding: 10px; }
            textarea {
                width: 100%; background: transparent; border: none; color: white; padding: 10px;
                font-size: 1rem; resize: none; outline: none; font-family: inherit;
            }
            .toolbar { display: flex; justify-content: space-between; align-items: center; padding-top: 10px; }
            
            .send-btn { 
                background: var(--accent-blue); color: #020617; border: none; padding: 10px 25px; 
                border-radius: 8px; font-weight: 800; cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="navbar">
            <div class="nav-logo">FIXIT AI 🛠️</div>
        </div>

        <div class="view-container">
            <aside class="sidebar">
                <div class="sidebar-title">Recent Reports</div>
                <div id="historyList" class="history-list"></div>
                <div style="padding: 20px;"><button onclick="location.reload()" style="width:100%; padding:10px; background:none; border:1px solid gray; color:white; border-radius:5px; cursor:pointer;">+ New Session</button></div>
            </aside>

            <main class="chat-window">
                <div id="chatScroll" class="chat-scroll">
                    <div class="ai-bubble bubble"><strong>System Ready.</strong> Upload an image or type a symptom for a quick mechanical scan.</div>
                </div>

                <div class="input-dock">
                    <div class="input-box">
                        <textarea id="userInput" rows="2" placeholder="Describe the issue..."></textarea>
                        <div class="toolbar">
                            <input type="file" id="imageInput" accept="image/*">
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

                const query = textInput.value.trim();
                const file = fileInput.files[0];

                if (!query && !file) return;

                const uMsg = document.createElement('div');
                uMsg.className = 'bubble user-bubble';
                uMsg.innerText = query || "Visual Scan Request";
                scroll.appendChild(uMsg);
                
                textInput.value = "";
                scroll.scrollTop = scroll.scrollHeight;

                const aiMsg = document.createElement('div');
                aiMsg.className = 'bubble ai-bubble';
                aiMsg.innerText = "Analyzing...";
                scroll.appendChild(aiMsg);

                const formData = new FormData();
                if (file) formData.append("image", file);
                formData.append("prompt", query);
                formData.append("history", JSON.stringify(memory));

                try {
                    const response = await fetch(`${window.location.origin}/analyze`, {
                        method: "POST",
                        body: formData
                    });
                    
                    if (!response.ok) throw new Error('Server error');
                    const data = await response.json();
                    
                    aiMsg.innerHTML = marked.parse(data.result);
                    
                    memory.push({role: "user", text: query || "Visual Analysis"});
                    memory.push({role: "model", text: data.result});
                    scroll.scrollTop = scroll.scrollHeight;
                    
                    updateSidebar(query || "Visual Scan");

                } catch (e) { 
                    aiMsg.innerText = "Connection Failed. Check your network."; 
                }
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

        # THE REFINED, CONCISE SYSTEM PROMPT
        system_rules = (
            "SYSTEM ROLE: You are FixIt AI, a Master Mechanic. "
            "INSTRUCTIONS: Be punchy and professional. Use Markdown. "
            "STRICTLY keep responses under 200 words. "
            "REQUIRED STRUCTURE: "
            "### 🛠️ Diagnostic\\n"
            "- **Issue**: [Technical Name]\\n"
            "- **Confidence**: [X%] | **Severity**: [Level]\\n"
            "- **Cost**: [Range]\\n"
            "### 🔍 Analysis\\n"
            "[2-3 sentence technical explanation]\\n"
            "### 👨‍🔧 DIY\\n"
            "- **Difficulty**: [1-10]\\n"
            "- **Quick Tip**: [Pro-tip]"
        )

        contents = [system_rules]
        for m in history: 
            if m.get('text'): contents.append(m['text'])
        
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                img = PIL.Image.open(io.BytesIO(file.read()))
                contents.append(img)
        
        contents.append(f"CURRENT QUERY: {user_text if user_text else 'Analyze image.'}")

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=contents
        )
        
        return jsonify({"result": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
