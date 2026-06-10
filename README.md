<div align="center">

# ₿ CryptoBot Pro

**Full-Stack Algorithmic Crypto Trading Dashboard**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38BDF8?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

*Paper trade → backtest → go live — all in one beautiful dashboard*

---

[Features](#-features) · [Quick Start](#-quick-start) · [Strategy](#-trading-strategy) · [Setup Guide](#-setup-guide) · [Screenshots](#-screenshots) · [Security](#-security)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 📊 Dashboard
- Live BTC / ETH / BNB / SOL prices
- Candlestick chart with **EMA overlay** (fast + slow)
- **Fear & Greed Index** widget (7-day history)
- Portfolio balance & PnL snapshot
- Risk controls at a glance

</td>
<td width="50%">

### 🤖 Auto-Bot
- EMA Crossover + RSI strategy
- **Trailing stop-loss** — locks in profits
- Auto-compound profits back to balance
- Daily loss limit (bot halts automatically)
- Runs every 60 seconds in background

</td>
</tr>
<tr>
<td>

### 📈 Analytics
- **Cumulative PnL line chart** with daily dots
- Weekly / Monthly / All-time summary cards
- Win/loss streak tracker
- Best & worst single trade display
- CSV export for tax / accounting

</td>
<td>

### 🔔 Alerts & Notifications
- In-app notification feed
- **Price alerts** — above/below target
- **Telegram bot** integration
- **Email (SMTP)** alerts
- Daily summary report to Telegram

</td>
</tr>
<tr>
<td>

### 💬 AI Advisor
- Powered by **Claude (Anthropic)**
- Context-aware: knows your current mode
- Quick-suggest buttons for common questions
- Bring your own Anthropic API key
- Routed securely through the backend

</td>
<td>

### 🔐 Auth & Security
- JWT authentication (7-day tokens)
- bcrypt password hashing
- Demo mode — no real money, ever
- Live mode gated behind Binance API key
- API keys masked in UI & logs

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Option A — One command (Linux / Mac)

```bash
git clone https://github.com/manoranjan2050/CryptoBot_Pro.git
cd CryptoBot_Pro
chmod +x start.sh && ./start.sh
```

### Option B — Windows one-click

```
Double-click START_DASHBOARD.bat
```

### Option C — Manual

**Backend**
```bash
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000
```

**Frontend** (new terminal)
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

**Demo login** → username: `demo` · password: `demo123`

---

## 🏗️ Architecture

```
CryptoBot_Pro/
├── backend/
│   ├── main.py              # FastAPI — all API routes (719 lines)
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Full React dashboard (single-file)
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore               # Protects secrets, DB, node_modules
├── START_DASHBOARD.bat      # Windows launcher
└── start.sh                 # Linux/Mac launcher
```

**Data flow**

```
Browser (React) ──► FastAPI (port 8000) ──► Binance API (live prices)
                                        ──► Anthropic API (AI chat)
                                        ──► Telegram API (alerts)
                                        ──► SQLite (users, trades, settings)
```

---

## 📐 Trading Strategy

### EMA Crossover + RSI Filter

```
┌─────────────────────────────────────────────────────┐
│  BUY  when EMA(21) crosses ABOVE EMA(55)            │
│         AND RSI is between 45 – 65                  │
│                                                     │
│  SELL when EMA(21) crosses BELOW EMA(55)            │
│         OR RSI exceeds 75                           │
│                                                     │
│  Stop Loss  : 1.5% below entry  (configurable)      │
│  Take Profit: 3.0% above entry  (configurable)      │
│  Trailing   : locks stop at high-water mark         │
└─────────────────────────────────────────────────────┘
```

All parameters are fully configurable in the **Bot Control** page.

---

## ⚙️ Setup Guide

### 1 · Binance API Keys

> Required only for **Live mode** — Demo mode works without any keys.

1. Log into Binance → **Account** → **API Management** → **Create API**
2. Enable **Spot & Margin Trading** permissions only
3. ❌ **Never** enable withdrawal permissions on bot keys
4. Optionally whitelist your server IP
5. Paste both keys in **Settings → Binance API**

### 2 · AI Advisor (Claude)

1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Create an API key under **API Keys**
3. Paste it in **Settings → AI Advisor**

### 3 · Telegram Alerts

1. Message **[@BotFather](https://t.me/botfather)** → `/newbot` → copy token
2. Message **[@userinfobot](https://t.me/userinfobot)** → copy your Chat ID
3. Paste both in **Settings → Telegram** → toggle alerts on
4. Click **Test Telegram** to verify

### 4 · Email Alerts (Gmail)

1. Enable 2FA on your Gmail account
2. **Google Account → Security → App Passwords** → generate one for "Mail"
3. In **Settings → Email**: host `smtp.gmail.com`, port `587`
4. Username = your Gmail address, password = the app password

---

## 🗄️ Database Schema

| Table | Purpose |
|---|---|
| `users` | Login credentials (bcrypt hashed) |
| `settings` | Per-user API keys, Telegram, email config |
| `bot_config` | Strategy params, EMA/RSI settings, mode |
| `funds` | Demo/live balances, risk limits, compound settings |
| `trades` | All open & closed trades with PnL |
| `alerts` | In-app notification feed |
| `price_alerts` | User-defined price trigger rules |
| `chat_messages` | AI conversation history |

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Login → JWT token |
| POST | `/api/auth/register` | Register new user |
| GET | `/api/market/overview` | Live prices for BTC/ETH/BNB/SOL |
| GET | `/api/market/klines/{symbol}` | OHLCV candlestick data |
| GET | `/api/market/ema/{symbol}` | EMA fast & slow series |
| GET | `/api/market/fear-greed` | Fear & Greed Index (7 days) |
| POST | `/api/demo/trade` | Place a paper trade |
| POST | `/api/demo/trade/{id}/close` | Close open paper trade |
| GET | `/api/bot/config` | Get bot strategy settings |
| PUT | `/api/bot/config` | Update bot settings |
| POST | `/api/bot/start` | Start the auto-bot |
| POST | `/api/bot/stop` | Stop the auto-bot |
| GET | `/api/analytics/pnl-history` | Daily PnL + cumulative |
| GET | `/api/analytics/summary` | Week / month / all-time stats |
| GET | `/api/analytics/streak` | Win/loss streak data |
| GET | `/api/trades/export` | Download trades as CSV |
| POST | `/api/chat` | AI advisor (Claude proxy) |
| GET | `/api/price-alerts` | List price alerts |
| POST | `/api/price-alerts` | Create price alert |

Full interactive docs at **[http://localhost:8000/docs](http://localhost:8000/docs)** when running.

---

## 🔒 Security

- **All API keys** are stored in SQLite, masked in API responses, and never logged
- **Secrets** (`.env`, `*.db`, `*.key`, `*.pem`) are excluded by `.gitignore`
- **JWT tokens** expire after 7 days; rotation requires re-login
- **Live mode** requires explicit confirmation + Binance keys before activating
- **Withdrawal permissions** are intentionally unsupported — trading only

> ⚠️ Never commit your `.env` file or share your Binance secret key. The bot only needs **Spot Trading** permission — never withdrawal.

---

## 🔮 Roadmap

- [ ] Backtesting engine — replay historical data through strategy
- [ ] Portfolio tracker — multi-coin holdings with pie chart
- [ ] Order book depth chart
- [ ] 2FA / session timeout
- [ ] Crypto news feed
- [ ] Tax report (annual PnL per coin)

---

## ⚠️ Risk Disclaimer

> Algorithmic trading involves **substantial financial risk**.
>
> - Always test on **Binance Testnet** first: [testnet.binance.vision](https://testnet.binance.vision)
> - Start with **small amounts** you can afford to lose entirely
> - Monitor the bot regularly — markets can move fast
> - Past performance in demo mode does **not** guarantee live results
> - The authors accept no responsibility for financial losses

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ using FastAPI + React + Claude AI

**[⬆ Back to top](#-cryptobot-pro)**

</div>
