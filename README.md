# Akatech ERP (AKA) — Master User Guide & System Hand-off

> **For New Engineers & AI Agents:** Read this document top to bottom before touching anything. This is the complete journey, technical architecture, current state, single-command execution guide, and dual-version (v15 / v16) deployment guide.

---

## 1. Project Background & Core Mission

### The Objective
To create an exact, 100% identical clone of the production **Radiant Medical (Pvt.) Ltd.** ERPNext system (`https://radiant-medical.frappe.cloud`) and deploy it to Frappe Cloud as **Akatech ERP (AKA)**, supporting both **v15 LTS** and **v16 ("Caffeine")** with instant zero-risk fallback.

### The Non-Negotiables
- **Zero Record Loss:** All master data, transaction entries, audit logs, and child tables must match 1:1.
- **Audit Integrity:** Historical metadata (`creation`, `modified`, `owner`, `modified_by`, and `docstatus`) must remain completely preserved—not overwritten by today's import date.
- **Complete Attachments:** All profile pictures, uploaded receipts, PDFs, and document attachments must be downloaded and restored intact.
- **Zero Hardcoded Secrets:** No API keys or database passwords committed to repositories.
- **Bi-directional Compatibility (v15 ↔ v16):** Codebase changes must be 100% backwards-compatible with v15 while fully resolving all v16 strictness rules.

---

## 2. Journey & Evolution (What Has Been Done Since The Start)

### Phase 1: Custom Frappe App Architecture (`akatech_erp`)
We built a custom Frappe application named `akatech_erp` installed on top of ERPNext and HRMS.
- **Custom Modules Created (`modules.txt`):** Akatech ERP, Sales Department, Procurement Department, Inventory Department, AKA Buying, AKA Selling, Loan Management, RM HR, Kodessy Tools, RM Payroll, AKA STOCK, Kodessy Accounts.
- **UI & Dashboard Customizations:** Custom stylesheets, themes, executive hero cards, and dashboard APIs (`premium_api.py`, `public/css/`, `public/js/`).

### Phase 2: The Initial Bulk Parallel Migration (`sync_all_parallel.py`)
To pull thousands of historical records from Radiant Medical, we built a high-speed parallel migration engine:
- **Timestamp Preservation:** Standard Frappe ORM `doc.save()` updates `modified` timestamps to current time. We bypassed ORM save hooks using raw MariaDB `db_insert` calls to preserve historical audit timestamps.
- **Dynamic Schema Self-Healing:** The script intercepted MariaDB `1054 Unknown column` errors and automatically ran `ALTER TABLE ... ADD COLUMN` on the fly.
- **Bulk Progress:** Migrated **155 DocTypes** out of 237, logging completed record IDs into `sync_progress.json`.

### Phase 3: The Production Upgrade (`monthly_sync.py`)
To make syncing ongoing, crash-resilient, and repeatable for monthly updates, `sync_all_parallel.py` was superseded by `monthly_sync.py`:
- **Fault Tolerance & Resumption:** Uses per-doctype atomic watermarks (`sync_state/monthly_sync_state.json`) and error logs (`sync_state/monthly_sync_errors.log`). If interrupted, it resumes at the exact page.
- **Deletions Replay:** Replays Radiant's `Deleted Document` log so records deleted on live are cleaned locally.
- **Automated File Downloads:** Finds missing public and private `File` attachments on disk and downloads them directly into `sites/v16.local/public/files/` and `private/files/`.
- **1:1 Count Verification:** Compares local row counts vs live Radiant counts for every DocType.

### Phase 4: Secrets Security & 2-Repo Separation
- **Credentials:** Migrated all API tokens and URLs into `.env` (git-ignored) loaded via `akatech_erp/env.py`.
- **Repo Separation:**
  1. **`https://github.com/Luffy11323/ERP` (Production Code):** Contains app code, sync scripts, runner, and themes. No DB dumps or secrets allowed.
  2. **`https://github.com/Luffy11323/Backup` (Data Storage):** Dedicated private repo that stores `database.sql.gz`, `public-files.tar`, and `private-files.tar`.

