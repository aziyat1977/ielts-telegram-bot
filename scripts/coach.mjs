/* Minimal coach adapter (reads heuristic rule JSON and returns a placeholder score map) */
import fs from "node:fs";
export function loadRules(path){ return JSON.parse(fs.readFileSync(path,"utf8")); }
export function scoreSimple(rules){
  const result = { bands: {}, notes: [] };
  if (rules.criteria?.TaskResponse)     result.bands.TR = 7;
  if (rules.criteria?.CoherenceCohesion)result.bands.CC = 7;
  if (rules.criteria?.LexicalResource)  result.bands.LR = 7;
  if (rules.criteria?.Grammar)          result.bands.GR = 7;
  return result;
}
