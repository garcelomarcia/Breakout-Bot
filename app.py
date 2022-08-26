import json, config
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
import pandas as pd
import time

app = Flask(__name__)
df = pd.read_excel("Book3.xlsx")
symbols_list = df['Symbol'].to_list()
symbols_list = [i.split("PERP")[0] for i in symbols_list]
df = df.set_index('Symbol')
client = Client(config.API_KEY, config.API_SECRET)
table = {}
exchange_info = client.futures_exchange_info().get('symbols')
for key in exchange_info:
    if key["symbol"] in symbols_list:
        table[key["symbol"]] = {}
        table[key["symbol"]]['Price Decimals'] = int(len(key['filters'][0]['tickSize'])-3)
        if int(len(key['filters'][1]['stepSize'])) >=3:
            table[key["symbol"]]['Order Decimals'] = int(len(key['filters'][1]['stepSize'])-2)
        else:
            table[key["symbol"]]['Order Decimals'] = 0   

def entry_order(side, quantity,symbol,price, opp_side, tp,sl):
    if client.futures_get_open_orders(symbol=symbol):
        print("Cancelling previous order")
        client.futures_cancel_all_open_orders(symbol=symbol)
        
    try:    
        print(f"sending order: Stop Market Order {side}{quantity}{symbol} @{price}")
        order = client.futures_create_order(symbol=symbol, side=side, type='STOP_MARKET', quantity=quantity, stopPrice=price)
    except Exception as e:
        print("an exception occured - {}".format(e))
        print("sending order at market price")
        order = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
    order_id = client.futures_get_open_orders(symbol=symbol)[0]['orderId']
    open_order = True
    while open_order == True:            
        if client.futures_get_open_orders(symbol=symbol):
            time.sleep(0.5)
            open_order = True
        else:
            open_order = False
            break
    last_order_id = client.futures_get_all_orders(symbol=symbol)[-1]['orderId']
    last_order_status = client.futures_get_all_orders(symbol=symbol)[-1]['status']
    if order_id == last_order_id and last_order_status == "FILLED":
        print(f"sending order: Take Profit Order {opp_side}{quantity}{symbol} @{tp}")
        tp_order = client.futures_create_order(symbol=symbol, side=opp_side, type='LIMIT', quantity=quantity, price=tp, reduceOnly=True, timeInForce="GTC")
        print(f"sending order: Stop Loss {opp_side}{quantity}{symbol} @{sl}")
        sl_order = client.futures_create_order(symbol=symbol, side=opp_side, type='STOP_MARKET', quantity=quantity, stopPrice=sl, reduceOnly=True, timeInForce="GTC")
    elif order_id == last_order_id and last_order_status == "CANCELED":
        print("order canceled")
        return False  
           
    return order,tp_order,sl_order

@app.route("/webhook", methods=['POST'])
def webhook():
    data = json.loads(request.data)
    if data['passphrase'] != config.WEBHOOK_PASSPHRASE:
        return {
            "code": "error",
            "message": "Invalid passhprase"
        }
    acc_balance = client.futures_account_balance()
    for check_balance in acc_balance:
        if check_balance["asset"] == "USDT":
            usdt_balance = float(check_balance["balance"])
    symbol = data['ticker'].upper()
    quantity_round = table[f"{symbol}"]['Order Decimals']
    price_round = table[f"{symbol}"]['Price Decimals']
    side = data['order_action'].upper()
    rank = float(df.at[symbol+"PERP","Rank"])
    price = float(data['order_price'])
    quantity = round((usdt_balance*rank)/price,quantity_round)    
    sl = float(data['sl'])
    tp = float(data['tp'])
    if side == "BUY":
        opp_side = "SELL"
    else:
        opp_side = "BUY"
    
    new_order = entry_order(side, quantity,symbol,price, opp_side, tp,sl)
    if new_order:
        return {
            "code": "success",
            "message": "stop order created"
        }
    else:
        
        return {
            "code": "error",
            "message": "stop order failed"
        }
        
        
        
@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)