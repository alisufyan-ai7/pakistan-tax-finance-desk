/**
 * Personal CFO — SINGLE private Google Drive Inbox, metadata-only indexer.
 *
 * Owner changes ONE value below to their dedicated private folder ID, then
 * runs setupPersonalCfoInbox ONCE in their own Google account. Never publish
 * as web app. Do not insert a Google password, banking details or tax IDs.
 *
 * No files downloaded, OCR'd, renamed, moved, deleted, shared or exported.
 * Sheet is created in the SAME owner's Google Drive. Hourly trigger runs
 * as the owner under the scopes in appsscript.json.
 *
 * NOTE: This is metadata triage, NOT certified financial reconciliation.
 * Original bank/FBR content requires private G1/G2/G3 security acceptance.
 */
const PERSONAL_CFO_INBOX_FOLDER_ID = "PASTE_PRIVATE_FOLDER_ID_HERE";
const PERSONAL_CFO_MAX_FILES = 500;
const PERSONAL_CFO_PROPERTY = "PERSONAL_CFO_INDEX_SHEET_ID";
const PERSONAL_CFO_HEADERS = [
  "Drive file ID", "Version", "Original filename", "Virtual collection",
  "MIME type", "Bytes", "Last modified (UTC)", "Review status",
  "Since last scan", "Possible duplicate?", "Private Drive link",
  "Financial facts verified?"
];

function cfoValidateFolderId_(value) {
  if (typeof value !== "string" ||
      !/^[A-Za-z0-9_-]{10,200}$/.test(value) ||
      value === "PASTE_PRIVATE_FOLDER_ID_HERE") {
    throw new Error("Configure the private upload folder ID first.");
  }
  return value;
}

function cfoSheetSafeText_(value) {
  // A file name is attacker-controlled: never allow spreadsheet formulas.
  const text = String(value == null ? "" : value);
  return /^[=+@\-\t\r\n]/.test(text) ? "'" + text : text;
}

function cfoCollectionHint_(filename) {
  const name = String(filename || "").toLowerCase().replace(/[-_]/g, " ");
  if (/accountant|working paper|draft calculation/.test(name))
    return "Accountant working papers";
  if (/wealth/.test(name) && /fbr|iris|tax/.test(name))
    return "FBR wealth candidates";
  if (/fbr|iris|tax return/.test(name))
    return "Tax return candidates";
  if (/statement|bank|account activity/.test(name))
    return "Bank statement candidates";
  if (/investment|broker|portfolio|mutual fund|dividend/.test(name))
    return "Investment candidates";
  if (/loan|cash receipt|advance/.test(name))
    return "Loan and cash candidates";
  if (/bill|invoice|rent|receipt|utility/.test(name))
    return "Bills and receipts";
  if (/whatsapp|chat|screenshot|image/.test(name))
    return "Correspondence and screenshots";
  return "Unclassified — review";
}

function cfoReviewStatus_(filename, mime, bytes) {
  const name = String(filename || "").toLowerCase();
  const ending = name.includes(".") ? "." + name.split(".").pop() : "";
  const allowed = {
    ".pdf": ["application/pdf"],
    ".csv": ["text/csv", "application/csv", "application/vnd.ms-excel"],
    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    ".jpg": ["image/jpeg"], ".jpeg": ["image/jpeg"], ".png": ["image/png"]
  };
  if (!allowed[ending] || allowed[ending].indexOf(mime) === -1)
    return "QUARANTINED — unsupported or mismatched format";
  if (!Number.isFinite(bytes) || bytes <= 0 || bytes > 60 * 1024 * 1024)
    return "QUARANTINED — empty/oversized/unknown size";
  return "AWAITING PRIVATE SOURCE VERIFICATION";
}

function cfoVersion_(file) {
  // Drive revision hint, NOT SHA256 of original contents.
  return String(file.modifiedAt) + ":" + String(file.bytes) + ":" + String(file.mime);
}

function cfoPreviousRows_(sheet) {
  const known = Object.create(null);
  const rowCount = sheet.getLastRow();
  if (rowCount <= 1) return known;
  const rows = sheet.getRange(2, 1, rowCount - 1, 12).getValues();
  rows.forEach(row => {
    const id = String(row[0] || "");
    if (id && Object.prototype.hasOwnProperty.call(known, id))
      throw new Error("Duplicate original file identity in private index.");
    if (id) known[id] = String(row[1] || "");
  });
  return known;
}

function cfoPrepareSnapshot_(files, old) {
  if (!Array.isArray(files) || files.length > PERSONAL_CFO_MAX_FILES)
    throw new Error("Too many files to index safely; previous index unchanged.");
  const ordered = files.slice().sort((a, b) => a.id.localeCompare(b.id));
  const seen = Object.create(null);
  const possibleDuplicates = Object.create(null);
  const rows = [];
  const events = [];
  const counts = Object.create(null);
  let duplicateCount = 0;
  ordered.forEach(f => {
    if (!/^[A-Za-z0-9_-]{10,200}$/.test(f.id) || seen[f.id])
      throw new Error("Invalid/duplicate Drive source ID.");
    seen[f.id] = true;
    const collection = cfoCollectionHint_(f.name);
    const status = cfoReviewStatus_(f.name, f.mime, f.bytes);
    const revision = cfoVersion_(f);
    const stage = !Object.prototype.hasOwnProperty.call(old, f.id) ? "NEW" :
      old[f.id] === revision ? "UNCHANGED" : "CHANGED — reverify";
    // Only a weak name+size hint. Never declare byte-level duplication.
    const weak = f.name.toLowerCase().trim().replace(/\s+/g, " ") + "|" + f.bytes;
    const duplicate = Object.prototype.hasOwnProperty.call(possibleDuplicates, weak);
    possibleDuplicates[weak] = true;
    if (duplicate) duplicateCount++;
    counts[collection] = (counts[collection] || 0) + 1;
    rows.push([
      f.id, revision, cfoSheetSafeText_(f.name), collection, f.mime,
      f.bytes, f.modifiedAt, status, stage,
      duplicate ? "MAYBE — review originals" : "Unknown — unverified",
      "https://drive.google.com/file/d/" + encodeURIComponent(f.id) + "/view",
      "NO — pending private G1/G2/G3 certification"
    ]);
    if (stage !== "UNCHANGED")
      events.push([new Date().toISOString(), stage, f.id, cfoSheetSafeText_(f.name),
                   "Original untouched; no financial import"]);
  });
  Object.keys(old).forEach(id => {
    if (!seen[id]) events.push([new Date().toISOString(),
      "NOT VISIBLE — access/move review", id, "", "Do not infer source was deleted"]);
  });
  return { rows, events, counts, duplicateCount };
}

