# Personal CFO — Owner-operated private Google Drive inbox indexer

**Status: source code prepared, NOT installed or running in any Google account.** This optional Google Apps Script is a free/usage-quota-limited way to monitor ONE folder hourly without an always-on computer or new cloud server. Requires the owner's explicit Google account authorization; do not use it in an unrelated or existing personal Drive.

## One-time activation (only after using a NEW dedicated Personal CFO Google account)

1. Create one **private** folder in the fresh account: `Personal CFO — Upload Here`. Upload everything there without organizing. Do not make the folder public or share with random service accounts.
2. In that exact account open [Google Apps Script](https://script.google.com/home/projects/create) and create a new **private, standalone** script. The source in `Code.gs` is intended for that script, not for a Google password or a service key. Paste the code into the editor.
3. Copy the folder ID from the private Drive URL and replace ONLY `PASTE_PRIVATE_FOLDER_ID_HERE` in the script. Do not paste account IDs, PDF passwords, emails, bank numbers, OAuth access tokens or private file names into public GitHub.
4. In Apps Script project settings, enable viewing the manifest, then replace `appsscript.json` with the supplied manifest. It explicitly requests **Drive read-only, Sheets write, and trigger management**. The Drive read scope is **account-wide** at Google permission level, but our code calls only `DriveApp.getFolderById(FOLDER_ID).getFiles()`; that is why the account must be new and dedicated. Read the authorization permissions carefully.
5. Select and run **`setupPersonalCfoInbox`** once. Accept Google's authorization only if it is the newly created Personal CFO account and you're comfortable with these scopes. This creates a private `Personal CFO — Private Inbox Index` Google spreadsheet and installs **one hourly scheduled scan**.
6. The spreadsheet has an **Inbox** sheet (virtual category, review status, possible duplicate, change status), **Summary** (counts and last scan), and **Changes** (new/modified/no-longer-visible audit). Original files remain in the single upload folder; there is no renaming, movement, deletion, or automatic parsing.
7. To stop monitoring, run **`pausePersonalCfoInbox`** in the script editor. The source folder and index spreadsheet are preserved. Apps Script quotas and triggers may cause scans to fail; review trigger history and the Summary sheet's last successful scan.

## Safety and limitations

- The script stores original *filenames, private Drive file IDs and links* in **a private Google Sheet in the same owner account**. The sheet is **not encrypted by our own application keys**; it relies on Google's account/storage protections, and it must remain private.
- Filename categorization is **only a suggestion**; a file named `FINAL-FBR` is **not** proof of an official FBR filing. It does not read original bytes, passwords, bank balances, payroll entries or workbook formulas. It cannot calculate the owner's tax, expenses, investments or net worth.
- Suspected duplicates are based on normalized file name and size, NOT byte-level SHA256 or bank row reconciliation. They are review hints; the index never deletes an original.
- The entire folder is listed up to a maximum of 500 items per scan; nested folders deliberately cause an error because the owner requested one flat folder. The scan stops before updating if a folder is incomplete/over capacity. Any worksheet editing can also cause an error; the Sheet is a convenience index, NOT an authoritative source of financial truth.
- The script never uses external webhooks, executes a PDF, stores a PDF unlock password or uploads original bytes to GitHub, Railway or another storage vendor.
- Hourly triggers are subject to Google's Apps Script service limits, time-window jitter and account authorization. No always-on ChatGPT conversation or installed ChatGPT connector is required for the **metadata index**, but neither ChatGPT nor Personal CFO's PWA automatically sees it until an approved integration is separately built.
- For actual **continuous financial reconciliation**, future authorized processing must verify each original PDF/CSV/XLSX in a private isolated parser, certify the genuine Pakistani bank/FBR formats, reconcile account/year/economic sources, and write only to the approved encrypted canonical ledger. **G1/G2/G3 remain BLOCKED.**
- The user's installed ChatGPT Google Drive connector is **different** from this standalone Google Apps Script and different again from Personal CFO's own OAuth flow. Nothing in this repository installs or runs on the user's Drive automatically.

Official docs: [DriveApp Folder.getFiles](https://developers.google.com/apps-script/reference/drive/folder), [hourly triggers](https://developers.google.com/apps-script/reference/script/clock-trigger-builder), [Apps Script scopes](https://developers.google.com/apps-script/guides/services/authorization), and [quotas](https://developers.google.com/apps-script/guides/services/quotas).

## Source and synthetic regression

`Code.gs` is the installable owner-side script, `appsscript.json` is the permission manifest, and `test.mjs` runs against pure helpers using a Node VM with synthetic fake filenames and no Google API calls. The CI workflow `google-drive-inbox-synthetic-ci.yml` never accesses a real Drive, originals or account credentials.

**Do not install yet on an account containing unrelated personal/project documents.** Use a fresh dedicated Personal CFO Google account and a private folder, as the owner requested.
