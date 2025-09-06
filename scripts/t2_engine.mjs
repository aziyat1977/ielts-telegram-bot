/* scripts/t2_engine.mjs — deterministic baseline scoring from rules + simple signals */
import fs from "node:fs";

const RULES = JSON.parse(fs.readFileSync("heuristics/t2-coach.rules.json","utf8"));
const input = (() => {
  try { return JSON.parse(fs.readFileSync("tests/sample_t2_input.json","utf8")); }
  catch { return { prompt: "Discuss both views and give your opinion.", essay: "Body1 ... Body2 ...", thesis: "I believe ..."}; }
})();

function checkTR(input){
  const res = { "tr.parts":0,"tr.position":0,"tr.support":0, notes:[] };
  const p = (input.prompt||"").toLowerCase();
  const e = (input.essay||"").toLowerCase();
  const t = (input.thesis||"").toLowerCase();

  // very light signals
  const partsNeeded = (p.includes("both views")?2: (p.includes("advantages")&&p.includes("disadvantages"))?2: (p.includes("cause")&&p.includes("solution"))?2: 1);
  const bodies = (input.essay||"").split(/\n{2,}|(?:^|\n)body\s*\d+/i).filter(x=>x.trim().length>50).length;
  if (bodies >= partsNeeded) res["tr.parts"]=1; else res.notes.push("Add body paragraphs to cover all parts.");

  if (t && !/i (do )?(believe|agree|disagree|think)/.test(t)) res.notes.push("Make position explicit in thesis.");
  res["tr.position"] = t ? 1 : 0;

  const developed = ((input.essay||"").match(/for example|for instance|such as|because|therefore|as a result/gi)||[]).length >= partsNeeded;
  res["tr.support"] = developed ? 1 : 0;
  if (!developed) res.notes.push("Add concrete examples/explanations.");

  return res;
}

function checkCC(input){
  const res = { "cc.paragraph":0,"cc.invisible":0, notes:[] };
  const paras = (input.essay||"").split(/\n{2,}/).filter(p=>p.trim());
  res["cc.paragraph"] = paras.length>=3 ? 1 : 0;

  const linkerCount = ((input.essay||"").match(/\b(moreover|furthermore|in addition|on the other hand|however|therefore)\b/gi)||[]).length;
  res["cc.invisible"] = linkerCount<=6 ? 1 : 0;
  if (linkerCount>6) res.notes.push("Reduce explicit linkers; use referencing/substitution.");
  return res;
}

function checkLR(input){
  const res = { "lr.precision":0, notes:[] };
  const essay = (input.essay||"");
  const uniq = new Set(essay.toLowerCase().split(/[^a-z]+/).filter(w=>w.length>=6));
  res["lr.precision"] = uniq.size>=30 ? 1 : 0;
  if (!res["lr.precision"]) res.notes.push("Increase lexical variety and precise collocations.");
  return res;
}

function checkGR(input){
  const res = { "gr.rangeacc":0, notes:[] };
  const comma = ((input.essay||"").match(/,/g)||[]).length;
  const subClause = ((input.essay||"").match(/\b(which|that|although|while|because|since)\b/gi)||[]).length;
  res["gr.rangeacc"] = (comma+subClause)>=8 ? 1 : 0;
  if (!res["gr.rangeacc"]) res.notes.push("Add complex but accurate structures; keep slips rare.");
  return res;
}

function bandFromChecks(weightedScore, maxScore){
  const ratio = maxScore? (weightedScore/maxScore):0;
  if (ratio>=0.85) return 9;
  if (ratio>=0.70) return 8;
  if (ratio>=0.55) return 7;
  if (ratio>=0.40) return 6;
  return 5;
}

function score(){
  const tr = checkTR(input);
  const cc = checkCC(input);
  const lr = checkLR(input);
  const gr = checkGR(input);

  const crit = {
    TR: { checks: tr, weights: { "tr.parts":3,"tr.position":3,"tr.support":2 } },
    CC: { checks: cc, weights: { "cc.paragraph":2,"cc.invisible":2 } },
    LR: { checks: lr, weights: { "lr.precision":2 } },
    GR: { checks: gr, weights: { "gr.rangeacc":2 } }
  };

  const result = { bands:{}, notes:[] };
  for (const [k,v] of Object.entries(crit)){
    let got=0, max=0;
    for (const [cid,val] of Object.entries(v.checks)){
      const w = v.weights[cid]||1; max+=w; got+= w*(val?1:0);
    }
    result.bands[k] = bandFromChecks(got,max);
    if (v.checks.notes?.length) result.notes.push(...v.checks.notes);
  }
  console.log(JSON.stringify(result,null,2));
}
score();