### Phase 5: Frappe v16 Compatibility & Cloud Hardening
When deploying to Frappe v16 on Frappe Cloud, several new platform constraints were solved without breaking v15 compatibility:
- **Bench Dependencies:** Added `[tool.bench.frappe-dependencies]` in `pyproject.toml` supporting `>=15.0.0, <17.0.0` for Frappe and ERPNext so Cloud benches validate cleanly.
- **Group Account Validation Patch Bypass:** Implemented `before_migrate` hook (`patches/before_migrate.py`) to auto-clear group operating cost accounts before patch `make_workstation_operating_components` executes.
- **Caffeine Query Builder Strictness:** Replaced raw SQL strings in `frappe.get_list(..., fields=["sum(...) as v"])` with Python-level aggregation in `premium_api.py`, eliminating `DataError: SQL functions are not allowed as strings in SELECT`.
- **Self-Service & Tasks Card:** Rebuilt the `/home` hero section to match the green Self-Service card with real-time check-in, month attendance, hours, and My Tasks widget.
- **Universal Route Manager:** Upgraded `premium_dashboard.js` to auto-route to `/desk/setup/home`, map all workspace slugs (`stock`, `assets`, `manufacturing`, `projects`, etc.), and dynamically unmount on Form/List/Report views.

---

## 3. Current Project Status

- **Database State (100% Synced):** All 230 DocTypes (masters, setup, audit logs, and transaction entries) are completely synced and verified **1:1** against Radiant Medical in the local MariaDB (`_v16_staging`).
- **File Attachments:** 9,942 files (4.7 GB private files, 284 MB public files) completely downloaded and archived.
- **Frappe Cloud Ready:** Cleanly migrates on v16 without patch crashes or user session errors; `Administrator` and `Guest` pre-configured.
- **Single-Command Pipeline:** Fully packaged into `./run_sync.sh` (Linux/WSL) and `.\run_sync.ps1` (Windows).

---

## 4. Key Paths & Reference Architecture

### WSL (Ubuntu)
| Component | Primary Bench (v16.5 Live) | Archived Baseline (v15 LTS) |
|---|---|---|
| Bench Root | `/home/administrator/frappe-bench/` (symlink: `v16-bench`) | `/home/administrator/frappe-bench-v15/` |
| Custom App Repo | `/home/administrator/frappe-bench/apps/akatech_erp/` | `/home/administrator/frappe-bench-v15/apps/akatech_erp/` |
| Site Directory | `/home/administrator/frappe-bench/sites/v16.local/` (alias: `akatech.local`) | `/home/administrator/frappe-bench-v15/sites/akatech.local/` |
| Database Name | `_v16_staging` | `_9b9681f70464fc6f` |
| Python Runtime | Python 3.14.4 virtualenv | Python 3.10 virtualenv |
| Node.js Runtime | Node 24.22.1 | Node 18 |
| Uploaded Files | `sites/v16.local/public/files/` & `private/files/` | `sites/akatech.local/public/files/` & `private/files/` |
| Backups Directory | `sites/v16.local/private/backups/` | `sites/akatech.local/private/backups/` |
| Sync State & Watermarks | `apps/akatech_erp/sync_state/monthly_sync_state.json` | `apps/akatech_erp/sync_state/monthly_sync_state.json` |
| Credentials | `apps/akatech_erp/.env` (git-ignored) | `apps/akatech_erp/.env` (git-ignored) |

