from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import jwt, bcrypt, sqlite3, requests, smtplib, threading, time, io, csv, os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="CryptoBot Pro", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
    ]:
        try: c.execute(stmt)
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

def run_auto_bot():
    c = get_db()
    try:
        check_price_alerts(c)
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

def _bot_loop():
    while True:
        try: run_auto_bot()
        except Exception as e: print("Bot thread error:",e)
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

@app.post("/api/demo/trade")
def place_trade(req: DemoTradeReq, user=Depends(current_user)):
    c=get_db()
    f=c.execute("SELECT * FROM funds WHERE user_id=?",(user["id"],)).fetchone()
    cfg=c.execute("SELECT * FROM bot_config WHERE user_id=?",(user["id"],)).fetchone()
    if not f: raise HTTPException(400,"Funds not found")
    balance=f["demo_balance"]; max_pct=f["max_trade_size_pct"] or 10; max_usdt=balance*(max_pct/100)
    if req.amount_usdt>max_usdt: raise HTTPException(400,f"Trade ${req.amount_usdt:.0f} exceeds max ${max_usdt:.0f} ({max_pct}% of balance)")
    if req.amount_usdt>balance: raise HTTPException(400,f"Insufficient balance: ${balance:.2f}")
    open_cnt=c.execute("SELECT COUNT(*) as n FROM trades WHERE user_id=? AND mode='demo' AND status='open'",(user["id"],)).fetchone()["n"]
    max_open=f["max_open_trades"] or 3
    if open_cnt>=max_open: raise HTTPException(400,f"Max {max_open} open trades reached")
    price=live_price(req.pair)
    if price==0: raise HTTPException(400,"Could not fetch live price from Binance")
    qty=round(req.amount_usdt/price,6)
    sl_pct=cfg["stop_loss_pct"] if cfg else 1.5
    c.execute("UPDATE funds SET demo_balance=? WHERE user_id=?",(balance-req.amount_usdt,user["id"]))
    cur=c.execute("INSERT INTO trades (user_id,mode,pair,side,entry_price,quantity,status,strategy,trailing_stop_pct) VALUES (?,?,?,?,?,?,'open',?,?)",
                  (user["id"],"demo",req.pair,req.side,price,qty,cfg["strategy"] if cfg else "MANUAL",sl_pct))
    tid=cur.lastrowid; c.commit(); c.close()
    add_alert(user["id"],"info",f"📈 {'Bought' if req.side=='BUY' else 'Sold'} {req.pair} @ ${price:,.2f} — ${req.amount_usdt:.0f} USDT","demo")
    return {"trade_id":tid,"pair":req.pair,"side":req.side,"price":price,"quantity":qty,"amount_usdt":req.amount_usdt}

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

@app.get("/api/demo/open-trades")
def open_trades(user=Depends(current_user)):
    c=get_db()
    trades=c.execute("SELECT * FROM trades WHERE user_id=? AND mode='demo' AND status='open' ORDER BY created_at DESC",(user["id"],)).fetchall()
    c.close(); out=[]
    for t in trades:
        d=dict(t); p=live_price(t["pair"])
        if p and t["entry_price"]:
            qty=t["quantity"] or 0
            unreal=((p-t["entry_price"])*qty) if t["side"]=="BUY" else ((t["entry_price"]-p)*qty)
            d["current_price"]=p; d["unrealized_pnl"]=round(unreal,4)
            d["unrealized_pct"]=round((unreal/(t["entry_price"]*qty))*100,2) if t["entry_price"]*qty else 0
            if t["trailing_high"]:
                sl=t["trailing_stop_pct"] or 1.5
                d["stop_price"]=round(t["trailing_high"]*(1-sl/100),2)
        out.append(d)
    return out

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

# ── SETTINGS ──────────────────────────────────────────────────────────────────
class SettingsUpdate(BaseModel):
    binance_api_key: Optional[str]=None; binance_secret_key: Optional[str]=None
    telegram_bot_token: Optional[str]=None; telegram_chat_id: Optional[str]=None
    email_smtp_host: Optional[str]=None; email_smtp_port: Optional[int]=None
    email_username: Optional[str]=None; email_password: Optional[str]=None
    email_alerts_enabled: Optional[bool]=None; telegram_alerts_enabled: Optional[bool]=None
    anthropic_api_key: Optional[str]=None

@app.get("/api/settings")
def get_settings(user=Depends(current_user)):
    c=get_db(); s=c.execute("SELECT * FROM settings WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    if not s: return {}
    d=dict(s)
    if d.get("binance_secret_key"): d["binance_secret_key"]="••••"+d["binance_secret_key"][-4:]
    if d.get("email_password"): d["email_password"]="••••••••"
    if d.get("anthropic_api_key"): d["anthropic_api_key"]="sk-ant-••••"+d["anthropic_api_key"][-4:]
    return d

@app.put("/api/settings")
def update_settings(req: SettingsUpdate, user=Depends(current_user)):
    c=get_db(); fields={k:v for k,v in req.dict().items() if v is not None}
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

@app.post("/api/chat")
def ai_chat(req: ChatReq, user=Depends(current_user)):
    c=get_db(); s=c.execute("SELECT anthropic_api_key FROM settings WHERE user_id=?",(user["id"],)).fetchone(); c.close()
    api_key=(s["anthropic_api_key"] if s and s["anthropic_api_key"] else None) or os.environ.get("ANTHROPIC_API_KEY","")
    if not api_key: raise HTTPException(400,"No Anthropic API key — add it in Settings → AI Advisor tab")
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-haiku-4-5-20251001","max_tokens":1024,
                  "system":f"You are CryptoBot Pro's AI trading advisor. User is in {req.mode.upper()} mode. Be concise and practical. Focus on EMA/RSI strategy, Binance, risk management, and demo vs live trading best practices.",
                  "messages":req.messages},timeout=30)
        data=r.json()
        if r.status_code!=200: raise HTTPException(400,data.get("error",{}).get("message","AI error"))
        return {"content":data["content"][0]["text"]}
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(500,str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
