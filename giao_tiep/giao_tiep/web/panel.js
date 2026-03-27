const state = { currentJob:null, polling:null };

function $(id){ return document.getElementById(id); }
function setEl(id,v){ const e=$(id); if(e) e.textContent=v; }
function setMsg(tab,msg,cls=''){ const e=$('msg-'+tab); if(e){ e.textContent=msg; e.className='msg '+cls; } }
function showProg(tab,pct){ const bar=$('prog-'+tab); const fill=$('fill-'+tab); if(bar) bar.style.display=pct>0?'block':'none'; if(fill) fill.style.width=pct+'%'; }
function prettyErr(payload, fallback='Lỗi không xác định'){ if(!payload) return fallback; if(payload.detail?.message) return payload.detail.message; if(payload.detail?.error?.detail) return payload.detail.error.detail; if(payload.message) return payload.message; if(payload.detail) return typeof payload.detail==='string' ? payload.detail : JSON.stringify(payload.detail); return fallback; }

function switchTab(tab){
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.tp').forEach(x=>x.classList.remove('active'));
  document.querySelector(`.tab[data-tab="${tab}"]`)?.classList.add('active');
  $('tp-'+tab)?.classList.add('active');
}

document.querySelectorAll('.tab').forEach(t=> t.onclick=()=>switchTab(t.dataset.tab));

['drop-zone','drop-zone-2'].forEach(id=>{
  const dz=$(id); if(!dz) return;
  dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag')});
  dz.addEventListener('dragleave',()=>dz.classList.remove('drag'));
  dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('drag');const fi=$(id+'-fi'); if(e.dataTransfer.files[0]){fi.files=e.dataTransfer.files; onFileChon(id,e.dataTransfer.files[0]);}});
  const fi=$(id+'-fi'); if(fi) fi.onchange=()=>{ if(fi.files[0]) onFileChon(id,fi.files[0]); };
});

function onFileChon(id,f){
  const dz=$(id); if(!dz) return;
  const p = dz.querySelector('p');
  if(p) p.textContent='📄 '+f.name+' ('+(f.size/1024).toFixed(1)+' KB)';
  if(id==='drop-zone') $('btn-upload').disabled=false;
  if(id==='drop-zone-2') $('btn-scan').disabled=false;
}

