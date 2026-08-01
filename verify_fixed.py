import ast
files = [
    'tests/test_seo_internal_linker.py',
    'tests/test_users.py',
    'tests/test_publish_integration.py',
]
for f in files:
    ast.parse(open(f).read(), filename=f)
    print(f'  {f}: OK')
print('All 3 fixed files compile clean')
