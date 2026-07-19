"""Reads _data.js, appends SSR data from SQLite, and inlines into dashboard HTML."""
import os, sqlite3, json

base = os.path.dirname(os.path.abspath(__file__))
data_js   = open(os.path.join(base, '_data.js')).read()
out_path  = os.path.join(base, 'staff_dashboard.html')

# ── Pull student-staff ratio data from SQLite ────────────────────────────────
conn = sqlite3.connect(os.path.join(base, 'staff_data.db'))
ssr_rows = conn.execute(
    'SELECT institution, year, academic_ratio FROM student_staff_ratio ORDER BY institution, year'
).fetchall()
conn.close()

SSR_YEARS = list(range(2014, 2024))   # 2014-2023

ssr_dict = {}   # institution -> {year_str -> ratio}
for inst, yr, ratio in ssr_rows:
    if ratio is None:
        continue
    ssr_dict.setdefault(inst, {})[str(yr)] = round(ratio, 2)

data_js += '\nconst SSR_YEARS=' + json.dumps(SSR_YEARS) + ';\n'
data_js += 'const SSR_DATA='   + json.dumps(ssr_dict,  separators=(',',':')) + ';\n'
# ────────────────────────────────────────────────────────────────────────────

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Australian Higher Education Staff 2021–2025</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1" integrity="sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ" crossorigin="anonymous"></script>
  <style>
    :root {
      --primary:#bc0002; --secondary:#794c90; --tertiary:#005ab6;
      --on-surface:#1e1b18; --on-surface-variant:#6b6460;
      --surface:#fff8f4; --surface-lowest:#ffffff;
      --surface-low:#faf2ec; --surface-mid:#f5ede5; --surface-high:#ede4dc;
      --shadow:rgba(121,76,144,0.06);
    }
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:"Inter",-apple-system,sans-serif; background:var(--surface); color:var(--on-surface); line-height:1.5; }
    .dash { max-width:1440px; margin:0 auto; padding:20px 24px 40px; display:flex; flex-direction:column; gap:14px; }

    /* ── Header ── */
    .header { background:linear-gradient(135deg,var(--secondary) 0%,#5c3470 100%); border-radius:16px; padding:22px 28px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; box-shadow:0 8px 40px var(--shadow); }
    .header h1 { font-family:"Manrope",sans-serif; font-size:1.25rem; font-weight:800; color:#fff; letter-spacing:-0.02em; }
    .header p  { font-size:0.72rem; color:rgba(255,255,255,0.6); margin-top:3px; }

    /* ── Filter bar ── */
    .filter-bar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; background:rgba(255,248,244,0.12); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); border-radius:12px; padding:10px 14px; border:1px solid rgba(255,255,255,0.15); }
    .fg { display:flex; align-items:center; gap:6px; }
    .fg label { font-size:0.69rem; font-weight:600; color:rgba(255,255,255,0.65); text-transform:uppercase; letter-spacing:0.06em; white-space:nowrap; }
    .fg select { padding:5px 24px 5px 10px; border:none; border-radius:6px; background:var(--surface-high); background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%236b6460' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E"); background-repeat:no-repeat; background-position:right 8px center; color:var(--on-surface); font-size:0.75rem; font-family:inherit; font-weight:500; cursor:pointer; outline:none; appearance:none; }

    /* ── Multi-select ── */
    .ms-wrap  { position:relative; }
    .ms-btn   { display:flex; align-items:center; gap:6px; padding:5px 10px; border:none; border-radius:6px; background:var(--surface-high); color:var(--on-surface); font-size:0.75rem; font-family:inherit; font-weight:500; cursor:pointer; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .ms-btn .arr { font-size:0.6rem; color:var(--on-surface-variant); flex-shrink:0; }
    .ms-panel { display:none; position:absolute; top:calc(100% + 8px); left:0; min-width:280px; background:var(--surface-lowest); border-radius:10px; box-shadow:0 8px 40px rgba(0,0,0,0.14); z-index:200; overflow:hidden; }
    .ms-panel.open { display:block; }
    .ms-search { padding:10px 12px 8px; border-bottom:1px solid var(--surface-mid); }
    .ms-search input { width:100%; padding:6px 10px; border:none; border-radius:6px; background:var(--surface-mid); font-size:0.75rem; font-family:inherit; color:var(--on-surface); outline:none; }
    .ms-controls { display:flex; gap:8px; padding:6px 12px; border-bottom:1px solid var(--surface-mid); }
    .ms-ctrl { font-size:0.68rem; font-weight:600; color:var(--secondary); background:none; border:none; cursor:pointer; padding:2px 0; }
    .ms-ctrl:hover { text-decoration:underline; }
    .ms-options { max-height:240px; overflow-y:auto; padding:4px 0; }
    .ms-opt { display:flex; align-items:center; gap:10px; padding:7px 14px; cursor:pointer; font-size:0.76rem; color:var(--on-surface) !important; }
    .ms-opt:hover { background:var(--surface-low); }
    .ms-opt input[type=checkbox] { accent-color:var(--secondary); width:14px; height:14px; flex-shrink:0; cursor:pointer; }
    .ms-sub { font-size:0.65rem; color:var(--on-surface-variant); }
    .ms-empty { padding:14px; font-size:0.75rem; color:var(--on-surface-variant); text-align:center; }

    /* ── Metric toggle ── */
    .mtoggle { display:flex; gap:4px; background:rgba(255,255,255,0.1); border-radius:8px; padding:3px; }
    .mbtn { padding:4px 12px; border:none; border-radius:6px; font-size:0.72rem; font-weight:600; font-family:inherit; cursor:pointer; color:rgba(255,255,255,0.65); background:transparent; transition:all 0.2s; }
    .mbtn.active { background:rgba(255,255,255,0.2); color:#fff; }

    /* ── Context chips ── */
    .ctx-strip { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .ctx-lbl { font-size:0.67rem; font-weight:600; color:var(--on-surface-variant); text-transform:uppercase; letter-spacing:0.06em; }
    .ctx-chip { display:inline-flex; align-items:center; gap:6px; padding:5px 12px; border-radius:100px; background:var(--surface-lowest); box-shadow:0 2px 8px var(--shadow); font-size:0.72rem; }
    .ctx-chip .dim { font-weight:600; color:var(--on-surface-variant); font-size:0.67rem; text-transform:uppercase; letter-spacing:0.05em; }
    .ctx-chip .val { font-weight:500; color:var(--on-surface); }

    /* ── KPI row ── */
    .kpi-row { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
    .kpi { background:var(--surface-lowest); border-radius:14px; padding:20px 22px; box-shadow:0 4px 24px var(--shadow); }
    .kpi.hero { background:linear-gradient(135deg,var(--secondary) 0%,#5c3470 100%); }
    .kpi.hero .klbl,.kpi.hero .kval,.kpi.hero .ksub { color:#fff !important; }
    .kpi.hero .kchg { color:rgba(255,255,255,0.8) !important; }
    .klbl { font-size:0.67rem; font-weight:600; color:var(--on-surface-variant); text-transform:uppercase; letter-spacing:0.07em; margin-bottom:10px; }
    .kval { font-family:"Manrope",sans-serif; font-size:2.3rem; font-weight:800; color:var(--on-surface); letter-spacing:-0.03em; line-height:1; }
    .ksub { font-size:0.72rem; color:var(--on-surface-variant); margin-top:4px; }
    .kchg { display:inline-block; font-size:0.71rem; font-weight:600; margin-top:8px; padding:3px 8px; border-radius:100px; }
    .kchg.up   { background:rgba(0,90,182,0.10); color:var(--tertiary); }
    .kchg.down { background:rgba(188,0,2,0.10);  color:var(--primary);  }

    /* ── Cards / bento ── */
    .bento-main { display:grid; grid-template-columns:3fr 2fr; gap:12px; }
    .bento-dim  { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
    .card { background:var(--surface-lowest); border-radius:14px; padding:22px 24px; box-shadow:0 4px 24px var(--shadow); }
    .card.full { grid-column:1/-1; }
    .card-hdr  { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px; }
    .card-title { font-family:"Manrope",sans-serif; font-size:0.9rem; font-weight:700; color:var(--on-surface); letter-spacing:-0.01em; }
    .card-sub  { font-size:0.7rem; color:var(--on-surface-variant); margin-top:2px; }

    /* Year pills inside dim tiles */
    .year-pills { display:flex; gap:4px; flex-wrap:wrap; justify-content:flex-end; }
    .ypill { padding:3px 8px; border:none; border-radius:100px; font-size:0.65rem; font-weight:600; font-family:inherit; cursor:pointer; background:var(--surface-mid); color:var(--on-surface-variant); transition:all 0.15s; }
    .ypill.active { background:var(--secondary); color:#fff; }

    .cw     { position:relative; height:300px; }
    .cw-sm  { position:relative; height:260px; }
    .cw-pie { position:relative; height:230px; }
    .note   { background:rgba(188,0,2,0.05); border-radius:8px; padding:7px 12px; font-size:0.69rem; color:var(--primary); font-weight:500; margin-bottom:14px; }
    .dim-note { font-size:0.66rem; color:var(--on-surface-variant); margin-top:10px; text-align:center; }

    /* ── Table ── */
    .table-wrap { overflow-x:auto; }
    .dtable { width:100%; border-collapse:collapse; font-size:0.78rem; }
    .dtable thead th { text-align:left; padding:8px 12px; font-size:0.65rem; font-weight:600; color:var(--on-surface-variant); text-transform:uppercase; letter-spacing:0.06em; border-bottom:1px solid var(--surface-high); white-space:nowrap; cursor:pointer; user-select:none; }
    .dtable thead th:hover { color:var(--on-surface); }
    .dtable tbody td { padding:9px 12px; border-bottom:1px solid var(--surface-mid); }
    .dtable tbody tr:last-child td { border-bottom:none; }
    .dtable tbody tr:hover { background:var(--surface-low); }
    .badge { display:inline-block; padding:2px 8px; border-radius:100px; font-size:0.64rem; font-weight:600; background:var(--surface-mid); color:var(--on-surface-variant); }
    .pos { color:var(--tertiary); font-weight:600; }
    .neg { color:var(--primary);  font-weight:600; }
    .footer { text-align:center; font-size:0.67rem; color:var(--on-surface-variant); padding-top:4px; }

    @media(max-width:960px) { .kpi-row{grid-template-columns:repeat(2,1fr);} .bento-main,.bento-dim{grid-template-columns:1fr;} }
    @media(max-width:600px) { .kpi-row{grid-template-columns:1fr 1fr;} .header{flex-direction:column;align-items:flex-start;} }
    @media print { body{background:white;} .filter-bar,.ms-panel{display:none;} .card,.kpi{break-inside:avoid;box-shadow:none;} }
  </style>
<script src="https://pdparker.github.io/dashboard-commons/commons.js" data-dash="staff"></script>
</head>
<body>
<div class="dash">

  <!-- Header -->
  <header class="header">
    <div>
      <h1>Australian Higher Education Staff</h1>
      <p>Staff FTE &amp; Headcount · 2021–2025 · Dept. of Education Higher Education Staff Collection</p>
    </div>
    <div class="filter-bar">
      <div class="fg">
        <label>State</label>
        <select id="f-state" onchange="D.onState()">
          <option value="all">All States</option>
          <option value="Australian Capital Territory">ACT</option>
          <option value="Multi-State">Multi-State</option>
          <option value="New South Wales">NSW</option>
          <option value="Northern Territory">NT</option>
          <option value="Queensland">QLD</option>
          <option value="South Australia">SA</option>
          <option value="Tasmania">TAS</option>
          <option value="Victoria">VIC</option>
          <option value="Western Australia">WA</option>
        </select>
      </div>
      <div class="fg">
        <label>Institution</label>
        <div class="ms-wrap" id="ms-wrap">
          <button class="ms-btn" id="ms-btn" onclick="D.togglePanel(event)">
            <span id="ms-lbl">All Institutions</span><span class="arr">&#9660;</span>
          </button>
          <div class="ms-panel" id="ms-panel">
            <div class="ms-search"><input type="text" id="ms-q" placeholder="Search institutions&hellip;" oninput="D.msSearch(this.value)"></div>
            <div class="ms-controls">
              <button class="ms-ctrl" onclick="D.msAll()">Select all</button>
              <button class="ms-ctrl" onclick="D.msClear()">Clear</button>
            </div>
            <div class="ms-options" id="ms-opts"></div>
          </div>
        </div>
      </div>
      <div class="mtoggle">
        <button class="mbtn active" id="mbtn-fte"   onclick="D.setMetric('fte',this)">FTE</button>
        <button class="mbtn"        id="mbtn-count" onclick="D.setMetric('count',this)">Headcount</button>
      </div>
      <button class="ms-ctrl" onclick="D.exportCsv()">&#8681; Export CSV</button>
    </div>
  </header>

  <!-- Context chips -->
  <div class="ctx-strip">
    <span class="ctx-lbl">Data scope</span>
    <span class="ctx-chip"><span class="dim">Classification</span><span class="val">All</span></span>
    <span class="ctx-chip"><span class="dim">Function</span><span class="val">All</span></span>
    <span class="ctx-chip"><span class="dim">Gender</span><span class="val">All</span></span>
    <span class="ctx-chip"><span class="dim">Work Contract</span><span class="val">All</span></span>
    <span class="ctx-chip"><span class="dim">Org. Unit</span><span class="val">All</span></span>
  </div>

  <!-- KPI row -->
  <div class="kpi-row">
    <div class="kpi hero">
      <div class="klbl">2025 Total Staff FTE</div>
      <div class="kval" id="k-fte">&#8212;</div>
      <div class="ksub">Full-time equivalents (excl. casual)</div>
      <div class="kchg" id="k-fte-c"></div>
    </div>
    <div class="kpi">
      <div class="klbl">2025 Staff Headcount</div>
      <div class="kval" id="k-cnt">&#8212;</div>
      <div class="ksub">Full-time &amp; fractional staff</div>
      <div class="kchg" id="k-cnt-c"></div>
    </div>
    <div class="kpi">
      <div class="klbl">Institutions</div>
      <div class="kval" id="k-inst">&#8212;</div>
      <div class="ksub" id="k-inst-s">Higher education providers</div>
    </div>
    <div class="kpi">
      <div class="klbl">FTE / Headcount Ratio</div>
      <div class="kval" id="k-ratio">&#8212;</div>
      <div class="ksub">2025 average, FT&amp;FF staff</div>
      <div class="kchg" id="k-ratio-c"></div>
    </div>
  </div>

  <!-- Main charts -->
  <div class="bento-main">
    <div class="card">
      <div class="card-hdr">
        <div>
          <div class="card-title" id="t-trend">Trend 2021&#8211;2025</div>
          <div class="card-sub"   id="s-trend">Staff FTE by year</div>
        </div>
      </div>
      <div class="note">&#9888; 2025 FTE excludes casual staff &#8212; prior years include actual casual FTE, affecting year-on-year comparisons.</div>
      <div class="cw"><canvas id="ch-trend"></canvas></div>
    </div>
    <div class="card">
      <div class="card-hdr">
        <div>
          <div class="card-title">Institution Comparison &middot; 2025</div>
          <div class="card-sub" id="s-comp">Ranked by Staff FTE</div>
        </div>
      </div>
      <div class="cw-sm"><canvas id="ch-comp"></canvas></div>
    </div>
  </div>

  <!-- Dimension tiles -->
  <div class="bento-dim">
    <div class="card">
      <div class="card-hdr">
        <div>
          <div class="card-title">Function</div>
          <div class="card-sub">FT&amp;FF staff breakdown</div>
        </div>
        <div class="year-pills" id="func-pills"></div>
      </div>
      <div class="cw-pie"><canvas id="ch-func"></canvas></div>
      <div class="dim-note">Full-time &amp; fractional full-time only &middot; Click legend to hide/show</div>
    </div>
    <div class="card">
      <div class="card-hdr">
        <div>
          <div class="card-title">Gender</div>
          <div class="card-sub">FT&amp;FF staff breakdown</div>
        </div>
        <div class="year-pills" id="gender-pills"></div>
      </div>
      <div class="cw-pie"><canvas id="ch-gender"></canvas></div>
      <div class="dim-note">Full-time &amp; fractional full-time only &middot; Click legend to hide/show</div>
    </div>
    <div class="card">
      <div class="card-hdr">
        <div>
          <div class="card-title">Classification</div>
          <div class="card-sub">FT&amp;FF staff breakdown</div>
        </div>
        <div class="year-pills" id="class-pills"></div>
      </div>
      <div class="cw-pie"><canvas id="ch-class"></canvas></div>
      <div class="dim-note">Full-time &amp; fractional full-time only &middot; Click legend to hide/show</div>
    </div>
  </div>

  <!-- Student-Staff Ratio trend -->
  <div class="card full">
    <div class="card-hdr">
      <div>
        <div class="card-title" id="t-ssr">Student&#8202;:&#8202;Academic Staff Ratio &middot; 2014&#8211;2023</div>
        <div class="card-sub"   id="s-ssr">Students per academic FTE &mdash; lower is better &middot; Source: Dept. of Education</div>
      </div>
    </div>
    <div class="cw" style="height:280px"><canvas id="ch-ssr"></canvas></div>
  </div>

  <!-- Detail table -->
  <div class="card full">
    <div class="card-hdr">
      <div>
        <div class="card-title">Institution Detail</div>
        <div class="card-sub">Click any header to sort &middot; 2025 FTE excludes casual staff</div>
      </div>
    </div>
    <div class="table-wrap">
      <table class="dtable">
        <thead><tr>
          <th onclick="D.sort('state')">State &#8597;</th>
          <th onclick="D.sort('institution')">Institution &#8597;</th>
          <th onclick="D.sort('fte2025')">2025 FTE &#8597;</th>
          <th onclick="D.sort('cnt2025')">2025 Count &#8597;</th>
          <th onclick="D.sort('fte2024')">2024 FTE &#8597;</th>
          <th onclick="D.sort('cnt2024')">2024 Count &#8597;</th>
          <th onclick="D.sort('growth')">5yr Count Growth &#8597;</th>
        </tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </div>

  <div class="footer">Source: Dept. of Education Higher Education Staff Collection &mdash; Data perturbed to protect privacy; grand totals unperturbed. &nbsp;&middot;&nbsp; Dashboard built April 2025.</div>
</div>

<script>
// ── Embedded data ────────────────────────────────────────
%%DATA%%

// ── Constants ────────────────────────────────────────────
const YEARS     = [2021,2022,2023,2024,2025];
const ALL_INSTS = Object.keys(INST_YEAR).sort();
const STATE_ABBR = {
  'Australian Capital Territory':'ACT','Multi-State':'Multi','New South Wales':'NSW',
  'Northern Territory':'NT','Queensland':'QLD','South Australia':'SA',
  'Tasmania':'TAS','Victoria':'VIC','Western Australia':'WA'
};
const COLORS     = ['#794c90','#005ab6','#bc0002','#c87d2a','#217a4b','#5c7fa3','#9b4a6b','#3d7a72','#8a6400','#6b3a2a','#4a7a50'];
const PIE_COLORS = ['#794c90','#005ab6','#bc0002','#c87d2a','#217a4b','#5c7fa3'];

function sname(n) {
  return n
    .replace('The University of','Uni of')
    .replace('University of','Uni of')
    .replace('Australian National University','ANU')
    .replace('Queensland University of Technology','QUT')
    .replace('University of Technology Sydney','UTS')
    .replace('Batchelor Institute of Indigenous Tertiary Education','Batchelor Inst.')
    .replace('Federation University Australia','Federation Uni')
    .replace('Southern Cross University','Southern Cross')
    .replace('University of the Sunshine Coast','Sunshine Coast');
}

// ── Dashboard class ──────────────────────────────────────
class Dashboard {
  constructor() {
    this.metric   = 'fte';
    this.sortCol  = 'fte2025';
    this.sortDir  = 'desc';
    this.statePool = [...ALL_INSTS];
    this.selected  = new Set();
    this.dimYr     = { func:2025, gender:2025, class:2025 };
    this.charts    = {};

    document.addEventListener('click', e => {
      if (!document.getElementById('ms-wrap').contains(e.target))
        document.getElementById('ms-panel').classList.remove('open');
    });

    this.initFromUrl();
  }

  // dashboard-commons: resolve ?state= / ?view= (sync) and ?inst= (async, via registry)
  initFromUrl() {
    const STATE_VALUES = ['Australian Capital Territory','Multi-State','New South Wales',
      'Northern Territory','Queensland','South Australia','Tasmania','Victoria','Western Australia'];

    if (typeof DashCommons === 'undefined') { this.rebuildOpts(); this.renderAll(); return; }

    const st = DashCommons.state.get('state', 'all');
    if (st === 'all' || STATE_VALUES.includes(st)) {
      document.getElementById('f-state').value = st;
      this.statePool = st === 'all' ? [...ALL_INSTS] : ALL_INSTS.filter(i => INST_YEAR[i]?.state === st);
    }

    const view = DashCommons.state.get('view', 'fte');
    if (view === 'fte' || view === 'count') {
      this.metric = view;
      document.querySelectorAll('.mbtn').forEach(b => b.classList.remove('active'));
      document.getElementById(view === 'fte' ? 'mbtn-fte' : 'mbtn-count').classList.add('active');
    }

    const instParam = DashCommons.state.get('inst', '');
    if (!instParam) { this.rebuildOpts(); this.renderAll(); return; }

    DashCommons.registry().then(reg => {
      instParam.split(',').forEach(id => {
        const inst = reg.byId[id.trim()];
        if (inst && ALL_INSTS.includes(inst.name)) this.selected.add(inst.name);
      });
      this.updateLabel();
      this.rebuildOpts();
      this.renderAll();
    }).catch(() => { this.rebuildOpts(); this.renderAll(); });
  }

  // dashboard-commons: push current filter state to the URL
  syncUrl() {
    if (typeof DashCommons === 'undefined') return;
    const stateVal = document.getElementById('f-state').value;
    DashCommons.state.set('state', stateVal === 'all' ? null : stateVal);
    DashCommons.state.set('view', this.metric === 'fte' ? null : this.metric);
    if (!this.selected.size) { DashCommons.state.set('inst', null); return; }
    DashCommons.registry().then(reg => {
      const ids = [...this.selected].map(n => { const m = reg.lookup(n); return m ? m.id : null; }).filter(Boolean);
      DashCommons.state.set('inst', ids.length ? ids.join(',') : null);
    }).catch(() => {});
  }

  get filtered() {
    return this.selected.size
      ? this.statePool.filter(i => this.selected.has(i))
      : [...this.statePool];
  }

  // ── Multi-select ────────────────────────────────────────
  togglePanel(e) {
    e.stopPropagation();
    document.getElementById('ms-panel').classList.toggle('open');
    document.getElementById('ms-q').value = '';
    this.rebuildOpts('');
  }

  rebuildOpts(q = '') {
    const lo = q.toLowerCase();
    const names = lo ? this.statePool.filter(n => n.toLowerCase().includes(lo)) : [...this.statePool];
    const el = document.getElementById('ms-opts');
    if (!names.length) { el.innerHTML = '<div class="ms-empty">No matches</div>'; return; }
    el.innerHTML = names.map(n => {
      const chk = this.selected.has(n) ? 'checked' : '';
      const st  = STATE_ABBR[INST_YEAR[n]?.state] || '';
      const safe = n.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
      return `<label class="ms-opt"><input type="checkbox" ${chk} onchange="D.toggle('${safe}',this.checked)"><span>${n} <span class="ms-sub">${st}</span></span></label>`;
    }).join('');
  }

  msSearch(q)  { this.rebuildOpts(q); }
  toggle(n, v) { v ? this.selected.add(n) : this.selected.delete(n); this.updateLabel(); this.refresh(); this.syncUrl(); }
  msAll()      { this.selected.clear(); this.rebuildOpts(document.getElementById('ms-q').value); this.updateLabel(); this.refresh(); this.syncUrl(); }
  msClear()    { this.msAll(); }

  updateLabel() {
    const n = this.selected.size;
    document.getElementById('ms-lbl').textContent =
      n === 0 ? 'All Institutions' :
      n === 1 ? [...this.selected][0].replace('The University of ','Uni of ') :
      `${n} institutions`;
  }

  onState() {
    const s = document.getElementById('f-state').value;
    this.statePool = s === 'all' ? [...ALL_INSTS] : ALL_INSTS.filter(i => INST_YEAR[i]?.state === s);
    const pool = new Set(this.statePool);
    for (const n of this.selected) if (!pool.has(n)) this.selected.delete(n);
    this.rebuildOpts();
    this.updateLabel();
    this.refresh();
    this.syncUrl();
  }

  setMetric(m, btn) {
    this.metric = m;
    document.querySelectorAll('.mbtn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    this.refresh();
    this.syncUrl();
  }

  // ── Refresh ─────────────────────────────────────────────
  refresh() {
    this.renderKPIs();
    this.updateTrend();
    this.updateComp();
    this.updateDim('func',   FUNC_DATA,   this.dimYr.func);
    this.updateDim('gender', GENDER_DATA, this.dimYr.gender);
    this.updateDim('class',  CLASS_DATA,  this.dimYr.class);
    this.updateSSR();
    this.renderTable();
  }

  renderAll() {
    this.renderKPIs();
    this.renderTrend();
    this.renderComp();
    this.renderDim('func',   'func-pills',   FUNC_DATA,   2025);
    this.renderDim('gender', 'gender-pills', GENDER_DATA, 2025);
    this.renderDim('class',  'class-pills',  CLASS_DATA,  2025);
    this.renderSSR();
    this.renderTable();
  }

  // ── Helpers ─────────────────────────────────────────────
  fmt(v) {
    if (v >= 1e6) return (v/1e6).toFixed(1)+'M';
    if (v >= 1e4) return (v/1e3).toFixed(1)+'K';
    return Math.round(v).toLocaleString('en-AU');
  }

  setChg(id, val, prev) {
    const el = document.getElementById(id);
    if (!el) return;
    if (!prev) { el.textContent = ''; return; }
    const p = ((val - prev) / prev * 100).toFixed(1);
    const sign = p >= 0 ? '+' : '';
    el.textContent = `${sign}${p}% vs 2024`;
    el.className = 'kchg ' + (p >= 0 ? 'up' : 'down');
  }

  // ── KPIs ────────────────────────────────────────────────
  renderKPIs() {
    const f = this.filtered;
    const sum = (yr, field) => f.reduce((a, i) => a + (INST_YEAR[i]?.years[String(yr)]?.[field] || 0), 0);
    const fte25 = sum(2025,'fte'), fte24 = sum(2024,'fte');
    const cnt25 = sum(2025,'count'), cnt24 = sum(2024,'count');
    const ratio25 = cnt25 ? fte25/cnt25 : 0;
    const ratio24 = cnt24 ? fte24/cnt24 : 0;

    document.getElementById('k-fte').textContent   = this.fmt(fte25);
    document.getElementById('k-cnt').textContent   = this.fmt(cnt25);
    document.getElementById('k-inst').textContent  = f.length;
    document.getElementById('k-ratio').textContent = ratio25.toFixed(2);
    document.getElementById('k-inst-s').textContent =
      f.length === ALL_INSTS.length ? 'All HE providers' : `of ${ALL_INSTS.length} total`;

    this.setChg('k-fte-c',   fte25,   fte24);
    this.setChg('k-cnt-c',   cnt25,   cnt24);
    this.setChg('k-ratio-c', ratio25, ratio24);
  }

  // ── Trend chart ─────────────────────────────────────────
  buildTrendDatasets() {
    const f = this.filtered, m = this.metric;
    const lbl = m === 'fte' ? 'Staff FTE' : 'Headcount';
    const multiLine = this.selected.size > 0 && f.length <= 10;

    if (!multiLine) {
      const data = YEARS.map(y => f.reduce((a,i) => a + (INST_YEAR[i]?.years[String(y)]?.[m] || 0), 0));
      return {
        title: 'Trend 2021–2025',
        sub: `${lbl} by year · ${f.length === ALL_INSTS.length ? 'all institutions' : f.length+' institutions'}`,
        multiLine: false,
        datasets: [{
          label: 'Total '+lbl, data,
          borderColor: COLORS[0], backgroundColor: COLORS[0]+'18',
          borderWidth: 2.5, fill: true, tension: 0.35,
          pointRadius: 5, pointHoverRadius: 8,
          pointBackgroundColor: '#fff', pointBorderColor: COLORS[0], pointBorderWidth: 2
        }]
      };
    }

    return {
      title: 'Institution Trend 2021–2025',
      sub: `${lbl} by year — ${f.length} institution${f.length !== 1 ? 's' : ''}`,
      multiLine: true,
      datasets: f.map((inst, i) => ({
        label: sname(inst),
        data: YEARS.map(y => INST_YEAR[inst]?.years[String(y)]?.[m] || 0),
        borderColor: COLORS[i % COLORS.length],
        backgroundColor: 'transparent',
        borderWidth: 2, fill: false, tension: 0.3,
        pointRadius: 4, pointHoverRadius: 7,
        pointBackgroundColor: '#fff',
        pointBorderColor: COLORS[i % COLORS.length], pointBorderWidth: 2
      }))
    };
  }

  trendOpts(multiLine) {
    const self = this;
    return {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: multiLine, labels: { usePointStyle: true, padding: 14, font: { family: 'Inter', size: 11 } } },
        tooltip: {
          backgroundColor: '#fff', borderColor: '#ede4dc', borderWidth: 1,
          titleColor: '#1e1b18', bodyColor: '#6b6460', padding: 12,
          callbacks: { label: ctx => ' ' + ctx.dataset.label + ': ' + self.fmt(ctx.parsed.y) }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 }, color: '#6b6460' } },
        y: { beginAtZero: false, grid: { color: 'rgba(107,100,96,0.08)' },
             ticks: { font: { family: 'Inter', size: 11 }, color: '#6b6460', callback: v => self.fmt(v) } }
      }
    };
  }

  renderTrend() {
    const { title, sub, datasets, multiLine } = this.buildTrendDatasets();
    this.charts.trend = new Chart(document.getElementById('ch-trend').getContext('2d'),
      { type: 'line', data: { labels: YEARS.map(String), datasets }, options: this.trendOpts(multiLine) });
    document.getElementById('t-trend').textContent = title;
    document.getElementById('s-trend').textContent = sub;
  }

  updateTrend() {
    const { title, sub, datasets, multiLine } = this.buildTrendDatasets();
    const ch = this.charts.trend;
    ch.data.datasets = datasets;
    ch.options.plugins.legend.display = multiLine;
    ch.update('none');
    document.getElementById('t-trend').textContent = title;
    document.getElementById('s-trend').textContent = sub;
  }

  // ── Comparison chart ─────────────────────────────────────
  compData() {
    const m = this.metric;
    const rows = [...this.filtered]
      .map(i => ({ inst: i, val: INST_YEAR[i]?.years['2025']?.[m] || 0 }))
      .sort((a, b) => b.val - a.val).slice(0, 20);
    return {
      labels: rows.map(r => sname(r.inst)),
      data:   rows.map(r => Math.round(r.val)),
      colors: rows.map((_, i) => COLORS[i % COLORS.length] + 'cc'),
    };
  }

  compOpts() {
    const self = this;
    return {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#fff', borderColor: '#ede4dc', borderWidth: 1,
          titleColor: '#1e1b18', bodyColor: '#6b6460', padding: 10,
          callbacks: { label: ctx => ' ' + self.fmt(ctx.parsed.x) }
        }
      },
      scales: {
        x: { beginAtZero: true, grid: { color: 'rgba(107,100,96,0.08)' },
             ticks: { font: { family: 'Inter', size: 10 }, color: '#6b6460', callback: v => self.fmt(v) } },
        y: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 10 }, color: '#6b6460' } }
      }
    };
  }

  renderComp() {
    const { labels, data, colors } = this.compData();
    this.charts.comp = new Chart(document.getElementById('ch-comp').getContext('2d'), {
      type: 'bar',
      data: { labels, datasets: [{ data, backgroundColor: colors, borderRadius: 4, borderSkipped: false }] },
      options: this.compOpts()
    });
    document.getElementById('s-comp').textContent = this.metric === 'fte' ? 'Ranked by Staff FTE' : 'Ranked by Headcount';
  }

  updateComp() {
    const { labels, data, colors } = this.compData();
    const ch = this.charts.comp;
    ch.data.labels = labels;
    ch.data.datasets[0].data   = data;
    ch.data.datasets[0].backgroundColor = colors;
    ch.update('none');
    document.getElementById('s-comp').textContent = this.metric === 'fte' ? 'Ranked by Staff FTE' : 'Ranked by Headcount';
  }

  // ── Dimension tiles: donut (1 / all) or stacked bar (2+) ─
  useBar() { return this.selected.size > 1; }

  // Aggregate totals across filtered institutions (for donut)
  dimAgg(dimData, yr) {
    const totals = {}, m = this.metric;
    for (const inst of this.filtered) {
      const byDim = dimData[inst]?.[String(yr)] || {};
      for (const [dim, vals] of Object.entries(byDim)) {
        if (!totals[dim]) totals[dim] = { count: 0, fte: 0 };
        totals[dim].count += vals.count;
        totals[dim].fte   += vals.fte;
      }
    }
    const entries = Object.entries(totals).sort((a, b) => b[1][m] - a[1][m]);
    return {
      labels: entries.map(([k]) => k),
      data:   entries.map(([, v]) => Math.round(m === 'fte' ? v.fte : v.count)),
      colors: PIE_COLORS.slice(0, entries.length).map(c => c + 'cc'),
    };
  }

  // Per-institution % breakdown (for 100% stacked bar)
  dimPerInst(dimData, yr) {
    const m = this.metric, f = this.filtered;
    const allCats = new Set(), instMap = {};
    for (const inst of f) {
      const byDim = dimData[inst]?.[String(yr)] || {};
      instMap[inst] = byDim;
      for (const cat of Object.keys(byDim)) allCats.add(cat);
    }
    // Sort categories by overall total descending so largest segment is always first
    const cats = [...allCats].sort((a, b) => {
      const ta = f.reduce((s, i) => s + (instMap[i]?.[a]?.[m] || 0), 0);
      const tb = f.reduce((s, i) => s + (instMap[i]?.[b]?.[m] || 0), 0);
      return tb - ta;
    });
    const datasets = cats.map((cat, ci) => ({
      label: cat,
      data: f.map(inst => {
        const byDim = instMap[inst];
        const total = Object.values(byDim).reduce((s, v) => s + (v[m] || 0), 0);
        const val   = byDim[cat]?.[m] || 0;
        return total ? parseFloat((val / total * 100).toFixed(2)) : 0;
      }),
      backgroundColor: PIE_COLORS[ci % PIE_COLORS.length] + 'cc',
      borderColor: '#fff8f4',
      borderWidth: 1,
    }));
    return { labels: f.map(i => sname(i)), datasets };
  }

  // Destroy old chart and draw the right type
  drawDim(key, dimData, yr) {
    if (this.charts[key]) { this.charts[key].destroy(); this.charts[key] = null; }
    const canvas = document.getElementById(`ch-${key}`);
    const wrap   = canvas.parentElement;

    if (this.useBar()) {
      // Dynamic height: 42px per institution + room for legend
      const h = Math.max(200, this.filtered.length * 44 + 80);
      wrap.style.height = h + 'px';
      const { labels, datasets } = this.dimPerInst(dimData, yr);
      this.charts[key] = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: { labels, datasets },
        options: this.stackedBarOpts()
      });
    } else {
      wrap.style.height = '230px';
      const { labels, data, colors } = this.dimAgg(dimData, yr);
      this.charts[key] = new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: colors, borderColor: '#fff8f4', borderWidth: 3 }] },
        options: this.pieOpts()
      });
    }
  }

  buildPills(pillsId, key, currentYr) {
    document.getElementById(pillsId).innerHTML = YEARS.map(y =>
      `<button class="ypill${y === currentYr ? ' active' : ''}" onclick="D.setDimYr('${key}',${y},this)">${y}</button>`
    ).join('');
  }

  setDimYr(key, yr, btn) {
    this.dimYr[key] = yr;
    btn.closest('.year-pills').querySelectorAll('.ypill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    this.drawDim(key, key === 'func' ? FUNC_DATA : key === 'gender' ? GENDER_DATA : CLASS_DATA, yr);
  }

  pieOpts() {
    const self = this;
    return {
      responsive: true, maintainAspectRatio: false, cutout: '52%',
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 10, font: { family: 'Inter', size: 10 }, color: '#1e1b18' } },
        tooltip: {
          backgroundColor: '#fff', borderColor: '#ede4dc', borderWidth: 1,
          titleColor: '#1e1b18', bodyColor: '#6b6460', padding: 10,
          callbacks: {
            label: ctx => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              return ` ${ctx.label}: ${self.fmt(ctx.parsed)} (${(ctx.parsed / total * 100).toFixed(1)}%)`;
            }
          }
        }
      }
    };
  }

  stackedBarOpts() {
    return {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 10, font: { family: 'Inter', size: 10 }, color: '#1e1b18' } },
        tooltip: {
          backgroundColor: '#fff', borderColor: '#ede4dc', borderWidth: 1,
          titleColor: '#1e1b18', bodyColor: '#6b6460', padding: 10,
          callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.x.toFixed(1)}%` }
        }
      },
      scales: {
        x: {
          stacked: true, max: 100,
          grid: { color: 'rgba(107,100,96,0.08)' },
          ticks: { font: { family: 'Inter', size: 10 }, color: '#6b6460', callback: v => v + '%' }
        },
        y: {
          stacked: true, grid: { display: false },
          ticks: { font: { family: 'Inter', size: 10 }, color: '#6b6460' }
        }
      }
    };
  }

  renderDim(key, pillsId, dimData, yr) {
    this.dimYr[key] = yr;
    this.buildPills(pillsId, key, yr);
    this.drawDim(key, dimData, yr);
  }

  updateDim(key, dimData, yr) {
    this.drawDim(key, dimData, yr || this.dimYr[key] || 2025);
  }

  // ── Student-Staff Ratio chart ────────────────────────────
  buildSSRDatasets() {
    const f = this.filtered;
    const multiLine = this.selected.size > 0 && f.length <= 10;
    const lbls = SSR_YEARS.map(String);

    if (!multiLine) {
      // National average across all filtered institutions that have data
      const avgs = SSR_YEARS.map(y => {
        const vals = f.map(i => SSR_DATA[i]?.[String(y)]).filter(v => v != null);
        return vals.length ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2)) : null;
      });
      const label = f.length === ALL_INSTS.length ? 'National Average' : 'Group Average';
      const sub   = f.length === ALL_INSTS.length
        ? 'National average · academic FTE (2014–2023)'
        : `Average of ${f.length} institution${f.length !== 1 ? 's' : ''} · academic FTE (2014–2023)`;
      return { lbls, sub, multiLine: false, datasets: [{
        label, data: avgs,
        borderColor: '#794c90', backgroundColor: '#794c9018',
        borderWidth: 2.5, fill: true, tension: 0.35,
        pointRadius: 5, pointHoverRadius: 8,
        pointBackgroundColor: '#fff', pointBorderColor: '#794c90', pointBorderWidth: 2,
        spanGaps: true
      }]};
    }

    const sub = `Students per academic FTE · ${f.length} institution${f.length !== 1 ? 's' : ''} (2014–2023)`;
    return { lbls, sub, multiLine: true, datasets: f.map((inst, i) => ({
      label: sname(inst),
      data: SSR_YEARS.map(y => SSR_DATA[inst]?.[String(y)] ?? null),
      borderColor: COLORS[i % COLORS.length],
      backgroundColor: 'transparent',
      borderWidth: 2, fill: false, tension: 0.3,
      pointRadius: 4, pointHoverRadius: 7,
      pointBackgroundColor: '#fff',
      pointBorderColor: COLORS[i % COLORS.length], pointBorderWidth: 2,
      spanGaps: true
    }))};
  }

  ssrOpts(multiLine) {
    return {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: multiLine, labels: { usePointStyle: true, padding: 14, font: { family: 'Inter', size: 11 } } },
        tooltip: {
          backgroundColor: '#fff', borderColor: '#ede4dc', borderWidth: 1,
          titleColor: '#1e1b18', bodyColor: '#6b6460', padding: 12,
          callbacks: { label: ctx => ctx.parsed.y != null ? ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)} students/staff` : '' }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 }, color: '#6b6460' } },
        y: {
          beginAtZero: false,
          grid: { color: 'rgba(107,100,96,0.08)' },
          title: { display: true, text: 'Students per academic FTE', font: { family: 'Inter', size: 10 }, color: '#6b6460' },
          ticks: { font: { family: 'Inter', size: 11 }, color: '#6b6460', callback: v => v.toFixed(0) + 'x' }
        }
      }
    };
  }

  renderSSR() {
    if (this.charts.ssr) { this.charts.ssr.destroy(); this.charts.ssr = null; }
    const { lbls, sub, datasets, multiLine } = this.buildSSRDatasets();
    this.charts.ssr = new Chart(document.getElementById('ch-ssr').getContext('2d'),
      { type: 'line', data: { labels: lbls, datasets }, options: this.ssrOpts(multiLine) });
    document.getElementById('s-ssr').textContent = sub;
  }

  updateSSR() { this.renderSSR(); }

  // ── Table ────────────────────────────────────────────────
  sort(col) {
    this.sortDir = this.sortCol === col ? (this.sortDir === 'asc' ? 'desc' : 'asc') : 'desc';
    this.sortCol = col;
    this.renderTable();
  }

  renderTable() {
    const gv = (inst, col) => {
      const d = INST_YEAR[inst]?.years;
      if (col === 'state')       return INST_YEAR[inst]?.state || '';
      if (col === 'institution') return inst;
      if (col === 'fte2025')     return d?.['2025']?.fte   || 0;
      if (col === 'cnt2025')     return d?.['2025']?.count || 0;
      if (col === 'fte2024')     return d?.['2024']?.fte   || 0;
      if (col === 'cnt2024')     return d?.['2024']?.count || 0;
      if (col === 'growth') {
        const c21 = d?.['2021']?.count, c25 = d?.['2025']?.count;
        return c21 ? (c25 - c21) / c21 * 100 : 0;
      }
      return 0;
    };

    const sorted = [...this.filtered].sort((a, b) => {
      const av = gv(a, this.sortCol), bv = gv(b, this.sortCol);
      const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
      return this.sortDir === 'asc' ? cmp : -cmp;
    });

    document.getElementById('tbody').innerHTML = sorted.map(inst => {
      const d   = INST_YEAR[inst]?.years;
      const c21 = d?.['2021']?.count || 0, c25 = d?.['2025']?.count || 0;
      const g   = c21 ? ((c25 - c21) / c21 * 100) : 0;
      const sign = g >= 0 ? '+' : '';
      return `<tr>
        <td><span class="badge">${STATE_ABBR[INST_YEAR[inst]?.state] || ''}</span></td>
        <td>${inst}</td>
        <td>${this.fmt(d?.['2025']?.fte   || 0)}</td>
        <td>${this.fmt(d?.['2025']?.count || 0)}</td>
        <td>${this.fmt(d?.['2024']?.fte   || 0)}</td>
        <td>${this.fmt(d?.['2024']?.count || 0)}</td>
        <td class="${g >= 0 ? 'pos' : 'neg'}">${sign}${g.toFixed(1)}%</td>
      </tr>`;
    }).join('');
  }

  // ---- CSV EXPORT (institution detail table, respects state/institution/view filters) ----
  exportCsv() {
    const rows = [['state','institution','2025_fte','2025_headcount','2024_fte','2024_headcount','5yr_headcount_growth_pct']];
    [...this.filtered].forEach(inst => {
      const d = INST_YEAR[inst]?.years;
      const c21 = d?.['2021']?.count || 0, c25 = d?.['2025']?.count || 0;
      const g = c21 ? +((c25 - c21) / c21 * 100).toFixed(1) : '';
      rows.push([
        INST_YEAR[inst]?.state || '',
        inst,
        d?.['2025']?.fte ?? '',
        d?.['2025']?.count ?? '',
        d?.['2024']?.fte ?? '',
        d?.['2024']?.count ?? '',
        g
      ]);
    });

    const csv = rows.map(r => r.map(v => {
      const s = String(v);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'staff-numbers-' + this.metric + (this.selected.size ? '-filtered' : '-all') + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

const D = new Dashboard();
</script>
</body>
</html>
"""

html = TEMPLATE.replace('%%DATA%%', data_js)

with open(out_path, 'w') as f:
    f.write(html)

size_kb = os.path.getsize(out_path) // 1024
print(f"Written: {out_path}  ({size_kb} KB)")
