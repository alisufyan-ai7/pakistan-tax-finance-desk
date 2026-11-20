import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const read=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");
function element(){return {children:[],hidden:true,textContent:"",
 append(...xs){this.children.push(...xs);},
 appendChild(x){this.children.push(x);},
 replaceChildren(...xs){this.children=xs;}};}
function harness(){
  const js=read("app.mjs");
  const a=js.indexOf("function validPrivatePropertyOverview(data) {");
  const b=js.indexOf("// Private, no-cache source-backed CSV bank observations",a);
  assert.ok(a>0 && b>a,"separate in-memory property evidence contract");
  const ids=new Map(["home-property-investment-list","property-investment-detail-list",
  "home-property-investments","property-investment-detail",
  "property-cost-chart","investment-partner-list","investment-partner-groups",
  "property-investment-detail-heading"].map(n=>[n,element()]));
  const ctx={HMAC_SHA:/^[a-f0-9]{64}$/,byId:id=>{assert.ok(ids.has(id));return ids.get(id);},
   document:{createElement:()=>element()},historicalMoney:{format:v=>"PKR "+v.toFixed(2)},
   propertyRefreshEpoch:0,safeToken:()=>true,csrfToken:"x".repeat(45),get:async()=>{}};
  vm.runInNewContext(js.slice(a,b),ctx);
  return {ctx,ids};
}
function evidence(){
  const assets=Array.from({length:12},(_,n)=>{
    const sold=n<6;
    return {ordinal:n+1,property_label:"Synthetic property "+(n+1),
      purchase_date:"2026-01-01",sale_date:sold?"2026-07-01":null,
      source_status:sold?"SOLD_IN_SOURCE_REGISTER":"HELD_COST_NOT_MARKET_VALUE",
      recorded_purchase_cost_minor:10000,
      net_sale_proceeds_minor:sold?11000:null,
      recorded_profit_minor:sold?1000:null,
      recorded_owner_profit_share_minor:sold?600:null};
  });
  return {contract:"personal_cfo_p6_property_inventory_v1",
    source_type:"PROPERTY_COST_AND_SALES_REGISTER",
    property_count:12,sold_property_count:6,held_property_count:6,
    held_recorded_investment_cost_minor:60000,
    all_recorded_sale_profit_minor:6000,owner_recorded_sale_profit_share_minor:3600,
    other_party_recorded_share_minor:2400,latest_sale_date:"2026-07-01",
    source_hmac:"a".repeat(64),source_content_hmac:"b".repeat(64),
    source_sha256_verified:true,content_retained_on_server:false,
    original_source_modified:false,owner_review_required:true,
    cash_proceeds_verified:false,market_value_minor:null,
    owner_total_net_worth_minor:null,properties:assets};
}
test("property register source-backed costs, gains and owner share rendered only after strict evidence",()=>{
  const {ctx,ids}=harness(),source=evidence(),data={
    contract:"personal_cfo_owner_property_inventory_overview_v1",
    reports:[source],property_register_sources_verified:1,xlsx_sources_examined:2,
    approved_source_folder:true,inventory_complete:true,originals_modified:false,
    content_retained_on_server:false,current_market_values_verified:false,owner_review_required:true};
  assert.equal(ctx.validPrivatePropertyOverview(data),true);
  ctx.renderPropertyInvestments(source);
  assert.equal(ids.get("home-property-investments").hidden,false);
  assert.equal(ids.get("property-investment-detail-list").children.length,12);
  assert.match(ids.get("home-property-investment-list").children[0].children[0].textContent,/PKR 600.00/);
  assert.match(ids.get("home-property-investment-list").children[0].children[1].textContent,/PKR 36.00/);
  assert.equal(ctx.validPrivatePropertyOverview({...data,reports:[{...source,market_value_minor:9999}]}),false);
  assert.equal(ctx.validPrivatePropertyOverview({...data,reports:[{...source,owner_recorded_sale_profit_share_minor:100}]}),false);
  ctx.clearPropertyInvestmentEvidence();
  assert.equal(ids.get("home-property-investments").hidden,true);
});
test("source private names cannot inject HTML, browser storage or public route",()=>{
  const js=read("app.mjs"),html=read("app.html"),ng=read("nginx.railway.conf"),dock=read("Dockerfile");
  assert.match(js,/name.textContent=p.property_label/);
  assert.match(js,/get\("\/api\/finance\/investments\/overview"\)/);
  assert.match(js,/clearPropertyInvestmentEvidence\(\)/);
  assert.doesNotMatch(js,/localStorage|sessionStorage|innerHTML|console\.log|document\.cookie/);
  assert.match(html,/id="home-property-investments"/);
  assert.match(html,/id="property-investment-detail"/);
  assert.match(ng,/location = \/api\/finance\/investments\/overview \{/);
  assert.match(ng,/if \(\$p6b_property_ingress != "1"\) \{ return 404; \}/);
  assert.match(ng,/proxy_pass http:\/\/\$private_google_upstream\/internal\/finance\/investments\/overview/);
  assert.match(dock,/P6B_INVESTMENTS_PUBLIC_INGRESS_ENABLED=0/);
});

test("partner names are owner-private and ventures stay distinct, no fabricated values",()=>{
  const {ctx,ids}=harness();
  const e=evidence();
  const reg={contract:"personal_cfo_p6_owner_investment_registry_v1",
    source:"PRIVATE_OWNER_DECLARATION",
    property_register_group_id:"property_group",
    current_market_values_verified:false,
    all_investment_contributions_reconciled:false,
    groups:[
      {id:"property_group",title:"Synthetic Partner One",owner_declared:true,ventures:[
        {id:"property_venture",title:"Synthetic property venture",category:"property",
          evidence_status:"PROPERTY_REGISTER_RECONCILED_HISTORICAL_COSTS_ONLY",
          property_register_linked:true,confirmed_invested_principal_minor:null,
          current_market_value_minor:null,realized_cash_return_minor:null,
          expected_return_minor:null}]},
      {id:"dual_venture",title:"Synthetic Partner Two",owner_declared:true,ventures:[
        {id:"first_venture",title:"Synthetic school",category:"education",
          evidence_status:"OWNER_DECLARED_AWAITING_TRANSACTION_ALLOCATION",
          property_register_linked:false,confirmed_invested_principal_minor:null,
          current_market_value_minor:null,realized_cash_return_minor:null,
          expected_return_minor:null},
        {id:"second_venture",title:"Synthetic publishing business",category:"business",
          evidence_status:"OWNER_DECLARED_AWAITING_TRANSACTION_ALLOCATION",
          property_register_linked:false,confirmed_invested_principal_minor:null,
          current_market_value_minor:null,realized_cash_return_minor:null,
          expected_return_minor:null}]}]};
  assert.equal(ctx.validInvestmentRelationshipRegistry(reg,true),true);
  ctx.renderPropertyInvestments(e);
  ctx.renderInvestmentRelationshipRegistry(reg);
  assert.equal(ids.get("investment-partner-list").children.length,2);
  assert.equal(ids.get("investment-partner-list").children[1].children[1].children.length,2);
  assert.equal(ids.get("investment-partner-groups").hidden,false);
  assert.match(ids.get("property-investment-detail-heading").textContent,/Synthetic Partner One/);
  assert.equal(ids.get("property-cost-chart").children.length,6);
  assert.equal(ids.get("property-cost-chart").children[0].children[1].max,10000);
  assert.equal(ctx.validInvestmentRelationshipRegistry({...reg,groups:[
    {...reg.groups[0],ventures:[{...reg.groups[0].ventures[0],
      confirmed_invested_principal_minor:123}]}]},true),false);
  assert.equal(ctx.validInvestmentRelationshipRegistry({...reg,groups:[
    {...reg.groups[0],ventures:[{...reg.groups[0].ventures[0],
      evidence_status:"OWNER_DECLARED_AWAITING_TRANSACTION_ALLOCATION"}]},
      reg.groups[1]]},true),false);
  assert.equal(ctx.validInvestmentRelationshipRegistry({...reg,groups:[
    reg.groups[0],{...reg.groups[1],id:"property_group"}]},true),false);
  ctx.clearPropertyInvestmentEvidence();
  assert.equal(ids.get("investment-partner-groups").hidden,true);
  assert.equal(ids.get("investment-partner-list").children.length,0);
});
