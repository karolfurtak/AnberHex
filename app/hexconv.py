#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AnberHex — logika konwersji systemów liczbowych (HEX ↔ DEC), bez SDL.

Wydzielona z main.py żeby była testowalna (pytest) i uruchamialna w CI bez
biblioteki SDL/wyświetlacza. Self-test: `python3 hexconv.py`.
"""
import sys

HEX_DIGITS = "0123456789ABCDEF"
DEC_DIGITS = "0123456789"
MAX_LEN    = 16   # limit długości wejścia (16 hex ≈ 64-bit; spokojnie się mieści)


def parse_value(s: str, mode: str):
    """Zwraca int z napisu w danym trybie ('H2D'→base16, 'D2H'→base10) lub None."""
    if not s:
        return None
    try:
        return int(s, 16 if mode == 'H2D' else 10)
    except ValueError:
        return None


def group(s: str, n: int, sep: str = ' ') -> str:
    """Grupuje napis od prawej co n znaków: '12345' /3 → '12 345'."""
    if len(s) <= n:
        return s
    out = []
    while len(s) > n:
        out.append(s[-n:]); s = s[:-n]
    out.append(s)
    return sep.join(reversed(out))


def conversions(s: str, mode: str):
    """Słownik wyników: dec/hex/bin/oct (pogrupowane) lub None gdy puste/błędne."""
    v = parse_value(s, mode)
    if v is None:
        return None
    return {
        'val': v,
        'dec': group(str(v), 3),
        'hex': group(format(v, 'X'), 4),
        'bin': group(format(v, 'b'), 4),
        'oct': format(v, 'o'),
    }


def derivation(s, mode):
    """Pełny zapis działania konwersji jako lista linii.
    H2D: rozwinięcie pozycyjne (potęgowanie · mnożenie · dodawanie).
    D2H: kolejne dzielenie z resztą (reszty czytane od dołu)."""
    v = parse_value(s, mode)
    if v is None:
        return []
    if mode == 'H2D':
        s = s.upper()
        n = len(s)
        pow_terms, mul_terms, add_terms = [], [], []
        for i, ch in enumerate(s):
            k = n - 1 - i
            d = int(ch, 16)
            pow_terms.append(f'{ch}·16^{k}')
            mul_terms.append(f'{d}·{16 ** k}')
            add_terms.append(str(d * 16 ** k))
        return [
            'wzór:  d_k·16^k + ... + d_1·16^1 + d_0·16^0',
            ' + '.join(pow_terms) + ' =',
            ' + '.join(mul_terms) + ' =',
            ' + '.join(add_terms) + ' =',
            str(v),
        ]
    # D2H — dzielenie z resztą
    wzor = 'wzór:  n : 16 = iloraz  r reszta  (powtarzaj do 0)'
    if v == 0:
        return [wzor, '0 : 16 = 0  r 0 → 0', 'reszty od dołu → 0']
    lines, digits, x = [wzor], [], v
    while x > 0:
        q, r = divmod(x, 16)
        hd = format(r, 'X')
        lines.append(f'{x} : 16 = {q}  r {r} → {hd}')
        digits.append(hd)
        x = q
    lines.append('reszty od dołu → ' + ''.join(reversed(digits)))
    return lines


def _selftest():
    cases = [
        ('1A3F', 'H2D', 6719),
        ('FF',   'H2D', 255),
        ('DEAD', 'H2D', 57005),
        ('255',  'D2H', 255),       # → FF
        ('4096', 'D2H', 4096),      # → 1000
        ('0',    'H2D', 0),
    ]
    ok = True
    for s, m, exp in cases:
        c = conversions(s, m)
        got = c['val'] if c else None
        status = 'OK ' if got == exp else 'FAIL'
        if got != exp:
            ok = False
        extra = f"dec={c['dec']} hex={c['hex']} bin={c['bin']}" if c else ''
        print(f"[{status}] {m} {s!r} -> {got} (exp {exp})  {extra}")
    assert conversions('', 'H2D') is None
    assert conversions('XYZ', 'H2D') is None
    assert conversions('9', 'D2H')['hex'] == '9'
    assert conversions('4660', 'D2H')['hex'] == '1234'
    dv = derivation('1A3F', 'H2D')
    print('H2D deriv:', ' | '.join(dv))
    assert dv[0].startswith('wzór')
    assert dv[1] == '1·16^3 + A·16^2 + 3·16^1 + F·16^0 ='
    assert dv[2].endswith('=') and dv[3].endswith('=')
    assert dv[-1] == '6719'
    dh = derivation('6719', 'D2H')
    print('D2H deriv:', ' | '.join(dh))
    assert dh[0].startswith('wzór')
    assert dh[-1].endswith('1A3F')
    v0 = parse_value('1A3F', 'H2D'); assert v0 == 6719 and format(v0, 'X') == '1A3F'
    print('selftest:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(_selftest())