async function uploadVaDich(){
  const fi=$('drop-zone-fi'); if(!fi?.files?.[0]) return;
  const lf=$('lang-from').value, lt=$('lang-to').value, pluginFilter=$('plugin-filter').value;
  setMsg('t1','Đang upload...','ty'); showProg('t1',15); $('btn-upload').disabled=true; $('dl-area').style.display='none';
  try{
    const fd=new FormData(); fd.append('file',fi.files[0]); fd.append('plugin_da_chon',pluginFilter);
    const r=await fetch('/api/jobs/upload',{method:'POST',body:fd}); const d=await r.json(); if(!r.ok || d.ok===false) throw new Error(prettyErr(d,'Upload lỗi'));
    const p=d.data||d;
    state.currentJob=p.ma_job; setMsg('t1',`Upload OK! ${p.scan.can_dich.length} file cần dịch. Đang gửi lệnh dịch...`,'ty'); showProg('t1',35);
    const r2=await fetch('/api/jobs/'+state.currentJob+'/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lang_from:lf,lang_to:lt})});
    const d2=await r2.json(); if(!r2.ok || d2.ok===false) throw new Error(prettyErr(d2,'Lỗi chạy job'));
    setMsg('t1','Đang dịch...','ty'); showProg('t1',50); startPolling();
  }catch(e){ setMsg('t1','❌ '+e.message,'tr'); $('btn-upload').disabled=false; showProg('t1',0); }
}

function startPolling(){
  clearInterval(state.polling); let p=50;
  state.polling=setInterval(async()=>{
    if(!state.currentJob){ clearInterval(state.polling); return; }
    const r=await fetch('/api/jobs/'+state.currentJob); const d=await r.json();
    const j=d.data||d;
    $('job-log').textContent=(j.log||[]).join('\n')||'...';
    const st=j.trang_thai||j.status;
    if(st==='done'){
      clearInterval(state.polling); showProg('t1',100); setMsg('t1','✅ Xong! Nhấn tải kết quả.','tg'); $('dl-area').style.display='block'; $('btn-upload').disabled=false; taiThongKe(); taiJobs();
    }else if(st==='error' || st==='cancelled'){
      clearInterval(state.polling); setMsg('t1','❌ Lỗi: '+((j.log||[]).slice(-1)[0]||'?'),'tr'); $('btn-upload').disabled=false; showProg('t1',0); taiJobs();
    }else{ p=Math.min(p+4,90); showProg('t1',p); }
  }, 1800);
}

function taiKetQua(){ if(state.currentJob) window.location.href='/api/jobs/'+state.currentJob+'/download'; }

async function scanPlugin(){
  const fi=$('drop-zone-2-fi'); if(!fi?.files?.[0]) return;
  setMsg('t2','Đang quét...','ty'); $('btn-scan').disabled=true;
  try{
    const fd=new FormData(); fd.append('file',fi.files[0]);
    const r=await fetch('/api/plugins/scan',{method:'POST',body:fd}); const d=await r.json(); if(!r.ok || d.ok===false) throw new Error(prettyErr(d,'Lỗi quét'));
    hienThiScanResult(d.data||d); $('scan-result-area').style.display='block'; setMsg('t2','Quét xong!','tg');
  }catch(e){ setMsg('t2','❌ '+e.message,'tr'); }
  $('btn-scan').disabled=false;
}

function hienThiScanResult(d){
  const muc=(d.scan_ngoai?.muc)||[];
  const badgeMap={nen_dao:'badge-nen',can_than:'badge-can',bo_qua:'badge-bo',xem_them:'badge-xem'};
  const labelMap={nen_dao:'NÊN ĐÀO',can_than:'CẨN THẬN',bo_qua:'BỎ QUA',xem_them:'XEM THÊM'};
  let html='<table class="tbl"><thead><tr><th><input type="checkbox" id="chk-all"></th><th>#</th><th>Tên Plugin</th><th>Path</th><th>File</th><th>Trạng thái</th><th>Điểm</th></tr></thead><tbody>';
  if(!muc.length){ html='<p style="color:var(--mu);padding:16px">Không tìm thấy folder plugin nào</p>'; }
  else{
    for(const m of muc){
      const bc=badgeMap[m.goi_y]||'badge-xem', lb=labelMap[m.goi_y]||m.goi_y, chk=m.goi_y==='nen_dao'?'checked':'';
      html+=`<tr><td><input type="checkbox" class="plugin-chk" value="${m.path}" ${chk}></td><td>${m.id}</td><td><b>${m.ten}</b></td><td style="font-family:monospace;font-size:.75rem">${m.path}</td><td>${m.so_file_hop_le}/${m.tong_file}</td><td><span class="${bc}">${lb}</span></td><td>${m.diem}</td></tr>`;
    }
    html+='</tbody></table>';
  }
  $('scan-table').innerHTML=html;
  $('chk-all')?.addEventListener('change',e=> document.querySelectorAll('.plugin-chk').forEach(c=>c.checked=e.target.checked));
}

async function luuPluginChon(){
  const chk=[...document.querySelectorAll('.plugin-chk:checked')].map(x=>x.value);
  if(!chk.length){ alert('Chưa chọn plugin nào'); return; }
  const fd=new FormData(); fd.append('plugin_da_chon',chk.join(','));
  const r=await fetch('/api/plugins/luu',{method:'POST',body:fd}); const d=await r.json();
  if((d.ok ?? true)){ setMsg('t2',`✅ Đã lưu ${((d.data||d).da_luu||[]).length} plugin`,'tg'); taiPlugins(); }
}

async function taiPlugins(){
  const r=await fetch('/api/plugins/list'); const d=await r.json(); const payload=d.data||d;
  let html='';
  if(!(payload.ds||[]).length) html='<p style="color:var(--mu)">Chưa có plugin</p>';
  else (payload.ds||[]).forEach(p=> html+=`<span class="pill nen" onclick="xoaPlugin(${JSON.stringify(p)})" title="Click để xóa">${p} ✕</span>`);
  $('plugin-list-ui').innerHTML=html;
  const sel=$('plugin-filter');
  if(sel){ const cur=sel.value; sel.innerHTML='<option value="">Dịch tất cả file</option>'+(payload.ds||[]).map(p=>`<option value="${p}"${cur===p?' selected':''}>${p}</option>`).join(''); }
}

async function xoaPlugin(ten){ if(!confirm('Xóa plugin '+ten+'?')) return; const r=await fetch('/api/plugins/xoa',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ten})}); const d=await r.json(); if(d.ok!==false) taiPlugins(); }
async function themPluginThuCong(){ const inp=$('new-plugin-inp'); const ten=inp.value.trim(); if(!ten) return; const r=await fetch('/api/plugins/them',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ten})}); const d=await r.json(); if(d.ok!==false){ inp.value=''; taiPlugins(); } }

