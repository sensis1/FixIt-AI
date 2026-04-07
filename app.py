import os
import io
import PIL.Image
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
        <style>
            :root {
                --accent-blue: #38bdf8;
                --accent-purple: #a855f7;
                --sidebar-bg: rgba(15, 23, 42, 0.95);
            }
            body { 
                font-family: 'Inter', sans-serif; margin: 0; display: flex; 
                height: 100vh; background: #0f172a; color: #f8fafc; overflow: hidden;
            }
            
            /* SIDEBAR */
            .sidebar {
                width: 260px; background: var(--sidebar-bg); border-right: 1px solid rgba(255,255,255,0.1);
                display: flex; flex-direction: column; transition: 0.3s;
            }
            .sidebar-header { padding: 20px; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.1); }
            .chat-list { flex: 1; overflow-y: auto; padding: 10px; }
            .chat-item { 
                padding: 12px; margin-bottom: 8px; border-radius: 8px; cursor: pointer;
                font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                background: rgba(255,255,255,0.03); border: 1px solid transparent;
            }
            .chat-item:hover { background: rgba(255,255,255,0.08); border-color: var(--accent-blue); }

            /* MAIN CHAT AREA */
            .main-content { flex: 1; display: flex; flex-direction: column; background: radial-gradient(circle at top, #1e1b4b, #0f172a); }
            .messages-container { flex: 1; overflow-y: auto; padding: 40px 20px; display: flex; flex-direction: column; gap: 20px; }
            
            .msg { max-width: 80%; padding: 15px 20px; border-radius: 18px; line-height: 1.6; font-size: 0.95rem; }
            .user-msg { align-self: flex-end; background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple)); color: white; }
            .ai-msg { align-self: flex-start; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); }

            .input-area { padding: 30px; border-top: 1px solid rgba(255,255,255,0.1); background: rgba(15, 23, 42, 0.8); }
            .input-container { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 10px; }
            
            textarea {
                width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2);
                border-radius: 12px; color: white; padding: 15px; resize: none; font-family: inherit;
            }
            .controls { display: flex; justify-content: space-between; align-items: center; }
            
            button { 
                background: linear-gradient(to right, var(--accent-blue), var(--accent-purple)); 
                color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer;
            }
            button:hover { filter: brightness(1.2); }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">FixIt AI History</div>
            <div id="chatList" class="chat-list">
                </div>
            <div style="padding: 20px;"><button onclick="newChat()" style="background: rgba(255,255,255,0.1); width: 100%;">+ New Diagnostic</button></div>
        </div>

        <div class="main-content">
            <div id="messages" class="messages-container">
                <div class="ai-msg msg">Welcome back. Upload a photo or describe the issue to start the diagnostic.</div>
            </div>

            <div class="input-area">
                <div class="input-container">
                    <textarea id="userInput" rows="2" placeholder="Ask about the car..."></textarea>
                    <div class="controls">
                        <input type="file" id="imageInput" accept="image/*" style="font-size: 0.8rem;">
                        <button onclick="sendRequest()">Send Message</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
        let currentHistory = []; // Stores the current active chat

        // 1. Load History from Browser on Startup
        window.onload = () => {
            const saved = JSON.parse(localStorage.getItem('fixit_history') || '[]');
            const list = document.getElementById('chatList');
            saved.forEach((chat, index) => {
                const item = document.createElement('div');
                item.className = 'chat-item';
                item.innerText = chat.title || `Diagnostic ${index + 1}`;
                item.onclick = () => loadChat(index);
                list.appendChild(item);
            });
        };

        async function sendRequest() {
            const textInput = document.getElementById('userInput');
            const fileInput = document.getElementById('imageInput');
            const messages = document.getElementById('messages');
            
            const prompt = textInput.value;
            const file = fileInput.files[0];
            if (!prompt && !file) return;

            // Add User Message to UI
            const userDiv = document.createElement('div');
            userDiv.className = 'msg user-msg';
            userDiv.innerText = prompt || "Sent an image";
            messages.appendChild(userDiv);
            textInput.value = "";

            // Prepare AI Response Placeholder
            const aiDiv = document.createElement('div');
            aiDiv.className = 'msg ai-msg';
            aiDiv.innerText = "Analyzing...";
            messages.appendChild(aiDiv);
            messages.scrollTop = messages.scrollHeight;

            const formData = new FormData();
            if (file) formData.append("image", file);
            formData.append("prompt", prompt);
            
            // ✅ SEND THE HISTORY SO IT REMEMBERS
            formData.append("history", JSON.stringify(currentHistory));

            try {
                const response = await fetch(`${window.location.origin}/analyze`, {
                    method: "POST",
                    body: formData
                });
                const data = await response.json();
                
                aiDiv.innerText = data.result;
                
                // Update History Memory
                currentHistory.push({ role: "user", text: prompt });
                currentHistory.push({ role: "model", text: data.result });
                
                // Auto-Save to Sidebar (Simplified)
                saveToSidebar(prompt || "Visual Analysis");

            } catch (err) {
                aiDiv.innerText = "Error connecting to server.";
            }
        }

        function saveToSidebar(title) {
            const saved = JSON.parse(localStorage.getItem('fixit_history') || '[]');
            saved.unshift({ title: title, history: currentHistory });
            localStorage.setItem('fixit_history', JSON.stringify(saved.slice(0, 10))); // Keep last 10
        }

        function newChat() {
            currentHistory = [];
            document.getElementById('messages').innerHTML = '<div class="ai-msg msg">New Diagnostic started.</div>';
        }
        </script>
    </body>
    </html>
    """

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        user_prompt = request.form.get('prompt', '')
        history_json = request.form.get('history', '[]')
        import json
        past_messages = json.loads(history_json)

        # Initialize the list of content for the AI
        contents = []
        
        # 1. Add History (This is how it remembers)
        for msg in past_messages:
            contents.append(msg['text'])

        # 2. Add current image if uploaded
        if 'image' in request.files:
            file = request.files['image']
            img = PIL.Image.open(io.BytesIO(file.read()))
            contents.append(img)
        
        # 3. Add current prompt
        contents.append(f"Master Mechanic Instruction: Assist with this specific car query. {user_prompt}")

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=contents
        )
        
        return jsonify({"result": response.text})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
