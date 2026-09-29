"""Build results/report.html, a self-contained UI over the saved results.

Reads only results/*.json (no API calls). Usage: python build_report.py [--open]
"""
import json
import sys
import webbrowser

from common import RESULTS_DIR

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jev vs LLM Triage</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1c1c1a;--mute:#6b6b66;--line:#e4e4df;--jev:#2f6fed;--llm:#e07a1f;--bad:#c2410c;--badbg:#fff1e6;--ok:#15803d}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ecece8;--mute:#9a9a92;--line:#33332f;--jev:#6b9bff;--llm:#f0a050;--bad:#ff9a5c;--badbg:#2e2016;--ok:#4ade80}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card .k{color:var(--mute);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.card .v{font-size:22px;font-weight:650;margin-top:2px}.card .s{color:var(--mute);font-size:13px}
.j{color:var(--jev)}.l{color:var(--llm)}
.bar{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--mute)}
.bar i{display:block;height:8px;border-radius:4px}
.tools{display:flex;gap:12px;align-items:center;margin:8px 0 10px;flex-wrap:wrap}
label{cursor:pointer;user-select:none}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:9px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}
tr.row{cursor:pointer}tr.row:hover td{background:color-mix(in srgb,var(--line) 35%,transparent)}
td.diff{background:var(--badbg);color:var(--bad);font-weight:600}
.title{max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tag{display:inline-block;font-size:12px;padding:1px 7px;border-radius:99px;border:1px solid var(--line);color:var(--mute)}
.tag.d{border-color:var(--bad);color:var(--bad)}
.detail td{background:var(--bg);padding:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:760px){.grid{grid-template-columns:1fr}}
pre{margin:0;white-space:pre-wrap;word-break:break-word;font:12.5px/1.45 ui-monospace,Consolas,monospace;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;max-height:260px;overflow:auto}
h4{margin:0 0 6px;font-size:13px}.note{color:var(--mute);font-size:13px;margin-top:20px}
.scroll{overflow-x:auto}
</style></head><body><main>
<h1>Jev vs <span id="llmname"></span> — GitHub issue triage</h1>
<p class="sub" id="sub"></p>
<div class="cards" id="cards"></div>
<div class="tools"><label><input type="checkbox" id="onlyDiff"> Show disagreements only</label>
<span class="sub" style="margin:0">Click a row to see the issue text and each model's raw answer.</span></div>
<div class="scroll"><table><thead><tr><th>#</th><th>Issue</th><th>Field</th><th class="j">Jev</th><th class="l" id="llmh"></th><th>Latency (s)</th></tr></thead><tbody id="tb"></tbody></table></div>
<p class="note" id="note"></p>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const F=['category','priority','needs_more_info','duplicate_likely'];
const yn=v=>v===true?'yes':v===false?'no':(v??'—');
const $=(t,p={},...c)=>{const e=document.createElement(t);for(const k in p){k==='class'?e.className=p[k]:e[k]=p[k]}c.flat().forEach(x=>e.append(x));return e};
const S=D.summary, M=D.llm_model;
document.getElementById('llmname').textContent=M;
document.getElementById('llmh').textContent=M;
document.getElementById('sub').textContent=`${S.issues_compared} open issues, same input to both models. All numbers come from results/*.json.`;
const fx=(n,d=3)=>Number(n).toFixed(d);
const mk=(k,v,s,cls='')=>$('div',{class:'card'},$('div',{class:'k'},k),$('div',{class:'v '+cls},v),$('div',{class:'s'},s));
const cards=document.getElementById('cards');
const mx=Math.max(S.jev_avg_latency_s,S.llm_avg_latency_s);
const bar=(c,v)=>{const b=$('div',{class:'bar'});const i=$('i');i.style.width=(v/mx*120)+'px';i.style.background=`var(--${c})`;b.append(i,fx(v,2)+' s');return b};
const lat=$('div',{class:'card'},$('div',{class:'k'},'Avg latency'),bar('jev',S.jev_avg_latency_s),bar('llm',S.llm_avg_latency_s),$('div',{class:'s'},'Jev (blue) vs LLM (orange)'));
cards.append(lat,
 mk('Total cost',`$${fx(S.jev_total_cost_usd,6)}`,`Jev · LLM at list price: $${fx(S.llm_total_cost_usd,6)}`,'j'),
 mk('Disagreements',`${S.issues_with_disagreement} / ${S.issues_compared}`,Object.entries(S.per_field_disagreements).map(([k,v])=>k+':'+v).join(' · ')),
 mk('LLM JSON parse failures',S.llm_parse_failures,'json_object mode',S.llm_parse_failures?'l':''));
const tb=document.getElementById('tb');
function render(){
 tb.replaceChildren();
 const only=document.getElementById('onlyDiff').checked;
 D.rows.forEach(r=>{
  if(only&&!r.diff.length)return;
  F.forEach((f,i)=>{
   const dd=r.diff.includes(f), row=$('tr',{class:i===0?'row':'sub'});
   if(i===0){row.dataset.n=r.number}
   row.append(
    i===0?$('td',{},'#'+r.number):$('td'),
    i===0?$('td',{class:'title',title:r.title},r.title):$('td'),
    $('td',{},f),
    $('td',{class:dd?'diff':''},yn(r.jev[f])),
    $('td',{class:dd?'diff':''},r.llm.parse_error?'PARSE ERROR':yn(r.llm[f])),
    i===0?$('td',{},`${fx(r.jev.latency_s,2)} / ${fx(r.llm.latency_s,2)}`):$('td'));
   tb.append(row);
  });
  const det=$('tr',{class:'detail'});det.hidden=true;
  const cell=$('td',{colSpan:6});
  const j=r.jev;
  cell.append($('div',{class:'grid'},
   $('div',{},$('h4',{},'Issue text (first 1500 chars)'),$('pre',{},r.body.slice(0,1500))),
   $('div',{},$('h4',{class:'j'},'Jev (typed answers)'),$('pre',{},
    `category: ${j.category} (confidence ${fx(j.category_confidence,2)})\npriority: ${j.priority}  raw score ${fx(j.priority_raw,2)} on 0-4 scale, +1 (confidence ${fx(j.priority_confidence,2)})\nneeds_more_info: P(yes)=${fx(j.needs_more_info_prob,2)}\nduplicate_likely: P(yes)=${fx(j.duplicate_likely_prob,2)}\ninput tokens: ${j.input_tokens}`),
    $('h4',{class:'l',style:'margin-top:12px'},M+' (raw response)'),$('pre',{},(r.llm.raw||'')+(r.llm.parse_error?'\n\nPARSE ERROR: '+r.llm.parse_error:'')))));
  det.append(cell);tb.append(det);
 });
 tb.querySelectorAll('tr.row').forEach(tr=>{
  const nxt=(()=>{let e=tr;while(e&&!e.classList.contains('detail'))e=e.nextElementSibling;return e})();
  tr.onclick=()=>{nxt.hidden=!nxt.hidden};
 });
}
document.getElementById('onlyDiff').onchange=render;render();
document.getElementById('note').textContent=`Priority for Jev = round(score)+1 (score is 0-4). Yes/no thresholded at 0.5. LLM cost uses list price ($${D.prices.in}/M in, $${D.prices.out}/M out); Jev $0.042/M input, output free. Single-run latency is noisy.`;
</script></body></html>
"""


def main():
    def load(n):
        return json.loads((RESULTS_DIR / n).read_text(encoding="utf-8"))

    issues = {i["number"]: i for i in load("issues.json")}
    jev = {r["number"]: r for r in load("jev_results.json")}
    llm = {r["number"]: r for r in load("llm_results.json")}
    summary = load("summary.json")
    diffs = {d["number"]: d["fields"] for d in summary["disagreements"]}
    fields = ["category", "priority", "needs_more_info", "duplicate_likely"]

    rows = []
    for n in sorted(set(jev) & set(llm), reverse=True):
        rows.append({
            "number": n, "title": issues[n]["title"], "body": issues[n]["body"],
            "jev": jev[n], "llm": llm[n],
            "diff": [f for f in diffs.get(n, []) if f in fields],
        })

    import os
    from dotenv import load_dotenv
    load_dotenv()
    data = {
        "summary": summary, "llm_model": summary.get("llm_model", "LLM"), "rows": rows,
        "prices": {"in": os.getenv("LLM_INPUT_PER_M", "0.15"),
                   "out": os.getenv("LLM_OUTPUT_PER_M", "0.60")},
    }
    payload = json.dumps(data).replace("</", "<\\/")
    out = RESULTS_DIR / "report.html"
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    print(f"Wrote {out}")
    if "--open" in sys.argv:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
