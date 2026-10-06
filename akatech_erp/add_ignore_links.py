import os

folder = '/mnt/c/Users/Administrator/Desktop/ERP'
files = ['setup_client.py', 'setup_extras.py', 'workspace_setup.py']

for f in files:
    path = os.path.join(folder, f)
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace doc.insert(ignore_permissions=True) with 
    # doc.flags.ignore_links = True
    # doc.insert(ignore_permissions=True)
    
    # Need to preserve indentation. So we find the indentation level.
    # Actually, we can just replace '            doc.insert(ignore_permissions=True)'
    
    # Using regex to preserve exactly whatever indentation was there
    import re
    # Match any amount of spaces before doc.insert
    content = re.sub(r'([ \t]+)doc.insert\(ignore_permissions=True\)', 
                     r'\1doc.flags.ignore_links = True\n\1doc.insert(ignore_permissions=True)', 
                     content)
                     
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)
        
print("Added ignore_links to all setup scripts.")
