/*
 * Source-bound recurring BANK MOVEMENT candidates, not debts, bills or income.
 * Input must be transactionSources already validated against the source SHA,
 * printed closing balance and every running balance by the owner frontend.
 * No persistence, duplicate-account merge, payment prediction or due date.
 */
import {periodContainsDate} from "./finance-period.mjs";

export function repeatingBankCandidates(sources,period,{minimumMonths=3}={}){
  if(!Array.isArray(sources) || sources.length>10 ||
     !Number.isInteger(minimumMonths) || minimumMonths<2 || minimumMonths>12)
    return [];
  const found=new Map();
  for(const source of sources){
    if(!source || typeof source.source_hmac!=="string" ||
       typeof source.source_name!=="string" ||
       !Array.isArray(source.transactions?.rows) ||
       source.transactions.rows.length>600)continue;
    for(const event of source.transactions.rows){
      if(!event || typeof event.description!=="string" ||
         event.description.length>180 ||
         !/^[0-9a-f]{64}$/.test(event.source_hmac) ||
         event.source_hmac!==source.source_hmac ||
         !/^\d{4}-\d{2}-\d{2}$/.test(event.date) ||
         !["INBOUND","OUTBOUND"].includes(event.direction) ||
         !Number.isSafeInteger(event.amount_minor) || event.amount_minor<=0)
        continue;
      const desc=event.description.trim().toLowerCase().replace(/\s+/g," ");
      if(desc.length<5)continue;
      // Group only events from the SAME original source and direction.
      // A separate bank account or mirrored transfer never becomes another
      // monthly payment in the same group.
      const key=source.source_hmac+"|"+event.direction+"|"+
        event.amount_minor+"|"+desc;
      let group=found.get(key);
      if(!group){
        group={
          source_name:source.source_name,source_hmac:source.source_hmac,
          direction:event.direction,amount_minor:event.amount_minor,
          description:event.description,events:[],observedMonths:new Set(),
        };
        found.set(key,group);
      }
      group.events.push(event);
      group.observedMonths.add(event.date.slice(0,7));
    }
  }
  return [...found.values()].filter(g=>
    g.observedMonths.size>=minimumMonths &&
    g.events.some(row=>periodContainsDate(row.date,period)))
    .map(g=>{
      const dated=[...g.events].sort((a,b)=>a.date.localeCompare(b.date) ||
        a.ordinal-b.ordinal);
      return {
        source_name:g.source_name,description:g.description,
        direction:g.direction,amount_minor:g.amount_minor,
        observed_month_count:g.observedMonths.size,
        first_observed:dated[0].date,last_observed:dated.at(-1).date,
        observed_in_selected_period:dated.some(row=>periodContainsDate(row.date,period)),
        // These are *candidates*. No inference to settled bill, recurring
        // charge, salary, contract, next date, debt, or household expense.
        purpose_verified:false,upcoming_due_date:null,
      };
    }).sort((a,b)=>b.last_observed.localeCompare(a.last_observed) ||
      b.observed_month_count-a.observed_month_count)
    .slice(0,50);
}
