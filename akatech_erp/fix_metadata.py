import os
import json
import urllib.parse
import frappe
from akatech_erp.sync_parties import api_call
from akatech_erp.sync_all_parallel import DOCTYPES

def fix_all_metadata():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    total_updated = 0
    
    for dt in DOCTYPES:
        print(f"Fetching metadata for {dt}...")
        try:
            # Fetch name, creation, modified, owner, modified_by from remote
            res = api_call(f"resource/{urllib.parse.quote(dt)}?fields=[\"name\",\"creation\",\"modified\",\"owner\",\"modified_by\"]&limit=0")
            if not res or not res.get("data"):
                continue
            
            data = res.get("data", [])
            print(f"Found {len(data)} records for {dt}. Updating local DB...")
            
            for d in data:
                frappe.db.sql("""
                    UPDATE `tab{doctype}` 
                    SET creation=%s, modified=%s, owner=%s, modified_by=%s
                    WHERE name=%s
                """.format(doctype=dt), (
                    d.get("creation"),
                    d.get("modified"),
                    d.get("owner"),
                    d.get("modified_by"),
                    d.get("name")
                ))
            total_updated += len(data)
            frappe.db.commit()
        except Exception as e:
            print(f"Error updating {dt}: {e}")

    print(f"Metadata fix complete! Updated {total_updated} documents.")

    print("Syncing Activity Logs (Versions, Comments)...")
    for log_dt in ["Version", "Comment", "Communication"]:
        print(f"Fetching {log_dt}...")
        try:
            res = api_call(f"resource/{urllib.parse.quote(log_dt)}?fields=[\"*\"]&limit=0")
            data = res.get("data", []) if res else []
            print(f"Found {len(data)} {log_dt} records.")
            inserted = 0
            for d in data:
                if not frappe.db.exists(log_dt, d.get("name")):
                    # clean doc
                    for k in ["_user_tags", "_comments", "_assign", "_liked_by"]:
                        d.pop(k, None)
                    new_doc = frappe.get_doc(d)
                    new_doc.flags.ignore_permissions = True
                    new_doc.flags.ignore_mandatory = True
                    new_doc.flags.ignore_links = True
                    # insert bypassing standard validations
                    new_doc.insert(set_name=True, set_child_names=True)
                    
                    # Fix creation/modified for the log itself
                    frappe.db.sql(f"UPDATE `tab{log_dt}` SET creation=%s, modified=%s, owner=%s, modified_by=%s WHERE name=%s",
                                  (d.get("creation"), d.get("modified"), d.get("owner"), d.get("modified_by"), d.get("name")))
                    inserted += 1
            frappe.db.commit()
            print(f"Inserted {inserted} new {log_dt} records.")
        except Exception as e:
            print(f"Error syncing {log_dt}: {e}")

if __name__ == "__main__":
    fix_all_metadata()
