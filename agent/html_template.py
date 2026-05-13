"""Dashboard Agent — HTML Template String for Jinja2 rendering."""

DASHBOARD_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" data-theme="{{ default_theme }}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{ title }}</title>
<script src="{{ plotly_cdn }}"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
:root,[data-theme="light"]{
--bg:#f0f2f5;--bg2:#ffffff;--bg3:#f8f9fa;--sidebar:#ffffff;
--text:#1a1a2e;--text2:#4a4a6a;--text3:#8a8aaa;
--border:#e2e4e8;--accent:#4361ee;--accent2:#3a0ca3;
--kpi-bg:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
--kpi-bg2:linear-gradient(135deg,#f093fb 0%,#f5576c 100%);
--kpi-bg3:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);
--kpi-bg4:linear-gradient(135deg,#43e97b 0%,#38f9d7 100%);
--kpi-bg5:linear-gradient(135deg,#fa709a 0%,#fee140 100%);
--kpi-bg6:linear-gradient(135deg,#a18cd1 0%,#fbc2eb 100%);
--kpi-text:#ffffff;--shadow:0 2px 12px rgba(0,0,0,0.08);
--chart-bg:#ffffff;--chart-border:#e8eaed;
--filter-bg:#f8f9fa;--filter-border:#dde0e4;
--hover:rgba(67,97,238,0.08);--scrollbar:#c4c8d0;
--plot-grid:#eaedf2;--plot-text:#4a4a6a;
}
[data-theme="dark"]{
--bg:#0f0f1a;--bg2:#1a1a2e;--bg3:#16213e;--sidebar:#1a1a2e;
--text:#e4e4f0;--text2:#a4a4c4;--text3:#6a6a8a;
--border:#2a2a4a;--accent:#4cc9f0;--accent2:#7209b7;
--kpi-bg:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
--kpi-bg2:linear-gradient(135deg,#f093fb 0%,#f5576c 100%);
--kpi-bg3:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);
--kpi-bg4:linear-gradient(135deg,#43e97b 0%,#38f9d7 100%);
--kpi-bg5:linear-gradient(135deg,#fa709a 0%,#fee140 100%);
--kpi-bg6:linear-gradient(135deg,#a18cd1 0%,#fbc2eb 100%);
--kpi-text:#ffffff;--shadow:0 2px 16px rgba(0,0,0,0.3);
--chart-bg:#1a1a2e;--chart-border:#2a2a4a;
--filter-bg:#16213e;--filter-border:#2a2a4a;
--hover:rgba(76,201,240,0.1);--scrollbar:#3a3a5a;
--plot-grid:#2a2a4a;--plot-text:#a4a4c4;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);
display:flex;height:100vh;overflow:hidden;transition:background .3s,color .3s;}
::-webkit-scrollbar{width:6px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}
.sidebar{width:280px;background:var(--sidebar);border-right:1px solid var(--border);
display:flex;flex-direction:column;height:100vh;overflow-y:auto;
transition:background .3s,border .3s;flex-shrink:0;}
.sidebar-header{padding:20px;border-bottom:1px solid var(--border);}
.sidebar-header h2{font-size:14px;font-weight:600;color:var(--accent);
text-transform:uppercase;letter-spacing:1.2px;}
.filter-section{padding:16px 20px;border-bottom:1px solid var(--border);}
.filter-label{font-size:11px;font-weight:600;color:var(--text3);
text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;}
.filter-select{width:100%;padding:8px 12px;background:var(--filter-bg);
color:var(--text);border:1px solid var(--filter-border);border-radius:6px;
font-size:13px;font-family:'Inter',sans-serif;cursor:pointer;
transition:border .2s;appearance:auto;}
.filter-select:focus{outline:none;border-color:var(--accent);}
.filter-input{width:100%;padding:8px 12px;background:var(--filter-bg);
color:var(--text);border:1px solid var(--filter-border);border-radius:6px;
font-size:13px;font-family:'Inter',sans-serif;transition:border .2s;}
.filter-input:focus{outline:none;border-color:var(--accent);}
.range-row{display:flex;gap:8px;align-items:center;}
.range-row input{flex:1;min-width:0;}
.range-row span{color:var(--text3);font-size:11px;}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;}
.header{padding:16px 28px;background:var(--bg2);border-bottom:1px solid var(--border);
display:flex;align-items:center;justify-content:space-between;
transition:background .3s,border .3s;flex-shrink:0;}
.header-left h1{font-size:20px;font-weight:700;color:var(--text);}
.header-left p{font-size:12px;color:var(--text3);margin-top:2px;}
.header-right{display:flex;align-items:center;gap:12px;}
.btn{padding:8px 16px;border-radius:8px;font-size:12px;font-weight:600;
font-family:'Inter',sans-serif;cursor:pointer;transition:all .2s;border:none;}
.btn-reset{background:var(--filter-bg);color:var(--text2);border:1px solid var(--filter-border);}
.btn-reset:hover{border-color:var(--accent);color:var(--accent);}
.btn-theme{background:var(--accent);color:#fff;padding:8px 14px;}
.btn-theme:hover{opacity:0.85;transform:translateY(-1px);}
.content{flex:1;overflow-y:auto;padding:24px 28px;}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
gap:16px;margin-bottom:24px;}
.kpi-card{border-radius:14px;padding:20px 22px;color:var(--kpi-text);
position:relative;overflow:hidden;transition:transform .2s,box-shadow .2s;
box-shadow:var(--shadow);}
.kpi-card:nth-child(6n+1){background:var(--kpi-bg);}
.kpi-card:nth-child(6n+2){background:var(--kpi-bg2);}
.kpi-card:nth-child(6n+3){background:var(--kpi-bg3);}
.kpi-card:nth-child(6n+4){background:var(--kpi-bg4);}
.kpi-card:nth-child(6n+5){background:var(--kpi-bg5);}
.kpi-card:nth-child(6n+6){background:var(--kpi-bg6);}
.kpi-card:hover{transform:translateY(-3px);box-shadow:0 8px 25px rgba(0,0,0,0.2);}
.kpi-card::after{content:'';position:absolute;top:-50%;right:-50%;width:100%;height:100%;
background:radial-gradient(circle,rgba(255,255,255,0.1) 0%,transparent 70%);pointer-events:none;}
.kpi-label{font-size:12px;font-weight:500;opacity:0.85;margin-bottom:6px;
text-transform:uppercase;letter-spacing:0.5px;}
.kpi-value{font-size:28px;font-weight:700;line-height:1.1;}
.kpi-delta{font-size:12px;margin-top:6px;font-weight:600;}
.delta-up{color:#a8ffc4;} .delta-down{color:#ffa8a8;}
.chart-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:20px;}
.chart-card{background:var(--chart-bg);border:1px solid var(--chart-border);
border-radius:14px;padding:20px;box-shadow:var(--shadow);
transition:background .3s,border .3s,transform .2s;}
.chart-card:hover{transform:translateY(-2px);}
.chart-card.primary{grid-column:span 2;}
.chart-title{font-size:15px;font-weight:600;color:var(--text);margin-bottom:2px;}
.chart-subtitle{font-size:11px;color:var(--text3);margin-bottom:12px;}
.chart-container{width:100%;height:350px;}
.chart-card.primary .chart-container{height:420px;}
@media(max-width:1200px){.chart-grid{grid-template-columns:1fr;}
.chart-card.primary{grid-column:span 1;}}
@media(max-width:768px){.sidebar{display:none;}.content{padding:16px;}
.kpi-row{grid-template-columns:repeat(2,1fr);}}
.slider-val{font-size:11px;color:var(--text2);text-align:center;margin-top:4px;}
input[type="range"]{width:100%;accent-color:var(--accent);}
</style>
</head>
<body>
<aside class="sidebar">
<div class="sidebar-header"><h2>⚙ Filters</h2></div>
{% for f in filters %}
<div class="filter-section">
<div class="filter-label">{{ f.label }}</div>
{% if f.type == "select" %}
<select class="filter-select" id="filter-{{ f.id }}" onchange="applyFilters()">
<option value="__all__">All</option>
{% for opt in f.options %}<option value="{{ opt }}">{{ opt }}</option>{% endfor %}
</select>
{% elif f.type == "date_range" %}
<div class="range-row">
<input type="date" class="filter-input" id="filter-{{ f.id }}-min" value="{{ f.min }}" onchange="applyFilters()">
<span>to</span>
<input type="date" class="filter-input" id="filter-{{ f.id }}-max" value="{{ f.max }}" onchange="applyFilters()">
</div>
{% elif f.type == "range" %}
<div>
<input type="range" id="filter-{{ f.id }}-min" min="{{ f.min }}" max="{{ f.max }}" value="{{ f.min }}" step="{{ f.step }}" oninput="updateSlider(this,'{{ f.id }}','min');applyFilters()">
<div class="slider-val" id="sv-{{ f.id }}-min">Min: {{ f.min }}</div>
</div>
<div style="margin-top:8px;">
<input type="range" id="filter-{{ f.id }}-max" min="{{ f.min }}" max="{{ f.max }}" value="{{ f.max }}" step="{{ f.step }}" oninput="updateSlider(this,'{{ f.id }}','max');applyFilters()">
<div class="slider-val" id="sv-{{ f.id }}-max">Max: {{ f.max }}</div>
</div>
{% endif %}
</div>
{% endfor %}
</aside>
<div class="main">
<div class="header">
<div class="header-left">
<h1>{{ title }}</h1>
<p>{{ domain }} · {{ total_rows }} records{% if sampled %} · Showing {{ sample_size }} sampled{% endif %}</p>
</div>
<div class="header-right">
<button class="btn btn-reset" onclick="resetFilters()">↺ Reset Filters</button>
<button class="btn btn-theme" id="themeBtn" onclick="toggleTheme()">{{ 'Light' if default_theme == 'dark' else 'Dark' }} Mode</button>
</div>
</div>
<div class="content">
<div class="kpi-row">
{% for k in kpis %}
<div class="kpi-card" id="kpi-{{ loop.index0 }}">
<div class="kpi-label">{{ k.label }}</div>
<div class="kpi-value" id="kpi-val-{{ loop.index0 }}">{{ k.formatted_value }}</div>
{% if k.delta_pct is not none %}
<div class="kpi-delta">
{% if k.delta_direction == 'up' %}<span class="delta-up">▲ {{ k.delta_pct }}%</span>
{% else %}<span class="delta-down">▼ {{ k.delta_pct|abs }}%</span>{% endif %}
</div>
{% endif %}
</div>
{% endfor %}
</div>
<div class="chart-grid">
{% for c in charts %}
<div class="chart-card{% if c.is_primary %} primary{% endif %}">
<div class="chart-title">{{ c.title }}</div>
<div class="chart-subtitle">{{ c.subtitle }}</div>
<div class="chart-container" id="chart-{{ c.chart_id }}"></div>
</div>
{% endfor %}
</div>
</div>
</div>
<script>
const DATA = {{ dataset_json }};
const CHART_CONFIGS = {{ chart_configs_json }};
const KPI_CONFIGS = {{ kpi_configs_json }};
const FILTER_CONFIGS = {{ filter_configs_json }};

function getTheme(){return document.documentElement.getAttribute('data-theme');}
function plotLayout(title){
  const dark=getTheme()==='dark';
  return {
    paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',
    font:{family:'Inter',color:dark?'#a4a4c4':'#4a4a6a',size:11},
    margin:{l:50,r:20,t:10,b:50},
    xaxis:{gridcolor:dark?'#2a2a4a':'#eaedf2',zerolinecolor:dark?'#2a2a4a':'#eaedf2'},
    yaxis:{gridcolor:dark?'#2a2a4a':'#eaedf2',zerolinecolor:dark?'#2a2a4a':'#eaedf2'},
    legend:{font:{size:10},bgcolor:'rgba(0,0,0,0)'},
    colorway:['#4361ee','#f72585','#4cc9f0','#7209b7','#3a0ca3','#4895ef','#560bad','#f07167','#00bbf9','#00f5d4'],
    hoverlabel:{font:{family:'Inter',size:12}}
  };
}
const COLORS=['#4361ee','#f72585','#4cc9f0','#7209b7','#3a0ca3','#4895ef','#560bad','#f07167','#00bbf9','#00f5d4'];

function toggleTheme(){
  const el=document.documentElement;const btn=document.getElementById('themeBtn');
  if(el.getAttribute('data-theme')==='dark'){el.setAttribute('data-theme','light');btn.textContent='Dark Mode';}
  else{el.setAttribute('data-theme','dark');btn.textContent='Light Mode';}
  renderAllCharts(getFilteredData());
}

function updateSlider(el,fid,which){
  document.getElementById('sv-'+fid+'-'+which).textContent=(which==='min'?'Min: ':'Max: ')+parseFloat(el.value).toLocaleString();
}

function getFilteredData(){
  let filtered=[...DATA];
  FILTER_CONFIGS.forEach(f=>{
    if(f.type==='select'){
      const v=document.getElementById('filter-'+f.id).value;
      if(v!=='__all__') filtered=filtered.filter(r=>String(r[f.column])===v);
    } else if(f.type==='date_range'){
      const mn=document.getElementById('filter-'+f.id+'-min').value;
      const mx=document.getElementById('filter-'+f.id+'-max').value;
      if(mn) filtered=filtered.filter(r=>r[f.column]>=mn);
      if(mx) filtered=filtered.filter(r=>r[f.column]<=mx+'T23:59:59');
    } else if(f.type==='range'){
      const mn=parseFloat(document.getElementById('filter-'+f.id+'-min').value);
      const mx=parseFloat(document.getElementById('filter-'+f.id+'-max').value);
      filtered=filtered.filter(r=>{const v=parseFloat(r[f.column]);return !isNaN(v)&&v>=mn&&v<=mx;});
    }
  });
  return filtered;
}

function applyFilters(){
  const fd=getFilteredData();
  updateKPIs(fd);
  renderAllCharts(fd);
}

function resetFilters(){
  FILTER_CONFIGS.forEach(f=>{
    if(f.type==='select') document.getElementById('filter-'+f.id).value='__all__';
    else if(f.type==='date_range'){
      document.getElementById('filter-'+f.id+'-min').value=f.min;
      document.getElementById('filter-'+f.id+'-max').value=f.max;
    } else if(f.type==='range'){
      document.getElementById('filter-'+f.id+'-min').value=f.min;
      document.getElementById('filter-'+f.id+'-max').value=f.max;
      document.getElementById('sv-'+f.id+'-min').textContent='Min: '+f.min;
      document.getElementById('sv-'+f.id+'-max').textContent='Max: '+f.max;
    }
  });
  applyFilters();
}

function fmtNum(v){
  if(v==null||isNaN(v)) return 'N/A';
  const a=Math.abs(v);const s=v<0?'-':'';
  if(a>=1e9) return s+(a/1e9).toFixed(1)+'B';
  if(a>=1e6) return s+(a/1e6).toFixed(1)+'M';
  if(a>=1e4) return s+(a/1e3).toFixed(1)+'K';
  if(a>=1) return s+a.toLocaleString(undefined,{maximumFractionDigits:1});
  if(a===0) return '0';
  return s+a.toFixed(2);
}

function updateKPIs(fd){
  KPI_CONFIGS.forEach((k,i)=>{
    const el=document.getElementById('kpi-val-'+i);
    if(!el) return;
    let val;
    if(k.source==='__total_rows__'){val=fd.length;el.textContent=val.toLocaleString();}
    else{
      const nums=fd.map(r=>parseFloat(r[k.source])).filter(v=>!isNaN(v));
      if(k.agg==='sum') val=nums.reduce((a,b)=>a+b,0);
      else if(k.agg==='mean') val=nums.length?nums.reduce((a,b)=>a+b,0)/nums.length:0;
      else val=nums.length;
      el.textContent=k.prefix+fmtNum(val)+k.suffix;
    }
  });
}

function isDateStr(s){return /^\d{4}-\d{2}/.test(s);}
function toMonth(s){if(!s)return'';const d=String(s).slice(0,7);return d;}

function aggregate(data,xCol,yCol,agg,isTimeSeries){
  if(!xCol) return {x:[],y:[]};
  const groups={};
  data.forEach(r=>{
    let key=String(r[xCol]||'');
    if(isTimeSeries) key=toMonth(key);
    if(!key||key==='undefined'||key==='null') return;
    if(!groups[key]) groups[key]={vals:[],count:0};
    if(yCol){const v=parseFloat(r[yCol]);if(!isNaN(v)) groups[key].vals.push(v);}
    groups[key].count++;
  });
  let keys=Object.keys(groups);
  if(isTimeSeries) keys.sort();
  const x=[],y=[];
  keys.forEach(k=>{
    x.push(k);
    const g=groups[k];
    if(agg==='count') y.push(g.count);
    else if(agg==='sum') y.push(g.vals.reduce((a,b)=>a+b,0));
    else if(agg==='mean') y.push(g.vals.length?g.vals.reduce((a,b)=>a+b,0)/g.vals.length:0);
    else if(agg==='median'){const s=[...g.vals].sort((a,b)=>a-b);const m=Math.floor(s.length/2);y.push(s.length?s.length%2?s[m]:(s[m-1]+s[m])/2:0);}
    else if(agg==='max') y.push(g.vals.length?Math.max(...g.vals):0);
    else if(agg==='min') y.push(g.vals.length?Math.min(...g.vals):0);
    else y.push(g.vals.reduce((a,b)=>a+b,0));
  });
  return {x,y};
}

function sortData(x,y,sortBy,topN){
  let pairs=x.map((v,i)=>({x:v,y:y[i]}));
  if(sortBy==='value_desc') pairs.sort((a,b)=>b.y-a.y);
  else if(sortBy==='value_asc') pairs.sort((a,b)=>a.y-b.y);
  else if(sortBy==='label_asc') pairs.sort((a,b)=>String(a.x).localeCompare(String(b.x)));
  if(topN>0) pairs=pairs.slice(0,topN);
  return {x:pairs.map(p=>p.x),y:pairs.map(p=>p.y)};
}

function renderChart(cfg,data){
  const div=document.getElementById('chart-'+cfg.chart_id);
  if(!div) return;
  const layout=plotLayout();
  let traces=[];
  const t=cfg.chart_type;
  const agg=cfg.aggregation||'sum';
  const isTS=((t==='line'||t==='area')&&cfg.x_column&&data.length>0&&isDateStr(String(data[0][cfg.x_column]||'')));

  try{
  if(t==='bar'||t==='horizontal_bar'){
    const d=aggregate(data,cfg.x_column,cfg.y_column,agg,false);
    const s=sortData(d.x,d.y,cfg.sort_by||'value_desc',cfg.top_n);
    if(t==='horizontal_bar'){
      traces=[{type:'bar',y:s.x,x:s.y,orientation:'h',marker:{color:s.x.map((_,i)=>COLORS[i%COLORS.length])}}];
      layout.margin.l=120;
    } else traces=[{type:'bar',x:s.x,y:s.y,marker:{color:s.x.map((_,i)=>COLORS[i%COLORS.length])}}];
  } else if(t==='line'||t==='area'){
    const d=aggregate(data,cfg.x_column,cfg.y_column,agg,isTS);
    if(d.x.length===0){div.innerHTML='<p style="color:var(--text3);text-align:center;padding:60px">No data</p>';return;}
    traces=[{type:'scatter',mode:'lines+markers',x:d.x,y:d.y,
      line:{color:COLORS[0],width:2.5,shape:'spline'},marker:{size:4},
      fill:t==='area'?'tozeroy':'none',
      hovertemplate:'%{x}<br>Value: %{y:,.0f}<extra></extra>'}];
    layout.xaxis.type=isTS?'category':undefined;
    layout.xaxis.tickangle=-45;
  } else if(t==='scatter'||t==='bubble'){
    const pairs=data.map(r=>({x:parseFloat(r[cfg.x_column]),y:parseFloat(r[cfg.y_column]),c:cfg.color_column?String(r[cfg.color_column]||''):''})).filter(p=>!isNaN(p.x)&&!isNaN(p.y));
    if(cfg.color_column){
      const cats=[...new Set(pairs.map(p=>p.c))];
      cats.forEach((cat,i)=>{
        const cp=pairs.filter(p=>p.c===cat);
        traces.push({type:'scatter',mode:'markers',x:cp.map(p=>p.x),y:cp.map(p=>p.y),name:cat,marker:{color:COLORS[i%COLORS.length],size:t==='bubble'?10:6,opacity:0.7}});
      });
    } else {
      traces=[{type:'scatter',mode:'markers',x:pairs.map(p=>p.x),y:pairs.map(p=>p.y),marker:{color:COLORS[0],size:t==='bubble'?10:6,opacity:0.7}}];
    }
  } else if(t==='pie'||t==='donut'){
    const d=aggregate(data,cfg.x_column,cfg.y_column,agg,false);
    if(d.x.length===0||d.y.every(v=>v===0)){div.innerHTML='<p style="color:var(--text3);text-align:center;padding:60px">No data available</p>';return;}
    const s=sortData(d.x,d.y,'value_desc',cfg.top_n||8);
    traces=[{type:'pie',labels:s.x,values:s.y,hole:t==='donut'?0.45:0,
      marker:{colors:COLORS},textinfo:'percent+label',textfont:{size:11},
      hovertemplate:'%{label}<br>Value: %{value:,.0f}<br>%{percent}<extra></extra>'}];
    layout.margin={l:10,r:10,t:10,b:10};layout.showlegend=true;
  } else if(t==='histogram'){
    const vals=data.map(r=>parseFloat(r[cfg.x_column])).filter(v=>!isNaN(v));
    traces=[{type:'histogram',x:vals,marker:{color:COLORS[0],line:{color:COLORS[0],width:0.5}},nbinsx:20,opacity:0.85}];
  } else if(t==='box'){
    if(cfg.x_column&&cfg.y_column){
      const cats=[...new Set(data.map(r=>String(r[cfg.x_column]||'')))].filter(c=>c&&c!=='undefined').slice(0,12);
      cats.forEach((c,i)=>{
        const cv=data.filter(r=>String(r[cfg.x_column])===c).map(r=>parseFloat(r[cfg.y_column])).filter(v=>!isNaN(v));
        if(cv.length>0) traces.push({type:'box',y:cv,name:c,marker:{color:COLORS[i%COLORS.length]},boxpoints:'outliers'});
      });
    } else {
      const vals=data.map(r=>parseFloat(r[cfg.y_column||cfg.x_column])).filter(v=>!isNaN(v));
      traces=[{type:'box',y:vals,marker:{color:COLORS[0]},boxpoints:'outliers'}];
    }
  } else if(t==='heatmap'){
    const d=aggregate(data,cfg.x_column,cfg.y_column,agg,false);
    traces=[{type:'heatmap',z:[d.y],x:d.x,y:[cfg.y_column||''],colorscale:'Viridis'}];
  } else if(t==='treemap'){
    const d=aggregate(data,cfg.x_column,cfg.y_column,agg,false);
    const s=sortData(d.x,d.y,'value_desc',cfg.top_n||15);
    traces=[{type:'treemap',labels:s.x,parents:s.x.map(()=>''),values:s.y,marker:{colors:COLORS}}];
    layout.margin={l:5,r:5,t:5,b:5};
  } else {
    const d=aggregate(data,cfg.x_column,cfg.y_column,agg,false);
    traces=[{type:'bar',x:d.x,y:d.y,marker:{color:COLORS[0]}}];
  }
  if(traces.length===0){div.innerHTML='<p style="color:var(--text3);text-align:center;padding:60px">No data to display</p>';return;}
  Plotly.react(div,traces,layout,{responsive:true,displayModeBar:false});
  }catch(e){console.error('Chart render error:',cfg.chart_id,e);div.innerHTML='<p style="color:var(--text3);text-align:center;padding:60px">Chart error</p>';}
}

function renderAllCharts(data){
  CHART_CONFIGS.forEach(c=>renderChart(c,data));
}

window.addEventListener('DOMContentLoaded',()=>{
  renderAllCharts(DATA);
});
window.addEventListener('resize',()=>renderAllCharts(getFilteredData()));
</script>
</body>
</html>"""
