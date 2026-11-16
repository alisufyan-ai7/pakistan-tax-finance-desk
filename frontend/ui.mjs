import { DEMO, MONTHS, formatPKR, transactionsForYear, summaryForYear,
  coverageSummary, monthlyMovement, hypotheticalBuffer, monthPulseSummary } from "./demo-data.mjs";

const state = { view:"overview", year:2027, search:"",
  opening:180000, essential:85000, reserveMonths:6 };
const root = document.getElementById("app");
const nav = Array.from(document.querySelectorAll("[data-view]"));
const titles = {
  overview:["Your money, at a glance.","This month’s spending, bills to check, expected investment dates and follow-ups — shown using a fictional snapshot.","Overview"],
  accounts:["Know what's covered.","Track accounts, source periods and missing statement months before trusting balances.","Accounts & coverage"],
  transactions:["Bills & spending.","See example upcoming bills, activity and evidence gaps. Nothing is marked paid without proof.","Transactions"],
  accountant:["Turn uncertainty into questions.","Keep your accountant's drafts, source requests and actual filed evidence distinct.","Accountant review"],
  tax:["Evidence before tax numbers.","Year-specific Pakistan tax rules, withholding and wealth continuity will require verified source documents.","Tax & wealth"],
  planning:["Investments & plans.","See illustrative holdings, possible return dates and savings goals without guaranteed return claims.","Planning"],
  security:["Private by design.","Follow the security gates required before this workspace can work with genuine bank or FBR records.","Security & status"],
};
function e(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}
function title(text,desc,action="") {
  return '<div class="panel-head"><div><h2 class="panel-title">'+e(text)+'</h2><p class="panel-desc">'+e(desc)+'</p></div>'+action+'</div>';
}
function metric(label,value,footer,icon,footClass="") {
  return '<article class="metric-card"><div class="metric-top"><span class="metric-label">'+e(label)+
    '</span><span class="metric-icon" aria-hidden="true">'+e(icon)+'</span></div>'+
    '<div class="metric-number">'+e(value)+'</div><div class="metric-foot '+e(footClass)+'">'+e(footer)+'</div></article>';
}
function pill(value) {
  const v=String(value);
  const cls=/review|required|missing|unclassified|estimate|requested|draft|unsupported/i.test(v)?"":/linked|reviewed|observed/i.test(v)?"green":"gray";
  return '<span class="pill '+cls+'">'+e(v)+'</span>';
}
function accountsMini(year) {
  const sums = coverageSummary(year);
  const observed = sums.counts.observed, all = sums.accountMonths;
  const percent = Math.round(observed/all*100);
  return '<div class="progress-line"><strong>Observed account-months</strong><span>'+observed+' of '+all+'</span></div>'+
    '<div class="progress-track"><div class="progress-fill" style="width:'+percent+'%"></div></div>'+
    '<p class="inline-note">Observed ≠ independently verified balances. Partial and missing months must remain unknown until supported by source evidence.</p>'+
    '<div class="divide"></div>'+
    Object.entries(sums.grid).map(([account,months]) => {
      const a=DEMO.accounts.find(x=>x.id===account);
      return '<div class="account-coverage"><div class="account-label"><span>'+e(a?.name||"Unknown")+'</span>'+
        '<span>'+months.filter(m=>m==="observed").length+'/12 observed</span></div>'+
        '<div class="coverage-grid">'+months.map((s,i)=>'<div class="coverage-cell '+e(s)+'" title="'+e(MONTHS[i]+": "+s)+'" role="img" aria-label="'+e(MONTHS[i]+": "+s)+'"></div>').join("")+'</div></div>';
    }).join("")+
    '<div class="coverage-months">'+MONTHS.map(m=>'<span>'+m+'</span>').join("")+'</div>'+
    '<div class="coverage-note"><span><i class="dot"></i>Observed</span><span><i class="dot out"></i>Partial</span><span><i class="dot" style="background:#e8ecea"></i>Missing</span><span><i class="dot" style="background:#d9bdca"></i>Unsupported</span></div>';
}
function movementsChart(year) {
  const rows = monthlyMovement(year);
  const largest = Math.max(1,...rows.flatMap(x=>[x.incoming,x.outgoing]));
  return '<div class="chart" role="img" aria-label="Illustrative monthly inflow and outflow bars, not complete account history">'+
    rows.map(x=>{
      const ih=x.incoming?Math.max(3,Math.round(x.incoming/largest*177)):2;
      const oh=x.outgoing?Math.max(3,Math.round(x.outgoing/largest*177)):2;
      return '<div class="chart-column"><div class="bar in" style="height:'+ih+'px" title="'+e(x.label)+' illustrative inflow"></div>'+
        '<div class="bar out" style="height:'+oh+'px" title="'+e(x.label)+' illustrative outflow"></div></div>';
    }).join("")+'</div><div class="chart-labels">'+MONTHS.map(x=>'<span>'+x+'</span>').join("")+'</div>'+
    '<div class="legend"><span><i class="dot"></i>Sample inflows</span><span><i class="dot out"></i>Sample outflows</span></div>';
}
function transactionRows(rows) {
  return rows.map(t=>{
    const account = DEMO.accounts.find(a=>a.id===t.account);
    const signed = t.direction==="in"?"+":t.direction==="out"?"−":"⇄ ";
    const mc=t.direction==="in"?"credit":t.direction==="out"?"debit":"";
    return '<tr><td><div class="table-strong">'+e(t.description)+'</div><div class="subtext">'+e(account?.name??"")+" · "+e(t.category)+'</div></td>'+
      '<td>'+e(t.date)+'</td><td>'+pill(t.status)+'</td>'+
      '<td class="money '+mc+'">'+signed+e(formatPKR(t.amountMinor))+'</td></tr>';
  }).join("") || '<tr><td colspan="4"><div class="empty">No fictional transactions match this filter and tax year.</div></td></tr>';
}
function transactionsPanel(year,limit=6) {
  const rows=transactionsForYear(year).slice(0,limit);
  return '<section class="panel">'+title("Recent source movements","Fictional examples only; transfers are not income.",
    '<button class="section-link" type="button" data-go="transactions">View all transactions →</button>')+
    '<div class="table-scroller"><table class="data-table"><thead><tr><th>Transaction</th><th>Posted</th><th>Source status</th><th style="text-align:right">Movement</th></tr></thead>'+
    '<tbody>'+transactionRows(rows)+'</tbody></table></div></section>';
}
function reviewList(limit=4) {
  return '<div class="list">'+DEMO.reviews.slice(0,limit).map(item=>
    '<div class="list-entry"><div class="list-icon" aria-hidden="true">!</div><div class="list-body">'+
    '<div class="list-name">'+e(item.title)+'</div><div class="list-meta">'+e(item.type)+' · '+e(item.detail)+'</div>'+
    pill(item.status)+'</div></div>').join("")+'</div>';
}

