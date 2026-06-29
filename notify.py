"""
Lokale PC-varsler (Windows): toast-popup og lyd-alarm.

Brukes i tillegg til ntfy slik at du blir varslet rett på maskinen uten å måtte
installere noen mobil-app. Begge funksjonene er "best effort" — feiler de (feil
OS, manglende pakke), logges det og resten av appen kjører videre.
"""

import logging

log = logging.getLogger("ullevaal")


def play_alarm(cycles=6):
    """
    Spill en lyd-alarm. Bruker innebygd winsound (kun Windows) — ingen ekstra
    pakke nødvendig. Alternerende toner et par sekunder så du hører det.
    """
    try:
        import winsound

        for _ in range(cycles):
            winsound.Beep(880, 250)   # høy tone
            winsound.Beep(660, 250)   # lavere tone
    except Exception as exc:  # noqa: BLE001 - lyd skal aldri kunne krasje appen
        log.warning("Klarte ikke spille lyd-alarm: %s", exc)


def show_toast(title, message, url=None):
    """
    Vis en Windows toast-popup. Krever pakken 'winotify'
    (pip install winotify). Popup-en er klikkbar og åpner billettsiden.
    """
    try:
        from winotify import Notification

        toast = Notification(
            app_id="Ullevaal billettvarsler",
            title=title,
            msg=message,
            duration="long",
        )
        if url:
            toast.add_actions(label="Åpne billettsiden", launch=url)
        toast.show()
    except ImportError:
        log.warning(
            "Pakken 'winotify' mangler — ingen toast-popup. "
            "Installer med: pip install winotify"
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Klarte ikke vise toast-popup: %s", exc)


def notify_local(title, message, url=None, do_toast=True, do_sound=True):
    """Fyr av de lokale varslene som er skrudd på."""
    if do_toast:
        show_toast(title, message, url)
    if do_sound:
        play_alarm()
