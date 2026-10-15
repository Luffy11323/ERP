# Akatech ERP (AKA) — Radiant Medical clone

Custom Frappe app (`akatech_erp`) + migration tooling for **AKA**, a 1:1 clone of the
**Radiant Medical (Pvt.) Ltd.** ERPNext v15 system. Goal: move every user to the new ERP
without losing any record, audit trace, attachment or profile picture.

> **New chat / new engineer? Read this file top to bottom — it is the full hand-off.**

---

## 1. Stack, repos & environments

| Item | Value |
|---|---|
| Framework | Frappe / ERPNext **v15** (frappe 15.122), apps: `frappe`, `erpnext`, `hrms`, `akatech_erp` |
| **Production repo (source of truth)** | **`https://github.com/Luffy11323/ERP`** (branch `main`) — this repo; deployed to Frappe Cloud |
| Other repo (NOT production) | `https://github.com/Luffy11323/Radiant` — old/backup mirror, do not push production work there |
| Source system (read-only) | `https://radiant-medical.frappe.cloud` (Radiant ERP, read via REST API token) |
| Local mirror | WSL Ubuntu, bench `/home/administrator/frappe-bench`, site **`akatech.local`**, MariaDB |
| Target (live) | Frappe Cloud site for AKA (erpnext + hrms + akatech_erp) |

Data flow: **Radiant (cloud) → local `akatech.local` (monthly script) → backup files → restore into AKA on Frappe Cloud.**

## 2. Paths (where everything lives)

**WSL (Ubuntu) — runs everything**

| What | Path |
|---|---|
| Bench root | `/home/administrator/frappe-bench/` |
| This app (git repo → `Luffy11323/ERP`) | `/home/administrator/frappe-bench/apps/akatech_erp/` |
| Site folder | `/home/administrator/frappe-bench/sites/akatech.local/` |
| Public / private uploaded files | `sites/akatech.local/public/files/` and `sites/akatech.local/private/files/` |
| **Database backups (+ files tars)** | `/home/administrator/frappe-bench/sites/akatech.local/private/backups/` (`*-database.sql.gz`, `*-files.tar`, `*-private-files.tar`, `*-site_config_backup.json`). The server also auto-backs-up every ~6 h here. |
| **MariaDB data dir** | `/var/lib/mariadb/` — database for `akatech.local` is `/var/lib/mariadb/_9b9681f70464fc6f/` (InnoDB `.ibd`). Never read these files directly; use Frappe/`bench mariadb`. |
| DB credentials | `sites/akatech.local/site_config.json` (`db_name`, `db_password`) |
| Monthly sync state | `/home/administrator/monthly_sync_state.json` |
| Monthly sync error log | `/home/administrator/monthly_sync_errors.log` |
| Old one-time migration progress | `/home/administrator/sync_progress.json` |
| `.env` (credentials, git-ignored) | `/home/administrator/frappe-bench/apps/akatech_erp/.env` |
| Whole WSL disk | `E:\WSL\Ubuntu\ext4.vhdx` (Windows side) |

**Windows**

| What | Path |
|---|---|
| Backup folder | `C:\Users\Administrator\Desktop\Radiant_ERP_Backup` (`code/`, `database_backup/`, `sync_progress.json`, `AKA_ERP_Context.md`) |
| Packaged copy | `C:\Users\Administrator\Desktop\Akatech_ERP_Package` |
| Extraction/audit tools | `C:\Users\Administrator\Desktop\ERP_Extractor` |
| Reach WSL files from Windows | `\\wsl$\Ubuntu\home\administrator\frappe-bench\...` |

## 3. Repo layout (`akatech_erp/`)

Modules (`modules.txt`): Akatech ERP, Sales Department, Procurement Department, Inventory Department,
AKA Buying, AKA Selling, Loan Management, RM HR, Kodessy Tools, RM Payroll, AKA STOCK, Kodessy Accounts.

| File | Purpose |
|---|---|
| `monthly_sync.py` | **The monthly sync** (see §5). |
| `env.py` | Tiny `.env` loader; exposes `API_KEY`, `API_SECRET`, `BASE_URL`. |
| `sync_all_parallel.py` | Original one-time bulk migration. Its ordered `DOCTYPES` list and `alter_table_add_col` are reused by the monthly sync. |
| `sync_parties.py` | Helper `api_call` / `clean_doc` for the original migration. |
| `premium_api.py`, `public/css`, `public/js` | Premium dashboard/theme. |
| `fix_*.py`, `check_*.py`, `test_*.py`, … | One-off repair / diagnostic scripts used during migration. |

## 4. Credentials (.env)

Secrets are **never committed**. Copy `.env.example` to `.env` (git-ignored) in `apps/akatech_erp/`:

```
RADIANT_BASE_URL=https://radiant-medical.frappe.cloud
RADIANT_API_KEY=...
RADIANT_API_SECRET=...
```

