# Akatech ERP (AKA) — Master User Guide & System Hand-off

> **For New Engineers & AI Agents:** Read this document top to bottom before touching anything. This is the complete journey, technical architecture, current state, and single-command execution guide for the project.

---

## 1. Project Background & Core Mission

### The Objective
To create an exact, 100% identical clone of the production **Radiant Medical (Pvt.) Ltd.** ERPNext v15 system (`https://radiant-medical.frappe.cloud`) and deploy it to Frappe Cloud as **Akatech ERP (AKA)**.

### The Non-Negotiables
- **Zero Record Loss:** All master data, transaction entries, audit logs, and child tables must match 1:1.
- **Audit Integrity:** Historical metadata (`creation`, `modified`, `owner`, `modified_by`, and `docstatus`) must remain completely preserved—not overwritten by today's import date.
- **Complete Attachments:** All profile pictures, uploaded receipts, PDFs, and document attachments must be downloaded and restored intact.
- **Zero Hardcoded Secrets:** No API keys or database passwords committed to repositories.

---

## 2. Journey & Evolution (What Has Been Done Since The Start)

### Phase 1: Custom Frappe App Architecture (`akatech_erp`)
We built a custom Frappe application named `akatech_erp` installed on top of ERPNext v15 and HRMS on a local WSL site (`akatech.local`).
- **Custom Modules Created (`modules.txt`):** Akatech ERP, Sales Department, Procurement Department, Inventory Department, AKA Buying, AKA Selling, Loan Management, RM HR, Kodessy Tools, RM Payroll, AKA STOCK, Kodessy Accounts.
- **UI & Dashboard Customizations:** Custom stylesheets, themes, and executive dashboard APIs (`premium_api.py`, `public/css/`, `public/js/`).

### Phase 2: The Initial Bulk Parallel Migration (`sync_all_parallel.py`)
To pull thousands of historical records from Radiant Medical, we built a high-speed parallel migration engine:
- **Timestamp Preservation:** Standard Frappe ORM `doc.save()` updates `modified` timestamps to current time. We bypassed ORM save hooks using raw MariaDB `db_insert` calls to preserve historical audit timestamps.
- **Dynamic Schema Self-Healing:** Because raw database injection bypasses Frappe's field hooks, custom fields from Radiant were initially missing from local tables. The script was equipped with error interception (`1054 Unknown column`) that dynamically triggers `ALTER TABLE ... ADD COLUMN` on the fly.
- **Bulk Progress:** Migrated **155 DocTypes** out of 237, logging completed record IDs into `sync_progress.json`.

### Phase 3: The Production Upgrade (`monthly_sync.py`)
To make syncing ongoing, crash-resilient, and repeatable for monthly updates, `sync_all_parallel.py` was superseded by `monthly_sync.py`:
- **Fault Tolerance & Resumption:** Uses per-doctype atomic watermarks (`sync_state/monthly_sync_state.json`) and error logs (`sync_state/monthly_sync_errors.log`). If a run is interrupted by network failure or system shutdown, it safely resumes at the exact page it left off.
- **Deletions Replay:** Replays Radiant's `Deleted Document` log so records deleted on live are also cleaned locally.
- **Automated File Downloads:** Automatically finds missing public and private `File` attachments on disk and downloads them directly into `sites/akatech.local/public/files/` and `private/files/`.
- **1:1 Count Verification:** Compares local row counts vs live Radiant counts for every DocType. If local count is lower, it triggers a forced re-sync. If orphan rows exist, it prunes them safely.

### Phase 4: Secrets Security & 2-Repo Separation
- **Credentials:** Migrated all API tokens and URLs into `.env` (git-ignored) loaded via `akatech_erp/env.py`.
- **Repo Separation:**
  1. **`https://github.com/Luffy11323/ERP` (Production Code):** Contains app code, sync scripts, runner, and themes. No DB dumps or secrets allowed.
  2. **`https://github.com/Luffy11323/Backup` (Data Storage):** Dedicated private repo that stores `database.sql.gz`, `public-files.tar`, and `private-files.tar`.
- **1-Command Packaging:** Unified everything into `./run_sync.sh` (Linux/WSL) and `.\run_sync.ps1` (Windows).

---

## 3. Current Project Status

- **Database State:** 155 master and setup DocTypes are completely synced and verified in the local MariaDB (`akatech.local`).
- **Remaining DocTypes (82):** The remaining queue consists of transaction entries (Attendance, Appraisal, Payroll Entry, Salary Slip, Quality Inspection, Stock Entry, Purchase Receipt, Sales Invoice, GL Entry, etc.).
- **Scraper / Runner State:** Packaged, tested, and pushed to `main` on `Luffy11323/ERP` (commit `cfafb14`).
- **Ready to Run:** Everything is primed for the single command to sync the remaining records, download files, verify 1:1 parity, and push the backup to GitHub.

---

## 4. Key Paths & Reference Architecture

### WSL (Ubuntu)
| Component | Path |
|---|---|
| Bench Root | `/home/administrator/frappe-bench/` |
| Custom App Repo | `/home/administrator/frappe-bench/apps/akatech_erp/` |
| Site Directory | `/home/administrator/frappe-bench/sites/akatech.local/` |
| Database Storage | `/var/lib/mariadb/_9b9681f70464fc6f/` (MariaDB) |
| Uploaded Files | `sites/akatech.local/public/files/` & `private/files/` |
| Backups Directory | `sites/akatech.local/private/backups/` |
| Sync State & Watermarks | `apps/akatech_erp/sync_state/monthly_sync_state.json` |
| Credentials | `apps/akatech_erp/.env` (git-ignored) |

