import { readFile, writeFile } from 'node:fs/promises';
const p = new URL('../web/index.html', import.meta.url);
let s = await readFile(p, 'utf8');
s = s.replace('<title>拾光 · PocketMemory-AI</title>', '<title>MemoDot · 一颗小点，收住一个念头</title><meta name="description" content="MemoDot 是你的随身记忆盒子：说一句、写一段，让每个灵感都有一个安静的落点。">');
s = s.replace('<div class="mark">✦</div><b>拾光</b>', '<div class="mark">·</div><b>MemoDot</b>');
s = s.replace('<section class="hero"><div><small>SHIGUANG · PERSONAL SPACE</small><h1>把每个想法，放到合适的时间里。</h1><p>语音记录、提取重点、安排提醒。今天也给自己一点从容。</p></div><div class="hero-clock">', '<section class="memodot-hero" id="memodot-hero"><div class="memodot-intro"><small>PERSONAL MEMORY · VOL. 001</small><h1 class="memodot-title" aria-label="MemoDot"></h1><p>一颗小点，收住一个念头。<br>把今天的声音、文字和心情，留在身边。</p><div class="memodot-controls"><button id="memodot-replay" class="hero-control">重播开场</button><button id="memodot-pause" class="hero-control" aria-pressed="false">暂停动画</button><span>悬停或触摸字母，看看另一种形状</span></div></div><div class="hero-clock">');
await writeFile(p, s);
