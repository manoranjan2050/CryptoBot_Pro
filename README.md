# ₿ CryptoBot Pro — Trading Dashboard

A full-stack algorithmic trading dashboard with AI chat advisor, real-time market data, Telegram & email alerts.

---

## Features

| Feature | Description |
|---|---|
| 🔐 Login / Register | JWT auth, bcrypt passwords, SQLite storage |
| 📊 Dashboard | Live BTC/ETH/BNB prices, candlestick chart, portfolio |
| 🤖 Bot Control | Start/stop bot, configure EMA+RSI strategy |
| 📈 Trade History | All trades, win rate, PnL stats |
| 🔔 Alerts | In-app + Telegram + Email notifications |
| 💬 AI Advisor | Claude-powered trading chat assistant |
| ⚙️ Settings | Binance API keys, Telegram bot, email SMTP |

---

## Quick Start

### Option 1 — One command
```bash
chmod +x start.sh && ./start.sh
```

### Option 2 — Manual

**Backend (Python):**
```bash
cd backend
pip install -r requirements.txt
python main.py
# Runs on http://localhost:8000
```

**Frontend (React):**
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

**Demo login:** `demo` / `demo123`

---

## Setup Guide

### 1. Binance API Keys
1. Go to Binance → Account → API Management
2. Create new key with **Spot & Margin trading** permissions
3. ❌ Do NOT enable withdrawal permissions
4. Paste in Settings → Binance API tab

### 2. Telegram Alerts
1. Message [@BotFather](https://t.me/botfather) → `/newbot`
2. Copy the bot token
3. Message [@userinfobot](https://t.me/userinfobot) to get your Chat ID
4. Paste both in Settings → Telegram tab
5. Click "Send Test Message" to verify

### 3. Email Alerts (Gmail)
1. Enable 2FA on Gmail
2. Go to Google Account → Security → App Passwords
3. Generate an app password for "Mail"
4. In Settings → Email: use `smtp.gmail.com`, port `587`
5. Username = your Gmail, Password = app password

---

## Strategy: EMA Crossover + RSI Filter

```
Signal: BUY when EMA(21) crosses above EMA(55) AND RSI between 45-65
Signal: SELL when EMA crosses back OR RSI > 75
Stop Loss: 1.5% below entry (configurable)
Take Profit: 3.0% above entry (configurable)

Spot: ETH/BNB grid bot for passive income
Futures: BTC/ETH trend following at 3-5x leverage
```

---

## File Structure

```
trading-bot/
├── backend/
│   ├── main.py          # FastAPI backend
│   ├── requirements.txt
│   └── cryptobot.db     # Auto-created SQLite database
├── frontend/
│   ├── src/
│   │   ├── App.jsx      # Full React dashboard
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── start.sh             # One-command launcher
```

---

## Adding Real Trading (Next Steps)

To connect real Binance trading, add to `backend/main.py`:

```bash
pip install python-binance
```

```python
from binance.client import Client

def get_binance_client(user_id):
    conn = get_db()
    s = conn.execute("SELECT * FROM settings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return Client(s["binance_api_key"], s["binance_secret_key"])

# Place real order
def place_order(user_id, symbol, side, quantity):
    client = get_binance_client(user_id)
    order = client.create_order(
        symbol=symbol,
        side=side,  # "BUY" or "SELL"
        type="MARKET",
        quantity=quantity
    )
    return order
```

---

## ⚠️ Risk Warning

Algorithmic trading involves substantial risk. Always:
- Test on Binance **testnet** first: https://testnet.binance.vision
- Start with small amounts
- Monitor the bot regularly
- Never trade more than you can afford to lose
