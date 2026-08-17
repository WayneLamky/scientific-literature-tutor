#!/usr/bin/env python3
"""Build a self-contained interactive paper reader from a JSON specification."""

from __future__ import annotations

import base64
import html
import json
import mimetypes
import sys
from pathlib import Path


TUTOR_CSS = r"""
body.tutor-open{overflow:hidden}.tutor-toggle{display:inline-flex;align-items:center;gap:7px;background:var(--green)!important;color:white!important;border-color:transparent!important}.tutor-toggle .spark{color:var(--lime)}
.ask-figure{margin:0 0 24px;border:1px solid var(--green);background:var(--card);color:var(--green);border-radius:999px;padding:9px 14px;font-weight:800;cursor:pointer}.ask-figure:hover,.ask-term:hover{background:color-mix(in srgb,var(--lime) 24%,var(--card))}
.term.ask-term{font:inherit;color:var(--ink);cursor:pointer}.selection-ask{display:none;position:fixed;z-index:79;border:0;border-radius:999px;background:var(--green);color:white;padding:8px 13px;box-shadow:var(--shadow);cursor:pointer;font-weight:800}.selection-ask.show{display:block}
.tutor-scrim{position:fixed;z-index:69;inset:0;background:rgba(7,20,16,.34);opacity:0;pointer-events:none;transition:.25s}.tutor-scrim.open{opacity:1;pointer-events:auto}
.tutor-panel{position:fixed;z-index:70;top:0;right:0;width:min(440px,100vw);height:100dvh;background:var(--card);border-left:1px solid var(--line);box-shadow:-18px 0 60px rgba(10,35,28,.18);transform:translateX(105%);transition:transform .28s ease;display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;color:var(--ink)}.tutor-panel.open{transform:none}
.tutor-head{display:flex;align-items:center;gap:12px;padding:18px;border-bottom:1px solid var(--line)}.tutor-head .avatar{display:grid;place-items:center;width:40px;height:40px;border-radius:13px;background:var(--green);color:var(--lime);font-weight:900}.tutor-head h2{font:800 1rem/1.25 system-ui,sans-serif;margin:0}.tutor-head p{font-size:.78rem;color:var(--muted);margin:3px 0 0}.tutor-head button{margin-left:auto;border:0;background:transparent;color:var(--muted);font-size:1.3rem;cursor:pointer;padding:8px}
.tutor-context{padding:10px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:8px;color:var(--muted);font-size:.78rem}.tutor-context b{color:var(--green);white-space:nowrap}.tutor-context span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tutor-messages{overflow:auto;padding:18px;display:flex;flex-direction:column;gap:12px}.tutor-message{max-width:92%;padding:11px 13px;border-radius:15px;white-space:pre-wrap;overflow-wrap:anywhere}.tutor-message.user{align-self:flex-end;background:var(--green);color:white;border-bottom-right-radius:5px}.tutor-message.assistant{align-self:flex-start;background:var(--paper);border:1px solid var(--line);border-bottom-left-radius:5px}.tutor-message.system{align-self:stretch;max-width:none;background:color-mix(in srgb,var(--lime) 16%,var(--card));border:1px solid color-mix(in srgb,var(--green) 25%,var(--line));font-size:.86rem}.tutor-message.error{align-self:stretch;max-width:none;background:color-mix(in srgb,var(--red) 10%,var(--card));border:1px solid color-mix(in srgb,var(--red) 45%,var(--line));color:var(--red)}.typing::after{content:'\2026';animation:blink 1s infinite}@keyframes blink{50%{opacity:.25}}
.tutor-starters{display:flex;flex-wrap:wrap;gap:7px;margin-top:4px}.tutor-starters button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:7px 10px;font-size:.78rem;cursor:pointer}
.obsidian-state{display:inline-flex;align-items:center;gap:5px}.obsidian-state::before{content:'';width:7px;height:7px;border-radius:50%;background:var(--muted)}.obsidian-state.ready::before{background:#6fa75e}.obsidian-state.error::before{background:var(--red)}
.tutor-save-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:11px;padding-top:9px;border-top:1px solid var(--line);white-space:normal}.tutor-save-actions button,.tutor-save-actions a{border:1px solid var(--line);background:var(--card);color:var(--green);border-radius:999px;padding:6px 9px;font:700 .72rem/1 system-ui,sans-serif;cursor:pointer;text-decoration:none}.tutor-save-actions button:hover,.tutor-save-actions a:hover{border-color:var(--green)}.tutor-save-actions button:disabled{opacity:.5;cursor:wait}.save-result{flex-basis:100%;font-size:.72rem;color:var(--muted);line-height:1.35}.save-result.error{color:var(--red)}
.save-composer{display:none;flex-basis:100%;padding:9px;background:var(--card);border:1px solid var(--line);border-radius:11px}.save-composer.open{display:block}.save-composer textarea,.save-composer input{width:100%;box-sizing:border-box;border:1px solid var(--line);border-radius:9px;background:var(--paper);color:var(--ink);font:inherit;padding:8px;white-space:normal}.save-composer textarea{min-height:62px;resize:vertical}.save-composer input{margin-top:6px}.save-composer-row{display:flex;justify-content:flex-end;gap:6px;margin-top:7px}
.tutor-compose{padding:12px 14px 16px;border-top:1px solid var(--line);background:var(--card)}.tutor-compose textarea{display:block;width:100%;min-height:76px;max-height:180px;resize:vertical;border:1px solid var(--line);border-radius:14px;padding:11px 12px;background:var(--paper);color:var(--ink);font:inherit;line-height:1.45}.tutor-compose textarea:focus{outline:2px solid color-mix(in srgb,var(--green) 38%,transparent);border-color:var(--green)}.tutor-actions{display:flex;align-items:center;gap:8px;margin-top:9px}.tutor-actions small{color:var(--muted);font-size:.72rem}.tutor-send{margin-left:auto;border:0;border-radius:999px;background:var(--green);color:white;padding:8px 15px;font-weight:800;cursor:pointer}.tutor-send:disabled{opacity:.45;cursor:wait}.tutor-clear{border:0;background:transparent;color:var(--muted);cursor:pointer}
@media(min-width:900px){body.tutor-open{overflow:auto}.tutor-scrim{display:none}}
@media(max-width:650px){.topbar{max-width:calc(100vw - 24px);flex-wrap:wrap;justify-content:flex-end}.tutor-toggle .label{display:none}}
@media print{.tutor-panel,.tutor-scrim,.selection-ask,.tutor-toggle,.ask-figure{display:none!important}}
"""


