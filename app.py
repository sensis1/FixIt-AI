import os
import io
import PIL.Image
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai 

app = Flask(__name__)
CORS(app)

# ✅ SECURE: Fetches from Render's Environment Variables
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
                --glass: rgba(255, 255, 255, 0.07);
            }
            body { 
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                margin: 0; display: flex; align-items: center; justify-content: center; 
                min-height: 100vh;
                background: radial-gradient(circle at top left, #1e1b4b, #0f172a, #2e1065);
                color: #f8fafc;
            }
            .container { 
                background: var(--glass);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                padding: 40px; border-radius: 28px; 
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); 
                border: 1px solid rgba(255, 255, 255, 0.1);
                max-width: 600px; width: 90%; text-align: center;
            }
            h1 { 
                font-size: 2.8rem; margin-bottom: 8px; 
                background: linear-gradient(to right, var(--accent-blue), var(--accent-purple)); 
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                letter-spacing: -1px;
            }
            .subtitle { color: #94a3b8; margin-bottom: 30px; font-weight: 300; }
            
            .input-section {
                background: rgba(0,0,0,0.2);
                border-radius: 16px;
                padding: 20px;
                margin-bottom: 25px;
                border: 1px solid rgba(255,255,255,0.05);
            }

            textarea {
                width: 100%;
                background: rgba(15, 23, 42, 0.5);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px;
                color: white;
                padding: 12px;
                margin-top: 15px;
                font-family: inherit;
                resize: vertical;
                box-sizing: border-box;
            }
            textarea:focus { outline: 2px solid var(--accent-blue); border-color: transparent; }

            #output { 
                text-align: left; white-space: pre-wrap; 
                background: rgba(15, 23, 42, 0.6); 
                padding: 24px; border-radius: 16px; margin-top: 25px; 
                border: 1px solid rgba(168, 85, 247, 0.3); 
                min-height: 120px; line-height: 1.7; color: #e2e8f0;
                font-family: 'Consolas', 'Monaco', monospace; font-size: 0.95rem;
            }

            button { 
                background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple)); 
                color: white; border: none; padding: 16px 32px; border-radius: 12px; 
                cursor: pointer; font-weight: 700; font-size: 1.1rem;
                transition: all 0.3s ease; width: 100%; text-transform: uppercase;
            }
            button:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(168, 85, 247, 0.4); }
            
            .cursor { display: inline-block; width: 10px; height: 1.2rem; background: var(--accent-blue); margin-left: 5px; animation: blink 1s infinite; vertical-align: middle; }
            @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>FixIt AI 🛠️</h1>
            <p class="subtitle">AI-Powered Mechanical Diagnostics</p>
            
            <div class="input-section">
                <input type="file" id="imageInput" accept="image/*">
                <textarea id="textInput" rows="3" placeholder="Describe the symptoms or ask a specific question..."></textarea>
            </div>

            <button onclick="processRequest()">Run Diagnostics</button>
            <div id="output">Waiting for system input...</div>
        </div>

        <script>
        function streamText(element, text) {
            element.innerHTML = "";
            let i = 0;
            const cursor = document.createElement("span");
            cursor.className = "cursor";
            function type() {
                if (i < text.length) {
                    element.innerHTML = text.substring(0, i + 1);
                    element.appendChild(cursor);
                    i++;
                    setTimeout(type, 15);
                } else { cursor.remove(); }
            }
            type();
        }

        async function processRequest() {
            const fileInput = document.getElementById('imageInput');
            const textInput = document.getElementById('textInput');
            const output = document.getElementById('output');
            
            const file = fileInput.files[0];
            const userText = textInput.value;

            if (!file && !userText) { alert("Please provide an image or a description!"); return; }
            
            output.innerHTML = "📡 <strong>Scanning...</strong> Processing mechanical data...";
            
            const formData = new FormData();
            if (file) formData.append("image", file);
            formData.append("prompt", userText);

            try {
                const response = await fetch(`${window.location.origin}/analyze`, {
                    method: "POST",
                    body: formData
                });
                
                const data = await response.json();
                if (data.result) { streamText(output, data.result); }
                else { output.innerText = "🚨 Error: " + data.error; }
            } catch (err) { output.innerText = "❌ Connection Failed."; }
        }
        </script>
    </body>
    </html>
    """

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        user_prompt = request.form.get('prompt', '')
        contents = []

        # 1. System Identity (Instruction)
        base_instruction = "You are FixIt AI, a master mechanic. Analyze the input and return: Issue, Confidence, Severity, Estimated Cost, DIY Difficulty, and Explanation."
        
        # 2. Add image if provided
        if 'image' in request.files:
            file = request.files['image']
            img = PIL.Image.open(io.BytesIO(file.read()))
            contents.append(img)
        
        # 3. Add text if provided (combining with instruction)
        full_prompt = f"{base_instruction}\n\nUser Question/Context: {user_prompt}"
        contents.append(full_prompt)

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
