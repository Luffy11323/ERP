import frappe

def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    print("Connected to DB.", flush=True)
    count = frappe.db.count('Customer')
    print(f"Customer count: {count}", flush=True)
    names = frappe.get_all('Customer', pluck='name')
    print(f"Fetched {len(names)} customer names", flush=True)
    
if __name__ == "__main__":
    main()