function setupPersonalCfoInbox() {
  const folderId = cfoValidateFolderId_(PERSONAL_CFO_INBOX_FOLDER_ID);
  // Access only the ONE configured folder, never search the whole account.
  DriveApp.getFolderById(folderId).getName();
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty(PERSONAL_CFO_PROPERTY)) {
    const book = SpreadsheetApp.create("Personal CFO — Private Inbox Index");
    book.getActiveSheet().setName("Inbox");
    book.insertSheet("Summary");
    book.insertSheet("Changes");
    const changes = book.getSheetByName("Changes");
    changes.getRange(1, 1, 1, 5).setValues([[
      "Detected UTC", "Event", "Drive file ID", "Original filename", "Safety note"
    ]]);
    props.setProperty(PERSONAL_CFO_PROPERTY, book.getId());
  }
  if (!ScriptApp.getProjectTriggers().some(trigger =>
      trigger.getHandlerFunction() === "scanPersonalCfoInbox")) {
    ScriptApp.newTrigger("scanPersonalCfoInbox").timeBased().everyHours(1).create();
  }
  return scanPersonalCfoInbox();
}

function scanPersonalCfoInbox() {
  const folderId = cfoValidateFolderId_(PERSONAL_CFO_INBOX_FOLDER_ID);
  const props = PropertiesService.getScriptProperties();
  const sheetId = props.getProperty(PERSONAL_CFO_PROPERTY);
  if (!sheetId) throw new Error("Run setupPersonalCfoInbox first.");
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) throw new Error("Previous scan still running.");
  try {
    const source = DriveApp.getFolderById(folderId);
    if (source.getFolders().hasNext())
      throw new Error("Nested folders detected; move files into the one private upload folder.");
    const iterator = source.getFiles();
    const files = [];
    while (iterator.hasNext()) {
      if (files.length >= PERSONAL_CFO_MAX_FILES)
        throw new Error("Inbox capacity exceeded; previous index remains unchanged.");
      const f = iterator.next();
      files.push({
        id: f.getId(), name: f.getName(), mime: f.getMimeType(),
        bytes: f.getSize(), modifiedAt: f.getLastUpdated().toISOString()
      });
    }
    const workbook = SpreadsheetApp.openById(sheetId);
    const inbox = workbook.getSheetByName("Inbox");
    const summary = workbook.getSheetByName("Summary");
    const changes = workbook.getSheetByName("Changes");
    if (!inbox || !summary || !changes)
      throw new Error("Private index tabs were altered; refusing import.");
    const old = cfoPreviousRows_(inbox);
    const planned = cfoPrepareSnapshot_(files, old);
    // Only after the ENTIRE folder has been inventoried successfully:
    inbox.clearContents();
    inbox.getRange(1, 1, 1, PERSONAL_CFO_HEADERS.length)
      .setValues([PERSONAL_CFO_HEADERS]);
    if (planned.rows.length)
      inbox.getRange(2, 1, planned.rows.length, PERSONAL_CFO_HEADERS.length)
        .setValues(planned.rows);
    if (planned.events.length)
      changes.getRange(changes.getLastRow() + 1, 1, planned.events.length, 5)
        .setValues(planned.events);
    const summaryRows = [
      ["Last successful scan UTC", new Date().toISOString()],
      ["Files in one folder", files.length],
      ["Possible duplicates (unverified)", planned.duplicateCount],
      ["Financial items fully reconciled", "NONE — no private parser activated"],
      ["Original files renamed/moved/deleted", "NONE"],
      ["Google Drive folder monitored", "ONE approved folder ONLY"]
    ];
    Object.keys(planned.counts).sort().forEach(k =>
      summaryRows.push([k, planned.counts[k]]));
    summary.clearContents();
    summary.getRange(1, 1, summaryRows.length, 2).setValues(summaryRows);
    SpreadsheetApp.flush();
    props.setProperty("PERSONAL_CFO_LAST_COMPLETE_SCAN", new Date().toISOString());
    return { fileCount: files.length, duplicateCandidates: planned.duplicateCount,
      originalFilesTouched: 0, realFinancialFactsVerified: 0 };
  } finally {
    lock.releaseLock();
  }
}

function pausePersonalCfoInbox() {
  // Does not delete spreadsheet, source files, or unrelated account triggers.
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === "scanPersonalCfoInbox")
      ScriptApp.deleteTrigger(trigger);
  });
  return "Hourly private inbox indexing paused; originals and index retained.";
}
