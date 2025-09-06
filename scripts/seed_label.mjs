/* scripts/seed_label.mjs — creates one synthetic label to verify pipeline */
import fs from "node:fs"; import path from "node:path";
const LABEL_FILE = path.join("annotations","sprint4_labels.json");
const sample = { id:1, TR:7, CC:7, LR:7, GR:7, OV:7, notes:"seed" };
let arr = []; try{ arr = JSON.parse(fs.readFileSync(LABEL_FILE,"utf8")); }catch{}
const i = arr.findIndex(x=>x.id===sample.id); if(i>=0) arr[i]=sample; else arr.push(sample);
fs.mkdirSync("annotations",{recursive:true}); fs.writeFileSync(LABEL_FILE, JSON.stringify(arr,null,2));
console.log("seeded", LABEL_FILE);