/* Owner-first, plain-language visual pulse: only fictional snapshot assumptions.
   Nothing here is inferred from real bank data or the year-wide ledger samples. */
function shortDate(value) {
  if(!value)return "Date not known";
  return new Intl.DateTimeFormat("en-PK",{day:"numeric",month:"short",
    timeZone:"UTC"}).format(new Date(value+"T12:00:00Z"));
}
function pulseBills(limit=4) {
  const p=monthPulseSummary();
  const rows=p.bills.filter(x=>x.state!=="PAID_SAMPLE").slice(0,limit);
  return '<section class="panel pulse-panel">'+
    title("Bills to check","Scheduled examples; no payment has been verified.",
      '<button class="section-link" type="button" data-go="transactions">All sample bills →</button>')+
    '<div class="pulse-list">'+rows.map(bill=>
      '<div class="pulse-list-row"><div class="pulse-mini-icon" aria-hidden="true">▣</div>'+
      '<div class="pulse-main"><strong>'+e(bill.name)+'</strong>'+
      '<span>'+e(bill.cycle)+' · '+e(shortDate(bill.dueOn))+'</span></div>'+
      '<div class="pulse-right"><strong>'+e(formatPKR(bill.displayAmountMinor))+'</strong>'+
      '<span class="pulse-tag '+(bill.needsChecking?'amber':'muted')+'">'+
      (bill.needsChecking?'Check payment':'Schedule unverified')+'</span></div></div>'
    ).join("")+'</div><p class="pulse-helper">This is not a payment reminder from your bank. Confirm due dates and whether anything was paid.</p></section>';
}
function pulseInvestments(limit=3) {
  const p=monthPulseSummary();
  return '<section class="panel pulse-panel">'+
    title("Investments & next returns","Illustrative holdings. Expected dates are not guaranteed payouts.",
      '<button type="button" class="section-link" data-go="planning">View investments →</button>')+
    '<div class="pulse-list">'+p.investments.slice(0,limit).map(item=>
      '<div class="pulse-investment"><div class="pulse-main"><strong>'+e(item.name)+'</strong>'+
      '<span>'+e(item.kind)+' · Example capital '+e(formatPKR(item.principalMinor))+'</span></div>'+
      '<div class="pulse-return"><strong>'+(item.nextReturnOn?e(shortDate(item.nextReturnOn)):'Not scheduled')+'</strong>'+
      '<span>'+(item.quotedReturnMinor!==null
         ?e(formatPKR(item.quotedReturnMinor))+' quoted'
         :'Variable return')+'</span></div></div>'
    ).join("")+'</div><p class="pulse-helper">No actual profit received, market value or tax has been verified.</p></section>';
}
function pulseSpending() {
  const p=monthPulseSummary();
  const max=Math.max(1,...p.categories.map(x=>x.currentMinor));
  return '<section class="panel pulse-panel">'+
    title("Where the example money goes","Illustrative November category comparison; real expense coverage is incomplete.")+
    '<div class="pulse-spend-list">'+p.categories.map(x=>{
      const pct=Math.max(2,Math.round(x.currentMinor/max*100));
      const change=x.priorMinor>0?Math.round((x.currentMinor-x.priorMinor)*100/x.priorMinor):null;
      return '<div class="pulse-spend-row"><div class="pulse-spend-label"><span>'+e(x.name)+'</span>'+
        '<strong>'+e(formatPKR(x.currentMinor))+'</strong></div>'+
        '<div class="pulse-spend-track"><div class="pulse-spend-bar" style="width:'+pct+'%"></div></div>'+
        '<div class="pulse-spend-change">'+(change===null?'Comparison unavailable':
          (change>0?'+'+change:change)+'% example vs prior')+'</div></div>';
    }).join("")+'</div>'+
    '<p class="pulse-helper"><strong>Important:</strong> these bars illustrate the planned view. They are not calculated from your statements.</p></section>';
}
function pulseFollowups(limit=3) {
  const p=monthPulseSummary();
  return '<section class="panel pulse-panel">'+
    title("What needs your attention","A clear next-action list, not an automated notification.",
      '<button class="section-link" type="button" data-go="accountant">Reviews →</button>')+
    '<div class="pulse-list">'+p.followups.slice(0,limit).map((item,i)=>
      '<div class="pulse-followup"><span class="pulse-sequence" aria-hidden="true">'+(i+1)+'</span>'+
      '<div class="pulse-main"><strong>'+e(item.title)+'</strong>'+
      '<span>'+e(item.subtitle)+'</span></div><span class="pulse-due">'+e(shortDate(item.dueOn))+'</span></div>'
    ).join("")+'</div><p class="pulse-helper">Future version: assign, resolve and remind with your approval.</p></section>';
}
function pulseHeadline() {
  const p=monthPulseSummary();
  return '<section class="pulse-hero" aria-label="Illustrative monthly financial pulse">'+
    '<div class="pulse-hero-copy"><span class="pulse-demo-label">● FICTIONAL MONTHLY SNAPSHOT</span>'+
    '<h2>Your month, in one look.</h2>'+
    '<p>'+e(p.monthLabel)+' · Example snapshot as of '+e(shortDate(p.asOf))+
    '. This is what your real dashboard will show after source verification.</p></div>'+
    '<div class="pulse-hero-alert"><span>Spending comparison</span>'+
    '<strong>'+(p.exampleGrowthPct>0?'+':'')+e(String(p.exampleGrowthPct))+'%</strong>'+
    '<small>Illustrative only · actual change unknown</small></div></section>'+
    '<section class="pulse-stats" aria-label="Illustrative monthly summary">'+
    '<div class="pulse-stat"><span>Example spending so far</span><strong>'+e(formatPKR(p.exampleCurrentExpenseMinor))+'</strong>'+
    '<small>Not verified from statements</small></div>'+
    '<div class="pulse-stat"><span>Bills to check</span><strong>'+p.billReviewCount+'</strong>'+
    '<small>Due or overdue in sample</small></div>'+
    '<div class="pulse-stat"><span>Sample invested capital</span><strong>'+e(formatPKR(p.exampleInvestedPrincipalMinor))+'</strong>'+
    '<small>Not your actual portfolio</small></div>'+
    '<div class="pulse-stat"><span>Open follow-ups</span><strong>'+p.pendingFollowupCount+'</strong>'+
    '<small>Examples to resolve</small></div></section>';
}

