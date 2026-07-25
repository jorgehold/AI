from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import subprocess, json, urllib.request, sys, os, tempfile
import warnings; warnings.filterwarnings("ignore")

app = Flask(__name__)
CORS(app, origins="*", methods=["GET","POST","OPTIONS"], allow_headers=["Content-Type"])

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = "llama3.2:3b"
JAI_PY = os.path.expanduser("~/AI/jai/jai.py")

@app.route('/')
def index():
    return send_file(os.path.expanduser('~/AI/jai/chat.html'))

@app.route('/chat', methods=['POST'])
def chat():
    msg = request.json.get('message','')
    prompt = f"Eres JAI, asistente personal de Jorge. Respondes en espanol, directo y util. Maximo 3 oraciones cortas.\n\nJorge: {msg}\nJAI:"
    payload = json.dumps({"model":MODELO,"prompt":prompt,"stream":False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL,data=payload,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=120) as r:
            data = json.loads(r.read())
            return jsonify({"reply": data.get("response","").strip()})
    except Exception as e:
        return jsonify({"reply": f"Error: {e}"})

@app.route('/speak', methods=['POST'])
def speak():
    text = request.json.get('text','')
    subprocess.Popen(["say","-v","Monica",text[:300]])
    return jsonify({"ok":True})

@app.route('/listen', methods=['POST'])
def listen():
    audio = tempfile.mktemp(suffix=".wav")
    try:
        subprocess.run(["rec","-r","16000","-c","1",audio,"trim","0","5"],
            check=True,capture_output=True,timeout=10)
        import whisper
        model = whisper.load_model("tiny")
        result = model.transcribe(audio,language="es")
        os.unlink(audio)
        return jsonify({"text": result["text"].strip()})
    except Exception as e:
        return jsonify({"text":"","error":str(e)})

if __name__ == '__main__':
    print("JAI Chat en: http://127.0.0.1:5001")
    app.run(host='127.0.0.1',port=5001,debug=False)
