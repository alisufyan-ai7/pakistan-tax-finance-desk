// Public fictional UI fixtures. NO genuine owner records, network calls or credentials.
export const DEMO = {
  owner: "Demo owner",
  currency: "PKR",
  years: [2027, 2026, 2025],
  accounts: [
    { id: "demo-everyday", name: "Everyday account", institution: "Fictional Bank A", type: "Current", balanceMinor: 32845000, lastEvidence: "2026-11-04", owner: "Individual" },
    { id: "demo-savings", name: "Savings reserve", institution: "Fictional Bank B", type: "Savings", balanceMinor: 82500000, lastEvidence: "2026-10-31", owner: "Individual" },
    { id: "demo-cash", name: "Cash in hand", institution: "Owner-declared sample", type: "Cash", balanceMinor: 6900000, lastEvidence: null, owner: "Individual" },
  ],
  transactions: [
    { id:"demo-01", date:"2026-11-04", account:"demo-everyday", description:"Fictional consulting payment", category:"Business receipt · unreviewed", direction:"in", amountMinor:34200000, status:"Review required", taxYear:2027 },
    { id:"demo-02", date:"2026-10-30", account:"demo-everyday", description:"Illustrative household spending", category:"Living expense", direction:"out", amountMinor:7250000, status:"Reviewed sample", taxYear:2027 },
    { id:"demo-03", date:"2026-10-23", account:"demo-savings", description:"Fictional own-account transfer", category:"Own transfer · excluded", direction:"transfer", amountMinor:15000000, status:"Linked sample", taxYear:2027 },
    { id:"demo-04", date:"2026-09-12", account:"demo-everyday", description:"Illustrative tax withholding", category:"WHT · character unverified", direction:"out", amountMinor:2350000, status:"Review required", taxYear:2027 },
    { id:"demo-05", date:"2026-08-05", account:"demo-everyday", description:"Fictional consulting payment", category:"Business receipt · unreviewed", direction:"in", amountMinor:28500000, status:"Review required", taxYear:2027 },
    { id:"demo-06", date:"2026-07-18", account:"demo-everyday", description:"Illustrative software subscription", category:"Recurring candidate", direction:"out", amountMinor:890000, status:"Estimate only", taxYear:2027 },
    { id:"demo-07", date:"2026-05-10", account:"demo-everyday", description:"Fictional professional fee", category:"Business receipt · unreviewed", direction:"in", amountMinor:27000000, status:"Review required", taxYear:2026 },
    { id:"demo-08", date:"2026-04-09", account:"demo-everyday", description:"Illustrative household spending", category:"Living expense", direction:"out", amountMinor:6200000, status:"Reviewed sample", taxYear:2026 },
    { id:"demo-09", date:"2025-12-04", account:"demo-savings", description:"Fictional interest credit", category:"Profit on debt · unverified", direction:"in", amountMinor:2700000, status:"Review required", taxYear:2026 },
    { id:"demo-10", date:"2025-09-21", account:"demo-everyday", description:"Illustrative annual insurance", category:"Insurance", direction:"out", amountMinor:3250000, status:"Reviewed sample", taxYear:2026 },
    { id:"demo-11", date:"2025-03-11", account:"demo-everyday", description:"Fictional consulting payment", category:"Business receipt · unreviewed", direction:"in", amountMinor:24000000, status:"Review required", taxYear:2025 },
    { id:"demo-12", date:"2025-01-11", account:"demo-everyday", description:"Illustrative household spending", category:"Living expense", direction:"out", amountMinor:5500000, status:"Reviewed sample", taxYear:2025 },
  ],
  coverage: {
    2027: {
      "demo-everyday": ["observed","observed","partial","observed","missing","missing","missing","missing","missing","missing","missing","missing"],
      "demo-savings":  ["observed","observed","observed","partial","missing","missing","missing","missing","missing","missing","missing","missing"],
      "demo-cash":     ["unsupported","unsupported","unsupported","unsupported","missing","missing","missing","missing","missing","missing","missing","missing"],
    },
    2026: {
      "demo-everyday": ["observed","observed","partial","missing","observed","observed","observed","partial","missing","observed","observed","observed"],
      "demo-savings":  ["observed","partial","observed","observed","observed","observed","missing","missing","observed","observed","observed","observed"],
      "demo-cash":     ["unsupported","unsupported","unsupported","unsupported","unsupported","unsupported","unsupported","unsupported","unsupported","unsupported","unsupported","unsupported"],
    },
    2025: {
      "demo-everyday": ["observed","missing","partial","observed","observed","observed","missing","observed","observed","observed","observed","observed"],
      "demo-savings":  ["missing","missing","observed","observed","partial","observed","observed","observed","observed","observed","missing","observed"],
      "demo-cash":     Array(12).fill("unsupported"),
    },
  },
  reviews: [
    { id:"R-001", type:"Bank evidence", title:"Missing statement period", detail:"Sample current account · November 2026", status:"Evidence requested", priority:"High" },
    { id:"R-002", type:"Accountant draft", title:"Workbook formula cache unresolved", detail:"TY2026 draft · not filed evidence", status:"Owner review", priority:"High" },
    { id:"R-003", type:"Wealth", title:"Opening wealth evidence gap", detail:"Prior filed source vs current draft", status:"Review required", priority:"Medium" },
    { id:"R-004", type:"Transaction", title:"Unreviewed incoming credit", detail:"Sample consulting payment", status:"Unclassified", priority:"Medium" },
  ],
  // Deliberately independent hypothetical November snapshot. NOT parsed
  // from the bank transaction examples above or connected to the owner.
  monthPulse: {
    asOf:"2026-11-16",
    evidenceState:"FICTIONAL_SCENARIO_NOT_VERIFIED",
    actualSourceComplete:false,
    expenses:{
      hypotheticalCurrentMinor:24800000,
      hypotheticalComparablePriorMinor:20900000,
      categories:[
        {name:"Home & utilities",currentMinor:10300000,priorMinor:9400000},
        {name:"Groceries",currentMinor:5800000,priorMinor:4600000},
        {name:"Transport",currentMinor:3200000,priorMinor:2500000},
        {name:"Subscriptions",currentMinor:1500000,priorMinor:1200000},
        {name:"Other essentials",currentMinor:4000000,priorMinor:3200000},
      ]
    },
    bills:[
      {id:"sample-internet",name:"Home internet",amountMinor:1250000,dueOn:"2026-11-18",
       state:"PAYMENT_UNCONFIRMED",cycle:"Monthly"},
      {id:"sample-mobile",name:"Mobile plan",amountMinor:320000,dueOn:"2026-11-20",
       state:"PAYMENT_UNCONFIRMED",cycle:"Monthly"},
      {id:"sample-insurance",name:"Insurance contribution",amountMinor:3100000,
       dueOn:"2026-12-02",state:"SCHEDULE_CANDIDATE",cycle:"Annual"},
      {id:"sample-rent",name:"Home rent",amountMinor:6500000,dueOn:"2026-11-05",
       state:"PAID_SAMPLE",cycle:"Monthly"},
    ],
    investments:[
      {id:"sample-term",name:"Example term deposit",kind:"Fixed term",
       principalMinor:500000000,nextReturnOn:"2026-12-20",quotedReturnMinor:12500000,
       quoteKind:"FICTIONAL_FIXED_CONTRACT_QUOTE",maturityOn:"2027-12-20"},
      {id:"sample-fund",name:"Example mutual fund",kind:"Market-linked",
       principalMinor:165000000,nextReturnOn:null,quotedReturnMinor:null,
       quoteKind:"VARIABLE_UNKNOWN",maturityOn:null},
      {id:"sample-certificate",name:"Example savings certificate",kind:"Fixed term",
       principalMinor:200000000,nextReturnOn:"2027-02-12",quotedReturnMinor:18000000,
       quoteKind:"FICTIONAL_FIXED_CONTRACT_QUOTE",maturityOn:"2028-02-12"},
    ],
    followups:[
      {id:"sample-doc-1",title:"Request missing bank statement",dueOn:"2026-11-18",
       subtitle:"Needed before expenses can be verified",kind:"Evidence"},
      {id:"sample-bill-1",title:"Check internet payment",dueOn:"2026-11-19",
       subtitle:"Scheduled amount is not a payment confirmation",kind:"Bill"},
      {id:"sample-tax-1",title:"Review accountant's draft questions",dueOn:"2026-11-22",
       subtitle:"A draft workbook is not a filed return",kind:"Accountant"},
    ],
  },
  goals: [
    { id:"g1", title:"Emergency reserve", targetMinor:120000000, savedMinor:82500000, note:"Illustrative savings balance" },
    { id:"g2", title:"Annual tax buffer", targetMinor:30000000, savedMinor:8200000, note:"Hypothetical goal, not actual liability" },
  ],
};
export const MONTHS = ["Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun"];

