/* scripts/t1_overview_check.mjs — presence + global (no numbers) */
import fs from "node:fs";
const input = (()=>{ try{ return JSON.parse(fs.readFileSync("tests/sample_t1_overview.json","utf8")); }catch{ return { overview:"Overall, X rose while Y fell." }; }})();
const ov = (input.overview||"").trim();
const hasNumbers = /\d/.test(ov);
const isGlobal = !hasNumbers && ov.split(/[.?!]/).filter(s=>s.trim()).length<=3;
const res = {
  checks: { "ov.present": ov.length>0, "ov.patterns": isGlobal },
  notes: []
};
if (!ov) res.notes.push("Write a 1–2 sentence, number-free overview.");
if (hasNumbers) res.notes.push("Remove specific data; keep overview global.");
console.log(JSON.stringify(res,null,2));
