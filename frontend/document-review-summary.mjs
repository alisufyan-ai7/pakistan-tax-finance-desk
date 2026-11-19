/* P3C: metadata-only source REVIEW status, not finance facts.
 * No provider network, browser storage, financial figures or trusted filename
 * classifications. Pure functions for owner-private dashboard rendering.
 */
const CATEGORIES = Object.freeze([
  "bank_statements","tax_returns","wealth_statements","accountant_working",
  "investments","loans_and_cash","bills_and_receipts",
  "screenshots_and_correspondence","unclassified",
]);
const REVIEW_STATUSES = Object.freeze([
  "awaiting_private_document_verification","needs_type_review",
  "needs_size_or_content_review","quarantined_unsupported_format",
  "quarantined_oversized","source_trashed_review","skip_folder",
]);
function categoryLabel(value) {
  return String(value).replaceAll("_"," ").replace(/\b\w/g, ch=>ch.toUpperCase());
}
function priority(status) {
  if (status.startsWith("quarantined")) return 0;
  if (status==="needs_size_or_content_review"||status==="needs_type_review") return 1;
  return 2;
}
export function summarizeSourceReview(items) {
  if (!Array.isArray(items)||items.length>1000) throw Error("Invalid source inventory");
  const byCategory=new Map(CATEGORIES.map(name=>[name,0]));
  const byStatus=new Map(REVIEW_STATUSES.map(name=>[name,0]));
  const flagged=[];
  for (const item of items) {
    if (!item||typeof item!=="object"
        || typeof item.display_name!=="string" || item.display_name.length>512
        || !CATEGORIES.includes(item.virtual_collection)
        || !REVIEW_STATUSES.includes(item.review_status)
        || item.financial_claims_verified!==false
        || item.original_content_imported!==false) {
      throw Error("Untrusted or unsupported source metadata");
    }
    byCategory.set(item.virtual_collection,byCategory.get(item.virtual_collection)+1);
    byStatus.set(item.review_status,byStatus.get(item.review_status)+1);
    if (item.review_status!=="awaiting_private_document_verification" ||
        item.virtual_collection==="unclassified") flagged.push(item);
  }
  const suggestedBank=byCategory.get("bank_statements");
  const suggestedTax=byCategory.get("tax_returns")+byCategory.get("wealth_statements");
  const suggestedInvestment=byCategory.get("investments");
  const suggestedBills=byCategory.get("bills_and_receipts");
  const quarantined=REVIEW_STATUSES.filter(s=>s.startsWith("quarantined"))
    .reduce((sum,s)=>sum+byStatus.get(s),0);
  const priorityItems=[...flagged].sort((a,b)=>priority(a.review_status)-priority(b.review_status) ||
    a.display_name.localeCompare(b.display_name)).slice(0,15).map(x=>({
    name:x.display_name,
    status:x.review_status,
    suggestedCategory:x.virtual_collection,
    reason:x.review_status.startsWith("quarantined")
      ?"Unsupported format or size; needs isolated review"
      :x.review_status==="needs_size_or_content_review"
      ?"File size or content cannot yet be verified"
      :x.virtual_collection==="unclassified"
      ?"Category is unknown; review source purpose"
      :"Format requires review",
  }));
  return {
    total:items.length,
    suggestions:{
      bank:suggestedBank,tax:suggestedTax,investments:suggestedInvestment,
      bills:suggestedBills,
    },
    quarantineCount:quarantined,
    reviewCount:flagged.length,
    priorityItems,
    categories:CATEGORIES.map(name=>({
      key:name,label:categoryLabel(name),count:byCategory.get(name),
    })).filter(x=>x.count),
    contentProcessedCount:0,
    financialFiguresVerified:false,
    allReportsComplete:false,
    backgroundSyncActive:false,
  };
}