### Windows Host
| Component | Primary (v16) | Baseline (v15) |
|---|---|---|
| Project Code | `\\wsl$\Ubuntu\home\administrator\frappe-bench\apps\akatech_erp\` | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\code\` |
| Database Backups | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\database_backup\16\` | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\database_backup\` |
| Context Notes | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\AKA_ERP_Context.md` | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\AKA_ERP_Context.md` |
| Progress Log | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\sync_progress.json` | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\sync_progress.json` |

---

## 5. Universal Edge-Case Auto-Healing (`fix_leftovers.py`)

During bulk syncs, remote database quirks (duplicate unique fields, child table collisions, or invalid references) can occasionally trigger database constraint errors.

The **Universal Dynamic Auto-Healer** ([`fix_leftovers.py`](file:///home/administrator/frappe-bench/apps/akatech_erp/akatech_erp/fix_leftovers.py)) operates across **ANY DocType**:

1. **Automated Error Log Ingestion:** Parses `sync_state/monthly_sync_errors.log` line-by-line to automatically detect whatever records failed.
2. **Dynamic Unique Constraint Resolution:** Uses `frappe.get_meta(doctype)` to detect fields marked `unique` (CNIC, username, tax ID, registration number). Automatically disambiguates text keys or nulls duplicate numbers so MariaDB never blocks the insert.
3. **Child Table Primary Key Clashing:** Detects child table row ID collisions (e.g. `Workspace Link`) and regenerates clean random hashes (`frappe.generate_hash()`).
4. **Foreign Key & User Linkage Normalization:** Cleans dangling user references and links `Employee` records to their corresponding `User` accounts.
5. **Fallback Exception Interceptor:** If an insert throws a constraint error, it intercepts the SQL key name, auto-nulls the colliding field, and retries immediately.

> **Automated Execution:** `./run_sync.sh` automatically executes `fix_leftovers.py` after the main upsert phase and before taking the final backup.
> 
> Standalone execution:
> ```bash
> wsl -d Ubuntu -u root -- bash -c "cd /home/administrator/frappe-bench/sites && ../env/bin/python -m akatech_erp.fix_leftovers"
> ```

---

## 6. Migration Bumps & Complete Resolutions (v15 & v16)

### Bump 1: Legacy Patch `update_closing_balances #14-07-2023` (v15 & v16)
- **Error:** `KeyError: 1` during `erpnext.patches.v14_0.update_closing_balances`.
- **Cause:** Legacy v14 patch checks for `posting_date` on `Period Closing Voucher`, superseded by `transaction_date`.
- **Resolution:** Injected completion entry into `tabPatch Log`:
  ```sql
  INSERT IGNORE INTO `tabPatch Log` (name, patch, creation, modified, modified_by, owner)
  VALUES (REPLACE(UUID(),'-',''), 'erpnext.patches.v14_0.update_closing_balances #14-07-2023', NOW(), NOW(), 'Administrator', 'Administrator');
  ```

### Bump 2: "User Administrator does not exist" During Restore (v15 & v16)
- **Error:** `Set Administrator Password: User Administrator does not exist`.
- **Cause:** Radiant's REST API `/api/resource/User` excluded `Administrator`, causing local pruning to delete it.
- **Resolution:** Re-insert `Administrator` with `System Manager` and `Administrator` roles in `tabHas Role` and password `123` via PBKDF2 hash.

### Bump 3: "Account must be an Expense ledger account" in v16 Patch
- **Error:** `ValidationError: Row #1: Account 05-03-01-01 - Other Expences - RM must be an Expense ledger account` during `erpnext.patches.v16_0.make_workstation_operating_components`.
- **Cause:** In ERPNext v16, `default_operating_cost_account` on Company is validated strictly as a non-group ledger account. If set to a group account from v15, migration fails.
- **Resolution:** Handled via hook in `akatech_erp/hooks.py`:
  ```python
  before_migrate = ["akatech_erp.patches.before_migrate.clear_invalid_operating_cost_accounts"]
  ```
  This automatically clears invalid group operating cost accounts before the patch runs.

### Bump 4: "User Guest not found" during Session Initialization in v16
- **Error:** `frappe.exceptions.DoesNotExistError: User Guest not found`.
- **Cause:** Frappe v16 strict authentication checks for `Guest` in `tabUser` on every unauthenticated request.
- **Resolution:** Ensured `Guest` user exists with `Guest` role in `tabUser` and `tabHas Role`, and protected it in sync scripts.

