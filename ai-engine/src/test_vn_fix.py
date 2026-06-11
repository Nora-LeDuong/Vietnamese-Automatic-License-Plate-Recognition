import ast, sys, re
from pathlib import Path

src_path = Path('ai-engine/src/inference.py').resolve()
src = src_path.read_text(encoding='utf-8')
ast.parse(src)
print('Syntax OK')

# Extract constants and function
ns = {'__file__': str(src_path)}
exec(src[:src.find('class ALPREngine')], ns)

match = re.search(
    r'def _correct_vn_plate\(text: str\) -> str:.*?return f\"\{prov\}\{series\} \{num_fixed\}\"',
    src, re.DOTALL
)
raw_fn = match.group()
dedented = '\n'.join(l[4:] if l.startswith('    ') else l for l in raw_fn.split('\n'))
exec(dedented, ns)
fn = ns['_correct_vn_plate']

cases = [
    # Cac loi pho bien da co
    ('514 05227',  '51A 05227',  '4 -> A  (series)'),
    ('S1A 05227',  '51A 05227',  'S -> 5  (tinh)'),
    ('5IA 05227',  '51A 05227',  'I -> 1  (tinh)'),
    ('30G 63611',  '30G 63611',  'giu nguyen'),
    ('88A 39307',  '88A 39307',  'giu nguyen'),
    ('614 05227',  '61A 05227',  '4->A, 61=Binh Duong'),
    ('B0G 63611',  '80G 63611',  'B -> 8  (tinh)'),
    ('3OG 63611',  '30G 63611',  'O -> 0  (tinh)'),
    ('51AB 123O',  '51AB 1230',  'O -> 0  (so bien)'),
    ('51F 3248B',  '51F 32488',  'B -> 8  (so bien)'),
    # Loi moi: F bị nham thanh 5
    ('FIF 79512',  '51F 79512',  'F->5, I->1 (tinh) | bien 51F-795.12'),
    ('F1F 79512',  '51F 79512',  'F->5 (tinh dau)'),
    ('FIF 63034',  '51F 63034',  'F->5, I->1 | bien 51F-630.34'),
    # E bị nham thanh 3, D bi nham thanh 0
    ('51F 7E512',  '51F 73512',  'E -> 3  (so bien)'),
    ('51F 7D512',  '51F 70512',  'D -> 0  (so bien)'),
]

print()
print(f"{'Input':<18} {'Got':<18} {'Expected':<18} Status  Note")
print('-' * 90)
ok = fail = 0
for inp, expected, note in cases:
    got    = fn(inp)
    passed = (got == expected)
    mark   = 'OK  ' if passed else 'FAIL'
    if passed: ok += 1
    else:      fail += 1
    print(f"{inp!r:<18} {got!r:<18} {expected!r:<18} {mark}  {note}")

print()
print(f"{'='*90}")
print(f"Result: {ok}/{ok+fail} passed {'✓ All good!' if fail == 0 else f'✗ {fail} failed'}")
