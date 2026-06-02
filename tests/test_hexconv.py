# -*- coding: utf-8 -*-
"""Testy logiki konwersji AnberHex (pytest). Importuje hexconv (bez SDL)."""
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'app'))
import hexconv as hc  # noqa: E402


# ── HEX → DEC ────────────────────────────────────────────────────────────────
def test_hex_to_dec_values():
    assert hc.conversions('1A3F', 'H2D')['val'] == 6719
    assert hc.conversions('FF', 'H2D')['val'] == 255
    assert hc.conversions('DEAD', 'H2D')['val'] == 57005
    assert hc.conversions('0', 'H2D')['val'] == 0


def test_hex_to_dec_formats():
    c = hc.conversions('FF', 'H2D')
    assert c['dec'] == '255'
    assert c['bin'] == '1111 1111'
    assert c['oct'] == '377'
    assert hc.conversions('DEAD', 'H2D')['dec'] == '57 005'


# ── DEC → HEX ────────────────────────────────────────────────────────────────
def test_dec_to_hex_values():
    assert hc.conversions('255', 'D2H')['hex'] == 'FF'
    assert hc.conversions('4096', 'D2H')['hex'] == '1000'
    assert hc.conversions('4660', 'D2H')['hex'] == '1234'
    assert hc.conversions('9', 'D2H')['hex'] == '9'


# ── przypadki brzegowe ───────────────────────────────────────────────────────
def test_invalid_input_returns_none():
    assert hc.conversions('', 'H2D') is None
    assert hc.conversions('XYZ', 'H2D') is None       # nie-hex
    assert hc.conversions('FF', 'D2H') is None         # F nie jest dziesiętne
    assert hc.parse_value('', 'H2D') is None


def test_group():
    assert hc.group('12345', 3) == '12 345'
    assert hc.group('FF', 4) == 'FF'
    assert hc.group('1234567', 3) == '1 234 567'
    assert hc.group('AB12', 4) == 'AB12'


# ── działanie (derivation) ───────────────────────────────────────────────────
def test_derivation_h2d():
    dv = hc.derivation('1A3F', 'H2D')
    assert dv[0].startswith('wzór')
    assert dv[1] == '1·16^3 + A·16^2 + 3·16^1 + F·16^0 ='
    assert dv[2].endswith('=') and dv[3].endswith('=')
    assert dv[-1] == '6719'


def test_derivation_d2h():
    dh = hc.derivation('6719', 'D2H')
    assert dh[0].startswith('wzór')
    assert dh[-1].endswith('1A3F')


def test_derivation_empty_for_invalid():
    assert hc.derivation('', 'H2D') == []
    assert hc.derivation('ZZ', 'H2D') == []


# ── carry-over przy zmianie kierunku (HEX↔DEC tej samej liczby) ───────────────
def test_roundtrip():
    for hexs in ('1A3F', 'FF', 'DEAD', '1000'):
        v = hc.parse_value(hexs, 'H2D')
        # ta sama wartość w DEC → z powrotem do HEX
        assert hc.conversions(str(v), 'D2H')['hex'].replace(' ', '') == hexs


def test_constants():
    assert hc.HEX_DIGITS == '0123456789ABCDEF'
    assert hc.DEC_DIGITS == '0123456789'
    assert hc.MAX_LEN == 16
