/* scripts/t1_features_check.mjs — 3–5 features + comparisons + units/time */
import fs from "node:fs";
const input = (()=>{ try{ return JSON.parse(fs.readFileSync("tests/sample_t1_features.json","utf8")); }catch{ return { features:["A highest","B lowest","C steady"], comparisons:["A > B","C ~ B"], units:true, time:true }; }})();
const kf = input.features||[];
const comps = input.comparisons||[];
const res = { checks:{
  "kf.selection": kf.length>=3 && kf.length<=5,
  "kf.compare":   comps.length>=1 && !!input.units && !!input.time,
  "kf.nospec":    !(input.speculation===true)
}, notes:[] };
if (!(kf.length>=3 && kf.length<=5)) res.notes.push("Select only 3–5 salient features.");
if (!(comps.length>=1 && input.units && input.time)) res.notes.push("Add valid comparisons with correct units and timeframe.");
console.log(JSON.stringify(res,null,2));