export function formatPKR(minor) {
  if (minor === null || minor === undefined) return "Unknown";
  if (!Number.isSafeInteger(minor)) throw new TypeError("Only exact integer fictional minor units are supported");
  return "Rs " + new Intl.NumberFormat("en-PK", {minimumFractionDigits:0,maximumFractionDigits:0}).format(minor / 100);
}
export function yearFromDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new TypeError("Expected ISO date");
  const year = Number(value.slice(0,4)), month = Number(value.slice(5,7));
  if (month < 1 || month > 12) throw new TypeError("Invalid month");
  return year + (month >= 7 ? 1 : 0);
}
export function transactionsForYear(year, filter="") {
  const query = String(filter).trim().toLowerCase();
  return DEMO.transactions.filter(t =>
    t.taxYear === Number(year) &&
    (!query || [t.description,t.category,t.status,DEMO.accounts.find(a=>a.id===t.account)?.name || ""]
      .some(x=>x.toLowerCase().includes(query))));
}
export function summaryForYear(year) {
  const rows = transactionsForYear(year);
  const incomes = rows.filter(x=>x.direction==="in");
  const outflows = rows.filter(x=>x.direction==="out");
  return {
    incomeMinor: incomes.reduce((s,x)=>s+x.amountMinor,0),
    outflowMinor: outflows.reduce((s,x)=>s+x.amountMinor,0),
    transferCount: rows.filter(x=>x.direction==="transfer").length,
    reviewCount: rows.filter(x=>x.status==="Review required").length,
    transactionCount: rows.length,
    illustrativeLiquidMinor: DEMO.accounts.reduce((s,x)=>s+x.balanceMinor,0),
  };
}
export function coverageSummary(year) {
  const grid = DEMO.coverage[Number(year)];
  if (!grid) throw new RangeError("Unsupported demo tax year");
  const counts = {observed:0, partial:0, missing:0, conflicting:0, unsupported:0};
  for(const months of Object.values(grid)){
    if(months.length!==12) throw new RangeError("Incomplete coverage display");
    for(const status of months) {
      if(!(status in counts)) throw new RangeError("Unknown coverage status");
      counts[status]++;
    }
  }
  return {grid,counts,accountMonths:Object.values(grid).reduce((n,x)=>n+x.length,0)};
}
export function monthlyMovement(year) {
  return MONTHS.map((name,index)=>{
    const month = ((index+6)%12)+1;
    const yr = Number(year) - (month>=7?1:0);
    const key = yr+"-"+String(month).padStart(2,"0");
    const matches = transactionsForYear(year).filter(t=>t.date.startsWith(key));
    return {label:name,
      incoming:matches.filter(x=>x.direction==="in").reduce((s,x)=>s+x.amountMinor,0),
      outgoing:matches.filter(x=>x.direction==="out").reduce((s,x)=>s+x.amountMinor,0),
      monthKey:key};
  });
}
export function hypotheticalBuffer({openingMinor, monthlyEssentialMinor, months}) {
  if (openingMinor !== null && (!Number.isSafeInteger(openingMinor) || openingMinor < 0))
    throw new TypeError("Invalid fictional opening");
  if (![monthlyEssentialMinor,months].every(Number.isSafeInteger) ||
      monthlyEssentialMinor < 0 || monthlyEssentialMinor > 1e11 || months < 1 || months > 12)
    throw new RangeError("Invalid scenario");
  const target = monthlyEssentialMinor * months;
  return {targetMinor:target, shortfallMinor:openingMinor===null?null:Math.max(0,target-openingMinor),
    coverageVerified:false, scenarioOnly:true};
}