Search order: real env vars → `$AKATECH_ENV_FILE` → `apps/akatech_erp/.env` → bench root `.env` → `~/.akatech.env`.

> ⚠️ The old API key/secret and past Frappe Cloud DB passwords are in git history and old chats. **Rotate them**
> (Radiant: User → API Access → Regenerate; Frappe Cloud: recreate the DB user), then update `.env`.

## 5. Monthly sync (run manually, from Windows PowerShell)

```powershell
# preview only (writes nothing)
wsl -d Ubuntu -- bash -lc "cd /home/administrator/frappe-bench/sites && ../env/bin/python -m akatech_erp.monthly_sync --dry-run"

# real run
wsl -d Ubuntu -- bash -lc "cd /home/administrator/frappe-bench/sites && ../env/bin/python -m akatech_erp.monthly_sync"
```

Pipeline (what makes it fast **and** exact):

1. **Lock** – only one run at a time. **Safety DB backup** first.
2. **Deletions** – replays Radiant's `Deleted Document` log since the last run (re-created names are kept).
3. **Precheck** – one concurrent count call per doctype ("modified since watermark?"); unchanged doctypes are skipped → fast monthly runs.
4. **Upserts** – changed doctypes only: list `(name, modified, docstatus)` since the watermark; fetch a full doc only if it's missing locally, newer remotely, or its `docstatus` changed. Child tables included, `workflow_state` kept, original `creation/modified/owner` preserved (raw `db_insert`, no hooks). Missing columns are added automatically.
5. **Files** – every `File` row's public/private file missing on disk is downloaded to `sites/akatech.local/public/files` / `private/files`.
6. **Verify (1:1)** – local vs Radiant row counts for every doctype. Fewer locally → forced full re-sync of that doctype. More locally → orphans pruned (refuses if >20% of rows). Leftover mismatches are printed and exit code is `2`.
7. **Full backup with files** – prints the 3 files to upload (`.sql.gz`, public `.tar`, private `.tar`), saved in `sites/akatech.local/private/backups/`.

State: `monthly_sync_state.json` holds per-doctype watermarks (a doctype only advances if it finished with zero errors); failed records are listed in `monthly_sync_errors.log` and retried next run.

Options: `--dry-run`, `--since YYYY-MM-DD`, `--doctypes A B`, `--skip-files`, `--skip-verify`, `--no-backup`, `--with-audit` (also `Version` + `Comment`), `--workers N`.

The **first** run has no watermarks, so it compares every record once (slow, one-time) — this also fixes anything that changed on Radiant since the original migration.

Known limits: deletions are only caught if Radiant logged them in `Deleted Document` (or via the count/prune check); `DocType`, `Error Log`, `Patch Log`, `Prepared Report`, `Data Import` are intentionally not synced; unique-key clashes (e.g. duplicate Employee CNIC) are logged and retried, not skipped.

## 6. Loading the result into the AKA site on Frappe Cloud

Site must have `erpnext`, `hrms`, `akatech_erp` installed **at creation** (installing erpnext onto a populated DB fails: "can only be installed on a fresh site").

1. Frappe Cloud → site → **Restore with files**: upload the `.sql.gz`, public `.tar`, private `.tar` from the backups folder (§2).
2. **Clear cache**, then **Migrate**.
3. Deploy the latest `main` of this repo (Updates tab) — the `rm_hr` report modules etc. live in this app.

Lessons learned:
- Browser upload of the big DB timed out and left the site *Failed* (migrations blocked → drop and recreate the site). Fallback used: create a Frappe Cloud DB user and stream the SQL with the `mysql` client (throttled, ~1 h).
- Restoring only DB tables loses attachments / logos / profile pictures → always restore the files tars too.
- Raw-injected DBs give `Module HR not found` / `ModuleNotFoundError: akatech_erp.rm_hr.report` unless the apps are registered on the site and this repo is deployed.
- A restore replaces everything on the live site — stop data entry in AKA before restoring.

## 7. Tips for continuing work

- From Windows: `wsl -d Ubuntu -- bash -lc "..."`; Python: `frappe-bench/env/bin/python`; SQL: `bench --site akatech.local mariadb -e "..."`.
- Do not alter schema locally except to fix a specific validation bug during cutover.
- Commit only this app to **`Luffy11323/ERP`** (never the bench, DB dumps or `.env`; `*.sql.gz`, `*.tar`, `.env` are git-ignored). Don't force-push; this repo is production.
- Original context notes: `AKA_ERP_Context.md` in the Windows backup folder.

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/Luffy11323/ERP --branch main
bench install-app akatech_erp
```

## Contributing

Uses `pre-commit` (ruff, eslint, prettier, pyupgrade): `cd apps/akatech_erp && pre-commit install`.

## License

MIT
