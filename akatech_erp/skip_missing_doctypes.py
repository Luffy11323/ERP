import os

folder = '/mnt/c/Users/Administrator/Desktop/ERP'
files = ['setup_client.py', 'setup_extras.py', 'workspace_setup.py']

for f in files:
    path = os.path.join(folder, f)
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # We want to replace:
    #             doc.flags.ignore_links = True
    #             doc.insert(ignore_permissions=True)
    # with:
    #             doc.flags.ignore_links = True
    #             try:
    #                 doc.insert(ignore_permissions=True)
    #             except frappe.DoesNotExistError:
    #                 print(f"Skipping {doc.name} as target DocType does not exist")
    #                 pass
    
    import re
    # Match the ignore_links and insert
    pattern = r'([ \t]+)doc\.flags\.ignore_links = True\n\1doc\.insert\(ignore_permissions=True\)'
    
    replacement = r'\1doc.flags.ignore_links = True\n\1try:\n\1    doc.insert(ignore_permissions=True)\n\1except frappe.DoesNotExistError:\n\1    print("Skipped because target DocType does not exist")\n\1except Exception as e:\n\1    print(f"Skipped due to error: {e}")'
    
    content = re.sub(pattern, replacement, content)
    
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)
        
print("Added exception handling to all setup scripts.")