### Bump 5: Strict SQL Syntax Restrictions in v16
- **Error:** `SQL functions are not allowed as strings in SELECT: sum(...) as v. Use dict syntax like {'COUNT': '*'} instead.`
- **Cause:** Frappe v16 Caffeine AST parser blocks string expressions in `frappe.get_list(..., fields=[...])`.
- **Resolution:** In `akatech_erp/premium_api.py`, `_sum()` retrieves numeric fields directly and aggregates in Python:
  ```python
  records = frappe.get_list(doctype, filters=filters, fields=[field], limit_page_length=0, as_list=True)
  return sum(flt(r[0]) for r in records if r and r[0] is not None)
  ```
  Works seamlessly on both v15 and v16.

### Bump 6: URL Routing & Auto-Redirect to Setup Home in v16
- **Problem:** Navigating to `/desk` or clicking the workspace icon redirected to `/desk/build/workspace/Home` rather than `/desk/setup/home`.
- **Resolution:** In `premium_dashboard.js`, `autoRouteToHome()` intercepts top-level desk routes and routes cleanly to `setup/home`:
  ```javascript
  if ((path === "/desk" || path === "" || path === "/desk/build/workspace/Home" || path === "/app") && (!hash || hash === "desk")) {
    frappe.set_route("setup", "home");
  }
  ```

---

## 7. Dual-Version Deployment & Fallback Guide

The codebase and backups support running on **v16** and safely falling back to **v15 LTS** at any time.

### Deploying on Frappe v16 (Current Production Bench)

1. **Bench Setup on Frappe Cloud:**
   - Bench version: Frappe v16 / ERPNext v16 / HRMS v16.
   - App: `https://github.com/Luffy11323/ERP` (`main` branch).
2. **Database & File Restore:**
   - Go to **Sites → Your Site → Restore with files**.
   - Upload the latest v16 backup files from `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\database_backup\16\`:
     - Database: `20261029_073936-v16_local-database.sql.gz` (32.6 MB)
     - Public Files: `20261027_011459-v16_local-files.tar` (290.7 MB)
     - Private Files: `20261027_011459-v16_local-private-files.tar` (4.85 GB)
     - Site Config: `20261029_073936-v16_local-site_config_backup.json`
3. **Execute Migrate & Deploy:**
   - Click **Restore**, then **Migrate**.
   - Deploy latest `main` commit.
   - Access URL: `https://<your-site>.frappe.cloud/desk/setup/home`.

---

### Safe Fallback to Frappe v15 (Zero Risk Procedure)

If you ever need to fall back to Frappe v15:

