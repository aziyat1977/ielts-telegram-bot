/* scripts/eval_qwk.mjs — Quadratic Weighted Kappa */
import fs from "node:fs";

function qwk(raterA, raterB, minRating, maxRating){
  const n = maxRating-minRating+1;
  const O = Array.from({length:n},()=>Array(n).fill(0));
  for (let i=0;i<raterA.length;i++){
    const a=raterA[i]-minRating, b=raterB[i]-minRating;
    if (a>=0&&a<n&&b>=0&&b<n) O[a][b] += 1;
  }
  const A = O.map(row=>row.reduce((s,x)=>s+x,0));
  const B = Array(n).fill(0); for (let j=0;j<n;j++) for (let i=0;i<n;i++) B[j]+=O[i][j];
  const E = Array.from({length:n},()=>Array(n).fill(0));
  const N = raterA.length;
  for (let i=0;i<n;i++) for (let j=0;j<n;j++) E[i][j] = (A[i]*B[j])/N;
  let wNum=0, wDen=0;
  for (let i=0;i<n;i++) for (let j=0;j<n;j++){
    const w = ((i-j)*(i-j))/((n-1)*(n-1));
    wNum += w * O[i][j];
    wDen += w * E[i][j];
  }
  return (wDen===0) ? 1 : 1-(wNum/wDen);
}

// Load sample gold/pred files or use inline sample
let gold, pred;
try {
  const g = JSON.parse(fs.readFileSync("tests/sample_gold.json","utf8"));
  const p = JSON.parse(fs.readFileSync("tests/sample_pred.json","utf8"));
  gold = g.map(x=>x.band);
  pred = p.map(x=>x.band);
} catch {
  gold = [7,7,8,6,9,8,7,6,8,7];
  pred = [7,6,8,6,9,7,7,6,8,7];
}
const min = 5, max = 9;
const score = qwk(gold, pred, min, max);
console.log(JSON.stringify({ qwk: Number(score.toFixed(4)), count: gold.length }, null, 2));
