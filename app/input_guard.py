"""Straznik wejscia evdev — czysta logika, testowalna bez SDL/urzadzenia.

Klasa bledu: petla czyta PARTIE zdarzen evdev (`gp.read()` zwraca kilka zdarzen
naraz). Jesli w tej partii jest przycisk WYJSCIA (MENU/MODE), a petla przetwarza
zdarzenia po kolei, to zdarzenie regulacji stojace PRZED MENU zdazy zmienic
wartosc/stan, zanim aplikacja wyjdzie ("MENU dubluje funkcje" / "wartosc mruga
przy wyjsciu").

Fix: PRZED przetworzeniem czegokolwiek z partii sprawdz, czy jest w niej klawisz
wyjscia; jesli tak — wyjdz czysto, nie ruszajac zadnego pola. `batch_has_exit`
to ta bramka.
"""

EV_KEY = 1        # typ zdarzenia evdev: klawisz/przycisk
VAL_PRESS = 1     # value==1 => wcisniecie (2=autorepeat, 0=puszczenie)


def batch_has_exit(events, exit_codes, *, ev_key=EV_KEY, press=VAL_PRESS):
    """Czy w partii zdarzen jest WCISNIECIE klawisza wyjscia.

    events      — iterowalne zdarzen z atrybutami .type/.code/.value (evdev).
    exit_codes  — zbior/kolekcja kodow wyjscia (np. {354, 316} = MENU/MODE).
    Zwraca True, gdy petla powinna NATYCHMIAST wyjsc bez regulacji.
    """
    for e in events:
        if e.type == ev_key and e.value == press and e.code in exit_codes:
            return True
    return False