TUTOR_JS = r"""
const CHAT_ENDPOINT=(location.protocol==='file:'?'http://127.0.0.1:8765/api/chat':'/api/chat');
const OBSIDIAN_STATUS_ENDPOINT=(location.protocol==='file:'?'http://127.0.0.1:8765/api/obsidian/status':'/api/obsidian/status');
const OBSIDIAN_SAVE_ENDPOINT=(location.protocol==='file:'?'http://127.0.0.1:8765/api/obsidian/save':'/api/obsidian/save');
const tutorPanel=document.querySelector('#tutor-panel');
const tutorScrim=document.querySelector('#tutor-scrim');
const tutorMessages=document.querySelector('#tutor-messages');
const tutorInput=document.querySelector('#tutor-input');
const tutorSend=document.querySelector('#tutor-send');
const tutorContextLabel=document.querySelector('#tutor-context-label');
const selectionAsk=document.querySelector('#selection-ask');
const obsidianState=document.querySelector('#obsidian-state');
let tutorHistory=[];
let tutorBusy=false;
let selectedText='';
let activeSectionId='logic';

function contextFor(sectionId){
  if(sectionId.startsWith('fig-')){
    const index=Number(sectionId.slice(4))-1;
    const figure=PAPER_CONTEXT.figures[index];
    if(figure)return {kind:'figure',label:figure.number+' · '+figure.title_zh,content:figure};
  }
  if(sectionId==='validation')return {kind:'validation',label:'验证强度审计',content:PAPER_CONTEXT.validation};
  if(sectionId==='closing')return {kind:'synthesis',label:'总结与术语表',content:{takeaways:PAPER_CONTEXT.takeaways,glossary:PAPER_CONTEXT.glossary}};
  return {kind:'paper-logic',label:'整篇论文逻辑链',content:{thesis:PAPER_CONTEXT.thesis,logic_chain:PAPER_CONTEXT.logic_chain,sample_audit:PAPER_CONTEXT.sample_audit}};
}

function updateTutorContext(){
  const ctx=contextFor(activeSectionId);
  tutorContextLabel.textContent=selectedText?ctx.label+' · 已选中文字':ctx.label;
}

function openTutor(prefill=''){
  tutorPanel.classList.add('open');tutorScrim.classList.add('open');document.body.classList.add('tutor-open');
  tutorPanel.setAttribute('aria-hidden','false');updateTutorContext();
  if(prefill)tutorInput.value=prefill;
  setTimeout(()=>tutorInput.focus(),180);
}

function closeTutor(){
  tutorPanel.classList.remove('open');tutorScrim.classList.remove('open');document.body.classList.remove('tutor-open');
  tutorPanel.setAttribute('aria-hidden','true');
}

function addTutorMessage(role,text,extra=''){
  const message=document.createElement('div');
  message.className='tutor-message '+role+(extra?' '+extra:'');
  message.textContent=text;
  tutorMessages.appendChild(message);tutorMessages.scrollTop=tutorMessages.scrollHeight;
  return message;
}

async function refreshObsidianStatus(){
  try{
    const response=await fetch(OBSIDIAN_STATUS_ENDPOINT);const payload=await response.json();
    if(!response.ok||!payload.configured)throw new Error(payload.error||'未配置');
    obsidianState.textContent='Obsidian · '+payload.vaultName;obsidianState.className='obsidian-state ready';
  }catch(_error){obsidianState.textContent='Obsidian 未连接';obsidianState.className='obsidian-state error'}
}

async function saveToObsidian(capture,userNote,tags,button,result){
  button.disabled=true;result.className='save-result';result.textContent='正在写入 Obsidian…';
  try{
    const response=await fetch(OBSIDIAN_SAVE_ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paper:capture.paper,context:capture.context,selection:capture.selection,question:capture.question,answer:capture.answer,userNote,tags})});
    const payload=await response.json().catch(()=>({}));if(!response.ok)throw new Error(payload.error||'保存失败');
    result.textContent=payload.duplicate?'这条内容已经在 Obsidian 中':'已保存到 '+payload.notePath;
    const open=document.createElement('a');open.href=payload.uri;open.textContent='在 Obsidian 打开';open.title='跳转到这条收藏';result.append(' · ',open);
    refreshObsidianStatus();
  }catch(error){result.className='save-result error';result.textContent=error.message||String(error)}finally{button.disabled=false}
}

function addSaveActions(message,capture){
  const actions=document.createElement('div');actions.className='tutor-save-actions';
  const quick=document.createElement('button');quick.type='button';quick.textContent='收藏到 Obsidian';
  const withNote=document.createElement('button');withNote.type='button';withNote.textContent='备注后收藏';
  const result=document.createElement('div');result.className='save-result';
  const composer=document.createElement('div');composer.className='save-composer';
  const note=document.createElement('textarea');note.placeholder='为什么值得留下？写下你自己的理解、疑问或下一步。';
  const tags=document.createElement('input');tags.placeholder='标签，用逗号分隔（可选）';
  const row=document.createElement('div');row.className='save-composer-row';
  const cancel=document.createElement('button');cancel.type='button';cancel.textContent='取消';
  const confirm=document.createElement('button');confirm.type='button';confirm.textContent='保存';
  row.append(cancel,confirm);composer.append(note,tags,row);actions.append(quick,withNote,composer,result);message.appendChild(actions);
  quick.onclick=()=>saveToObsidian(capture,'',[],quick,result);
  withNote.onclick=()=>{composer.classList.add('open');note.focus()};cancel.onclick=()=>composer.classList.remove('open');
  confirm.onclick=async()=>{await saveToObsidian(capture,note.value,tags.value.split(/[,，]/).map(tag=>tag.trim()).filter(Boolean),confirm,result);composer.classList.remove('open')};
}

async function resetTutor(clearServer=false){
  tutorHistory=[];tutorMessages.innerHTML='';
  const welcome=addTutorMessage('system','我是这篇论文的 Codex 学习助手，通过你已登录的 ChatGPT 订阅回答。我的回答会优先使用当前 Figure 和阅读器中的证据，并把“论文写了什么”与“一般知识”分开。');
  const starters=document.createElement('div');starters.className='tutor-starters';
  ['解释当前 Figure','用本科生能懂的话讲','指出当前证据的局限','解释一个术语'].forEach(text=>{const b=document.createElement('button');b.type='button';b.textContent=text;b.onclick=()=>{tutorInput.value=text;tutorInput.focus()};starters.appendChild(b)});
  welcome.appendChild(starters);
  if(clearServer){try{await fetch(CHAT_ENDPOINT+'/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})}catch(_error){/* 下一次发送时会显示连接问题 */}}
}

async function sendTutorMessage(){
  const message=tutorInput.value.trim();if(!message||tutorBusy)return;
  tutorBusy=true;tutorSend.disabled=true;tutorInput.value='';
  addTutorMessage('user',message);
  const typing=addTutorMessage('assistant','正在结合当前论文证据思考','typing');
  const ctx=contextFor(activeSectionId);const selectionAtSend=selectedText;
  try{
    const response=await fetch(CHAT_ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,selection:selectedText,context:ctx,history:tutorHistory.slice(-10),paper:{title:PAPER_CONTEXT.paper.title,authors:PAPER_CONTEXT.paper.authors,year:PAPER_CONTEXT.paper.year,doi:PAPER_CONTEXT.paper.doi}})});
    const payload=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(payload.error||'聊天服务暂时不可用');
    typing.remove();const assistant=addTutorMessage('assistant',payload.answer);
    addSaveActions(assistant,{question:message,answer:payload.answer,selection:selectionAtSend,context:ctx,paper:{title:PAPER_CONTEXT.paper.title,authors:PAPER_CONTEXT.paper.authors,year:PAPER_CONTEXT.paper.year,doi:PAPER_CONTEXT.paper.doi}});
    tutorHistory.push({role:'user',content:message},{role:'assistant',content:payload.answer});
    selectedText='';updateTutorContext();
  }catch(error){
    typing.remove();
    const hint=location.protocol==='file:'?'请先运行本地服务：python3 skill-development/scientific-literature-tutor/scripts/serve_reader.py':'请确认本地服务正在运行，并且 Codex 已使用 ChatGPT 账号登录。';
    addTutorMessage('error',(error.message||String(error))+'\n\n'+hint);
  }finally{tutorBusy=false;tutorSend.disabled=false;tutorInput.focus()}
}

document.querySelector('#tutor-open').onclick=()=>openTutor();
document.querySelector('#tutor-close').onclick=closeTutor;tutorScrim.onclick=closeTutor;
document.querySelector('#tutor-clear').onclick=()=>resetTutor(true);tutorSend.onclick=sendTutorMessage;
tutorInput.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendTutorMessage()}});
document.querySelectorAll('.ask-term').forEach(button=>button.onclick=()=>{selectedText=button.dataset.termZh+' ('+button.dataset.termEn+')';openTutor('请解释“'+selectedText+'”，并说明它在当前 Figure 中的具体含义。')});
document.querySelectorAll('.ask-figure').forEach(button=>button.onclick=()=>{activeSectionId='fig-'+button.dataset.figure;selectedText='';openTutor('请逐步解释当前 Figure：数据怎么来、图怎么读、作者主张什么，以及它不能证明什么。')});

document.addEventListener('mouseup',event=>{
  if(tutorPanel.contains(event.target)||selectionAsk.contains(event.target))return;
  const selection=window.getSelection();const text=selection?selection.toString().trim():'';
  if(text.length<2||text.length>240){selectionAsk.classList.remove('show');return}
  selectedText=text;const range=selection.getRangeAt(0);const rect=range.getBoundingClientRect();
  selectionAsk.style.left=Math.min(window.innerWidth-105,Math.max(10,rect.left+rect.width/2-42))+'px';
  selectionAsk.style.top=Math.max(8,rect.top-45)+'px';selectionAsk.classList.add('show');updateTutorContext();
});
selectionAsk.onclick=()=>{selectionAsk.classList.remove('show');openTutor('请解释我选中的内容：“'+selectedText+'”。先说明本文语境，再补充一般概念。')};

const tutorSectionSpy=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){activeSectionId=entry.target.id;updateTutorContext()}}),{rootMargin:'-25% 0px -65%'});
document.querySelectorAll('main>section').forEach(section=>tutorSectionSpy.observe(section));
addEventListener('keydown',event=>{if(event.key==='Escape'&&tutorPanel.classList.contains('open'))closeTutor()});
resetTutor();updateTutorContext();refreshObsidianStatus();
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def li(items: list[str]) -> str:
    return "".join(f"<li>{esc(item)}</li>" for item in items)


def figure_section(item: dict, index: int, base: Path) -> str:
    glossary = "".join(
        f'<button type="button" class="term ask-term" data-term-zh="{esc(term["zh"])}" data-term-en="{esc(term["en"])}"><b>{esc(term["zh"])}</b><small>{esc(term["en"])}</small></button>'
        for term in item["glossary"]
    )
    callout = ""
    if item.get("callout"):
        callout = f'<div class="callout"><b>审稿人视角 · Reader audit</b><p>{esc(item["callout"])}</p></div>'
    diagram = ""
    if item.get("diagram"):
        diagram = f'<div class="mini-diagram" aria-label="解释性重绘"><span>解释性重绘</span>{esc(item["diagram"])}</div>'
    return f"""
    <section class="figure-section reveal" id="fig-{index}">
      <div class="section-kicker">{esc(item['number'])} · SOURCE FIGURE</div>
      <h2>{esc(item['title_zh'])}</h2>
      <p class="english-title">{esc(item['title_en'])}</p>
      <div class="key-answer"><span>这一图先记一句</span><strong>{esc(item['takeaway'])}</strong></div>
      <figure class="paper-figure">
        <img loading="lazy" src="{data_uri((base / item['image']).resolve())}" alt="{esc(item['number'])} {esc(item['title_en'])}">
        <figcaption>论文原图 · 点击图片可放大</figcaption>
      </figure>
      {diagram}
      <div class="question-card"><span>本图回答什么 / Question</span><p>{esc(item['question'])}</p></div>
      <button type="button" class="ask-figure" data-figure="{index}">问 Codex：逐步解释这张图</button>
      <div class="explain-grid">
        <details open><summary>数据怎么来的 <small>Data provenance</small></summary><ol>{li(item['provenance'])}</ol></details>
        <details open><summary>图怎么读 <small>Reading guide</small></summary><ul>{li(item['reading'])}</ul></details>
        <details><summary>肉眼看到了什么 <small>Observation</small></summary><ul>{li(item['observations'])}</ul></details>
        <details><summary>作者怎样解释 <small>Claim</small></summary><p>{esc(item['claim'])}</p></details>
        <details class="limit"><summary>这张图不能证明什么 <small>Limitation</small></summary><p>{esc(item['limitation'])}</p></details>
      </div>
      {callout}
      <div class="terms">{glossary}</div>
    </section>"""


def build(data: dict, spec_path: Path) -> str:
    paper = data["paper"]
    base = spec_path.parent
    logic = "".join(
        f'<article><span>{i:02d}</span><h3>{esc(step["label"])}</h3><small>{esc(step["en"])}</small><p>{esc(step["text"])}</p></article>'
        for i, step in enumerate(data["logic_chain"], 1)
    )
    audits = "".join(
        f'<div class="audit-stat"><span>{esc(item["label"])}</span><b>{esc(item["value"])}</b><p>{esc(item["note"])}</p></div>'
        for item in data["sample_audit"]
    )
    figures = "".join(figure_section(item, i, base) for i, item in enumerate(data["figures"], 1))
    nav = "".join(
        f'<a href="#fig-{i}"><span>{i}</span>{esc(item["number"])}<small>{esc(item["title_zh"])}</small></a>'
        for i, item in enumerate(data["figures"], 1)
    )
    validation_steps = "".join(
        f'<div class="validation-step"><span>{i}</span><div><b>{esc(step["label"])}</b><p>{esc(step["text"])}</p></div></div>'
        for i, step in enumerate(data["validation"]["steps"], 1)
    )
    metrics = "".join(
        f'<article><h4>{esc(metric["name"])}</h4><strong>{esc(metric["direction"])}</strong><p>{esc(metric["meaning"])}</p></article>'
        for metric in data["validation"]["metrics"]
    )
    validation_audit = li(data["validation"]["audit"])
    takeaways = "".join(f'<li><span>{i:02d}</span>{esc(item)}</li>' for i, item in enumerate(data["takeaways"], 1))
    questions = "".join(
        f'<details class="quiz"><summary>{esc(item["q"])}</summary><p>{esc(item["a"])}</p></details>'
        for item in data["questions"]
    )
    glossary = "".join(
        f'<tr><td>{esc(item["zh"])}</td><td>{esc(item["en"])}</td><td>{esc(item["note"])}</td></tr>'
        for item in data["glossary"]
    )
    paper_context = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tutor_script = f"const PAPER_CONTEXT={paper_context};\n{TUTOR_JS}"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(paper['title'])} · 交互式精读</title>
<style>
:root{{--ink:#17211f;--muted:#61706b;--paper:#f6f4ee;--card:#fffdf8;--line:#d9ddd6;--green:#16624f;--lime:#c8f05b;--blue:#4675ad;--red:#d9624d;--amber:#f1bd50;--shadow:0 18px 50px rgba(20,42,36,.10)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,"PingFang SC","Noto Sans CJK SC",system-ui,sans-serif;line-height:1.65}}body.dark{{--paper:#111816;--card:#18211e;--ink:#edf3ef;--muted:#a9bab3;--line:#33433d;--shadow:0 18px 50px rgba(0,0,0,.35)}}
#progress{{position:fixed;z-index:30;top:0;left:0;height:4px;width:0;background:linear-gradient(90deg,var(--green),var(--lime))}}button{{font:inherit}}.topbar{{position:fixed;z-index:20;top:18px;right:24px;display:flex;gap:8px}}.topbar button{{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:8px 13px;cursor:pointer;box-shadow:var(--shadow)}}
.hero{{min-height:92vh;padding:10vh max(6vw,28px) 70px;background:radial-gradient(circle at 80% 15%,rgba(200,240,91,.4),transparent 30%),linear-gradient(135deg,#143f35,#102d27 64%,#0a1d19);color:#f3faf6;display:grid;align-content:center}}.hero .kicker{{letter-spacing:.16em;text-transform:uppercase;color:var(--lime);font-size:.78rem;font-weight:800}}.hero h1{{max-width:1100px;font-family:Georgia,"Songti SC",serif;font-size:clamp(2.5rem,6vw,5.8rem);line-height:1.03;margin:.25em 0}}.hero .subtitle{{font-size:clamp(1.05rem,2vw,1.45rem);max-width:920px;color:#cadbd4}}.meta{{display:flex;flex-wrap:wrap;gap:12px 24px;margin-top:28px;color:#adc5bb;font-size:.93rem}}.thesis{{margin-top:48px;max-width:950px;border-left:5px solid var(--lime);padding:8px 0 8px 24px;font-size:clamp(1.25rem,2.2vw,1.8rem);font-weight:700}}
.layout{{display:grid;grid-template-columns:250px minmax(0,1fr);max-width:1500px;margin:auto}}nav{{position:sticky;top:0;height:100vh;padding:34px 20px;border-right:1px solid var(--line);overflow:auto}}nav h3{{font-size:.82rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}nav a{{display:grid;grid-template-columns:30px 1fr;gap:0 9px;padding:9px;border-radius:12px;text-decoration:none;color:var(--ink);margin:4px 0}}nav a:hover,nav a.active{{background:var(--card);box-shadow:0 5px 20px rgba(20,42,36,.06)}}nav a span{{grid-row:1/3;display:grid;place-items:center;width:28px;height:28px;border-radius:8px;background:var(--green);color:white;font-weight:800}}nav small{{color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}main{{min-width:0;padding:70px clamp(24px,5vw,78px) 120px}}section{{scroll-margin-top:24px}}.intro-section,.figure-section,.validation,.closing{{max-width:1100px;margin:0 auto 110px}}.section-kicker{{font-size:.78rem;font-weight:900;letter-spacing:.16em;color:var(--green)}}h2{{font-family:Georgia,"Songti SC",serif;font-size:clamp(2rem,4vw,3.6rem);line-height:1.15;margin:.22em 0}}.english-title{{color:var(--muted);font-style:italic;margin-top:-10px}}
.logic-chain{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:35px}}.logic-chain article{{position:relative;background:var(--card);border:1px solid var(--line);padding:22px;border-radius:18px}}.logic-chain article>span{{font-weight:900;color:var(--green)}}.logic-chain h3{{margin:10px 0 0}}.logic-chain small{{color:var(--muted)}}.logic-chain p{{margin-bottom:0}}.audit-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:35px}}.audit-stat{{background:var(--ink);color:var(--paper);padding:20px;border-radius:16px}}.audit-stat span{{font-size:.8rem;color:#a9bab3}}.audit-stat b{{display:block;font-size:1.7rem;color:var(--lime)}}.audit-stat p{{font-size:.86rem;margin-bottom:0;color:#c9d6d1}}
.figure-section{{border-top:1px solid var(--line);padding-top:80px}}.key-answer{{display:grid;grid-template-columns:150px 1fr;gap:18px;background:var(--green);color:white;border-radius:18px;padding:20px 24px;margin:28px 0}}.key-answer span{{color:var(--lime);font-weight:800}}.key-answer strong{{font-size:1.1rem}}.paper-figure{{margin:28px 0;background:white;padding:16px;border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}}.paper-figure img{{display:block;width:100%;max-height:1050px;object-fit:contain;cursor:zoom-in}}.paper-figure figcaption{{color:#66736e;text-align:center;font-size:.85rem;margin-top:9px}}.mini-diagram{{display:flex;gap:14px;align-items:center;justify-content:center;flex-wrap:wrap;margin:20px 0;padding:20px;border:1px dashed var(--green);border-radius:16px;font-family:ui-monospace,monospace;font-weight:700}}.mini-diagram span{{font-family:inherit;background:var(--lime);color:#15231e;border-radius:999px;padding:4px 10px;font-size:.72rem}}.question-card{{border-left:5px solid var(--amber);background:color-mix(in srgb,var(--amber) 14%,var(--card));padding:18px 22px;margin:24px 0;border-radius:0 16px 16px 0}}.question-card span{{font-weight:900;color:#8a5b00}}.question-card p{{font-size:1.15rem;margin:4px 0}}.explain-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}details{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:0 18px}}summary{{cursor:pointer;font-weight:800;padding:16px 0}}summary small{{color:var(--muted);font-weight:500;margin-left:6px}}details p,details ul,details ol{{margin-top:0;padding-bottom:9px}}details li+li{{margin-top:8px}}details.limit{{border-color:color-mix(in srgb,var(--red) 60%,var(--line))}}.callout{{margin-top:14px;background:color-mix(in srgb,var(--red) 10%,var(--card));border:1px solid color-mix(in srgb,var(--red) 55%,var(--line));padding:20px;border-radius:15px}}.callout b{{color:var(--red)}}.callout p{{margin-bottom:0}}.terms{{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}}.term{{display:flex;gap:7px;align-items:baseline;background:var(--card);border:1px solid var(--line);padding:7px 11px;border-radius:999px}}.term small{{color:var(--muted)}}
.validation{{background:#102f28;color:#eef7f2;padding:clamp(25px,5vw,60px);border-radius:30px}}.validation .section-kicker{{color:var(--lime)}}.validation .lead{{font-size:1.2rem;color:#c7d9d2}}.validation-step{{display:grid;grid-template-columns:42px 1fr;gap:15px;margin:22px 0}}.validation-step>span{{display:grid;place-items:center;width:40px;height:40px;border-radius:50%;background:var(--lime);color:#153329;font-weight:900}}.validation-step b{{font-size:1.08rem}}.validation-step p{{color:#c7d9d2;margin:3px 0}}.metric-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:28px 0}}.metric-grid article{{background:#194438;padding:20px;border-radius:16px}}.metric-grid h4{{margin:0}}.metric-grid strong{{color:var(--lime)}}.metric-grid p{{margin-bottom:0;color:#c7d9d2}}.audit-list{{border-top:1px solid #315b50;padding-top:22px}}.audit-list li+li{{margin-top:9px}}
.takeaway-list{{list-style:none;padding:0}}.takeaway-list li{{display:grid;grid-template-columns:48px 1fr;gap:15px;padding:18px 0;border-bottom:1px solid var(--line);font-size:1.08rem}}.takeaway-list span{{font-weight:900;color:var(--green)}}.quiz{{margin:10px 0}}table{{width:100%;border-collapse:collapse;background:var(--card);border-radius:14px;overflow:hidden}}th,td{{text-align:left;padding:13px;border-bottom:1px solid var(--line)}}th{{background:var(--green);color:white}}footer{{max-width:1100px;margin:40px auto 0;color:var(--muted);font-size:.86rem}}.reveal{{opacity:0;transform:translateY(16px);transition:.55s ease}}.reveal.visible{{opacity:1;transform:none}}
.modal{{display:none;position:fixed;z-index:50;inset:0;background:rgba(0,0,0,.88);padding:20px;align-items:center;justify-content:center}}.modal.open{{display:flex}}.modal img{{max-width:96vw;max-height:94vh;object-fit:contain}}.modal button{{position:absolute;right:24px;top:18px;background:white;border:0;border-radius:999px;padding:9px 13px;cursor:pointer}}
@media(max-width:950px){{.layout{{display:block}}nav{{position:sticky;z-index:10;top:0;height:auto;border:0;border-bottom:1px solid var(--line);background:color-mix(in srgb,var(--paper) 90%,transparent);backdrop-filter:blur(12px);display:flex;gap:5px;padding:8px 12px;overflow:auto}}nav h3{{display:none}}nav a{{min-width:max-content;display:flex;align-items:center}}nav a small{{display:none}}main{{padding-top:45px}}.logic-chain{{grid-template-columns:1fr 1fr}}.audit-grid{{grid-template-columns:1fr 1fr}}}}
@media(max-width:650px){{.hero{{min-height:auto;padding-top:110px}}.logic-chain,.audit-grid,.explain-grid,.metric-grid{{grid-template-columns:1fr}}.key-answer{{grid-template-columns:1fr;gap:4px}}.topbar{{top:12px;right:12px}}main{{padding-left:16px;padding-right:16px}}}}
@media print{{nav,.topbar,#progress{{display:none}}.layout{{display:block}}main{{padding:20px}}.reveal{{opacity:1;transform:none}}details{{break-inside:avoid}}details>*{{display:block!important}}}}
{TUTOR_CSS}
</style>
</head>
<body>
<div id="progress"></div>
<div class="topbar"><button id="tutor-open" class="tutor-toggle" aria-label="打开 Codex 学习助手"><span class="spark">✦</span><span class="label">Codex 学习助手</span></button><button id="theme" aria-label="切换主题">明 / 暗</button><button onclick="window.print()">打印 / PDF</button></div>
<header class="hero" id="top">
  <div class="kicker">{esc(paper.get('kicker','INTERACTIVE PAPER READER'))}</div>
  <h1>{esc(paper['title'])}</h1>
  <p class="subtitle">{esc(paper['subtitle'])}</p>
  <div class="meta"><span>{esc(paper['authors'])}</span><span>{esc(paper['journal'])} · {esc(paper['year'])}</span><span>DOI {esc(paper['doi'])}</span></div>
  <div class="thesis">{esc(data['thesis'])}</div>
</header>
<div class="layout">
<nav><h3>阅读路线</h3><a href="#logic"><span>0</span>逻辑链<small>Paper logic</small></a>{nav}<a href="#validation"><span>V</span>验证<small>Validation audit</small></a><a href="#closing"><span>✓</span>总结<small>Takeaways</small></a></nav>
<main>
  <section class="intro-section reveal" id="logic">
    <div class="section-kicker">PAPER LOGIC · 先搭骨架</div><h2>整篇论文在做什么</h2>
    <div class="logic-chain">{logic}</div>
    <div class="audit-grid">{audits}</div>
  </section>
  {figures}
  <section class="validation reveal" id="validation">
    <div class="section-kicker">VALIDATION · 不要和 workflow 混为一谈</div><h2>{esc(data['validation']['title'])}</h2><p class="lead">{esc(data['validation']['summary'])}</p>
    {validation_steps}
    <div class="metric-grid">{metrics}</div>
    <div class="audit-list"><h3>验证强度审计</h3><ul>{validation_audit}</ul></div>
  </section>
  <section class="closing reveal" id="closing">
    <div class="section-kicker">SYNTHESIS · 读完以后应该会什么</div><h2>把整篇论文压成五件事</h2><ol class="takeaway-list">{takeaways}</ol>
    <h2>自测</h2>{questions}
    <h2>中英术语表</h2><table><thead><tr><th>中文</th><th>English</th><th>在本文中的意思</th></tr></thead><tbody>{glossary}</tbody></table>
    <footer>{esc(data.get('source_note',''))}<br>源文件：{esc(paper['source_pdf'])}</footer>
  </section>
</main></div>
<div class="modal" id="modal"><button aria-label="关闭">关闭 ×</button><img alt="放大后的论文原图"></div>
<button type="button" class="selection-ask" id="selection-ask">问 Codex</button>
<div class="tutor-scrim" id="tutor-scrim"></div>
<aside class="tutor-panel" id="tutor-panel" aria-hidden="true" aria-label="Codex 论文学习助手">
  <header class="tutor-head"><div class="avatar">CX</div><div><h2>Codex 论文学习助手</h2><p>ChatGPT 订阅 · 当前 Figure 证据感知 · <span class="obsidian-state" id="obsidian-state">检查 Obsidian…</span></p></div><button type="button" id="tutor-close" aria-label="关闭聊天">×</button></header>
  <div class="tutor-context"><b>正在阅读</b><span id="tutor-context-label"></span></div>
  <div class="tutor-messages" id="tutor-messages" aria-live="polite"></div>
  <div class="tutor-compose"><textarea id="tutor-input" placeholder="问一个术语、Figure 或验证问题……" aria-label="向 GPT 提问"></textarea><div class="tutor-actions"><button type="button" class="tutor-clear" id="tutor-clear">清空</button><small>Enter 发送 · Shift+Enter 换行</small><button type="button" class="tutor-send" id="tutor-send">发送</button></div></div>
</aside>
<script>
const progress=document.querySelector('#progress');
const update=()=>{{const h=document.documentElement;const p=h.scrollTop/(h.scrollHeight-h.clientHeight)*100;progress.style.width=Math.max(0,p)+'%'}};addEventListener('scroll',update,{{passive:true}});update();
document.querySelector('#theme').onclick=()=>document.body.classList.toggle('dark');
const modal=document.querySelector('#modal'),modalImg=modal.querySelector('img');document.querySelectorAll('.paper-figure img').forEach(img=>img.onclick=()=>{{modalImg.src=img.src;modal.classList.add('open')}});modal.onclick=e=>{{if(e.target!==modalImg)modal.classList.remove('open')}};addEventListener('keydown',e=>{{if(e.key==='Escape')modal.classList.remove('open')}});
const reveal=new IntersectionObserver(es=>es.forEach(e=>{{if(e.isIntersecting)e.target.classList.add('visible')}}),{{threshold:.05}});document.querySelectorAll('.reveal').forEach(e=>reveal.observe(e));
const links=[...document.querySelectorAll('nav a')];const sections=links.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);const spy=new IntersectionObserver(es=>es.forEach(e=>{{if(e.isIntersecting){{links.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+e.target.id))}}}}),{{rootMargin:'-20% 0px -70%'}});sections.forEach(s=>spy.observe(s));
{tutor_script}
</script>
</body></html>"""


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: build_reader.py SPEC.json OUTPUT.html", file=sys.stderr)
        return 2
    spec = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    data = json.loads(spec.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build(data, spec), encoding="utf-8")
    print(f"Built {output} ({output.stat().st_size / 1024 / 1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
