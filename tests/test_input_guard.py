# -*- coding: utf-8 -*-
"""Guard-testy wejscia AnberHex: MENU (partia zdarzen) NIE zmienia stanu.

Klasa bledu "MENU dubluje funkcje": petla czyta partie zdarzen evdev; jesli
regulacja stoi PRZED MENU w tej samej partii, to zmienia wartosc, po czym
aplikacja wychodzi. Fix = pre-scan calej partii (batch_has_exit) i czyste
wyjscie PRZED przetworzeniem czegokolwiek.

Uruchomienie lokalne (bez SDL): python -m unittest -q  (albo pytest na CI).
"""
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'app'))
from input_guard import batch_has_exit  # noqa: E402

MENU_KEYS = {354, 316}   # KEY_MENU / BTN_MODE — zgodnie z main.py
EV_KEY, EV_ABS = 1, 3


class Ev:
    """Minimalny sobowtor zdarzenia evdev (type/code/value)."""
    __slots__ = ('type', 'code', 'value')

    def __init__(self, type, code, value):
        self.type, self.code, self.value = type, code, value


def press(code):   return Ev(EV_KEY, code, 1)
def release(code): return Ev(EV_KEY, code, 0)
def dpad(code, v): return Ev(EV_ABS, code, v)


class TestBatchHasExit(unittest.TestCase):
    def test_menu_press_detected(self):
        self.assertTrue(batch_has_exit([press(354)], MENU_KEYS))
        self.assertTrue(batch_has_exit([press(316)], MENU_KEYS))

    def test_exit_detected_anywhere_in_batch(self):
        # MENU po zdarzeniu regulacji — bramka i tak lapie (klucz fiksa)
        batch = [dpad(16, 1), press(304), press(316)]
        self.assertTrue(batch_has_exit(batch, MENU_KEYS))

    def test_no_exit_when_only_adjustments(self):
        batch = [dpad(16, 1), press(304), dpad(17, -1)]
        self.assertFalse(batch_has_exit(batch, MENU_KEYS))

    def test_release_is_not_exit(self):
        # value==0 (puszczenie) nie moze wyzwalac wyjscia
        self.assertFalse(batch_has_exit([release(354)], MENU_KEYS))

    def test_wrong_code_is_not_exit(self):
        # 313 (martwy na tym egz.) ani zwykle przyciski nie sa wyjsciem
        self.assertFalse(batch_has_exit([press(313), press(304)], MENU_KEYS))


class TestMenuDoesNotMutateState(unittest.TestCase):
    """Symulacja petli: dyspozytor zmienia 'wartosc' na kody regulacji.
    Z bramka batch_has_exit partia z MENU nie moze zmienic wartosci."""

    ADJUST = {16, 17, 304, 305, 307}   # dpad + A/B/X → mutacje w apce

    def _dispatch_batch(self, state, batch):
        # replika logiki petli po fiksie: pre-scan → wyjscie bez regulacji
        if batch_has_exit(batch, MENU_KEYS):
            return 'exit'
        for e in batch:
            if e.code in self.ADJUST and e.value != 0:
                state['n'] += 1
        return 'run'

    def test_menu_batch_leaves_state_untouched(self):
        state = {'n': 0}
        # regulacja PRZED MENU w jednej partii — najgorszy przypadek
        r = self._dispatch_batch(state, [dpad(16, 1), press(304), press(316)])
        self.assertEqual(r, 'exit')
        self.assertEqual(state['n'], 0)   # NIC nie ruszone mimo regulacji przed MENU

    def test_normal_batch_still_mutates(self):
        state = {'n': 0}
        r = self._dispatch_batch(state, [dpad(16, 1), press(304)])
        self.assertEqual(r, 'run')
        self.assertEqual(state['n'], 2)   # bez MENU dziala normalnie


if __name__ == '__main__':
    unittest.main()
