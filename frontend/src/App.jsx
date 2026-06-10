import { useState, useEffect, useRef } from "react";

const API = "http://localhost:8000";
function api(path, opts = {}, token) {
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(opts.headers || {}) },
  }).then(r => r.json()).catch(() => ({}));
}

const paths = {
  dashboard:"M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z",
  chart:"M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z",
  bot:"M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7H4a7 7 0 017-7h1V5.73A2 2 0 0110 4a2 2 0 012-2zM7 14v2a5 5 0 0010 0v-2H7zm3 3v1h4v-1h-4z",
  trade:"M7 14l5-5 5 5H7zm0-4h10v1H7v-1z",
  alert:"M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z",
  settings:"M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.57 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.21.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z",
  chat:"M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z",
  logout:"M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z",
  play:"M8 5v14l11-7z", stop:"M6 6h12v12H6z",
  send:"M2.01 21L23 12 2.01 3 2 10l15 2-15 2z",
  check:"M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
  trend_up:"M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z",
  analytics:"M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z",
  key:"M12.65 10A5.99 5.99 0 007 6c-3.31 0-6 2.69-6 6s2.69 6 6 6a5.99 5.99 0 005.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z",
  bell:"M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z",
  mail:"M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z",
  refresh:"M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
  user:"M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z",
  shield:"M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z",
  warning:"M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z",
  money:"M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z",
  portfolio:"M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z",
};

