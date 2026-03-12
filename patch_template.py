"""Patch script: assembles new_template_p1..p4 and replaces HTML_TEMPLATE in app.py"""
import re, sys, os

base = os.path.dirname(__file__)

# Load each part
parts = []
for i in range(1, 5):
    fname = os.path.join(base, f'new_template_p{i}.py')
    ns = {}
    with open(fname, 'r', encoding='utf-8') as f:
        exec(f.read(), ns)
    parts.append(ns[f'PART{i}'])

new_template = ''.join(parts)

# Read app.py
app_path = os.path.join(base, 'app.py')
with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find old HTML_TEMPLATE bounds using a robust approach
start_marker = 'HTML_TEMPLATE = """'
end_marker = '"""\n'

start_idx = content.index(start_marker)
# Find the closing triple-quote AFTER the start
after_start = start_idx + len(start_marker)
end_idx = content.index('\n"""', after_start)

old_section = content[start_idx : end_idx + 4]  # include \n"""

new_section = 'HTML_TEMPLATE = """\n' + new_template + '\n"""'

new_content = content.replace(old_section, new_section, 1)

if new_content == content:
    print("ERROR: replacement had no effect — marker not found")
    sys.exit(1)

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"SUCCESS: HTML_TEMPLATE replaced. New template length: {len(new_template):,} chars")

# cleanup part files
for i in range(1, 5):
    fname = os.path.join(base, f'new_template_p{i}.py')
    try:
        os.remove(fname)
    except:
        pass
print("Temp files cleaned up.")
