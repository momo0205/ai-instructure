"""生成自包含的论文精读工作台 index.html。

读取磁盘上的实际 questions / papers / checkpoints / code 文件，
内嵌为 JSON 数据，产出单个可直接双击打开的 HTML（进度与笔记存 localStorage）。

Run:  python3 build_dashboard.py
输出: index.html（与本脚本同目录）
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def read(rel):
    with open(os.path.join(BASE, rel), "r", encoding="utf-8") as f:
        return f.read()


PAPERS = [
    {
        "id": "resnet",
        "name": "ResNet",
        "title": "Deep Residual Learning for Image Recognition",
        "meta": "He et al. · 2015 · CVPR 2016",
        "qnum": "Q1",
        "pdf": "papers/resnet/resnet.pdf",
        "question": read("questions/q1-why-deep-networks-fail.md"),
        "notes": read("papers/resnet/notes.md"),
        "summary": read("papers/resnet/summary.md"),
        "checkpoint": read("checkpoints/checkpoint-1-resnet.md"),
        "code": read("code/resnet/plain_vs_residual.py"),
        "code_file": "code/resnet/plain_vs_residual.py",
        "run_cmd": "python3 resnet/plain_vs_residual.py",
        "code_lang": "python",
        "result": "梯度比 residual/plain = 1.79e+11：plain 浅层梯度趋近 0，残差连接保住梯度通路。",
    },
    {
        "id": "transformer",
        "name": "Transformer",
        "title": "Attention Is All You Need",
        "meta": "Vaswani et al. · 2017 · NeurIPS",
        "qnum": "Q2",
        "pdf": "papers/transformer/attention_is_all_you_need.pdf",
        "question": read("questions/q2-why-attention-works.md"),
        "notes": read("papers/transformer/notes.md"),
        "summary": read("papers/transformer/summary.md"),
        "checkpoint": read("checkpoints/checkpoint-2-transformer.md"),
        "code": read("code/transformer/tiny_attention.py"),
        "code_file": "code/transformer/tiny_attention.py",
        "run_cmd": "python3 transformer/tiny_attention.py",
        "code_lang": "python",
        "result": "loss 2.48 → 1.99；注意力矩阵上三角全 0（因果掩码生效）。",
    },
    {
        "id": "ddpm",
        "name": "DDPM",
        "title": "Denoising Diffusion Probabilistic Models",
        "meta": "Ho, Jain, Abbeel · 2020 · NeurIPS",
        "qnum": "Q3",
        "pdf": "papers/ddpm/ddpm.pdf",
        "question": read("questions/q3-why-diffusion-generates.md"),
        "notes": read("papers/ddpm/notes.md"),
        "summary": read("papers/ddpm/summary.md"),
        "checkpoint": read("checkpoints/checkpoint-3-ddpm.md"),
        "code": read("code/ddpm/simple_ddpm.py"),
        "code_file": "code/ddpm/simple_ddpm.py",
        "run_cmd": "python3 ddpm/simple_ddpm.py",
        "code_lang": "python",
        "result": "mse 0.095 → 0.056；从纯噪声生成出数字形态。",
    },
]

DATA_JSON = json.dumps(PAPERS, ensure_ascii=False)

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>论文精读工作台 · ResNet / Transformer / DDPM</title>
<style>
:root{
  --bg:#f6f7f9; --card:#ffffff; --ink:#1c2430; --muted:#5b6572;
  --line:#e3e7ec; --accent:#2563eb; --accent-soft:#e8effd; --ok:#16a34a;
  --code-bg:#0f172a; --code-ink:#e2e8f0; --radius:12px; --shadow:0 1px 3px rgba(16,24,40,.06),0 4px 16px rgba(16,24,40,.06);
}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);line-height:1.65}
a{color:var(--accent);text-decoration:none}
.wrap{max-width:1080px;margin:0 auto;padding:24px 20px 80px}
header.top{position:sticky;top:0;background:rgba(246,247,249,.9);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);z-index:20}
.top-inner{max-width:1080px;margin:0 auto;padding:14px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.brand{font-weight:700;font-size:15px;letter-spacing:.2px}
.brand small{display:block;font-weight:400;color:var(--muted);font-size:11px}
.progress{flex:1;min-width:220px}
.progress .bar{height:8px;background:var(--line);border-radius:99px;overflow:hidden}
.progress .bar>i{display:block;height:100%;width:0;background:linear-gradient(90deg,#2563eb,#4f8dfd);transition:width .35s ease}
.progress .pct{font-size:12px;color:var(--muted);margin-top:4px}
.tabs{display:flex;gap:6px;max-width:1080px;margin:16px auto 0;padding:0 20px}
.tab{flex:1;text-align:center;padding:10px 12px;border:1px solid var(--line);background:var(--card);border-radius:10px 10px 0 0;border-bottom:none;cursor:pointer;font-weight:600;font-size:14px;color:var(--muted);transition:.15s}
.tab .qn{font-size:11px;font-weight:600;color:var(--accent);display:block}
.tab.active{color:var(--ink);background:var(--card);box-shadow:var(--shadow);position:relative;top:1px}
.tab .done{font-size:11px;color:var(--ok);font-weight:600}
.pane{display:none}
.pane.active{display:block}
.hero{background:var(--card);border:1px solid var(--line);border-radius:0 var(--radius) var(--radius) var(--radius);padding:22px 24px;box-shadow:var(--shadow)}
.hero h1{margin:0 0 4px;font-size:22px}
.hero .meta{color:var(--muted);font-size:13px;margin-bottom:14px}
.hero .actions{display:flex;gap:10px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:9px;border:1px solid var(--line);background:#fff;font-size:13px;font-weight:600;cursor:pointer;transition:.15s;color:var(--ink)}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{background:#1d4fd0}
.btn.ghost{background:transparent}
.sec{margin-top:26px}
.sec>h2{display:flex;align-items:center;gap:10px;font-size:16px;margin:0 0 12px}
.sec>h2 .tag{font-size:11px;font-weight:600;color:var(--accent);background:var(--accent-soft);padding:2px 8px;border-radius:99px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;box-shadow:var(--shadow)}
.md h1,.md h2,.md h3{line-height:1.35;margin:.9em 0 .4em}
.md h1{font-size:19px}.md h2{font-size:16px}.md h3{font-size:14.5px}
.md p{margin:.5em 0}
.md code{background:#eef2f6;padding:1px 5px;border-radius:5px;font-size:.88em;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.md pre{background:var(--code-bg);color:var(--code-ink);padding:14px 16px;border-radius:10px;overflow:auto;font-size:12.5px}
.md pre code{background:transparent;color:inherit;padding:0}
.md table{border-collapse:collapse;width:100%;font-size:13.5px;margin:.6em 0}
.md th,.md td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
.md th{background:#f2f5f8;font-weight:600}
.md blockquote{border-left:3px solid var(--accent);margin:.6em 0;padding:2px 14px;color:var(--muted);background:var(--accent-soft);border-radius:0 8px 8px 0}
.md ul,.md ol{padding-left:22px}
.md details{border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:6px 0;background:#fbfcfd}
.md details summary{cursor:pointer;font-weight:600;color:var(--accent)}
.md details[open]{background:var(--accent-soft);border-color:#c9dbfb}
textarea.note{width:100%;min-height:150px;border:1px solid var(--line);border-radius:10px;padding:12px 14px;font:inherit;font-size:13.5px;resize:vertical;background:#fbfcfd}
textarea.note:focus{outline:2px solid var(--accent-soft);border-color:var(--accent)}
.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:10px;flex-wrap:wrap}
.save-hint{font-size:12px;color:var(--muted)}
.save-hint.saved{color:var(--ok)}
.code-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:8px}
.code-file{font-family:ui-monospace,monospace;font-size:12px;color:var(--muted)}
.cmdline{display:flex;align-items:center;gap:8px;background:#0b1220;border-radius:8px;padding:8px 12px;margin:10px 0}
.cmdline code{flex:1;color:#7dd3fc;font-family:ui-monospace,monospace;font-size:13px;overflow:auto;white-space:nowrap}
.copy{font-size:12px;padding:4px 10px;border-radius:6px;border:1px solid #243447;background:#16233a;color:#cfe4ff;cursor:pointer}
.copy:hover{background:#1d3350}
.copy.copied{background:var(--ok);border-color:var(--ok);color:#fff}
pre.codeblock{background:var(--code-bg);color:var(--code-ink);padding:16px 18px;border-radius:10px;overflow:auto;font-size:12.5px;max-height:480px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}{background:var(--code-bg);color:var(--code-ink);padding:16px 18px;border-radius:10px;overflow:auto;font-size:12.5px;max-height:480px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.result-banner{margin-top:10px;font-size:13px;background:#f0fdf4;border:1px solid #bbf7d0;color:#166534;padding:10px 14px;border-radius:9px}
.quiz-item{border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:10px 0;background:var(--card)}
.quiz-item .qrow{display:flex;gap:10px;align-items:flex-start}
.quiz-item input[type=checkbox]{margin-top:5px;transform:scale(1.15);accent-color:var(--ok);cursor:pointer}
.quiz-item.done .qtext{color:var(--muted);text-decoration:line-through}
.quiz-q{font-weight:600;font-size:14px;flex:1}
.checks{display:flex;gap:18px;flex-wrap:wrap}
.checks label{display:flex;gap:8px;align-items:center;font-size:13.5px;cursor:pointer;padding:8px 12px;border:1px solid var(--line);border-radius:9px;background:#fff}
.checks input{accent-color:var(--ok);transform:scale(1.15)}
footer{margin-top:40px;text-align:center;color:var(--muted);font-size:12px}
.reset{font-size:12px;color:var(--muted);background:none;border:none;cursor:pointer;text-decoration:underline}
.paper-badge{display:inline-block;background:var(--accent-soft);color:var(--accent);font-size:11px;font-weight:700;padding:2px 9px;border-radius:99px;margin-right:8px}
@media(max-width:640px){.tabs{flex-direction:column}.hero h1{font-size:19px}}
</style>
</head>
<body>
<header class="top">
  <div class="top-inner">
    <div class="brand">论文精读工作台<small>问题驱动 · 最小复现 · 本地保存</small></div>
    <div class="progress">
      <div class="bar"><i id="gbar"></i></div>
      <div class="pct" id="gpct">整体进度 0%</div>
    </div>
    <button class="reset" id="resetAll">清空进度</button>
  </div>
  <nav class="tabs" id="tabs"></nav>
</header>
<main class="wrap" id="panes"></main>
<footer>论文原文请点 Tab 顶部「打开 PDF」调用系统阅读器 · 进度与笔记保存在本浏览器 localStorage</footer>

<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const LS = 'paperDeepDive.v1';
let state = {};
try { state = JSON.parse(localStorage.getItem(LS) || '{}'); } catch(e){ state = {}; }
function save(){ localStorage.setItem(LS, JSON.stringify(state)); }
function get(k, d){ return (k in state) ? state[k] : d; }
function set(k, v){ state[k] = v; save(); renderProgress(); }

// 内置轻量 markdown 解析（离线可用，无外部依赖）
function escHtml(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function inline(s){
  s = escHtml(s);
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return s;
}
function md(src){
  if(!src) return '';
  const lines = src.split('\\n');
  let html='', i=0;
  while(i<lines.length){
    const line=lines[i];
    if(/^```/.test(line)){ let buf=[]; i++; while(i<lines.length && !/^```/.test(lines[i])){buf.push(lines[i]);i++;} i++; html+='<pre><code>'+escHtml(buf.join('\\n'))+'</code></pre>'; continue; }
    if(/^# /.test(line)){ html+='<h1>'+inline(line.slice(2))+'</h1>'; i++; continue; }
    if(/^## /.test(line)){ html+='<h2>'+inline(line.slice(3))+'</h2>'; i++; continue; }
    if(/^### /.test(line)){ html+='<h3>'+inline(line.slice(4))+'</h3>'; i++; continue; }
    if(/^> ?/.test(line)){ html+='<blockquote>'+inline(line.replace(/^> ?/,''))+'</blockquote>'; i++; continue; }
    if(/^<details/.test(line)){ let buf=[line]; i++; while(i<lines.length && !/<\/details>/.test(lines[i])){buf.push(lines[i]);i++;} if(i<lines.length)buf.push(lines[i]); i++;
      let inner=buf.join('\\n'); inner=inner.replace(/<details><summary>(.*?)<\/summary>/s,'<details><summary>'+inline('$1')+'</summary>');
      inner=inner.replace(/<\/summary>([\s\S]*)<\/details>/, (m,g)=>'</summary><div>'+inline(g.trim())+'</div></details>');
      html+=inner; continue; }
    if(/^\|/.test(line)){ let rows=[]; while(i<lines.length && /^\|/.test(lines[i])){rows.push(lines[i]);i++;}
      if(rows.length>=2){ let head=rows[0].split('|').slice(1,-1).map(c=>c.trim()); let body=rows.slice(2);
        html+='<table><thead><tr>'+head.map(c=>'<th>'+inline(c)+'</th>').join('')+'</tr></thead><tbody>'
          +body.map(r=>'<tr>'+r.split('|').slice(1,-1).map(c=>'<td>'+inline(c.trim())+'</td>').join('')+'</tr>').join('')+'</tbody></table>'; }
      continue; }
    if(/^\d+\. /.test(line)){ let items=[]; while(i<lines.length && /^\d+\. /.test(lines[i])){items.push(lines[i].replace(/^\d+\. /,''));i++;} html+='<ol>'+items.map(x=>'<li>'+inline(x)+'</li>').join('')+'</ol>'; continue; }
    if(/^[-*] /.test(line)){ let items=[]; while(i<lines.length && /^[-*] /.test(lines[i])){items.push(lines[i].replace(/^[-*] /,''));i++;} html+='<ul>'+items.map(x=>'<li>'+inline(x)+'</li>').join('')+'</ul>'; continue; }
    if(line.trim()===''){ i++; continue; }
    html+='<p>'+inline(line)+'</p>'; i++;
  }
  return html;
}

function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;'); }

function renderTabs(){
  const nav = document.getElementById('tabs');
  nav.innerHTML = DATA.map((p,i)=>{
    const done = paperPct(p.id)===100 ? '<span class="done">✓ 已完成</span>' : '';
    return '<div class="tab'+(i===0?' active':'')+'" data-p="'+p.id+'"><span class="qn">'+p.qnum+'</span>'+p.name+' '+done+'</div>';
  }).join('');
  nav.querySelectorAll('.tab').forEach(t=>t.onclick=()=>selectPane(t.dataset.p));
}

function sectionChecklist(p){
  const items=[['q','已读核心问题并写下初始理解'],['read','已速读 Abstract/Intro/Conclusion'],['derive','已推导核心公式（有手写存档）'],['code','已跑通最小复现并改过参数'],['quiz','自测 ≥ 8/10'],['sum','已写一页纸总结']];
  return '<div class="checks">'+items.map(it=>{
    const k=p.id+'.ck.'+it[0];
    const on=get(k,false)?' checked':'';
    return '<label><input type="checkbox" data-k="'+k+'"'+on+'><span>'+it[1]+'</span></label>';
  }).join('')+'</div>';
}

function quizBlock(p){
  const raw = p.checkpoint;
  const parts = raw.split(/^## /m).slice(1);
  const items = parts.map(part=>{
    const nl = part.indexOf('\\n');
    const q = part.slice(0,nl).trim();
    const body = part.slice(nl+1).trim();
    return {q, body};
  });
  return items.map((it,idx)=>{
    const k = p.id+'.quiz.'+idx;
    const on = get(k,false);
    return '<div class="quiz-item'+(on?' done':'')+'"><div class="qrow">'
      +'<input type="checkbox" data-k="'+k+'"'+(on?' checked':'')+'>'
      +'<div style="flex:1"><div class="quiz-q qtext">'+esc(it.q)+'</div>'
      +'<div class="md">'+md(it.body)+'</div></div></div></div>';
  }).join('');
}

function renderPanes(){
  const main=document.getElementById('panes');
  main.innerHTML = DATA.map((p,i)=>{
    const noteKey=p.id+'.note', sumKey=p.id+'.summary';
    const note=get(noteKey,''), sum=get(sumKey,'');
    return '<section class="pane'+(i===0?' active':'')+'" id="pane-'+p.id+'">'
    +'<div class="hero">'
    +'<span class="paper-badge">'+p.qnum+'</span><h1 style="display:inline">'+esc(p.name)+'</h1>'
    +'<div class="meta">'+esc(p.title)+' · '+esc(p.meta)+'</div>'
    +'<div class="actions">'
    +'<a class="btn primary" href="'+p.pdf+'" target="_blank" rel="noopener">打开论文 PDF</a>'
    +'<span style="font-size:12px;color:var(--muted);align-self:center">已在系统阅读器打开 · 笔记区在下方</span>'
    +'</div></div>'

    +'<div class="sec"><h2>学习进度自检</h2><div class="card">'+sectionChecklist(p)+'</div></div>'

    +'<div class="sec"><h2>核心问题 <span class="tag">'+p.qnum+'</span></h2><div class="card md">'+md(p.question)+'</div></div>'

    +'<div class="sec"><h2>精读笔记模板</h2><div class="card md">'+md(p.notes)+'</div>'
    +'<div class="card" style="margin-top:12px"><div class="toolbar"><strong style="font-size:14px">我的精读笔记</strong><span class="save-hint" id="hint-'+p.id+'-note">自动保存</span></div>'
    +'<textarea class="note" data-k="'+noteKey+'" data-hint="hint-'+p.id+'-note" placeholder="在这里写你的精读笔记、公式推导理解、困惑点……">'+esc(note)+'</textarea></div></div>'

    +'<div class="sec"><h2>最小复现</h2><div class="card">'
    +'<div class="code-head"><span class="code-file">'+p.code_file+'</span></div>'
    +'<div class="cmdline"><code>$ '+p.run_cmd+'</code><button class="copy" data-cmd="'+p.run_cmd+'">复制命令</button></div>'
    +'<pre class="codeblock"><code>'+esc(p.code)+'</code></pre>'
    +'<div class="result-banner">预期结果：'+esc(p.result)+'</div>'
    +'</div></div>'

    +'<div class="sec"><h2>自测题（勾选表示已掌握）</h2>'+quizBlock(p)+'</div>'

    +'<div class="sec"><h2>一页纸总结</h2><div class="card md" style="margin-bottom:12px">'+md(p.summary)+'</div>'
    +'<div class="card"><div class="toolbar"><strong style="font-size:14px">我的一页纸总结</strong><span class="save-hint" id="hint-'+p.id+'-sum">自动保存</span></div>'
    +'<textarea class="note" data-k="'+sumKey+'" data-hint="hint-'+p.id+'-sum" placeholder="用自己的话写一页纸总结……">'+esc(sum)+'</textarea></div></div>'

    +'</section>';
  }).join('');

  main.querySelectorAll('textarea.note').forEach(t=>{
    t.addEventListener('input', ()=>{
      set(t.dataset.k, t.value);
      const h=document.getElementById(t.dataset.hint);
      if(h){h.textContent='已保存';h.classList.add('saved');}
    });
  });
  main.querySelectorAll('input[type=checkbox]').forEach(c=>{
    c.addEventListener('change', ()=>{ set(c.dataset.k, c.checked); });
  });
  main.querySelectorAll('.copy').forEach(b=>{
    b.addEventListener('click', ()=>{
      navigator.clipboard.writeText(b.dataset.cmd).then(()=>{
        b.textContent='已复制';b.classList.add('copied');
        setTimeout(()=>{b.textContent='复制命令';b.classList.remove('copied');},1500);
      });
    });
  });
}

function paperPct(id){
  const cks=['q','read','derive','code','quiz','sum'].map(s=>id+'.ck.'+s);
  const ckDone=cks.filter(k=>get(k,false)).length;
  const quizN=10, quizDone=Array.from({length:quizN},(_,i)=>get(id+'.quiz.'+i,false)).filter(Boolean).length;
  const note=get(id+'.note','').trim().length>0?1:0;
  const sum=get(id+'.summary','').trim().length>0?1:0;
  const total=cks.length+quizN+2, done=ckDone+quizDone+note+sum;
  return Math.round(done/total*100);
}
function renderProgress(){
  const pcts=DATA.map(p=>paperPct(p.id));
  const g=Math.round(pcts.reduce((a,b)=>a+b,0)/pcts.length);
  document.getElementById('gbar').style.width=g+'%';
  document.getElementById('gpct').textContent='整体进度 '+g+'%';
  renderTabsOnly();
}
function renderTabsOnly(){
  document.querySelectorAll('#tabs .tab').forEach((t,i)=>{
    const p=DATA[i], done=paperPct(p.id)===100;
    const d=t.querySelector('.done');
    if(done && !d){ t.innerHTML='<span class="qn">'+p.qnum+'</span>'+p.name+' <span class="done">✓ 已完成</span>'; }
    if(!done && d){ d.remove(); }
  });
}
function selectPane(id){
  document.querySelectorAll('#tabs .tab').forEach(t=>t.classList.toggle('active',t.dataset.p===id));
  document.querySelectorAll('.pane').forEach(pn=>pn.classList.toggle('active',pn.id==='pane-'+id));
  window.scrollTo({top:0,behavior:'smooth'});
}
document.getElementById('resetAll').onclick=()=>{
  if(confirm('确定清空所有进度、勾选和笔记？此操作不可恢复。')){ state={}; save(); renderPanes(); renderProgress(); }
};

renderTabs(); renderPanes(); renderProgress();
</script>
</body>
</html>
"""


def main():
    html = HTML.replace("__DATA__", DATA_JSON)
    out = os.path.join(BASE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成: {out}  ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