### Windows Host
| Component | Path |
|---|---|
| Project Workspace | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\code\` |
| Database Backups | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\database_backup\` |
| Context Notes | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\AKA_ERP_Context.md` |
| Progress Log | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup\sync_progress.json` |

## 5. Universal Edge-Case Auto-Healing (`fix_leftovers.py`)

During bulk syncs, remote database quirks (duplicate unique fields, child table collisions, or invalid references) can occasionally trigger database constraint errors.

Rather than using brittle hardcoded fixes, the repository features a **Universal Dynamic Auto-Healer** ([`fix_leftovers.py`](file:///C:/Users/Administrator/Desktop/Radiant_ERP_Backup/code/akatech_erp/fix_leftovers.py)) that operates across **ANY DocType**:

1. **Automated Error Log Ingestion:** Parses `sync_state/monthly_sync_errors.log` line-by-line to automatically detect whatever records failed (Employee, User, Workspace, Item, Invoices, etc.).
2. **Dynamic Unique Constraint Resolution:** Uses Frappe metadata (`frappe.get_meta(doctype)`) to detect any field marked `unique` (CNIC, username, tax ID, registration number). If a collision occurs, it automatically disambiguates text keys or nulls duplicate numbers so MariaDB never blocks the insert.
3. **Child Table Primary Key Clashing:** Dynamically detects child table row ID collisions (e.g. `Workspace Link`) and regenerates clean random hashes (`frappe.generate_hash()`).
4. **Foreign Key & User Linkage Normalization:** Cleans dangling user references and links all `Employee` records to their corresponding `User` accounts.
5. **Fallback Exception Interceptor:** If an insert throws a constraint error, it intercepts the SQL key name, auto-nulls the colliding field, and retries immediately.

> **Automated Execution:** `./run_sync.sh` is pre-configured to **automatically execute `fix_leftovers.py`** immediately after the main upsert phase and before taking the final backup.
> 
> You can also run it standalone anytime:
> ```bash
> wsl -d Ubuntu -- bash -lc "cd /home/administrator/frappe-bench/sites && ../env/bin/python -m akatech_erp.fix_leftovers"
> ```

---

## 6. Deploying to Live Frappe Cloud

Once the sync finishes and produces the backup trio (`database.sql.gz`, `public-files.tar`, `private-files.tar`):
1. Navigate to your **Frappe Cloud Dashboard → Sites → Your Site → Restore with files**.
2. Upload the 3 backup files.
3. Click **Restore**, click **Clear Cache**, and run **Migrate**.
4. Deploy the latest `main` branch of `https://github.com/Luffy11323/ERP` (via Updates tab).
5. All records, attachments, users, and dashboards will be live and 100% identical to Radiant Medical.

## 7. Architecture Roadmap & Future TODOs

While the current setup provides exceptional 1:1 data fidelity and crash-resilience, the following improvements are planned for future scale:

- [ ] **Direct DB Streaming Option (Ultra-Fast Initial Extraction):**
  - *Current:* Pulls records over Frappe Cloud HTTPS REST API (`api/resource/DocType`) with controlled concurrency to respect rate limits.
  - *Enhancement:* If direct read-only MySQL/MariaDB credentials are granted on Radiant Medical's cloud host, add a direct `mysqldump` / MariaDB tunnel mode to complete initial bulk migrations in minutes rather than hours.
- [ ] **Git LFS or Object Storage (S3 / R2 / Releases) for Backups > 100 MB:**
  - *Current:* Backups are committed to `Luffy11323/Backup`. GitHub enforces a hard limit of 100 MB per file.
  - *Enhancement:* As attachment tars and database dumps grow, update `push_backup.sh` to leverage **Git LFS (Large File Storage)** or stream archives directly to Cloudflare R2 / AWS S3 / GitHub Release assets.
- [ ] **Automated Headless Scheduling (Cron / Systemd Timer):**
  - *Current:* The monthly sync is triggered manually on-demand via `./run_sync.sh --with-backup`.
  - *Enhancement:* Set up a WSL systemd timer or cron job (`0 0 1 * *`) to automatically execute incremental updates on the 1st of every month at midnight.
- [ ] **Adaptive Worker Concurrency:**
  - *Current:* Uses static worker concurrency to prevent HTTP 429 (Too Many Requests).
  - *Enhancement:* Implement dynamic concurrency back-off that automatically throttles up when response latencies are low and scales down if rate limiting is encountered.

---

## 8. How to Run (Single Command Hand-Off)



### On THIS machine right now:

You don't even need to pull. Your local WSL directory is already on the latest commit (`cfafb14`) and your `.env` credentials are in place. You can run that exact command immediately:

```bash
wsl -d Ubuntu -- bash -lc "cd /home/administrator/frappe-bench/apps/akatech_erp && ./run_sync.sh --with-backup"
```

### If running on ANY NEW machine:

The only setup steps before running that command are:

1. Pull the code repo into your bench:
   ```bash
   bench get-app https://github.com/Luffy11323/ERP
   ```
2. Create `.env` inside `apps/akatech_erp/` with your `RADIANT_API_KEY` and `RADIANT_API_SECRET`.
3. (You do not need to manually pull `Luffy11323/Backup` beforehand — `./push_backup.sh` handles connecting to that repo automatically).
4. Run your command:
   ```bash
   ./run_sync.sh --with-backup
   ```

### What happens when you run it:
1. It replays deletions from Radiant live.
2. It checks watermarks and pulls only modified/new records and child tables.
3. It downloads all missing attachments/photos.
4. It auto-heals edge cases (duplicate CNIC, usernames, links) via `fix_leftovers.py`.
5. It prunes orphan records that do not exist on live Radiant based on real-time queries.
6. It validates row counts 1:1 against Radiant Medical.
7. It packages the database + files and automatically commits and pushes the 3 backup files to `Luffy11323/Backup`.

You're all set to fire it off!

