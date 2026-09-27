// 小熊漫画日记：自动生成、叠放卡片、键盘与触摸切换、原图放大。
(() => {
  if (document.getElementById('comics')) return;
  const nav = document.querySelector('.nav');
  nav.insertAdjacentHTML('beforeend', '<button data-view="comics">漫画日记</button>');
  document.querySelector('#workspace').insertAdjacentHTML('beforeend', `
    <main id="comics" class="view">
      <header class="comic-heading"><span>MEMODOT · LITTLE BEAR DIARY</span><h1>把日常，画成回忆。</h1>
      <p>一件小事，一张小熊漫画。左右滑动，翻看你的故事。</p><small id="comic-status" role="status">正在读取事件…</small></header>
      <div id="comic-stage" tabindex="0" aria-label="漫画卡片，使用左右方向键切换"></div>
      <div class="comic-controls"><button id="comic-prev" aria-label="上一张">←</button><span id="comic-position"></span><button id="comic-next" aria-label="下一张">→</button></div>
      <p class="comic-hint">选中卡片居中放大 · 再点一次查看原图</p>
    </main>`);
  document.body.insertAdjacentHTML('beforeend', '<dialog id="comic-zoom"><button id="comic-close" aria-label="关闭大图">✕</button><img alt="小熊漫画原图"><p></p></dialog>');
  const style = document.createElement('style');
  style.textContent = `
    .comic-heading{text-align:center;padding:52px 12px 12px}.comic-heading>span{font-size:11px;letter-spacing:3px;color:#92836d}.comic-heading h1{font-size:clamp(30px,4vw,54px);font-weight:550;letter-spacing:-2px;margin:16px 0}.comic-heading p,.comic-hint{color:#82786c;font-size:14px}.comic-heading small{display:block;min-height:22px;color:#82786c}
    #comic-stage{position:relative;height:470px;overflow:hidden;perspective:1300px;touch-action:pan-y;outline-offset:-4px}
    .comic-card{position:absolute;left:50%;top:36px;width:286px;height:376px;margin-left:-143px;padding:0;border:1px solid #ded6c9;border-radius:21px;background:#fffaf1;box-shadow:0 22px 40px #392a1522;overflow:hidden;cursor:pointer;text-align:left;transition:transform .4s,opacity .4s;display:flex;flex-direction:column;color:#332a21}
    .comic-card img{width:100%;height:278px;object-fit:contain;background:#fffaf1;pointer-events:none}.comic-card .comic-placeholder{height:278px;display:grid;place-content:center;text-align:center;background:linear-gradient(145deg,#f9efdc,#eee2cd);font-size:64px}.comic-placeholder small{font-size:13px;margin-top:14px;color:#786954}.comic-caption{padding:14px 18px;overflow:hidden}.comic-caption b{display:block;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.comic-caption time{display:block;margin-top:8px;font-size:11px;color:#8b7e6e}.comic-controls{display:flex;align-items:center;justify-content:center;gap:24px}.comic-controls button,#comic-close{border:1px solid #ded6c9;border-radius:50%;background:white;width:42px;height:42px;cursor:pointer}.comic-controls button:disabled{opacity:.3;cursor:default}.comic-controls span{font-size:13px;color:#7d7264;min-width:60px;text-align:center}.comic-hint{text-align:center;margin:20px}.comic-empty{text-align:center;padding:130px 24px;color:#82786c}
    #comic-zoom{border:0;border-radius:24px;padding:20px;background:#fffaf1;width:min(850px,90vw);max-height:92vh}#comic-zoom::backdrop{background:#19130fbb}#comic-zoom img{display:block;max-height:75vh;width:100%;object-fit:contain}#comic-close{float:right}#comic-zoom p{text-align:center;color:#574b3c}
    @media(max-width:800px){.nav{display:flex!important;overflow-x:auto;width:100%;order:5}.topbar{flex-wrap:wrap;height:auto;min-height:90px;padding:12px 0}.nav button{white-space:nowrap}.comic-card{width:244px;margin-left:-122px;height:342px}.comic-card img,.comic-card .comic-placeholder{height:240px}#comic-stage{height:410px}.comic-heading{padding-top:30px}}
    @media(prefers-reduced-motion:reduce){.comic-card{transition:none}}`;
  document.head.appendChild(style);
  const el = id => document.getElementById(id);
  let cards = [], selected = 0, fetching = false, lastSignature = '';
  const labels = {queued:'等待绘制',running:'正在绘制…',ready:'已完成',failed:'绘制失败',unconfigured:'请配置绘图 Key'};
  const active = () => el('comics').classList.contains('active');
  const key = card => `${card.id}:${card.index}`;

  function position() {
    [...el('comic-stage').querySelectorAll('.comic-card')].forEach((node,i) => {
      const distance = i - selected;
      const step = window.innerWidth < 650 ? 118 : 177;
      node.style.transform = `translateX(${distance * step}px) translateZ(${-Math.abs(distance)*105}px) rotateY(${distance === 0 ? 0 : distance > 0 ? -13 : 13}deg) scale(${distance === 0 ? 1 : .94})`;
      node.style.zIndex = String(30 - Math.abs(distance));
      node.style.opacity = Math.abs(distance) > 3 ? '0' : '1';
      node.style.pointerEvents = Math.abs(distance) > 3 ? 'none' : 'auto';
      node.tabIndex = Math.abs(distance) > 3 ? -1 : 0;
      node.setAttribute('aria-pressed', String(distance === 0));
    });
    el('comic-position').textContent = cards.length ? `${selected+1} / ${cards.length}` : '0 / 0';
    el('comic-prev').disabled = selected <= 0;
    el('comic-next').disabled = selected >= cards.length-1;
    const card = cards[selected];
    el('comic-status').textContent = card?.error || (cards.length ? `已完成 ${cards.filter(x=>x.url).length} / ${cards.length} 张 · 正在绘制 ${cards.filter(x=>x.status==='running').length} 张 · 等待 ${cards.filter(x=>x.status==='queued').length} 张` : '还没有事件，请先新增记录。');
  }
  function cardTime(card) {
    const raw = String(card.time || '').trim();
    const base = new Date(card.created_at || Date.now());
    const date = new Date(base);
    const relative = raw;
    const explicit = relative.match(/(20\d{2})[年\/-](\d{1,2})[月\/-](\d{1,2})/);
    if (/明天/.test(relative)) date.setDate(date.getDate() + 1);
    else if (/后天/.test(relative)) date.setDate(date.getDate() + 2);
    if (explicit) date.setFullYear(+explicit[1], +explicit[2] - 1, +explicit[3]);
    const timeMatch = relative.match(/(上午|下午|晚上|早上)?\s*([0-9]{1,2})\s*(?:点(?:([0-9]{1,2})分?)?|:([0-9]{2}))/);
    if (timeMatch) {
      let hour = +timeMatch[2];
      if ((timeMatch[1] === '下午' || timeMatch[1] === '晚上') && hour < 12) hour += 12;
      date.setHours(hour, +(timeMatch[3] || timeMatch[4] || 0), 0, 0);
    } else if (!raw || /日常的一刻/.test(raw)) {
      if (!card.created_at) return '时间待定';
      if (Number.isNaN(date.getTime())) return '时间待定';
    } else {
      return raw;
    }
    if (Number.isNaN(date.getTime())) return '时间待定';
    const pad = value => String(value).padStart(2, '0');
    return `${date.getFullYear()}年${pad(date.getMonth()+1)}月${pad(date.getDate())}日 ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }
  function render() {
    el('comic-stage').innerHTML = cards.length ? cards.map((card,i) => `<button class="comic-card" data-card="${i}" aria-label="${escapeHtml(card.title)}">
      ${card.url ? `<img src="${escapeHtml(card.url)}" alt="小熊日常手绘插画" draggable="false">` : `<div class="comic-placeholder">🐻<small>${labels[card.status] || '等待绘制'}</small></div>`}
      <div class="comic-caption"><b>${escapeHtml(card.title)}</b><time>${escapeHtml(cardTime(card))}</time></div></button>`).join('') : '<p class="comic-empty">你的第一张小熊日记，从一件小事开始。</p>';
    position();
  }
  async function sync() {
    if (!active() || fetching) return;
    fetching = true;
    try {
      const response = await fetch('/illustrations/gallery/sync', {method:'POST'});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || '读取漫画失败，请重启后端');
      const signature = JSON.stringify(data.items);
      if (signature !== lastSignature) {
        const old = cards[selected] && key(cards[selected]);
        cards = data.items; selected = Math.max(0, cards.findIndex(card=>key(card) === old));
        lastSignature = signature; render();
      } else position();
    } catch(error) { el('comic-status').textContent = error.message; }
    finally { fetching = false; }
  }
  nav.querySelector('[data-view="comics"]').onclick = () => { show('comics'); render(); sync(); };
  function move(delta) { selected = Math.max(0, Math.min(cards.length-1, selected+delta)); position(); }
  el('comic-prev').onclick = () => move(-1); el('comic-next').onclick = () => move(1);
  el('comic-stage').onkeydown = event => { if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {event.preventDefault();move(event.key === 'ArrowLeft' ? -1 : 1);} };
  let startX = 0, swiped = false;
  el('comic-stage').addEventListener('pointerdown', event => { startX = event.clientX; swiped = false; });
  el('comic-stage').addEventListener('pointerup', event => { const delta = event.clientX-startX; if(Math.abs(delta)>45){swiped=true;move(delta>0?-1:1);} });
  el('comic-stage').onclick = event => {
    if (swiped) {swiped=false;return;}
    const card = event.target.closest('[data-card]'); if (!card) return;
    const index = Number(card.dataset.card);
    if (selected !== index) {selected=index;position();return;}
    if (!cards[index].url) return;
    el('comic-zoom').querySelector('img').src = cards[index].url;
    el('comic-zoom').querySelector('p').textContent = cards[index].title;
    el('comic-zoom').showModal();
  };
  el('comic-close').onclick = () => el('comic-zoom').close();
  window.addEventListener('resize', position);
  setInterval(()=>{if(!document.hidden)sync();},4000);
})();
