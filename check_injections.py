import ast, glob

# Find all test files that have the bad injection pattern
for f in sorted(glob.glob('tests/test_*.py')):
    with open(f) as fh:
        lines = fh.readlines()
    
    # Check if this file has the bad pattern (indented import pytest block inside function)
    bad_inserted = False
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        # Match the injected "import pytest" at column 0 inside a function
        if stripped == 'import pytest' and i > 0:
            # Check if previous non-blank line is indented (inside function)
            for j in range(i-1, -1, -1):
                if lines[j].strip():
                    if lines[j][0] in (' ', '\t'):
                        bad_inserted = True
                        print(f'  BAD: {f} line {i+1} (after indented line {j+1})')
                    break
            if bad_inserted:
                break
    
print('Done scanning')