function overview() {
  const s=summaryForYear(state.year), cov=coverageSummary(state.year);
  return pulseHeadline()+
    '<div class="layout-2 pulse-main-grid">'+pulseBills(3)+pulseInvestments(2)+'</div>'+
    '<div class="layout-2 pulse-main-grid">'+pulseSpending()+pulseFollowups(3)+'</div>'+
    '<div class="pulse-section-title"><div><h2>Explore the evidence</h2>'+
    '<p>Additional fictional ledger screens. Missing statement months never mean zero spending.</p></div></div>'+
    '<div class="cards">'+
    metric("Illustrative liquid position",formatPKR(s.illustrativeLiquidMinor),"Different fictional ledger sample · not verified","◫")+
    metric("Sample cash inflows",formatPKR(s.incomeMinor),"Unclassified receipts are not taxable income","↗","warn")+
    metric("Sample cash outflows",formatPKR(s.outflowMinor),"Incomplete ledger sample, not full spending","↘")+
    metric("Open evidence questions",String(DEMO.reviews.length),"Sample accountant review list","!","warn")+
    '</div><div class="layout-2"><section class="panel">'+
    title("Financial movement","Separate fictional ledger sample · fiscal July–June",'<span class="stat-chip">Sample only</span>')+
    movementsChart(state.year)+'</section><section class="panel">'+
    title("Statement coverage","Missing months are never assumed to have zero activity.",'<button class="section-link" data-go="accounts" type="button">See all →</button>')+
    accountsMini(state.year)+'</section></div>'+
    '<div class="layout-2">'+transactionsPanel(state.year,5)+
    '<section class="panel">'+title("Accountant review sample","Example evidence queue, not connected to your accountant.",'<button class="section-link" data-go="accountant" type="button">Review queue →</button>')+
    reviewList(3)+'</section></div>'+
    '<section class="banner-card"><div><strong>A clear dashboard needs complete records.</strong>'+
    '<p>'+cov.counts.missing+' account-months are missing in this separate fictional ledger example. Actual accounts, bills, investments and returns will remain unverified until source evidence is available.</p></div>'+
    '<button type="button" data-go="accounts">Review coverage</button></section>';
}
function accounts() {
  const cov=coverageSummary(state.year);
  return '<div class="split">'+DEMO.accounts.map(a=>
    '<article class="account-tile"><div class="account-name">'+e(a.name)+'</div>'+
    '<div class="account-amount">'+e(formatPKR(a.balanceMinor))+'</div>'+
    '<div class="account-meta">'+e(a.institution)+' · '+e(a.type)+' · '+e(a.owner)+
    '<br>Fictional amount · '+(a.lastEvidence?'Sample evidence '+e(a.lastEvidence):'No independent statement evidence')+'</div></article>').join("")+
    '<article class="account-tile"><div class="account-name">Source coverage summary</div>'+
    '<div class="account-amount">'+cov.counts.observed+' / '+cov.accountMonths+'</div>'+
    '<div class="account-meta">Observed account-months. The remainder may be missing, partial or unsupported. Not an account-balance verification.</div></article></div>'+
    '<section class="panel" style="margin-top:18px">'+title("Bank statement period map","Fiscal year starts in July. Each square is one account and one month.")+
    accountsMini(state.year)+'</section>'+
    '<div class="warning-note">Real statement uploads are locked until encrypted canonical storage, private MFA/deployment and supported bank-format verification pass. This public preview must never receive original bank PDFs or statements.</div>';
}
function transactions() {
  const rows=transactionsForYear(state.year,state.search);
  return '<div class="pulse-subsection">'+pulseBills(4)+'</div>'+
    '<section class="panel">'+title("Transaction review","Search fictional records; classification and reconciliation write actions are intentionally disabled.")+
    '<div class="form-controls"><label class="field" for="transactionSearch">Search description, source or status'+
    '<input id="transactionSearch" class="input-search" type="search" autocomplete="off" maxlength="120" placeholder="Try consulting, expense, review..." value="'+e(state.search)+'"></label>'+
    '<span class="small-status gray" id="transactionCount">'+rows.length+' sample movements</span></div>'+
    '<div class="table-scroller"><table class="data-table"><thead><tr><th>Movement</th><th>Posted</th><th>Evidence status</th><th style="text-align:right">Amount</th></tr></thead>'+
    '<tbody id="transactionRows">'+transactionRows(rows)+'</tbody></table></div></section>'+
    '<p class="inline-note">Own transfers are separated from inflows and outflows. A bank credit is not automatically taxable income. Review decisions require authenticated evidence and an auditable backend write path.</p>';
}
function accountant() {
  return '<div class="cards">'+
    metric("Sample questions",String(DEMO.reviews.length),"Not synced with your accountant","▤")+
    metric("TY2026 workbook","DRAFT","A workbook is not a filed return","◇")+
    metric("Filed return proof","Unavailable","Official IRIS acknowledgment not verified","!")+
    metric("Review export","Locked","Requires authenticated evidence store","⇧")+
    '</div><div class="layout-2"><section class="panel">'+
    title("Evidence review queue","Provisional questions prepared from fictional source gaps.")+
    reviewList()+'</section><section class="panel">'+title("Accountant workflow","Source-first, versioned and owner-controlled.")+
    '<div class="feature-list">'+
    '<div class="feature-line">Keep each draft version and formula review separate from filed history.</div>'+
    '<div class="feature-line">Attach original source citations and preserve uncertainty.</div>'+
    '<div class="feature-line">Request clarification, record answers and audit every decision.</div>'+
    '<div class="feature-line">Require independent IRIS acknowledgment before marking a return FILED.</div>'+
    '</div><div class="divide"></div><div class="warning-note">A review manifest exists in backend synthetic tests, but real accountant evidence persistence, exports and access controls are not yet enabled.</div>'+
    '</section></div>';
}
function tax() {
  return '<div class="cards">'+
    metric("Tax engine","Not verified","Mixed-income rules still incomplete","▧")+
    metric("Filed return","Not verified","Requires independent IRIS evidence","▤")+
    metric("Withholding","Review required","Final vs adjustable not classified","◈")+
    metric("Wealth bridge","Partial","Missing account/assets/cash evidence","◫")+
    '</div><div class="layout-2"><section class="panel">'+
    title("Tax-year rule coverage","Status of actual software capabilities — not a tax liability calculation.")+
    '<div class="list">'+[
      ["Salary slabs","Narrow preview","2026 and 2027 illustrative component only"],
      ["Business & investment income","Not implemented","Mixed heads and credits need year-specific law"],
      ["Withholding tax character","Not verified","Final, minimum and adjustable treatments remain unsupported"],
      ["Capital gains & asset disposal","Not implemented","Need acquisition dates, rates and source provenance"],
      ["Wealth continuity","Review only","Draft vs filed evidence must not be conflated"],
    ].map(([n,status,note])=>'<div class="list-entry"><div class="list-icon" aria-hidden="true">◇</div><div class="list-body"><div class="list-name">'+e(n)+'</div><div class="list-meta">'+e(note)+'</div>'+pill(status)+'</div></div>').join("")+
    '</div></section><section class="panel">'+title("Wealth reconciliation","A financial position is only as reliable as the source coverage behind it.")+
    '<div class="empty">No verified net worth or FBR payable/refund is available. This preview never estimates tax savings from unsupported statute or ambiguous bank credits.</div>'+
    '<div class="divide"></div><div class="feature-list"><div class="feature-line">Preserve filed return originals and revisions.</div>'+
    '<div class="feature-line">Match bank, cash, loans, assets and investment lots by tax year.</div>'+
    '<div class="feature-line">Use independently sourced Finance Act rules with reviewed golden cases.</div></div></section></div>';
}
function goalCard(goal) {
  const ratio=Math.max(0,Math.min(100,Math.round(goal.savedMinor/goal.targetMinor*100)));
  return '<article class="panel"><div class="panel-head"><div><h2 class="panel-title">'+e(goal.title)+'</h2>'+
    '<p class="panel-desc">'+e(goal.note)+'</p></div><span class="stat-chip">'+ratio+'%</span></div>'+
    '<div class="metric-number">'+e(formatPKR(goal.savedMinor))+'</div>'+
    '<div class="progress-track"><div class="progress-fill" style="width:'+ratio+'%"></div></div>'+
    '<div class="progress-line"><span>Fictional progress</span><strong>Goal '+e(formatPKR(goal.targetMinor))+'</strong></div></article>';
}
function scenarioResult() {
  const result=hypotheticalBuffer({
    openingMinor:state.opening*100,
    monthlyEssentialMinor:state.essential*100,
    months:state.reserveMonths,
  });
  return '<div class="cards" style="margin:0">'+
    metric("Hypothetical reserve target",formatPKR(result.targetMinor),"Assumption only","◎")+
    metric("Hypothetical shortfall",formatPKR(result.shortfallMinor),"Not an observed liquidity gap","↗","warn")+
    metric("Tax savings","Unavailable","No deduction or legal rule assumed","▧")+
    metric("Source confidence","Not verified","This demonstration has no bank feed","!")+
    '</div>';
}
function planning() {
  return '<div class="pulse-subsection">'+pulseInvestments(3)+'</div>'+
    '<div class="split">'+DEMO.goals.map(goalCard).join("")+'</div>'+
    '<section class="panel" style="margin-top:18px">'+
    title("Emergency reserve simulator","Edit assumptions and see a hypothetical result. Nothing is saved or transferred.")+
    '<div class="scenario"><div class="split">'+
    '<label class="field">Fictional opening liquidity (PKR)<input id="scenarioOpening" type="number" min="0" max="100000000" step="1000" value="'+state.opening+'"></label>'+
    '<label class="field">Essential monthly expenses (PKR)<input id="scenarioEssential" type="number" min="0" max="10000000" step="1000" value="'+state.essential+'"></label>'+
    '<label class="field">Reserve months<select id="scenarioMonths">'+[3,4,6,9,12].map(n=>'<option value="'+n+'"'+(n===state.reserveMonths?' selected':'')+'>'+n+' months</option>').join("")+'</select></label>'+
    '</div><div id="scenarioOutput">'+scenarioResult()+'</div>'+
    '<p class="scenario-terms">These inputs are entirely hypothetical. A verified opening balance and source-complete account months will be required before real budgeting guidance is possible. No external requests or automatic actions occur.</p></div></section>';
}
function security() {
  const gates=[
    ["G1","Confidential finance ledger","In progress","Protected candidate and backups exist; active legacy plaintext tables not retired."],
    ["G2","Private authentication & hosting","Blocked","Actual private MFA/TLS, recovery and approved production hosting not certified."],
    ["G3","Real bank/FBR evidence","Blocked","Synthetic format contracts exist; real document adapters not certified."],
    ["G4","Year-specific FBR tax engine","Partial","Narrow salary preview only; mixed income/withholding law still requires review."],
    ["G5","Owner workflow","In progress","This is a static UI preview; authenticated end-to-end tests remain."],
  ];
  return '<section class="panel">'+title("Release gate status","The difference between a running demonstration and a private, financially trustworthy application.")+
    '<div class="table-scroller"><table class="data-table"><thead><tr><th>Gate</th><th>Scope</th><th>Status</th><th>Missing</th></tr></thead><tbody>'+
    gates.map(([gate,label,status,detail])=>'<tr><td class="table-strong">'+e(gate)+'</td><td>'+e(label)+'</td><td>'+pill(status)+'</td><td>'+e(detail)+'</td></tr>').join("")+
    '</tbody></table></div></section>'+
    '<div class="layout-2" style="margin-top:20px"><section class="panel">'+title("This preview's privacy properties","Only fictional objects, no network or browser persistence.")+
    '<div class="feature-list"><div class="feature-line">Static HTML, CSS and JavaScript with one same-origin, synthetic status request; no external fonts, trackers or financial API requests.</div>'+
    '<div class="feature-line">No file upload field or secret entry point.</div>'+
    '<div class="feature-line">No local storage, cookies or personally identifying samples.</div>'+
    '<div class="feature-line">No automatic financial transactions or filing.</div></div></section>'+
    '<section class="panel">'+title("Deployment boundary","Free public UI hosting is separate from secure financial operations.")+
    '<div class="warning-note">Railway hosts this public synthetic dashboard and a private PostgreSQL-connected status API. Full financial database security, MFA, private document storage, independent backups and authenticated real-data workflows still require separate acceptance.</div></section></div>';
}
function render() {
  const [heading,sub,breadcrumb]=titles[state.view] ?? titles.overview;
  document.getElementById("pageTitle").textContent=heading;
  document.getElementById("pageSummary").textContent=sub;
  document.getElementById("currentSection").textContent=breadcrumb;
  document.getElementById("taxYear").value=String(state.year);
  nav.forEach(b=>{
    const current=b.dataset.view===state.view;
    b.classList.toggle("active",current);
    if(current)b.setAttribute("aria-current","page");
    else b.removeAttribute("aria-current");
  });
  const views={overview,accounts,transactions,accountant,tax,planning,security};
  root.innerHTML=views[state.view]();
}
function go(view) {
  if(!Object.prototype.hasOwnProperty.call(titles,view))return;
  state.view=view;
  state.search="";
  render();
  window.scrollTo({top:0,behavior:"instant"});
}
document.addEventListener("click",event=>{
  const button=event.target.closest("[data-view],[data-go]");
  if(button)go(button.dataset.view??button.dataset.go);
});
document.getElementById("taxYear").addEventListener("change",event=>{
  const value=Number(event.target.value);
  if(DEMO.years.includes(value)){state.year=value;render();}
});
root.addEventListener("input",event=>{
  if(event.target.id==="transactionSearch"){
    state.search=event.target.value;
    const rows=transactionsForYear(state.year,state.search);
    document.getElementById("transactionRows").innerHTML=transactionRows(rows);
    document.getElementById("transactionCount").textContent=rows.length+" sample movements";
    return;
  }
  const id=event.target.id;
  if(!["scenarioOpening","scenarioEssential","scenarioMonths"].includes(id))return;
  const parsed=Number(event.target.value);
  if(!Number.isSafeInteger(parsed))return;
  if(id==="scenarioOpening"&&parsed>=0&&parsed<=100000000)state.opening=parsed;
  if(id==="scenarioEssential"&&parsed>=0&&parsed<=10000000)state.essential=parsed;
  if(id==="scenarioMonths"&&[3,4,6,9,12].includes(parsed))state.reserveMonths=parsed;
  try{document.getElementById("scenarioOutput").innerHTML=scenarioResult();}
  catch{document.getElementById("scenarioOutput").textContent="Invalid fictional scenario assumptions.";}
});
render();

