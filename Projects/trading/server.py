from flask import Flask, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

app = Flask(__name__, template_folder='templates')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/quote')
def quote():
    hist = yf.Ticker("GC=F").history(period="2d", interval="1m")
    if hist.empty:
        return jsonify({"error": "sin datos"})
    price = round(float(hist['Close'].iloc[-1]), 2)
    prev = round(float(hist['Close'].iloc[0]), 2)
    spread = 0.40
    return jsonify({
        "price": price, "bid": round(price-spread/2,2), "ask": round(price+spread/2,2),
        "open": round(float(hist['Open'].iloc[0]),2), "prev": prev,
        "high": round(float(hist['High'].max()),2), "low": round(float(hist['Low'].min()),2),
        "vol": int(hist['Volume'].sum()), "spread": spread,
        "change": round(price-prev,2), "changePct": round((price-prev)/prev*100,3)
    })

@app.route('/candles/<tf>')
def candles(tf):
    periods = {"m1":"1d","m5":"5d","m15":"5d","m30":"60d","h1":"60d","h4":"60d","d1":"1y"}
    intervals = {"m1":"1m","m5":"5m","m15":"15m","m30":"30m","h1":"1h","h4":"1h","d1":"1d"}
    hist = yf.Ticker("GC=F").history(period=periods.get(tf,"5d"), interval=intervals.get(tf,"15m"))
    if hist.empty:
        return jsonify([])
    return jsonify([{
        "time": int(ts.timestamp()), "open": round(float(r['Open']),2),
        "high": round(float(r['High']),2), "low": round(float(r['Low']),2),
        "close": round(float(r['Close']),2), "value": int(r['Volume'])
    } for ts, r in hist.iterrows()])

if __name__ == '__main__':
    print("Abre: http://localhost:5000")
    app.run(port=5000, debug=False)
