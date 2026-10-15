"""
Monthly incremental sync:  Radiant (Frappe Cloud)  ->  local akatech.local
Goal: keep the local site a 1:1 mirror of Radiant (rows, child rows, files).

Run from the bench `sites` dir:
    ../env/bin/python -m akatech_erp.monthly_sync              # normal monthly run
    ../env/bin/python -m akatech_erp.monthly_sync --dry-run    # report only, writes nothing

Pipeline
  0. Lock (only one run at a time) + load .env credentials.
  1. Safety DB backup (no files, quick).
  2. DELETIONS  - replays Radiant's "Deleted Document" log since the last run.
  3. PRECHECK   - ONE concurrent count call per doctype ("anything modified since
                  the watermark?"). Unchanged doctypes are skipped entirely, which
                  is what makes monthly runs fast.
  4. UPSERTS    - for changed doctypes: list (name, modified, docstatus) since the
                  watermark; fetch a full document only if it is missing locally,
                  newer remotely, or its docstatus changed. workflow_state kept.
                  Original creation/modified/owner preserved (raw db_insert).
  5. FILES      - downloads every File missing on disk (public + private).
  6. VERIFY     - compares local vs Radiant row counts for every doctype.
                  local < remote  -> forced full re-sync of that doctype
                  local > remote  -> orphans pruned (guarded, see MAX_PRUNE_RATIO)
                  Any mismatch left is printed and the exit code is 2.
  7. BACKUP     - full backup with public + private files (the 3 files you upload
                  to Frappe Cloud). Paths printed at the end.

A doctype's watermark only advances if it finished with no errors, so failed
records are retried automatically next run (see monthly_sync_errors.log).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import frappe
import requests
from frappe.utils import get_datetime
from requests.adapters import HTTPAdapter

from akatech_erp.env import API_KEY, API_SECRET, BASE_URL
from akatech_erp.sync_all_parallel import DOCTYPES, alter_table_add_col

SITE = "akatech.local"
# State + error log live INSIDE the repo (apps/akatech_erp/sync_state/) so they can be committed/pushed.
STATE_DIR = os.environ.get(
    "MONTHLY_SYNC_STATE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sync_state")
)
STATE_FILE = os.path.join(STATE_DIR, "monthly_sync_state.json")
ERROR_LOG = os.path.join(STATE_DIR, "monthly_sync_errors.log")
LOCK_FILE = os.environ.get("MONTHLY_SYNC_LOCK", "/tmp/akatech_monthly_sync.lock")

PAGE = 5000
COMMIT_EVERY = 200
MAX_PRUNE_RATIO = 0.2  # refuse to prune if orphans exceed 20% of local rows (safety net)
# Noise / unsafe to replay: logs, schema docs, and Deleted Document (handled separately).
SKIP = {"Error Log", "Patch Log", "Prepared Report", "Data Import", "Deleted Document", "DocType"}
AUDIT = ["Version", "Comment"]  # optional (--with-audit): audit trail, can be large
STRIP = ("_user_tags", "_comments", "_assign", "_liked_by")


class RemoteError(Exception):
    pass


# ───────────────────────────── HTTP ─────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({"Authorization": f"token {API_KEY}:{API_SECRET}", "Accept": "application/json"})


def init_http(workers):
    ad = HTTPAdapter(pool_connections=workers, pool_maxsize=workers * 2)
    SESSION.mount("https://", ad)
    SESSION.mount("http://", ad)


def get_json(path, params=None, retries=4):
    """GET /api/<path>. Returns parsed JSON, None on 404. Raises RemoteError otherwise."""
    last = None
    for i in range(retries):
        try:
            r = SESSION.get(f"{BASE_URL}/api/{path}", params=params, timeout=90)
            if r.status_code == 404:
                return None
            if r.status_code in (429, 502, 503, 504):
                time.sleep(2 * (i + 1))
                last = f"HTTP {r.status_code}"
                continue
            if r.status_code >= 400:
                raise RemoteError(f"HTTP {r.status_code} {r.text[:120]}")
            return r.json()
        except requests.exceptions.RequestException as e:
            last = str(e)
            time.sleep(2 * (i + 1))
    raise RemoteError(last or "unknown error")


def list_remote(doctype, filters, fields):
    start = 0
    while True:
        params = {
            "fields": json.dumps(fields),
            "order_by": "modified asc",
            "limit_start": start,
            "limit_page_length": PAGE,
        }
        if filters:
            params["filters"] = json.dumps(filters)
        res = get_json(f"resource/{urllib.parse.quote(doctype)}", params)
        data = (res or {}).get("data") or []
        if not data:
            return
        yield data
        if len(data) < PAGE:
            return
        start += PAGE


def remote_count(doctype, filters=None):
    """Row count on Radiant, or None if it can't be determined."""
    params = {"doctype": doctype}
    if filters:
        params["filters"] = json.dumps(filters)
    try:
        res = get_json("method/frappe.client.get_count", params)
        return (res or {}).get("message")
    except RemoteError:
        return None


