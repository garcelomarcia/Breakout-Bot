import json, config
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
app = Flask(__name__)

client = Client(config.API_KEY, config.API_SECRET)

def order(side, quantity, symbol,order_type=ORDER_TYPE_MARKET):
    try:
        print(f"sending order {order_type}-{side}{quantity}{symbol}")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        print(order)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return True
@app.route("/webhook", methods=['POST'])
def webhook():
    data = json.loads(request.data)
    if data['passphrase'] != config.WEBHOOK_PASSPHRASE:
        return {
            "code": "error",
            "message": "Invalid passhprase"
        }
    order_response = order("BUY")
    return {
        "code": "succes",
        "message": data
    }

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debut=True)