function validSampleMinor(value) {
  if (!Number.isSafeInteger(value) || value < 0) throw new TypeError("Invalid fictional minor amount");
  return value;
}
function assertISODate(value) {
  if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(value) || Number.isNaN(Date.parse(value+"T12:00:00Z")))
    throw new TypeError("Invalid fictional ISO date");
  return value;
}
export function monthPulseSummary(snapshot=DEMO.monthPulse) {
  if (snapshot.evidenceState!=="FICTIONAL_SCENARIO_NOT_VERIFIED" ||
      snapshot.actualSourceComplete!==false)
    throw new TypeError("Only an explicitly fictional unverified snapshot can be displayed");
  const asOf=assertISODate(snapshot.asOf);
  const expense=snapshot.expenses;
  const current=validSampleMinor(expense.hypotheticalCurrentMinor);
  const prior=validSampleMinor(expense.hypotheticalComparablePriorMinor);
  const catCurrent=expense.categories.reduce((n,x)=>n+validSampleMinor(x.currentMinor),0);
  const catPrior=expense.categories.reduce((n,x)=>n+validSampleMinor(x.priorMinor),0);
  if(catCurrent!==current || catPrior!==prior)
    throw new RangeError("Fictional spending categories do not reconcile");
  const sampleGrowth=prior===0?null:Math.round((current-prior)*100/prior);
  const seen=new Set();
  for(const item of [...snapshot.bills,...snapshot.investments,...snapshot.followups]){
    if(seen.has(item.id))throw new RangeError("Duplicate fictional action reference");
    seen.add(item.id);
    if(item.dueOn)assertISODate(item.dueOn);
    if(item.nextReturnOn)assertISODate(item.nextReturnOn);
  }
  const sevenDays=new Date(asOf+"T12:00:00Z");
  sevenDays.setUTCDate(sevenDays.getUTCDate()+7);
  const dueBy=sevenDays.toISOString().slice(0,10);
  const bills=[...snapshot.bills].map(x=>({
    ...x,
    displayAmountMinor:validSampleMinor(x.amountMinor),
    needsChecking:x.state!=="PAID_SAMPLE" && x.dueOn<=dueBy,
    amountVerified:false,
    paymentConfirmed:false,
  })).sort((a,b)=>a.dueOn.localeCompare(b.dueOn));
  const investments=[...snapshot.investments].map(x=>{
    validSampleMinor(x.principalMinor);
    if(x.quotedReturnMinor!==null){
      validSampleMinor(x.quotedReturnMinor);
      if(x.quoteKind!=="FICTIONAL_FIXED_CONTRACT_QUOTE" || !x.nextReturnOn)
        throw new RangeError("Quoted return requires a dated fictional fixed contract");
    }
    return {...x,principalVerified:false,actualReturnMinor:null,returnGuaranteed:false,
      withholdingTaxMinor:null};
  }).sort((a,b)=>(a.nextReturnOn??"9999").localeCompare(b.nextReturnOn??"9999"));
  const followups=[...snapshot.followups].sort((a,b)=>a.dueOn.localeCompare(b.dueOn));
  return {
    asOf, dueBy,
    monthLabel:new Intl.DateTimeFormat("en-PK",{month:"long",year:"numeric",timeZone:"UTC"})
       .format(new Date(asOf+"T12:00:00Z")),
    exampleCurrentExpenseMinor:current,
    examplePriorExpenseMinor:prior,
    exampleGrowthPct:sampleGrowth,
    verifiedCurrentExpenseMinor:null,
    verifiedExpenseGrowthPct:null,
    coverageComplete:false,
    billReviewCount:bills.filter(x=>x.needsChecking).length,
    bills,investments,followups,
    pendingFollowupCount:followups.length,
    exampleInvestedPrincipalMinor:investments.reduce((n,x)=>n+x.principalMinor,0),
    verifiedInvestedPrincipalMinor:null,
    categories:expense.categories.map(x=>({...x,verified:false})),
    sourceStatus:"DEMO_ONLY_NOT_CONNECTED_TO_OWNER",
    taxesAndActualReturnsReady:false,
  };
}
