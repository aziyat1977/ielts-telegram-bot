/* annotator/server.mjs — static annotator + JSON API (no deps) */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const DATA_FILE = path.join(ROOT, "data", "sprint3_t2_samples.json");
const LABEL_FILE = path.join(ROOT, "annotations", "sprint4_labels.json");

function send(res, code, body, type="application/json"){
  res.writeHead(code, { "content-type": type, "cache-control": "no-store" });
  res.end(body);
}
function serveStatic(req, res){
  let p = url.parse(req.url).pathname;
  if (p === "/") p = "/index.html";
  const filePath = path.join(__dirname, p);
  if (!filePath.startsWith(__dirname)) return send(res, 403, "forbidden", "text/plain");
  fs.readFile(filePath, (err, data)=>{
    if (err) return send(res, 404, "not found", "text/plain");
    const ext = path.extname(filePath);
    const type = ext === ".html" ? "text/html" : ext === ".js" ? "text/javascript" : ext === ".css" ? "text/css" : "text/plain";
    send(res, 200, data, type);
  });
}
function readJsonSafe(file, fallback){ try{ return JSON.parse(fs.readFileSync(file,"utf8")); }catch{ return fallback; } }
function writeJsonSafe(file, obj){ fs.mkdirSync(path.dirname(file),{recursive:true}); fs.writeFileSync(file, JSON.stringify(obj,null,2)); }

const server = http.createServer((req,res)=>{
  const { method } = req;
  const parsed = url.parse(req.url,true);
  if (parsed.pathname.startsWith("/api/")){
    res.setHeader("access-control-allow-origin","*");
    res.setHeader("access-control-allow-methods","GET,POST,OPTIONS");
    res.setHeader("access-control-allow-headers","content-type");
    if (method === "OPTIONS") return send(res,204,"");
    if (parsed.pathname === "/api/samples" && method === "GET"){
      const samples = readJsonSafe(DATA_FILE, []);
      return send(res, 200, JSON.stringify(samples));
    }
    if (parsed.pathname === "/api/labels" && method === "GET"){
      const labels = readJsonSafe(LABEL_FILE, []);
      return send(res, 200, JSON.stringify(labels));
    }
    if (parsed.pathname === "/api/annotate" && method === "POST"){
      let buf=[]; req.on("data",c=>buf.push(c)); req.on("end",()=>{
        try{
          const payload = JSON.parse(Buffer.concat(buf).toString("utf8"));
          if (!payload || typeof payload.id !== "number") return send(res,400,JSON.stringify({error:"id required"}));
          const labels = readJsonSafe(LABEL_FILE, []);
          const idx = labels.findIndex(x=>x.id===payload.id);
          if (idx>=0) labels[idx] = payload; else labels.push(payload);
          writeJsonSafe(LABEL_FILE, labels);
          return send(res,200,JSON.stringify({ok:true,count:labels.length}));
        }catch{ return send(res,400,JSON.stringify({error:"bad json"})); }
      });
      return;
    }
    return send(res,404,JSON.stringify({error:"not found"}));
  }
  return serveStatic(req,res);
});
const PORT = process.env.PORT || 8081;
server.listen(PORT, "0.0.0.0", ()=>console.log("annotator up on", PORT));
