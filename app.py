import json, config
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
import pandas as pd
import time

app = Flask(__name__)
client = Client(config.API_KEY, config.API_SECRET)
table = {}
exchange_info = client.futures_exchange_info().get('symbols')
symbols_list = ['BTCUSDT', 'ETHUSDT']
for key in exchange_info:
    if key["symbol"] in symbols_list:
        table[key["symbol"]] = {}
        table[key["symbol"]]['Price Decimals'] = int(len(key['filters'][0]['tickSize'])-3)
        if int(len(key['filters'][1]['stepSize'])) >=3:
            table[key["symbol"]]['Order Decimals'] = int(len(key['filters'][1]['stepSize'])-2)
        else:
            table[key["symbol"]]['Order Decimals'] = 0


def entry_order(side, quantity,symbol,price, opp_side, tp,sl):
    if float(client.futures_position_information(symbol=symbol)[0]['positionAmt']) == 0.0:
        client.futures_cancel_all_open_orders(symbol=symbol)
    try:    
        print(f"sending order: Stop Market Order {side}{quantity}{symbol} @{price}")
        order = client.futures_create_order(symbol=symbol, side=side, type='STOP_MARKET', quantity=quantity, stopPrice=price)
        time.sleep(0.5)        
        order_executed = False
        while order_executed == False:
            if float(client.futures_position_information(symbol=symbol)[0]['positionAmt']) != 0.0:            
                try:
                    print(f"sending order: Take Profit Order {opp_side}{quantity}{symbol} @{tp}")
                    tp_order = client.futures_create_order(symbol=symbol, side=opp_side, type='LIMIT', quantity=quantity, price=tp, reduceOnly=True, timeInForce="GTC")
                    print(f"sending order: Stop Loss {opp_side}{quantity}{symbol} @{sl}")
                    sl_order = client.futures_create_order(symbol=symbol, side=opp_side, type='STOP_MARKET', quantity=quantity, stopPrice=sl, reduceOnly=True, timeInForce="GTC")
                except BinanceAPIException as err:
                    if str(err.message) == "Order would immediately trigger.":
                        print(f"Exiting trade at Market Price")
                        client.futures_create_order(symbol=symbol, side=opp_side, type='MARKET', quantity=quantity, reduceOnly=True)
                        client.futures_cancel_all_open_orders(symbol=symbol)
                    return False
                order_executed = True
                break
            else:
                order_executed = False
    except BinanceAPIException as e:
        
        # print("an exception occured - {}".format(e))    
        if not client.futures_get_open_orders(symbol=symbol) and float(client.futures_position_information(symbol=symbol)[0]['positionAmt']) == 0.0 and str(e.message) == "Order would immediately trigger.":                        
            print("sending order at market price")
            order = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
            time.sleep(0.5)
            try:
                print(f"sending order: Take Profit Order {opp_side}{quantity}{symbol} @{tp}")
                tp_order = client.futures_create_order(symbol=symbol, side=opp_side, type='LIMIT', quantity=quantity, price=tp, reduceOnly=True, timeInForce="GTC")
                print(f"sending order: Stop Loss {opp_side}{quantity}{symbol} @{sl}")
                sl_order = client.futures_create_order(symbol=symbol, side=opp_side, type='STOP_MARKET', quantity=quantity, stopPrice=sl, reduceOnly=True, timeInForce="GTC")
            except BinanceAPIException as err:
                if str(err.message) == "Order would immediately trigger.":
                    print(f"Exiting trade at Market Price")
                    client.futures_create_order(symbol=symbol, side=opp_side, type='MARKET', quantity=quantity, reduceOnly=True)
                    client.futures_cancel_all_open_orders(symbol=symbol)
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
    symbol = data['ticker'].upper()
    if client.futures_get_open_orders(symbol=symbol) and client.futures_get_open_orders(symbol=symbol)[0]['reduceOnly'] == "False":
        print("Cancelling previous order")
        client.futures_cancel_all_open_orders(symbol=symbol)
    acc_balance = client.futures_account_balance()
    for check_balance in acc_balance:
        if check_balance["asset"] == "USDT":
            usdt_balance = float(check_balance["balance"])    
    quantity_round = table[f"{symbol}"]['Order Decimals']
    side = data['order_action'].upper()
    price = float(data['order_price'])
    quantity = round((usdt_balance)/price,quantity_round)    
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