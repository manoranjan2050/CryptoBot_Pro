from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import jwt, bcrypt, sqlite3, requests, smtplib, threading, time, io, csv, os, hmac, hashlib, json, sys, math
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Windows console defaults to cp1252 which can't encode Unicode (₿, emoji etc.)
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8', errors='replace')

app = FastAPI(title="CryptoBot Pro", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "CryptoBot Pro"}

SECRET = os.environ.get("JWT_SECRET", "cryptobot-secret-2024")
ALGO = "HS256"
security = HTTPBearer()

def get_db():
    c = sqlite3.connect("cryptobot.db", check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        binance_api_key TEXT, binance_secret_key TEXT,
        telegram_bot_token TEXT, telegram_chat_id TEXT,
        email_smtp_host TEXT, email_smtp_port INTEGER DEFAULT 587,
        email_username TEXT, email_password TEXT,
        email_alerts_enabled INTEGER DEFAULT 0,
        telegram_alerts_enabled INTEGER DEFAULT 0,
        anthropic_api_key TEXT
    );
    CREATE TABLE IF NOT EXISTS funds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        demo_balance REAL DEFAULT 10000,
        demo_initial REAL DEFAULT 10000,
        live_balance REAL DEFAULT 0,
        max_daily_loss_pct REAL DEFAULT 5.0,
        max_trade_size_pct REAL DEFAULT 10.0,
        max_open_trades INTEGER DEFAULT 3,
        daily_profit_target REAL DEFAULT 3.0,
        risk_per_trade_pct REAL DEFAULT 1.0,
        auto_compound INTEGER DEFAULT 0,
        compound_pct REAL DEFAULT 50.0,
        daily_loss_used REAL DEFAULT 0,
        daily_reset_date TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS bot_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        mode TEXT DEFAULT 'demo',
        strategy TEXT DEFAULT 'EMA_RSI',
        trading_pair TEXT DEFAULT 'BTCUSDT',
        market_type TEXT DEFAULT 'spot',
        leverage INTEGER DEFAULT 3,
        trade_amount REAL DEFAULT 100,
        ema_fast INTEGER DEFAULT 21,
        ema_slow INTEGER DEFAULT 55,
        rsi_period INTEGER DEFAULT 14,
        rsi_buy_threshold REAL DEFAULT 45,
        rsi_sell_threshold REAL DEFAULT 65,
        stop_loss_pct REAL DEFAULT 1.5,
        take_profit_pct REAL DEFAULT 3.0,
        trailing_stop_enabled INTEGER DEFAULT 0,
        auto_trade INTEGER DEFAULT 0,
        is_running INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mode TEXT DEFAULT 'demo',
        pair TEXT NOT NULL,
        side TEXT NOT NULL,
        entry_price REAL,
        exit_price REAL,
        quantity REAL,
        pnl REAL,
        pnl_pct REAL,
        status TEXT DEFAULT 'open',
        strategy TEXT,
        trailing_high REAL,
        trailing_stop_pct REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        closed_at TEXT
    );
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        message TEXT NOT NULL,
        mode TEXT DEFAULT 'demo',
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS price_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        target_price REAL NOT NULL,
        condition TEXT NOT NULL,
        is_triggered INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        pair TEXT DEFAULT 'BTCUSDT',
        timeframe TEXT DEFAULT '1h',
        strategy TEXT DEFAULT 'EMA',
        params TEXT DEFAULT '{}',
        capital_usdt REAL DEFAULT 100,
        sl_pct REAL DEFAULT 1.5,
        tp1_pct REAL DEFAULT 3.0,
        tp2_pct REAL DEFAULT 6.0,
        trailing_enabled INTEGER DEFAULT 1,
        is_running INTEGER DEFAULT 0,
        total_pnl REAL DEFAULT 0,
        trade_count INTEGER DEFAULT 0,
        win_count INTEGER DEFAULT 0,
        active_hours TEXT DEFAULT 'all',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_signal TEXT,
        last_run_at TEXT
    );
    """)
    # Migrate existing DBs
    for stmt in [
        "ALTER TABLE bot_config ADD COLUMN trailing_stop_enabled INTEGER DEFAULT 0",
        "ALTER TABLE bot_config ADD COLUMN auto_trade INTEGER DEFAULT 0",
        "ALTER TABLE trades ADD COLUMN trailing_high REAL",
        "ALTER TABLE trades ADD COLUMN trailing_stop_pct REAL",
        "ALTER TABLE settings ADD COLUMN anthropic_api_key TEXT",
        "ALTER TABLE users ADD COLUMN name TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'trader'",
        "ALTER TABLE trades ADD COLUMN take_profit_pct REAL",
        "ALTER TABLE trades ADD COLUMN order_type TEXT DEFAULT 'MARKET'",
        "ALTER TABLE trades ADD COLUMN limit_price REAL",
        "ALTER TABLE settings ADD COLUMN ai_provider TEXT DEFAULT 'anthropic'",
        "ALTER TABLE settings ADD COLUMN groq_api_key TEXT",
        "ALTER TABLE settings ADD COLUMN gemini_api_key TEXT",
        "ALTER TABLE settings ADD COLUMN openrouter_api_key TEXT",
        "ALTER TABLE settings ADD COLUMN ai_model TEXT",
        "ALTER TABLE trades ADD COLUMN notes TEXT",
        "ALTER TABLE trades ADD COLUMN tag TEXT DEFAULT 'Manual'",
        "ALTER TABLE trades ADD COLUMN bot_id INTEGER",
        "ALTER TABLE trades ADD COLUMN avg_entry_price REAL",
        "ALTER TABLE trades ADD COLUMN scale_count INTEGER DEFAULT 0",
        "ALTER TABLE trades ADD COLUMN tp2_pct REAL",
        "ALTER TABLE trades ADD COLUMN tp1_hit INTEGER DEFAULT 0",
        "ALTER TABLE trades ADD COLUMN tp2_hit INTEGER DEFAULT 0",
        "ALTER TABLE trades ADD COLUMN tp1_qty_pct REAL DEFAULT 50",
        "ALTER TABLE trades ADD COLUMN breakeven_at_pct REAL",
        "ALTER TABLE trades ADD COLUMN breakeven_activated INTEGER DEFAULT 0",
        "ALTER TABLE chat_messages ADD COLUMN provider TEXT",
    ]:
        try: c.execute(stmt)
        except: pass
    # Clean up secrets corrupted by the old save bug (masked '••••xxxx' written back to DB)
    for f in ("binance_api_key","binance_secret_key","anthropic_api_key","groq_api_key",
              "gemini_api_key","openrouter_api_key","email_password","telegram_bot_token"):
        try: c.execute(f"UPDATE settings SET {f}=NULL WHERE {f} LIKE '%••%'")
        except: pass
    c.commit()
    try:
        pw = bcrypt.hashpw(b"demo123", bcrypt.gensalt()).decode()
        c.execute("INSERT OR IGNORE INTO users (username,email,password_hash) VALUES (?,?,?)", ("demo","demo@cryptobot.pro",pw))
        c.commit()
        u = c.execute("SELECT id FROM users WHERE username='demo'").fetchone()
        if u:
            uid = u["id"]
            c.execute("INSERT OR IGNORE INTO settings (user_id) VALUES (?)", (uid,))
            c.execute("INSERT OR IGNORE INTO bot_config (user_id) VALUES (?)", (uid,))
            c.execute("INSERT OR IGNORE INTO funds (user_id) VALUES (?)", (uid,))
            c.commit()
            exist = c.execute("SELECT COUNT(*) as n FROM trades WHERE user_id=?", (uid,)).fetchone()["n"]
            if exist == 0:
                sample = [
                    (uid,'demo','BTCUSDT','BUY',42150.0,43800.0,0.005,8.25,1.96,'closed','EMA_RSI','2024-01-10 09:00','2024-01-10 14:30'),
                    (uid,'demo','ETHUSDT','BUY',2240.0,2310.0,0.1,7.0,3.12,'closed','EMA_RSI','2024-01-11 10:15','2024-01-11 16:45'),
                    (uid,'demo','BTCUSDT','SELL',44200.0,43100.0,0.004,4.4,2.49,'closed','EMA_RSI','2024-01-12 08:30','2024-01-12 12:00'),
                    (uid,'demo','BNBUSDT','BUY',310.5,298.0,0.5,-6.25,-2.01,'closed','EMA_RSI','2024-01-13 11:00','2024-01-13 15:20'),
                    (uid,'demo','ETHUSDT','BUY',2180.0,2260.0,0.08,6.4,2.94,'closed','EMA_RSI','2024-01-14 09:45','2024-01-14 17:10'),
                    (uid,'demo','SOLUSDT','BUY',95.0,103.5,1.5,12.75,8.42,'closed','EMA_RSI','2024-01-15 08:00','2024-01-15 20:00'),
                    (uid,'demo','BTCUSDT','BUY',43500.0,44800.0,0.004,5.2,2.99,'closed','EMA_RSI','2024-01-16 10:00','2024-01-16 18:00'),
                    (uid,'demo','ETHUSDT','SELL',2350.0,2280.0,0.06,4.2,2.98,'closed','EMA_RSI','2024-01-17 09:00','2024-01-17 15:00'),
                ]
                for t in sample:
                    c.execute("INSERT INTO trades (user_id,mode,pair,side,entry_price,exit_price,quantity,pnl,pnl_pct,status,strategy,created_at,closed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", t)
                c.commit()
    except Exception as e:
        print("Seed error:", e)
    c.close()

init_db()

# ── HELPERS ───────────────────────────────────────────────────────────────────
def make_token(uid, username):
    return jwt.encode({"sub":str(uid),"username":username,"exp":datetime.utcnow()+timedelta(days=7)}, SECRET, algorithm=ALGO)

def current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        p = jwt.decode(creds.credentials, SECRET, algorithms=[ALGO])
        return {"id":int(p["sub"]),"username":p["username"]}
    except:
        raise HTTPException(401, "Invalid token")

def add_alert(user_id, atype, message, mode="demo"):
    c = get_db()
    c.execute("INSERT INTO alerts (user_id,type,message,mode) VALUES (?,?,?,?)", (user_id,atype,message,mode))
    c.commit(); c.close()

def live_price(symbol):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=4)
        return float(r.json().get("price",0))
    except:
        return 0

def calc_ema(prices, period):
    if len(prices) < period: return []
    k = 2/(period+1)
    ema = [sum(prices[:period])/period]
    for p in prices[period:]:
        ema.append(p*k + ema[-1]*(1-k))
    return ema

def calc_rsi(prices, period=14):
    if len(prices) < period+1: return 50
    changes = [prices[i]-prices[i-1] for i in range(1,len(prices))]
    gains = [max(c,0) for c in changes[-period:]]
    losses = [max(-c,0) for c in changes[-period:]]
    avg_g = sum(gains)/period; avg_l = sum(losses)/period
    if avg_l == 0: return 100
    return round(100-(100/(1+(avg_g/avg_l))),2)

def calc_sma(prices, period):
    if len(prices) < period: return []
    return [sum(prices[i:i+period])/period for i in range(len(prices)-period+1)]

def calc_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow+signal: return None, None, None
    ef = calc_ema(prices, fast); es = calc_ema(prices, slow)
    diff = len(ef)-len(es)
    macd_line = [f-s for f,s in zip(ef[diff:], es)]
    if len(macd_line)<signal: return (macd_line[-1] if macd_line else 0), 0, 0
    sig_line = calc_ema(macd_line, signal)
    offset = len(macd_line)-len(sig_line)
    hist = [m-s for m,s in zip(macd_line[offset:], sig_line)]
    return macd_line[-1], sig_line[-1], (hist[-1] if hist else 0)

def calc_bollinger(prices, period=20, stddev=2.0):
    if len(prices)<period: return None, None, None
    sma = calc_sma(prices, period); mid = sma[-1]; window = prices[-period:]
    std = math.sqrt(sum((p-mid)**2 for p in window)/period)
    return mid+stddev*std, mid, mid-stddev*std

def calc_atr(highs, lows, closes, period=14):
    if len(closes)<period+1: return 0
    trs=[max(highs[i]-lows[i],abs(highs[i]-closes[i-1]),abs(lows[i]-closes[i-1])) for i in range(1,len(closes))]
    return sum(trs[-period:])/period

def calc_supertrend(highs, lows, closes, period=10, mult=3.0):
    if len(closes)<period+1: return None, None
    atr=calc_atr(highs,lows,closes,period); mid=(highs[-1]+lows[-1])/2
    upper=mid+mult*atr; lower=mid-mult*atr
    trend=1 if closes[-1]>lower else (-1 if closes[-1]<upper else 0)
    return trend, (lower if trend==1 else upper)

def get_signal(strategy, pair, interval="1h", params_json="{}"):
    """Returns ('BUY'|'SELL'|'HOLD', rsi, info_dict) for the given strategy."""
    try:
        params=json.loads(params_json) if params_json else {}
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={pair}&interval={interval}&limit=200",timeout=8).json()
        if not isinstance(r,list) or len(r)<30: return "HOLD",50,{}
        closes=[float(k[4]) for k in r]; highs=[float(k[2]) for k in r]; lows=[float(k[3]) for k in r]
        rsi=calc_rsi(closes,14); s=strategy.upper()

        if s=="EMA":
            fast=params.get("ema_fast",21); slow=params.get("ema_slow",55)
            ef=calc_ema(closes,fast); es=calc_ema(closes,slow)
            if len(ef)<2 or len(es)<2: return "HOLD",rsi,{}
            if ef[-1]>es[-1] and ef[-2]<=es[-2] and 45<=rsi<=65:
                return "BUY",rsi,{"ema_fast":round(ef[-1],2),"ema_slow":round(es[-1],2)}
            if ef[-1]<es[-1] and ef[-2]>=es[-2]:
                return "SELL",rsi,{"ema_fast":round(ef[-1],2),"ema_slow":round(es[-1],2)}
            return "HOLD",rsi,{"ema_fast":round(ef[-1],2),"ema_slow":round(es[-1],2)}

        elif s=="MACD":
            macd,sig,hist=calc_macd(closes)
            if macd is None: return "HOLD",rsi,{}
            prev_macd,prev_sig,_=calc_macd(closes[:-1])
            if prev_macd is None: return "HOLD",rsi,{}
            if macd>sig and prev_macd<=prev_sig and rsi<70:
                return "BUY",rsi,{"macd":round(macd,4),"signal":round(sig,4),"hist":round(hist,4)}
            if macd<sig and prev_macd>=prev_sig and rsi>30:
                return "SELL",rsi,{"macd":round(macd,4),"signal":round(sig,4),"hist":round(hist,4)}
            return "HOLD",rsi,{"macd":round(macd,4),"signal":round(sig,4)}

        elif s=="BB":
            period=params.get("bb_period",20); std=params.get("bb_std",2.0)
            upper,mid,lower=calc_bollinger(closes,period,std)
            if upper is None: return "HOLD",rsi,{}
            price=closes[-1]
            if price<=lower and rsi<35: return "BUY",rsi,{"upper":round(upper,2),"mid":round(mid,2),"lower":round(lower,2)}
            if price>=upper and rsi>65: return "SELL",rsi,{"upper":round(upper,2),"mid":round(mid,2),"lower":round(lower,2)}
            return "HOLD",rsi,{"upper":round(upper,2),"mid":round(mid,2),"lower":round(lower,2)}

        elif s=="RSI_REV":
            oversold=params.get("oversold",30); overbought=params.get("overbought",70)
            if rsi<=oversold: return "BUY",rsi,{"oversold":oversold,"overbought":overbought}
            if rsi>=overbought: return "SELL",rsi,{"oversold":oversold,"overbought":overbought}
            return "HOLD",rsi,{"oversold":oversold,"overbought":overbought}

        elif s=="GOLDEN":
            sma50=calc_sma(closes,50); sma_slow=calc_sma(closes,200) if len(closes)>=200 else calc_sma(closes,100)
            if len(sma50)<2 or len(sma_slow)<2: return "HOLD",rsi,{}
            if sma50[-1]>sma_slow[-1] and sma50[-2]<=sma_slow[-2]:
                return "BUY",rsi,{"sma_fast":round(sma50[-1],2),"sma_slow":round(sma_slow[-1],2)}
            if sma50[-1]<sma_slow[-1] and sma50[-2]>=sma_slow[-2]:
                return "SELL",rsi,{"sma_fast":round(sma50[-1],2),"sma_slow":round(sma_slow[-1],2)}
            return "HOLD",rsi,{"sma_fast":round(sma50[-1],2),"sma_slow":round(sma_slow[-1],2)}

        elif s=="SUPER":
            period=int(params.get("st_period",10)); mult=float(params.get("st_mult",3.0))
            st=_supertrend_series(highs,lows,closes,period,mult)
            if len(st)<2 or st[-1] is None or st[-2] is None: return "HOLD",rsi,{}
            if st[-1]==1 and st[-2]==-1 and rsi<70: return "BUY",rsi,{"trend":"FLIP UP"}
            if st[-1]==-1 and st[-2]==1 and rsi>30: return "SELL",rsi,{"trend":"FLIP DOWN"}
            return "HOLD",rsi,{"trend":"UP" if st[-1]==1 else "DOWN"}

        return "HOLD",rsi,{}
    except Exception as e:
        print(f"get_signal error ({strategy}/{pair}): {e}"); return "HOLD",50,{}

def send_telegram(token, chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                     json={"chat_id":chat_id,"text":text,"parse_mode":"HTML"}, timeout=5)
    except: pass

# ── AUTO-BOT ──────────────────────────────────────────────────────────────────
def close_trade_auto(c, t, exit_p, uid, mode):
    qty=t["quantity"]; entry=t["entry_price"]
    pnl=((exit_p-entry)*qty) if t["side"]=="BUY" else ((entry-exit_p)*qty)
    pnl_pct=(((exit_p-entry)/entry)*100) if t["side"]=="BUY" else (((entry-exit_p)/entry)*100)
    pnl=round(pnl,4); pnl_pct=round(pnl_pct,2)
    returned=(entry*qty)+pnl
    f=c.execute("SELECT * FROM funds WHERE user_id=?",(uid,)).fetchone()
    if f:
        new_bal=(f["demo_balance"] or 0)+returned
        daily_loss=(f["daily_loss_used"] or 0)+(abs(pnl) if pnl<0 else 0)
        c.execute("UPDATE funds SET demo_balance=?,daily_loss_used=? WHERE user_id=?",(new_bal,daily_loss,uid))
    c.execute("UPDATE trades SET exit_price=?,pnl=?,pnl_pct=?,status='closed',closed_at=? WHERE id=?",
              (exit_p,pnl,pnl_pct,datetime.utcnow().isoformat(),t["id"]))
    add_alert(uid,"success" if pnl>=0 else "error",
              f"{'✅' if pnl>=0 else '❌'} Auto-closed {t['pair']} — PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)",mode)

def check_price_alerts(c):
    alerts = c.execute("SELECT * FROM price_alerts WHERE is_triggered=0").fetchall()
    for a in alerts:
        price = live_price(a["symbol"])
        if price == 0: continue
        triggered = (a["condition"]=="above" and price>=a["target_price"]) or \
                    (a["condition"]=="below" and price<=a["target_price"])
        if triggered:
            c.execute("UPDATE price_alerts SET is_triggered=1 WHERE id=?", (a["id"],))
            msg = f"🎯 Price Alert: {a['symbol']} is ${price:,.2f} (target: {a['condition']} ${a['target_price']:,.2f})"
            add_alert(a["user_id"],"warning",msg)
            s = c.execute("SELECT * FROM settings WHERE user_id=?",(a["user_id"],)).fetchone()
            if s and s["telegram_bot_token"] and s["telegram_alerts_enabled"]:
                send_telegram(s["telegram_bot_token"],s["telegram_chat_id"],msg)

def fill_pending_orders(c):
    """Auto-fill LIMIT/STOP_MARKET orders when price reaches trigger."""
    pending=c.execute("SELECT * FROM trades WHERE status='pending' AND mode='demo'").fetchall()
    for t in pending:
        price=live_price(t["pair"])
        if price==0: continue
        otype=t["order_type"] or "LIMIT"; lp=t["limit_price"] or 0
        if lp==0: continue
        triggered=False
        if otype=="LIMIT":
            triggered=(t["side"]=="BUY" and price<=lp) or (t["side"]=="SELL" and price>=lp)
        elif otype=="STOP_MARKET":
            triggered=(t["side"]=="BUY" and price>=lp) or (t["side"]=="SELL" and price<=lp)
        if triggered:
            c.execute("UPDATE trades SET status='open',entry_price=?,order_type=? WHERE id=?",(price,otype,t["id"]))
            add_alert(t["user_id"],"success",f"Order filled: {t['side']} {t['pair']} @ ${price:,.2f} ({otype})","demo")

def run_auto_bot():
    c = get_db()
    try:
        check_price_alerts(c)
        fill_pending_orders(c)
        bots = c.execute("SELECT * FROM bot_config WHERE is_running=1").fetchall()
        for cfg in bots:
            uid=cfg["user_id"]; pair=cfg["trading_pair"] or "BTCUSDT"; mode=cfg["mode"] or "demo"
            funds=c.execute("SELECT * FROM funds WHERE user_id=?",(uid,)).fetchone()
            if not funds: continue
            today=datetime.utcnow().strftime("%Y-%m-%d")
            if funds["daily_reset_date"]!=today:
                c.execute("UPDATE funds SET daily_loss_used=0,daily_reset_date=? WHERE user_id=?",(today,uid))
            # Hard stop on daily loss limit
            if funds["max_daily_loss_pct"] and funds["daily_loss_used"]:
                max_loss=funds["demo_balance"]*(funds["max_daily_loss_pct"]/100)
                if funds["daily_loss_used"]>=max_loss:
                    add_alert(uid,"error","🛑 Daily loss limit reached — bot stopped",mode)
                    c.execute("UPDATE bot_config SET is_running=0 WHERE user_id=?",(uid,))
                    c.commit(); continue
            # Manage open trades (SL/TP/trailing)
            open_trades=c.execute("SELECT * FROM trades WHERE user_id=? AND status='open' AND mode=?",(uid,mode)).fetchall()
            for t in open_trades:
                curr_p=live_price(t["pair"])
                if curr_p==0: continue
                sl=t["trailing_stop_pct"] or cfg["stop_loss_pct"] or 1.5
                tp=cfg["take_profit_pct"] or 3.0
                if t["side"]=="BUY":
                    trail_high=t["trailing_high"] or t["entry_price"]
                    if curr_p>trail_high:
                        c.execute("UPDATE trades SET trailing_high=? WHERE id=?",(curr_p,t["id"]))
                        trail_high=curr_p
                    stop_price=trail_high*(1-sl/100)
                    if curr_p<=stop_price or curr_p>=t["entry_price"]*(1+tp/100):
                        close_trade_auto(c,t,curr_p,uid,mode)
                elif t["side"]=="SELL":
                    if curr_p>=t["entry_price"]*(1+sl/100) or curr_p<=t["entry_price"]*(1-tp/100):
                        close_trade_auto(c,t,curr_p,uid,mode)
            c.commit()
            # Auto-trade entry signals (demo only for safety)
            if not cfg["auto_trade"] or mode!="demo": continue
            open_cnt=c.execute("SELECT COUNT(*) as n FROM trades WHERE user_id=? AND mode='demo' AND status='open'",(uid,)).fetchone()["n"]
            max_open=funds["max_open_trades"] or 3
            if open_cnt>=max_open: continue
            try:
                r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1h&limit=100",timeout=5).json()
                closes=[float(k[4]) for k in r]
            except: continue
            ef=calc_ema(closes,cfg["ema_fast"] or 21); es=calc_ema(closes,cfg["ema_slow"] or 55)
            rsi=calc_rsi(closes,cfg["rsi_period"] or 14)
            if len(ef)<2 or len(es)<2: continue
            buy_sig=(ef[-1]>es[-1] and ef[-2]<=es[-2] and (cfg["rsi_buy_threshold"] or 45)<=rsi<=(cfg["rsi_sell_threshold"] or 65))
            sell_sig=(ef[-1]<es[-1] and ef[-2]>=es[-2] and rsi>(cfg["rsi_sell_threshold"] or 65))
            price=live_price(pair)
            if price==0: continue
            if buy_sig:
                # Refresh funds after possible modifications
                funds=c.execute("SELECT * FROM funds WHERE user_id=?",(uid,)).fetchone()
                trade_amt=min(cfg["trade_amount"] or 100, funds["demo_balance"]*(funds["max_trade_size_pct"] or 10)/100)
                if trade_amt>10 and funds["demo_balance"]>trade_amt:
                    qty=round(trade_amt/price,6)
                    c.execute("UPDATE funds SET demo_balance=? WHERE user_id=?",(funds["demo_balance"]-trade_amt,uid))
                    c.execute("INSERT INTO trades (user_id,mode,pair,side,entry_price,quantity,status,strategy,trailing_stop_pct) VALUES (?,?,?,?,?,?,'open',?,?)",
                              (uid,"demo",pair,"BUY",price,qty,cfg["strategy"] or "EMA_RSI",cfg["stop_loss_pct"] or 1.5))
                    add_alert(uid,"info",f"🤖 Auto-BUY {pair} @ ${price:,.2f} | RSI:{rsi:.1f}","demo")
                    c.commit()
            elif sell_sig:
                longs=c.execute("SELECT * FROM trades WHERE user_id=? AND mode='demo' AND status='open' AND side='BUY'",(uid,)).fetchall()
                for t in longs:
                    close_trade_auto(c,t,price,uid,"demo")
                c.commit()
    except Exception as e:
        print("Auto-bot error:",e)
    finally:
        try: c.close()
        except: pass

def run_multi_bots():
    """Run all user-created named bots (bots table)."""
    c=get_db()
    try:
        bots=c.execute("SELECT * FROM bots WHERE is_running=1").fetchall()
        for bot in bots:
            uid=bot["user_id"]
            funds=c.execute("SELECT * FROM funds WHERE user_id=?",(uid,)).fetchone()
            if not funds: continue
            # Manage existing open bot trades (SL/TP/trailing/partial-TP)
            open_trades=c.execute("SELECT * FROM trades WHERE user_id=? AND mode='demo' AND status='open' AND bot_id=?",(uid,bot["id"])).fetchall()
            for t in open_trades:
                curr_p=live_price(t["pair"])
                if curr_p==0: continue
                entry=t["avg_entry_price"] or t["entry_price"] or curr_p
                sl=t["trailing_stop_pct"] or bot["sl_pct"] or 1.5
                tp1=t["take_profit_pct"] or bot["tp1_pct"] or 3.0
                tp2=t["tp2_pct"] or bot["tp2_pct"] or 6.0
                # Breakeven activation
                if t["breakeven_at_pct"] and not t["breakeven_activated"] and t["side"]=="BUY":
                    if curr_p>=entry*(1+t["breakeven_at_pct"]/100):
                        c.execute("UPDATE trades SET trailing_stop_pct=0.1,breakeven_activated=1 WHERE id=?",(t["id"],))
                        add_alert(uid,"info",f"🔒 Break-even on {t['pair']} @ ${curr_p:,.2f}","demo")
                # TP1 partial close
                if not t["tp1_hit"] and t["side"]=="BUY" and curr_p>=entry*(1+tp1/100):
                    tp1_qty_pct=t["tp1_qty_pct"] or 50
                    close_qty=round(t["quantity"]*(tp1_qty_pct/100),6)
                    remaining=round(t["quantity"]-close_qty,6)
                    pnl=(curr_p-entry)*close_qty; returned=entry*close_qty+pnl
                    f2=c.execute("SELECT * FROM funds WHERE user_id=?",(uid,)).fetchone()
                    c.execute("UPDATE funds SET demo_balance=? WHERE user_id=?",((f2["demo_balance"] or 0)+returned,uid))
                    c.execute("UPDATE trades SET quantity=?,tp1_hit=1 WHERE id=?",(remaining,t["id"]))
                    c.execute("UPDATE bots SET total_pnl=total_pnl+? WHERE id=?",(pnl,bot["id"]))
                    add_alert(uid,"success",f"📤 TP1! Closed {tp1_qty_pct:.0f}% {t['pair']} @ ${curr_p:,.2f} PnL:${pnl:+.2f}","demo")
                    c.commit(); continue
                # TP2 full close
                if t["tp1_hit"] and not t["tp2_hit"] and t["side"]=="BUY" and curr_p>=entry*(1+tp2/100):
                    close_trade_auto(c,t,curr_p,uid,"demo")
                    pnl=(curr_p-entry)*t["quantity"]
                    c.execute("UPDATE bots SET total_pnl=total_pnl+?,trade_count=trade_count+1,win_count=win_count+1,last_signal='TP2 HIT' WHERE id=?",(pnl,bot["id"]))
                    c.commit(); continue
                # Stop management: fixed SL until TP1 books profit; after TP1 trail with break-even floor
                if t["side"]=="BUY":
                    if t["tp1_hit"] and bot["trailing_enabled"]:
                        trail_high=t["trailing_high"] or entry
                        if curr_p>trail_high:
                            c.execute("UPDATE trades SET trailing_high=? WHERE id=?",(curr_p,t["id"])); trail_high=curr_p
                        stop=max(entry,trail_high*(1-sl/100))
                    elif t["tp1_hit"]:
                        stop=entry  # break-even after TP1
                    else:
                        stop=entry*(1-sl/100)
                    if curr_p<=stop:
                        close_trade_auto(c,t,curr_p,uid,"demo")
                        pnl=(curr_p-entry)*t["quantity"]
                        c.execute("UPDATE bots SET total_pnl=total_pnl+?,trade_count=trade_count+1,last_signal=? WHERE id=?",
                                  (pnl,"TRAIL EXIT" if t["tp1_hit"] else "SL HIT",bot["id"]))
                        if pnl>=0: c.execute("UPDATE bots SET win_count=win_count+1 WHERE id=?",(bot["id"],))
                        c.commit()
            c.commit()
            # Entry signal (only if no open trade for this bot)
            if open_trades: continue
            signal,rsi_val,_=get_signal(bot["strategy"],bot["pair"],bot["timeframe"],bot["params"] or "{}")
            c.execute("UPDATE bots SET last_signal=?,last_run_at=? WHERE id=?",(f"{signal} RSI:{rsi_val:.1f}",datetime.utcnow().isoformat(),bot["id"]))
            c.commit()
            if signal!="BUY": continue
            funds=c.execute("SELECT * FROM funds WHERE user_id=?",(uid,)).fetchone()
            capital=min(bot["capital_usdt"] or 100, funds["demo_balance"] or 0)
            if capital<10 or (funds["demo_balance"] or 0)<capital: continue
            price=live_price(bot["pair"])
            if price==0: continue
            qty=round(capital/price,6)
            c.execute("UPDATE funds SET demo_balance=? WHERE user_id=?",((funds["demo_balance"] or 0)-capital,uid))
            c.execute("INSERT INTO trades (user_id,mode,pair,side,entry_price,quantity,status,strategy,trailing_stop_pct,take_profit_pct,tp2_pct,tp1_qty_pct,bot_id,tag) VALUES (?,?,?,?,?,?,'open',?,?,?,?,?,?,'Bot')",
                      (uid,"demo",bot["pair"],"BUY",price,qty,f"BOT:{bot['strategy']}",bot["sl_pct"] or 1.5,bot["tp1_pct"] or 3.0,bot["tp2_pct"] or 6.0,50,bot["id"]))
            add_alert(uid,"info",f"🤖 Bot '{bot['name']}' BUY {bot['pair']} @ ${price:,.2f} | {bot['strategy']} RSI:{rsi_val:.1f}","demo")
            c.commit()
    except Exception as e:
        print("Multi-bot error:",e)
    finally:
        try: c.close()
        except: pass

def _bot_loop():
    while True:
        try: run_auto_bot()
        except Exception as e: print("Bot thread error:",e)
        try: run_multi_bots()
        except Exception as e: print("Multi-bot thread error:",e)
        time.sleep(60)

threading.Thread(target=_bot_loop, daemon=True).start()

# ── AUTH ──────────────────────────────────────────────────────────────────────
class LoginReq(BaseModel):
    username: str; password: str

class RegisterReq(BaseModel):
    username: str; email: str; password: str; name: Optional[str]=""

@app.post("/api/auth/login")
def login(req: LoginReq):
    c=get_db(); u=c.execute("SELECT * FROM users WHERE username=? OR email=?",(req.username,req.username)).fetchone(); c.close()
    if not u or not bcrypt.checkpw(req.password.encode(),u["password_hash"].encode()):
        raise HTTPException(401,"Invalid credentials")
    return {"token":make_token(u["id"],u["username"]),"username":u["username"],"email":u["email"]}

@app.post("/api/auth/register")
def register(req: RegisterReq):
    c=get_db()
    try:
        pw=bcrypt.hashpw(req.password.encode(),bcrypt.gensalt()).decode()
        cur=c.execute("INSERT INTO users (username,email,password_hash,name) VALUES (?,?,?,?)",(req.username,req.email,pw,req.name or ""))
        uid=cur.lastrowid
        c.execute("INSERT OR IGNORE INTO settings (user_id) VALUES (?)",(uid,))
        c.execute("INSERT OR IGNORE INTO bot_config (user_id) VALUES (?)",(uid,))
        c.execute("INSERT OR IGNORE INTO funds (user_id) VALUES (?)",(uid,))
        c.commit()
        return {"token":make_token(uid,req.username),"username":req.username,"email":req.email}
    except:
        raise HTTPException(400,"Username or email taken")
    finally:
        c.close()

# ── PROFILE ───────────────────────────────────────────────────────────────────
@app.get("/api/auth/profile")
def get_profile(user=Depends(current_user)):
    c=get_db(); u=c.execute("SELECT id,username,email,name,role,created_at FROM users WHERE id=?",(user["id"],)).fetchone(); c.close()
    if not u: raise HTTPException(404,"User not found")
    return dict(u)

class ProfileUpdate(BaseModel):
    name: Optional[str]=None; username: Optional[str]=None; email: Optional[str]=None
    current_password: Optional[str]=None; new_password: Optional[str]=None

@app.put("/api/auth/profile")
def update_profile(req: ProfileUpdate, user=Depends(current_user)):
    c=get_db()
    u=c.execute("SELECT * FROM users WHERE id=?",(user["id"],)).fetchone()
    if not u: c.close(); raise HTTPException(404,"User not found")
    updates={}
    if req.name is not None: updates["name"]=req.name
    if req.username and req.username!=u["username"]:
        if c.execute("SELECT id FROM users WHERE username=? AND id!=?",(req.username,user["id"])).fetchone():
            c.close(); raise HTTPException(400,"Username already taken")
        updates["username"]=req.username
    if req.email and req.email!=u["email"]:
        if c.execute("SELECT id FROM users WHERE email=? AND id!=?",(req.email,user["id"])).fetchone():
            c.close(); raise HTTPException(400,"Email already taken")
        updates["email"]=req.email
    if req.new_password:
        if not req.current_password: c.close(); raise HTTPException(400,"Current password is required")
        if not bcrypt.checkpw(req.current_password.encode(),u["password_hash"].encode()):
            c.close(); raise HTTPException(401,"Current password is incorrect")
        if len(req.new_password)<6: c.close(); raise HTTPException(400,"Password must be at least 6 characters")
        updates["password_hash"]=bcrypt.hashpw(req.new_password.encode(),bcrypt.gensalt()).decode()
    if updates:
        c.execute(f"UPDATE users SET {','.join(f'{k}=?' for k in updates)} WHERE id=?",(*updates.values(),user["id"]))
        c.commit()
    u2=c.execute("SELECT id,username,email,name,role,created_at FROM users WHERE id=?",(user["id"],)).fetchone(); c.close()
    return dict(u2)

# ── MODE ──────────────────────────────────────────────────────────────────────
@app.get("/api/bot/mode")
def get_mode(user=Depends(current_user)):
    c=get_db(); cfg=c.execute("SELECT mode FROM bot_config WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    return {"mode":cfg["mode"] if cfg else "demo"}

@app.post("/api/bot/mode/{mode}")
def set_mode(mode: str, user=Depends(current_user)):
    if mode not in ("demo","live"): raise HTTPException(400,"Must be demo or live")
    c=get_db(); c.execute("UPDATE bot_config SET mode=?,is_running=0 WHERE user_id=?",(mode,user["id"])); c.commit(); c.close()
    add_alert(user["id"],"info" if mode=="demo" else "warning",f"{'🧪 Demo' if mode=='demo' else '⚡ Live'} mode activated — bot stopped for safety",mode)
    return {"mode":mode}

# ── FUNDS ─────────────────────────────────────────────────────────────────────
class FundsUpdate(BaseModel):
    demo_balance: Optional[float]=None; demo_initial: Optional[float]=None; live_balance: Optional[float]=None
    max_daily_loss_pct: Optional[float]=None; max_trade_size_pct: Optional[float]=None; max_open_trades: Optional[int]=None
    daily_profit_target: Optional[float]=None; risk_per_trade_pct: Optional[float]=None
    auto_compound: Optional[bool]=None; compound_pct: Optional[float]=None

@app.get("/api/funds")
def get_funds(user=Depends(current_user)):
    c=get_db(); f=c.execute("SELECT * FROM funds WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    if not f: return {"demo_balance":10000,"demo_initial":10000}
    d=dict(f); today=datetime.utcnow().strftime("%Y-%m-%d")
    if d.get("daily_reset_date")!=today:
        c2=get_db(); c2.execute("UPDATE funds SET daily_loss_used=0,daily_reset_date=? WHERE user_id=?",(today,user["id"])); c2.commit(); c2.close()
        d["daily_loss_used"]=0
    return d

@app.put("/api/funds")
def update_funds(req: FundsUpdate, user=Depends(current_user)):
    c=get_db(); fields={k:v for k,v in req.dict().items() if v is not None}
    if fields: c.execute(f"UPDATE funds SET {','.join(f'{k}=?' for k in fields)} WHERE user_id=?",(*fields.values(),user["id"]))
    c.commit(); c.close(); return {"status":"updated"}

@app.post("/api/funds/reset-demo")
def reset_demo(user=Depends(current_user)):
    c=get_db(); f=c.execute("SELECT demo_initial FROM funds WHERE user_id=?",(user["id"],)).fetchone()
    initial=f["demo_initial"] if f else 10000
    c.execute("UPDATE funds SET demo_balance=?,daily_loss_used=0 WHERE user_id=?",(initial,user["id"]))
    c.execute("DELETE FROM trades WHERE user_id=? AND mode='demo'",(user["id"],))
    c.commit(); c.close()
    add_alert(user["id"],"info",f"🔄 Demo reset to ${initial:,.0f}","demo")
    return {"status":"reset","balance":initial}

# ── DEMO TRADING ──────────────────────────────────────────────────────────────
class DemoTradeReq(BaseModel):
    pair: str; side: str; amount_usdt: float
    order_type: str="MARKET"       # MARKET | LIMIT | STOP_MARKET | OCO
    limit_price: Optional[float]=None   # price to execute LIMIT / trigger STOP_MARKET
    stop_loss_pct: Optional[float]=None  # override bot config SL
    take_profit_pct: Optional[float]=None  # override bot config TP

@app.post("/api/demo/trade")
def place_trade(req: DemoTradeReq, user=Depends(current_user)):
    c=get_db()
    f=c.execute("SELECT * FROM funds WHERE user_id=?",(user["id"],)).fetchone()
    cfg=c.execute("SELECT * FROM bot_config WHERE user_id=?",(user["id"],)).fetchone()
    if not f: raise HTTPException(400,"Funds not found")
    balance=f["demo_balance"]; max_pct=f["max_trade_size_pct"] or 10; max_usdt=balance*(max_pct/100)
    if req.amount_usdt>max_usdt: raise HTTPException(400,f"Trade ${req.amount_usdt:.0f} exceeds max ${max_usdt:.0f} ({max_pct}% of balance)")
    if req.amount_usdt>balance: raise HTTPException(400,f"Insufficient balance: ${balance:.2f}")
    otype=req.order_type.upper()
    # validate limit price required for LIMIT / STOP_MARKET
    if otype in("LIMIT","STOP_MARKET") and not req.limit_price:
        raise HTTPException(400,f"{otype} order requires a limit/trigger price")
    open_cnt=c.execute("SELECT COUNT(*) as n FROM trades WHERE user_id=? AND mode='demo' AND status IN ('open','pending')",(user["id"],)).fetchone()["n"]
    max_open=f["max_open_trades"] or 3
    if open_cnt>=max_open: raise HTTPException(400,f"Max {max_open} open trades reached")
    price=live_price(req.pair)
    if price==0: raise HTTPException(400,"Could not fetch live price from Binance")
    sl_pct=req.stop_loss_pct if req.stop_loss_pct else (cfg["stop_loss_pct"] if cfg else 1.5)
    tp_pct=req.take_profit_pct if req.take_profit_pct else (cfg["take_profit_pct"] if cfg else 3.0)
    # MARKET / OCO: execute immediately; LIMIT / STOP_MARKET: store as pending
    if otype in("MARKET","OCO"):
        qty=round(req.amount_usdt/price,6); exec_price=price; status="open"
    else:
        lp=req.limit_price; qty=round(req.amount_usdt/lp,6); exec_price=lp; status="pending"
    c.execute("UPDATE funds SET demo_balance=? WHERE user_id=?",(balance-req.amount_usdt,user["id"]))
    cur=c.execute("INSERT INTO trades (user_id,mode,pair,side,entry_price,quantity,status,strategy,trailing_stop_pct,take_profit_pct,order_type,limit_price) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (user["id"],"demo",req.pair,req.side,exec_price if status=="open" else None,qty,status,
                   cfg["strategy"] if cfg else "MANUAL",sl_pct,tp_pct,otype,req.limit_price))
    tid=cur.lastrowid; c.commit(); c.close()
    if status=="open":
        add_alert(user["id"],"info",f"Trade placed: {req.side} {req.pair} @ ${exec_price:,.2f} ({otype}) — ${req.amount_usdt:.0f} USDT","demo")
    else:
        add_alert(user["id"],"info",f"{otype} order queued: {req.side} {req.pair} @ ${lp:,.2f} — waiting for price","demo")
    return {"trade_id":tid,"pair":req.pair,"side":req.side,"order_type":otype,"price":exec_price,"quantity":qty,"amount_usdt":req.amount_usdt,"status":status}

@app.post("/api/demo/trade/{trade_id}/close")
def close_trade(trade_id: int, user=Depends(current_user)):
    c=get_db()
    t=c.execute("SELECT * FROM trades WHERE id=? AND user_id=? AND mode='demo' AND status='open'",(trade_id,user["id"])).fetchone()
    if not t: raise HTTPException(404,"Trade not found")
    exit_p=live_price(t["pair"])
    if exit_p==0: raise HTTPException(400,"Could not fetch live price")
    qty=t["quantity"]; entry=t["entry_price"]
    pnl=((exit_p-entry)*qty) if t["side"]=="BUY" else ((entry-exit_p)*qty)
    pnl_pct=(((exit_p-entry)/entry)*100) if t["side"]=="BUY" else (((entry-exit_p)/entry)*100)
    pnl=round(pnl,4); pnl_pct=round(pnl_pct,2)
    returned=(entry*qty)+pnl
    f=c.execute("SELECT * FROM funds WHERE user_id=?",(user["id"],)).fetchone()
    new_bal=(f["demo_balance"] or 0)+returned
    daily_loss=(f["daily_loss_used"] or 0)+(abs(pnl) if pnl<0 else 0)
    if pnl>0 and f["auto_compound"] and f["compound_pct"]:
        new_bal+=pnl*(f["compound_pct"]/100)
    c.execute("UPDATE funds SET demo_balance=?,daily_loss_used=? WHERE user_id=?",(new_bal,daily_loss,user["id"]))
    c.execute("UPDATE trades SET exit_price=?,pnl=?,pnl_pct=?,status='closed',closed_at=? WHERE id=?",
              (exit_p,pnl,pnl_pct,datetime.utcnow().isoformat(),trade_id))
    c.commit(); c.close()
    add_alert(user["id"],"success" if pnl>=0 else "error",f"{'✅' if pnl>=0 else '❌'} Closed {t['pair']} — PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)","demo")
    return {"trade_id":trade_id,"exit_price":exit_p,"pnl":pnl,"pnl_pct":pnl_pct,"new_balance":round(new_bal,2)}

class PartialCloseReq(BaseModel):
    close_pct: float  # 25, 50, 75, 100

@app.post("/api/demo/trade/{trade_id}/partial-close")
def partial_close(trade_id: int, req: PartialCloseReq, user=Depends(current_user)):
    c=get_db()
    t=c.execute("SELECT * FROM trades WHERE id=? AND user_id=? AND mode='demo' AND status='open'",(trade_id,user["id"])).fetchone()
    if not t: c.close(); raise HTTPException(404,"Open trade not found")
    if req.close_pct<=0 or req.close_pct>100: c.close(); raise HTTPException(400,"close_pct must be 1-100")
    exit_p=live_price(t["pair"])
    if exit_p==0: c.close(); raise HTTPException(400,"Could not fetch live price")
    close_qty=round(t["quantity"]*(req.close_pct/100),6)
    remaining_qty=round(t["quantity"]-close_qty,6)
    entry=t["entry_price"] or t["avg_entry_price"] or exit_p
    pnl=((exit_p-entry)*close_qty) if t["side"]=="BUY" else ((entry-exit_p)*close_qty)
    pnl_pct=(((exit_p-entry)/entry)*100) if t["side"]=="BUY" else (((entry-exit_p)/entry)*100)
    pnl=round(pnl,4); pnl_pct=round(pnl_pct,2)
    returned=(entry*close_qty)+pnl
    f=c.execute("SELECT * FROM funds WHERE user_id=?",(user["id"],)).fetchone()
    new_bal=(f["demo_balance"] or 0)+returned
    daily_loss=(f["daily_loss_used"] or 0)+(abs(pnl) if pnl<0 else 0)
    c.execute("UPDATE funds SET demo_balance=?,daily_loss_used=? WHERE user_id=?",(new_bal,daily_loss,user["id"]))
    if req.close_pct>=100 or remaining_qty<0.000001:
        c.execute("UPDATE trades SET exit_price=?,pnl=?,pnl_pct=?,status='closed',closed_at=?,quantity=? WHERE id=?",
                  (exit_p,pnl,pnl_pct,datetime.utcnow().isoformat(),close_qty,trade_id))
        msg=f"{'✅' if pnl>=0 else '❌'} Closed 100% {t['pair']} @ ${exit_p:,.2f} PnL:${pnl:+.2f}"
    else:
        c.execute("UPDATE trades SET quantity=? WHERE id=?",(remaining_qty,trade_id))
        msg=f"📤 Closed {req.close_pct:.0f}% {t['pair']} @ ${exit_p:,.2f} PnL:${pnl:+.2f} | Remaining:{remaining_qty}"
    c.commit(); c.close()
    add_alert(user["id"],"success" if pnl>=0 else "error",msg,"demo")
    return {"trade_id":trade_id,"close_pct":req.close_pct,"exit_price":exit_p,"pnl":pnl,"pnl_pct":pnl_pct,"remaining_qty":remaining_qty,"new_balance":round(new_bal,2)}

class ScaleInReq(BaseModel):
    amount_usdt: float

@app.post("/api/demo/trade/{trade_id}/scale-in")
def scale_in(trade_id: int, req: ScaleInReq, user=Depends(current_user)):
    c=get_db()
    t=c.execute("SELECT * FROM trades WHERE id=? AND user_id=? AND mode='demo' AND status='open'",(trade_id,user["id"])).fetchone()
    if not t: c.close(); raise HTTPException(404,"Open trade not found")
    f=c.execute("SELECT * FROM funds WHERE user_id=?",(user["id"],)).fetchone()
    if req.amount_usdt>(f["demo_balance"] or 0): c.close(); raise HTTPException(400,"Insufficient balance")
    curr_price=live_price(t["pair"])
    if curr_price==0: c.close(); raise HTTPException(400,"Could not fetch live price")
    new_qty=round(req.amount_usdt/curr_price,6)
    old_qty=t["quantity"]; old_entry=t["avg_entry_price"] or t["entry_price"] or curr_price
    total_qty=old_qty+new_qty
    avg_entry=round((old_entry*old_qty+curr_price*new_qty)/total_qty,2)
    scale_count=(t["scale_count"] or 0)+1
    c.execute("UPDATE funds SET demo_balance=? WHERE user_id=?",((f["demo_balance"] or 0)-req.amount_usdt,user["id"]))
    c.execute("UPDATE trades SET quantity=?,avg_entry_price=?,scale_count=? WHERE id=?",(total_qty,avg_entry,scale_count,trade_id))
    c.commit(); c.close()
    add_alert(user["id"],"info",f"📥 Scale-in {t['pair']}: +{new_qty} @ ${curr_price:,.2f} | Avg entry:${avg_entry:,.2f}","demo")
    return {"trade_id":trade_id,"new_qty":total_qty,"avg_entry":avg_entry,"scale_count":scale_count}

class TPLevelsReq(BaseModel):
    tp1_pct: Optional[float]=None; tp2_pct: Optional[float]=None
    tp1_qty_pct: Optional[float]=None; breakeven_at_pct: Optional[float]=None

@app.put("/api/demo/trade/{trade_id}/tp-levels")
def set_tp_levels(trade_id: int, req: TPLevelsReq, user=Depends(current_user)):
    c=get_db()
    t=c.execute("SELECT * FROM trades WHERE id=? AND user_id=? AND status='open'",(trade_id,user["id"])).fetchone()
    if not t: c.close(); raise HTTPException(404,"Open trade not found")
    updates={}
    if req.tp1_pct is not None: updates["take_profit_pct"]=req.tp1_pct
    if req.tp2_pct is not None: updates["tp2_pct"]=req.tp2_pct
    if req.tp1_qty_pct is not None: updates["tp1_qty_pct"]=req.tp1_qty_pct
    if req.breakeven_at_pct is not None: updates["breakeven_at_pct"]=req.breakeven_at_pct
    if updates:
        c.execute(f"UPDATE trades SET {','.join(f'{k}=?' for k in updates)} WHERE id=?",(*updates.values(),trade_id))
        c.commit()
    t2=c.execute("SELECT * FROM trades WHERE id=?",(trade_id,)).fetchone(); c.close()
    entry=t2["entry_price"] or 0; tp1=t2["take_profit_pct"] or 3.0; tp2=t2["tp2_pct"] or 6.0
    return {"trade_id":trade_id,"tp1_pct":tp1,"tp2_pct":tp2,
            "tp1_price":round(entry*(1+tp1/100),2),"tp2_price":round(entry*(1+tp2/100),2),
            "tp1_qty_pct":t2["tp1_qty_pct"],"breakeven_at_pct":t2["breakeven_at_pct"]}

class NoteReq(BaseModel):
    notes: Optional[str]=None; tag: Optional[str]=None

@app.put("/api/demo/trade/{trade_id}/note")
def update_trade_note(trade_id: int, req: NoteReq, user=Depends(current_user)):
    c=get_db()
    t=c.execute("SELECT * FROM trades WHERE id=? AND user_id=?",(trade_id,user["id"])).fetchone()
    if not t: c.close(); raise HTTPException(404,"Trade not found")
    updates={}
    if req.notes is not None: updates["notes"]=req.notes
    if req.tag is not None: updates["tag"]=req.tag
    if updates:
        c.execute(f"UPDATE trades SET {','.join(f'{k}=?' for k in updates)} WHERE id=?",(*updates.values(),trade_id))
        c.commit()
    c.close(); return {"status":"updated"}

@app.get("/api/demo/open-trades")
def open_trades(user=Depends(current_user)):
    c=get_db()
    trades=c.execute("SELECT * FROM trades WHERE user_id=? AND mode='demo' AND status IN ('open','pending') ORDER BY created_at DESC",(user["id"],)).fetchall()
    c.close(); out=[]
    for t in trades:
        d=dict(t); p=live_price(t["pair"])
        if p and t["entry_price"]:
            qty=t["quantity"] or 0
            unreal=((p-t["entry_price"])*qty) if t["side"]=="BUY" else ((t["entry_price"]-p)*qty)
            d["current_price"]=p; d["unrealized_pnl"]=round(unreal,4)
            d["unrealized_pct"]=round((unreal/(t["entry_price"]*qty))*100,2) if t["entry_price"]*qty else 0
            sl=t["trailing_stop_pct"] or 1.5
            tp=t["take_profit_pct"] or 3.0
            trail_ref=t["trailing_high"] or t["entry_price"]
            d["stop_price"]=round(trail_ref*(1-sl/100),2)
            d["target_price"]=round(t["entry_price"]*(1+tp/100),2)
            d["stop_loss_pct"]=sl; d["take_profit_pct"]=tp
            d["margin_value"]=round(t["entry_price"]*qty,2)
            d["current_value"]=round(p*qty,2)
        out.append(d)
    return out

# ── TRADE SL/TP UPDATE ────────────────────────────────────────────────────────
class SLTPUpdate(BaseModel):
    stop_loss_pct: Optional[float]=None; take_profit_pct: Optional[float]=None

@app.put("/api/demo/trade/{trade_id}/sltp")
def update_trade_sltp(trade_id: int, req: SLTPUpdate, user=Depends(current_user)):
    c=get_db()
    t=c.execute("SELECT * FROM trades WHERE id=? AND user_id=? AND status='open'",(trade_id,user["id"])).fetchone()
    if not t: c.close(); raise HTTPException(404,"Open trade not found")
    if req.stop_loss_pct is not None and (req.stop_loss_pct<=0 or req.stop_loss_pct>=50):
        c.close(); raise HTTPException(400,"Stop loss must be between 0% and 50%")
    if req.take_profit_pct is not None and (req.take_profit_pct<=0 or req.take_profit_pct>=200):
        c.close(); raise HTTPException(400,"Take profit must be between 0% and 200%")
    updates={}
    if req.stop_loss_pct is not None: updates["trailing_stop_pct"]=req.stop_loss_pct
    if req.take_profit_pct is not None: updates["take_profit_pct"]=req.take_profit_pct
    if updates:
        c.execute(f"UPDATE trades SET {','.join(f'{k}=?' for k in updates)} WHERE id=?",(*updates.values(),trade_id))
        c.commit()
    t2=c.execute("SELECT * FROM trades WHERE id=?",(trade_id,)).fetchone(); c.close()
    entry=t2["entry_price"]; sl=t2["trailing_stop_pct"] or 1.5; tp=t2["take_profit_pct"] or 3.0
    add_alert(user["id"],"info",f"✏️ Updated {t2['pair']} — SL: {sl}% | TP: {tp}%","demo")
    return {"trade_id":trade_id,"stop_loss_pct":sl,"take_profit_pct":tp,
            "stop_price":round(entry*(1-sl/100),2),"target_price":round(entry*(1+tp/100),2)}

# ── BACKTEST ──────────────────────────────────────────────────────────────────
def fetch_historical_klines(symbol, interval, start_ms, end_ms):
    all_klines=[]; current=start_ms
    while current<end_ms:
        try:
            r=requests.get("https://api.binance.com/api/v3/klines",
                params={"symbol":symbol,"interval":interval,"startTime":current,"endTime":end_ms,"limit":1000},
                timeout=15).json()
            if not isinstance(r,list) or not r: break
            all_klines.extend(r)
            if len(r)<1000: break
            current=r[-1][0]+1
        except Exception as e:
            print(f"Binance klines error: {e}"); break
    return all_klines

class BacktestReq(BaseModel):
    symbol: str="BTCUSDT"; interval: str="1h"
    start_date: str; end_date: str
    initial_balance: float=10000; trade_amount: float=500
    ema_fast: int=21; ema_slow: int=55; rsi_period: int=14
    rsi_buy_min: float=45; rsi_buy_max: float=65
    stop_loss_pct: float=1.5; take_profit_pct: float=3.0

@app.post("/api/backtest")
def run_backtest(req: BacktestReq, user=Depends(current_user)):
    try:
        start_dt=datetime.strptime(req.start_date,"%Y-%m-%d")
        end_dt=datetime.strptime(req.end_date,"%Y-%m-%d")
    except ValueError:
        raise HTTPException(400,"Invalid date — use YYYY-MM-DD")
    start_ms=int(start_dt.timestamp()*1000); end_ms=int(end_dt.timestamp()*1000)
    if end_ms<=start_ms: raise HTTPException(400,"End date must be after start date")
    if (end_ms-start_ms)>730*86400*1000: raise HTTPException(400,"Maximum range is 2 years")
    if req.ema_fast>=req.ema_slow: raise HTTPException(400,"EMA fast must be less than EMA slow")
    if req.trade_amount<=0 or req.trade_amount>req.initial_balance: raise HTTPException(400,"Trade amount must be > 0 and ≤ initial balance")

    klines=fetch_historical_klines(req.symbol.upper(),req.interval,start_ms,end_ms)
    min_c=req.ema_slow+req.rsi_period+5
    if len(klines)<min_c: raise HTTPException(400,f"Not enough data — {len(klines)} candles fetched, need ≥ {min_c}. Try a wider date range or larger interval.")

    closes=[float(k[4]) for k in klines]
    highs=[float(k[2]) for k in klines]
    lows=[float(k[3]) for k in klines]
    times=[k[0] for k in klines]

    ema_f=calc_ema(closes,req.ema_fast); ema_s=calc_ema(closes,req.ema_slow)
    offset_fast=req.ema_slow-req.ema_fast
    balance=req.initial_balance; position=None
    trades=[]; equity_curve=[]; peak_balance=balance; max_drawdown=0.0

    for j in range(1,len(ema_s)):
        i=j+req.ema_slow-1
        if i>=len(closes): break
        close=closes[i]; high=highs[i]; low=lows[i]
        dt_str=datetime.utcfromtimestamp(times[i]/1000).strftime("%Y-%m-%d %H:%M")

        if position:
            exit_price=None; exit_reason=None
            if low<=position["stop"]: exit_price=position["stop"]; exit_reason="stop_loss"
            elif high>=position["target"]: exit_price=position["target"]; exit_reason="take_profit"
            if exit_reason:
                qty=position["quantity"]
                pnl=(exit_price-position["entry"])*qty
                pnl_pct=((exit_price-position["entry"])/position["entry"])*100
                balance+=position["entry"]*qty+pnl
                trades.append({"entry_date":position["entry_time"],"exit_date":dt_str,"side":"BUY",
                    "entry_price":round(position["entry"],2),"exit_price":round(exit_price,2),
                    "quantity":round(qty,6),"pnl":round(pnl,4),"pnl_pct":round(pnl_pct,2),"exit_reason":exit_reason})
                position=None
                peak_balance=max(peak_balance,balance)
                max_drawdown=max(max_drawdown,((peak_balance-balance)/peak_balance)*100)

        if not position:
            ef_c=ema_f[j+offset_fast]; ef_p=ema_f[j+offset_fast-1]
            es_c=ema_s[j]; es_p=ema_s[j-1]
            rsi=calc_rsi(closes[max(0,i-req.rsi_period*3):i+1],req.rsi_period)
            if ef_c>es_c and ef_p<=es_p and req.rsi_buy_min<=rsi<=req.rsi_buy_max and req.trade_amount<=balance:
                qty=req.trade_amount/close; balance-=req.trade_amount
                position={"entry":close,"quantity":qty,"entry_time":dt_str,
                    "stop":close*(1-req.stop_loss_pct/100),"target":close*(1+req.take_profit_pct/100)}

        unreal=(close-position["entry"])*position["quantity"] if position else 0
        eq_val=balance+(position["entry"]*position["quantity"] if position else 0)+unreal
        equity_curve.append({"date":dt_str,"balance":round(eq_val,2)})

    if position:
        close=closes[-1]; qty=position["quantity"]
        pnl=(close-position["entry"])*qty
        pnl_pct=((close-position["entry"])/position["entry"])*100
        balance+=position["entry"]*qty+pnl
        trades.append({"entry_date":position["entry_time"],"exit_date":datetime.utcfromtimestamp(times[-1]/1000).strftime("%Y-%m-%d %H:%M"),
            "side":"BUY","entry_price":round(position["entry"],2),"exit_price":round(close,2),
            "quantity":round(qty,6),"pnl":round(pnl,4),"pnl_pct":round(pnl_pct,2),"exit_reason":"period_end"})

    pnls=[t["pnl"] for t in trades]
    wins=[p for p in pnls if p>0]; losses=[p for p in pnls if p<=0]
    if len(equity_curve)>600:
        step=max(1,len(equity_curve)//600); equity_curve=equity_curve[::step]

    return {
        "symbol":req.symbol.upper(),"interval":req.interval,
        "start_date":req.start_date,"end_date":req.end_date,"candles_used":len(klines),
        "initial_balance":req.initial_balance,"final_balance":round(balance,2),
        "total_return_pct":round((balance-req.initial_balance)/req.initial_balance*100,2),
        "total_pnl":round(sum(pnls),2),"total_trades":len(trades),
        "winning_trades":len(wins),"losing_trades":len(losses),
        "win_rate":round(len(wins)/len(trades)*100,1) if trades else 0,
        "avg_pnl":round(sum(pnls)/len(pnls),2) if pnls else 0,
        "best_trade":round(max(pnls),2) if pnls else 0,
        "worst_trade":round(min(pnls),2) if pnls else 0,
        "max_drawdown_pct":round(max_drawdown,2),
        "profit_factor":round(sum(wins)/abs(sum(losses)),2) if losses and sum(losses)!=0 else 0,
        "trades":trades,"equity_curve":equity_curve,
    }

# ── ADVANCED MULTI-STRATEGY BACKTEST ─────────────────────────────────────────
def _ema_full(closes, period):
    e=calc_ema(closes,period)
    return ([None]*(period-1)+e) if e else [None]*len(closes)

def _sma_full(closes, period):
    s=calc_sma(closes,period)
    return ([None]*(period-1)+s) if s else [None]*len(closes)

def _rsi_full(closes, period=14):
    out=[50.0]*len(closes)
    for i in range(period,len(closes)):
        w=closes[i-period:i+1]
        chg=[w[j]-w[j-1] for j in range(1,len(w))]
        g=sum(c for c in chg if c>0)/period; l=sum(-c for c in chg if c<0)/period
        out[i]=100.0 if l==0 else 100-100/(1+g/l)
    return out

def _macd_full(closes, fast=12, slow=26, sig=9):
    ef=_ema_full(closes,fast); es=_ema_full(closes,slow)
    macd=[(ef[i]-es[i]) if (ef[i] is not None and es[i] is not None) else None for i in range(len(closes))]
    vals=[m for m in macd if m is not None]
    sig_full=[None]*len(closes)
    if len(vals)>=sig:
        sl_=calc_ema(vals,sig); start=(slow-1)+(sig-1)
        for k,v in enumerate(sl_):
            if start+k<len(closes): sig_full[start+k]=v
    return macd,sig_full

def _boll_at(closes, i, period=20, stddev=2.0):
    if i+1<period: return None,None,None
    w=closes[i+1-period:i+1]; mid=sum(w)/period
    std=math.sqrt(sum((p-mid)**2 for p in w)/period)
    return mid+stddev*std, mid, mid-stddev*std

def _supertrend_series(highs, lows, closes, period=10, mult=3.0):
    """Proper stateful Supertrend: final-band carry-over, flips on band breaks. Returns trend per candle (1/-1/None)."""
    n=len(closes); trend=[None]*n
    if n<period+2: return trend
    trs=[0.0]*n
    for j in range(1,n):
        trs[j]=max(highs[j]-lows[j],abs(highs[j]-closes[j-1]),abs(lows[j]-closes[j-1]))
    fu=[None]*n; fl=[None]*n; t=1
    for j in range(period,n):
        atr=sum(trs[j-period+1:j+1])/period
        mid=(highs[j]+lows[j])/2
        bu=mid+mult*atr; bl=mid-mult*atr
        fu[j]=bu if (fu[j-1] is None or bu<fu[j-1] or closes[j-1]>fu[j-1]) else fu[j-1]
        fl[j]=bl if (fl[j-1] is None or bl>fl[j-1] or closes[j-1]<fl[j-1]) else fl[j-1]
        if t==1 and closes[j]<fl[j]: t=-1
        elif t==-1 and closes[j]>fu[j]: t=1
        trend[j]=t
    return trend

def _bt_signal(strategy, i, closes, highs, lows, ind, params):
    """Per-candle signal for the advanced backtest — mirrors live get_signal logic."""
    rsi=ind["rsi"][i]
    if strategy=="EMA":
        ef,es=ind["ema_f"],ind["ema_s"]
        if ef[i] is None or es[i] is None or ef[i-1] is None or es[i-1] is None: return "HOLD"
        if ef[i]>es[i] and ef[i-1]<=es[i-1] and 45<=rsi<=65: return "BUY"
        if ef[i]<es[i] and ef[i-1]>=es[i-1]: return "SELL"
    elif strategy=="MACD":
        m,sg=ind["macd"],ind["macd_sig"]
        if m[i] is None or sg[i] is None or m[i-1] is None or sg[i-1] is None: return "HOLD"
        if m[i]>sg[i] and m[i-1]<=sg[i-1] and rsi<70: return "BUY"
        if m[i]<sg[i] and m[i-1]>=sg[i-1] and rsi>30: return "SELL"
    elif strategy=="BB":
        up,mid,lo=_boll_at(closes,i,int(params.get("bb_period",20)),float(params.get("bb_std",2.0)))
        if up is None: return "HOLD"
        if closes[i]<=lo and rsi<35: return "BUY"
        if closes[i]>=up and rsi>65: return "SELL"
    elif strategy=="RSI_REV":
        if rsi<=float(params.get("oversold",30)): return "BUY"
        if rsi>=float(params.get("overbought",70)): return "SELL"
    elif strategy=="GOLDEN":
        f,s=ind["sma_f"],ind["sma_s"]
        if f[i] is None or s[i] is None or f[i-1] is None or s[i-1] is None: return "HOLD"
        if f[i]>s[i] and f[i-1]<=s[i-1]: return "BUY"
        if f[i]<s[i] and f[i-1]>=s[i-1]: return "SELL"
    elif strategy=="SUPER":
        st=ind.get("st",[])
        if i>=len(st) or st[i] is None or st[i-1] is None: return "HOLD"
        if st[i]==1 and st[i-1]==-1 and rsi<70: return "BUY"
        if st[i]==-1 and st[i-1]==1 and rsi>30: return "SELL"
    return "HOLD"

class AdvBacktestReq(BaseModel):
    symbol: str="BTCUSDT"; interval: str="1h"
    start_date: str; end_date: str
    strategy: str="EMA"; params: str="{}"
    initial_balance: float=10000; trade_amount: float=500
    sl_pct: float=1.5; tp1_pct: float=3.0; tp2_pct: float=6.0; tp1_qty_pct: float=50
    trailing_enabled: bool=True

@app.post("/api/backtest/advanced")
def run_advanced_backtest(req: AdvBacktestReq, user=Depends(current_user)):
    """Backtest any of the 6 bot strategies with TP1 partial close, TP2, trailing stop."""
    try:
        start_dt=datetime.strptime(req.start_date,"%Y-%m-%d"); end_dt=datetime.strptime(req.end_date,"%Y-%m-%d")
    except ValueError:
        raise HTTPException(400,"Invalid date — use YYYY-MM-DD")
    start_ms=int(start_dt.timestamp()*1000); end_ms=int(end_dt.timestamp()*1000)
    if end_ms<=start_ms: raise HTTPException(400,"End date must be after start date")
    if (end_ms-start_ms)>730*86400*1000: raise HTTPException(400,"Maximum range is 2 years")
    strategy=req.strategy.upper()
    if strategy not in ("EMA","MACD","BB","RSI_REV","GOLDEN","SUPER"): raise HTTPException(400,f"Unknown strategy {strategy}")
    if req.trade_amount<=0 or req.trade_amount>req.initial_balance: raise HTTPException(400,"Trade amount must be > 0 and ≤ initial balance")
    try: params=json.loads(req.params or "{}")
    except: params={}

    klines=fetch_historical_klines(req.symbol.upper(),req.interval,start_ms,end_ms)
    warmup=210 if strategy=="GOLDEN" else 60
    if len(klines)<warmup+20: raise HTTPException(400,f"Not enough data — {len(klines)} candles, need ≥ {warmup+20}. Use a wider date range or larger interval.")
    closes=[float(k[4]) for k in klines]; highs=[float(k[2]) for k in klines]; lows=[float(k[3]) for k in klines]; times=[k[0] for k in klines]

    ind={"rsi":_rsi_full(closes,14)}
    if strategy=="EMA":
        ind["ema_f"]=_ema_full(closes,int(params.get("ema_fast",21))); ind["ema_s"]=_ema_full(closes,int(params.get("ema_slow",55)))
    elif strategy=="MACD":
        ind["macd"],ind["macd_sig"]=_macd_full(closes)
    elif strategy=="GOLDEN":
        slow=200 if len(closes)>=220 else 100
        ind["sma_f"]=_sma_full(closes,50); ind["sma_s"]=_sma_full(closes,slow)
    elif strategy=="SUPER":
        ind["st"]=_supertrend_series(highs,lows,closes,int(params.get("st_period",10)),float(params.get("st_mult",3.0)))

    balance=req.initial_balance; pos=None
    trades=[]; equity=[]; peak=balance; maxdd=0.0
    tp1_hits=0; tp2_hits=0; sl_hits=0; hold_candles=[]

    def record(exit_p,qty,reason,dt,entry,entry_t,entry_i,i):
        nonlocal balance
        pnl=(exit_p-entry)*qty; pnl_pct=((exit_p-entry)/entry)*100
        balance+=entry*qty+pnl
        trades.append({"entry_date":entry_t,"exit_date":dt,"side":"BUY","entry_price":round(entry,2),
            "exit_price":round(exit_p,2),"quantity":round(qty,6),"pnl":round(pnl,4),"pnl_pct":round(pnl_pct,2),"exit_reason":reason})
        hold_candles.append(i-entry_i)

    for i in range(warmup,len(closes)):
        price=closes[i]; high=highs[i]; low=lows[i]
        dt=datetime.utcfromtimestamp(times[i]/1000).strftime("%Y-%m-%d %H:%M")
        if pos:
            # Fixed SL until TP1 books profit; then trail (with break-even floor) so the runner can't lose
            if pos["tp1_done"]:
                stop=max(pos["entry"],pos["trail_high"]*(1-req.sl_pct/100)) if req.trailing_enabled else pos["entry"]
            else:
                stop=pos["entry"]*(1-req.sl_pct/100)
            tp1_price=pos["entry"]*(1+req.tp1_pct/100); tp2_price=pos["entry"]*(1+req.tp2_pct/100)
            if low<=stop:
                reason="trail_exit" if pos["tp1_done"] else "stop_loss"
                if not pos["tp1_done"]: sl_hits+=1
                record(stop,pos["qty"],reason,dt,pos["entry"],pos["time"],pos["entry_i"],i); pos=None
            elif not pos["tp1_done"] and high>=tp1_price:
                qty1=pos["qty"]*(req.tp1_qty_pct/100)
                record(tp1_price,qty1,"tp1_partial",dt,pos["entry"],pos["time"],pos["entry_i"],i); tp1_hits+=1
                pos["qty"]-=qty1; pos["tp1_done"]=True
                if pos["qty"]<=0: pos=None
            elif pos["tp1_done"] and high>=tp2_price:
                record(tp2_price,pos["qty"],"tp2",dt,pos["entry"],pos["time"],pos["entry_i"],i); tp2_hits+=1; pos=None
            else:
                sig=_bt_signal(strategy,i,closes,highs,lows,ind,params)
                if sig=="SELL":
                    record(price,pos["qty"],"signal_exit",dt,pos["entry"],pos["time"],pos["entry_i"],i); pos=None
            if pos and req.trailing_enabled and high>pos["trail_high"]: pos["trail_high"]=high
        if not pos:
            sig=_bt_signal(strategy,i,closes,highs,lows,ind,params)
            if sig=="BUY" and req.trade_amount<=balance:
                qty=req.trade_amount/price; balance-=req.trade_amount
                pos={"entry":price,"qty":qty,"time":dt,"trail_high":price,"tp1_done":False,"entry_i":i}
        eq=balance+(pos["qty"]*price if pos else 0)
        equity.append({"date":dt,"balance":round(eq,2)})
        peak=max(peak,eq); maxdd=max(maxdd,((peak-eq)/peak)*100 if peak else 0)

    if pos:
        dt=datetime.utcfromtimestamp(times[-1]/1000).strftime("%Y-%m-%d %H:%M")
        record(closes[-1],pos["qty"],"period_end",dt,pos["entry"],pos["time"],pos["entry_i"],len(closes)-1)

    pnls=[t["pnl"] for t in trades]
    wins=[p for p in pnls if p>0]; losses=[p for p in pnls if p<=0]
    if len(equity)>600:
        step=max(1,len(equity)//600); equity=equity[::step]

    return {
        "symbol":req.symbol.upper(),"interval":req.interval,"strategy":strategy,
        "start_date":req.start_date,"end_date":req.end_date,"candles_used":len(klines),
        "initial_balance":req.initial_balance,"final_balance":round(balance,2),
        "total_return_pct":round((balance-req.initial_balance)/req.initial_balance*100,2),
        "total_pnl":round(sum(pnls),2),"total_trades":len(trades),
        "winning_trades":len(wins),"losing_trades":len(losses),
        "win_rate":round(len(wins)/len(trades)*100,1) if trades else 0,
        "avg_pnl":round(sum(pnls)/len(pnls),2) if pnls else 0,
        "best_trade":round(max(pnls),2) if pnls else 0,
        "worst_trade":round(min(pnls),2) if pnls else 0,
        "max_drawdown_pct":round(maxdd,2),
        "profit_factor":round(sum(wins)/abs(sum(losses)),2) if losses and sum(losses)!=0 else 0,
        "tp1_hits":tp1_hits,"tp2_hits":tp2_hits,"sl_hits":sl_hits,
        "avg_hold_candles":round(sum(hold_candles)/len(hold_candles),1) if hold_candles else 0,
        "sl_pct":req.sl_pct,"tp1_pct":req.tp1_pct,"tp2_pct":req.tp2_pct,"trailing_enabled":req.trailing_enabled,
        "trades":trades,"equity_curve":equity,
    }

# ── AI STRATEGY GENERATOR ─────────────────────────────────────────────────────
class AIStrategyReq(BaseModel):
    pair: str="BTCUSDT"; timeframe: str="1h"; risk: str="medium"
    goal: Optional[str]=None

@app.post("/api/ai/strategy")
def ai_suggest_strategy(req: AIStrategyReq, user=Depends(current_user)):
    """Ask the configured AI to design a bot strategy config (JSON), ready to backtest or deploy."""
    c=get_db(); s=c.execute("SELECT * FROM settings WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    provider=(s and s["ai_provider"]) or "anthropic"
    key=_provider_key(s,provider)
    if not key:
        for p in ("groq","gemini","openrouter","anthropic"):
            if _provider_key(s,p): provider=p; key=_provider_key(s,p); break
    if not key: raise HTTPException(400,"No AI provider configured — add a key in Settings → AI Advisor")
    market=""
    try:
        r=requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={req.pair}",timeout=5).json()
        market=f"Current market: last price ${float(r.get('lastPrice',0)):,.2f}, 24h change {r.get('priceChangePercent')}%, 24h volume {float(r.get('volume',0)):,.0f}."
    except: pass
    prompt=(f"Design a crypto trading bot strategy for {req.pair} on the {req.timeframe} timeframe. "
        f"Risk tolerance: {req.risk}. "
        +(f"User goal: {req.goal}. " if req.goal else "")
        +market+" "
        "Choose exactly ONE strategy from this list with its params: "
        "EMA (params: ema_fast, ema_slow), MACD (params: none), BB (params: bb_period, bb_std), "
        "RSI_REV (params: oversold, overbought), GOLDEN (params: none), SUPER (params: st_period, st_mult). "
        "Reply with ONLY a raw JSON object, no markdown fences, exactly this shape: "
        '{"name": "short bot name", "strategy": "EMA", "params": {}, "sl_pct": 1.5, "tp1_pct": 3.0, "tp2_pct": 6.0, '
        '"trailing_enabled": true, "capital_usdt": 100, "reasoning": "2-3 sentences why this fits the market and risk level"}')
    content=_call_provider(provider,key,None,"You are a quantitative crypto strategy designer. Reply with strict raw JSON only — no markdown, no extra text.",[{"role":"user","content":prompt}])
    try:
        start=content.find("{"); end=content.rfind("}")
        cfg=json.loads(content[start:end+1])
    except Exception:
        raise HTTPException(400,f"AI returned an unparseable response — try again. Raw: {content[:200]}")
    def clamp(v,lo,hi,d):
        try: return max(lo,min(hi,float(v)))
        except: return d
    cfg["strategy"]=str(cfg.get("strategy","EMA")).upper()
    if cfg["strategy"] not in ("EMA","MACD","BB","RSI_REV","GOLDEN","SUPER"): cfg["strategy"]="EMA"
    cfg["sl_pct"]=clamp(cfg.get("sl_pct"),0.3,20,1.5)
    cfg["tp1_pct"]=clamp(cfg.get("tp1_pct"),0.5,50,3.0)
    cfg["tp2_pct"]=clamp(cfg.get("tp2_pct"),cfg["tp1_pct"],100,max(6.0,cfg["tp1_pct"]*2))
    cfg["capital_usdt"]=clamp(cfg.get("capital_usdt"),10,100000,100)
    cfg["trailing_enabled"]=bool(cfg.get("trailing_enabled",True))
    if not isinstance(cfg.get("params"),dict): cfg["params"]={}
    cfg["name"]=str(cfg.get("name") or f"AI {cfg['strategy']} Bot")[:40]
    cfg["reasoning"]=str(cfg.get("reasoning",""))[:600]
    cfg["pair"]=req.pair; cfg["timeframe"]=req.timeframe
    return {"config":cfg,"provider":provider,"label":PROVIDER_LABELS.get(provider,provider)}

# ── BOT ───────────────────────────────────────────────────────────────────────
class BotUpdate(BaseModel):
    strategy: Optional[str]=None; trading_pair: Optional[str]=None; market_type: Optional[str]=None
    leverage: Optional[int]=None; trade_amount: Optional[float]=None
    ema_fast: Optional[int]=None; ema_slow: Optional[int]=None; rsi_period: Optional[int]=None
    rsi_buy_threshold: Optional[float]=None; rsi_sell_threshold: Optional[float]=None
    stop_loss_pct: Optional[float]=None; take_profit_pct: Optional[float]=None
    trailing_stop_enabled: Optional[bool]=None; auto_trade: Optional[bool]=None

@app.get("/api/bot/config")
def bot_config(user=Depends(current_user)):
    c=get_db(); cfg=c.execute("SELECT * FROM bot_config WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    return dict(cfg) if cfg else {}

@app.put("/api/bot/config")
def update_bot(req: BotUpdate, user=Depends(current_user)):
    c=get_db(); fields={k:v for k,v in req.dict().items() if v is not None}
    if fields: c.execute(f"UPDATE bot_config SET {','.join(f'{k}=?' for k in fields)} WHERE user_id=?",(*fields.values(),user["id"]))
    c.commit(); c.close(); return {"status":"updated"}

@app.post("/api/bot/start")
def start_bot(user=Depends(current_user)):
    c=get_db(); cfg=c.execute("SELECT mode FROM bot_config WHERE user_id=?",(user["id"],)).fetchone(); mode=cfg["mode"] if cfg else "demo"
    if mode=="live":
        s=c.execute("SELECT binance_api_key FROM settings WHERE user_id=?",(user["id"],)).fetchone()
        if not s or not s["binance_api_key"]: c.close(); raise HTTPException(400,"Live mode requires Binance API keys in Settings")
    c.execute("UPDATE bot_config SET is_running=1 WHERE user_id=?",(user["id"],)); c.commit(); c.close()
    add_alert(user["id"],"info",f"🤖 Bot started in {'🧪 Demo' if mode=='demo' else '⚡ Live'} mode",mode)
    return {"status":"started","mode":mode}

@app.post("/api/bot/stop")
def stop_bot(user=Depends(current_user)):
    c=get_db(); cfg=c.execute("SELECT mode FROM bot_config WHERE user_id=?",(user["id"],)).fetchone(); mode=cfg["mode"] if cfg else "demo"
    c.execute("UPDATE bot_config SET is_running=0 WHERE user_id=?",(user["id"],)); c.commit(); c.close()
    add_alert(user["id"],"warning","⏹ Bot stopped",mode); return {"status":"stopped"}

@app.get("/api/bot/signals/{symbol}")
def get_signals(symbol: str, user=Depends(current_user)):
    cfg=bot_config(user)
    try:
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}&interval=1h&limit=100",timeout=5).json()
        closes=[float(k[4]) for k in r]
    except:
        return {"error":"Could not fetch data"}
    ef=calc_ema(closes,cfg.get("ema_fast",21)); es=calc_ema(closes,cfg.get("ema_slow",55))
    rsi=calc_rsi(closes,cfg.get("rsi_period",14))
    signal="NEUTRAL"
    if len(ef)>=2 and len(es)>=2:
        if ef[-1]>es[-1] and ef[-2]<=es[-2]: signal="BUY"
        elif ef[-1]<es[-1] and ef[-2]>=es[-2]: signal="SELL"
    return {"symbol":symbol.upper(),"signal":signal,"rsi":rsi,
            "ema_fast":round(ef[-1],2) if ef else 0,"ema_slow":round(es[-1],2) if es else 0,
            "price":closes[-1] if closes else 0}

# ── ANALYTICS ─────────────────────────────────────────────────────────────────
@app.get("/api/analytics/pnl-history")
def pnl_history(mode: str="demo", user=Depends(current_user)):
    c=get_db()
    rows=c.execute("""SELECT DATE(closed_at) as date, SUM(pnl) as daily_pnl, COUNT(*) as count,
                      SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) as wins
                      FROM trades WHERE user_id=? AND mode=? AND status='closed' AND closed_at IS NOT NULL
                      GROUP BY DATE(closed_at) ORDER BY date""",(user["id"],mode)).fetchall()
    c.close(); result=[]; cumulative=0
    for r in rows:
        cumulative+=(r["daily_pnl"] or 0)
        result.append({"date":r["date"],"daily_pnl":round(r["daily_pnl"] or 0,2),
                        "cumulative_pnl":round(cumulative,2),"trades":r["count"],"wins":r["wins"]})
    return result

@app.get("/api/analytics/summary")
def performance_summary(mode: str="demo", user=Depends(current_user)):
    c=get_db()
    now=datetime.utcnow()
    def stats(rows):
        pnls=[r["pnl"] for r in rows if r["pnl"] is not None]
        wins=[p for p in pnls if p>0]
        return {"total":len(pnls),"pnl":round(sum(pnls),2),
                "win_rate":round(len(wins)/len(pnls)*100,1) if pnls else 0,
                "best":round(max(pnls),2) if pnls else 0,"worst":round(min(pnls),2) if pnls else 0,
                "avg":round(sum(pnls)/len(pnls),2) if pnls else 0}
    week_ago=(now-timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago=(now-timedelta(days=30)).strftime("%Y-%m-%d")
    w=c.execute("SELECT pnl FROM trades WHERE user_id=? AND mode=? AND status='closed' AND DATE(closed_at)>=?",(user["id"],mode,week_ago)).fetchall()
    m=c.execute("SELECT pnl FROM trades WHERE user_id=? AND mode=? AND status='closed' AND DATE(closed_at)>=?",(user["id"],mode,month_ago)).fetchall()
    a=c.execute("SELECT pnl FROM trades WHERE user_id=? AND mode=? AND status='closed'",(user["id"],mode)).fetchall()
    c.close()
    return {"week":stats(w),"month":stats(m),"all_time":stats(a)}

@app.get("/api/analytics/streak")
def win_streak(mode: str="demo", user=Depends(current_user)):
    c=get_db()
    trades=c.execute("SELECT pnl FROM trades WHERE user_id=? AND mode=? AND status='closed' ORDER BY closed_at DESC LIMIT 100",(user["id"],mode)).fetchall()
    c.close()
    pnls=[t["pnl"] for t in trades if t["pnl"] is not None]
    if not pnls: return {"current_streak":0,"streak_type":"none","max_win_streak":0,"max_loss_streak":0}
    cur=1; stype="win" if pnls[0]>0 else "loss"
    for i in range(1,len(pnls)):
        if (pnls[i]>0)==(pnls[0]>0): cur+=1
        else: break
    max_w=max_l=w=l=0
    for p in reversed(pnls):
        if p>0: w+=1; l=0
        else: l+=1; w=0
        max_w=max(max_w,w); max_l=max(max_l,l)
    return {"current_streak":cur,"streak_type":stype,"max_win_streak":max_w,"max_loss_streak":max_l}

@app.get("/api/trades/export")
def export_csv(mode: str="demo", user=Depends(current_user)):
    c=get_db()
    trades=c.execute("SELECT * FROM trades WHERE user_id=? AND mode=? ORDER BY created_at DESC",(user["id"],mode)).fetchall()
    c.close()
    out=io.StringIO()
    writer=csv.writer(out)
    writer.writerow(["ID","Pair","Side","Entry","Exit","Quantity","PnL","PnL%","Status","Strategy","Opened","Closed"])
    for t in trades:
        writer.writerow([t["id"],t["pair"],t["side"],t["entry_price"],t["exit_price"],t["quantity"],
                         t["pnl"],t["pnl_pct"],t["status"],t["strategy"],t["created_at"],t["closed_at"] or ""])
    out.seek(0)
    return StreamingResponse(io.BytesIO(out.getvalue().encode()),media_type="text/csv",
                             headers={"Content-Disposition":f"attachment; filename=trades_{mode}.csv"})

# ── MARKET ────────────────────────────────────────────────────────────────────
@app.get("/api/market/overview")
def market_overview(user=Depends(current_user)):
    out=[]
    for s in ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT"]:
        try:
            r=requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={s}",timeout=3).json()
            out.append({"symbol":s,"price":float(r.get("lastPrice",0)),"change_pct":float(r.get("priceChangePercent",0)),"volume":float(r.get("volume",0))})
        except:
            out.append({"symbol":s,"price":0,"change_pct":0,"volume":0})
    return out

@app.get("/api/market/price/{symbol}")
def market_price(symbol: str, user=Depends(current_user)):
    try:
        r=requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}",timeout=4).json()
        return {"symbol":symbol.upper(),"price":float(r.get("lastPrice",0)),"change_pct":float(r.get("priceChangePercent",0)),"high":float(r.get("highPrice",0)),"low":float(r.get("lowPrice",0))}
    except:
        return {"symbol":symbol,"price":0,"change_pct":0}

@app.get("/api/market/klines/{symbol}")
def klines(symbol: str, interval: str="1h", limit: int=60, user=Depends(current_user)):
    try:
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}&interval={interval}&limit={limit}",timeout=5).json()
        return [{"time":k[0],"open":float(k[1]),"high":float(k[2]),"low":float(k[3]),"close":float(k[4]),"volume":float(k[5])} for k in r]
    except:
        return []

@app.get("/api/market/fear-greed")
def fear_greed(user=Depends(current_user)):
    try:
        r=requests.get("https://api.alternative.me/fng/?limit=7",timeout=5).json()
        return r.get("data",[])
    except:
        return []

@app.get("/api/market/ema/{symbol}")
def market_ema(symbol: str, ema_fast: int=21, ema_slow: int=55, interval: str="1h", limit: int=100, user=Depends(current_user)):
    try:
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}&interval={interval}&limit={limit}",timeout=5).json()
        times=[k[0] for k in r]; closes=[float(k[4]) for k in r]
        ef=calc_ema(closes,ema_fast); es=calc_ema(closes,ema_slow)
        return {"ema_fast":[{"time":t,"value":round(v,2)} for t,v in zip(times[ema_fast-1:],ef)],
                "ema_slow":[{"time":t,"value":round(v,2)} for t,v in zip(times[ema_slow-1:],es)]}
    except:
        return {"ema_fast":[],"ema_slow":[]}

# ── TRADES ────────────────────────────────────────────────────────────────────
@app.get("/api/trades")
def get_trades(mode: str="demo", user=Depends(current_user)):
    c=get_db(); t=c.execute("SELECT * FROM trades WHERE user_id=? AND mode=? ORDER BY created_at DESC LIMIT 100",(user["id"],mode)).fetchall(); c.close()
    return [dict(x) for x in t]

@app.get("/api/trades/stats")
def trade_stats(mode: str="demo", user=Depends(current_user)):
    c=get_db(); trades=c.execute("SELECT pnl FROM trades WHERE user_id=? AND mode=? AND status='closed'",(user["id"],mode)).fetchall(); c.close()
    pnls=[t["pnl"] for t in trades if t["pnl"] is not None]; wins=[p for p in pnls if p>0]
    return {"total_trades":len(trades),"win_rate":round(len(wins)/len(pnls)*100,1) if pnls else 0,
            "total_pnl":round(sum(pnls),2),"avg_pnl":round(sum(pnls)/len(pnls),2) if pnls else 0,
            "best_trade":round(max(pnls),2) if pnls else 0,"worst_trade":round(min(pnls),2) if pnls else 0}

# ── ALERTS ────────────────────────────────────────────────────────────────────
@app.get("/api/alerts")
def get_alerts(user=Depends(current_user)):
    c=get_db(); a=c.execute("SELECT * FROM alerts WHERE user_id=? ORDER BY created_at DESC LIMIT 50",(user["id"],)).fetchall(); c.close()
    return [dict(x) for x in a]

@app.post("/api/alerts/{aid}/read")
def mark_read(aid: int, user=Depends(current_user)):
    c=get_db(); c.execute("UPDATE alerts SET is_read=1 WHERE id=? AND user_id=?",(aid,user["id"])); c.commit(); c.close()
    return {"status":"ok"}

@app.post("/api/alerts/read-all")
def mark_all_read(user=Depends(current_user)):
    c=get_db(); c.execute("UPDATE alerts SET is_read=1 WHERE user_id=?",(user["id"],)); c.commit(); c.close()
    return {"status":"ok"}

# ── PRICE ALERTS ──────────────────────────────────────────────────────────────
class PriceAlertReq(BaseModel):
    symbol: str; target_price: float; condition: str

@app.get("/api/price-alerts")
def get_price_alerts(user=Depends(current_user)):
    c=get_db(); a=c.execute("SELECT * FROM price_alerts WHERE user_id=? ORDER BY created_at DESC",(user["id"],)).fetchall(); c.close()
    return [dict(x) for x in a]

@app.post("/api/price-alerts")
def create_price_alert(req: PriceAlertReq, user=Depends(current_user)):
    if req.condition not in ("above","below"): raise HTTPException(400,"condition must be above or below")
    c=get_db()
    c.execute("INSERT INTO price_alerts (user_id,symbol,target_price,condition) VALUES (?,?,?,?)",
              (user["id"],req.symbol.upper(),req.target_price,req.condition))
    c.commit(); c.close(); return {"status":"created"}

@app.delete("/api/price-alerts/{aid}")
def delete_price_alert(aid: int, user=Depends(current_user)):
    c=get_db(); c.execute("DELETE FROM price_alerts WHERE id=? AND user_id=?",(aid,user["id"])); c.commit(); c.close()
    return {"status":"deleted"}

# ── MULTI-BOT MANAGEMENT ─────────────────────────────────────────────────────
class BotCreateReq(BaseModel):
    name: str; pair: str="BTCUSDT"; timeframe: str="1h"; strategy: str="EMA"; params: str="{}"
    capital_usdt: float=100; sl_pct: float=1.5; tp1_pct: float=3.0; tp2_pct: float=6.0
    trailing_enabled: bool=True

class BotUpdateReq(BaseModel):
    name: Optional[str]=None; pair: Optional[str]=None; timeframe: Optional[str]=None
    strategy: Optional[str]=None; params: Optional[str]=None
    capital_usdt: Optional[float]=None; sl_pct: Optional[float]=None
    tp1_pct: Optional[float]=None; tp2_pct: Optional[float]=None; trailing_enabled: Optional[bool]=None

@app.get("/api/bots")
def list_bots(user=Depends(current_user)):
    c=get_db(); bots=c.execute("SELECT * FROM bots WHERE user_id=? ORDER BY created_at DESC",(user["id"],)).fetchall(); c.close()
    return [dict(b) for b in bots]

@app.post("/api/bots")
def create_bot(req: BotCreateReq, user=Depends(current_user)):
    c=get_db()
    cur=c.execute("INSERT INTO bots (user_id,name,pair,timeframe,strategy,params,capital_usdt,sl_pct,tp1_pct,tp2_pct,trailing_enabled) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (user["id"],req.name,req.pair,req.timeframe,req.strategy,req.params,req.capital_usdt,req.sl_pct,req.tp1_pct,req.tp2_pct,1 if req.trailing_enabled else 0))
    c.commit(); bot=c.execute("SELECT * FROM bots WHERE id=?",(cur.lastrowid,)).fetchone(); c.close()
    return dict(bot)

@app.get("/api/bots/{bot_id}")
def get_bot(bot_id: int, user=Depends(current_user)):
    c=get_db(); bot=c.execute("SELECT * FROM bots WHERE id=? AND user_id=?",(bot_id,user["id"])).fetchone(); c.close()
    if not bot: raise HTTPException(404,"Bot not found"); return dict(bot)

@app.put("/api/bots/{bot_id}")
def update_bot_record(bot_id: int, req: BotUpdateReq, user=Depends(current_user)):
    c=get_db()
    if not c.execute("SELECT id FROM bots WHERE id=? AND user_id=?",(bot_id,user["id"])).fetchone():
        c.close(); raise HTTPException(404,"Bot not found")
    fields={k:v for k,v in req.dict().items() if v is not None}
    if "trailing_enabled" in fields: fields["trailing_enabled"]=1 if fields["trailing_enabled"] else 0
    if fields:
        c.execute(f"UPDATE bots SET {','.join(f'{k}=?' for k in fields)} WHERE id=?",(*fields.values(),bot_id)); c.commit()
    bot=c.execute("SELECT * FROM bots WHERE id=?",(bot_id,)).fetchone(); c.close(); return dict(bot)

@app.delete("/api/bots/{bot_id}")
def delete_bot(bot_id: int, user=Depends(current_user)):
    c=get_db(); c.execute("DELETE FROM bots WHERE id=? AND user_id=?",(bot_id,user["id"])); c.commit(); c.close(); return {"status":"deleted"}

@app.post("/api/bots/{bot_id}/start")
def start_named_bot(bot_id: int, user=Depends(current_user)):
    c=get_db(); bot=c.execute("SELECT * FROM bots WHERE id=? AND user_id=?",(bot_id,user["id"])).fetchone()
    if not bot: c.close(); raise HTTPException(404,"Bot not found")
    c.execute("UPDATE bots SET is_running=1 WHERE id=?",(bot_id,)); c.commit(); c.close()
    add_alert(user["id"],"info",f"🤖 Bot '{bot['name']}' started ({bot['strategy']} on {bot['pair']})","demo")
    return {"status":"started"}

@app.post("/api/bots/{bot_id}/stop")
def stop_named_bot(bot_id: int, user=Depends(current_user)):
    c=get_db(); bot=c.execute("SELECT * FROM bots WHERE id=? AND user_id=?",(bot_id,user["id"])).fetchone()
    if not bot: c.close(); raise HTTPException(404,"Bot not found")
    c.execute("UPDATE bots SET is_running=0 WHERE id=?",(bot_id,)); c.commit(); c.close()
    add_alert(user["id"],"warning",f"⏹ Bot '{bot['name']}' stopped","demo"); return {"status":"stopped"}

@app.get("/api/bots/{bot_id}/signal")
def bot_signal(bot_id: int, user=Depends(current_user)):
    c=get_db(); bot=c.execute("SELECT * FROM bots WHERE id=? AND user_id=?",(bot_id,user["id"])).fetchone(); c.close()
    if not bot: raise HTTPException(404,"Bot not found")
    signal,rsi_val,info=get_signal(bot["strategy"],bot["pair"],bot["timeframe"],bot["params"] or "{}")
    return {"signal":signal,"rsi":rsi_val,"info":info,"pair":bot["pair"],"strategy":bot["strategy"]}

# ── SETTINGS ──────────────────────────────────────────────────────────────────
class SettingsUpdate(BaseModel):
    binance_api_key: Optional[str]=None; binance_secret_key: Optional[str]=None
    telegram_bot_token: Optional[str]=None; telegram_chat_id: Optional[str]=None
    email_smtp_host: Optional[str]=None; email_smtp_port: Optional[int]=None
    email_username: Optional[str]=None; email_password: Optional[str]=None
    email_alerts_enabled: Optional[bool]=None; telegram_alerts_enabled: Optional[bool]=None
    anthropic_api_key: Optional[str]=None
    ai_provider: Optional[str]=None; ai_model: Optional[str]=None
    groq_api_key: Optional[str]=None; gemini_api_key: Optional[str]=None
    openrouter_api_key: Optional[str]=None

@app.get("/api/settings")
def get_settings(user=Depends(current_user)):
    c=get_db(); s=c.execute("SELECT * FROM settings WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    if not s: return {}
    d=dict(s)
    if d.get("binance_secret_key"): d["binance_secret_key"]="••••"+d["binance_secret_key"][-4:]
    if d.get("email_password"): d["email_password"]="••••••••"
    if d.get("anthropic_api_key"): d["anthropic_api_key"]="sk-ant-••••"+d["anthropic_api_key"][-4:]
    for k in ("groq_api_key","gemini_api_key","openrouter_api_key"):
        if d.get(k): d[k]="••••"+d[k][-4:]
    return d

SECRET_FIELDS={"binance_api_key","binance_secret_key","anthropic_api_key","groq_api_key",
               "gemini_api_key","openrouter_api_key","email_password","telegram_bot_token"}

@app.put("/api/settings")
def update_settings(req: SettingsUpdate, user=Depends(current_user)):
    c=get_db(); fields={k:v for k,v in req.dict().items() if v is not None}
    # Never overwrite a stored secret with its masked placeholder (••••xxxx) or an empty string —
    # the GET endpoint returns masked values and the frontend echoes the whole object back on save.
    fields={k:v for k,v in fields.items()
            if not (k in SECRET_FIELDS and isinstance(v,str) and ("••" in v or v.strip()==""))}
    if fields: c.execute(f"UPDATE settings SET {','.join(f'{k}=?' for k in fields)} WHERE user_id=?",(*fields.values(),user["id"]))
    c.commit(); c.close(); return {"status":"updated"}

@app.post("/api/notify/test-telegram")
def test_telegram(user=Depends(current_user)):
    c=get_db(); s=c.execute("SELECT * FROM settings WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    if not s or not s["telegram_bot_token"]: raise HTTPException(400,"Telegram not configured")
    r=requests.post(f"https://api.telegram.org/bot{s['telegram_bot_token']}/sendMessage",json={"chat_id":s["telegram_chat_id"],"text":"✅ CryptoBot Pro v3 connected!"},timeout=5)
    if r.status_code==200: return {"status":"sent"}
    raise HTTPException(400,r.text)

@app.post("/api/notify/test-email")
def test_email(user=Depends(current_user)):
    c=get_db(); s=c.execute("SELECT * FROM settings WHERE user_id=?",(user["id"],)).fetchone(); u=c.execute("SELECT email FROM users WHERE id=?",(user["id"],)).fetchone(); c.close()
    if not s or not s["email_smtp_host"]: raise HTTPException(400,"Email not configured")
    try:
        msg=MIMEMultipart(); msg["From"]=s["email_username"]; msg["To"]=u["email"]; msg["Subject"]="✅ CryptoBot Pro — Email Working"
        msg.attach(MIMEText("<h2>Email alerts are working!</h2>","html"))
        with smtplib.SMTP(s["email_smtp_host"],s["email_smtp_port"]) as srv:
            srv.starttls(); srv.login(s["email_username"],s["email_password"]); srv.send_message(msg)
        return {"status":"sent"}
    except Exception as e:
        raise HTTPException(400,str(e))

@app.post("/api/settings/test-binance")
def test_binance_connection(user=Depends(current_user)):
    c=get_db(); s=c.execute("SELECT binance_api_key,binance_secret_key FROM settings WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    if not s or not s["binance_api_key"] or not s["binance_secret_key"]:
        raise HTTPException(400,"No API keys saved — enter and save your Binance API key + secret first")
    api_key=s["binance_api_key"]; secret=s["binance_secret_key"]
    if api_key.startswith("••") or secret.startswith("••"):
        raise HTTPException(400,"Keys appear masked — re-enter your actual key and secret, save, then test again")

    def signed_get(base,path):
        ts=int(time.time()*1000); qs=f"timestamp={ts}"
        sig=hmac.new(secret.encode(),qs.encode(),hashlib.sha256).hexdigest()
        r=requests.get(f"{base}{path}?{qs}&signature={sig}",headers={"X-MBX-APIKEY":api_key},timeout=10)
        return r.status_code,r.json()

    # connectivity check
    try:
        ping=requests.get("https://api.binance.com/api/v3/ping",timeout=5)
        if ping.status_code!=200: return{"status":"error","message":"Cannot reach Binance — check your internet connection"}
    except Exception as e: return{"status":"error","message":f"Network error: {e}"}

    # spot account test
    try:
        code,data=signed_get("https://api.binance.com","/api/v3/account")
        if code!=200 or "code" in data:
            bc=data.get("code",0); msg=data.get("msg","Binance error")
            if bc in(-2014,-2015): return{"status":"invalid_key","message":"Invalid API key or signature — check you pasted the correct key and secret","binance_code":bc}
            return{"status":"error","message":msg,"binance_code":bc}
        permissions=data.get("permissions",[]); can_trade=data.get("canTrade",False); can_withdraw=data.get("canWithdraw",False)
        balances={b["asset"]:round(float(b["free"])+float(b["locked"]),8) for b in data.get("balances",[]) if float(b["free"])+float(b["locked"])>0}
        usdt_free=round(float(next((b["free"] for b in data.get("balances",[]) if b["asset"]=="USDT"),0)),2)
        top5=dict(sorted(balances.items(),key=lambda x:-x[1])[:5])
        spot={"ok":True,"can_trade":can_trade,"can_withdraw":can_withdraw,"permissions":permissions,"usdt_free":usdt_free,"top_balances":top5}
    except Exception as e: return{"status":"error","message":str(e)}

    # futures test (optional — may fail without futures enabled)
    futures=None
    try:
        fcode,fdata=signed_get("https://fapi.binance.com","/fapi/v1/account")
        if fcode==200 and "totalWalletBalance" in fdata:
            futures={"ok":True,"wallet_balance":round(float(fdata.get("totalWalletBalance",0)),2),"unrealized_pnl":round(float(fdata.get("totalUnrealizedProfit",0)),2)}
        else:
            fmsg=fdata.get("msg",""); fbc=fdata.get("code",0)
            futures={"ok":False,"binance_code":fbc,"message":fmsg,
                     "needs_ip_restriction":"IP Access Restriction" in fmsg or fbc==-1130,
                     "key_before_futures":"created before" in fmsg.lower() or fbc==-1130}
    except Exception as e: futures={"ok":False,"message":str(e)}

    return{"status":"ok","spot":spot,"futures":futures}

@app.post("/api/notify/daily-summary")
def daily_summary(user=Depends(current_user)):
    c=get_db(); today=datetime.utcnow().strftime("%Y-%m-%d")
    trades=c.execute("SELECT pnl FROM trades WHERE user_id=? AND status='closed' AND DATE(closed_at)=?",(user["id"],today)).fetchall()
    s=c.execute("SELECT * FROM settings WHERE user_id=?",(user["id"],)).fetchone()
    f=c.execute("SELECT * FROM funds WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    pnls=[t["pnl"] for t in trades if t["pnl"] is not None]; wins=[p for p in pnls if p>0]
    bal=f["demo_balance"] if f else 0
    text=(f"📊 <b>CryptoBot Daily Summary</b>\n📅 {today}\n\n"
          f"💰 Demo Balance: ${bal:,.2f}\n📈 Trades Today: {len(pnls)}\n"
          f"✅ Wins: {len(wins)} ❌ Losses: {len(pnls)-len(wins)}\n"
          f"💵 PnL Today: ${sum(pnls):+.2f}")
    if s and s["telegram_bot_token"] and s["telegram_alerts_enabled"]:
        send_telegram(s["telegram_bot_token"],s["telegram_chat_id"],text)
        return {"status":"sent","summary":text}
    return {"status":"no_telegram","summary":text}

# ── AI CHAT PROXY ─────────────────────────────────────────────────────────────
class ChatReq(BaseModel):
    messages: list; mode: str="demo"
    provider: Optional[str]=None  # override settings: groq|gemini|openrouter|anthropic|all
    model: Optional[str]=None     # per-request model override (from chat page dropdown)

AI_SYSTEM = "You are CryptoBot Pro's AI trading advisor. Be concise and practical. Focus on EMA/RSI/MACD strategy, Binance, risk management, and demo vs live trading best practices."

def _openai_compat(base_url, api_key, model, system, messages, extra_headers={}):
    """Call any OpenAI-compatible API (Groq, OpenRouter, etc.)."""
    body=json.dumps({"model":model,"max_tokens":1024,
        "messages":[{"role":"system","content":system}]+list(messages)},
        ensure_ascii=False).encode("utf-8")
    r=requests.post(f"{base_url}/chat/completions",
        headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json; charset=utf-8",**extra_headers},
        data=body,timeout=30)
    data=json.loads(r.content.decode("utf-8"))
    if r.status_code!=200: raise HTTPException(400,data.get("error",{}).get("message","API error"))
    return data["choices"][0]["message"]["content"]

def _gemini(api_key, model, system, messages):
    """Call Google Gemini API."""
    contents=[{"role":"model" if m["role"]=="assistant" else "user","parts":[{"text":m["content"]}]} for m in messages]
    body=json.dumps({"systemInstruction":{"parts":[{"text":system}]},"contents":contents,
        "generationConfig":{"maxOutputTokens":1024}},ensure_ascii=False).encode("utf-8")
    r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        headers={"Content-Type":"application/json; charset=utf-8"},data=body,timeout=30)
    data=json.loads(r.content.decode("utf-8"))
    if r.status_code!=200: raise HTTPException(400,data.get("error",{}).get("message","Gemini error"))
    return data["candidates"][0]["content"]["parts"][0]["text"]

PROVIDER_LABELS={"groq":"Groq (Llama 3.3)","gemini":"Google Gemini","openrouter":"OpenRouter","anthropic":"Claude (Anthropic)"}

_OR_FREE_CACHE={"ts":0,"models":[]}
def openrouter_free_models():
    """Live list of currently-free OpenRouter models (cached 1h) — hardcoded slugs go stale."""
    if time.time()-_OR_FREE_CACHE["ts"]<3600 and _OR_FREE_CACHE["models"]:
        return _OR_FREE_CACHE["models"]
    try:
        r=requests.get("https://openrouter.ai/api/v1/models",timeout=10)
        data=json.loads(r.content.decode("utf-8"))
        free=[str(m.get("id","")) for m in data.get("data",[]) if str(m.get("id","")).endswith(":free")]
        def prio(mid):
            for i,kw in enumerate(("llama-3.3","deepseek","qwen","llama","gemma","mistral")):
                if kw in mid.lower(): return i
            return 99
        free.sort(key=prio)
        if free:
            _OR_FREE_CACHE["ts"]=time.time(); _OR_FREE_CACHE["models"]=free
            return free
    except Exception as e:
        print("OpenRouter model list error:",e)
    return ["meta-llama/llama-3.3-70b-instruct:free","deepseek/deepseek-chat-v3-0324:free","qwen/qwen-2.5-72b-instruct:free"]

def _provider_key(s, provider):
    """Return the saved API key for a provider, or '' if not configured."""
    if provider=="groq": return (s and s["groq_api_key"]) or ""
    if provider=="gemini": return (s and s["gemini_api_key"]) or ""
    if provider=="openrouter": return (s and s["openrouter_api_key"]) or ""
    if provider=="anthropic": return (s and s["anthropic_api_key"]) or os.environ.get("ANTHROPIC_API_KEY","")
    return ""

def _call_provider(provider, key, model_override, system, messages):
    """Call one AI provider, return response text. Raises HTTPException on error."""
    if provider=="groq":
        if not key: raise HTTPException(400,"No Groq API key — add it in Settings → AI Advisor (free at console.groq.com)")
        model=model_override or "llama-3.3-70b-versatile"
        return _openai_compat("https://api.groq.com/openai/v1",key,model,system,messages)
    elif provider=="openrouter":
        if not key: raise HTTPException(400,"No OpenRouter API key — add it in Settings → AI Advisor (free at openrouter.ai)")
        hdrs={"HTTP-Referer":"http://localhost:3000","X-Title":"CryptoBot Pro"}
        # OpenRouter rotates its free models — fetch the live free list and try until one works.
        # A saved model is tried first, but if it was retired we still fall through the chain.
        free_chain=openrouter_free_models()[:6]
        candidates=([model_override] if model_override else [])+[m for m in free_chain if m!=model_override]
        last_err="OpenRouter error"
        for m in candidates:
            try:
                return _openai_compat("https://openrouter.ai/api/v1",key,m,system,messages,extra_headers=hdrs)
            except HTTPException as e:
                last_err=str(e.detail)
                low=last_err.lower()
                # key/credit problems won't be fixed by another model — fail fast
                if any(w in low for w in ("api key","auth","credit","quota exceeded")): raise
                # model unavailable/retired → try next candidate
                continue
        raise HTTPException(400,f"All free OpenRouter models failed — last error: {last_err}. Pick a model manually in Settings → AI Advisor (check openrouter.ai/models?q=free for current free models)")
    elif provider=="gemini":
        if not key: raise HTTPException(400,"No Gemini API key — add it in Settings → AI Advisor (free at aistudio.google.com)")
        model=model_override or "gemini-1.5-flash"
        return _gemini(key,model,system,messages)
    else:  # anthropic
        if not key: raise HTTPException(400,"No Anthropic API key — add it in Settings → AI Advisor (or switch to Groq/Gemini free tier)")
        model=model_override or "claude-haiku-4-5-20251001"
        body=json.dumps({"model":model,"max_tokens":1024,"system":system,"messages":messages},
            ensure_ascii=False).encode("utf-8")
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json; charset=utf-8"},
            data=body,timeout=30)
        data=json.loads(r.content.decode("utf-8"))
        if r.status_code!=200: raise HTTPException(400,data.get("error",{}).get("message","AI error"))
        return data["content"][0]["text"]

@app.get("/api/chat/providers")
def chat_providers(user=Depends(current_user)):
    """Which AI providers have keys configured + which is the default."""
    c=get_db(); s=c.execute("SELECT * FROM settings WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    out=[]
    for p in ("groq","gemini","openrouter","anthropic"):
        out.append({"id":p,"label":PROVIDER_LABELS[p],"configured":bool(_provider_key(s,p))})
    return {"providers":out,"default":(s and s["ai_provider"]) or "anthropic"}

PROVIDER_MODELS={
    "groq":["llama-3.3-70b-versatile","llama-3.1-8b-instant","deepseek-r1-distill-llama-70b","gemma2-9b-it"],
    "gemini":["gemini-1.5-flash","gemini-2.0-flash","gemini-1.5-pro"],
    "anthropic":["claude-haiku-4-5-20251001","claude-sonnet-4-6"],
}

@app.get("/api/chat/models")
def chat_models(provider: str="openrouter", user=Depends(current_user)):
    """Model list for the chat page dropdown — OpenRouter list is fetched live (free models only)."""
    if provider=="openrouter": return {"models":openrouter_free_models()[:30]}
    return {"models":PROVIDER_MODELS.get(provider,[])}

def _save_chat(uid, role, content, provider=None):
    try:
        c=get_db(); c.execute("INSERT INTO chat_messages (user_id,role,content,provider) VALUES (?,?,?,?)",(uid,role,content,provider)); c.commit(); c.close()
    except Exception as e:
        print("Chat save error:",e)

@app.get("/api/chat/history")
def chat_history(user=Depends(current_user)):
    c=get_db(); rows=c.execute("SELECT id,role,content,provider,created_at FROM chat_messages WHERE user_id=? ORDER BY id ASC LIMIT 500",(user["id"],)).fetchall(); c.close()
    return [dict(r) for r in rows]

@app.delete("/api/chat/history")
def clear_chat_history(user=Depends(current_user)):
    c=get_db(); c.execute("DELETE FROM chat_messages WHERE user_id=?",(user["id"],)); c.commit(); c.close()
    return {"status":"cleared"}

@app.delete("/api/chat/history/{mid}")
def delete_chat_message(mid: int, user=Depends(current_user)):
    c=get_db(); c.execute("DELETE FROM chat_messages WHERE id=? AND user_id=?",(mid,user["id"])); c.commit(); c.close()
    return {"status":"deleted"}

@app.post("/api/chat")
def ai_chat(req: ChatReq, user=Depends(current_user)):
    c=get_db(); s=c.execute("SELECT * FROM settings WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    provider=req.provider or (s and s["ai_provider"]) or "anthropic"
    # explicit model from chat dropdown wins; settings ai_model applies only with the settings default provider
    model_override=req.model or (None if req.provider else ((s and s["ai_model"]) or None))
    system=f"{AI_SYSTEM} User is in {req.mode.upper()} mode."
    # Sanitize history: collapse consecutive same-role messages (Compare-All saves several
    # assistant rows in a row, which Anthropic/Gemini reject), start with user, cap at 20
    msgs=[]
    for m in req.messages:
        role=m.get("role"); content=str(m.get("content","") or "")
        if not content or role not in ("user","assistant"): continue
        if msgs and msgs[-1]["role"]==role: msgs[-1]["content"]+="\n\n"+content
        else: msgs.append({"role":role,"content":content})
    msgs=msgs[-20:]
    while msgs and msgs[0]["role"]!="user": msgs.pop(0)
    if not msgs: raise HTTPException(400,"No user message")
    last_user=msgs[-1]["content"] if msgs[-1]["role"]=="user" else None
    try:
        # Compare mode: ask every configured provider at once
        if provider=="all":
            configured=[p for p in ("groq","gemini","openrouter","anthropic") if _provider_key(s,p)]
            if not configured: raise HTTPException(400,"No AI provider keys configured — add at least one in Settings → AI Advisor")
            from concurrent.futures import ThreadPoolExecutor
            def ask(p):
                try:
                    return {"provider":p,"label":PROVIDER_LABELS[p],
                            "content":_call_provider(p,_provider_key(s,p),None,system,msgs)}
                except HTTPException as e:
                    return {"provider":p,"label":PROVIDER_LABELS[p],"error":str(e.detail)}
                except Exception as e:
                    return {"provider":p,"label":PROVIDER_LABELS[p],"error":str(e)}
            with ThreadPoolExecutor(max_workers=4) as pool:
                results=list(pool.map(ask,configured))
            if last_user and any(r.get("content") for r in results):
                _save_chat(user["id"],"user",last_user)
                for r in results:
                    if r.get("content"): _save_chat(user["id"],"assistant",r["content"],r["provider"])
            return {"results":results,"mode":"all"}
        # Single provider (request override or settings default)
        content=_call_provider(provider,_provider_key(s,provider),model_override,system,msgs)
        if last_user:
            _save_chat(user["id"],"user",last_user)
            _save_chat(user["id"],"assistant",content,provider)
        return {"content":content,"provider":provider,"label":PROVIDER_LABELS.get(provider,provider)}
    except HTTPException: raise
    except UnicodeEncodeError as e:
        raise HTTPException(500,f"Encoding error ({e})")
    except Exception as e:
        raise HTTPException(500,str(e))

# ── SERVE BUILT FRONTEND (production / single-service deploy) ──────────────────
# Mounted last so all /api routes above take priority. In local dev the dist folder
# usually doesn't exist (you run `npm run dev` separately) — guarded so it's a no-op.
from fastapi.staticfiles import StaticFiles
_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=False)
