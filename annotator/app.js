let SAMPLES=[], LABELS=[], idx=0;
const el=(id)=>document.getElementById(id);
async function loadJSON(u){ const r=await fetch(u); return r.json(); }
function render(){
  el("pos").textContent = `Item ${idx+1} / ${SAMPLES.length}`;
  const s = SAMPLES[idx]||{};
  el("sample").innerHTML = `
    <h2>#${s.id}</h2>
    <p><b>Prompt:</b> ${s.prompt||""}</p>
    <p><b>Thesis:</b> ${s.thesis||""}</p>
    <pre class="essay">${s.essay||""}</pre>
    <p><b>Gold:</b> ${s.gold ?? "—"}</p>`;
  const lab = LABELS.find(x=>x.id===s.id) || {};
  ["TR","CC","LR","GR","OV"].forEach(k=> el(k).value = lab[k] ?? "");
  el("notes").value = lab.notes ?? "";
}
async function save(){
  const s=SAMPLES[idx]; if(!s) return;
  const payload = {
    id: s.id,
    TR: Number(el("TR").value||0),
    CC: Number(el("CC").value||0),
    LR: Number(el("LR").value||0),
    GR: Number(el("GR").value||0),
    OV: Number(el("OV").value||0),
    notes: el("notes").value||""
  };
  const r = await fetch("/api/annotate",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(payload)});
  const j = await r.json();
  if (j.ok){ const i = LABELS.findIndex(x=>x.id===payload.id); if(i>=0) LABELS[i]=payload; else LABELS.push(payload); el("status").textContent=`Saved (${j.count} total)`; }
}
async function main(){
  SAMPLES = await loadJSON("/api/samples");
  LABELS  = await loadJSON("/api/labels");
  render();
  el("prev").onclick=()=>{ if(idx>0){idx--;render();} };
  el("next").onclick=()=>{ if(idx<SAMPLES.length-1){idx++;render();} };
  el("save").onclick=save;
}
main();
