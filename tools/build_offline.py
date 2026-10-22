"""生成离线单文件版：dist/paper-recycle-offline.html

为什么要有这个
--------------
线上版依赖 HTTP 服务（FastAPI + 网络）。当浏览器无法访问托管域名、
或现场没有网络时，用户看到的就是"打不开"。
离线版把**全部数据内联进一个 HTML**，双击即可打开，不联网、不起服务。

能力差异（如实说明）：
- 保留：对话问答、区域统计、历年数据、分类结构、企业分布、CSV 导出
- 不含：xlsx 多表导出（需要 openpyxl）、语音输入（浏览器 API 与网络相关）
"""

import json
from pathlib import Path

import paper_recycle_agent
from paper_recycle_agent import data as yearbook
from paper_recycle_agent import enterprises, io_table, knowledge, regions
from paper_recycle_agent import stats as stats_mod

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "paper-recycle-offline.html"


def build_payload() -> dict:
    years = [int(r["year"]) for r in stats_mod.get_history()]
    shares = {y: stats_mod._interp_shares(y) for y in years}

    provinces = []
    for p in regions.get_children("CN"):
        provinces.append({
            "code": p["code"],
            "name": p["name"],
            "rank": p["rank"],
            "tier": p["tier_label"],
            "quality": p["quality"],
            "stats": p["stats"],
        })

    return {
        "version": paper_recycle_agent.__version__,
        "national": {
            "name": "全国",
            "year": regions.NATIONAL_YEAR,
            "stats": regions.NATIONAL_STATS,
            "provenance": regions.PROVENANCE_OFFICIAL,
        },
        "provinces": provinces,
        "history": stats_mod.get_history(),
        "imports": stats_mod.get_import_series(),
        "shares": shares,
        "catmeta": stats_mod.CATEGORY_META,
        "years": years,
        "national_year": regions.NATIONAL_YEAR,
        "latest_year": stats_mod.LATEST_YEAR,
        "enterprises": enterprises.ENTERPRISES,
        "ent_is_demo": enterprises.IS_DEMO,
        "ent_types": enterprises.TYPES,
        "knowledge": [
            {
                "name": c.name,
                "aliases": c.aliases,
                "recyclable": c.recyclable,
                "price": c.value_per_kg,
                "tips": c.tips,
            }
            for c in knowledge.CATEGORIES
        ],
        "gbt": yearbook.CATEGORIES_8,
        "quality_rules": yearbook.QUALITY_RULES,
        "sources": yearbook.SOURCES + stats_mod.SOURCES,
        "io": {
            "spend": io_table.spend(io_table.NATIONAL_IO["year"]),
            "direct": io_table.direct_coefficient(io_table.NATIONAL_IO["year"]),
            "unit": io_table.unit_consumption(io_table.NATIONAL_IO["year"]),
            "provinces": io_table.province_spend(io_table.NATIONAL_IO["year"]),
            "levels": io_table.LEVELS,
        },
    }


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>废纸回收 Agent 对话助手（离线版）</title>
<style>
  :root {
    --bg:#f5f7fa; --panel:#fff; --ink:#1f2329; --muted:#6b7280;
    --brand:#2f7d4f; --brand-soft:#e8f3ec; --brand-line:#cfe6da; --border:#e5e7eb;
    --warn-bg:#fff8e6; --warn-line:#f2dfae; --warn-ink:#8a6d1f;
    --bot:#eef1f5; --bar:#4a9d6b; --bar2:#8fbfa3;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
       background:var(--bg);color:var(--ink);height:100vh;display:flex;flex-direction:column}
  header{background:var(--brand);color:#fff;padding:11px 20px;font-size:17px;font-weight:600;
         display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  header .sub{font-size:12px;font-weight:400;opacity:.9}
  header .off{background:rgba(255,255,255,.2);border-radius:10px;padding:2px 8px;font-size:11px;font-weight:400}
  .layout{flex:1;display:flex;min-height:0}
  .chat{flex:1;display:flex;flex-direction:column;min-width:0}
  .messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
  .msg{max-width:82%;padding:9px 13px;border-radius:13px;line-height:1.55;white-space:pre-wrap;
       word-break:break-word;font-size:13.5px}
  .msg.bot{background:var(--bot);align-self:flex-start;border-bottom-left-radius:4px}
  .msg.user{background:var(--brand);color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
  .chips{display:flex;gap:8px;flex-wrap:wrap;padding:0 16px 8px}
  .chip{background:var(--brand-soft);color:var(--brand);border:1px solid var(--brand-line);
        border-radius:15px;padding:5px 11px;font-size:12px;cursor:pointer}
  .chip:hover{background:#dcefe2}
  .inputbar{display:flex;gap:8px;padding:12px 16px;border-top:1px solid var(--border);background:var(--panel)}
  .inputbar input{flex:1;padding:10px 13px;border:1px solid var(--border);border-radius:9px;font-size:14px;outline:none}
  .inputbar input:focus{border-color:var(--brand)}
  .inputbar button{background:var(--brand);color:#fff;border:none;border-radius:9px;padding:0 18px;height:38px;font-size:14px;cursor:pointer}
  .side{width:500px;border-left:1px solid var(--border);background:var(--panel);overflow-y:auto;padding:12px 14px 24px}
  .tabs{display:flex;gap:4px;margin-bottom:10px;border-bottom:1px solid var(--border)}
  .tab{padding:7px 12px;font-size:13px;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
  .tab.active{color:var(--brand);font-weight:600;border-bottom-color:var(--brand)}
  .pane{display:none}.pane.active{display:block}
  .summary{border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:10px;background:#fbfcfd}
  .sum-name{font-weight:700;font-size:15px;margin-bottom:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .badge{font-size:11px;font-weight:400;color:var(--brand);background:var(--brand-soft);border-radius:10px;padding:2px 8px}
  .badge.grey{color:var(--muted);background:#f1f2f4}
  .sum-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px}
  .sum-grid div{display:flex;justify-content:space-between;font-size:12px}
  .sum-grid span{color:var(--muted)}.sum-grid b{color:var(--ink)}
  .prov{font-size:10.5px;color:var(--muted);margin-top:8px;line-height:1.45}
  .sect-title{font-size:13px;font-weight:600;margin:14px 0 6px;display:flex;justify-content:space-between;gap:8px}
  .sect-title .hintline{font-size:10.5px;font-weight:400;color:var(--muted)}
  .scroll{max-height:268px;overflow-y:auto;border:1px solid var(--border);border-radius:8px}
  .kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}
  .kpi{border:1px solid var(--border);border-radius:10px;padding:9px 11px;background:#fbfcfd}
  .kpi .k{font-size:11px;color:var(--muted)}
  .kpi .v{font-size:19px;font-weight:700;margin-top:2px;font-variant-numeric:tabular-nums}
  .kpi .v .u{font-size:11px;font-weight:400;color:var(--muted);margin-left:3px}
  .kpi .n{font-size:10.5px;color:var(--muted);margin-top:3px;line-height:1.45}
  table{width:100%;border-collapse:collapse;font-size:12px}
  th,td{border-bottom:1px solid var(--border);padding:5px 6px;text-align:left;white-space:nowrap}
  th{background:var(--brand-soft);color:var(--brand);font-weight:600;position:sticky;top:0;z-index:1}
  tbody tr.row{cursor:pointer}tbody tr.row:hover{background:#f2f8f4}
  td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
  tr.hi{background:#f0f8f3}
  td.empty{color:var(--muted);text-align:center;padding:14px 0}
  .barwrap{display:flex;align-items:center;gap:6px}
  .bartrack{flex:1;height:7px;background:#eef1f4;border-radius:4px;overflow:hidden;min-width:40px}
  .barfill{height:100%;background:var(--bar);border-radius:4px}
  .barval{font-size:11px;color:var(--muted);width:46px;text-align:right}
  .chart{border:1px solid var(--border);border-radius:8px;padding:8px 10px;margin-bottom:8px}
  .chart .rowc{display:grid;grid-template-columns:40px 1fr 56px;align-items:center;gap:6px;margin:3px 0;font-size:11px}
  .chart .lbl{color:var(--muted)}
  .chart .track{height:12px;background:#eef1f4;border-radius:3px;overflow:hidden}
  .chart .fill{height:100%;background:var(--bar);border-radius:3px}
  .chart .val{text-align:right}
  .yearbar{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:12px;color:var(--muted);flex-wrap:wrap}
  .yearbar select{padding:4px 8px;border:1px solid var(--border);border-radius:6px;font-size:12.5px;color:var(--ink);background:#fff}
  .notice{background:var(--warn-bg);border:1px solid var(--warn-line);color:var(--warn-ink);
          border-radius:8px;padding:7px 10px;font-size:11px;line-height:1.5;margin-bottom:10px}
  .actions{display:flex;gap:8px;margin:10px 0 4px}
  .actions button{flex:1;height:34px;border-radius:8px;font-size:13px;cursor:pointer;
                  border:1px solid var(--border);background:#fff;color:var(--ink)}
  .actions #csvBtn{background:var(--brand);color:#fff;border-color:var(--brand)}
  details.standards{margin-top:14px;border-top:1px dashed var(--border);padding-top:8px}
  details.standards summary{font-size:12px;color:var(--muted);cursor:pointer}
  .std-cat{border:1px solid var(--border);border-radius:8px;padding:7px 9px;margin-top:6px;font-size:11px}
  .std-cat .nm{font-weight:600;font-size:12px}
  .std-cat .ex,.std-cat .nt{color:var(--muted);margin-top:2px}
  @media (max-width:980px){.side{display:none}}
</style>
</head>
<body>
<header>🪨 废纸回收 Agent 对话助手
  <span class="sub">v__VERSION__ · 全国+省级 · 历年 · 八大类 · 企业分布 · CSV 导出</span>
  <span class="off">离线单文件版 · 不需要联网</span>
</header>
<div class="layout">
  <div class="chat">
    <div class="messages" id="messages"></div>
    <div class="chips" id="chips"></div>
    <div class="inputbar">
      <input id="input" placeholder="输入：纸箱 2kg / 山东省回收量 / 2020年分类数据 / 企业名录"
             onkeydown="if(event.key==='Enter')send()" />
      <button onclick="send()">发送</button>
    </div>
  </div>
  <aside class="side">
    <div class="tabs">
      <div class="tab active" data-pane="region" onclick="switchTab('region')">区域统计</div>
      <div class="tab" data-pane="history" onclick="switchTab('history')">历年数据</div>
      <div class="tab" data-pane="category" onclick="switchTab('category')">分类结构</div>
      <div class="tab" data-pane="enterprise" onclick="switchTab('enterprise')">企业分布</div>
      <div class="tab" data-pane="io" onclick="switchTab('io')">投入产出</div>
    </div>

    <section class="pane active" id="pane-region">
      <div class="crumb" id="crumb" style="font-size:12.5px;margin-bottom:8px;color:var(--brand);cursor:pointer"></div>
      <div class="summary" id="summary"></div>
      <div class="notice">只提供<b>全国</b>与<b>省级</b>两级统计。市级、县级无公开权威数据，故不提供。
        山东、广东为公开报道值，其余省份为梯队测算（表中标注）。</div>
      <div class="sect-title"><span>省级回收量排名（2024 年）</span><span class="hintline">点击行查看该省</span></div>
      <div class="scroll">
        <table id="provTable"><thead><tr>
          <th class="num">#</th><th>区域</th><th class="num">回收量(万吨)</th>
          <th class="num">占比(%)</th><th>数据</th></tr></thead><tbody></tbody></table>
      </div>
      <div class="actions">
        <button onclick="goNational()">返回全国</button>
        <button id="csvBtn" onclick="exportCSV()">导出 CSV</button>
      </div>
    </section>

    <section class="pane" id="pane-history">
      <div class="yearbar"><span>数据年份</span><select id="yearSel" onchange="changeYear(this.value)"></select></div>
      <div class="sect-title"><span>回收量走势（万吨）</span><span class="hintline" id="histScope"></span></div>
      <div class="chart" id="histChart"></div>
      <div class="sect-title"><span>历年明细</span><span class="hintline">中国造纸协会年度报告</span></div>
      <div class="scroll"><table id="histTable"><thead><tr>
        <th class="num">年份</th><th class="num">回收量</th><th class="num">同比</th>
        <th class="num">回收率</th><th class="num">利用率</th><th class="num">进口量</th>
        </tr></thead><tbody></tbody></table></div>
      <div class="sect-title"><span>废纸进口量（万吨）</span><span class="hintline">2021 年禁废令后清零</span></div>
      <div class="chart" id="impChart"></div>
    </section>

    <section class="pane" id="pane-category">
      <div class="yearbar"><span>数据年份</span><select id="yearSel2" onchange="changeYear(this.value)"></select>
        <span id="catScope"></span></div>
      <div class="notice">官方<b>未逐类公布</b>回收量。下表为「行业结构占比 × 当年回收量」估算，
        占比按 2015/2020/2025 三锚点插值，货值按参考价估算。</div>
      <div class="sect-title"><span>八大类回收量（GB/T 20811-2018）</span><span class="hintline" id="catTotal"></span></div>
      <div class="chart" id="catChart"></div>
      <div class="scroll" style="max-height:320px"><table id="catTable"><thead><tr>
        <th class="num">代码</th><th>类别</th><th class="num">占比</th>
        <th class="num">回收量(万吨)</th><th class="num">货值(亿元)</th>
        </tr></thead><tbody></tbody></table></div>
      <details class="standards"><summary>内部参考：GB/T 20811-2018 分类技术要求</summary>
        <div id="standardsBody"></div></details>
    </section>

    <section class="pane" id="pane-enterprise">
      <div class="yearbar"><span>省份</span><select id="entProv" onchange="renderEnt()"></select>
        <span>大类</span><select id="entCat" onchange="renderEnt()"></select>
        <span>类型</span><select id="entType" onchange="renderEnt()"></select></div>
      <div class="notice" id="entNotice"></div>
      <div class="sect-title"><span>企业地理分布（示意图）</span><span class="hintline" id="entTotal"></span></div>
      <div class="chart" style="padding:4px"><svg id="entMap" viewBox="0 0 480 300"
        style="width:100%;height:300px;display:block"></svg></div>
      <div class="sect-title"><span>按类型</span><span class="hintline">家数 / 万吨</span></div>
      <div class="chart" id="entTypeChart"></div>
      <div class="sect-title"><span>企业明细</span><span class="hintline">按年回收量降序</span></div>
      <div class="scroll" style="max-height:260px"><table id="entTable"><thead><tr>
        <th>企业</th><th>城市</th><th>类型</th><th class="num">年回收量(万吨)</th><th>主营</th>
        </tr></thead><tbody></tbody></table></div>
    </section>

    <section class="pane" id="pane-io">
      <div class="kpis" id="ioKpis"></div>
      <div class="notice" id="ioNotice"></div>
      <div class="sect-title"><span>分省消耗金额（亿元）</span>
        <span class="hintline">按回收量占比分摊</span></div>
      <div class="scroll" style="max-height:300px"><table id="ioTable"><thead><tr>
        <th class="num">#</th><th>省份</th><th class="num">占比(%)</th>
        <th class="num">金额(亿元)</th><th>口径</th>
        </tr></thead><tbody></tbody></table></div>
      <div class="notice" style="margin-top:8px">
        <b>地图</b>与<b>模型配置</b>需要本地服务版：双击「启动本地版.bat」后访问
        <code>http://localhost:8000</code>。离线版不含这两项（地图需正版底图密钥，
        模型配置需服务端保存密钥）。
      </div>
    </section>
  </aside>
</div>

<script>
const D = __DATA_JSON__;
const S = { code: "CN", year: D.national_year };

/* ---------- 通用 ---------- */
const $ = id => document.getElementById(id);
function addMsg(text, who) {
  const d = document.createElement("div");
  d.className = "msg " + who;
  d.textContent = text;
  $("messages").appendChild(d);
  $("messages").scrollTop = $("messages").scrollHeight;
}
["纸箱能回收吗","办公用纸 3kg","山东省回收量","历年数据","分类回收数据","企业名录"].forEach(s => {
  const c = document.createElement("span");
  c.className = "chip"; c.textContent = s;
  c.onclick = () => { $("input").value = s; send(); };
  $("chips").appendChild(c);
});
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.pane === name));
  document.querySelectorAll(".pane").forEach(p => p.classList.toggle("active", p.id === "pane-" + name));
  if (name === "enterprise") renderEnt();
  if (name === "io") renderIO();
}

/* ---------- 投入产出 ---------- */
function ioNum(n, d) {
  if (n === null || n === undefined || n === "") return "—";
  const v = Number(n);
  if (!isFinite(v)) return "—";
  return v.toLocaleString("zh-CN", {minimumFractionDigits: d || 0, maximumFractionDigits: d || 0});
}

function renderIO() {
  const io = D.io;
  const s = io.spend, dc = io.direct, uc = io.unit;
  $("ioKpis").innerHTML = [
    ["废纸消耗金额", ioNum(s.amount, 1), "亿元", s.provenance + "；按回收参考价计，属纸厂成本下限"],
    ["直接消耗系数", dc.coefficient === null ? "—" : ioNum(dc.coefficient_pct, 2), "%",
      dc.coefficient === null ? "该年营收无公开值" : "货值 " + ioNum(dc.spend, 1) + " 亿 ÷ 营收 " + ioNum(dc.revenue, 0) + " 亿"],
    ["单位产值消耗", uc.value === null ? "—" : ioNum(uc.value, 3), "吨/万元", "消耗量 ÷ 营业收入"],
    ["加权参考价", ioNum(s.avg_price, 0), "元/吨", "分类结构加权，居民 / 回收站口径"]
  ].map(([k, v, u, n]) =>
    '<div class="kpi"><div class="k">' + k + '</div><div class="v">' + v +
    '<span class="u">' + u + '</span></div><div class="n">' + n + '</div></div>'
  ).join("");

  $("ioNotice").innerHTML =
    "<b>口径分级</b>：" + io.levels.map(l =>
      l.name + "（" + (l.io_available ? "有官方表" : "无官方表") + "，" + l.provenance + "）"
    ).join("　") +
    "。国家统计局明确「地级市暂不编制投入产出表」，企业只有财务报表——这两级的金额都是分摊估算。";

  document.querySelector("#ioTable tbody").innerHTML = io.provinces.rows.map(r =>
    '<tr><td class="num">' + r.rank + '</td><td>' + r.name + '</td><td class="num">' +
    r.share_pct + '</td><td class="num">' + ioNum(r.amount, 1) + '</td><td>' + r.provenance + '</td></tr>'
  ).join("");
}

/* ---------- 区域 ---------- */
function provByCode(code) { return D.provinces.find(p => p.code === code) || null; }
function share(code) { const p = provByCode(code); return p ? p.stats["回收量(万吨)"] / D.national.stats["回收量(万吨)"] : 1; }

function renderRegion(code) {
  S.code = code;
  const p = provByCode(code);
  const node = p || D.national;
  const s = node.stats;
  $("crumb").innerHTML = p
    ? `<span onclick="renderRegion('CN')">全国</span> / ${p.name}`
    : `全国`;
  const isN = !p;
  const badge = isN ? `<span class="badge">国家</span>`
                    : `<span class="badge">省</span><span class="badge grey">${p.tier}</span>`;
  const extra = isN
    ? `<div><span>纸及纸板产量</span><b>${s["纸及纸板产量(万吨)"]} 万吨</b></div>
       <div><span>从业人员</span><b>${s["从业人员(人)"]} 人</b></div>`
    : `<div><span>占全国比重</span><b>${s["占全国比重(%)"]}%</b></div>
       <div><span>全国排名</span><b>第 ${p.rank} 位</b></div>`;
  $("summary").innerHTML =
    `<div class="sum-name">${node.name} ${badge}</div>
     <div class="sum-grid">
       <div><span>回收量</span><b>${s["回收量(万吨)"]} 万吨</b></div>
       <div><span>回收率</span><b>${s["回收率(%)"]}%</b></div>
       <div><span>利用率</span><b>${s["利用率(%)"]}%</b></div>
       <div><span>企业数</span><b>${s["回收企业数(家)"]} 家</b></div>
       ${extra}
     </div>
     <div class="prov">数据年度 ${D.national.year} 年 · ${isN ? D.national.provenance : (p.quality === "reported" ? "回收量为公开报道值，其余测算" : "梯队测算，非官方逐省统计")}</div>`;

  const max = Math.max(...D.provinces.map(x => x.stats["回收量(万吨)"]));
  document.querySelector("#provTable tbody").innerHTML = D.provinces.map(x =>
    `<tr class="row${x.code === code ? " hi" : ""}" onclick="renderRegion('${x.code}')">
       <td class="num">${x.rank}</td><td>${x.name}</td>
       <td class="num"><div class="barwrap"><div class="bartrack">
         <div class="barfill" style="width:${(x.stats["回收量(万吨)"]/max*100).toFixed(1)}%"></div></div>
         <div class="barval">${x.stats["回收量(万吨)"]}</div></div></td>
       <td class="num">${x.stats["占全国比重(%)"]}</td>
       <td>${x.quality === "reported" ? "报道" : "测算"}</td></tr>`).join("");
  renderHistory(); renderCategory();
}
function goNational() { renderRegion("CN"); }

/* ---------- 历年 ---------- */
function renderHistory() {
  const k = share(S.code);
  const rows = D.history.filter(h => h.recovery !== null)
    .map(h => ({ ...h, recovery: +(h.recovery * k).toFixed(1) }));
  const max = Math.max(...rows.map(h => h.recovery));
  $("histScope").textContent = S.code === "CN" ? "全国" : "按该省占比折算";
  $("histChart").innerHTML = rows.map(h =>
    `<div class="rowc"><div class="lbl">${h.year}</div>
      <div class="track"><div class="fill" style="width:${(h.recovery/max*100).toFixed(1)}%"></div></div>
      <div class="val">${h.recovery}</div></div>`).join("");

  document.querySelector("#histTable tbody").innerHTML = D.history.map(h => {
    const yoy = h.yoy === null ? "—" : (h.yoy > 0 ? "+" : "") + h.yoy + "%";
    const rec = h.recovery === null ? "—" : +(h.recovery * k).toFixed(1);
    const util = h.utilization === null ? "—" : h.utilization + "%";
    const imp = h.import === null || h.import === undefined ? "—" : h.import;
    return `<tr><td class="num">${h.year}</td><td class="num">${rec}</td>
      <td class="num">${yoy}</td><td class="num">${h.recovery_rate}%</td>
      <td class="num">${util}</td><td class="num">${imp}</td></tr>`;
  }).join("");

  const imax = Math.max(...D.imports.map(r => r.value)) || 1;
  $("impChart").innerHTML = D.imports.map(r =>
    `<div class="rowc"><div class="lbl">${r.year}</div>
      <div class="track"><div class="fill" style="width:${(r.value/imax*100).toFixed(1)}%;background:var(--bar2)"></div></div>
      <div class="val">${r.value}</div></div>`).join("");
}

/* ---------- 分类 ---------- */
function catRows(year) {
  const k = share(S.code);
  const total = (D.history.find(h => h.year === year) || {}).recovery || 0;
  const base = total * k;
  const shares = D.shares[year] || D.shares[D.latest_year];
  return Object.keys(D.catmeta).sort().map(code => {
    const m = D.catmeta[code];
    const sh = shares[code];
    const t = +(base * sh / 100).toFixed(1);
    return { code, name: m.name, share: sh, tonnage: t, price: m.price,
             value: +(t * m.price * 0.1).toFixed(1), use: m.use };
  });
}
function renderCategory() {
  const rows = catRows(S.year);
  const total = rows.reduce((s, r) => s + r.tonnage, 0);
  const max = Math.max(...rows.map(r => r.share));
  $("catScope").textContent = S.code === "CN" ? "全国" : provByCode(S.code).name;
  $("catTotal").textContent = `合计 ${total.toFixed(1)} 万吨`;
  $("catChart").innerHTML = rows.map(r =>
    `<div class="rowc" style="grid-template-columns:118px 1fr 62px">
      <div class="lbl">${r.name}</div>
      <div class="track"><div class="fill" style="width:${(r.share/max*100).toFixed(1)}%"></div></div>
      <div class="val">${r.share}%</div></div>`).join("");
  document.querySelector("#catTable tbody").innerHTML = rows.map(r =>
    `<tr title="${r.use}"><td class="num">${r.code}</td><td>${r.name}</td>
      <td class="num">${r.share}%</td><td class="num">${r.tonnage}</td>
      <td class="num">${r.value}</td></tr>`).join("");
}
function changeYear(y) {
  S.year = parseInt(y, 10);
  $("yearSel").value = S.year; $("yearSel2").value = S.year;
  renderCategory();
}

/* ---------- 企业 ---------- */
const ENT_COLORS = {"回收站点":"#8fbfa3","分拣打包中心":"#4a9d6b","造纸企业":"#1f5c3a","贸易商":"#b7a06a"};
function initEnt() {
  $("entProv").innerHTML = `<option value="">全部省份</option>` +
    D.provinces.map(p => `<option value="${p.code}">${p.name}</option>`).join("");
  $("entCat").innerHTML = `<option value="">全部大类</option>` +
    Object.keys(D.catmeta).sort().map(c => `<option value="${c}">${c} ${D.catmeta[c].name}</option>`).join("");
  $("entType").innerHTML = `<option value="">全部类型</option>` +
    D.ent_types.map(t => `<option value="${t}">${t}</option>`).join("");
  $("entNotice").innerHTML = D.ent_is_demo
    ? `当前为<b>示例企业名录</b>（名称为虚构），用于演示「企业 × 地理位置 × 品类」分析。`
    : `当前为<b>自有企业名录</b>。`;
}
function entList() {
  const p = $("entProv").value, c = $("entCat").value, t = $("entType").value;
  return D.enterprises.filter(e =>
    (!p || e.province_code === p) && (!c || e.categories.includes(c)) && (!t || e.type === t)
  ).sort((a, b) => b.volume - a.volume);
}
function renderEnt() {
  const list = entList();
  const X = lon => 22 + (lon - 73) / (135 - 73) * 436;
  const Y = lat => 14 + (54 - lat) / (54 - 18) * 272;
  const svg = $("entMap");
  if (!list.length) {
    svg.innerHTML = `<text x="240" y="150" text-anchor="middle" fill="#6b7280" font-size="12">当前筛选没有企业</text>`;
  } else {
    const mv = Math.max(...list.map(e => e.volume));
    let out = `<rect x="1" y="1" width="478" height="298" fill="#fbfcfd" stroke="#e5e7eb" rx="6"/>`;
    for (let lon = 80; lon <= 130; lon += 10) {
      out += `<line x1="${X(lon)}" y1="14" x2="${X(lon)}" y2="286" stroke="#eef1f4"/>`
           + `<text x="${X(lon)}" y="296" font-size="9" fill="#9aa3af" text-anchor="middle">${lon}°E</text>`;
    }
    for (let lat = 20; lat <= 50; lat += 10) {
      out += `<line x1="22" y1="${Y(lat)}" x2="458" y2="${Y(lat)}" stroke="#eef1f4"/>`
           + `<text x="2" y="${Y(lat)+3}" font-size="9" fill="#9aa3af">${lat}°N</text>`;
    }
    list.forEach(e => {
      const r = (3 + Math.sqrt(e.volume / mv) * 9).toFixed(1);
      out += `<circle cx="${X(e.lon).toFixed(1)}" cy="${Y(e.lat).toFixed(1)}" r="${r}"
        fill="${ENT_COLORS[e.type] || "#4a9d6b"}" fill-opacity="0.72" stroke="#fff" stroke-width="1">
        <title>${e.name}\n${e.city} · ${e.type}\n年回收量 ${e.volume} 万吨\n主营 ${e.category_names.join("、")}</title></circle>`;
    });
    let lx = 30;
    Object.keys(ENT_COLORS).forEach(t => {
      out += `<circle cx="${lx}" cy="10" r="3.5" fill="${ENT_COLORS[t]}"/>`
           + `<text x="${lx+7}" y="13" font-size="9" fill="#6b7280">${t}</text>`;
      lx += 78;
    });
    svg.innerHTML = out;
  }

  const byType = {};
  D.ent_types.forEach(t => byType[t] = { count: 0, volume: 0 });
  list.forEach(e => { byType[e.type].count++; byType[e.type].volume += e.volume; });
  const tv = Math.max(...Object.values(byType).map(v => v.volume), 1);
  $("entTypeChart").innerHTML = Object.keys(byType).filter(t => byType[t].count).map(t =>
    `<div class="rowc" style="grid-template-columns:96px 1fr 74px">
      <div class="lbl">${t}</div>
      <div class="track"><div class="fill" style="width:${(byType[t].volume/tv*100).toFixed(1)}%;background:${ENT_COLORS[t]}"></div></div>
      <div class="val">${byType[t].count}家 / ${byType[t].volume.toFixed(1)}</div></div>`).join("");

  $("entTotal").textContent = `${list.length} 家 · 合计 ${list.reduce((s,e)=>s+e.volume,0).toFixed(1)} 万吨`;
  document.querySelector("#entTable tbody").innerHTML = list.length
    ? list.map(e => `<tr title="${e.note}"><td>${e.name}</td><td>${e.city}</td><td>${e.type}</td>
        <td class="num">${e.volume}</td><td>${e.category_names.join("、")}</td></tr>`).join("")
    : `<tr><td colspan="5" class="empty">当前筛选没有企业</td></tr>`;
}

/* ---------- 对话（离线规则引擎，与 Python 版同序） ---------- */
function findProv(text) {
  if (/全国|中国|国家/.test(text)) return "CN";
  const hits = D.provinces.filter(p => text.indexOf(p.name) >= 0);
  if (hits.length) return hits[0].code;
  const shorts = D.provinces.filter(p => {
    const s = p.name.replace(/^(中国)?/, "").replace(/(壮族|回族|维吾尔)?自治区$|特别行政区$|省$|市$/, "");
    return s.length >= 2 && text.indexOf(s) >= 0;
  });
  return shorts.length ? shorts[0].code : null;
}
function findEnt(text) {
  const generic = ["废纸","回收","废纸回收","回收站","公司","企业","造纸","纸厂","中心","站点","分拣","打包"];
  if (text.length < 3 || generic.indexOf(text) >= 0) return null;
  return D.enterprises.find(e => e.name.indexOf(text) >= 0) || null;
}
function catSummary(year) {
  const rows = catRows(year);
  const lines = [`【${year} 年废纸回收量按类别拆分（GB/T 20811-2018 八大类）】`,
                 "说明：官方未逐类公布回收量，下表为「行业结构占比 × 官方回收量」估算。"];
  rows.forEach(r => lines.push(`- ${r.code} ${r.name}：${r.share}%，约 ${r.tonnage} 万吨，参考价 ${r.price} 元/公斤`));
  return lines.join("\n");
}
function historySummary() {
  const lines = ["【历年废纸回收利用（中国造纸协会年度报告）】",
                 "年份　回收量(万吨)　回收率(%)　利用率(%)　废纸进口(万吨)"];
  D.history.forEach(h => lines.push(
    `${h.year}　${h.recovery}　${h.recovery_rate}　${h.utilization === null ? "—" : h.utilization}　${h.import === null || h.import === undefined ? "—" : h.import}`));
  const a = D.history[0], b = D.history[D.history.length - 1];
  lines.push(`趋势：${a.year}—${b.year} 回收量从 ${a.recovery} 万吨增至 ${b.recovery} 万吨；废纸进口自 2021 年禁废令后清零。`);
  return lines.join("\n");
}
function entSummary(code) {
  const list = code ? D.enterprises.filter(e => e.province_code === code) : D.enterprises;
  if (!list.length) return "暂无企业名录数据。";
  const name = code ? provByCode(code).name : "全国";
  const tv = list.reduce((s, e) => s + e.volume, 0);
  const lines = [`【${name}回收企业概览】`];
  if (D.ent_is_demo) lines.push("注：以下为示例企业名录（虚构名称），用于演示企业维度。");
  lines.push(`- 收录企业 ${list.length} 家，年回收量合计 ${tv.toFixed(1)} 万吨`);
  if (code) {
    const official = provByCode(code).stats["回收量(万吨)"];
    lines.push(`- 占该省官方回收量（${official} 万吨）的 ${(tv / official * 100).toFixed(1)}%（名录覆盖率）`);
  }
  lines.push("", "按类型：");
  const bt = {};
  list.forEach(e => { bt[e.type] = bt[e.type] || { c: 0, v: 0 }; bt[e.type].c++; bt[e.type].v += e.volume; });
  Object.keys(bt).forEach(t => lines.push(`- ${t}：${bt[t].c} 家，${bt[t].v.toFixed(1)} 万吨`));
  lines.push("", "年回收量前五：");
  list.slice().sort((a, b) => b.volume - a.volume).slice(0, 5).forEach(e =>
    lines.push(`  ${e.name}（${e.city}·${e.type}）${e.volume} 万吨，主营 ${e.category_names.join("、")}`));
  return lines.join("\n");
}
function classify(text) {
  const low = text.toLowerCase();
  let hit = null;
  D.knowledge.forEach(k => {
    if (hit) return;
    if (k.aliases.some(a => low.indexOf(a) >= 0) || low.indexOf(k.name) >= 0) hit = k;
  });
  if (!hit) return "未能识别废纸类型，请描述更具体的物品（如：纸箱、报纸、纸巾、热敏小票）。";
  return hit.recyclable
    ? `【${hit.name}】可回收，参考回收价 ${hit.price} 元/公斤。\n提示：${hit.tips}`
    : `【${hit.name}】不可回收。\n原因：${hit.tips}`;
}
function priceOf(text, kg) {
  const low = text.toLowerCase();
  const hit = D.knowledge.find(k => k.aliases.some(a => low.indexOf(a) >= 0) || low.indexOf(k.name) >= 0);
  if (!hit) return "未能识别废纸类型，请描述更具体的物品（如：纸箱、报纸）。";
  if (!hit.recyclable) return `【${hit.name}】不可回收，回收价值为 0。\n原因：${hit.tips}`;
  const val = (hit.price * Math.max(kg, 0)).toFixed(2);
  return `【${hit.name}】${kg} 公斤，参考回收价值约 ${val} 元（按 ${hit.price} 元/公斤估算）。\n提示：${hit.tips}`;
}
function respond(text) {
  if (!text) return "请输入你想查询的废纸物品，例如「纸箱 2kg 能卖多少钱」。";
  if (["你好","您好","hi","hello","在吗","在么"].indexOf(text.toLowerCase()) >= 0)
    return "你好，我是废纸回收助手 🪨。可以问我：能不能回收、值多少钱、全国/各省回收量、历年趋势、八大类分类、某省企业。";
  if (/帮助|help|怎么用|功能|能做什么|用法/.test(text)) {
    return ["废纸回收助手使用说明：",
      "1) 是否可回收：直接说物品名，如「纸箱」「纸巾」。",
      "2) 估算价值：物品名 + 重量，如「办公用纸 3kg」「纸箱 5 斤」。",
      "3) 分类标准：输入「废纸分类」。",
      "4) 按类别看回收量：输入「分类回收数据」「2020 年分类数据」。",
      "5) 历年趋势：输入「历年数据」。",
      "6) 区域统计（全国与省级）：输入「山东省回收量」。",
      "7) 企业分布：输入「企业名录」「山东有哪些回收企业」。",
      "8) 导出：右侧「导出 CSV」。离线版不支持 xlsx，在线版可导出六表 Excel。"].join("\n");
  }
  const ent = findEnt(text);
  if (ent) {
    return [`【${ent.name}】`, `- 位置：${ent.city}（${ent.lat}, ${ent.lon}）`,
      `- 类型：${ent.type}`, `- 主营：${ent.category_names.join("、")}`,
      `- 年回收量：${ent.volume} 万吨`, `- 备注：${ent.note}`,
      D.ent_is_demo ? "（示例数据）" : ""].filter(Boolean).join("\n");
  }
  if (/企业|公司|回收站|回收点|打包厂|分拣中心|造纸厂|贸易商|名录|哪家|厂家/.test(text)) {
    return entSummary(findProv(text));
  }
  if (/分类数据|分类回收|类别占比|各类回收|八大类|按类别|分类占比|品种结构/.test(text)) {
    const m = text.match(/(20\d{2})/);
    const y = m && D.years.indexOf(parseInt(m[1], 10)) >= 0 ? parseInt(m[1], 10) : D.latest_year;
    return catSummary(y);
  }
  if (/历年|年份|以前|过去|趋势|增长|变化|这几年|近五年|历史数据/.test(text)) return historySummary();
  if (/年鉴|行业数据|进口|标准|分类标准|gb\/t|20811|造纸|废纸分几类|废纸分类/.test(text)) {
    const lines = ["【废纸分类（GB/T 20811-2018，8 大类 42 小类）】"];
    D.gbt.forEach(c => lines.push(`${c.code}. ${c.name}：${c.examples.join("、")}`));
    lines.push("", "【2024 年废纸回收利用】", "回收量 6971 万吨、回收率 51.1%、利用率 51.6%。");
    return lines.join("\n");
  }
  if (/回收量|利用率|回收率|统计|企业数|从业人员|数据|排名|占比/.test(text)) {
    const code = findProv(text) || "CN";
    const p = provByCode(code);
    if (!p) return regionText("CN");
    return regionText(code);
  }
  const code = findProv(text);
  if (code && code !== "CN") return regionText(code);
  const m = text.match(/(\d+(?:\.\d+)?)\s*(kg|公斤|千克|斤)/i);
  if (m) {
    let kg = parseFloat(m[1]);
    if (m[2] === "斤") kg = kg / 2;
    return priceOf(text, kg);
  }
  return classify(text);
}
function regionText(code) {
  const p = provByCode(code);
  if (!p) {
    const n = D.national;
    const top = D.provinces.slice(0, 5).map(x => `  ${x.rank}. ${x.name} ${x.stats["回收量(万吨)"]} 万吨（占全国 ${x.stats["占全国比重(%)"]}%）`);
    return [`【全国】废纸回收统计（${n.year} 年，官方）`,
      `- 回收量：${n.stats["回收量(万吨)"]} 万吨`,
      `- 回收率：${n.stats["回收率(%)"]}%；利用率：${n.stats["利用率(%)"]}%`,
      `- 纸及纸板产量：${n.stats["纸及纸板产量(万吨)"]} 万吨`,
      "回收量前五：", ...top, "", "注：本工具仅提供全国与省级两级统计。"].join("\n");
  }
  const s = p.stats;
  return [`【${p.name}】废纸回收统计（${D.national.year} 年，${p.quality === "reported" ? "回收量为公开报道值" : "梯队测算"}）`,
    `- 回收量：${s["回收量(万吨)"]} 万吨（占全国 ${s["占全国比重(%)"]}%，第 ${p.rank} 位）`,
    `- 回收率：${s["回收率(%)"]}%；利用率：${s["利用率(%)"]}%`,
    `- 纸及纸板产量：${s["纸及纸板产量(万吨)"]} 万吨`,
    `- 回收企业数：${s["回收企业数(家)"]} 家；从业人员：${s["从业人员(人)"]} 人`,
    `- 梯队：${p.tier}`, "", "注：本工具仅提供全国与省级两级统计。"].join("\n");
}
function send() {
  const el = $("input");
  const text = el.value.trim();
  if (!text) return;
  addMsg(text, "user");
  el.value = "";
  addMsg(respond(text), "bot");
}

/* ---------- CSV 导出 ---------- */
function exportCSV() {
  const lines = [];
  const push = arr => lines.push(arr.map(v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`).join(","));
  push(["废纸回收统计（离线版）"]);
  push(["全国", D.national.year, "回收量(万吨)", D.national.stats["回收量(万吨)"],
        "回收率(%)", D.national.stats["回收率(%)"], "利用率(%)", D.national.stats["利用率(%)"]]);
  push([]);
  push(["一、省级统计（2024 年）"]);
  push(["排名","区域","梯队","回收量(万吨)","占全国比重(%)","回收率(%)","利用率(%)","数据性质"]);
  D.provinces.forEach(p => push([p.rank, p.name, p.tier, p.stats["回收量(万吨)"],
    p.stats["占全国比重(%)"], p.stats["回收率(%)"], p.stats["利用率(%)"],
    p.quality === "reported" ? "公开报道" : "梯队测算"]));
  push([]);
  push([`二、分类回收（${S.year} 年，${S.code === "CN" ? "全国" : provByCode(S.code).name}）`]);
  push(["代码","类别","占比(%)","回收量(万吨)","参考价(元/公斤)","估算货值(亿元)"]);
  catRows(S.year).forEach(r => push([r.code, r.name, r.share, r.tonnage, r.price, r.value]));
  push([]);
  push(["三、历年回收"]);
  push(["年份","回收量(万吨)","回收率(%)","利用率(%)","废纸进口(万吨)"]);
  D.history.forEach(h => push([h.year, h.recovery, h.recovery_rate,
    h.utilization === null ? "—" : h.utilization,
    h.import === null || h.import === undefined ? "—" : h.import]));
  push([]);
  push(["四、企业名录" + (D.ent_is_demo ? "（示例数据）" : "")]);
  push(["企业名称","城市","类型","主营大类","年回收量(万吨)","纬度","经度","备注"]);
  entList().forEach(e => push([e.name, e.city, e.type, e.category_names.join("、"),
    e.volume, e.lat, e.lon, e.note]));

  const csv = "\uFEFF" + lines.join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `废纸回收统计_${S.code === "CN" ? "全国" : provByCode(S.code).name}_${S.year}.csv`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 3000);
}

/* ---------- 初始化 ---------- */
(function init() {
  $("yearSel").innerHTML = D.years.map(y => `<option value="${y}"${y === D.national_year ? " selected" : ""}>${y} 年</option>`).join("");
  $("yearSel2").innerHTML = $("yearSel").innerHTML;
  $("standardsBody").innerHTML = D.gbt.map(c =>
    `<div class="std-cat"><div class="nm">${c.code}. ${c.name}</div>
     <div class="ex">${c.examples.join("、")}</div><div class="nt">${c.note}</div></div>`).join("");
  initEnt();
  renderRegion("CN");
  renderEnt();
  addMsg("你好，我是废纸回收助手 🪨（离线版，不联网）。\n"
    + "可以问我：能不能回收、值多少钱、各省回收量、历年趋势、八大类分类、某省有哪些企业。\n"
    + "右侧四个标签页：区域统计 / 历年数据 / 分类结构 / 企业分布。", "bot");
})();
</script>
</body>
</html>
"""


def main() -> int:
    payload = build_payload()
    html = TEMPLATE.replace("__VERSION__", payload["version"])
    html = html.replace("__DATA_JSON__", json.dumps(payload, ensure_ascii=False))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"已生成 {OUT.relative_to(ROOT)}（{OUT.stat().st_size} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
