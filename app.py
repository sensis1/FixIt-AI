import os
import io
import PIL.Image
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai 

app = Flask(__name__)
CORS(app)

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
                --text-main: #f1f5f9;
            }
            * { box-sizing: border-box; }
            body { 
                font-family: 'Inter', sans-serif; 
                margin: 0; background: #020617; color: var(--text-main);
                display: flex; flex-direction: column; height: 100vh; overflow: hidden;
            }

            .navbar {
                height: 65px; background: #0f172a;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                display: flex; align-items: center; justify-content: center; z-index: 1000;
            }
            .nav-logo { 
                font-size: 1.6rem; font-weight: 900; 
                background: linear-gradient(to right, var(--accent-blue), var(--accent-purple)); 
                -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                text-transform: uppercase; letter-spacing: 1px;
            }

            .view-container { display: flex; flex: 1; overflow: hidden; }

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

            .chat-window { flex: 1; display: flex; flex-direction: column; background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #020617 100%); }
            .chat-scroll { flex: 1; overflow-y: auto; padding: 30px; display: flex; flex-direction: column; gap: 20px; }
            
            .bubble { max-width: 85%; padding: 18px; border-radius: 15px; line-height: 1.6; font-size: 0.95rem; position: relative; }
            .user-bubble { align-self: flex-end; background: linear-gradient(135deg, #4f46e5, #9333ea); color: white; }
            .ai-bubble { align-self: flex-start; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255,255,255,0.1); }

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
            
            /* Typing Cursor */
            .typing::after { content: '|'; animation: blink 0.7s infinite; margin-left: 2px; color: var(--accent-blue); }
            @keyframes blink { 50% { opacity: 0; } }
        </style>
    </head>
    <body>
        <div class="navbar"><div class="nav-logo">FIXIT AI 🛠️</div></div>
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

            // --- SMOOTH TYPING ENGINE ---
            function smoothType(element, markdownText) {
                const htmlContent = marked.parse(markdownText);
                element.innerHTML = "";
                element.classList.add('typing');
                
                let i = 0;
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = htmlContent;
                const fullText = tempDiv.innerHTML;
                
                // Fast interval for high-end feel
                const timer = setInterval(() => {
                    element.innerHTML = fullText.substring(0, i);
                    i += 4; // Reveal 4 characters at a time for "fast-smooth" look
                    if (i >= fullText.length + 4) {
                        element.innerHTML = fullText;
                        element.classList.remove('typing');
                        clearInterval(timer);
                    }
                    document.getElementById('chatScroll').scrollTop = document.getElementById('chatScroll').scrollHeight;
                }, 10); 
            }

            async function submitDiagnostic() {
                const textInput = document.getElementById('userInput');
                const fileInput = document.getElementById('imageInput');
                const scroll = document.getElementById('chatScroll');

                const query = textInput.value.trim();
                const file = fileInput.files[0];

                if (!query && !file) return;

                // 1. ADD USER MSG
                const uMsg = document.createElement('div');
                uMsg.className = 'bubble user-bubble';
                uMsg.innerText = query || "Visual Scan Request";
                scroll.appendChild(uMsg);
                
                // 2. ⚡ AUTO-RESET INPUTS IMMEDIATELY
                textInput.value = "";
                fileInput.value = ""; // This "deletes" the file from the box after click
                scroll.scrollTop = scroll.scrollHeight;

                // 3. AI PLACEHOLDER
                const aiMsg = document.createElement('div');
                aiMsg.className = 'bubble ai-bubble';
                aiMsg.innerText = "...";
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
                    const data = await response.json();
                    
                    // 4. TRIGGER SMOOTH REVEAL
                    smoothType(aiMsg, data.result);
                    
                    memory.push({role: "user", text: query || "Visual Analysis"});
                    memory.push({role: "model", text: data.result});
                    
                    updateSidebar(query || "Visual Scan");
                } catch (e) { 
                    aiMsg.innerText = "Connection Failed."; 
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

        # THE "GARAGE LEGEND" PERSONALITY OVERHAUL
        system_rules = (
            "ROLE: You are FixIt AI, a legendary Master Mechanic who has seen it all. "
            "TONE: Expert, funny, and deeply realistic. You treat the user like a 'rookie' in your shop. "
            "STYLE: Mix humor with deep technical knowledge. If you see a missing engine, roast them, "
            "but then explain the actual mechanical nightmare of sourcing a block, wiring harnesses, and mounts. "
            "INSTRUCTIONS: Use Markdown. Keep responses around 250-300 words. Be detailed! "
            "REQUIRED STRUCTURE: "
            "### 🛠️ The FixIt Diagnostic: [Catchy Name]\\n"
            "- **Confidence**: [X%] | **Severity**: [Critical/Moderate/Minor]\\n"
            "- **Estimated Cost**: [Realistic Range or a joke if it's totaled]\\n"
            "- **DIY Difficulty**: [1-10/10] (Explain why, e.g., '10/10: You need a crane and a prayer')\\n"
            "### 🔍 The Real Talk (Analysis)\\n"
            "[Provide a detailed, funny, and technical breakdown of what you see. "
            "Use mechanic slang like 'knuckle-buster,' 'money-pit,' or 'crate motor.']\\n"
            "### 👨‍🔧 The Master's Advice\\n"
            "[Give actual, high-quality advice on what the next 3 steps should be, "
            "even if the advice is 'call a priest' or 'buy a new car.']"
        )

        contents = [system_rules]
        # Add text history for context
        for m in history: 
            if m.get('text'): contents.append(m['text'])
        
        # Handle Image
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                img = PIL.Image.open(io.BytesIO(file.read()))
                contents.append(img)
        
        # Final User Query
        contents.append(f"USER SAYS: {user_text if user_text else 'Look at this mess.'}")

        response = client.models.generate_content(model='gemini-2.5-flash-lite', contents=contents)
        return jsonify({"result": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
