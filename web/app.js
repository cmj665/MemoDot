const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

let records = [];
let month = new Date();
let recording = false;
let visibleRecords = null;
const generatingCards = new Set();

// 参考页面的顶部工具、诗词和天气信息，挂载到实际的 PocketMemory 工作区。
const extraStyle = document.createElement("style");
extraStyle.textContent = `.top-tools{display:flex;align-items:center;gap:10px;margin-left:auto}.top-search{display:flex;align-items:center;border:1px solid #d2d2d7;border-radius:999px;background:#fff;padding:3px 6px 3px 12px}.top-search input{width:145px;border:0;outline:0;background:transparent;font:13px inherit}.top-search button{border:0;background:transparent;color:#0071e3;font-size:17px}.login-button{border:0;border-radius:999px;padding:9px 13px;background:#0071e3;color:#fff;cursor:pointer;font-size:12px}.daily-strip{display:grid;grid-template-columns:1fr;gap:16px;margin:24px 0 0}.daily-poem,.weather-card{border-radius:20px;padding:22px;box-shadow:var(--shadow)}.daily-poem{background:linear-gradient(135deg,#69758d,#8792a8);color:#fff;min-height:145px}.daily-poem small{letter-spacing:1.5px;color:#dbe7ff}.daily-poem small b{float:right;font:12px ui-monospace,monospace;letter-spacing:0}.daily-poem h2{margin:20px 0 8px;font:32px "STKaiti","KaiTi",serif}.daily-poem p{margin:0;color:#e5ebf5}.weather-card{background:linear-gradient(135deg,#eaf4ff,#f5efff);display:flex;align-items:center;gap:20px}.weather-card>div:first-child{display:flex;flex-direction:column;gap:6px;color:#687da5;min-width:100px}.weather-main{display:flex;align-items:center;gap:12px;margin:0}.weather-main span{font-size:36px}.weather-main strong{font-size:29px}.weather-card small{color:var(--muted)}.weather-card select{margin-left:auto;width:180px;padding:8px;border:1px solid #d2d2d7;border-radius:8px;background:#fff}.memory-login{position:fixed;inset:0;z-index:30;display:grid;place-items:center;background:#0007}.memory-login[hidden]{display:none}.memory-login-panel{position:relative;width:min(390px,calc(100% - 30px));padding:28px;border-radius:20px;background:#fff;box-shadow:0 20px 70px #0005}.memory-login-panel h2{margin:0 0 8px}.memory-login-panel label{display:block;margin-top:14px;color:var(--muted);font-size:13px}.memory-login-panel input{display:block;width:100%;margin-top:6px;padding:10px;border:1px solid #d2d2d7;border-radius:8px}.memory-login-panel .primary{width:100%;margin-top:18px}.memory-login-close{position:absolute;right:12px;top:9px;border:0;background:transparent;font-size:22px}@media(max-width:800px){.top-tools{width:100%;order:5}.top-search{flex:1}.top-search input{width:100%}.weather-card{align-items:flex-start;flex-wrap:wrap}.weather-card select{margin-left:0;width:100%}}`;
document.head.appendChild(extraStyle);
const loginStyle = document.createElement("style");
loginStyle.textContent = `.memory-login{background:#f6f8fb}.memory-login-panel{width:min(615px,calc(100% - 32px));padding:48px 30px 28px;border:1px solid #d8dee4;border-radius:10px;background:#f6f8fb;box-shadow:0 8px 25px #1f23280d;text-align:center}.project-logo{display:flex;justify-content:center;align-items:center;height:52px;margin-bottom:20px}.project-logo img{width:42px;height:42px;object-fit:contain;margin-left:-5px}.memory-login-panel h2{font-size:30px;font-weight:400;margin:0 0 22px}.memory-login-panel>p{font-size:21px;color:#656d76;margin:0 0 30px}.memory-login-panel form{text-align:left;border:1px solid #d8dee4;border-radius:10px;padding:30px;background:#f6f8fb}.login-methods{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}.login-methods button{border:1px solid #d8dee4;border-radius:8px;background:#fff;padding:14px 5px;font-size:18px;cursor:pointer}.login-methods button.active{border-color:#0969da;color:#0969da}.memory-login-panel label{display:block;margin-top:17px;color:#1f2328;font-size:16px;font-weight:700}.memory-login-panel input{font-size:17px;padding:14px;border-radius:8px}.memory-login-panel .primary{width:100%;margin-top:22px;border-radius:8px;padding:14px;font-size:18px}.register-row{margin-top:20px;text-align:center;font-size:21px}.register-row button{border:0;background:transparent;color:#0969da;font-size:21px;cursor:pointer}.login-note{margin-top:25px;color:#656d76;font-size:16px}@media(max-width:650px){.memory-login-panel{padding:30px 16px 20px}.memory-login-panel>p{font-size:17px}.memory-login-panel form{padding:20px}.login-methods button,.register-row{font-size:15px}}`;
document.head.appendChild(loginStyle);
function mountReferenceExtras() {
  const header = document.querySelector(".topbar");
  if (!header || document.querySelector(".daily-strip")) return;
  const oldTime = document.querySelector("#top-time");
  const tools = document.createElement("div"); tools.className = "top-tools";
  tools.innerHTML = `<div class="top-search"><input id="top-search" placeholder="搜索记录…"><button id="top-search-button" type="button">⌕</button></div>`;
  if (oldTime) tools.append(oldTime); const login = document.createElement("button"); login.className="login-button"; login.id="login-button"; login.type="button"; login.textContent="登录 / 注册"; tools.append(login); header.append(tools);
  const strip = document.createElement("section"); strip.className="daily-strip"; strip.innerHTML=`<div class="daily-poem"><small>TODAY'S POEM · 北京时间 <b id="big-clock">--:--:--</b></small><h2 id="poem-title">一蓑烟雨任平生</h2><p id="poem-sub">Let me live through wind and rain with an untroubled heart. — Su Shi</p></div><div class="weather-card"><div><small>今日天气</small><span id="weather-city">北京</span></div><div class="weather-main"><span id="weather-icon">☀️</span><strong id="weather-temp">--°</strong><b id="weather-text">获取中</b></div><small id="weather-meta">天气数据加载中</small><select id="weather-city-select"><option value="39.90,116.40,北京">北京</option><option value="31.23,121.47,上海">上海</option><option value="23.13,113.26,广州">广州</option><option value="30.57,104.07,成都">成都</option><option value="30.27,120.15,杭州">杭州</option></select></div>`;
  const overview = document.querySelector("#overview");
  if (overview) overview.prepend(strip);
  document.body.insertAdjacentHTML("beforeend", `<div class="memory-login" id="memory-login" hidden><div class="memory-login-panel"><button class="memory-login-close" id="memory-login-close">×</button><div class="project-logo"><img src="/assets/memodot/00-M-a.webp" alt="M"><img src="/assets/memodot/01-e-a.webp" alt="e"><img src="/assets/memodot/02-m-a.webp" alt="m"><img src="/assets/memodot/03-o-a.webp" alt="o"><img src="/assets/memodot/04-D-a.webp" alt="D"><img src="/assets/memodot/05-o-a.webp" alt="o"><img src="/assets/memodot/06-t-a.webp" alt="t"></div><h2>登录 MemoDot</h2><p>继续记录你的生活与灵感</p><form><div class="login-methods"><button type="button" class="active" data-method="邮箱">邮箱</button><button type="button" data-method="手机号">手机号</button><button type="button" data-method="QQ">QQ</button><button type="button" data-method="微信">微信</button></div><label id="memory-account-label">邮箱<input id="memory-login-account" placeholder="you@example.com"></label><label>密码<input id="memory-login-password" type="password" placeholder="请输入密码"></label><button type="button" class="primary" id="memory-login-submit">登录</button><div class="register-row"><span id="memory-register-hint">还没有账号？</span><button type="button" id="memory-register">注册账号</button></div></form><div class="login-note">登录即代表你同意 MemoDot 的服务条款与隐私政策</div></div></div>`);
  document.querySelector("#top-search-button").onclick=()=>{document.querySelector("#memory-search").value=document.querySelector("#top-search").value;show("records");renderHistory()}; document.querySelector("#top-search").onkeydown=e=>{if(e.key==='Enter')document.querySelector("#top-search-button").click()};
  const modal=document.querySelector("#memory-login"); document.querySelector("#login-button").onclick=()=>modal.hidden=false; document.querySelector("#memory-login-close").onclick=()=>modal.hidden=true; document.querySelector("#memory-login-submit").onclick=()=>{if(document.querySelector("#memory-login-account").value.trim()){document.querySelector("#login-button").textContent=document.querySelector("#memory-login-account").value.trim().slice(0,12);modal.hidden=true}};
  document.querySelectorAll(".login-methods button").forEach(button=>button.onclick=()=>{document.querySelectorAll(".login-methods button").forEach(item=>item.classList.remove("active"));button.classList.add("active");document.querySelector("#memory-account-label").firstChild.textContent=button.dataset.method;document.querySelector("#memory-login-account").placeholder=button.dataset.method==="手机号"?"请输入手机号":button.dataset.method==="QQ"?"请输入 QQ 号":button.dataset.method==="微信"?"请输入微信号":"you@example.com"});
  let registering=false; document.querySelector("#memory-register").onclick=()=>{registering=!registering;document.querySelector("#memory-login-submit").textContent=registering?"注册并登录":"登录";document.querySelector("#memory-register-hint").textContent=registering?"已有账号？":"还没有账号？";document.querySelector("#memory-register").textContent=registering?"返回登录":"注册账号"};
  const poems=[["一蓑烟雨任平生","Let me live through wind and rain with an untroubled heart. — Su Shi"],["海上生明月，天涯共此时","The moon rises over the sea; we share it though far apart. — Zhang Jiuling"],["晚来天欲雪，能饮一杯无","Snow is about to fall tonight; shall we share a cup? — Bai Juyi"]]; let pi=0; const showPoem=()=>{document.querySelector("#poem-title").textContent=poems[pi][0];document.querySelector("#poem-sub").textContent=poems[pi][1]}; document.querySelector("#poem-title").onclick=()=>{pi=(pi+1)%poems.length;showPoem()};setInterval(()=>{pi=(pi+1)%poems.length;showPoem()},12000);
  const update=()=>{const n=new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Shanghai"}));document.querySelector("#big-clock").textContent=n.toLocaleTimeString("zh-CN",{hour12:false});document.querySelector("#top-time").textContent=n.toLocaleDateString("zh-CN",{month:"numeric",day:"numeric",weekday:"short"})}; update();setInterval(update,1000);
  const weather=(code,temp,city)=>{const s=code<=1?["☀️","晴朗"]:code<=3?["⛅","多云"]:code<=67?["🌧️","有雨"]:code<=77?["❄️","降雪"]:["⛈️","雷雨"];document.querySelector("#weather-icon").textContent=s[0];document.querySelector("#weather-text").textContent=s[1];document.querySelector("#weather-temp").textContent=Math.round(temp)+"°";document.querySelector("#weather-city").textContent=city;document.querySelector("#weather-meta").textContent="实时天气 · 中国标准时间"}; const loadWeather=async(v="39.90,116.40,北京")=>{const [lat,lon,city]=v.split(",");try{const j=await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,weather_code&timezone=Asia%2FShanghai`).then(r=>r.json());weather(j.current.weather_code,j.current.temperature_2m,city)}catch{weather(0,22,city)}};document.querySelector("#weather-city-select").onchange=e=>loadWeather(e.target.value);loadWeather();
}
mountReferenceExtras();

// 每个事件独立展示日记插画；文字由网页排版，不画进图片。
function sceneCard(record, index) {
  const image = record.illustrations?.[String(index)];
  const key = `${record.id}:${index}`;
  return `<div class="scene-card">${image
    ? `<img loading="lazy" src="${escapeHtml(image.url)}" alt="这条事件的动物手绘场景"><span>一件小事，一张回忆</span>`
    : `<div class="scene-placeholder">🐰 ☕ 🐻<small>把这件事画进日记</small></div><button class="secondary" data-action="generate-image" data-id="${record.id}" data-index="${index}" ${generatingCards.has(key) ? 'disabled' : ''}>${generatingCards.has(key) ? '正在绘制，请稍候…' : '生成场景卡'}</button>`}</div>`;
}

// 搜索条件和详情面板在页面初始化时挂载。
document.querySelector(".search-box").insertAdjacentHTML("beforeend", '<input id="memory-date" type="date" aria-label="按日期筛选"><button class="secondary" id="clear-search">清除</button>');
document.body.insertAdjacentHTML("beforeend", '<dialog id="memory-dialog"><div class="dialog-head"><h2>记录详情</h2><button id="close-detail" class="secondary">关闭</button></div><div id="memory-detail"></div></dialog>');

// 原声播放器沿用页面的 Apple 风格，不额外引入前端框架。
const mediaStyle = document.createElement("style");
mediaStyle.textContent += `.search-box{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.search-box input{width:180px;padding:9px 12px;border:1px solid #d2d2d7;border-radius:999px;font:inherit}.mood-history{margin-top:20px}.mood-delete{margin-left:10px}#memory-dialog{width:min(680px,calc(100vw - 32px));max-height:85vh;overflow:auto;border:1px solid #e5e5ea;border-radius:20px;padding:26px;box-shadow:0 20px 70px #0003;color:#1d1d1f}#memory-dialog::backdrop{background:#0007}.dialog-head{display:flex;justify-content:space-between;align-items:center}.dialog-head h2{margin:0}.detail-text{white-space:pre-wrap;line-height:1.7}`;
document.head.appendChild(mediaStyle);
mediaStyle.textContent += `.scene-card{max-width:340px;margin:18px 0;padding:12px;background:#fffaf0;border:1px solid #e7dfd3;border-radius:22px;box-shadow:0 8px 22px #48351b0c}.scene-card img{display:block;width:100%;aspect-ratio:1;object-fit:contain;border-radius:15px}.scene-card>span{display:block;padding:12px;color:#786c5b;font-size:12px}.scene-placeholder{padding:25px;text-align:center;font-size:35px}.scene-placeholder small{display:block;margin-top:10px;font-size:13px;color:#786c5b}.scene-card button{width:100%}.scene-card button:disabled{opacity:.6}`;
mediaStyle.textContent += `.audio-block{display:grid;grid-template-columns:auto minmax(180px,520px);align-items:center;gap:14px;margin:16px 0 12px;padding-top:0;border-top:0}.audio-block>span{color:#4f5964;font-size:14px;white-space:nowrap}.audio-block audio{display:block;width:100%;height:38px;max-height:38px;border-radius:999px}.record-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:14px}.record-actions button{border:1px solid #d4dbe5;border-radius:999px;background:#f4f8ff;color:#2563c7;padding:8px 14px;font-size:13px;cursor:pointer;transition:background .2s,border-color .2s}.record-actions button:hover{background:#e4efff;border-color:#8eb6ed}.record-actions button.danger{background:#fff3f3;border-color:#f0c4c4;color:#c43d45}.record-actions button.danger:hover{background:#ffe5e5}.memory-item{padding:20px 0}.memory-item+.memory-item{margin-top:8px}@media(max-width:650px){.audio-block{grid-template-columns:1fr;gap:7px}.audio-block audio{max-width:100%}.record-actions{gap:7px}.record-actions button{padding:7px 11px;font-size:12px}}`;
mediaStyle.textContent += `.recent-more{margin-top:18px;border-top:1px solid #e5e5ea;padding-top:14px}.recent-more summary{display:inline-block;cursor:pointer;color:#2563c7;background:#f4f8ff;border:1px solid #d4dbe5;border-radius:999px;padding:8px 15px;font-size:13px}.recent-more summary:hover{background:#e4efff}.recent-more-list{margin-top:10px}.quick-actions{display:flex;gap:18px;margin-top:16px;align-items:center}.quick-actions .upload-button{font-size:14px;font-weight:500;padding:10px 18px}.quick-actions #create-text{padding:10px 18px}@media(max-width:650px){.quick-actions{gap:12px;flex-wrap:wrap}}`;
mediaStyle.textContent += `.recent-record{padding:20px 0 18px;border-bottom:1px solid #dfe3e8}.recent-record:first-child{padding-top:8px}.recent-record-separated{border-top:1px solid #dfe3e8;padding-top:20px}.recent-record .record-meta{margin:12px 0 8px}.record-meta .time{background:#e8f2ff;color:#0969da}.record-meta span{background:#e8f2ff;color:#0969da}.recent-record .memory-item,.history-item .memory-item{padding:10px 0 6px}.recent-record .record-actions,.history-item .record-actions{margin-top:8px}.history-item .record-meta{margin:12px 0 8px}.recent-more-list .recent-record:last-child{border-bottom:0}.recent-more-list .recent-record:first-child{border-top:1px solid #dfe3e8}`;
mediaStyle.textContent += `.calendar-controls{display:flex;align-items:center;gap:8px}.calendar-controls input{border:1px solid #d2d2d7;border-radius:999px;padding:8px 11px;background:#fff;color:var(--ink);font:13px inherit}.week{display:grid;grid-template-columns:repeat(7,1fr);gap:0;padding:0}.week span{text-align:center;padding:14px 8px;color:var(--muted);border-bottom:1px solid #e5e5ea}.day{min-height:105px;overflow:hidden}.calendar-day-number{display:block;margin-bottom:4px;font-size:13px;font-weight:600;color:var(--ink)}.day.today .calendar-day-number{display:grid;place-items:center;width:25px;height:25px;border-radius:50%;background:var(--blue);color:#fff}.calendar-event{display:block;width:100%;margin-top:8px;padding:5px 7px;border:0;border-radius:7px;background:#e8f2ff;color:#0969da;font:11px inherit;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer}.calendar-event:hover{background:#d7eaff}.calendar-more{display:block;margin-top:6px;color:#6e6e73;font-size:11px}@media(max-width:650px){.calendar-controls input{width:130px}.week span{padding:10px 3px}.day{min-height:80px;padding:7px}.calendar-event{font-size:10px;padding:4px}}`;

// MemoDot opening: each character has two independent transparent assets.
const memoConfig = { text: "MemoDot", images: [["/assets/memodot/00-M-a.webp","/assets/memodot/00-M-b.webp"],["/assets/memodot/01-e-a.webp","/assets/memodot/01-e-b.webp"],["/assets/memodot/02-m-a.webp","/assets/memodot/02-m-b.webp"],["/assets/memodot/03-o-a.webp","/assets/memodot/03-o-b.webp"],["/assets/memodot/04-D-a.webp","/assets/memodot/04-D-b.webp"],["/assets/memodot/05-o-a.webp","/assets/memodot/05-o-b.webp"],["/assets/memodot/06-t-a.webp","/assets/memodot/06-t-b.webp"]] };
let memoPaused = false; let memoRun = 0;
function buildMemoTitle(){const title=$(".memodot-title"); if(!title)return; title.innerHTML=""; [...memoConfig.text].forEach((char,index)=>{const slot=document.createElement("span");slot.className="memo-letter";slot.tabIndex=0;slot.dataset.index=index;slot.style.setProperty("--tilt",`${index%2?-3:3}deg`);slot.innerHTML=`<span class="memo-fallback">${char}</span><img alt="${char}" src="${memoConfig.images[index][0]}">`; const swap=()=>{const img=slot.querySelector("img");img.src=img.src.endsWith(memoConfig.images[index][0])?memoConfig.images[index][1]:memoConfig.images[index][0]};slot.addEventListener("mouseenter",swap);slot.addEventListener("focus",swap);slot.addEventListener("touchstart",()=>{slot.classList.add("touching");swap();setTimeout(()=>slot.classList.remove("touching"),500)},{passive:true});title.append(slot)});}
function playMemo(){if(memoPaused)return; memoRun+=1;const run=memoRun;document.querySelectorAll(".memo-letter").forEach((slot,index)=>{slot.classList.remove("exiting");setTimeout(()=>{if(run===memoRun&&!memoPaused)slot.classList.add("revealed")},index*145)});}
function exitMemo(){document.querySelectorAll(".memo-letter").forEach((slot,index)=>setTimeout(()=>slot.classList.add("exiting"),index*35));}
buildMemoTitle(); playMemo(); setInterval(()=>{if(!memoPaused&&document.visibilityState==="visible"){document.querySelectorAll(".memo-letter").forEach(slot=>{if(Math.random()<.22){const img=slot.querySelector("img");const i=Number(slot.dataset.index);img.src=img.src.endsWith(memoConfig.images[i][0])?memoConfig.images[i][1]:memoConfig.images[i][0]}})}},4200);
$("#memodot-replay")?.addEventListener("click",()=>{buildMemoTitle();playMemo()}); $("#memodot-pause")?.addEventListener("click",(event)=>{memoPaused=!memoPaused;event.currentTarget.textContent=memoPaused?"继续动画":"暂停动画";event.currentTarget.setAttribute("aria-pressed",String(memoPaused));if(!memoPaused)playMemo()});
function enterWorkspace(){
  exitMemo();
  setTimeout(()=>{$("#welcome").hidden=true;$("#workspace").hidden=false;window.scrollTo({top:0,behavior:"smooth"});},640);
}
function returnToWelcome(){
  $("#workspace").hidden=true;$("#welcome").hidden=false;buildMemoTitle();playMemo();window.scrollTo({top:0,behavior:"smooth"});
}
$("#enter-app")?.addEventListener("click",enterWorkspace);
$("#back-welcome")?.addEventListener("click",returnToWelcome);

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[char]);
}

function toast(text) {
  const element = $("#toast");
  element.textContent = text;
  element.classList.add("show");
  setTimeout(() => element.classList.remove("show"), 2200);
}

async function confirmSuggestedMood(value) {
  if (!value || !confirm(`语音中提到了“${value}”。要保存为今天的心情吗？`)) return;
  await requestJson("/moods", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: value, source: "voice-confirmed" })
  });
  await loadMoods();
}

function tick() {
  const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Shanghai" }));
  $("#top-time").textContent = now.toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" });
  $("#clock").textContent = now.toLocaleTimeString("zh-CN", { hour12: false });
  const target = new Date(now);
  target.setHours(18, 0, 0, 0);
  if (target < now) target.setDate(target.getDate() + 1);
  const remaining = target - now;
  $("#countdown").textContent = String(Math.floor(remaining / 36e5)).padStart(2, "0") + ":" +
    String(Math.floor(remaining % 36e5 / 6e4)).padStart(2, "0") + ":" +
    String(Math.floor(remaining % 6e4 / 1e3)).padStart(2, "0");
}

function show(view) {
  $$(".view").forEach((element) => element.classList.toggle("active", element.id === view));
  $$(".nav button").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  if (view === "calendar") renderCalendar();
  if (view === "records") renderHistory();
  if (view === "reminders") renderReminders();
  if (view === "mood") loadMoods();
}

function analysisHtml(record) {
  if (!(record.analysis?.items || []).length) return '';
  return (record.analysis?.items || []).map((item, index) => `
    <article class="memory-item${item.completed ? " task-done" : ""}">
      <label class="todo-row">
        <input type="checkbox" data-action="complete" data-id="${record.id}" data-index="${index}" ${item.completed ? "checked" : ""}>
        <b class="todo-text${item.completed ? " done" : ""}">${escapeHtml(item.summary || item.task || "一条记忆")}</b>
      </label>
      <div class="chips">
        ${item.time ? `<span class="time">◷ ${escapeHtml(formatPlannedTime(item.time, record))}</span>` : ""}
        ${item.location ? `<span class="place">⌖ ${escapeHtml(item.location)}</span>` : ""}
        ${(item.tags || []).map((tag) => `<span>#${escapeHtml(tag)}</span>`).join("")}
      </div>
    </article>`).join("");
}

function syncEditedAnalysis(analysis, oldText, newText) {
  if (!analysis || oldText === newText) return analysis;
  let start = 0;
  while (start < oldText.length && start < newText.length && oldText[start] === newText[start]) start += 1;
  let oldEnd = oldText.length;
  let newEnd = newText.length;
  while (oldEnd > start && newEnd > start && oldText[oldEnd - 1] === newText[newEnd - 1]) { oldEnd -= 1; newEnd -= 1; }
  const oldPart = oldText.slice(start, oldEnd);
  const newPart = newText.slice(start, newEnd);
  if (!oldPart) return analysis;
  const visit = (value, key = "") => {
    if ((key === "summary" || key === "task") && typeof value === "string") return newText;
    if (typeof value === "string") return value.replaceAll(oldPart, newPart);
    if (Array.isArray(value)) return value.map((item) => visit(item, key));
    if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([childKey, item]) => [childKey, visit(item, childKey)]));
    return value;
  };
  return visit(analysis);
}

function formatPlannedTime(raw, record) {
  if (!raw) return "时间待定";
  const source = String(raw).trim();
  const base = new Date(record.created_at || Date.now());
  const date = new Date(base);
  if (/明天/.test(source)) date.setDate(date.getDate() + 1);
  else if (/后天/.test(source)) date.setDate(date.getDate() + 2);
  const dateMatch = source.match(/(20\d{2})[年\/-](\d{1,2})[月\/-](\d{1,2})/);
  if (dateMatch) { date.setFullYear(+dateMatch[1], +dateMatch[2] - 1, +dateMatch[3]); }
  const timeMatch = source.match(/(上午|下午|晚上|早上)?\s*([0-9]{1,2})\s*点(?:([0-9]{1,2})分?)?/);
  if (timeMatch) {
    let hour = +timeMatch[2]; if (timeMatch[1] === "下午" || timeMatch[1] === "晚上") hour = hour < 12 ? hour + 12 : hour;
    date.setHours(hour, +(timeMatch[3] || 0), 0, 0);
  }
  const pad = value => String(value).padStart(2, "0");
  return `${date.getFullYear()}年${pad(date.getMonth() + 1)}月${pad(date.getDate())}日 ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function actionsHtml(record) {
  return `<div class="record-actions">
    <button data-action="detail" data-id="${record.id}">查看详情</button>
    ${record.mood_suggestion ? `<button data-action="save-mood" data-id="${record.id}">确认心情：${escapeHtml(record.mood_suggestion)}</button>` : ""}
    <button data-action="edit" data-id="${record.id}">编辑文字</button>
    <button data-action="replace" data-id="${record.id}">替换录音</button>
    <button class="danger" data-action="delete" data-id="${record.id}">删除</button>
  </div>`;
}

function audioHtml(record) {
  if (!record.audio_url) return `<p class="audio-missing">这条旧记录没有可用的原始音频</p>`;
  return `<div class="audio-block"><span>原声录音</span><audio controls preload="none" src="${escapeHtml(record.audio_url)}"></audio></div>`;
}

function fallbackMetaHtml(record) {
  const text = record.text || "";
  const time = text.match(/(今天|明天|后天|周[一二三四五六日末])?\s*(上午|下午|晚上|早上)?\s*([0-9]{1,2})\s*点(?:([0-9]{1,2})分)?/);
  const tags = [];
  if (/睡觉|起床|吃饭|早餐|午餐|晚餐/.test(text)) tags.push("#作息");
  if (/工作|项目|会议|客户/.test(text)) tags.push("#工作");
  if (/学习|读书|看书/.test(text)) tags.push("#学习");
  if (!tags.length) tags.push("#随手记");
  const timeLabel = time ? formatPlannedTime(`${time[1] || "今天"} ${time[2] || ""}${time[3]}${time[4] ? `${time[4]}分` : ""}`, record) : "记录时间待定";
  return `<div class="chips record-meta"><span class="time">◷ ${escapeHtml(timeLabel)}</span>${tags.map(tag => `<span>${escapeHtml(tag)}</span>`).join("")}</div>`;
}

function recordMetaHtml(record) {
  return (record.analysis?.items || []).length ? analysisHtml(record) : fallbackMetaHtml(record);
}

function renderLatest(recentRecords) {
  const latest = $("#latest");
  if (!recentRecords.length) {
    latest.className = "empty";
    latest.textContent = "最近 12 小时还没有记录。";
    return;
  }
  latest.classList.remove("empty");
  const visible = recentRecords.slice(0, 2);
  const hidden = recentRecords.slice(2);
  latest.innerHTML = visible.map((record, index) => `
    <article class="recent-record${index ? " recent-record-separated" : ""}">
      <small class="muted">${new Date(record.created_at).toLocaleString()}</small>
      <span class="transcript-label">语音识别文字</span>
      <p class="latest-text">${escapeHtml(record.text || "未识别到文字")}</p>
      ${audioHtml(record)}
      ${recordMetaHtml(record)}
      ${actionsHtml(record)}
    </article>`).join("") + (hidden.length ? `<details class="recent-more"><summary>查看其余 ${hidden.length} 条记录</summary><div class="recent-more-list">${hidden.map((record) => `
    <article class="recent-record recent-record-separated"><small class="muted">${new Date(record.created_at).toLocaleString()}</small><span class="transcript-label">语音识别文字</span><p class="latest-text">${escapeHtml(record.text || "未识别到文字")}</p>${audioHtml(record)}${recordMetaHtml(record)}${actionsHtml(record)}</article>`).join("")}</div></details>` : "");
  const item = recentRecords[0].analysis?.items?.[0];
  if (item) $("#next-event").textContent = `${item.time || "待定"} · ${item.task || item.summary || "新的安排"}`;
}

function renderHistory() {
  const shown = visibleRecords ?? records;
  $("#record-count").textContent = `${shown.length} 条${visibleRecords ? "搜索结果" : ""}`;
  $("#history").innerHTML = shown.length ? shown.map((record) => `
    <article class="history-item">
      <time>${new Date(record.created_at).toLocaleString()}</time>
      <span class="transcript-label">语音识别文字</span>
      <p>${escapeHtml(record.text || "未识别到文字")}</p>
      ${audioHtml(record)}
      ${recordMetaHtml(record)}
      ${actionsHtml(record)}
    </article>`).join("") : '<p class="muted">还没有记录。</p>';
}

function renderReminders() {
  const items = records.flatMap((record) => (record.analysis?.items || []).map((item, index) => ({ item, index, record })));
  $("#reminder-list").innerHTML = items.filter(({ item }) => item.time || item.intent === "计划").map(({ item, index, record }) => `
    <article class="history-item${item.completed ? " task-done" : ""}">
      <label class="todo-row">
        <input type="checkbox" data-action="complete" data-id="${record.id}" data-index="${index}" ${item.completed ? "checked" : ""}>
        <b class="todo-text${item.completed ? " done" : ""}">🔔 ${escapeHtml(item.task || item.summary || "待办事项")}</b>
      </label>
        <p class="muted">${escapeHtml(item.time || "时间待定")} · ${escapeHtml(item.location || "未指定地点")}</p>
        ${item.time && !item.completed ? `<button class="secondary" data-action="send-reminder" data-id="${record.id}" data-index="${index}">发送到 StickS3</button>` : ""}
    </article>`).join("") || '<p class="muted">暂无提醒。</p>';
}

async function loadRecords({ quiet = false } = {}) {
  try {
    const [allResponse, recentResponse] = await Promise.all([
      fetch("/memories?limit=100", { cache: "no-store" }),
      fetch("/memories/recent?hours=12&limit=3", { cache: "no-store" })
    ]);
    if (!allResponse.ok) throw new Error("读取历史记录失败，请确认网页后端正在运行");
    const allData = await allResponse.json();
    records = allData.items || [];
    // 兼容后端重启前的旧接口：即便 recent 暂时不可用，全部记录也不能显示为空。
    const recentData = recentResponse.ok ? await recentResponse.json() : { items: records.slice(0, 3) };
    renderLatest(recentData.items || []);
    if (visibleRecords) await runSearch(); else renderHistory();
    renderReminders();
  } catch (error) {
    if (!quiet) toast(error.message);
  }
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "操作失败");
  return data;
}

// 新增入口：用户既可以创建纯文字记录，也可以上传音频并自动识别。
$("#record").insertAdjacentHTML("afterend", `
  <div class="quick-actions">
    <button class="secondary" id="create-text">＋ 新增文字</button>
    <label class="secondary upload-button">上传音频
      <input id="upload-audio" type="file" accept="audio/*,.mp3,.wav,.m4a,.flac,.ogg,.aac,.webm" hidden>
    </label>
  </div>`);

$("#create-text").onclick = async () => {
  const text = prompt("输入新的记录内容");
  if (!text?.trim()) return;
  try {
    await requestJson("/memories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.trim() })
    });
    await loadRecords();
    toast("文字记录已创建");
  } catch (error) { toast(error.message); }
};

$("#upload-audio").onchange = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  $("#record-status").textContent = "正在识别上传的音频…";
  try {
    const result = await requestJson(`/memories/transcribe?analyze=${$("#analyze").checked}`, { method: "POST", body: form });
    await loadRecords();
    await confirmSuggestedMood(result.mood_suggestion);
    toast("录音、文字和原声已保存");
  } catch (error) { toast(error.message); }
  finally {
    event.target.value = "";
    $("#record-status").textContent = "硬件或音频均可";
  }
};

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = button.dataset.id;
  const record = records.find((item) => item.id === id);
  try {
    if (button.dataset.action === 'generate-image') {
      const index = Number(button.dataset.index);
      const key = `${id}:${index}`;
      if (generatingCards.has(key)) return;
      generatingCards.add(key);
      button.disabled = true;
      button.textContent = '正在绘制，请稍候…';
      try {
        const updated = await requestJson(`/memories/${id}/items/${index}/image`, {method:'POST'});
        if ($('#memory-dialog').open) {
          $('#memory-detail').innerHTML = `<p class="detail-text">${escapeHtml(updated.text)}</p>${audioHtml(updated)}${analysisHtml(updated)}${actionsHtml(updated)}`;
        }
        toast('场景卡已保存');
      } finally {
        generatingCards.delete(key);
        button.disabled = false;
        button.textContent = '生成场景卡';
        await loadRecords();
      }
      return;
    }
    if (button.dataset.action === "detail") {
      const detail = await requestJson(`/memories/${id}`);
      $("#memory-detail").innerHTML = `<p class="muted">${new Date(detail.created_at).toLocaleString()}</p><span class="transcript-label">完整识别文字</span><p class="detail-text">${escapeHtml(detail.text || "未识别到文字")}</p>${audioHtml(detail)}${analysisHtml(detail)}${actionsHtml(detail)}`;
      $("#memory-dialog").showModal();
      return;
    }
    if (button.dataset.action === "save-mood") {
      await confirmSuggestedMood(record?.mood_suggestion);
      return;
    }
    if (button.dataset.action === "send-reminder") {
      button.disabled = true;
      button.textContent = "正在连接设备…";
      try {
        const result = await requestJson(`/memories/${id}/items/${button.dataset.index}/reminder`, { method: "POST" });
        toast(`已发送，${result.seconds} 秒后播报`);
      } finally {
        button.disabled = false;
        button.textContent = "发送到 StickS3";
      }
      return;
    }
    if (button.dataset.action === "edit") {
      const oldText = record?.text || "";
      const text = prompt("修改识别文字", oldText);
      if (!text?.trim() || text.trim() === oldText) return;
      const updated = await requestJson(`/memories/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.trim() })
      });
      const current = records.find((item) => item.id === id);
      if (current) {
        current.text = text.trim();
        current.analysis = syncEditedAnalysis(updated.analysis || current.analysis, oldText, current.text);
      }
      // 记录页在搜索状态下使用 visibleRecords 渲染，也要同步更新其中的对象。
      const visible = visibleRecords?.find((item) => item.id === id);
      if (visible && visible !== current) {
        visible.text = text.trim();
        visible.analysis = syncEditedAnalysis(updated.analysis || visible.analysis, oldText, visible.text);
      }
      renderHistory();
      renderLatest(records.slice(0, 3));
      renderReminders();
      toast("文字已修改");
    } else if (button.dataset.action === "delete") {
      if (!confirm("确定删除这条记录吗？项目保存的原声也会一起删除。")) return;
      await requestJson(`/memories/${id}`, { method: "DELETE" });
      toast("记录已删除");
    } else if (button.dataset.action === "replace") {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "audio/*,.mp3,.wav,.m4a,.flac,.ogg,.aac,.webm";
      input.onchange = async () => {
        if (!input.files[0]) return;
        const form = new FormData();
        form.append("file", input.files[0]);
        toast("正在替换录音并重新识别…");
        try {
          await requestJson(`/memories/${id}/audio?analyze=${$("#analyze").checked}`, { method: "PUT", body: form });
          await loadRecords();
          toast("原声和识别文字已更新");
        } catch (error) { toast(error.message); }
      };
      input.click();
      return;
    }
    if ($("#memory-dialog").open) $("#memory-dialog").close();
    await loadRecords();
  } catch (error) { toast(error.message); }
});

async function loadMoods() {
  try {
    const data = await requestJson("/moods?limit=30");
    const items = data.items || [];
    const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Shanghai" });
    const latest = items.find((item) => new Date(item.created_at).toLocaleDateString("en-CA", { timeZone: "Asia/Shanghai" }) === today);
    $("#mood-text").textContent = latest ? latest.content : "尚未记录";
    $("#mood-history").innerHTML = items.length ? items.map((mood) => `
      <article class="history-item"><time>${new Date(mood.created_at).toLocaleString()}</time><p>${escapeHtml(mood.content)}</p><small>${escapeHtml(mood.source)}</small><button class="link mood-delete" data-mood-id="${mood.id}">删除</button></article>`).join("") : '<p class="muted">还没有心情记录。</p>';
  } catch (error) { toast(error.message); }
}

$("#mood-btn").onclick = async () => {
  const content = prompt("记录今天的心情，确认后保存", $("#mood-text").textContent === "尚未记录" ? "" : $("#mood-text").textContent);
  if (!content?.trim()) return;
  try { await requestJson("/moods", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: content.trim(), source: "manual" }) }); await loadMoods(); toast("心情已保存"); }
  catch (error) { toast(error.message); }
};

async function runSearch() {
  const query = $("#memory-search").value.trim();
  const date = $("#memory-date").value;
  if (!query && !date) { visibleRecords = null; renderHistory(); return; }
  try { const data = await requestJson(`/memories/search?q=${encodeURIComponent(query)}&date=${encodeURIComponent(date)}&limit=100`); visibleRecords = data.items || []; renderHistory(); }
  catch (error) { toast(error.message); }
}
$("#search-memory").onclick = runSearch;
$("#clear-search").onclick = () => { $("#memory-search").value = ""; $("#memory-date").value = ""; visibleRecords = null; renderHistory(); };
$("#memory-search").onkeydown = (event) => { if (event.key === "Enter") $("#search-memory").click(); };
$("#memory-date").onchange = runSearch;
$("#close-detail").onclick = () => $("#memory-dialog").close();
document.addEventListener("click", async (event) => {
  const button = event.target.closest(".mood-delete");
  if (!button) return;
  if (!confirm("删除这条心情记录吗？")) return;
  try { await requestJson(`/moods/${button.dataset.moodId}`, { method: "DELETE" }); await loadMoods(); toast("心情已删除"); }
  catch (error) { toast(error.message); }
});

document.addEventListener("change", async (event) => {
  const checkbox = event.target.closest('input[data-action="complete"]');
  if (!checkbox) return;
  checkbox.disabled = true;
  try {
    await requestJson(`/memories/${checkbox.dataset.id}/items/${checkbox.dataset.index}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ completed: checkbox.checked })
    });
    await loadRecords();
    toast(checkbox.checked ? "待办已完成" : "已恢复为待办");
  } catch (error) {
    checkbox.checked = !checkbox.checked;
    checkbox.disabled = false;
    toast(error.message);
  }
});

