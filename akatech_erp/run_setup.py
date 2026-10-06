import frappe
import os

def run():
    folder = '/mnt/c/Users/Administrator/Desktop/ERP'
    scripts = ['doctype_setup.py', 'setup_client.py', 'setup_extras.py', 'workspace_setup.py']
    
    exec_globals = globals().copy()
    exec_globals['log'] = lambda msg: print(msg)
    
    frappe.flags.in_fixtures = True
    frappe.flags.in_patch = True
    
    for s in scripts:
        path = os.path.join(folder, s)
        print(f'Executing {path}...')
        with open(path, 'r', encoding='utf-8') as f:
            exec(f.read(), exec_globals)
        frappe.db.commit()
    print('All scripts executed successfully!')
