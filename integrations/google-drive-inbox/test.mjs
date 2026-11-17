import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { test } from 'node:test';

const source = fs.readFileSync(new URL('./Code.gs', import.meta.url), 'utf8');
const sandbox = vm.createContext({ Date, console });
vm.runInContext(source, sandbox, { timeout: 1000 });
const helper = (name) => vm.runInContext(name, sandbox);

const label = helper('cfoCollectionHint_');
const safe = helper('cfoSheetSafeText_');
const review = helper('cfoReviewStatus_');
const snapshot = helper('cfoPrepareSnapshot_');
const version = helper('cfoVersion_');

const f = (id, name, overrides={}) => ({
  id, name, mime: 'application/pdf', bytes: 1024,
  modifiedAt: '2026-11-17T07:00:00.000Z', ...overrides
});

test('uncategorized originals remain pending, never financial truth', () => {
  assert.equal(label('2025 IRIS wealth statement.pdf'), 'FBR wealth candidates');
  assert.equal(label('Bank_statement.pdf'), 'Bank statement candidates');
  assert.equal(label('Accountant draft calculation.xlsx'), 'Accountant working papers');
  assert.equal(label('loan and cash receipt.pdf'), 'Loan and cash candidates');
  assert.equal(label('mystery.pdf'), 'Unclassified — review');
  assert.equal(review('2025 FBR FINAL FILED.pdf', 'application/pdf', 1000),
               'AWAITING PRIVATE SOURCE VERIFICATION');
});

test('unsafe extensions, mismatched content types, oversize are quarantined', () => {
  for (const [name, mime] of [
    ['real-bank-statement.xlsm','application/vnd.ms-excel.sheet.macroEnabled.12'],
    ['password-source.zip','application/zip'],
    ['reconcile.exe','application/octet-stream'],
    ['report.pdf','text/html']
  ]) assert.match(review(name, mime, 2000), /^QUARANTINED/);
  assert.match(review('legit.pdf','application/pdf',0),/^QUARANTINED/);
  assert.match(review('legit.pdf','application/pdf',70*1024*1024),/^QUARANTINED/);
});

test('untrusted spreadsheet formula filenames are literal not executable', () => {
  for (const raw of [
    '=IMPORTXML("https://bad.invalid", "/")',
    '+SUM(A1:A3)', '-cmd()', '@HYPERLINK("https://bad.invalid")',
    '\t=HYPERLINK("https://bad.invalid")'
  ]) assert.equal(safe(raw), "'" + raw);
  assert.equal(safe('bank_statement.pdf'), 'bank_statement.pdf');
});

test('full one-folder synthetic snapshot yields safe virtual rows only', () => {
  const files = [
    f('SIMULATEDFILEBANK0001','statement.pdf'),
    f('SIMULATEDFILEBANK0002','statement.pdf'),
    f('SIMULATEDFILETAX00003','IRIS tax return.pdf')
  ];
  const report = snapshot(files, {});
  assert.equal(report.rows.length, 3);
  assert.equal(report.events.length, 3);
  assert.equal(report.duplicateCount, 1);
  assert.equal(report.counts['Bank statement candidates'], 2);
  assert.equal(report.counts['Tax return candidates'], 1);
  assert.ok(report.rows.every(row =>
    row[11] === 'NO — pending private G1/G2/G3 certification'));
  assert.equal(report.rows[1][9], 'MAYBE — review originals');
  assert.equal(report.events[0][1], 'NEW');
  assert.ok(source.includes('source.getFiles()'));
  assert.ok(!source.includes('.getBlob('));
  assert.ok(!source.includes('.setTrashed('));
  assert.ok(!source.includes('.moveTo('));
});

test('changed and disappeared records are review events, not automatic deletion', () => {
  const file = f('SIMULATEDFILEBANK0001','my bank statement.pdf');
  const known = { [file.id]: version(file), 'SIMULATEDFILEPREVIOUS999':'older' };
  const same = snapshot([file], known);
  assert.equal(same.events.length, 1); // previous file not visible
  assert.match(same.events[0][1], /NOT VISIBLE/);
  const changed = snapshot([f(file.id,file.name,{ bytes:2048 })], known);
  assert.equal(changed.rows[0][8], 'CHANGED — reverify');
  assert.equal(changed.events.length, 2);
  assert.ok(changed.events.some(ev => ev[1] === 'CHANGED — reverify'));
});

test('hard fail on malformed ids, duplicated ids or unbounded snapshot', () => {
  assert.throws(() => snapshot([f('bad','statement.pdf')],{}), /Invalid\/duplicate/);
  const one=f('SIMULATEDFILEBANK0001','statement.pdf');
  assert.throws(() => snapshot([one, one], {}), /Invalid\/duplicate/);
  const lots=Array.from({length: 501},(_,i)=>
    f('SIMULATEDFILEBANK'+String(i).padStart(5,'0'),'statement.pdf'));
  assert.throws(() => snapshot(lots, {}), /Too many/);
});

test('owner setup requires explicit private inbox id, no default inherited folder', () => {
  const validate=helper('cfoValidateFolderId_');
  assert.throws(() => validate('PASTE_PRIVATE_FOLDER_ID_HERE'), /Configure/);
  assert.throws(() => validate(''), /Configure/);
  assert.equal(validate('OWNER_SPECIFIC_FOLDER_2026'), 'OWNER_SPECIFIC_FOLDER_2026');
});