const Icon = ({ name, size=18, className="" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d={paths[name]||paths.chart}/>
  </svg>
);

const ModeBadge = ({ mode }) => (
  <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider border ${mode==="live"?"bg-red-500/15 border-red-500/40 text-red-400":"bg-amber-400/15 border-amber-400/40 text-amber-400"}`}>
    <span className={`w-1.5 h-1.5 rounded-full ${mode==="live"?"bg-red-400 animate-pulse":"bg-amber-400"}`}/>
    {mode==="live"?"LIVE":"DEMO"}
  </span>
);

const Toggle = ({ value, onChange }) => (
  <button onClick={()=>onChange(!value)} className={`w-12 h-6 rounded-full transition-colors relative flex-shrink-0 ${value?"bg-cyan-500":"bg-slate-700"}`}>
    <div className={`absolute w-5 h-5 bg-white rounded-full top-0.5 transition-transform shadow ${value?"translate-x-6":"translate-x-0.5"}`}/>
  </button>
);

const Input = ({ label, value, onChange, type="text", placeholder="", readOnly=false, hint }) => (
  <div>
    {label && <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">{label}</label>}
    <input type={type} readOnly={readOnly} placeholder={placeholder}
      className={`w-full bg-slate-800 border rounded-lg px-4 py-2.5 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors ${readOnly?"opacity-60 cursor-not-allowed border-slate-700":"border-slate-700"}`}
      value={value??""} onChange={e=>!readOnly&&onChange(type==="number"?parseFloat(e.target.value)||0:e.target.value)}/>
    {hint && <p className="text-slate-600 text-xs mt-1">{hint}</p>}
  </div>
);

const Select = ({ label, value, onChange, options }) => (
  <div>
    {label && <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">{label}</label>}
    <select className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500"
      value={value??""} onChange={e=>onChange(e.target.value)}>
      {options.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

const StatCard = ({ label, value, sub, icon, color="cyan" }) => {
  const c={cyan:"from-cyan-500/10 to-cyan-500/5 border-cyan-500/20 text-cyan-400",green:"from-green-500/10 to-green-500/5 border-green-500/20 text-green-400",violet:"from-violet-500/10 to-violet-500/5 border-violet-500/20 text-violet-400",amber:"from-amber-500/10 to-amber-500/5 border-amber-500/20 text-amber-400",red:"from-red-500/10 to-red-500/5 border-red-500/20 text-red-400"};
  return (
    <div className={`bg-gradient-to-br ${c[color]} border rounded-xl p-5`}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">{label}</span>
        <span className={c[color].split(" ").pop()}><Icon name={icon} size={16}/></span>
      </div>
      <div className="text-white font-bold text-2xl tracking-tight">{value}</div>
      {sub && <div className="text-slate-500 text-xs mt-1">{sub}</div>}
    </div>
  );
};

const CandleChart = ({ klines, emaFast=[], emaSlow=[] }) => {
  if (!klines?.length) return <div className="flex items-center justify-center h-full text-slate-500 text-sm">Loading chart…</div>;
  const w=700,h=200,prices=klines.flatMap(k=>[k.high,k.low]),minP=Math.min(...prices),maxP=Math.max(...prices),range=maxP-minP||1,cw=Math.floor(w/klines.length)-1,toY=p=>h-((p-minP)/range)*(h-20)-10,toX=i=>i*(cw+1)+cw/2;
  const emaLine=(data,col)=>{
    if(!data?.length) return null;
    const offset=klines.length-data.length;
    const pts=data.map((v,i)=>`${toX(i+offset)},${toY(v.value??v)}`).join(" ");
    return <polyline points={pts} fill="none" stroke={col} strokeWidth="1.5" opacity="0.85"/>;
  };
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full">
      {klines.map((k,i)=>{
        const x=toX(i),bull=k.close>=k.open,col=bull?"#22c55e":"#ef4444",bodyTop=toY(Math.max(k.open,k.close)),bodyH=Math.max(2,Math.abs(toY(k.open)-toY(k.close)));
        return <g key={i}><line x1={x} y1={toY(k.high)} x2={x} y2={toY(k.low)} stroke={col} strokeWidth="1"/><rect x={i*(cw+1)} y={bodyTop} width={cw} height={bodyH} fill={col}/></g>;
      })}
      {emaLine(emaFast,"#22d3ee")}
      {emaLine(emaSlow,"#a78bfa")}
    </svg>
  );
};

// ── MODE SWITCHER ─────────────────────────────────────────────────────────────
const ModeSwitcher = ({ mode, onSwitch }) => {
  const [confirm, setConfirm] = useState(false);
  return (
    <>
      <div className="flex items-center gap-1 bg-slate-800/80 border border-slate-700 rounded-xl p-1">
        <button onClick={()=>mode==="live"&&onSwitch("demo")}
          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-bold transition-all ${mode==="demo"?"bg-amber-400/20 text-amber-400 border border-amber-400/30":"text-slate-500 hover:text-slate-300"}`}>
          🧪 Demo
        </button>
        <button onClick={()=>mode==="demo"?setConfirm(true):null}
          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-bold transition-all ${mode==="live"?"bg-red-500/20 text-red-400 border border-red-500/30":"text-slate-500 hover:text-slate-300"}`}>
          ⚡ Live
        </button>
      </div>
      {confirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-red-500/40 rounded-2xl p-6 max-w-sm w-full shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-500/20 rounded-full flex items-center justify-center text-red-400"><Icon name="warning" size={20}/></div>
              <h3 className="text-white font-bold text-lg">Switch to Live Trading?</h3>
            </div>
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-5 space-y-1.5 text-sm text-red-300">
              <p className="font-bold text-red-400">⚠️ Real money will be at risk</p>
              <p>• Orders execute on real Binance account</p>
              <p>• Losses are permanent — no reset button</p>
              <p>• Requires Binance API keys in Settings</p>
              <p>• Bot stops automatically when switching</p>
            </div>
            <div className="flex gap-3">
              <button onClick={()=>setConfirm(false)} className="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-xl font-medium text-sm">Cancel</button>
              <button onClick={()=>{setConfirm(false);onSwitch("live");}} className="flex-1 bg-red-500 hover:bg-red-400 text-white py-2.5 rounded-xl font-bold text-sm">Yes, Go Live</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

// ── LOGIN ─────────────────────────────────────────────────────────────────────
const LoginPage = ({ onLogin }) => {
  const [form, setForm] = useState({username:"",password:""});
  const [isReg, setIsReg] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true); setError("");
    if (isReg) {
      if (!name.trim()) { setError("Full name is required"); setLoading(false); return; }
      if (form.password !== confirmPw) { setError("Passwords do not match"); setLoading(false); return; }
      if (form.password.length < 6) { setError("Password must be at least 6 characters"); setLoading(false); return; }
    }
    const body = isReg ? {...form, email, name} : form;
    const res = await api(isReg?"/api/auth/register":"/api/auth/login",{method:"POST",body:JSON.stringify(body)});
    if (res.token) onLogin(res); else setError(res.detail||"Login failed");
    setLoading(false);
  };

  const resetRegFields = () => { setName(""); setEmail(""); setConfirmPw(""); setError(""); };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl"/>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/5 rounded-full blur-3xl"/>
      </div>
      <div className="w-full max-w-md relative">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-2">
            <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-violet-500 rounded-xl flex items-center justify-center"><span className="text-white font-bold text-lg">₿</span></div>
            <span className="text-2xl font-bold text-white">CryptoBot <span className="text-cyan-400">Pro</span></span>
          </div>
          <p className="text-slate-400 text-sm">Demo & Live algorithmic trading</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
          <h2 className="text-white font-semibold text-xl mb-6">{isReg?"Create Account":"Sign In"}</h2>

          <div className="space-y-4">
            {isReg && (
              <Input label="Full Name" value={name} onChange={setName} placeholder="Your full name"/>
            )}
            <Input label="Username" value={form.username} onChange={v=>setForm(f=>({...f,username:v}))} placeholder="Choose a username"/>
            {isReg && (
              <Input label="Email Address" value={email} onChange={setEmail} placeholder="your@email.com"/>
            )}
            <Input label="Password" type="password" value={form.password} onChange={v=>setForm(f=>({...f,password:v}))} placeholder="••••••••" hint={isReg?"Minimum 6 characters":undefined}/>
            {isReg && (
              <Input label="Confirm Password" type="password" value={confirmPw} onChange={setConfirmPw} placeholder="Repeat your password"/>
            )}
          </div>

          {error && (
            <div className="mt-4 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 flex items-start gap-2">
              <Icon name="warning" size={15} className="flex-shrink-0 mt-0.5"/>
              {error}
            </div>
          )}

          <button onClick={submit} disabled={loading}
            className="w-full mt-6 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 shadow-lg shadow-cyan-500/20">
            {loading?"Please wait…":isReg?"Create Account":"Sign In"}
          </button>

          <p className="text-center text-slate-500 text-sm mt-4">
            {isReg?"Already have an account? ":"Don't have an account? "}
            <button onClick={()=>{setIsReg(!isReg);resetRegFields();setForm({username:"",password:""});}}
              className="text-cyan-400 hover:text-cyan-300 font-medium">{isReg?"Sign In":"Register"}</button>
          </p>
          {!isReg && <p className="text-center text-slate-600 text-xs mt-2">Demo: <span className="text-slate-400 font-medium">demo / demo123</span></p>}
        </div>
      </div>
    </div>
  );
};

// ── DASHBOARD ─────────────────────────────────────────────────────────────────
const DashboardPage = ({ token, mode }) => {
  const [market,setMarket]=useState([]);
  const [stats,setStats]=useState({});
  const [botCfg,setBotCfg]=useState({});
  const [klines,setKlines]=useState([]);
  const [pair,setPair]=useState("BTCUSDT");
  const [funds,setFunds]=useState({});
  const [emaData,setEmaData]=useState({ema_fast:[],ema_slow:[]});
  const [fearGreed,setFearGreed]=useState([]);

  useEffect(()=>{
    const load=async()=>{
      const [m,s,b,k,f,ema,fg]=await Promise.all([
        api("/api/market/overview",{},token),
        api(`/api/trades/stats?mode=${mode}`,{},token),
        api("/api/bot/config",{},token),
        api(`/api/market/klines/${pair}?interval=1h&limit=60`,{},token),
        api("/api/funds",{},token),
        api(`/api/market/ema/${pair}?interval=1h&limit=60`,{},token),
        api("/api/market/fear-greed",{},token),
      ]);
      setMarket(Array.isArray(m)?m:[]);setStats(s||{});setBotCfg(b||{});setKlines(Array.isArray(k)?k:[]);setFunds(f||{});
      setEmaData(ema||{ema_fast:[],ema_slow:[]});setFearGreed(Array.isArray(fg)?fg:[]);
    };
    load(); const t=setInterval(load,30000); return()=>clearInterval(t);
  },[token,mode,pair]);

  const balance=mode==="demo"?funds.demo_balance:funds.live_balance;
  const initial=mode==="demo"?funds.demo_initial:null;
  const balPct=initial&&initial>0?(((balance-initial)/initial)*100):null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-white text-2xl font-bold">Dashboard</h1>
          <p className="text-slate-500 text-sm mt-0.5">Viewing <span className={mode==="live"?"text-red-400 font-semibold":"text-amber-400 font-semibold"}>{mode==="live"?"Live Account":"Demo Account"}</span> — prices live from Binance</p>
        </div>
        <div className={`flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-medium ${botCfg.is_running?"bg-green-500/10 border-green-500/30 text-green-400":"bg-slate-800 border-slate-700 text-slate-400"}`}>
          <div className={`w-2 h-2 rounded-full ${botCfg.is_running?"bg-green-400 animate-pulse":"bg-slate-500"}`}/>{botCfg.is_running?"Bot Running":"Bot Stopped"}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {market.map(m=>(
          <button key={m.symbol} onClick={()=>setPair(m.symbol)} className={`bg-slate-900 border rounded-xl p-4 text-left transition-all ${pair===m.symbol?"border-cyan-500/50 bg-slate-800":"border-slate-800 hover:border-slate-700"}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-xs font-medium">{m.symbol.replace("USDT","")}/USDT</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${m.change_pct>=0?"bg-green-500/15 text-green-400":"bg-red-500/15 text-red-400"}`}>{m.change_pct>=0?"+":""}{m.change_pct?.toFixed(2)}%</span>
            </div>
            <div className="text-white font-bold text-lg">${m.price?.toLocaleString(undefined,{maximumFractionDigits:2})}</div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label={mode==="demo"?"Demo Balance":"Live Balance"} value={`$${(balance||0).toLocaleString(undefined,{maximumFractionDigits:0})}`} sub={balPct!=null?`${balPct>=0?"+":""}${balPct.toFixed(1)}% from initial`:undefined} icon="portfolio" color={!balPct||balPct>=0?"green":"red"}/>
        <StatCard label="Total PnL" value={`${(stats.total_pnl||0)>=0?"+":""}$${(stats.total_pnl||0).toFixed(2)}`} icon="chart" color={(stats.total_pnl||0)>=0?"cyan":"red"}/>
        <StatCard label="Win Rate" value={`${stats.win_rate||0}%`} sub={`${stats.total_trades||0} trades`} icon="trend_up" color="violet"/>
        <StatCard label="Best Trade" value={`$${stats.best_trade||0}`} icon="money" color="amber"/>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <div><h3 className="text-white font-semibold">{pair} — 1H Candlestick Chart</h3><p className="text-slate-500 text-xs mt-0.5">Live data from Binance API · auto-refresh 30s</p></div>
          <div className="flex gap-2 flex-wrap">
            {["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT"].map(p=>(
              <button key={p} onClick={()=>setPair(p)} className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${pair===p?"bg-cyan-500/20 text-cyan-400 border border-cyan-500/30":"text-slate-500 hover:text-slate-300"}`}>{p.replace("USDT","")}</button>
            ))}
          </div>
        </div>
        <div className="h-52"><CandleChart klines={klines} emaFast={emaData.ema_fast} emaSlow={emaData.ema_slow}/></div>
        <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
          <span className="flex items-center gap-1.5"><span className="w-4 h-0.5 bg-cyan-400 inline-block rounded"/>EMA {botCfg.ema_fast||21}</span>
          <span className="flex items-center gap-1.5"><span className="w-4 h-0.5 bg-violet-400 inline-block rounded"/>EMA {botCfg.ema_slow||55}</span>
        </div>
      </div>

      {fearGreed.length>0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">Fear & Greed Index</h3>
          <div className="flex items-center gap-6 flex-wrap">
            {(()=>{
              const fg=fearGreed[0]; const val=parseInt(fg.value||0);
              const col=val>=75?"text-green-400":val>=55?"text-lime-400":val>=45?"text-amber-400":val>=25?"text-orange-400":"text-red-400";
              const bgCol=val>=75?"bg-green-400":val>=55?"bg-lime-400":val>=45?"bg-amber-400":val>=25?"bg-orange-400":"bg-red-400";
              return (
                <>
                  <div className="flex items-center gap-4">
                    <div className={`w-16 h-16 rounded-full ${bgCol} flex items-center justify-center`}>
                      <span className="text-slate-900 font-bold text-xl">{val}</span>
                    </div>
                    <div>
                      <div className={`font-bold text-lg ${col}`}>{fg.value_classification}</div>
                      <div className="text-slate-500 text-xs">Today · crypto market sentiment</div>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {fearGreed.slice(1,8).map((d,i)=>{
                      const v=parseInt(d.value||0);
                      const bc=v>=75?"bg-green-400":v>=55?"bg-lime-400":v>=45?"bg-amber-400":v>=25?"bg-orange-400":"bg-red-400";
                      return <div key={i} className="text-center"><div className={`w-9 h-9 rounded-lg ${bc} flex items-center justify-center text-xs font-bold text-slate-900`}>{v}</div><div className="text-slate-600 text-xs mt-1">{i+1}d ago</div></div>;
                    })}
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      )}

      {funds.max_daily_loss_pct && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">Risk Snapshot</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[{l:"Max Daily Loss",v:`${funds.max_daily_loss_pct}%`,c:"text-red-400"},{l:"Max Trade Size",v:`${funds.max_trade_size_pct}%`,c:"text-amber-400"},{l:"Max Open Trades",v:funds.max_open_trades,c:"text-cyan-400"},{l:"Risk / Trade",v:`${funds.risk_per_trade_pct}%`,c:"text-violet-400"}].map(r=>(
              <div key={r.l} className="bg-slate-800 rounded-xl p-3 text-center"><div className={`text-xl font-bold ${r.c}`}>{r.v}</div><div className="text-slate-500 text-xs mt-1">{r.l}</div></div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ── TRADING PAGE ──────────────────────────────────────────────────────────────
const TradingPage = ({ token, mode }) => {
  const [funds,setFunds]=useState({});
  const [openTrades,setOpenTrades]=useState([]);
  const [closedTrades,setClosedTrades]=useState([]);
  const [pair,setPair]=useState("BTCUSDT");
  const [side,setSide]=useState("BUY");
  const [amount,setAmount]=useState("");
  const [orderType,setOrderType]=useState("MARKET");
  const [limitPrice,setLimitPrice]=useState("");
  const [tradeSlPct,setTradeSlPct]=useState("");
  const [tradeTpPct,setTradeTpPct]=useState("");
  const [livePrice,setLivePrice]=useState(null);
  const [liveData,setLiveData]=useState({});
  const [msg,setMsg]=useState(null);
  const [loading,setLoading]=useState(false);
  const [closingId,setClosingId]=useState(null);
  const [editTrade,setEditTrade]=useState(null);
  const [editForm,setEditForm]=useState({stop_loss_pct:"",take_profit_pct:""});
  const [editSaving,setEditSaving]=useState(false);

  const PAIRS = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT"];

  const load = async () => {
    const [f,o,c,p] = await Promise.all([
      api("/api/funds",{},token),
      api("/api/demo/open-trades",{},token),
      api(`/api/trades?mode=${mode}`,{},token),
      api(`/api/market/price/${pair}`,{},token),
    ]);
    setFunds(f||{}); setOpenTrades(Array.isArray(o)?o:[]); setClosedTrades(Array.isArray(c)?c:[]); setLivePrice(p?.price||null); setLiveData(p||{});
  };

  useEffect(()=>{ load(); const t=setInterval(load,8000); return()=>clearInterval(t); },[token,mode,pair]);

  const placeTrade = async () => {
    if (!amount||isNaN(parseFloat(amount))) return;
    if ((orderType==="LIMIT"||orderType==="STOP_MARKET")&&(!limitPrice||isNaN(parseFloat(limitPrice)))){ setMsg({ok:false,text:`${orderType} order requires a price`}); return; }
    setLoading(true); setMsg(null);
    const body={pair,side,amount_usdt:parseFloat(amount),order_type:orderType};
    if(orderType==="LIMIT"||orderType==="STOP_MARKET") body.limit_price=parseFloat(limitPrice);
    if(tradeSlPct&&parseFloat(tradeSlPct)>0) body.stop_loss_pct=parseFloat(tradeSlPct);
    if(tradeTpPct&&parseFloat(tradeTpPct)>0) body.take_profit_pct=parseFloat(tradeTpPct);
    const res = await api("/api/demo/trade",{method:"POST",body:JSON.stringify(body)},token);
    if (res.trade_id) {
      const priceStr=res.price?`@ $${res.price?.toLocaleString()}`:"(pending fill)";
      const statusStr=res.status==="pending"?"⏳ Queued":"✅";
      setMsg({ok:true,text:`${statusStr} ${side} ${pair} ${priceStr} — ${orderType} order`});
      setAmount(""); setLimitPrice(""); load();
    } else setMsg({ok:false,text:res.detail||"Trade failed"});
    setLoading(false);
  };

  const closeTrade = async id => {
    setClosingId(id);
    const res = await api(`/api/demo/trade/${id}/close`,{method:"POST"},token);
    if (res.pnl!==undefined) { setMsg({ok:res.pnl>=0,text:`${res.pnl>=0?"✅":"❌"} Closed @ $${res.exit_price?.toLocaleString(undefined,{maximumFractionDigits:2})} — PnL: ${res.pnl>=0?"+":""}$${res.pnl?.toFixed(2)} (${res.pnl_pct>=0?"+":""}${res.pnl_pct?.toFixed(2)}%)`}); load(); }
    else setMsg({ok:false,text:res.detail||"Failed"});
    setClosingId(null);
  };

  const resetDemo = async () => {
    if (!window.confirm(`Reset demo to $${(funds.demo_initial||10000).toLocaleString()}? All trades cleared.`)) return;
    const res = await api("/api/funds/reset-demo",{method:"POST"},token);
    if (res.balance) { setMsg({ok:true,text:`✅ Demo reset to $${res.balance.toLocaleString()}`}); load(); }
  };

  const openEdit = (t) => {
    setEditTrade(t);
    setEditForm({stop_loss_pct: t.stop_loss_pct||1.5, take_profit_pct: t.take_profit_pct||3.0});
  };

  const saveSlTp = async () => {
    if (!editTrade) return;
    setEditSaving(true);
    const res = await api(`/api/demo/trade/${editTrade.id}/sltp`,{method:"PUT",body:JSON.stringify({stop_loss_pct:parseFloat(editForm.stop_loss_pct)||undefined,take_profit_pct:parseFloat(editForm.take_profit_pct)||undefined})},token);
    if (res.trade_id) { setMsg({ok:true,text:`✅ ${editTrade.pair} — SL: ${res.stop_loss_pct}% ($${res.stop_price}) | TP: ${res.take_profit_pct}% ($${res.target_price})`}); setEditTrade(null); load(); }
    else setMsg({ok:false,text:res.detail||"Update failed"});
    setEditSaving(false);
  };

  const balance = mode==="demo"?funds.demo_balance:funds.live_balance;
  const maxTrade = balance?(balance*(funds.max_trade_size_pct||10)/100):0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-white text-2xl font-bold">{mode==="demo"?"Paper Trading":"Live Trading"}</h1>
            <ModeBadge mode={mode}/>
          </div>
          <p className="text-slate-500 text-sm">{mode==="demo"?"Simulate trades using real Binance prices — no real money involved":"Real orders on your Binance account — actual money at risk"}</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className={`px-4 py-2 rounded-xl border text-sm font-bold ${mode==="demo"?"bg-amber-400/10 border-amber-400/30 text-amber-400":"bg-red-500/10 border-red-500/30 text-red-400"}`}>
            Balance: ${(balance||0).toLocaleString(undefined,{maximumFractionDigits:2})}
          </div>
          {mode==="demo" && <button onClick={resetDemo} className="text-xs px-3 py-2 bg-slate-800 hover:bg-slate-700 text-amber-400 border border-amber-400/30 rounded-lg transition-colors font-medium">🔄 Reset Demo</button>}
        </div>
      </div>

      {mode==="live" && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
          <Icon name="warning" size={18} className="text-red-400 flex-shrink-0 mt-0.5"/>
          <p className="text-sm text-slate-300"><span className="text-red-400 font-bold">Live mode active.</span> All trades placed here execute real orders on Binance. Prices are live from Binance API. Make sure API keys are configured in Settings first.</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT: Trade Panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5">
          <h3 className="text-white font-semibold text-base">{mode==="demo"?"Place Paper Trade":"Place Order"}</h3>

          {/* Pair selector */}
          <div>
            <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-2 block">Select Pair</label>
            <div className="grid grid-cols-3 gap-1.5">
              {PAIRS.map(p=>(
                <button key={p} onClick={()=>setPair(p)} className={`py-2 text-xs font-bold rounded-lg transition-all ${pair===p?"bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-sm":"bg-slate-800 text-slate-400 hover:text-white border border-slate-700"}`}>{p.replace("USDT","")}</button>
              ))}
            </div>
          </div>

          {/* Live price display */}
          <div className={`rounded-xl p-4 border text-center ${mode==="live"?"bg-red-500/5 border-red-500/20":"bg-slate-800 border-slate-700"}`}>
            <div className="text-slate-400 text-xs mb-1 uppercase tracking-wider">Live Price · {pair}</div>
            <div className="text-white font-bold text-2xl">{livePrice?`$${livePrice.toLocaleString(undefined,{maximumFractionDigits:2})}`:"Loading…"}</div>
            <div className="flex items-center justify-center gap-3 mt-1">
              {liveData.change_pct!==undefined && <span className={`text-xs font-semibold ${liveData.change_pct>=0?"text-green-400":"text-red-400"}`}>{liveData.change_pct>=0?"+":""}{liveData.change_pct?.toFixed(2)}% 24h</span>}
              <span className="text-slate-600 text-xs">Binance API · live</span>
            </div>
          </div>

          {/* Order type */}
          <div>
            <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-2 block">Order Type</label>
            <div className="grid grid-cols-4 gap-1">
              {["MARKET","LIMIT","STOP_MARKET","OCO"].map(t=>(
                <button key={t} onClick={()=>setOrderType(t)}
                  className={`py-2 text-xs font-bold rounded-lg transition-all ${orderType===t?"bg-cyan-500/20 text-cyan-400 border border-cyan-500/40":"bg-slate-800 text-slate-500 border border-slate-700 hover:text-slate-300"}`}>
                  {t==="STOP_MARKET"?"STOP":t==="OCO"?"OCO":t}
                </button>
              ))}
            </div>
            <p className="text-slate-600 text-xs mt-1.5">
              {orderType==="MARKET"&&"Executes immediately at the current live price"}
              {orderType==="LIMIT"&&"Fills only when market price reaches your limit price"}
              {orderType==="STOP_MARKET"&&"Triggers a market order when price hits the stop level"}
              {orderType==="OCO"&&"Market order with automatic Stop Loss + Take Profit"}
            </p>
          </div>

          {/* Direction */}
          <div>
            <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-2 block">Direction</label>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={()=>setSide("BUY")} className={`py-3 rounded-xl font-bold text-sm transition-all ${side==="BUY"?"bg-green-500/20 text-green-400 border border-green-500/40 shadow-sm":"bg-slate-800 text-slate-500 border border-slate-700 hover:border-slate-600"}`}>▲ BUY / LONG</button>
              <button onClick={()=>setSide("SELL")} className={`py-3 rounded-xl font-bold text-sm transition-all ${side==="SELL"?"bg-red-500/20 text-red-400 border border-red-500/40 shadow-sm":"bg-slate-800 text-slate-500 border border-slate-700 hover:border-slate-600"}`}>▼ SELL / SHORT</button>
            </div>
          </div>

          {/* Amount */}
          <div>
            <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">Amount (USDT)</label>
            <input type="number" placeholder="e.g. 100" value={amount} onChange={e=>setAmount(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500 transition-colors placeholder-slate-500"/>
            {maxTrade>0 && (
              <>
                <div className="flex gap-1.5 mt-2">
                  {[25,50,75,100].map(pct=>(
                    <button key={pct} onClick={()=>setAmount(Math.floor(maxTrade*(pct/100)).toString())}
                      className="flex-1 text-xs py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg border border-slate-700 transition-colors font-medium">{pct}%</button>
                  ))}
                </div>
                <p className="text-slate-600 text-xs mt-1">Max: ${maxTrade.toFixed(0)} ({funds.max_trade_size_pct}% of balance)</p>
              </>
            )}
          </div>

          {/* Limit / Stop price (LIMIT and STOP_MARKET only) */}
          {(orderType==="LIMIT"||orderType==="STOP_MARKET") && (
            <div>
              <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">
                {orderType==="LIMIT"?"Limit Price (USDT)":"Stop Trigger Price (USDT)"}
              </label>
              <input type="number" placeholder={livePrice?`Current: $${livePrice.toLocaleString(undefined,{maximumFractionDigits:2})}`:"Enter price"} value={limitPrice} onChange={e=>setLimitPrice(e.target.value)}
                className="w-full bg-slate-800 border border-violet-500/40 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-violet-500 transition-colors placeholder-slate-600"/>
              {livePrice&&limitPrice&&parseFloat(limitPrice)>0&&(
                <p className={`text-xs mt-1 ${orderType==="LIMIT"?(side==="BUY"&&parseFloat(limitPrice)<livePrice?"text-green-400":"text-amber-400"):(side==="SELL"&&parseFloat(limitPrice)<livePrice?"text-red-400":"text-cyan-400")}`}>
                  {orderType==="LIMIT"
                    ? side==="BUY"
                      ? parseFloat(limitPrice)<livePrice?"Below market — will fill when price drops to $"+parseFloat(limitPrice).toLocaleString():"Above market — fills immediately (like market order)"
                      : parseFloat(limitPrice)>livePrice?"Above market — will fill when price rises to $"+parseFloat(limitPrice).toLocaleString():"Below market — fills immediately"
                    : `Stop trigger at $${parseFloat(limitPrice).toLocaleString(undefined,{maximumFractionDigits:2})}`
                  }
                </p>
              )}
            </div>
          )}

          {/* SL / TP inputs */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">Stop Loss %</label>
              <div className="relative">
                <input type="number" step="0.1" min="0.1" max="49" placeholder="e.g. 2" value={tradeSlPct} onChange={e=>setTradeSlPct(e.target.value)}
                  className="w-full bg-slate-800 border border-red-500/30 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-red-500 transition-colors placeholder-slate-600"/>
                {livePrice&&tradeSlPct&&parseFloat(tradeSlPct)>0&&(
                  <p className="text-red-400 text-xs mt-1">Stop: ${(livePrice*(1-parseFloat(tradeSlPct)/100)).toFixed(2)}</p>
                )}
              </div>
            </div>
            <div>
              <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">Take Profit %</label>
              <div className="relative">
                <input type="number" step="0.1" min="0.1" max="199" placeholder="e.g. 4" value={tradeTpPct} onChange={e=>setTradeTpPct(e.target.value)}
                  className="w-full bg-slate-800 border border-green-500/30 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-green-500 transition-colors placeholder-slate-600"/>
                {livePrice&&tradeTpPct&&parseFloat(tradeTpPct)>0&&(
                  <p className="text-green-400 text-xs mt-1">Target: ${(livePrice*(1+parseFloat(tradeTpPct)/100)).toFixed(2)}</p>
                )}
              </div>
            </div>
            <p className="text-slate-600 text-xs col-span-2 -mt-1">Leave blank to use bot config defaults (SL: {funds.max_daily_loss_pct||1.5}% · TP: 3%)</p>
          </div>

          {msg && <div className={`text-sm rounded-xl px-4 py-3 leading-relaxed ${msg.ok?"bg-green-500/10 border border-green-500/20 text-green-400":"bg-red-500/10 border border-red-500/20 text-red-400"}`}>{msg.text}</div>}

          <button onClick={placeTrade} disabled={loading||!amount}
            className={`w-full font-bold py-3 rounded-xl text-sm transition-all disabled:opacity-40 shadow-lg ${side==="BUY"?"bg-green-500 hover:bg-green-400 text-white shadow-green-500/20":"bg-red-500 hover:bg-red-400 text-white shadow-red-500/20"}`}>
            {loading?"Processing…":`${side==="BUY"?"▲ BUY":"▼ SELL"} ${pair} · ${orderType} ${mode==="demo"?"(Paper)":"(REAL)"}`}
          </button>

          {/* Order preview */}
          {livePrice&&amount&&parseFloat(amount)>0 && (
            <div className="bg-slate-800 rounded-xl p-3 text-xs text-slate-400 space-y-1.5">
              <div className="flex justify-between"><span>Order Type</span><span className="text-cyan-400 font-medium">{orderType}</span></div>
              {(orderType==="MARKET"||orderType==="OCO") && <>
                <div className="flex justify-between"><span>Est. entry</span><span className="text-white">${livePrice.toLocaleString(undefined,{maximumFractionDigits:2})}</span></div>
                <div className="flex justify-between"><span>Quantity</span><span className="text-white font-medium">{(parseFloat(amount)/livePrice).toFixed(6)} {pair.replace("USDT","")}</span></div>
              </>}
              {(orderType==="LIMIT"||orderType==="STOP_MARKET")&&limitPrice&&parseFloat(limitPrice)>0 && <>
                <div className="flex justify-between"><span>Trigger / Limit</span><span className="text-violet-400">${parseFloat(limitPrice).toLocaleString(undefined,{maximumFractionDigits:2})}</span></div>
                <div className="flex justify-between"><span>Quantity</span><span className="text-white font-medium">{(parseFloat(amount)/parseFloat(limitPrice)).toFixed(6)} {pair.replace("USDT","")}</span></div>
              </>}
              {tradeSlPct&&parseFloat(tradeSlPct)>0 && <div className="flex justify-between"><span>Stop Loss</span><span className="text-red-400">{tradeSlPct}% — ${(livePrice*(1-parseFloat(tradeSlPct)/100)).toFixed(2)}</span></div>}
              {tradeTpPct&&parseFloat(tradeTpPct)>0 && <div className="flex justify-between"><span>Take Profit</span><span className="text-green-400">{tradeTpPct}% — ${(livePrice*(1+parseFloat(tradeTpPct)/100)).toFixed(2)}</span></div>}
            </div>
          )}
        </div>

        {/* RIGHT: Positions */}
        <div className="lg:col-span-2 space-y-5">
          {/* Edit SL/TP Modal */}
          {editTrade && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-sm w-full shadow-2xl">
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <h3 className="text-white font-bold text-lg">Edit Position</h3>
                    <p className="text-slate-400 text-sm mt-0.5">{editTrade.pair} · Entry ${editTrade.entry_price?.toLocaleString(undefined,{maximumFractionDigits:2})}</p>
                  </div>
                  <button onClick={()=>setEditTrade(null)} className="text-slate-500 hover:text-white w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-800 transition-colors text-lg">✕</button>
                </div>

                <div className="bg-slate-800 rounded-xl p-3 mb-4 grid grid-cols-2 gap-3 text-xs text-center">
                  <div><div className="text-slate-500">Current Price</div><div className="text-white font-bold text-base">${editTrade.current_price?.toLocaleString(undefined,{maximumFractionDigits:2})}</div></div>
                  <div><div className="text-slate-500">Unrealized PnL</div><div className={`font-bold text-base ${(editTrade.unrealized_pnl||0)>=0?"text-green-400":"text-red-400"}`}>{(editTrade.unrealized_pnl||0)>=0?"+":""}${(editTrade.unrealized_pnl||0).toFixed(2)}</div></div>
                  <div><div className="text-slate-500">Margin</div><div className="text-amber-400 font-semibold">${editTrade.margin_value?.toLocaleString()}</div></div>
                  <div><div className="text-slate-500">Current Value</div><div className="text-cyan-400 font-semibold">${editTrade.current_value?.toLocaleString()}</div></div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">Stop Loss %</label>
                    <input type="number" step="0.1" min="0.1" max="49" value={editForm.stop_loss_pct} onChange={e=>setEditForm(f=>({...f,stop_loss_pct:e.target.value}))}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-red-500 transition-colors"/>
                    {editTrade.entry_price&&editForm.stop_loss_pct&&(
                      <p className="text-red-400 text-xs mt-1">Stop at <span className="font-semibold">${(editTrade.entry_price*(1-parseFloat(editForm.stop_loss_pct)/100)).toFixed(2)}</span></p>
                    )}
                  </div>
                  <div>
                    <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">Take Profit %</label>
                    <input type="number" step="0.1" min="0.1" max="199" value={editForm.take_profit_pct} onChange={e=>setEditForm(f=>({...f,take_profit_pct:e.target.value}))}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-green-500 transition-colors"/>
                    {editTrade.entry_price&&editForm.take_profit_pct&&(
                      <p className="text-green-400 text-xs mt-1">Target at <span className="font-semibold">${(editTrade.entry_price*(1+parseFloat(editForm.take_profit_pct)/100)).toFixed(2)}</span></p>
                    )}
                  </div>
                </div>

                <div className="flex gap-3 mt-5">
                  <button onClick={()=>setEditTrade(null)} className="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-xl font-medium text-sm transition-colors">Cancel</button>
                  <button onClick={saveSlTp} disabled={editSaving} className="flex-1 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white py-2.5 rounded-xl font-bold text-sm transition-all disabled:opacity-50">
                    {editSaving?"Saving…":"Update"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Open positions */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">Open Positions <span className="text-slate-500 font-normal text-sm">({openTrades.length}/{funds.max_open_trades||3})</span></h3>
              <span className="text-slate-500 text-xs">Live · refreshes every 8s</span>
            </div>
            {openTrades.length===0?(
              <div className="text-center py-8 text-slate-600">
                <div className="text-3xl mb-2">📊</div>
                <p className="text-sm">No open positions</p>
              </div>
            ):(
              <div className="space-y-3">
                {openTrades.map(t=>{
                  const isPending=t.status==="pending";
                  const pnl=t.unrealized_pnl||0; const pct=t.unrealized_pct||0;
                  const isProfit=pnl>=0;
                  return (
                    <div key={t.id} className={`rounded-xl border p-4 transition-all ${isPending?"border-violet-500/25 bg-violet-500/5":isProfit?"border-green-500/20 bg-green-500/5":"border-red-500/20 bg-red-500/5"}`}>
                      {/* Top row */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2.5 flex-wrap">
                          <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${t.side==="BUY"?"bg-green-500/20 text-green-400":"bg-red-500/20 text-red-400"}`}>{t.side}</span>
                          <span className="text-white font-bold">{t.pair}</span>
                          {isPending
                            ? <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-semibold">⏳ {t.order_type||"PENDING"}</span>
                            : <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400">{t.order_type||"MARKET"}</span>
                          }
                          <span className="text-slate-600 text-xs">#{t.id}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {!isPending && <button onClick={()=>openEdit(t)} className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-cyan-500/10 text-slate-400 hover:text-cyan-400 border border-slate-700 hover:border-cyan-500/30 rounded-lg transition-all font-medium">Edit</button>}
                          <button onClick={()=>closeTrade(t.id)} disabled={closingId===t.id}
                            className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-red-500/10 text-slate-400 hover:text-red-400 border border-slate-700 hover:border-red-500/30 rounded-lg transition-all font-medium disabled:opacity-50">
                            {closingId===t.id?"…":isPending?"Cancel":"Close"}
                          </button>
                        </div>
                      </div>

                      {/* Pending order: show trigger info */}
                      {isPending ? (
                        <div className="bg-violet-500/10 rounded-xl p-3 text-xs space-y-1.5">
                          <div className="flex justify-between"><span className="text-slate-400">Order Type</span><span className="text-violet-300 font-semibold">{t.order_type}</span></div>
                          <div className="flex justify-between"><span className="text-slate-400">Trigger Price</span><span className="text-white font-bold">${t.limit_price?.toLocaleString(undefined,{maximumFractionDigits:2})}</span></div>
                          <div className="flex justify-between"><span className="text-slate-400">Current Price</span><span className="text-cyan-300">${t.current_price?.toLocaleString(undefined,{maximumFractionDigits:2})}</span></div>
                          <div className="flex justify-between"><span className="text-slate-400">Amount</span><span className="text-white">{t.quantity?.toFixed(6)} {t.pair?.replace("USDT","")}</span></div>
                          <div className="mt-1 text-violet-300/70">Waiting for price to reach trigger — auto-fills when condition met</div>
                        </div>
                      ) : (<>
                        {/* Live PnL */}
                        <div className="flex items-end justify-between mb-3">
                          <div>
                            <div className="text-slate-500 text-xs mb-0.5">Unrealized PnL</div>
                            <div className={`text-2xl font-bold tracking-tight ${isProfit?"text-green-400":"text-red-400"}`}>{isProfit?"+":""}${pnl.toFixed(2)}</div>
                            <div className={`text-sm font-semibold ${isProfit?"text-green-500":"text-red-500"}`}>{isProfit?"+":""}{pct.toFixed(2)}%</div>
                          </div>
                          <div className="text-right">
                            <div className="text-slate-500 text-xs mb-0.5">Current Price</div>
                            <div className="text-white font-bold text-lg">${t.current_price?.toLocaleString(undefined,{maximumFractionDigits:2})}</div>
                            <div className="text-slate-500 text-xs">{t.current_value?`Value $${t.current_value?.toLocaleString(undefined,{maximumFractionDigits:2})}`:""}</div>
                          </div>
                        </div>
                        {/* Position details grid */}
                        <div className="grid grid-cols-4 gap-2 text-xs bg-slate-800/60 rounded-lg p-2.5">
                          <div className="text-center"><div className="text-slate-500 mb-0.5">Entry</div><div className="text-white font-medium">${t.entry_price?.toLocaleString(undefined,{maximumFractionDigits:2})}</div></div>
                          <div className="text-center"><div className="text-slate-500 mb-0.5">Margin</div><div className="text-amber-400 font-semibold">${t.margin_value?.toLocaleString(undefined,{maximumFractionDigits:0})}</div></div>
                          <div className="text-center"><div className="text-slate-500 mb-0.5">Stop</div><div className="text-red-400 font-semibold">${t.stop_price?.toLocaleString(undefined,{maximumFractionDigits:2})}</div><div className="text-slate-600">{t.stop_loss_pct}%</div></div>
                          <div className="text-center"><div className="text-slate-500 mb-0.5">Target</div><div className="text-green-400 font-semibold">${t.target_price?.toLocaleString(undefined,{maximumFractionDigits:2})}</div><div className="text-slate-600">{t.take_profit_pct}%</div></div>
                        </div>
                      </>)}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Closed trades */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h3 className="text-white font-semibold mb-4">Recent Closed Trades</h3>
            {closedTrades.filter(t=>t.status==="closed").length===0?(
              <p className="text-slate-600 text-sm text-center py-4">No closed trades yet</p>
            ):(
              <div>
                {closedTrades.filter(t=>t.status==="closed").slice(0,8).map(t=>(
                  <div key={t.id} className="flex items-center justify-between py-3 border-b border-slate-800 last:border-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`text-xs font-bold flex-shrink-0 ${t.side==="BUY"?"text-green-400":"text-red-400"}`}>{t.side}</span>
                      <span className="text-slate-300 text-sm font-medium">{t.pair}</span>
                      <span className="text-slate-600 text-xs truncate">@ ${t.entry_price?.toFixed(2)} → ${t.exit_price?.toFixed(2)}</span>
                    </div>
                    <div className={`font-bold text-sm flex-shrink-0 ${(t.pnl||0)>=0?"text-green-400":"text-red-400"}`}>
                      {(t.pnl||0)>=0?"+":""}${(t.pnl||0).toFixed(2)} <span className="text-xs opacity-60">({(t.pnl_pct||0)>=0?"+":""}{(t.pnl_pct||0).toFixed(1)}%)</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ── BOT PAGE ──────────────────────────────────────────────────────────────────
const BotPage = ({ token, mode }) => {
  const [config,setConfig]=useState({});
  const [saved,setSaved]=useState(false);
  const [loading,setLoading]=useState(false);
  useEffect(()=>{ api("/api/bot/config",{},token).then(c=>setConfig(c||{})); },[token]);
  const save = async()=>{ setLoading(true); await api("/api/bot/config",{method:"PUT",body:JSON.stringify(config)},token); setSaved(true); setLoading(false); setTimeout(()=>setSaved(false),2500); };
  const toggleBot = async()=>{ const res=await api(config.is_running?"/api/bot/stop":"/api/bot/start",{method:"POST"},token); if(!res.detail) setConfig(c=>({...c,is_running:!c.is_running})); else alert(res.detail); };
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div><h1 className="text-white text-2xl font-bold">Bot Control</h1><p className="text-slate-500 text-sm mt-0.5">Currently in <ModeBadge mode={mode}/> mode</p></div>
        <button onClick={toggleBot} className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all ${config.is_running?"bg-red-500/20 border border-red-500/30 text-red-400":"bg-green-500/20 border border-green-500/30 text-green-400"}`}>
          <Icon name={config.is_running?"stop":"play"} size={16}/>{config.is_running?"Stop Bot":"Start Bot"}
        </button>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-white font-semibold">Market Settings</h3>
          <Select label="Strategy" value={config.strategy} onChange={v=>setConfig(c=>({...c,strategy:v}))} options={[{value:"EMA_RSI",label:"EMA Crossover + RSI"},{value:"GRID",label:"Grid Trading"},{value:"MEAN_REVERSION",label:"Mean Reversion"}]}/>
          <Select label="Trading Pair" value={config.trading_pair} onChange={v=>setConfig(c=>({...c,trading_pair:v}))} options={["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT"].map(p=>({value:p,label:p.replace("USDT","/USDT")}))}/>
          <Select label="Market Type" value={config.market_type} onChange={v=>setConfig(c=>({...c,market_type:v}))} options={[{value:"spot",label:"Spot"},{value:"futures",label:"Futures (Leveraged)"}]}/>
          <Input label="Leverage" type="number" value={config.leverage} onChange={v=>setConfig(c=>({...c,leverage:v}))}/>
          <Input label="Trade Amount (USDT)" type="number" value={config.trade_amount} onChange={v=>setConfig(c=>({...c,trade_amount:v}))}/>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-white font-semibold">Strategy Parameters</h3>
          <Input label="EMA Fast Period" type="number" value={config.ema_fast} onChange={v=>setConfig(c=>({...c,ema_fast:v}))}/>
          <Input label="EMA Slow Period" type="number" value={config.ema_slow} onChange={v=>setConfig(c=>({...c,ema_slow:v}))}/>
          <Input label="RSI Period" type="number" value={config.rsi_period} onChange={v=>setConfig(c=>({...c,rsi_period:v}))}/>
          <Input label="RSI Buy Threshold" type="number" value={config.rsi_buy_threshold} onChange={v=>setConfig(c=>({...c,rsi_buy_threshold:v}))}/>
          <Input label="RSI Sell Threshold" type="number" value={config.rsi_sell_threshold} onChange={v=>setConfig(c=>({...c,rsi_sell_threshold:v}))}/>
          <Input label="Stop Loss %" type="number" value={config.stop_loss_pct} onChange={v=>setConfig(c=>({...c,stop_loss_pct:v}))}/>
          <Input label="Take Profit %" type="number" value={config.take_profit_pct} onChange={v=>setConfig(c=>({...c,take_profit_pct:v}))}/>
        </div>
      </div>
      <button onClick={save} disabled={loading} className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-all disabled:opacity-50">
        {saved?<><Icon name="check" size={14}/>Saved!</>:loading?"Saving…":"Save Configuration"}
      </button>
    </div>
  );
};

// ── TRADES HISTORY ────────────────────────────────────────────────────────────
const TradesPage = ({ token, mode }) => {
  const [trades,setTrades]=useState([]);
  const [stats,setStats]=useState({});
  useEffect(()=>{ Promise.all([api(`/api/trades?mode=${mode}`,{},token),api(`/api/trades/stats?mode=${mode}`,{},token)]).then(([t,s])=>{ setTrades(Array.isArray(t)?t:[]); setStats(s||{}); }); },[token,mode]);
  return (
    <div className="space-y-6">
      <div><h1 className="text-white text-2xl font-bold">Trade History</h1><p className="text-slate-500 text-sm mt-0.5">All <ModeBadge mode={mode}/> trades</p></div>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Total Trades" value={stats.total_trades||0} icon="trade" color="cyan"/>
        <StatCard label="Win Rate" value={`${stats.win_rate||0}%`} icon="trend_up" color="green"/>
        <StatCard label="Total PnL" value={`${(stats.total_pnl||0)>=0?"+":""}$${stats.total_pnl||0}`} icon="portfolio" color={(stats.total_pnl||0)>=0?"violet":"red"}/>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between"><h3 className="text-white font-semibold">All Trades</h3><ModeBadge mode={mode}/></div>
        {trades.length===0?(<div className="text-center py-16 text-slate-500 text-sm">No trades yet.</div>):(
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr className="border-b border-slate-800">{["Pair","Side","Entry","Exit","PnL","Status","Date"].map(h=><th key={h} className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">{h}</th>)}</tr></thead>
              <tbody>
                {trades.map(t=>(
                  <tr key={t.id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                    <td className="px-5 py-4 text-white text-sm font-medium">{t.pair}</td>
                    <td className="px-5 py-4"><span className={`text-xs font-semibold px-2 py-1 rounded-full ${t.side==="BUY"?"bg-green-500/15 text-green-400":"bg-red-500/15 text-red-400"}`}>{t.side}</span></td>
                    <td className="px-5 py-4 text-slate-300 text-sm">${t.entry_price?.toFixed(2)}</td>
                    <td className="px-5 py-4 text-slate-300 text-sm">{t.exit_price?`$${t.exit_price?.toFixed(2)}`:"—"}</td>
                    <td className="px-5 py-4"><span className={`text-sm font-medium ${(t.pnl||0)>=0?"text-green-400":"text-red-400"}`}>{t.pnl!=null?`${t.pnl>=0?"+":""}$${t.pnl?.toFixed(2)}`:"open"}</span></td>
                    <td className="px-5 py-4"><span className={`text-xs px-2 py-1 rounded-full ${t.status==="closed"?"bg-slate-700 text-slate-300":"bg-cyan-500/15 text-cyan-400"}`}>{t.status}</span></td>
                    <td className="px-5 py-4 text-slate-500 text-xs">{new Date(t.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

// ── ALERTS ────────────────────────────────────────────────────────────────────
const AlertsPage = ({ token }) => {
  const [alerts,setAlerts]=useState([]);
  const [filter,setFilter]=useState("all");
  useEffect(()=>{ api("/api/alerts",{},token).then(a=>setAlerts(Array.isArray(a)?a:[])); },[token]);
  const markRead = async id=>{ await api(`/api/alerts/${id}/read`,{method:"POST"},token); setAlerts(a=>a.map(x=>x.id===id?{...x,is_read:1}:x)); };
  const tc={info:"border-cyan-500/30 bg-cyan-500/5",warning:"border-amber-500/30 bg-amber-500/5",error:"border-red-500/30 bg-red-500/5",success:"border-green-500/30 bg-green-500/5"};
  const filtered=filter==="all"?alerts:alerts.filter(a=>a.mode===filter);
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div><h1 className="text-white text-2xl font-bold">Alerts</h1><p className="text-slate-500 text-sm mt-0.5">{alerts.filter(a=>!a.is_read).length} unread</p></div>
        <div className="flex gap-2">{["all","demo","live"].map(f=><button key={f} onClick={()=>setFilter(f)} className={`text-xs px-3 py-1.5 rounded-lg font-medium capitalize transition-colors ${filter===f?"bg-cyan-500/20 text-cyan-400 border border-cyan-500/30":"text-slate-500 hover:text-white border border-slate-800"}`}>{f}</button>)}</div>
      </div>
      <div className="space-y-2">
        {filtered.length===0&&<div className="text-center py-16 text-slate-500 bg-slate-900 border border-slate-800 rounded-xl text-sm">No alerts</div>}
        {filtered.map(a=>(
          <div key={a.id} className={`border rounded-xl px-4 py-3.5 flex items-start justify-between gap-4 ${tc[a.type]||tc.info} ${a.is_read?"opacity-40":""}`}>
            <div className="flex items-start gap-3 min-w-0">
              <span className={`text-xs px-2 py-0.5 rounded-full font-bold flex-shrink-0 mt-0.5 ${a.mode==="live"?"bg-red-500/20 text-red-400":"bg-amber-400/20 text-amber-400"}`}>{a.mode}</span>
              <div><p className="text-white text-sm">{a.message}</p><p className="text-slate-500 text-xs mt-0.5">{new Date(a.created_at).toLocaleString()}</p></div>
            </div>
            {!a.is_read&&<button onClick={()=>markRead(a.id)} className="text-slate-500 hover:text-slate-300 flex-shrink-0"><Icon name="check" size={16}/></button>}
          </div>
        ))}
      </div>
    </div>
  );
};

// ── SETTINGS ──────────────────────────────────────────────────────────────────
const SettingsPage = ({ token, user, onProfileUpdate }) => {
  const [settings,setSettings]=useState({});
  const [funds,setFunds]=useState({});
  const [tab,setTab]=useState("funds");
  const [saving,setSaving]=useState(false);
  const [saved,setSaved]=useState("");
  const [testStatus,setTestStatus]=useState({});
  const [profile,setProfile]=useState({});
  const [pwForm,setPwForm]=useState({current:"",new_password:"",confirm:""});
  const [profileMsg,setProfileMsg]=useState(null);
  const [profileSaving,setProfileSaving]=useState(false);
  const [apiTest,setApiTest]=useState(null);
  const [apiTesting,setApiTesting]=useState(false);
  const [showFuturesGuide,setShowFuturesGuide]=useState(false);

  useEffect(()=>{
    api("/api/settings",{},token).then(s=>setSettings(s||{}));
    api("/api/funds",{},token).then(f=>setFunds(f||{}));
    api("/api/auth/profile",{},token).then(p=>setProfile(p||{}));
  },[token]);

  const saveProfile = async()=>{
    setProfileSaving(true); setProfileMsg(null);
    const res=await api("/api/auth/profile",{method:"PUT",body:JSON.stringify({name:profile.name,username:profile.username,email:profile.email})},token);
    if(res.username){ setProfileMsg({ok:true,text:"Profile updated successfully!"}); setProfile(res); if(onProfileUpdate) onProfileUpdate(res); }
    else setProfileMsg({ok:false,text:res.detail||"Update failed"});
    setProfileSaving(false);
  };

  const changePassword = async()=>{
    if(!pwForm.current||!pwForm.new_password){ setProfileMsg({ok:false,text:"Enter current and new password"}); return; }
    if(pwForm.new_password!==pwForm.confirm){ setProfileMsg({ok:false,text:"New passwords do not match"}); return; }
    if(pwForm.new_password.length<6){ setProfileMsg({ok:false,text:"Password must be at least 6 characters"}); return; }
    setProfileSaving(true); setProfileMsg(null);
    const res=await api("/api/auth/profile",{method:"PUT",body:JSON.stringify({current_password:pwForm.current,new_password:pwForm.new_password})},token);
    if(res.username){ setProfileMsg({ok:true,text:"Password updated successfully!"}); setPwForm({current:"",new_password:"",confirm:""}); }
    else setProfileMsg({ok:false,text:res.detail||"Password update failed"});
    setProfileSaving(false);
  };

  const doSave = async(endpoint,data,key)=>{ setSaving(true); await api(endpoint,{method:"PUT",body:JSON.stringify(data)},token); setSaved(key); setSaving(false); setTimeout(()=>setSaved(""),2500); };
  const doTest = async type=>{ setTestStatus(t=>({...t,[type]:"testing"})); try{ await api(`/api/notify/test-${type}`,{method:"POST"},token); setTestStatus(t=>({...t,[type]:"ok"})); }catch{ setTestStatus(t=>({...t,[type]:"error"})); } setTimeout(()=>setTestStatus(t=>({...t,[type]:null})),3000); };
  const testBinanceApi = async()=>{
    setApiTesting(true); setApiTest(null);
    const r=await api("/api/settings/test-binance",{method:"POST"},token);
    if(!r||!r.status) setApiTest({_ok:false,_err:"Cannot reach backend — is the server running on port 8000?"});
    else if(r.detail) setApiTest({_ok:false,_err:typeof r.detail==="string"?r.detail:r.detail[0]?.msg||"Error"});
    else setApiTest({...r,_ok:true});
    setApiTesting(false);
  };
  const resetDemo = async()=>{ if(!window.confirm(`Reset demo to $${(funds.demo_initial||10000).toLocaleString()}?`)) return; const res=await api("/api/funds/reset-demo",{method:"POST"},token); if(res.balance) setFunds(f=>({...f,demo_balance:res.balance})); };

  const demoGrowth = funds.demo_initial&&funds.demo_balance?(((funds.demo_balance-funds.demo_initial)/funds.demo_initial)*100).toFixed(1):null;
  const SaveBtn = ({ dataKey }) => (
    <button onClick={()=>doSave(dataKey==="funds"?"/api/funds":"/api/settings",dataKey==="funds"?funds:settings,dataKey)} disabled={saving}
      className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-all disabled:opacity-50">
      {saved===dataKey?<><Icon name="check" size={14}/>Saved!</>:saving?"Saving…":"Save"}
    </button>
  );
  const TestBtn = ({ type }) => (
    <button onClick={()=>doTest(type)} className={`px-4 py-2.5 rounded-xl border font-medium text-sm transition-colors ${testStatus[type]==="ok"?"border-green-500/30 bg-green-500/10 text-green-400":testStatus[type]==="error"?"border-red-500/30 bg-red-500/10 text-red-400":"border-slate-700 text-slate-400 hover:text-white"}`}>
      {testStatus[type]==="testing"?"Testing…":testStatus[type]==="ok"?"✓ Sent":testStatus[type]==="error"?"✗ Failed":`Test ${type.charAt(0).toUpperCase()+type.slice(1)}`}
    </button>
  );

  const tabs=[{id:"funds",label:"Funds & Risk",icon:"shield"},{id:"api",label:"Binance API",icon:"key"},{id:"ai",label:"AI Advisor",icon:"chat"},{id:"telegram",label:"Telegram",icon:"send"},{id:"email",label:"Email",icon:"mail"},{id:"profile",label:"Profile",icon:"user"}];

  return (
    <div className="space-y-6">
      <div><h1 className="text-white text-2xl font-bold">Settings</h1><p className="text-slate-500 text-sm mt-0.5">API keys, notifications, and fund management</p></div>
      <div className="flex gap-1.5 bg-slate-900 border border-slate-800 rounded-xl p-1.5 overflow-x-auto">
        {tabs.map(t=>(
          <button key={t.id} onClick={()=>setTab(t.id)} className={`flex items-center gap-2 flex-shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-all ${tab===t.id?"bg-slate-800 text-white shadow-sm":"text-slate-500 hover:text-slate-300"}`}>
            <Icon name={t.icon} size={14}/><span className="hidden sm:inline">{t.label}</span>
          </button>
        ))}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">

        {/* ── FUNDS & RISK TAB ── */}
        {tab==="funds" && <>
          <div className="flex items-start gap-3 p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-xl">
            <Icon name="shield" size={16} className="text-cyan-400 flex-shrink-0 mt-0.5"/>
            <p className="text-slate-300 text-sm">These controls apply in both Demo and Live modes. Configure limits carefully — they protect your capital from large unexpected losses.</p>
          </div>

          {/* Demo vs Live balance cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="bg-slate-800 border border-amber-400/20 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-white font-semibold text-sm">🧪 Demo Account</h4>
                <ModeBadge mode="demo"/>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-400">Current Balance</span><span className="text-amber-400 font-bold text-base">${(funds.demo_balance||0).toLocaleString(undefined,{maximumFractionDigits:2})}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Starting Balance</span><span className="text-slate-300">${(funds.demo_initial||10000).toLocaleString()}</span></div>
                {demoGrowth && <div className="flex justify-between border-t border-slate-700 pt-2"><span className="text-slate-400">Account Growth</span><span className={`font-bold ${parseFloat(demoGrowth)>=0?"text-green-400":"text-red-400"}`}>{demoGrowth>=0?"+":""}{demoGrowth}%</span></div>}
              </div>
              <Input label="Set Starting Balance" type="number" value={funds.demo_initial} onChange={v=>setFunds(f=>({...f,demo_initial:v}))} hint="Applied when you reset the demo account"/>
              <button onClick={resetDemo} className="w-full text-sm py-2 bg-amber-400/10 hover:bg-amber-400/20 text-amber-400 border border-amber-400/30 rounded-xl font-medium transition-colors">🔄 Reset Demo Account</button>
            </div>

            <div className="bg-slate-800 border border-red-500/20 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-white font-semibold text-sm">⚡ Live Account</h4>
                <ModeBadge mode="live"/>
              </div>
              <div className="text-sm">
                <div className="flex justify-between mb-3"><span className="text-slate-400">Reference Balance</span><span className="text-red-400 font-bold text-base">${(funds.live_balance||0).toLocaleString(undefined,{maximumFractionDigits:2})}</span></div>
                <p className="text-slate-600 text-xs">Manually update this to match your actual Binance balance. This is used for position size calculations.</p>
              </div>
              <Input label="Live Balance Reference (USDT)" type="number" value={funds.live_balance} onChange={v=>setFunds(f=>({...f,live_balance:v}))} hint="Sync with your real Binance account balance"/>
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 text-xs text-red-300">
                <p className="font-semibold mb-1">⚠️ Live Mode Warning</p>
                <p>Ensure Binance API keys are configured before enabling Live mode. Enable trading permissions only, never withdrawals.</p>
              </div>
            </div>
          </div>

          {/* Risk Controls */}
          <div className="border-t border-slate-700 pt-5">
            <h4 className="text-white font-semibold mb-4">Risk Controls</h4>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Input label="Max Daily Loss % of Balance" type="number" value={funds.max_daily_loss_pct} onChange={v=>setFunds(f=>({...f,max_daily_loss_pct:v}))} hint="Bot stops automatically if daily loss hits this %"/>
              <Input label="Max Single Trade Size % of Balance" type="number" value={funds.max_trade_size_pct} onChange={v=>setFunds(f=>({...f,max_trade_size_pct:v}))} hint="Caps each individual trade as a % of total balance"/>
              <Input label="Max Open Trades at Once" type="number" value={funds.max_open_trades} onChange={v=>setFunds(f=>({...f,max_open_trades:v}))} hint="Prevents over-exposure across multiple positions"/>
              <Input label="Risk Per Trade % (for sizing)" type="number" value={funds.risk_per_trade_pct} onChange={v=>setFunds(f=>({...f,risk_per_trade_pct:v}))} hint="Used with stop loss to auto-size positions correctly"/>
              <Input label="Daily Profit Target %" type="number" value={funds.daily_profit_target} onChange={v=>setFunds(f=>({...f,daily_profit_target:v}))} hint="Optional: bot can pause after hitting daily target"/>
            </div>
          </div>

          {/* Auto-Compound */}
          <div className="border-t border-slate-700 pt-5">
            <h4 className="text-white font-semibold mb-4">Auto-Compound Profits</h4>
            <div className="flex items-center justify-between p-4 bg-slate-800 rounded-xl mb-4">
              <div>
                <div className="text-white text-sm font-medium">Enable Auto-Compounding</div>
                <div className="text-slate-400 text-xs mt-0.5">Automatically reinvest a portion of each profit into your trading balance</div>
              </div>
              <Toggle value={!!funds.auto_compound} onChange={v=>setFunds(f=>({...f,auto_compound:v}))}/>
            </div>
            {!!funds.auto_compound && <Input label="Reinvest % of each profit" type="number" value={funds.compound_pct} onChange={v=>setFunds(f=>({...f,compound_pct:v}))} hint="e.g. 50 → half of each win added back to balance automatically"/>}
          </div>

          {/* Position Calculator */}
          <div className="border-t border-slate-700 pt-5">
            <h4 className="text-white font-semibold mb-3">📐 Position Size Calculator</h4>
            <div className="bg-slate-800 rounded-xl p-4 text-sm space-y-2.5">
              {(()=>{
                const bal=funds.demo_balance||10000, rpt=funds.risk_per_trade_pct||1, sl=funds.max_daily_loss_pct||2;
                const riskAmt=bal*(rpt/100), posSize=riskAmt/(sl/100);
                return [
                  {l:"Demo balance",v:`$${bal.toLocaleString(undefined,{maximumFractionDigits:0})}`},
                  {l:`Risk per trade (${rpt}%)`,v:`$${riskAmt.toFixed(2)}`},
                  {l:`Stop loss (${sl}%)`,v:`${sl}%`},
                  {l:"→ Recommended position size",v:`$${posSize.toFixed(2)}`,hi:true},
                ].map(r=><div key={r.l} className={`flex justify-between ${r.hi?"border-t border-slate-700 pt-2.5 mt-1":""}`}><span className={r.hi?"text-cyan-400 font-semibold":"text-slate-400"}>{r.l}</span><span className={r.hi?"text-cyan-400 font-bold text-base":"text-white"}>{r.v}</span></div>);
              })()}
            </div>
          </div>

          <SaveBtn dataKey="funds"/>
        </>}

        {/* ── BINANCE API TAB ── */}
        {tab==="api" && <>
            <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
              <Icon name="warning" size={16} className="text-amber-400 flex-shrink-0 mt-0.5"/>
              <p className="text-amber-300 text-sm">Enable <strong>Spot & Margin Trading only</strong>. Never enable withdrawal permissions on bot keys. For Futures — see the guide below.</p>
            </div>
            <Input label="Binance API Key" value={settings.binance_api_key} onChange={v=>setSettings(s=>({...s,binance_api_key:v}))} placeholder="Paste your API key"/>
            <Input label="Binance Secret Key" type="password" value={settings.binance_secret_key?.startsWith("••")?"":settings.binance_secret_key||""} onChange={v=>setSettings(s=>({...s,binance_secret_key:v}))} placeholder="Paste your secret key"/>
            <SaveBtn dataKey="settings"/>

            {/* Test connection button */}
            <div className="border-t border-slate-700 pt-4">
              <button onClick={testBinanceApi} disabled={apiTesting}
                className="flex items-center gap-2 px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 rounded-xl text-sm font-semibold text-white transition-colors">
                {apiTesting ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>Testing…</> : <><Icon name="chart" size={14}/>Test API Connection</>}
              </button>
              {/* test result */}
              {apiTest && !apiTest._ok && <div className="mt-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl"><p className="text-red-300 text-sm font-medium">Test failed</p><p className="text-red-400 text-xs mt-1">{apiTest._err}</p></div>}
              {apiTest?.status==="invalid_key" && <div className="mt-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
                <p className="text-red-300 font-semibold text-sm mb-1">Invalid API Key or Signature</p>
                <ul className="text-red-300/80 text-xs space-y-1 list-disc list-inside">
                  <li>Make sure you copied the <strong>full</strong> API key (no spaces, no truncation)</li>
                  <li>Secret key can only be viewed at creation — if lost, delete the key and create a new one</li>
                  <li>Check that your <strong>system clock</strong> is accurate (Binance rejects requests ±1 second off)</li>
                </ul>
              </div>}
              {apiTest?.status==="error" && <div className="mt-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
                <p className="text-red-300 font-semibold text-sm mb-1">Binance Error {apiTest.binance_code||""}</p>
                <p className="text-red-400 text-xs">{apiTest.message}</p>
              </div>}
              {apiTest?.status==="ok" && <>
                {/* Spot success card */}
                <div className="mt-3 p-4 bg-emerald-500/10 border border-emerald-500/25 rounded-xl space-y-3">
                  <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"/><span className="text-emerald-300 font-semibold text-sm">Spot API — Connected</span></div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-800 rounded-lg p-2.5"><div className="text-slate-400 mb-1">USDT Balance</div><div className="text-white font-bold">${(apiTest.spot?.usdt_free||0).toLocaleString()}</div></div>
                    <div className="bg-slate-800 rounded-lg p-2.5"><div className="text-slate-400 mb-1">Can Trade</div><div className={apiTest.spot?.can_trade?"text-emerald-400 font-bold":"text-red-400 font-bold"}>{apiTest.spot?.can_trade?"Yes":"No"}</div></div>
                    <div className="bg-slate-800 rounded-lg p-2.5 col-span-2"><div className="text-slate-400 mb-1.5">Permissions</div><div className="flex flex-wrap gap-1.5">{(apiTest.spot?.permissions||[]).map(p=><span key={p} className="px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 text-xs">{p}</span>)}{(apiTest.spot?.permissions||[]).length===0&&<span className="text-slate-500 text-xs">None returned</span>}</div></div>
                    {(apiTest.spot?.can_withdraw) && <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2.5 col-span-2"><p className="text-red-300 text-xs font-semibold">Warning: Withdrawal is enabled on this key. Disable it on Binance for security.</p></div>}
                  </div>
                  {Object.keys(apiTest.spot?.top_balances||{}).length>0 && <div><p className="text-slate-400 text-xs mb-1.5">Non-zero Balances</p><div className="flex flex-wrap gap-1.5">{Object.entries(apiTest.spot.top_balances).map(([k,v])=><span key={k} className="px-2 py-0.5 rounded-full bg-slate-700 text-slate-200 text-xs">{k}: {v}</span>)}</div></div>}
                </div>
                {/* Futures card */}
                {apiTest.futures && <>
                  {apiTest.futures.ok
                    ? <div className="mt-3 p-4 bg-violet-500/10 border border-violet-500/25 rounded-xl">
                        <div className="flex items-center gap-2 mb-2"><div className="w-2 h-2 rounded-full bg-violet-400 animate-pulse"/><span className="text-violet-300 font-semibold text-sm">Futures API — Connected</span></div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-slate-800 rounded-lg p-2.5"><div className="text-slate-400 mb-1">Wallet Balance</div><div className="text-white font-bold">${apiTest.futures.wallet_balance?.toLocaleString()}</div></div>
                          <div className="bg-slate-800 rounded-lg p-2.5"><div className="text-slate-400 mb-1">Unrealized PnL</div><div className={apiTest.futures.unrealized_pnl>=0?"text-emerald-400 font-bold":"text-red-400 font-bold"}>${apiTest.futures.unrealized_pnl}</div></div>
                        </div>
                      </div>
                    : <div className="mt-3 p-4 bg-orange-500/10 border border-orange-500/25 rounded-xl">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-orange-400"/><span className="text-orange-300 font-semibold text-sm">Futures API — Not available</span></div>
                          <button onClick={()=>setShowFuturesGuide(v=>!v)} className="text-orange-400 text-xs underline">{showFuturesGuide?"Hide fix":"How to fix"}</button>
                        </div>
                        <p className="text-orange-300/70 text-xs mt-1.5">{apiTest.futures.message||"Futures not enabled on this key"}</p>
                        {(apiTest.futures.needs_ip_restriction||apiTest.futures.key_before_futures) && <div className="mt-2 flex flex-wrap gap-1.5">
                          {apiTest.futures.needs_ip_restriction && <span className="px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-300 text-xs">IP Restriction required</span>}
                          {apiTest.futures.key_before_futures && <span className="px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-300 text-xs">Key created before Futures opened</span>}
                        </div>}
                      </div>}
                </>}
              </>}
            </div>

            {/* Futures setup guide */}
            <div className="border-t border-slate-700 pt-4">
              <button onClick={()=>setShowFuturesGuide(v=>!v)} className="flex items-center justify-between w-full text-left">
                <div className="flex items-center gap-2"><Icon name="chart" size={14} className="text-violet-400"/><span className="text-slate-300 text-sm font-medium">Futures API Setup Guide (local PC)</span></div>
                <span className="text-slate-500 text-xs">{showFuturesGuide?"▲ Hide":"▼ Show"}</span>
              </button>
              {showFuturesGuide && <div className="mt-3 bg-slate-800 rounded-xl p-4 space-y-3 text-xs text-slate-300">
                <p className="text-orange-300 font-semibold">Why you may see: "The Futures API cannot be used if the API key was created before the Futures account was opened"</p>
                <p className="text-slate-400">Binance requires: (1) Futures account opened first, then (2) new API key created, and (3) IP Access Restriction enabled before Futures permission is allowed.</p>
                <div className="space-y-2">
                  {[
                    {step:"1",title:"Open your Futures account",desc:'Login Binance → top menu → "Derivatives" → "USD-M Futures" → click "Open Now" (one-time activation)'},
                    {step:"2",title:"Delete your old API key",desc:'Account → API Management → find your current bot key → Delete it. Old keys never gain Futures permission retroactively.'},
                    {step:"3",title:"Create a new API key",desc:'Still in API Management → "Create API" → give it a name like "CryptoBotPro" → copy the KEY and SECRET (secret shown only once!)'},
                    {step:"4",title:"Find your public IP",desc:'Open a browser and go to whatismyip.com — copy the IP shown (e.g. 203.0.113.45). Your local PC\'s public IP changes sometimes (if you restart your router).'},
                    {step:"5",title:"Enable IP restriction + Futures permission",desc:'On the new key: Edit → IP Access Restriction → select "Restrict access to trusted IPs only" → add your IP. Then tick "Enable Futures". Save.'},
                    {step:"6",title:"Paste new keys here and save",desc:'Enter the new API key and secret in the fields above → click Save → then click Test API Connection.'},
                  ].map(s=><div key={s.step} className="flex gap-3">
                    <div className="w-5 h-5 rounded-full bg-violet-500/20 text-violet-300 flex items-center justify-center flex-shrink-0 font-bold text-xs mt-0.5">{s.step}</div>
                    <div><p className="text-white font-medium">{s.title}</p><p className="text-slate-400 mt-0.5">{s.desc}</p></div>
                  </div>)}
                </div>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                  <p className="text-amber-300 font-medium mb-1">Dynamic IP on home internet?</p>
                  <p className="text-amber-300/70">Your home IP may change when your router restarts. Options: (a) Use <strong>Unrestricted</strong> access on the API key (less secure), or (b) set up a static IP via a cheap VPS or VPN, or (c) update the IP whitelist on Binance whenever it changes.</p>
                </div>
                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                  <p className="text-blue-300 font-medium mb-1">Portfolio Margin error?</p>
                  <p className="text-blue-300/70">If you have Portfolio Margin enabled on Binance, Futures API requires an additional step: go to Futures → Portfolio Margin → Settings → enable API access separately.</p>
                </div>
              </div>}
            </div>
        </>}

        {/* ── AI ADVISOR TAB ── */}
        {tab==="ai" && <>
          <div className="flex items-start gap-3 p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-xl">
            <Icon name="chat" size={16} className="text-cyan-400 flex-shrink-0 mt-0.5"/>
            <p className="text-slate-300 text-sm">The AI Advisor uses Claude (Anthropic). Get an API key at <span className="text-cyan-400 font-medium">console.anthropic.com</span>. Your key is stored securely on the backend and never exposed in the browser.</p>
          </div>
          <Input label="Anthropic API Key" type="password" value={settings.anthropic_api_key?.startsWith("sk-ant")?"":settings.anthropic_api_key||""} onChange={v=>setSettings(s=>({...s,anthropic_api_key:v}))} placeholder="sk-ant-api03-…"/>
          <SaveBtn dataKey="settings"/>
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 text-xs space-y-2">
            <p className="text-amber-300 font-semibold">Getting "credit balance too low" in AI chat?</p>
            <p className="text-amber-300/80">The free tier has no ongoing credits. You need to purchase API credits to use Claude:</p>
            <div className="space-y-1 text-amber-300/70">
              <p>1. Go to <strong className="text-amber-300">console.anthropic.com → Settings → Billing</strong></p>
              <p>2. Click <strong className="text-amber-300">Add Credits</strong> — minimum $5</p>
              <p>3. Your existing API key will start working immediately after purchase</p>
              <p>4. The AI Advisor uses <strong>claude-haiku</strong> — very cost-efficient (~$0.001 per message)</p>
            </div>
          </div>
        </>}

        {/* ── TELEGRAM TAB ── */}
        {tab==="telegram" && <>
          <p className="text-slate-400 text-sm">1. Create a bot via <span className="text-cyan-400 font-medium">@BotFather</span> on Telegram → copy the token.<br/>2. Get your Chat ID from <span className="text-cyan-400 font-medium">@userinfobot</span>.</p>
          <Input label="Bot Token" value={settings.telegram_bot_token} onChange={v=>setSettings(s=>({...s,telegram_bot_token:v}))} placeholder="123456:ABC-DEF..."/>
          <Input label="Chat ID" value={settings.telegram_chat_id} onChange={v=>setSettings(s=>({...s,telegram_chat_id:v}))} placeholder="Your Telegram Chat ID"/>
          <div className="flex items-center justify-between py-1"><label className="text-slate-300 text-sm font-medium">Enable Telegram Alerts</label><Toggle value={!!settings.telegram_alerts_enabled} onChange={v=>setSettings(s=>({...s,telegram_alerts_enabled:v}))}/></div>
          <div className="flex gap-3"><SaveBtn dataKey="settings"/><TestBtn type="telegram"/></div>
        </>}

        {/* ── EMAIL TAB ── */}
        {tab==="email" && <>
          <Input label="SMTP Host" value={settings.email_smtp_host} onChange={v=>setSettings(s=>({...s,email_smtp_host:v}))} placeholder="smtp.gmail.com"/>
          <Input label="SMTP Port" type="number" value={settings.email_smtp_port} onChange={v=>setSettings(s=>({...s,email_smtp_port:v}))} placeholder="587"/>
          <Input label="Email Username" value={settings.email_username} onChange={v=>setSettings(s=>({...s,email_username:v}))} placeholder="your@gmail.com"/>
          <Input label="App Password" type="password" value={settings.email_password?.startsWith("••")?"":settings.email_password||""} onChange={v=>setSettings(s=>({...s,email_password:v}))} placeholder="Gmail app password"/>
          <div className="flex items-center justify-between py-1"><label className="text-slate-300 text-sm font-medium">Enable Email Alerts</label><Toggle value={!!settings.email_alerts_enabled} onChange={v=>setSettings(s=>({...s,email_alerts_enabled:v}))}/></div>
          <div className="flex gap-3"><SaveBtn dataKey="settings"/><TestBtn type="email"/></div>
        </>}

        {/* ── PROFILE TAB ── */}
        {tab==="profile" && <>
          {/* Avatar card */}
          <div className="flex items-center gap-5 p-5 bg-gradient-to-r from-slate-800 to-slate-800/60 border border-slate-700 rounded-xl">
            <div className="relative flex-shrink-0">
              <div className="w-20 h-20 bg-gradient-to-br from-cyan-400 to-violet-500 rounded-full flex items-center justify-center text-white font-bold text-3xl shadow-lg shadow-cyan-500/20 select-none">
                {(profile.name||profile.username||"?").charAt(0).toUpperCase()}
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-5 h-5 bg-green-400 rounded-full border-2 border-slate-800"/>
            </div>
            <div className="min-w-0">
              <div className="text-white font-bold text-xl truncate">{profile.name||profile.username||"—"}</div>
              <div className="text-slate-400 text-sm mt-0.5 truncate">{profile.email||"—"}</div>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-cyan-500/15 border border-cyan-500/30 text-cyan-400 text-xs font-semibold rounded-full capitalize">
                  {profile.role||"trader"}
                </span>
                <span className="text-slate-600 text-xs">ID #{profile.id||"—"}</span>
              </div>
            </div>
          </div>

          {profileMsg && (
            <div className={`text-sm rounded-xl px-4 py-3 flex items-center gap-2 ${profileMsg.ok?"bg-green-500/10 border border-green-500/20 text-green-400":"bg-red-500/10 border border-red-500/20 text-red-400"}`}>
              <Icon name={profileMsg.ok?"check":"warning"} size={15} className="flex-shrink-0"/>
              {profileMsg.text}
            </div>
          )}

          {/* Personal Info */}
          <div>
            <h4 className="text-white font-semibold mb-3">Personal Info</h4>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Input label="Full Name" value={profile.name||""} onChange={v=>setProfile(p=>({...p,name:v}))} placeholder="Your full name"/>
              <Input label="Username" value={profile.username||""} onChange={v=>setProfile(p=>({...p,username:v}))} placeholder="username" hint="Changing username requires re-login"/>
              <Input label="Email Address" value={profile.email||""} onChange={v=>setProfile(p=>({...p,email:v}))} placeholder="your@email.com"/>
              <Input label="Role" value={profile.role||"trader"} onChange={()=>{}} readOnly hint="Role is assigned by admin"/>
            </div>
            <button onClick={saveProfile} disabled={profileSaving}
              className="mt-4 flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-all disabled:opacity-50 shadow-lg shadow-cyan-500/10">
              {profileSaving?"Saving…":<><Icon name="check" size={14}/>Save Profile</>}
            </button>
          </div>

          {/* Change Password */}
          <div className="border-t border-slate-700 pt-5">
            <h4 className="text-white font-semibold mb-1">Change Password</h4>
            <p className="text-slate-500 text-xs mb-4">Leave blank if you don't want to change your password.</p>
            <div className="space-y-3">
              <Input label="Current Password" type="password" value={pwForm.current} onChange={v=>setPwForm(p=>({...p,current:v}))} placeholder="Enter your current password"/>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <Input label="New Password" type="password" value={pwForm.new_password} onChange={v=>setPwForm(p=>({...p,new_password:v}))} placeholder="New password" hint="Minimum 6 characters"/>
                <Input label="Confirm New Password" type="password" value={pwForm.confirm} onChange={v=>setPwForm(p=>({...p,confirm:v}))} placeholder="Repeat new password"/>
              </div>
            </div>
            {pwForm.new_password && pwForm.confirm && pwForm.new_password!==pwForm.confirm && (
              <p className="text-red-400 text-xs mt-1.5 flex items-center gap-1"><Icon name="warning" size={12}/>Passwords do not match</p>
            )}
            {pwForm.new_password && pwForm.confirm && pwForm.new_password===pwForm.confirm && (
              <p className="text-green-400 text-xs mt-1.5 flex items-center gap-1"><Icon name="check" size={12}/>Passwords match</p>
            )}
            <button onClick={changePassword} disabled={profileSaving}
              className="mt-4 flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 hover:border-slate-500 text-white font-medium px-5 py-2.5 rounded-xl text-sm transition-all disabled:opacity-50">
              {profileSaving?"Updating…":<><Icon name="shield" size={14}/>Update Password</>}
            </button>
          </div>

          {/* Account Info */}
          <div className="border-t border-slate-700 pt-5">
            <h4 className="text-white font-semibold mb-3">Account Info</h4>
            <div className="bg-slate-800 rounded-xl p-4 space-y-2.5 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Member since</span>
                <span className="text-white">{profile.created_at?new Date(profile.created_at).toLocaleDateString(undefined,{year:"numeric",month:"long",day:"numeric"}):"—"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">User ID</span>
                <span className="text-slate-500 font-mono text-xs">#{profile.id||"—"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Account role</span>
                <span className="text-cyan-400 capitalize font-medium">{profile.role||"trader"}</span>
              </div>
            </div>
          </div>
        </>}
      </div>
    </div>
  );
};

// ── AI CHAT ───────────────────────────────────────────────────────────────────
const ChatPage = ({ token, user, mode }) => {
  const [messages,setMessages]=useState([{role:"assistant",content:`👋 Hi! I'm your CryptoBot AI advisor.\nYou're in **${mode.toUpperCase()} mode**.\n\nAsk me about strategies, risk management, or how to configure your bot.`}]);
  const [input,setInput]=useState("");
  const [loading,setLoading]=useState(false);
  const bottomRef=useRef(null);
  useEffect(()=>{ bottomRef.current?.scrollIntoView({behavior:"smooth"}); },[messages]);
  const send = async()=>{
    if(!input.trim()||loading) return;
    const userMsg=input.trim(); setInput("");
    setMessages(m=>[...m,{role:"user",content:userMsg}]); setLoading(true);
    try {
      const apiMsgs=messages.concat([{role:"user",content:userMsg}]).filter((m,i)=>m.role!=="assistant"||i>0).map(m=>({role:m.role,content:m.content}));
      const data=await api("/api/chat",{method:"POST",body:JSON.stringify({messages:apiMsgs,mode})},token);
      const errMsg=data.detail||"";
      if(errMsg.includes("credit balance")||errMsg.includes("Plans & Billing")){
        setMessages(m=>[...m,{role:"assistant",content:"__CREDIT_ERROR__"}]);
      } else {
        setMessages(m=>[...m,{role:"assistant",content:data.content||errMsg||"Sorry, couldn't process that."}]);
      }
    } catch { setMessages(m=>[...m,{role:"assistant",content:"Connection error. Check your Anthropic API key in Settings → AI Advisor."}]); }
    setLoading(false);
  };
  const suggestions=["Best risk rules for demo mode?","When should I switch to live?","How to size positions properly?","Explain EMA crossover signals"];
  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-4"><h1 className="text-white text-2xl font-bold">AI Advisor</h1><p className="text-slate-500 text-sm mt-0.5">Powered by Claude · context-aware for <ModeBadge mode={mode}/> mode</p></div>
      <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m,i)=>(
            <div key={i} className={`flex gap-3 ${m.role==="user"?"justify-end":"justify-start"}`}>
              {m.role==="assistant"&&<div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-violet-500 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-1">₿</div>}
              {m.content==="__CREDIT_ERROR__"
                ? <div className="max-w-[80%] bg-orange-500/10 border border-orange-500/25 rounded-2xl rounded-tl-sm px-4 py-3 text-sm space-y-2">
                    <p className="text-orange-300 font-semibold">Anthropic API — Insufficient Credits</p>
                    <p className="text-orange-300/80 text-xs">Your API key has no credits remaining. The AI Advisor needs a paid Anthropic account to work.</p>
                    <div className="space-y-1 text-xs text-orange-300/70">
                      <p>1. Go to <strong className="text-orange-300">console.anthropic.com</strong></p>
                      <p>2. Click <strong className="text-orange-300">Plans & Billing → Add Credits</strong></p>
                      <p>3. Purchase credits (starts at $5), then retry here</p>
                    </div>
                    <a href="https://console.anthropic.com/settings/billing" target="_blank" rel="noopener noreferrer"
                      className="inline-block mt-1 px-3 py-1.5 bg-orange-500/20 hover:bg-orange-500/30 text-orange-300 rounded-lg text-xs font-medium transition-colors">
                      Open Anthropic Billing →
                    </a>
                  </div>
                : <div className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${m.role==="user"?"bg-gradient-to-r from-cyan-500 to-violet-500 text-white rounded-tr-sm":"bg-slate-800 text-slate-200 rounded-tl-sm"}`}>{m.content}</div>
              }
              {m.role==="user"&&<div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center text-xs font-bold text-slate-300 flex-shrink-0 mt-1">{user?.username?.charAt(0)?.toUpperCase()}</div>}
            </div>
          ))}
          {loading&&<div className="flex gap-3"><div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-violet-500 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">₿</div><div className="bg-slate-800 px-4 py-3 rounded-2xl rounded-tl-sm"><div className="flex gap-1">{[0,1,2].map(i=><div key={i} className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{animationDelay:`${i*0.15}s`}}/>)}</div></div></div>}
          <div ref={bottomRef}/>
        </div>
        {messages.length<=1&&<div className="px-5 pb-4 grid grid-cols-2 gap-2">{suggestions.map(s=><button key={s} onClick={()=>setInput(s)} className="text-xs text-left px-3 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-slate-400 hover:text-white transition-colors">{s}</button>)}</div>}
        <div className="p-4 border-t border-slate-800">
          <div className="flex gap-3">
            <input className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors" placeholder="Ask about strategy, risk, demo vs live…" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&!e.shiftKey&&send()}/>
            <button onClick={send} disabled={!input.trim()||loading} className="bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white p-3 rounded-xl transition-all disabled:opacity-40"><Icon name="send" size={18}/></button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── EQUITY CHART ──────────────────────────────────────────────────────────────
const EquityChart = ({ data, initial }) => {
  if (!data?.length) return <div className="flex items-center justify-center h-full text-slate-500 text-sm">No data</div>;
  const vals=data.map(d=>d.balance);
  const minV=Math.min(...vals)*0.998, maxV=Math.max(...vals)*1.002, range=maxV-minV||1;
  const w=700,h=180,toY=v=>h-((v-minV)/range)*(h-20)-10,toX=i=>(i/(data.length-1||1))*w;
  const pts=data.map((d,i)=>`${toX(i)},${toY(d.balance)}`).join(" ");
  const initY=toY(initial||vals[0]);
  const isProfit=vals[vals.length-1]>=(initial||vals[0]);
  const col=isProfit?"#22c55e":"#ef4444";
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full">
      <defs><linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={col} stopOpacity="0.2"/><stop offset="100%" stopColor={col} stopOpacity="0"/></linearGradient></defs>
      <line x1="0" y1={initY} x2={w} y2={initY} stroke="#475569" strokeWidth="1" strokeDasharray="4"/>
      <polygon points={`0,${h} ${pts} ${w},${h}`} fill="url(#eqGrad)"/>
      <polyline points={pts} fill="none" stroke={col} strokeWidth="2"/>
    </svg>
  );
};

// ── BACKTEST ──────────────────────────────────────────────────────────────────
const BacktestPage = ({ token }) => {
  const today=new Date().toISOString().split("T")[0];
  const sixMonthsAgo=new Date(Date.now()-180*86400*1000).toISOString().split("T")[0];
  const [cfg,setCfg]=useState({symbol:"BTCUSDT",interval:"1h",start_date:sixMonthsAgo,end_date:today,
    initial_balance:10000,trade_amount:500,ema_fast:21,ema_slow:55,rsi_period:14,
    rsi_buy_min:45,rsi_buy_max:65,stop_loss_pct:1.5,take_profit_pct:3.0});
  const [results,setResults]=useState(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState(null);

  const runBacktest=async()=>{
    setLoading(true); setError(null); setResults(null);
    const res=await api("/api/backtest",{method:"POST",body:JSON.stringify(cfg)},token);
    if(res.total_trades!==undefined) setResults(res);
    else setError(res.detail||"Backtest failed");
    setLoading(false);
  };

  const S=({label,value,color="text-white",sub})=>(
    <div className="bg-slate-800 rounded-xl p-4 text-center">
      <div className={`font-bold text-xl ${color}`}>{value}</div>
      <div className="text-slate-500 text-xs mt-1">{label}</div>
      {sub&&<div className="text-slate-600 text-xs mt-0.5">{sub}</div>}
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-white text-2xl font-bold">Backtesting</h1>
        <p className="text-slate-500 text-sm mt-0.5">Replay your strategy on real Binance historical data</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Config panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-white font-semibold">Configuration</h3>
          <Select label="Symbol" value={cfg.symbol} onChange={v=>setCfg(c=>({...c,symbol:v}))} options={["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT"].map(s=>({value:s,label:s.replace("USDT","/USDT")}))}/>
          <Select label="Candle Interval" value={cfg.interval} onChange={v=>setCfg(c=>({...c,interval:v}))} options={[{value:"15m",label:"15 Minutes"},{value:"1h",label:"1 Hour (recommended)"},{value:"4h",label:"4 Hours"},{value:"1d",label:"1 Day"}]}/>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">Start Date</label>
              <input type="date" style={{colorScheme:"dark"}} value={cfg.start_date} onChange={e=>setCfg(c=>({...c,start_date:e.target.value}))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500 transition-colors"/>
            </div>
            <div>
              <label className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1.5 block">End Date</label>
              <input type="date" style={{colorScheme:"dark"}} value={cfg.end_date} onChange={e=>setCfg(c=>({...c,end_date:e.target.value}))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500 transition-colors"/>
            </div>
          </div>
          <Input label="Starting Balance (USDT)" type="number" value={cfg.initial_balance} onChange={v=>setCfg(c=>({...c,initial_balance:v}))}/>
          <Input label="Trade Size per Signal (USDT)" type="number" value={cfg.trade_amount} onChange={v=>setCfg(c=>({...c,trade_amount:v}))}/>
          <div className="border-t border-slate-700 pt-4">
            <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-3">Strategy Parameters</p>
            <div className="grid grid-cols-2 gap-2">
              <Input label="EMA Fast" type="number" value={cfg.ema_fast} onChange={v=>setCfg(c=>({...c,ema_fast:v}))}/>
              <Input label="EMA Slow" type="number" value={cfg.ema_slow} onChange={v=>setCfg(c=>({...c,ema_slow:v}))}/>
              <Input label="RSI Period" type="number" value={cfg.rsi_period} onChange={v=>setCfg(c=>({...c,rsi_period:v}))}/>
              <Input label="RSI Buy Min" type="number" value={cfg.rsi_buy_min} onChange={v=>setCfg(c=>({...c,rsi_buy_min:v}))}/>
              <Input label="RSI Buy Max" type="number" value={cfg.rsi_buy_max} onChange={v=>setCfg(c=>({...c,rsi_buy_max:v}))}/>
              <div/>
              <Input label="Stop Loss %" type="number" value={cfg.stop_loss_pct} onChange={v=>setCfg(c=>({...c,stop_loss_pct:v}))}/>
              <Input label="Take Profit %" type="number" value={cfg.take_profit_pct} onChange={v=>setCfg(c=>({...c,take_profit_pct:v}))}/>
            </div>
          </div>
          {error&&<div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-red-400 text-sm flex items-start gap-2"><Icon name="warning" size={14} className="flex-shrink-0 mt-0.5"/>{error}</div>}
          <button onClick={runBacktest} disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white font-semibold py-3 rounded-xl text-sm transition-all disabled:opacity-50 shadow-lg shadow-cyan-500/10">
            {loading?<><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>Fetching from Binance…</>:<><Icon name="play" size={16}/>Run Backtest</>}
          </button>
          <p className="text-slate-600 text-xs text-center">Live OHLCV data via Binance API · max 2 years</p>
        </div>

        {/* Results panel */}
        <div className="lg:col-span-2 space-y-4">
          {!results&&!loading&&(
            <div className="bg-slate-900 border border-slate-800 rounded-xl flex flex-col items-center justify-center text-center p-12 min-h-64">
              <div className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mb-4"><Icon name="analytics" size={30} className="text-slate-600"/></div>
              <div className="text-slate-400 font-semibold text-lg">Ready to Backtest</div>
              <p className="text-slate-600 text-sm mt-2 max-w-xs">Configure strategy parameters and click Run Backtest to simulate against real Binance historical data.</p>
            </div>
          )}
          {loading&&(
            <div className="bg-slate-900 border border-slate-800 rounded-xl flex flex-col items-center justify-center text-center p-12 min-h-64 gap-5">
              <div className="w-14 h-14 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin"/>
              <div><div className="text-white font-semibold text-lg">Running Backtest</div><p className="text-slate-500 text-sm mt-1">Fetching historical candles from Binance…</p></div>
            </div>
          )}
          {results&&(<>
            {/* Summary metrics */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <StatCard label="Total Return" value={`${results.total_return_pct>=0?"+":""}${results.total_return_pct}%`} sub={`$${results.initial_balance.toLocaleString()} → $${results.final_balance.toLocaleString()}`} icon="trend_up" color={results.total_return_pct>=0?"green":"red"}/>
              <StatCard label="Win Rate" value={`${results.win_rate}%`} sub={`${results.winning_trades}W / ${results.losing_trades}L`} icon="chart" color={results.win_rate>=50?"violet":"amber"}/>
              <StatCard label="Total Trades" value={results.total_trades} sub={`${results.candles_used.toLocaleString()} candles`} icon="trade" color="cyan"/>
              <StatCard label="Max Drawdown" value={`-${results.max_drawdown_pct}%`} sub={`PF: ${results.profit_factor}x`} icon="warning" color={results.max_drawdown_pct>15?"red":"amber"}/>
            </div>
            <div className="grid grid-cols-4 gap-3">
              {[{l:"Total PnL",v:`${results.total_pnl>=0?"+":""}$${results.total_pnl}`,c:results.total_pnl>=0?"text-green-400":"text-red-400"},
                {l:"Avg Trade",v:`${results.avg_pnl>=0?"+":""}$${results.avg_pnl}`,c:results.avg_pnl>=0?"text-cyan-400":"text-red-400"},
                {l:"Best Trade",v:`+$${results.best_trade}`,c:"text-green-400"},
                {l:"Worst Trade",v:`$${results.worst_trade}`,c:"text-red-400"},
              ].map(r=><S key={r.l} label={r.l} value={r.v} color={r.c}/>)}
            </div>

            {/* Equity curve */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <div>
                  <h3 className="text-white font-semibold">Equity Curve</h3>
                  <p className="text-slate-500 text-xs mt-0.5">{results.symbol} · {results.interval} · {results.start_date} → {results.end_date}</p>
                </div>
                <div className={`text-xl font-bold ${results.total_return_pct>=0?"text-green-400":"text-red-400"}`}>{results.total_return_pct>=0?"+":""}{results.total_return_pct}%</div>
              </div>
              <div className="h-52"><EquityChart data={results.equity_curve} initial={results.initial_balance}/></div>
            </div>

            {/* Trade log */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between flex-wrap gap-2">
                <h3 className="text-white font-semibold">Trade Log <span className="text-slate-500 font-normal text-sm">({results.trades.length})</span></h3>
                <div className="flex gap-3 text-xs font-medium">
                  <span className="text-green-400">✅ {results.winning_trades} wins</span>
                  <span className="text-red-400">❌ {results.losing_trades} losses</span>
                </div>
              </div>
              <div className="overflow-x-auto max-h-72 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-slate-900 z-10"><tr className="border-b border-slate-800">
                    {["Entry","Exit","Entry $","Exit $","Qty","PnL","PnL %","Reason"].map(h=><th key={h} className="px-3 py-2.5 text-left text-slate-500 font-medium uppercase tracking-wider whitespace-nowrap">{h}</th>)}
                  </tr></thead>
                  <tbody>
                    {results.trades.map((t,i)=>(
                      <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                        <td className="px-3 py-2 text-slate-400 whitespace-nowrap">{t.entry_date}</td>
                        <td className="px-3 py-2 text-slate-400 whitespace-nowrap">{t.exit_date}</td>
                        <td className="px-3 py-2 text-white font-medium">${t.entry_price.toLocaleString()}</td>
                        <td className="px-3 py-2 text-white font-medium">${t.exit_price.toLocaleString()}</td>
                        <td className="px-3 py-2 text-slate-400">{t.quantity}</td>
                        <td className="px-3 py-2 font-semibold"><span className={t.pnl>=0?"text-green-400":"text-red-400"}>{t.pnl>=0?"+":""}${t.pnl.toFixed(2)}</span></td>
                        <td className="px-3 py-2"><span className={t.pnl_pct>=0?"text-green-400":"text-red-400"}>{t.pnl_pct>=0?"+":""}{t.pnl_pct.toFixed(2)}%</span></td>
                        <td className="px-3 py-2">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${t.exit_reason==="take_profit"?"bg-green-500/15 text-green-400":t.exit_reason==="stop_loss"?"bg-red-500/15 text-red-400":"bg-slate-700 text-slate-400"}`}>
                            {t.exit_reason.replace(/_/g," ")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>)}
        </div>
      </div>
    </div>
  );
};

// ── ANALYTICS ─────────────────────────────────────────────────────────────────
const PnLChart = ({ data }) => {
  if (!data?.length) return <div className="flex items-center justify-center h-full text-slate-500 text-sm">No closed trades yet</div>;
  const vals=data.map(d=>d.cumulative_pnl),minV=Math.min(0,...vals),maxV=Math.max(0,...vals),range=maxV-minV||1;
  const w=700,h=160,toY=v=>h-((v-minV)/range)*(h-20)-10,toX=i=>(i/(data.length-1||1))*w;
  const pts=data.map((d,i)=>`${toX(i)},${toY(d.cumulative_pnl)}`).join(" ");
  const zeroY=toY(0);
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full">
      <defs><linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#22d3ee" stopOpacity="0.25"/><stop offset="100%" stopColor="#22d3ee" stopOpacity="0"/></linearGradient></defs>
      <line x1="0" y1={zeroY} x2={w} y2={zeroY} stroke="#334155" strokeWidth="1" strokeDasharray="4"/>
      <polygon points={`0,${h} ${pts} ${w},${h}`} fill="url(#pnlGrad)"/>
      <polyline points={pts} fill="none" stroke="#22d3ee" strokeWidth="2"/>
      {data.map((d,i)=><circle key={i} cx={toX(i)} cy={toY(d.cumulative_pnl)} r="3" fill={d.daily_pnl>=0?"#22c55e":"#ef4444"}/>)}
    </svg>
  );
};

const AnalyticsPage = ({ token, mode }) => {
  const [pnlHistory,setPnlHistory]=useState([]);
  const [summary,setSummary]=useState({});
  const [streak,setStreak]=useState({});

  useEffect(()=>{
    Promise.all([
      api(`/api/analytics/pnl-history?mode=${mode}`,{},token),
      api(`/api/analytics/summary?mode=${mode}`,{},token),
      api(`/api/analytics/streak?mode=${mode}`,{},token),
    ]).then(([h,s,st])=>{ setPnlHistory(Array.isArray(h)?h:[]); setSummary(s||{}); setStreak(st||{}); });
  },[token,mode]);

  const SummaryBlock = ({ label, data }) => (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-3">{label}</div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        {[
          {l:"Trades",v:data?.total||0},
          {l:"Win Rate",v:`${data?.win_rate||0}%`,c:(data?.win_rate||0)>=50?"text-green-400":"text-red-400"},
          {l:"Total PnL",v:`${(data?.pnl||0)>=0?"+":""}$${(data?.pnl||0).toFixed(2)}`,c:(data?.pnl||0)>=0?"text-green-400":"text-red-400"},
          {l:"Avg Trade",v:`${(data?.avg||0)>=0?"+":""}$${(data?.avg||0).toFixed(2)}`,c:(data?.avg||0)>=0?"text-cyan-400":"text-red-400"},
        ].map(r=><div key={r.l}><div className="text-slate-500 text-xs">{r.l}</div><div className={`font-semibold ${r.c||"text-white"}`}>{r.v}</div></div>)}
      </div>
    </div>
  );

  const latestPnl=pnlHistory[pnlHistory.length-1]?.cumulative_pnl||0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-white text-2xl font-bold">Analytics</h1>
        <p className="text-slate-500 text-sm mt-0.5">Performance breakdown · <ModeBadge mode={mode}/></p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div><h3 className="text-white font-semibold">Cumulative PnL</h3><p className="text-slate-500 text-xs mt-0.5">{pnlHistory.length} trading days</p></div>
          <div className={`text-2xl font-bold ${latestPnl>=0?"text-green-400":"text-red-400"}`}>{latestPnl>=0?"+":""}${latestPnl.toFixed(2)}</div>
        </div>
        <div className="h-44"><PnLChart data={pnlHistory}/></div>
        {pnlHistory.length>0 && (
          <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
            {pnlHistory.slice(-3).map(d=>(
              <div key={d.date} className="bg-slate-800 rounded-lg p-2">
                <div className="text-slate-500">{new Date(d.date).toLocaleDateString(undefined,{month:"short",day:"numeric"})}</div>
                <div className={`font-semibold ${d.daily_pnl>=0?"text-green-400":"text-red-400"}`}>{d.daily_pnl>=0?"+":""}${d.daily_pnl.toFixed(2)}</div>
                <div className="text-slate-600">{d.trades} trade{d.trades!==1?"s":""}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <SummaryBlock label="This Week" data={summary.week}/>
        <SummaryBlock label="This Month" data={summary.month}/>
        <SummaryBlock label="All Time" data={summary.all_time}/>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-4">Win / Loss Streak</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            {l:"Current",v:`${streak.current_streak||0} ${streak.streak_type==="win"?"W":streak.streak_type==="loss"?"L":"—"}`,c:streak.streak_type==="win"?"text-green-400":streak.streak_type==="loss"?"text-red-400":"text-slate-400"},
            {l:"Status",v:streak.streak_type==="win"?"🔥 Winning":streak.streak_type==="loss"?"❄️ Losing":"—",c:streak.streak_type==="win"?"text-green-400":streak.streak_type==="loss"?"text-red-400":"text-slate-400"},
            {l:"Best Win Streak",v:streak.max_win_streak||0,c:"text-green-400"},
            {l:"Worst Loss Streak",v:streak.max_loss_streak||0,c:"text-red-400"},
          ].map(r=><div key={r.l} className="bg-slate-800 rounded-xl p-3 text-center"><div className={`text-xl font-bold ${r.c}`}>{r.v}</div><div className="text-slate-500 text-xs mt-1">{r.l}</div></div>)}
        </div>
      </div>

      {summary.all_time && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-900 border border-green-500/20 rounded-xl p-5">
            <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Best Single Trade</div>
            <div className="text-green-400 text-2xl font-bold">+${(summary.all_time.best||0).toFixed(2)}</div>
          </div>
          <div className="bg-slate-900 border border-red-500/20 rounded-xl p-5">
            <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Worst Single Trade</div>
            <div className="text-red-400 text-2xl font-bold">${(summary.all_time.worst||0).toFixed(2)}</div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── MAIN APP ──────────────────────────────────────────────────────────────────
export default function App() {
  const [auth,setAuth]=useState(()=>{ try{return JSON.parse(localStorage.getItem("cb_auth")||"null");}catch{return null;} });
  const [page,setPage]=useState("dashboard");
  const [mode,setMode]=useState("demo");
  const [sidebarOpen,setSidebarOpen]=useState(false);
  const [unread,setUnread]=useState(0);

  useEffect(()=>{
    if(auth?.token){
      api("/api/bot/mode",{},auth.token).then(r=>{ if(r.mode) setMode(r.mode); });
      api("/api/alerts",{},auth.token).then(a=>{ if(Array.isArray(a)) setUnread(a.filter(x=>!x.is_read).length); });
    }
  },[auth,page]);

  const login=data=>{ setAuth(data); localStorage.setItem("cb_auth",JSON.stringify(data)); };
  const logout=()=>{ setAuth(null); localStorage.removeItem("cb_auth"); };
  const switchMode=async m=>{ await api(`/api/bot/mode/${m}`,{method:"POST"},auth.token); setMode(m); };

  if(!auth) return <LoginPage onLogin={login}/>;

  const nav=[
    {id:"dashboard",label:"Dashboard",icon:"dashboard"},
    {id:"trading",label:mode==="demo"?"Paper Trading":"Live Trading",icon:"trade"},
    {id:"bot",label:"Bot Control",icon:"bot"},
    {id:"history",label:"Trade History",icon:"chart"},
    {id:"analytics",label:"Analytics",icon:"analytics"},
    {id:"backtest",label:"Backtesting",icon:"play"},
    {id:"alerts",label:"Alerts",icon:"alert",badge:unread},
    {id:"chat",label:"AI Advisor",icon:"chat"},
    {id:"settings",label:"Settings",icon:"settings"},
  ];

  const pages={
    dashboard:<DashboardPage token={auth.token} mode={mode}/>,
    trading:<TradingPage token={auth.token} mode={mode}/>,
    bot:<BotPage token={auth.token} mode={mode}/>,
    history:<TradesPage token={auth.token} mode={mode}/>,
    analytics:<AnalyticsPage token={auth.token} mode={mode}/>,
    backtest:<BacktestPage token={auth.token}/>,
    alerts:<AlertsPage token={auth.token}/>,
    chat:<ChatPage token={auth.token} user={auth} mode={mode}/>,
    settings:<SettingsPage token={auth.token} user={auth} onProfileUpdate={p=>{ const updated={...auth,username:p.username,email:p.email}; setAuth(updated); localStorage.setItem("cb_auth",JSON.stringify(updated)); }}/>,
  };

  const SidebarContent = () => (
    <>
      <div className="p-5 border-b border-slate-800 space-y-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-gradient-to-br from-cyan-400 to-violet-500 rounded-xl flex items-center justify-center"><span className="text-white font-bold">₿</span></div>
          <div><div className="text-white font-bold text-sm">CryptoBot Pro</div><div className="text-slate-500 text-xs">Algorithmic Trading</div></div>
        </div>
        <ModeSwitcher mode={mode} onSwitch={switchMode}/>
      </div>
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {nav.map(n=>(
          <button key={n.id} onClick={()=>{setPage(n.id);setSidebarOpen(false);}}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${page===n.id?"bg-gradient-to-r from-cyan-500/15 to-violet-500/10 text-white border border-cyan-500/20":"text-slate-500 hover:text-slate-200 hover:bg-slate-800/60"}`}>
            <Icon name={n.icon} size={18} className={page===n.id?"text-cyan-400":""}/>
            {n.label}
            {n.badge>0&&<span className="ml-auto bg-cyan-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">{n.badge}</span>}
          </button>
        ))}
      </nav>
      <div className="p-3 border-t border-slate-800">
        <div className="flex items-center gap-3 px-3 py-2.5">
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-violet-500 rounded-full flex items-center justify-center text-white text-xs font-bold">{auth.username?.charAt(0)?.toUpperCase()}</div>
          <div className="flex-1 min-w-0"><div className="text-white text-sm font-medium truncate">{auth.username}</div><ModeBadge mode={mode}/></div>
          <button onClick={logout} className="text-slate-500 hover:text-red-400 transition-colors" title="Sign out"><Icon name="logout" size={18}/></button>
        </div>
      </div>
    </>
  );

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden lg:flex flex-col w-64 bg-slate-950 border-r border-slate-800 flex-shrink-0">
        <SidebarContent/>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={()=>setSidebarOpen(false)}/>
          <div className="relative z-10 w-64 bg-slate-950 border-r border-slate-800 flex flex-col h-full"><SidebarContent/></div>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile header */}
        <div className="lg:hidden flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-950 flex-shrink-0">
          <button onClick={()=>setSidebarOpen(true)} className="text-slate-400 hover:text-white p-1">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-cyan-400 to-violet-500 rounded-lg flex items-center justify-center"><span className="text-white font-bold text-xs">₿</span></div>
            <span className="text-white font-bold text-sm">CryptoBot Pro</span>
            <ModeBadge mode={mode}/>
          </div>
          <div className="w-8"/>
        </div>
        <main className="flex-1 overflow-y-auto p-5 lg:p-7">{pages[page]}</main>
      </div>
    </div>
  );
}
