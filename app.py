import os
import io
import PIL.Image
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai 

app = Flask(__name__)
CORS(app)

# ✅ SECURE: Fetches from Render's Environment Variables
# If running locally, it will look for a system variable named GOOGLE_API_KEY
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
                margin: 0; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                min-height: 100vh;
                background: radial-gradient(circle at top left, #1e1b4b, #0f172a, #2e1065);
                color: #f8fafc;
            }
            .container { 
                background: var(--glass);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                padding: 40px; 
                border-radius: 28px; 
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); 
                border: 1px solid rgba(255, 255, 255, 0.1);
                max-width: 600px;
                width: 90%;
                text-align: center;
            }
            h1 { 
                font-size: 2.8rem; 
                margin-bottom: 8px; 
                background: linear-gradient(to right, var(--accent-blue), var(--accent-purple)); 
                -webkit-background-clip: text; 
                -webkit-text-fill-color: transparent;
                letter-spacing: -1px;
            }
            .subtitle { color: #94a3b8; margin-bottom: 30px; font-weight: 300; }
            
            .upload-box {
                background: rgba(0,0,0,0.2);
                border: 2px dashed rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 30px;
                margin-bottom: 25px;
                transition: all 0.3s ease;
            }
            .upload-box:hover { border-color: var(--accent-blue); background: rgba(56, 189, 248, 0.05); }

            #output { 
                text-align: left; 
                white-space: pre-wrap; 
                background: rgba(15, 23, 42, 0.6); 
                padding: 24px; 
                border-radius: 16px; 
                margin-top: 25px; 
                border: 1px solid rgba(168, 85, 247, 0.3); 
                min-height: 120px;
                line-height: 1.7;
                color: #e2e8f0;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 0.95rem;
                box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06);
            }

            button { 
                background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple)); 
                color: white; 
                border: none; 
                padding: 16px 32px; 
                border-radius: 12px; 
                cursor: pointer; 
                font-weight: 700; 
                font-size: 1.1rem;
                transition: all 0.3s ease;
                width: 100%;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            button:hover { 
                transform: translateY(-3px); 
                box-shadow: 0 10px 20px rgba(168, 85, 247, 0.4);
                filter: brightness(1.1);
            }
            
            input[type="file"]::file-selector-button {
                background: rgba(255,255,255,0.1);
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 8px;
                margin-right: 15px;
                cursor: pointer;
            }
            
            .cursor { display: inline-block; width: 10px; height: 1.2rem; background: var(--accent-blue); margin-left: 5px; animation: blink 1s infinite; vertical-align: middle; }
            @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>FixIt AI 🛠️</h1>
            <p class="subtitle">AI-Powered Mechanical Diagnostics</p>
            
            <div class="upload-box">
                <input type="file" id="imageInput" accept="image/*">
            </div>

            <button onclick="processVehicle()">Run Diagnostics</button>
            <div id="output">Waiting for vehicle scan...</div>
        </div>

        <script>
        // TYPEWRITER EFFECT
        function streamText(element, text) {
            element.innerHTML = "";
            let i = 0;
            const speed = 20; // Lower is faster
            
            const cursor = document.createElement("span");
            cursor.className = "cursor";
            
            function type() {
                if (i < text.length) {
                    element.innerHTML = text.substring(0, i + 1);
                    element.appendChild(cursor);
                    i++;
                    setTimeout(type, speed);
                } else {
                    cursor.remove();
                }
            }
            type();
        }

        async function processVehicle() {
            const fileInput = document.getElementById('imageInput');
            const file = fileInput.files[0];
            const output = document.getElementById('output');
            
            if (!file) { alert("Please upload a vehicle image first."); return; }
            
            output.innerHTML = "📡 <strong>Initializing Neural Link...</strong> Analyzing image data...";
            
            const formData = new FormData();
            formData.append("image", file);

            try {
                // Corrected: Uses relative path so it works on Render AND Local
                const response = await fetch(`${window.location.origin}/analyze`, {
                    method: "POST",
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.result) {
                    streamText(output, data.result);
                } else {
                    output.innerText = "🚨 System Error: " + data.error;
                }
            } catch (err) {
                output.innerText = "❌ Connection Failed. Ensure the backend is live.";
            }
        }
        </script>
    </body>
    </html>
    """

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "Missing image file"}), 400
            
        file = request.files['image']
        image_bytes = file.read()
        
        # We use Pillow to open the image bytes
        img = PIL.Image.open(io.BytesIO(image_bytes))

        # Model 2.5-flash-lite is the way to go for speed
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
                "You are FixIt AI, a master mechanic. Analyze this car image and return: Issue, Confidence, Severity, Estimated Cost, DIY Difficulty, and Explanation.",
                img
            ]
        )
        
        return jsonify({"result": response.text})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    # PORT is assigned by Render automatically
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