/* Same-origin, exact-route synthetic status only. No financial inputs or secrets
   are ever placed in this request; real finance APIs remain unavailable. */
async function checkPrivatePreview() {
  const element=document.getElementById("backendConnection");
  if(!element)return;
  try{
    const response=await fetch("/api/preview/status?tax_year=2027",{
      method:"GET",credentials:"omit",cache:"no-store",
      headers:{"Accept":"application/json"}
    });
    if(!response.ok)throw new Error("Synthetic backend check failed");
    const payload=await response.json();
    if(payload.contract!=="personal_cfo_private_preview_status_v1" ||
       payload.synthetic_only!==true ||
       payload.backend!=="connected" ||
       payload.postgresql!=="private_connected" ||
       payload.canonical_finance_schema!=="NOT_CERTIFIED" ||
       payload.real_data_authorized!==false ||
       payload.owner_workspace?.financial_facts?.bank_balance_minor!==null ||
       payload.owner_workspace?.actions?.real_evidence_upload_enabled!==false)
      throw new Error("Unsupported preview readiness contract");
    element.textContent="Private synthetic backend + PostgreSQL connected";
    element.classList.add("connected");
  }catch{
    element.textContent="Private backend unavailable · demo remains local";
    element.classList.remove("connected");
  }
}
checkPrivatePreview();
