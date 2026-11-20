/* Real source-derived period selection. No source, account or money is persisted. */
const YEAR_MONTH=/^20[0-4][0-9]-(0[1-9]|1[0-2])$/;
const DATE=/^20[0-4][0-9]-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$/;
export function safePeriod(mode,value){
  if(mode==="all" && value==="all")return {mode:"all",value:"all"};
  if(mode==="month" && YEAR_MONTH.test(value))return {mode,value};
  if((mode==="year" || mode==="tax-year") &&
      /^20[0-4][0-9]$/.test(value))return {mode,value};
  return null;
}
export function periodContainsMonth(month,period){
  if(!YEAR_MONTH.test(month) || !period || !safePeriod(period.mode,period.value))return false;
  if(period.mode==="all")return true;
  if(period.mode==="month")return month===period.value;
  if(period.mode==="year")return month.slice(0,4)===period.value;
  return (+month.slice(0,4) - (month.slice(5,7)>="07"?0:1))===+period.value;
}
export function periodContainsDate(iso,period){
  return DATE.test(iso) && periodContainsMonth(iso.slice(0,7),period);
}
export function periodMonths(period) {
  if(!period || !safePeriod(period.mode,period.value))return [];
  if(period.mode==="all")return [];
  if(period.mode==="month")return [period.value];
  const year=+period.value;
  if(period.mode==="year")return Array.from({length:12},(_,i)=>year+"-"+String(i+1).padStart(2,"0"));
  return Array.from({length:12},(_,i)=>{
    const y=i<6?year:year+1;
    const m=i<6?i+7:i-5;
    return y+"-"+String(m).padStart(2,"0");
  });
}
export function periodTitle(period){
  if(!period || !safePeriod(period.mode,period.value))return "Source evidence";
  if(period.mode==="all")return "All available verified evidence";
  if(period.mode==="month"){
    const [year,month]=period.value.split("-").map(Number);
    return new Date(Date.UTC(year,month-1,1)).toLocaleDateString(
      "en-GB",{month:"long",year:"numeric",timeZone:"UTC"});
  }
  if(period.mode==="year")return "Calendar year "+period.value;
  return "Pakistan tax year "+period.value+"–"+String(+period.value+1).slice(-2);
}
export function observedPeriods({reports=[],candidates=[],properties=[]}={}){
  const months=new Set();
  for(const r of reports)for(const m of r.months??[]){
    if(YEAR_MONTH.test(m.month))months.add(m.month);
  }
  for(const candidate of candidates)if(DATE.test(candidate.date))months.add(candidate.date.slice(0,7));
  for(const p of properties)if(DATE.test(p.sale_date))months.add(p.sale_date.slice(0,7));
  const month=[...months].sort().reverse();
  const year=[...new Set(month.map(s=>s.slice(0,4)))].sort().reverse();
  const taxYear=[...new Set(month.map(s=>
    String(+s.slice(0,4)-(s.slice(5,7)>="07"?0:1))))].sort().reverse();
  return {month,year,taxYear};
}
export function sourcePeriodSummary(reports,period){
  if(!safePeriod(period?.mode,period?.value))return [];
  return reports.map(r=>{
    const months=(r.months??[]).filter(row=>periodContainsMonth(row.month,period));
    const sum=k=>months.reduce((n,m)=>n+m[k],0);
    return {
      source_hmac:r.source_hmac,
      source_name:r.source_name,
      statement_start:r.statement_start,
      statement_end:r.statement_end,
      covered_months:months.map(m=>m.month),
      movements:sum("transaction_count"),
      credits_minor:sum("gross_bank_credits_minor"),
      debits_minor:sum("gross_bank_debits_minor"),
      bank_profit_minor:sum("bank_labelled_profit_minor"),
      bank_profit_tax_minor:sum("bank_labelled_profit_tax_minor"),
      last_observed_balance_minor:months.length?months.at(-1).last_reported_balance_minor:null,
    };
  }).filter(s=>s.covered_months.length>0);
}
export function candidatePeriodEvidence(groups,period) {
  if(!safePeriod(period?.mode,period?.value))return [];
  return groups.map(g=>({
    group_id:g.group_id,
    rows:g.rows.filter(row=>periodContainsDate(row.date,period)),
  })).filter(g=>g.rows.length).map(g=>({
    ...g,
    outgoing_minor:g.rows.filter(x=>x.direction==="OUTBOUND").reduce((n,x)=>n+x.amount_minor,0),
    incoming_minor:g.rows.filter(x=>x.direction==="INBOUND").reduce((n,x)=>n+x.amount_minor,0),
  }));
}
