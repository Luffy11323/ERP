import re
import json

path = '/mnt/c/Users/Administrator/Desktop/ERP/doctype_setup.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The file contains:
# doctypes = [
#     { ... },
#     { ... }
# ]
# We will use regex to find the Loan Refund dictionary and remove the duplicate amended_from field.
# But it's easier to just parse the whole file, fix the dict, and reconstruct it.

def fix_doctypes():
    # Extract the doctypes list string
    start_str = "    doctypes = ["
    start_idx = content.find(start_str)
    
    end_str = "    for dt_data in doctypes:"
    end_idx = content.find(end_str)
    
    if start_idx == -1 or end_idx == -1:
        print("Could not find doctypes array")
        return
        
    array_str = content[start_idx + 15 : end_idx].strip()
    
    # It's a python list but mostly JSON. It might have null, true, false.
    array_str = array_str.replace("null", "None").replace("true", "True").replace("false", "False")
    
    # Wait, ast.literal_eval would work if we replace null->None
    import ast
    try:
        doctypes = ast.literal_eval(array_str)
    except Exception as e:
        print(f"Failed to parse doctypes: {e}")
        return
        
    # Find Loan Refund
    for dt in doctypes:
        if dt.get("name") == "Loan Refund":
            # Remove duplicate amended_from
            seen = set()
            new_fields = []
            for f in dt.get("fields", []):
                fname = f.get("fieldname")
                if fname in seen:
                    print(f"Removing duplicate field {fname}")
                    continue
                seen.add(fname)
                new_fields.append(f)
            dt["fields"] = new_fields
            
    # Now format it back
    # Convert True/False/None back to true/false/null
    new_array_str = json.dumps(doctypes)
    
    # We want it to be nicely formatted or just dump it? 
    # Just dump it, it's fine.
    
    new_content = content[:start_idx + 15] + new_array_str + "\n" + content[end_idx:]
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print("Fixed Loan Refund!")

fix_doctypes()