async function taiKeys(){
  const r=await fetch('/api/keys'); const d=await r.json(); const payload=d.data||d; let html='';
  if(!(payload.keys||[]).length) html='<p style="color:var(--mu)">Chưa có key</p>';
  else (payload.keys||[]).forEach(k=>{ const cls=k.status==='working'?'dot':k.status==='failed'?'dot dot-f':'dot dot-c'; const short=k.key.substring(0,8)+'...'+k.key.slice(-4); html+=`<div class="key-item"><span class="${cls}"></span>${short}<span style="color:var(--mu);margin-left:auto;font-size:.7rem">${k.status||'active'}</span></div>`; });
  $('key-list-ui').innerHTML=html;
}
async function themKey(){ const inp=$('new-key-inp'); const key=inp.value.trim(); if(!key) return; const r=await fetch('/api/keys',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ten:key})}); const d=await r.json(); if(d.ok!==false){ inp.value=''; taiKeys(); setMsg('keys','✅ Đã thêm key!','tg'); } }

async function taiJobs(){
  const r=await fetch('/api/jobs?limit=50'); const d=await r.json(); const payload=d.data||d; const jobs=payload.items||payload;
  const cMap={pending:'ch-p',queued:'ch-p',running:'ch-r',done:'ch-d',error:'ch-e',cancelled:'ch-e'}; let html='';
  if(!jobs.length) html='<tr><td colspan="5" style="text-align:center;color:var(--mu);padding:20px">Chưa có job</td></tr>';
  else jobs.forEach(j=> html+=`<tr><td style="font-family:monospace;font-size:.75rem">${j.ma_job}</td><td>${j.ten_file||'?'}</td><td><span class="chip ${cMap[j.trang_thai]||'ch-p'}">${j.trang_thai}</span></td><td>${j.so_file||j.progress?.total||'-'}</td><td>${(j.trang_thai==='done' && (j.file_ket_qua||j.gofile_link))?`<a href="/api/jobs/${j.ma_job}/download" style="color:var(--g)">⬇ Tải</a>`:'—'}</td></tr>`);
  $('jobs-tbody').innerHTML=html;
}

async function taiThongKe(){
  try{ const r=await fetch('/api/stats'); const d=await r.json(); const payload=d.data||d; const s=payload.statistics||payload; setEl('st-req',s.requests??0); setEl('st-ok',s.successful??0); setEl('st-fail',s.failed??0); setEl('st-keys',(payload.total_keys??0)+' ('+(payload.failed_keys??0)+' lỗi)'); setEl('st-model',payload.current_model||payload.models?.[0]||'—'); }catch{}
  try{ const r=await fetch('/api/jobs?limit=50'); const d=await r.json(); const payload=d.data||d; const j=payload.items||payload; setEl('st-jobs',j.length); setEl('st-done',j.filter(x=>x.trang_thai==='done').length); }catch{}
}

async function init(){
  await taiThongKe(); await taiJobs(); await taiPlugins(); await taiKeys();
  try{ const r=await fetch('/api/system/health'); await r.json(); $('conn').textContent='● Online'; $('conn').style.color='var(--g)'; }catch{ $('conn').textContent='● Offline'; $('conn').style.color='var(--r)'; }
}
setInterval(taiThongKe,15000); setInterval(taiJobs,8000); init();
