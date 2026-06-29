"""
Hindrer at Windows-maskinen sovner mens overvåkingen kjører.

Bruker Windows-APIet SetThreadExecutionState (via ctypes — ingen ekstra pakke).
Vi ber kun om at *systemet* holdes våkent; skjermen får fortsatt slå seg av, og
det er greit — scriptet kjører videre uansett.

Effekten varer så lenge prosessen lever (ES_CONTINUOUS) og nullstilles når vi
kaller allow_sleep() ved avslutning.
"""

import logging

log = logging.getLogger("ullevaal")

# Flagg fra Windows-APIet.
ES_CONTINUOUS = 0x80000000        # innstillingen skal gjelde til vi sier fra
ES_SYSTEM_REQUIRED = 0x00000001   # hold systemet våkent


def prevent_sleep():
    """Be Windows holde systemet våkent. Returnerer True hvis det lyktes."""
    try:
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )
        return True
    except Exception as exc:  # noqa: BLE001 - skal aldri kunne krasje appen
        log.warning("Klarte ikke hindre dvale (fortsetter uansett): %s", exc)
        return False


def allow_sleep():
    """Nullstill — la maskinen sove normalt igjen."""
    try:
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception:  # noqa: BLE001
        pass