$("#record").onclick = async () => {
  const button = $("#record");
  recording = true;
  button.disabled = true;
  $("#record-status").textContent = "等待硬件按钮录音…";
  $("#error").hidden = true;
  try {
    const response = await fetch(`/hardware/record?analyze=${$("#analyze").checked}`, { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "硬件录音失败");
    await loadRecords();
    await confirmSuggestedMood(data.mood_suggestion);
    toast("新记忆和原声已保存");
    $("#record-status").textContent = "硬件或音频均可";
  } catch (error) {
    $("#error").textContent = error.message;
    $("#error").hidden = false;
    $("#record-status").textContent = "处理失败";
  } finally {
    recording = false;
    button.disabled = false;
  }
};

function renderCalendar() {
  const year = month.getFullYear(), monthIndex = month.getMonth();
  const firstDay = new Date(year, monthIndex, 1).getDay();
  const days = new Date(year, monthIndex + 1, 0).getDate();
  $("#month-title").textContent = `${year}年${monthIndex + 1}月`;
  const dateInput = $("#calendar-date");
  if (dateInput) dateInput.value = `${year}-${String(monthIndex + 1).padStart(2, "0")}-01`;
  let html = "";
  for (let index = 0; index < firstDay; index++) html += '<div class="day blank"></div>';
  for (let day = 1; day <= days; day++) {
    const today = new Date();
    const isToday = today.getFullYear() === year && today.getMonth() === monthIndex && today.getDate() === day;
    const dateKey = `${year}-${String(monthIndex + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const events = records.flatMap(record => (record.analysis?.items || []).map(item => ({ record, item }))).filter(({ record, item }) => {
      const created = new Date(record.created_at); const relative = `${item.time || ""} ${record.text || ""}`;
      const target = new Date(created); if (/明天/.test(relative)) target.setDate(target.getDate() + 1); if (/后天/.test(relative)) target.setDate(target.getDate() + 2);
      return target.getFullYear() === year && target.getMonth() === monthIndex && target.getDate() === day;
    });
    html += `<div class="day ${isToday ? "today" : ""}" data-date="${dateKey}" aria-label="${dateKey}"><b class="calendar-day-number">${day}</b>${events.slice(0, 3).map(({ record, item }) => `<button type="button" class="calendar-event" data-action="detail" data-id="${escapeHtml(record.id)}">${escapeHtml(formatPlannedTime(item.time || "", record))} · ${escapeHtml(item.task || item.summary || "待办事项")}</button>`).join("")}${events.length > 3 ? `<small class="calendar-more">还有 ${events.length - 3} 项</small>` : ""}</div>`;
  }
  $("#days").innerHTML = html;
}

const calendarToolbar = document.querySelector("#calendar .section-head > div:last-child");
if (calendarToolbar && !document.querySelector("#calendar-date")) {
  calendarToolbar.classList.add("calendar-controls");
  calendarToolbar.insertAdjacentHTML("afterbegin", '<input id="calendar-date" type="date" aria-label="选择日期">');
  const week = document.querySelector("#calendar .week");
  if (week) week.innerHTML = ["日", "一", "二", "三", "四", "五", "六"].map(day => `<span>${day}</span>`).join("");
  document.querySelector("#calendar-date").onchange = event => { const picked = new Date(`${event.target.value}T00:00:00`); if (!Number.isNaN(picked.getTime())) { month = picked; renderCalendar(); } };
}

$$(".nav button").forEach((button) => button.onclick = () => show(button.dataset.view));
$("#refresh").onclick = () => loadRecords();
$("#prev").onclick = () => { month.setMonth(month.getMonth() - 1); renderCalendar(); };
$("#next").onclick = () => { month.setMonth(month.getMonth() + 1); renderCalendar(); };
$("#today").onclick = () => { month = new Date(); renderCalendar(); };

setInterval(tick, 1000);
// 自动同步其他命令行或硬件入口刚保存的记录；录音处理中不重复请求。
setInterval(() => { if (!recording && !document.hidden) loadRecords({ quiet: true }); }, 5000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) loadRecords({ quiet: true }); });
$("#latest").closest(".card").querySelector("h2").textContent = "最新记录 · 近12小时";
tick();
loadRecords();
loadMoods();
// 独立漫画导航页，避免插画挤占语音记录区域。
const galleryScript = document.createElement('script');
galleryScript.src = '/gallery.js';
document.body.appendChild(galleryScript);
