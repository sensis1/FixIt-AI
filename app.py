import os
import io
import PIL.Image
from flask import Flask, request, jsonify
from flask_cors import CORS
# This is the new 2026 import style
from google import genai 

app = Flask(__name__)
CORS(app)

# 🔑 PASTE YOUR KEY FROM https://aistudio.google.com/
client = genai.Client(api_key="")

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FixIt AI</title>
        <style>
            body { font-family: sans-serif; max-width: 600px; margin: 50px auto; text-align: center; background: #f0f4f8; }
            .card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            #output { text-align: left; white-space: pre-wrap; background: #fff; padding: 15px; border-radius: 8px; margin-top: 20px; border: 1px solid #d1d5db; min-height: 50px; }
            button { background: #1d4ed8; color: white; border: none; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>FixIt AI 🛠️</h1>
            <p>Upload a car photo for a master mechanic's analysis.</p>
            <input type="file" id="imageInput" accept="image/*"><br><br>
            <button onclick="upload()">Analyze My Car</button>
            <div id="output">Results will appear here...</div>
        </div>
        <script>
        async function upload() {
            const fileInput = document.getElementById('imageInput');
            const file = fileInput.files[0];
            const output = document.getElementById('output');
            if (!file) { alert("Please select an image!"); return; }
            output.innerText = "🔍 FixIt AI is inspecting the vehicle...";
            const formData = new FormData();
            formData.append("image", file);
            try {
                const response = await fetch("/analyze", {
                    method: "POST",
                    body: formData
                });
                const data = await response.json();
                output.innerText = data.result || "❌ Error: " + data.error;
            } catch (err) {
                output.innerText = "⚠️ Request failed: " + err;
            }
        }
        </script>
    </body>
    </html>
    """

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        file = request.files['image']
        image_bytes = file.read()
        img = PIL.Image.open(io.BytesIO(image_bytes))

        # gemini-2.0-flash is the fastest free model in 2026
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
    # Use port 5000 to match the JavaScript fetch call
    app.run(debug=True, port=5000)