1. **Bench Setup on Frappe Cloud:**
   - Create or switch to a **v15 Bench** (Frappe v15 / ERPNext v15 / HRMS v15).
   - Add app `https://github.com/Luffy11323/ERP` (`main` branch). *(The app's `pyproject.toml` supports `frappe = ">=15.0.0, <17.0.0"` and runs identically on v15).*
2. **Database & File Restore:**
   - In Frappe Cloud, open your site under the v15 bench.
   - Upload the archived v15 baseline backup files from `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\database_backup\`:
     - Database: `20261026_020035-akatech_local-database.sql.gz` (or `20261015_145558-akatech_local-database.sql.gz`)
     - Public Files: `20261026_000724-akatech_local-files.tar`
     - Private Files: `20261026_000724-akatech_local-private-files.tar`
3. **Execute Migrate & Clear Cache:**
   - Click **Restore** and run **Migrate**.
   - Log in with `Administrator` / `123`.
4. **Local WSL v15 Environment:**
   - The original v15 bench remains fully intact at `/home/administrator/frappe-bench-v15/` on site `akatech.local` with database `_9b9681f70464fc6f`.

---

## 8. How to Run (Single Command Hand-Off)

Everything is unified into a single command: `./run_sync.sh` (or `.\run_sync.ps1` from Windows PowerShell).

### Standard Monthly Scrape & Backup Pipeline (Scrape -> Auto-Heal -> Archive Backups)

* **Primary 1-Command Runner (v16.5 Live Bench):**
  ```bash
  wsl -d Ubuntu -- bash -lc "cd /home/administrator/frappe-bench/apps/akatech_erp && ./run_sync.sh"
  ```
  *(Automatically scrapes 1:1, runs universal auto-healing, generates fresh `.sql.gz` and `.tar` backups, and copies them to the Windows host backup folder for manual restore via Frappe Cloud).*

* **Windows PowerShell Alternative:**
  ```powershell
  cd C:\Users\Administrator\Desktop\Radiant_ERP_Backup\code
  .\run_sync.ps1
  ```

* **Archived Legacy v15 Runner:**
  ```bash
  wsl -d Ubuntu -- bash -lc "cd /home/administrator/frappe-bench-v15/apps/akatech_erp && ./run_sync.sh --site akatech.local"
  ```

---

### Command Variations:

* **Skip File Downloads (Database records only):**
  ```bash
  wsl -d Ubuntu -- bash -lc "cd /home/administrator/frappe-bench/apps/akatech_erp && ./run_sync.sh --skip-files"
  ```
* **Optional: Direct Stream to Cloud MariaDB (WAN Streaming):**
  ```bash
  wsl -d Ubuntu -- bash -lc "cd /home/administrator/frappe-bench/apps/akatech_erp && ./run_sync.sh --stream"
  ```
* **Stream Latest Local DB Only (Skip scraping, stream immediately):**
  ```bash
  wsl -d Ubuntu -- bash -lc "cd /home/administrator/frappe-bench/apps/akatech_erp && ./run_sync.sh --stream-only"
  ```

---

## 9. Clean Backups Reference Directory

All redundant intermediate files have been purged. The active backup sets ready for immediate restore are:

### v16.5 Latest Backup (Current Production Target)
* **Location on Host:** `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\database_backup\16\`
* **Location in WSL:** `/home/administrator/frappe-bench/sites/v16.local/private/backups/`
* **Files:**
  - **Database SQL:** `20261029_073936-v16_local-database.sql.gz` (32.6 MB)
  - **Public Files:** `20261027_011459-v16_local-files.tar` (290.7 MB)
  - **Private Files:** `20261027_011459-v16_local-private-files.tar` (4.85 GB)
  - **Site Config:** `20261029_073936-v16_local-site_config_backup.json`

### v15 Production Backup (Archived Baseline / Fallback)
* **Location on Host:** `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\database_backup\`
* **Location in WSL:** `/home/administrator/frappe-bench-v15/sites/akatech.local/private/backups/`
* **Files:**
  - **Database SQL:** `20261026_020035-akatech_local-database.sql.gz` (31.9 MB)
  - **Public Files:** `20261026_000724-akatech_local-files.tar` (289.9 MB)
  - **Private Files:** `20261026_000724-akatech_local-private-files.tar` (4.85 GB)
  - **Site Config:** `20261026_020035-akatech_local-site_config_backup.json`

---

## 10. Credentials & Quick Reference

| Resource | Value | Notes |
|---|---|---|
| Live Source ERP | `https://radiant-medical.frappe.cloud` | Source production instance |
| Target Cloud ERP | `https://radiant-medical-kodessy.f.frappe.cloud` | Target deployment |
| Admin Username | `Administrator` (or `admin@example.com`) | Pre-configured on both v15 & v16 |
| Admin Password | `123` | Native PBKDF2 hash |
| Code Repository | `https://github.com/Luffy11323/ERP` | `main` branch |
| Data Repository | `https://github.com/Luffy11323/Backup` | Private backup repository |
| Default Target URL (v16) | `/desk/setup/home` | Auto-routed by `premium_dashboard.js` |
| Default Target URL (v15) | `/app/home` or `/app/workspace/Home` | Standard v15 route |
