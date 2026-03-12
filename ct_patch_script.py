import os

P4 = r"""
<script>
// ── State ──
let currentUser = null, currentUserType = null;
const charts = {};
let allStudents = [], allOpps = [];

// ── Helpers ──
function destroyChart(id){if(charts[id]){charts[id].destroy();delete charts[id];}}
function showAlert(msg, type='info'){
  const c=document.getElementById('alert-container');
  const el=document.createElement('div');
  const colors={success:'#2D7A3A',error:'#C0392B',info:'#C65A2E'};
  const icons={success:'fa-check-circle',error:'fa-exclamation-circle',info:'fa-info-circle'};
  el.className='alert-item';
  el.style.cssText=`background:${colors[type]};color:#fff;border:1px solid rgba(255,255,255,.2)`;
  el.innerHTML=`<i class="fas ${icons[type]} text-lg"></i><span>${msg}</span>`;
  c.appendChild(el);
  setTimeout(()=>{el.style.opacity='0';el.style.transition='opacity .3s';setTimeout(()=>el.remove(),300);},4000);
}

function switchTab(tabId){
  document.querySelectorAll('.tab-pane').forEach(t=>{t.classList.remove('active');t.style.display='none';});
  document.querySelectorAll('.nav-link').forEach(n=>{n.classList.remove('active');});
  const pane=document.getElementById('tab-'+tabId);
  if(pane){pane.classList.add('active');pane.style.display='block';}
  document.querySelectorAll('[data-tab="'+tabId+'"]').forEach(n=>n.classList.add('active'));
  const titles={'dashboard':'Overview','ai-matches':'AI Matches','my-schedule':'My Schedule','explore':'Explore Opportunities','student-explorer':'Student Explorer','analytics':'My Impact','system-overview':'Platform Overview','ngo-dashboard':'NGO Dashboard','ngo-manage':'Post Opportunity'};
  const th=document.getElementById('topbar-title');
  if(th)th.textContent=titles[tabId]||tabId;
  
  if(tabId==='dashboard')loadDashboardStats();
  if(tabId==='ai-matches')loadRecommendations();
  if(tabId==='my-schedule')loadMyBookings();
  if(tabId==='explore')loadAllOpportunities();
  if(tabId==='analytics')loadMyImpact();
  if(tabId==='system-overview')loadSystemOverview();
  if(tabId==='student-explorer')loadStudentExplorer();
  if(tabId==='ngo-dashboard')loadNGODashboard();
}

// ── Login Modal ──
function openLoginModal(type) {
  document.getElementById('login-modal').classList.add('open');
  if (type === 'student') {
    document.getElementById('modal-login-title').textContent = 'Student Access';
    document.getElementById('modal-login-desc').textContent = 'Enter your Demo Student ID to start matching.';
    document.getElementById('login-student-form').classList.remove('hidden');
    document.getElementById('login-ngo-form').classList.add('hidden');
  } else {
    document.getElementById('modal-login-title').textContent = 'NGO Portal';
    document.getElementById('modal-login-desc').textContent = 'Log in to manage opportunities and view recommendations.';
    document.getElementById('login-ngo-form').classList.remove('hidden');
    document.getElementById('login-student-form').classList.add('hidden');
  }
}
function closeLoginModal() {
  document.getElementById('login-modal').classList.remove('open');
}

// ── Auth ──
async function loginAs(type){
  const idVal=type==='student'?document.getElementById('demo-student-id').value:document.getElementById('demo-ngo-email').value;
  if(!idVal){showAlert('Please enter ID/Email','error');return;}
  try{
    const res=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'Demo User',email:type==='student'?'student'+idVal+'@example.com':idVal,user_type:type,student_id:type==='student'?parseInt(idVal):null})});
    const data=await res.json();
    if(data.success){
      currentUser=data.user_id; currentUserType=data.user_type;
      closeLoginModal();
      document.getElementById('public-area').classList.add('hidden');
      document.getElementById('sidebar').classList.remove('hidden');
      document.getElementById('sidebar').classList.add('flex');
      document.getElementById('top-header').classList.remove('hidden');
      document.getElementById('private-area').classList.remove('hidden');
      
      if(type==='student'){
        document.getElementById('nav-student').classList.remove('hidden');
        document.getElementById('nav-ngo').classList.add('hidden');
        document.getElementById('sidebar-name').textContent='Student #'+currentUser;
        document.getElementById('sidebar-role').textContent='Volunteer';
        document.getElementById('sidebar-avatar').textContent='S';
        document.getElementById('sidebar-avatar').style.background='var(--primary)';
        document.getElementById('topbar-avatar').textContent='S';
        document.getElementById('topbar-avatar').style.background='var(--primary)';
        switchTab('dashboard');
        loadStudentProfile();
        loadDashboardStats();
      } else {
        document.getElementById('nav-ngo').classList.remove('hidden');
        document.getElementById('nav-student').classList.add('hidden');
        document.getElementById('sidebar-name').textContent='NGO Admin';
        document.getElementById('sidebar-role').textContent='Organization';
        document.getElementById('sidebar-avatar').textContent='N';
        document.getElementById('sidebar-avatar').style.background='var(--accent)';
        document.getElementById('topbar-avatar').textContent='N';
        document.getElementById('topbar-avatar').style.background='var(--accent)';
        switchTab('ngo-dashboard');
      }
      showAlert('Welcome back!','success');
      window.scrollTo(0,0);
    } else { showAlert(data.message,'error'); }
  } catch(e){ showAlert('Network error','error'); }
}

function logout(){
  currentUser=null; currentUserType=null;
  ['sidebar','top-header','nav-student','nav-ngo'].forEach(id=>document.getElementById(id).classList.add('hidden'));
  document.getElementById('sidebar').classList.remove('flex');
  document.getElementById('private-area').classList.add('hidden');
  document.getElementById('public-area').classList.remove('hidden');
  showAlert('Signed out','info');
  window.scrollTo(0,0);
}

// ── Profile ──
async function loadStudentProfile(){
  try{
    const res=await fetch('/api/profile/'+currentUser);
    if(res.ok){
      const p=await res.json();
      document.getElementById('profile-name').textContent=p.name;
      document.getElementById('profile-email').textContent=p.email;
      document.getElementById('profile-university').textContent=p.university;
      const ps=document.getElementById('profile-skills'); ps.innerHTML='';
      if(p.skills)p.skills.split(',').forEach(s=>{if(s.trim())ps.innerHTML+=`<span class="badge badge-primary">${s.trim()}</span>`;});
      const pi=document.getElementById('profile-interests'); pi.innerHTML='';
      if(p.interests)p.interests.split(',').forEach(i=>{if(i.trim())pi.innerHTML+=`<span class="badge badge-neutral">${i.trim()}</span>`;});
    }
  } catch(e){}
}

// ── Dashboard stats ──
async function loadDashboardStats(){
  try{
    const [br,rr]=await Promise.all([fetch('/api/my-bookings/'+currentUser),fetch('/api/recommendations/'+currentUser)]);
    const bookings=await br.json(); const recs=await rr.json();
    const bCount=Array.isArray(bookings)?bookings.length:0;
    const rCount=Array.isArray(recs)?recs.length:0;
    
    const elB=document.getElementById('dash-booking-count'); if(elB)elB.textContent=bCount;
    const elI=document.getElementById('dash-impact-hours'); if(elI)elI.textContent=(bCount*4)+'h';
    const elM=document.getElementById('dash-match-count'); if(elM)elM.textContent=rCount;
    const mb=document.getElementById('match-badge'); if(mb)mb.textContent=rCount;
    
    const nt=document.getElementById('next-action-text'); const nb=document.getElementById('next-action-btn');
    if(nt&&nb){
      if(rCount===0){nt.textContent='No matches yet — the AI is calibrating.';nb.textContent='Retry';nb.onclick=()=>switchTab('ai-matches');}
      else if(bCount===0){nt.textContent=`You have ${rCount} AI-matched opportunities waiting — book one now!`;nb.textContent='View Matches';nb.onclick=()=>switchTab('ai-matches');}
      else{nt.textContent=`${bCount} active booking(s). Keep exploring to maximise your impact!`;nb.textContent='My Schedule';nb.onclick=()=>switchTab('my-schedule');}
    }
  } catch(e){}
}

// ── Recommendations ──
async function loadRecommendations(){
  document.getElementById('loading').classList.remove('hidden');
  document.getElementById('recommendations-container').classList.add('hidden');
  document.getElementById('no-recommendations').classList.add('hidden');
  try{
    const res=await fetch('/api/recommendations/'+currentUser);
    const data=await res.json();
    document.getElementById('loading').classList.add('hidden');
    if(data&&data.length>0){
      const cont=document.getElementById('recommendations-list'); cont.innerHTML='';
      data.forEach((r,i)=>{
        const score=r.match_percentage??Math.round(r.score*100);
        const reasons=Array.isArray(r.reasons)?r.reasons:[];
        const impColor={'emergency':'#C0392B','high':'#C65A2E','medium':'#2A6F6A','standard':'#6B6355'};
        const ic=impColor[r.importance||'medium'];
        const pct=Math.min(score,100);
        
        let reasonHTML = '';
        if(reasons.length) {
          reasonHTML = `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px">${reasons.slice(0,3).map(rn=>`<span class="badge badge-primary" style="font-size:.65rem;font-weight:600"><i class="fas fa-magic text-xs opacity-70"></i>${rn}</span>`).join('')}</div>`;
        }
        
        cont.innerHTML+=`
        <div class="card p-5 relative overflow-hidden">
          <div class="match-card-top" style="position:absolute;top:0;left:0;right:0"></div>
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;margin-top:8px">
            <div style="flex:1;margin-right:12px">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                <h3 style="font-family:'Playfair Display',serif;font-size:1.15rem;font-weight:700;color:var(--text);margin:0">${r.ngo_name}</h3>
                <span class="badge" style="background:#fff;border-color:var(--border);color:${ic};font-size:.6rem;font-weight:700">${(r.importance||'standard').toUpperCase()}</span>
              </div>
              <p style="font-size:.84rem;color:var(--text-muted);line-height:1.6;margin:0">${r.description}</p>
            </div>
            <!-- score ring -->
            <div style="position:relative;width:56px;height:56px;flex-shrink:0;background:var(--bg);border-radius:50%">
              <svg width="56" height="56" viewBox="0 0 56 56" style="position:absolute;top:0;left:0;transform:rotate(-90deg)">
                <circle cx="28" cy="28" r="24" fill="none" stroke="var(--border)" stroke-width="4"/>
                <circle cx="28" cy="28" r="24" fill="none" stroke="var(--primary)" stroke-width="4" stroke-dasharray="${Math.round(2*Math.PI*24*pct/100)} ${Math.round(2*Math.PI*24*(100-pct)/100)}" stroke-linecap="round"/>
              </svg>
              <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Playfair Display',serif;font-size:.85rem;font-weight:700;color:var(--text)">${score}%</div>
            </div>
          </div>
          <!-- skills -->
          <div style="margin-bottom:12px;display:flex;align-items:baseline;gap:6px">
            <span style="font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--text-muted)">Required: </span>
            <span style="font-size:.8rem;color:var(--text);font-weight:500">${r.required_skills}</span>
          </div>
          ${reasonHTML}
          <!-- footer -->
          <div style="display:flex;justify-content:space-between;align-items:center;padding-top:14px;border-top:1.5px solid var(--border)">
            <span style="font-size:.75rem;color:var(--text-muted);font-weight:500"><i class="fas fa-calendar mr-1"></i>${r.work_calendar||'Flexible'}</span>
            <button onclick="showBookingCalendar(${i},${r.opportunity_id},'${r.ngo_name.replace(/'/g,"\\'")}')" class="btn-primary sm"><i class="fas fa-calendar-plus text-xs"></i> Book Slot</button>
          </div>
        </div>`;
      });
      document.getElementById('recommendations-container').classList.remove('hidden');
    } else { document.getElementById('no-recommendations').classList.remove('hidden'); }
  } catch(e){document.getElementById('loading').classList.add('hidden');document.getElementById('no-recommendations').classList.remove('hidden');}
}

// ── Bookings ──
async function loadMyBookings(){
  document.getElementById('bookings-loading').classList.remove('hidden');
  document.getElementById('bookings-container').classList.add('hidden');
  document.getElementById('no-bookings').classList.add('hidden');
  try{
    const res=await fetch('/api/my-bookings/'+currentUser);
    const data=await res.json();
    document.getElementById('bookings-loading').classList.add('hidden');
    if(data&&data.length>0){
      const list=document.getElementById('bookings-list'); list.innerHTML='';
      data.forEach(b=>{
        list.innerHTML+=`
        <div class="slot-item" style="background:var(--surface)">
          <div style="display:flex;align-items:center;gap:16px">
            <div style="width:50px;height:50px;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:var(--accent-light);border:1px solid rgba(42,111,106,.2);flex-shrink:0">
              <span style="font-family:'Playfair Display',serif;font-size:1rem;font-weight:700;color:var(--accent)">${new Date(b.date).getDate()}</span>
              <span style="font-size:.6rem;color:var(--accent);text-transform:uppercase;font-weight:600">${new Date(b.date).toLocaleString('en',{month:'short'})}</span>
            </div>
            <div>
              <p style="font-weight:700;color:var(--text);font-size:.95rem;margin-bottom:2px">${b.ngo_name}</p>
              <p style="font-size:.8rem;color:var(--text-muted)">${b.start_time} – ${b.end_time} <span style="opacity:.5">·</span> ${b.description||''}</p>
            </div>
          </div>
          <span class="badge badge-green" style="font-size:.7rem"><i class="fas fa-check text-xs"></i> Confirmed</span>
        </div>`;
      });
      document.getElementById('bookings-container').classList.remove('hidden');
    } else { document.getElementById('no-bookings').classList.remove('hidden'); }
  } catch(e){document.getElementById('bookings-loading').classList.add('hidden');document.getElementById('no-bookings').classList.remove('hidden');}
}

// ── Explore Opportunities ──
async function loadAllOpportunities(){
  document.getElementById('explore-loading').classList.remove('hidden');
  document.getElementById('explore-grid').classList.add('hidden');
  try{
    const hr=await fetch('/api/heatmap'); allOpps=await hr.json();
    document.getElementById('explore-loading').classList.add('hidden');
    document.getElementById('explore-grid').classList.remove('hidden');
    renderExploreGrid(allOpps);
  } catch(e){document.getElementById('explore-loading').classList.add('hidden');}
}
function renderExploreGrid(opps){
  const g=document.getElementById('explore-grid'); g.innerHTML='';
  const ic={'emergency':'#C0392B','high':'#C65A2E','medium':'#2A6F6A','standard':'#6B6355'};
  opps.slice(0,24).forEach(o=>{
    const c=ic[o.importance||'standard'];
    const nm = o.ngo_name || o.name || 'Opportunity';
    const views = o.interactions ?? o.interaction_count ?? 0;
    g.innerHTML+=`
    <div class="card p-5 shadow-sm">
      <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:10px">
        <h3 style="font-family:'Playfair Display',serif;font-size:1.05rem;font-weight:700;color:var(--text)">${nm}</h3>
        <span class="badge" style="background:#fff;border-color:var(--border);color:${c};font-size:.6rem;font-weight:700">${(o.importance||'standard').toUpperCase()}</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin-top:12px">
        <div class="prog-bar" style="flex:1;background:var(--border)"><div class="prog-primary" style="width:${Math.min((o.heat||0)*100,100)}%"></div></div>
        <span style="font-size:.75rem;color:var(--text-muted);flex-shrink:0;font-weight:600">${views} views</span>
      </div>
    </div>`;
  });
}
function filterExplore(){
  const q=document.getElementById('explore-search').value.toLowerCase();
  renderExploreGrid(allOpps.filter(o=>{
    const nm = o.ngo_name || o.name || '';
    return nm.toLowerCase().includes(q) || (o.importance||'').toLowerCase().includes(q);
  }));
}

// ── Booking modal ──
let currentOppId=null;
async function showBookingCalendar(idx,oppId,ngoName){
  currentOppId=oppId;
  const mo=document.getElementById('modal-opp-name');
  if(mo) mo.textContent=ngoName||'Scheduling Slot';
  document.getElementById('booking-modal').classList.add('open');
  document.getElementById('calendar-loading').classList.remove('hidden');
  document.getElementById('calendar-content').classList.add('hidden');
  document.getElementById('no-slots').classList.add('hidden');
  try{
    const res=await fetch('/api/slots/'+oppId);
    const slots=await res.json();
    document.getElementById('calendar-loading').classList.add('hidden');
    if(slots&&slots.length>0){
      const list=document.getElementById('slots-list'); list.innerHTML='';
      slots.forEach(s=>{
        list.innerHTML+=`
        <div class="slot-item" style="margin-bottom:8px">
          <div>
            <p style="font-size:.9rem;font-weight:600;color:var(--text);margin-bottom:2px">${s.date} <span style="color:var(--border)">|</span> ${s.start_time}–${s.end_time}</p>
            <p style="font-size:.75rem;color:var(--text-muted)">${s.available_spots} slots available</p>
          </div>
          <button onclick="bookSlot(${s.slot_id},${oppId})" class="btn-primary sm" ${s.available_spots===0?'disabled style="opacity:.4;cursor:not-allowed"':''}>Select</button>
        </div>`;
      });
      document.getElementById('calendar-content').classList.remove('hidden');
    } else { document.getElementById('no-slots').classList.remove('hidden'); }
  } catch(e){document.getElementById('calendar-loading').classList.add('hidden');document.getElementById('no-slots').classList.remove('hidden');}
}

function closeBookingModal(){document.getElementById('booking-modal').classList.remove('open');}

async function bookSlot(slotId,oppId){
  try{
    const res=await fetch('/api/book',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({student_id:currentUser,slot_id:slotId,notes:'VolunteerIQ UI booking'})});
    const data=await res.json();
    if(data.success){showAlert('Booking confirmed!','success');closeBookingModal();loadDashboardStats();}
    else showAlert(data.message,'error');
  } catch(e){showAlert('Booking failed','error');}
}

// ── My Impact ──
async function loadMyImpact(){
  try{
    const res=await fetch('/api/analytics/'+currentUser);
    const d=await res.json();
    const eh=document.getElementById('impact-hours'); if(eh)eh.textContent=d.impact_hours+'h';
    const ep=document.getElementById('impact-projects'); if(ep)ep.textContent=d.projects_completed;
    const eq=document.getElementById('impact-quality'); if(eq)eq.textContent=d.avg_match_quality+'%';

    destroyChart('radar'); destroyChart('bar');
    const rCtx=document.getElementById('skills-radar-chart');
    if(rCtx&&d.skills_radar){
      charts['radar']=new Chart(rCtx,{type:'radar',data:{labels:d.skills_radar.labels,datasets:[{label:'Skills',data:d.skills_radar.values,backgroundColor:'rgba(198,90,46,.15)',borderColor:'#C65A2E',pointBackgroundColor:'#A84422',pointBorderColor:'#fff',pointRadius:4}]},options:{scales:{r:{grid:{color:'rgba(30,27,22,.08)'},pointLabels:{color:'#6B6355',font:{family:'Inter',size:11,weight:'600'}},ticks:{display:false},angleLines:{color:'rgba(30,27,22,.06)'}}},plugins:{legend:{display:false}},responsive:true,maintainAspectRatio:false}});
    }
    const bCtx=document.getElementById('priority-bar-chart');
    if(bCtx&&d.category_distribution){
      charts['bar']=new Chart(bCtx,{type:'bar',data:{labels:d.category_distribution.labels,datasets:[{data:d.category_distribution.values,backgroundColor:['#C65A2E','#2A6F6A','#C4B9AC','#8B7D6B'],borderRadius:6,borderWidth:0}]},options:{plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#6B6355',font:{family:'Inter',size:10,weight:'600'}}},y:{grid:{color:'rgba(30,27,22,.06)'},ticks:{color:'#6B6355',font:{family:'Inter',size:10}}}},responsive:true,maintainAspectRatio:false}});
    }
  } catch(e){}
}

// ── System Overview ──
function drawSparkline(canvasId,data,color){
  destroyChart(canvasId);
  const ctx=document.getElementById(canvasId);
  if(!ctx)return;
  charts[canvasId]=new Chart(ctx,{type:'line',data:{labels:data.map((_,i)=>i),datasets:[{data,borderColor:color,fill:true,backgroundColor:color.replace(')',',0.15)').replace('rgb','rgba'),tension:.4,pointRadius:0,borderWidth:2}]},options:{plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{display:false},y:{display:false}},animation:{duration:600},responsive:false,maintainAspectRatio:false}});
}

async function loadSystemOverview(){
  try{
    const [or,pr]=await Promise.all([fetch('/api/overview'),fetch('/api/performance')]);
    const ov=await or.json(); const perf=await pr.json();
    
    document.getElementById('ov-students').textContent=ov.students?.value ?? ov.students ?? '—';
    document.getElementById('ov-opps').textContent=ov.opportunities?.value ?? ov.opportunities ?? '—';
    document.getElementById('ov-interactions').textContent=ov.interactions?.value ?? ov.interactions ?? '—';
    document.getElementById('ov-bookings').textContent=ov.bookings?.value ?? ov.bookings ?? '—';
    document.getElementById('ov-pos').textContent=ov.pos_feedback?.value ?? ov.pos_feedback ?? '—';
    document.getElementById('ov-neg').textContent=ov.neg_feedback?.value ?? ov.neg_feedback ?? '—';
    
    const colors={students:'rgb(198,90,46)',opportunities:'rgb(42,111,106)',interactions:'rgb(198,90,46)',bookings:'rgb(42,111,106)',pos_feedback:'rgb(45,122,58)',neg_feedback:'rgb(192,57,43)'};
    ['students','opportunities','interactions','bookings','pos_feedback','neg_feedback'].forEach(k=>{
      const trend = ov[k]?.spark || ov[k+'_trend'];
      if(trend) drawSparkline('spark-'+k, trend.slice(-14), colors[k]);
    });
    
    destroyChart('perf');
    const pc=document.getElementById('perf-chart');
    if(pc&&perf.labels){
      charts['perf']=new Chart(pc,{type:'line',data:{labels:perf.labels,datasets:[{label:'Match Score',data:perf.match_scores,borderColor:'#C65A2E',backgroundColor:'rgba(198,90,46,.08)',fill:true,tension:.4,pointRadius:0,borderWidth:2},{label:'Booking Rate',data:perf.booking_rates,borderColor:'#2A6F6A',backgroundColor:'rgba(42,111,106,.08)',fill:true,tension:.4,pointRadius:0,borderWidth:2}]},options:{plugins:{legend:{labels:{color:'#6B6355',font:{family:'Inter',size:11,weight:'600'},boxWidth:12,usePointStyle:true}}},scales:{x:{grid:{color:'rgba(30,27,22,.06)'},ticks:{color:'#6B6355',font:{family:'Inter',size:10}}},y:{grid:{color:'rgba(30,27,22,.06)'},ticks:{color:'#6B6355',font:{family:'Inter',size:10}}}},responsive:true,maintainAspectRatio:false}});
    }
  } catch(e){}
}

// ── Student Explorer ──
async function loadStudentExplorer(){
  document.getElementById('student-loading').classList.remove('hidden');
  document.getElementById('student-table-wrap').classList.add('hidden');
  try{
    const res=await fetch('/api/students'); allStudents=await res.json();
    document.getElementById('student-loading').classList.add('hidden');
    document.getElementById('student-table-wrap').classList.remove('hidden');
    renderStudentTable(allStudents);
  } catch(e){document.getElementById('student-loading').classList.add('hidden');}
}
function renderStudentTable(students){
  const tb=document.getElementById('student-table-body'); tb.innerHTML='';
  students.slice(0,50).forEach(s=>{
    const skills=(s.skills||'').split(',').slice(0,3).map(sk=>`<span class="badge badge-primary" style="font-size:.6rem">${sk.trim()}</span>`).join('');
    const w=Math.min((s.interaction_count||0)/10*100,100);
    tb.innerHTML+=`<tr>
      <td><div style="font-weight:700;color:var(--text);font-size:.85rem">${s.name}</div><div style="font-size:.7rem;color:var(--text-muted)">#${s.student_id}</div></td>
      <td style="color:var(--text-muted);font-size:.8rem;font-weight:500">${s.university||'—'}</td>
      <td><div style="display:flex;flex-wrap:wrap;gap:4px">${skills}</div></td>
      <td><div style="display:flex;align-items:center;gap:8px"><div class="prog-bar" style="width:60px;flex-shrink:0"><div class="prog-primary" style="width:${w}%"></div></div><span style="font-size:.75rem;color:var(--text-muted);font-weight:600">${s.interaction_count||0}</span></div></td>
    </tr>`;
  });
}
function filterStudents(){
  const q=document.getElementById('student-search').value.toLowerCase();
  renderStudentTable(allStudents.filter(s=>(s.name||'').toLowerCase().includes(q)||(s.skills||'').toLowerCase().includes(q)||(s.university||'').toLowerCase().includes(q)));
}


// ── NGO Dashboard ──
async function loadNGODashboard(){
  try{
    destroyChart('ngo-bar'); destroyChart('ngo-doughnut');
    const hr=await fetch('/api/heatmap'); const heat=await hr.json();
    const top=heat.slice(0,6);
    const bc=document.getElementById('ngo-bar-chart');
    if(bc){
      charts['ngo-bar']=new Chart(bc,{type:'bar',data:{labels:top.map(o=>(o.ngo_name||o.name||'').slice(0,18)),datasets:[{data:top.map(o=>o.interactions??o.interaction_count??0),backgroundColor:'#C65A2E',borderRadius:6,borderWidth:0}]},options:{plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#6B6355',font:{family:'Inter',size:9,weight:'600'}}},y:{grid:{color:'rgba(30,27,22,.06)'},ticks:{color:'#6B6355',font:{family:'Inter',size:9}}}},responsive:true,maintainAspectRatio:false}});
    }
    const dc=document.getElementById('ngo-doughnut-chart');
    if(dc){
      charts['ngo-doughnut']=new Chart(dc,{type:'doughnut',data:{labels:['Emergency','High','Medium','Standard'],datasets:[{data:[12,28,45,15],backgroundColor:['#C0392B','#C65A2E','#2A6F6A','#C4B9AC'],borderWidth:1,borderColor:'#fff',hoverOffset:4}]},options:{plugins:{legend:{labels:{color:'#6B6355',font:{family:'Inter',size:10,weight:'600'},boxWidth:12,usePointStyle:true}}},cutout:'65%',responsive:true,maintainAspectRatio:false}});
    }
    const rr=await fetch('/api/students'); const studs=await rr.json();
    const tb=document.getElementById('ngo-volunteer-table'); tb.innerHTML='';
    studs.slice(0,8).forEach(s=>{
      const score=Math.round(65+Math.random()*30);
      tb.innerHTML+=`<tr>
        <td style="font-weight:700;color:var(--text);font-size:.84rem">${s.name}</td>
        <td style="color:var(--text-muted);font-size:.8rem;font-weight:500">${s.university||'—'}</td>
        <td>${(s.skills||'').split(',').slice(0,2).map(sk=>`<span class="badge badge-primary" style="font-size:.65rem">${sk.trim()}</span>`).join(' ')}</td>
        <td><div style="display:flex;align-items:center;gap:8px"><div class="prog-bar" style="width:60px"><div class="prog-accent" style="width:${score}%"></div></div><span style="font-size:.75rem;color:var(--text-muted);font-weight:600">${score}%</span></div></td>
        <td><span class="badge badge-green" style="font-size:.65rem">Ranked</span></td>
      </tr>`;
    });
  } catch(e){}
}

// ── Post Opportunity ──
async function postOpportunity(){
  const payload={ngo_name:document.getElementById('opportunity-ngo-name').value,description:document.getElementById('opportunity-desc').value,required_skills:document.getElementById('opportunity-skills').value,importance:document.getElementById('opportunity-importance').value,work_calendar:document.getElementById('opportunity-calendar').value};
  if(!payload.ngo_name||!payload.description){showAlert('Please fill required fields','error');return;}
  try{
    const res=await fetch('/api/opportunities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const data=await res.json();
    if(data.success){
      showAlert('Opportunity posted!','success');
      document.getElementById('opportunity-desc').value='';
      document.getElementById('opportunity-skills').value='';
    } else showAlert(data.message||'Failed','error');
  } catch(e){showAlert('Network error','error');}
}
</script>
"""

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

start_idx = text.find('<script>')
end_idx = text.find('</script>', start_idx) + 9

new_text = text[:start_idx] + P4.strip() + text[end_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("SUCCESS: script block replaced.")
