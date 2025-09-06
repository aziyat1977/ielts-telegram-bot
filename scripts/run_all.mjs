/* scripts/run_all.mjs — run baseline engines + produce a predictions file for QWK */
import fs from "node:fs";
import { spawnSync } from "node:child_process";

function run(cmd, args){
  const r = spawnSync(process.execPath, ["-e", `
    const {spawnSync}=require('node:child_process');
    const r=spawnSync(${JSON.stringify(cmd)}, ${JSON.stringify(args)}, {stdio:'pipe',encoding:'utf8'});
    if(r.status!==0){ console.error(r.stderr); process.exit(r.status||1); }
    process.stdout.write(r.stdout||'');
  `], {stdio:'pipe',encoding:'utf8'});
  if (r.status!==0) { console.error(r.stderr); process.exit(r.status||1); }
  return r.stdout;
}

// Ensure sample inputs exist
if (!fs.existsSync("tests")) fs.mkdirSync("tests",{recursive:true});
if (!fs.existsSync("tests/sample_t2_input.json")){
  fs.writeFileSync("tests/sample_t2_input.json", JSON.stringify({
    prompt: "Discuss both views and give your opinion.",
    thesis: "I believe that benefits outweigh drawbacks.",
    essay: "Body 1...\n\nFor example, ... Therefore, ...\n\nBody 2...\n\nIn addition, ... For instance, ..."
  }, null, 2));
}
if (!fs.existsSync("tests/sample_t1_overview.json")){
  fs.writeFileSync("tests/sample_t1_overview.json", JSON.stringify({
    overview: "Overall, X rose while Y declined; meanwhile Z remained broadly stable."
  }, null, 2));
}
if (!fs.existsSync("tests/sample_t1_features.json")){
  fs.writeFileSync("tests/sample_t1_features.json", JSON.stringify({
    features: ["A highest", "B lowest", "C stable"],
    comparisons: ["A > B", "C ~ B"],
    units: true, time: true
  }, null, 2));
}
if (!fs.existsSync("tests/sample_gold.json")){
  fs.writeFileSync("tests/sample_gold.json", JSON.stringify([
    {"id":1,"band":7},{"id":2,"band":7},{"id":3,"band":8},{"id":4,"band":6},{"id":5,"band":9},
    {"id":6,"band":8},{"id":7,"band":7},{"id":8,"band":6},{"id":9,"band":8},{"id":10,"band":7}
  ], null, 2));
}

// Run engines
const t2 = run("node", ["scripts/t2_engine.mjs"]);
const t1ov = run("node", ["scripts/t1_overview_check.mjs"]);
const t1kf = run("node", ["scripts/t1_features_check.mjs"]);

// Convert bands → flat band list for sample_pred.json from t2 (TR/CC/LR/GR → simple average)
const t2res = JSON.parse(t2);
const bands = Object.values(t2res.bands||{});
const avg = Math.round(bands.reduce((s,x)=>s+x,0)/Math.max(1,bands.length));
const pred = Array.from({length:10}, (_,i)=>({id:i+1, band: avg}));
fs.writeFileSync("tests/sample_pred.json", JSON.stringify(pred,null,2));

// Output summary
console.log(JSON.stringify({
  t2: t2res, t1_overview: JSON.parse(t1ov), t1_features: JSON.parse(t1kf),
  pred_avg_band: avg
}, null, 2));
