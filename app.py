import json, config
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
app = Flask(__name__)
import pandas as pd
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


def entry_order(side,quantity,symbol,tp,opp_side):
    try:
        print(f"sending order: Market {side}{quantity}{symbol}")
        order = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
        print(f"sending order: Limit {opp_side} {quantity} on {symbol} @{tp}")
        tp_order = client.futures_create_order(symbol=symbol, side=opp_side, type='LIMIT', quantity=quantity, price=tp,timeInForce="GTC")
        print(order)    
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False
    
    return order,tp_order

def exit_order(symbol,side):
    quantity = float(client.futures_position_information(symbol=symbol)[0].get('positionAmt'))
    if (quantity > 0) or (quantity < 0):
        order = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
        close = client.futures_cancel_all_open_orders(symbol=symbol)
    else:
        return False
        
    return order,close

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
    symbol = data['ticker'].split('PERP')[0]
    quantity_round = table[f"{symbol}"]['Order Decimals']
    price_round = table[f"{symbol}"]['Price Decimals']
    side = data['strategy']['order_action'].upper()
    prev_position = data['strategy']['prev_market_position']
    rank = float(df.at[symbol+"PERP","Rank"])
    quantity = round((usdt_balance*rank)/(data['bar']['close']),quantity_round)
    price = float(data['strategy']['order_price'])
    rr = float(df.at[symbol+"PERP","R:R"])
    if side == "BUY":
        sl = price * (1-(float(df.at[symbol+"PERP","SL %"])/100))
        tp = round((price + (price-sl) * rr),price_round)
        opp_side = "SELL"
    elif side =="SELL":
        sl = price * (1+(float(df.at[symbol+"PERP","SL %"])/100))
        tp = round((price - (sl-price) * rr),price_round)
        opp_side = "BUY"
    
    if prev_position == "flat":
        new_order = entry_order(side, quantity, symbol,tp,opp_side)
        if new_order:
            return {
                "code": "success",
                "message": "create order executed"
            }
        else:
            return {
                "code": "error",
                "message": "create order failed"
            }
    elif prev_position =="long" or "short":
        close_order = exit_order(symbol,side)  
        if close_order:
            return {
                "code": "success",
                "message": "close order executed"
            }
        else:
            return {
                "code": "error",
                "message": "close order failed"
            }
    
        
@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"
