import ast, glob
broken = []
ok = 0
for f in sorted(glob.glob('tests/test_*.py')):
    try:
        with open(f) as fh:
            ast.parse(fh.read(), filename=f)
        ok += 1
    except SyntaxError as e:
        broken.append((f, e))
print(f'OK: {ok}, BROKEN: {len(broken)}')
for path, err in broken:
    print(f'  {path}: line {err.lineno}: {err.msg}')
