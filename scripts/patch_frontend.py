from pathlib import Path
p=Path('/mnt/data/assignment_modern_v1/src/main.js')
s=p.read_text()
s=s.replace("date:isDemo?'2026-11-11':dateWita(),store:'all',subTab", "date:isDemo?'2026-11-11':dateWita(),store:'all',brand:'all',subTab")
s=s.replace("const filteredIssues=()=> (state.data?.issues||[]).filter(i=>allowedStore(i.store_id)&&(state.store==='all'||state.store===i.store_id));", "const inScope=id=>allowedStore(id)&&(state.store==='all'||state.store===id)&&(state.brand==='all'||STORES.find(s=>s.id===id)?.brand===state.brand);\nconst filteredIssues=()=> (state.data?.issues||[]).filter(i=>inScope(i.store_id));")
s=s.replace("const storesInScope=()=>active().filter(s=>state.store==='all'||s.id===state.store);", "const storesInScope=()=>active().filter(s=>inScope(s.id));")
s=s.replace("const dayBriefings=()=> (state.data?.briefings||[]).filter(b=>b.briefing_date===state.date&&allowedStore(b.store_id));", "const dayBriefings=()=> (state.data?.briefings||[]).filter(b=>b.briefing_date===state.date&&inScope(b.store_id));")
s=s.replace("<select id=\"brandFilter\" disabled><option>Semua brand</option></select>","<select id=\"brandFilter\"><option value=\"all\" ${state.brand==='all'?'selected':''}>Semua brand</option><option value=\"MAMU\" ${state.brand==='MAMU'?'selected':''}>MAMU</option><option value=\"Tigalapankaos\" ${state.brand==='Tigalapankaos'?'selected':''}>Tigalapankaos</option></select>")
s=s.replace("const compliance=scope.map(s=>({s,ok:reported.has(s.id)}));", "const compliance=scope.map(s=>({s,ok:reported.has(s.id)}));")
s=s.replace("state.data.briefings.filter(b=>b.briefing_date===day&&(state.store==='all'||b.store_id===state.store)).length", "state.data.briefings.filter(b=>b.briefing_date===day&&inScope(b.store_id)).length")
s=s.replace("state.data.checklists.filter(c=>allowedStore(c.store_id)&&(state.store==='all'||state.store===c.store_id)&&c.check_date===state.date)","state.data.checklists.filter(c=>inScope(c.store_id)&&c.check_date===state.date)")
s=s.replace("state.data.dso.filter(x=>allowedStore(x.store_id)&&(state.store==='all'||state.store===x.store_id))", "state.data.dso.filter(x=>inScope(x.store_id))")
s=s.replace("state.data.schedules.filter(x=>allowedStore(x.store_id)&&(state.store==='all'||state.store===x.store_id))", "state.data.schedules.filter(x=>inScope(x.store_id))")
s=s.replace("state.data.visits.filter(x=>allowedStore(x.store_id)&&(state.store==='all'||state.store===x.store_id))", "state.data.visits.filter(x=>inScope(x.store_id))")
s=s.replace("state.data.visits.filter(x=>allowedStore(x.store_id))", "state.data.visits.filter(x=>inScope(x.store_id))")
s=s.replace("state.store=$('storeFilter')?.value||state.store;", "state.store=$('storeFilter')?.value||state.store;state.brand=$('brandFilter')?.value||state.brand;")
start=s.find('function exportCurrent(){')
end=s.find('\nasync function reload()',start)
assert start>=0 and end>=0
s=s[:start]+'''function exportCurrent(){
 const filtered=(arr)=>arr.filter(x=>inScope(x.store_id));
 let rows=[];
 if(['overview','issues','pending'].includes(state.page)){
  rows=sortedIssues(filteredIssues().filter(x=>(state.page!=='pending'||x.origin==='visit')&&(state.status==='all'||x.status===state.status)&&(!state.search||`${x.title||''} ${x.pic_name||''} ${storeName(x.store_id)}`.toLowerCase().includes(state.search.toLowerCase()))));
 }else if(state.page==='compliance')rows=storesInScope().map(s=>({toko:s.name,tanggal:state.date,status:submitted().has(s.id)?'Sudah':'Belum'}));
 else if(state.page==='schedule')rows=filtered(state.data.schedules);
 else if(state.page==='visits')rows=filtered(state.data.visits);
 else if(state.page==='checklist')rows=filtered(state.data.checklists).filter(c=>c.check_date===state.date);
 else if(state.page==='dso')rows=filtered(state.data.dso).filter(d=>d.report_date===state.date);
 else if(state.page==='scorecard')rows=storesInScope().map(s=>({toko:s.name,issues:filteredIssues().filter(i=>i.store_id===s.id).length}));
 csvDownload(rows,`assignment_${state.page}_${state.date}.csv`);
}
''' + s[end:]
p.write_text(s)
print('updated',p.stat().st_size)
