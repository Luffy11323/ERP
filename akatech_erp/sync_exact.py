import frappe
from akatech_erp.sync_parties import api_call
import urllib.parse
from akatech_erp.sync_all_parallel import DOCTYPES

def sync_exact_all_fields():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    for dt in DOCTYPES:
        print(f"Fetching all fields for {dt}...")
        
        # Get valid columns for this doctype in the local DB
        try:
            valid_cols = set(frappe.db.get_table_columns(dt))
        except Exception:
            continue
            
        try:
            res = api_call(f"resource/{urllib.parse.quote(dt)}?fields=[\"*\"]&limit=0")
            if not res or not res.get("data"):
                continue
            
            data = res.get("data", [])
            print(f"Found {len(data)} records for {dt}. Syncing exact fields...")
            
            total_updated = 0
            for d in data:
                # Update Parent
                update_dict = {k: v for k, v in d.items() if k in valid_cols and k != "name" and not isinstance(v, list) and not isinstance(v, dict)}
                if update_dict:
                    set_clause = ", ".join([f"`{k}`=%s" for k in update_dict.keys()])
                    values = list(update_dict.values())
                    values.append(d.get("name"))
                    frappe.db.sql(f"UPDATE `tab{dt}` SET {set_clause} WHERE name=%s", tuple(values))
                
                # Update Child Tables
                for k, v in d.items():
                    if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and "name" in v[0]:
                        if not frappe.db.has_column(v[0].get("doctype"), "name"):
                            continue
                        child_valid_cols = set(frappe.db.get_table_columns(v[0].get("doctype")))
                        for row in v:
                            c_update = {ck: cv for ck, cv in row.items() if ck in child_valid_cols and ck != "name" and not isinstance(cv, list) and not isinstance(cv, dict)}
                            if c_update:
                                c_set = ", ".join([f"`{ck}`=%s" for ck in c_update.keys()])
                                c_vals = list(c_update.values())
                                c_vals.append(row.get("name"))
                                frappe.db.sql(f"UPDATE `tab{row.get('doctype')}` SET {c_set} WHERE name=%s", tuple(c_vals))
                                
                total_updated += 1
                
            frappe.db.commit()
            print(f"Successfully synced {total_updated} exact records for {dt}.")
        except Exception as e:
            print(f"Error syncing {dt}: {e}")

if __name__ == "__main__":
    sync_exact_all_fields()
