import ccxt
import os
import time
from flask import Flask

# Flask server for UptimeRobot pinging
app = Flask(__name__)
@app.route('/')
def home():
    return "👀 ETH Bot Running..."
import threading
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=3000)).start()

# === CONFIG ===
PAIR = 'ETH/CAD'
BUY_TRIGGER_DROP = 0.02   # 2% drop from rolling high triggers buy
SELL_TARGET_GAIN = 0.025  # Sell at +2.5% gain
MIN_CAD = 50              # Minimum balance to attempt a buy

API_KEY = os.environ['API_KEY']
API_SECRET = os.environ['API_SECRET']

# === Initialize Exchange ===
exchange = ccxt.kraken({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True
})

def get_price(): return exchange.fetch_ticker(PAIR)['last']
def get_cad_balance(): return exchange.fetch_balance()['CAD']['free']
def get_eth_balance(): return exchange.fetch_balance()['ETH']['free']

def place_buy(cad_amount):
    price = get_price()
    eth_amount = round(cad_amount / price, 6)
    print(f"🟢 Buying {eth_amount} ETH at ${price:.2f} CAD")
    exchange.create_market_buy_order(PAIR, eth_amount)
    return price, eth_amount

def place_sell(eth_amount):
    print(f"🚀 Selling {eth_amount} ETH")
    exchange.create_market_sell_order(PAIR, eth_amount)

# === MAIN LOGIC ===
print("🔁 ETH bot starting up...")
rolling_high = get_price()
in_trade = False
entry_price, eth_amount = 0, 0
first_run = True

while True:
    try:
        current_price = get_price()
        cad_balance = get_cad_balance()
        eth_balance = get_eth_balance()
        rolling_high = max(rolling_high, current_price)

        # FIRST BUY (instantly if CAD available)
        if first_run and cad_balance >= MIN_CAD:
            entry_price, eth_amount = place_buy(cad_balance)
            in_trade = True
            first_run = False
            continue

        # DIP BUY (after first run)
        if not in_trade and cad_balance >= MIN_CAD:
            drop = (rolling_high - current_price) / rolling_high
            print(f"💹 Price: ${current_price:.2f} | Drop: {drop:.2%} from high ${rolling_high:.2f}")
            if drop >= BUY_TRIGGER_DROP:
                entry_price, eth_amount = place_buy(cad_balance)
                in_trade = True

        # SELL AT TARGET
        if in_trade:
            gain = (current_price - entry_price) / entry_price
            print(f"📈 Gain: {gain:.2%} | Target: {SELL_TARGET_GAIN:.2%}")
            if gain >= SELL_TARGET_GAIN:
                eth_amount = get_eth_balance()
                place_sell(eth_amount)
                in_trade = False
                rolling_high = current_price  # reset high

        time.sleep(60)

    except Exception as e:
        print(f"⚠️ Error: {e}")
        time.sleep(60)
