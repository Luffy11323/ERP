"""READ-ONLY discovery of Radiant doctypes and record counts. Only HTTP GET is used."""
import json
import urllib.parse

import frappe
import requests

from akatech_erp.sync_parties import HEADERS, BASE_URL


def get(path, params=None):
    r = requests.get(f"{BASE_URL}/api/{path}", headers=HEADERS, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    dts = get("resource/DocType", {
        "fields": json.dumps(["name", "module", "custom", "istable", "issingle", "is_virtual"]),
        "limit_page_length": 5000,
    })["data"]
    print(f"Radiant DocTypes: {len(dts)}", flush=True)
    out = []
    for d in dts:
        if d["istable"] or d["issingle"] or d.get("is_virtual"):
            continue
        try:
            c = get("method/frappe.client.get_count", {"doctype": d["name"]})["message"]
        except Exception as e:
            out.append({**d, "count": None, "err": str(e)[:80]})
            continue
        if c:
            local_exists = bool(frappe.db.exists("DocType", d["name"]))
            local_c = frappe.db.count(d["name"]) if local_exists and not frappe.get_meta(d["name"]).issingle else None
            out.append({**d, "count": c, "local_exists": local_exists, "local_count": local_c})
    with open("/home/administrator/radiant_counts.json", "w") as f:
        json.dump(out, f, indent=1)
    for o in sorted(out, key=lambda x: -(x.get("count") or 0)):
        print(f"{o['name']}|{o['module']}|{o.get('count')}|local:{o.get('local_exists')}/{o.get('local_count')}|{o.get('err','')}", flush=True)


if __name__ == "__main__":
    main()