def fetch_doc(doctype, name):
    try:
        res = get_json(f"resource/{urllib.parse.quote(doctype)}/{urllib.parse.quote(str(name), safe='')}")
        return name, (res or {}).get("data"), None
    except Exception as e:  # noqa: BLE001
        return name, None, str(e)


# ───────────────────────────── State / logging ─────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"watermarks": {}, "deleted_wm": None, "runs": []}


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def log_error(msg):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(ERROR_LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def acquire_lock():
    try:
        import fcntl
    except ImportError:  # non-Linux: no locking
        return None
    fh = open(LOCK_FILE, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("Another monthly_sync run is already in progress. Exiting.")
    return fh


# ───────────────────────────── Local DB helpers ─────────────────────────────
def clean_doc(d):
    """Like sync_parties.clean_doc but KEEPS workflow_state (user_id only if User exists)."""
    for k in STRIP:
        d.pop(k, None)
    if d.get("user_id") and not frappe.db.exists("User", d["user_id"]):
        d.pop("user_id")
    return d


def local_state(doctype, names):
    """{name: (modified, docstatus)} for the given names, scoped to this doctype's table."""
    out = {}
    for i in range(0, len(names), 1000):
        chunk = names[i : i + 1000]
        rows = frappe.db.sql(
            f"select name, modified, docstatus from `tab{doctype}` where name in %s",
            (tuple(chunk),),
        )
        for n, m, ds in rows:
            out[n] = (get_datetime(m), ds)
    return out


def delete_local(doctype, name):
    meta = frappe.get_meta(doctype)
    for df in meta.get_table_fields():
        try:
            frappe.db.delete(df.options, {"parent": name, "parenttype": doctype})
        except Exception:  # noqa: BLE001
            pass
    frappe.db.delete(doctype, {"name": name})


def insert_with_heal(doc):
    for _ in range(25):
        try:
            doc.db_insert()
            return
        except Exception as e:  # noqa: BLE001
            m = re.search(r"Unknown column '(.+?)'", str(e))
            if not m:
                raise
            alter_table_add_col(doc.doctype, m.group(1))
    raise RuntimeError("too many missing columns")


def write_doc(doctype, data, existed):
    name = data["name"]
    if existed:
        delete_local(doctype, name)
    d = clean_doc(dict(data))
    d["doctype"] = doctype
    doc = frappe.get_doc(d)
    doc.flags.ignore_permissions = True
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.name = name
    insert_with_heal(doc)
    for child in doc.get_all_children():
        insert_with_heal(child)


# ───────────────────────────── Files ─────────────────────────────
def local_file_path(file_url):
    base = os.path.realpath(frappe.get_site_path())
    if file_url.startswith("/private/files/"):
        rel = os.path.join("private", "files", file_url[len("/private/files/") :])
    elif file_url.startswith("/files/"):
        rel = os.path.join("public", "files", file_url[len("/files/") :])
    else:
        return None
    path = os.path.realpath(os.path.join(base, rel))
    return path if path.startswith(base + os.sep) else None


def remove_local_file(file_url):
    p = file_url and local_file_path(file_url)
    if p and os.path.exists(p):
        os.remove(p)


def download_file(item):
    file_url, path = item
    err = ""
    for i in range(3):
        try:
            r = SESSION.get(BASE_URL + urllib.parse.quote(file_url, safe="/"), stream=True, timeout=120)
            if r.status_code == 404:
                return file_url, "missing-remote"
            r.raise_for_status()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
            os.replace(tmp, path)
            return file_url, "ok"
        except Exception as e:  # noqa: BLE001
            err = str(e)
            time.sleep(2 * (i + 1))
    return file_url, f"error: {err[:100]}"


def sync_files(workers, dry_run):
    rows = frappe.db.sql(
        "select file_url from `tabFile` where ifnull(is_folder,0)=0 "
        "and (file_url like '/files/%%' or file_url like '/private/files/%%')"
    )
    todo = []
    for (url,) in rows:
        p = local_file_path(url)
        if p and not os.path.exists(p):
            todo.append((url, p))
    print(f"\n--- Files: {len(rows)} File rows, {len(todo)} missing on disk ---", flush=True)
    stats = {"ok": 0, "missing-remote": 0, "error": 0}
    if dry_run or not todo:
        return stats
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (url, res) in enumerate(ex.map(download_file, todo), 1):
            key = res.split(":")[0]
            stats[key] = stats.get(key, 0) + 1
            if key == "error":
                log_error(f"file {url}: {res}")
            if i % 200 == 0:
                print(f"  files {i}/{len(todo)}", flush=True)
    print(f"  files done: {stats}", flush=True)
    return stats


# ───────────────────────────── Deletions ─────────────────────────────
def sync_deletions(state, args):
    wm = args.since or state.get("deleted_wm")
    filters = [["modified", ">=", wm]] if wm else None
    print(f"\n--- Deletions (since {wm or 'beginning'}) ---", flush=True)
    deleted = skipped = 0
    max_mod = wm
    try:
        for page in list_remote("Deleted Document", filters, ["deleted_doctype", "deleted_name", "modified"]):
            for r in page:
                max_mod = max(max_mod or "", r["modified"])
                dt, nm = r.get("deleted_doctype"), r.get("deleted_name")
                if not dt or not nm or dt in SKIP or not frappe.db.table_exists(dt):
                    continue
                if not frappe.db.exists(dt, nm):
                    continue
                # Safety: name may have been re-created on Radiant after deletion.
                if get_json(f"resource/{urllib.parse.quote(dt)}/{urllib.parse.quote(nm, safe='')}"):
                    skipped += 1
                    continue
                deleted += 1
                if args.dry_run:
                    continue
                if dt == "File":
                    remove_local_file(frappe.db.get_value("File", nm, "file_url"))
                delete_local(dt, nm)
        frappe.db.commit()
        if not args.dry_run and max_mod:
            state["deleted_wm"] = max_mod
            save_state(state)
    except Exception as e:  # noqa: BLE001
        print(f"  deletion sync error: {e}", flush=True)
        log_error(f"deletions: {e}")
    print(f"  deleted locally: {deleted}, kept (re-created remotely): {skipped}", flush=True)
    return deleted


# ───────────────────────────── Upserts ─────────────────────────────
def sync_doctype(dt, state, args, full=False):
    """Sync one doctype. full=True ignores the watermark (used to repair count mismatches)."""
    wm = None if full else (args.since or state["watermarks"].get(dt))
    filters = [["modified", ">=", wm]] if wm else None
    stats = {"new": 0, "updated": 0, "unchanged": 0, "errors": 0}
    max_mod = wm

    try:
        try:
            gen = list_remote(dt, filters, ["name", "modified", "docstatus"])
            first = next(gen, None)
        except RemoteError:  # doctype without a docstatus column remotely
            gen = list_remote(dt, filters, ["name", "modified"])
            first = next(gen, None)

        def all_pages():
            if first:
                yield first
            yield from gen

        for page in all_pages():
            names = [r["name"] for r in page]
            local = local_state(dt, names)
            todo = []
            for r in page:
                rm = r["modified"]
                max_mod = max(max_mod or "", rm)
                cur = local.get(r["name"])
                if cur is None:
                    todo.append((r["name"], False))
                elif get_datetime(rm) > cur[0] or ("docstatus" in r and r["docstatus"] != cur[1]):
                    todo.append((r["name"], True))
                else:
                    stats["unchanged"] += 1
            if not todo:
                continue
            if args.dry_run:
                stats["new"] += sum(1 for _, e in todo if not e)
                stats["updated"] += sum(1 for _, e in todo if e)
                continue

            existed = dict(todo)
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                fetched = list(ex.map(lambda n: fetch_doc(dt, n[0]), todo))
            done = 0
            for name, data, err in fetched:
                if err or not data:
                    stats["errors"] += 1
                    log_error(f"{dt} {name}: fetch {err or 'empty'}")
                    continue
                try:
                    write_doc(dt, data, existed[name])
                    if dt == "File" and existed[name]:
                        remove_local_file(data.get("file_url"))  # content may differ -> re-download
                    stats["updated" if existed[name] else "new"] += 1
                except Exception as e:  # noqa: BLE001
                    frappe.db.rollback()
                    stats["errors"] += 1
                    log_error(f"{dt} {name}: {str(e)[:300]}")
                done += 1
                if done % COMMIT_EVERY == 0:
                    frappe.db.commit()
            frappe.db.commit()
            # Checkpoint: pages are ordered by modified, so after a clean page everything up to
            # its last row is in sync. A killed run then resumes from here instead of from scratch.
            if stats["errors"] == 0 and max_mod:
                cur = state["watermarks"].get(dt)
                if not cur or max_mod > cur:
                    state["watermarks"][dt] = max_mod
                    save_state(state)
    except Exception as e:  # noqa: BLE001
        stats["errors"] += 1
        log_error(f"{dt}: {e}")
        print(f"  [{dt}] ERROR: {str(e)[:150]}", flush=True)

    if not args.dry_run and stats["errors"] == 0 and max_mod:
        state["watermarks"][dt] = max_mod
    if stats["new"] + stats["updated"] + stats["errors"]:
        print(f"  [{dt}] {stats}", flush=True)
    return stats


def precheck(doctypes, state, args):
    """One concurrent count call per doctype -> {doctype: rows modified since watermark (or None)}."""

    def one(dt):
        wm = args.since or state["watermarks"].get(dt)
        if not wm:
            return dt, None
        return dt, remote_count(dt, [["modified", ">", wm]])

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        return dict(ex.map(one, doctypes))


# ───────────────────────────── Verify / prune (1:1) ─────────────────────────────
def prune_extras(dt, args):
    """Delete local rows that no longer exist on Radiant. Guarded by MAX_PRUNE_RATIO."""
    remote = set()
    for page in list_remote(dt, None, ["name"]):
        remote.update(r["name"] for r in page)
    local = set(frappe.db.sql_list(f"select name from `tab{dt}`"))
    extras = local - remote
    if not extras:
        return 0
    if not getattr(args, "force_prune", False) and len(extras) > max(50, MAX_PRUNE_RATIO * len(local)):
        msg = f"{dt}: refusing to prune {len(extras)} of {len(local)} local rows (too many) - check manually"
        print("  " + msg, flush=True)
        log_error(msg)
        return 0
    if args.dry_run:
        return len(extras)
    for n in extras:
        if dt == "File":
            remove_local_file(frappe.db.get_value("File", n, "file_url"))
        delete_local(dt, n)
    frappe.db.commit()
    return len(extras)


def verify(doctypes, state, args):
    """Compare counts; repair mismatches; return the list of doctypes still mismatching."""
    print("\n--- Verify (local vs Radiant row counts) ---", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        remote = dict(zip(doctypes, ex.map(remote_count, doctypes)))
    mismatches = []
    for dt in doctypes:
        if not frappe.db.table_exists(dt) or remote[dt] is None:
            continue
        loc = frappe.db.count(dt)
        if loc == remote[dt]:
            continue
        print(f"  [{dt}] local={loc} remote={remote[dt]}", flush=True)
        if args.dry_run:
            mismatches.append((dt, loc, remote[dt]))
            continue
        if loc < remote[dt]:
            sync_doctype(dt, state, args, full=True)
        else:
            n = prune_extras(dt, args)
            print(f"  [{dt}] pruned {n} orphan rows", flush=True)
        save_state(state)
        loc2 = frappe.db.count(dt)
        if loc2 != remote[dt]:
            mismatches.append((dt, loc2, remote[dt]))
    if not mismatches:
        print("  all doctypes match 1:1", flush=True)
    return mismatches


# ───────────────────────────── Backup ─────────────────────────────
def do_backup(with_files):
    from frappe.utils.backups import new_backup

    odb = new_backup(ignore_files=not with_files, force=True)
    paths = [odb.backup_path_db]
    if with_files:
        paths += [odb.backup_path_files, odb.backup_path_private_files]
    return paths


# ───────────────────────────── Main ─────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report changes only, write nothing")
    ap.add_argument("--since", help="override watermark, e.g. 2026-09-01 (re-checks everything after it)")
    ap.add_argument("--doctypes", nargs="*", help="limit to these doctypes")
    ap.add_argument("--skip-files", action="store_true")
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--force-prune", action="store_true", help="allow pruning orphan rows even if exceeding MAX_PRUNE_RATIO")
    ap.add_argument("--with-audit", action="store_true", help="also sync Version + Comment")

    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    lock = acquire_lock()  # noqa: F841 (kept open for the process lifetime)
    init_http(args.workers)
    frappe.init(site=SITE)
    frappe.connect()
    frappe.flags.in_import = True
    started = time.time()

    seen, doctypes = set(), []
    for d in list(DOCTYPES) + ["File"] + (AUDIT if args.with_audit else []):
        if d not in seen and d not in SKIP:
            seen.add(d)
            doctypes.append(d)
    if args.doctypes:
        doctypes = [d for d in doctypes if d in set(args.doctypes)]
    doctypes = [d for d in doctypes if frappe.db.table_exists(d)]

    state = load_state()
    backups, mismatches = [], []
    total = {"new": 0, "updated": 0, "errors": 0}
    try:
        if not args.dry_run and not args.no_backup:
            print("Pre-sync safety backup...", flush=True)
            print("  ", do_backup(False)[0], flush=True)

        sync_deletions(state, args)

        print("\n--- Upserts ---", flush=True)
        changed = precheck(doctypes, state, args)
        skipped = sum(1 for dt in doctypes if changed.get(dt) == 0)
        print(f"  {skipped}/{len(doctypes)} doctypes unchanged since last run (skipped)", flush=True)
        for dt in doctypes:
            if changed.get(dt) == 0:
                continue
            s = sync_doctype(dt, state, args)
            for k in total:
                total[k] += s[k]
            if not args.dry_run:
                save_state(state)

        fstats = {} if args.skip_files else sync_files(args.workers, args.dry_run)

        if not args.skip_verify:
            mismatches = verify(doctypes, state, args)
            if not args.skip_files and not args.dry_run:
                fstats = sync_files(args.workers, args.dry_run)  # files of rows repaired by verify

        if not args.dry_run:
            state["runs"] = (state.get("runs") or [])[-11:] + [
                {"at": time.strftime("%Y-%m-%d %H:%M:%S"), **total, "files": fstats,
                 "mismatches": [m[0] for m in mismatches]}
            ]
            save_state(state)
            if not args.no_backup:
                print("\nFull backup with files...", flush=True)
                backups = do_backup(True)

        print(f"\n=== MONTHLY SYNC COMPLETE in {int(time.time() - started)}s === {total}", flush=True)
        if total["errors"]:
            print(f"  {total['errors']} errors -> see {ERROR_LOG} (they retry next run)", flush=True)
        for dt, loc, rem in mismatches:
            print(f"  NOT 1:1: {dt} local={loc} remote={rem}", flush=True)
        for p in backups:
            print("  upload:", p, flush=True)
    finally:
        frappe.destroy()
    if mismatches or total["errors"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
