#!/usr/bin/env python3
"""
Billettvarsler for Fotballfesten Ullevaal 2026.

Poller billettsiden med jevne mellomrom og varsler (toast + lyd på PC, og/eller
ntfy) når noe skjer med billettsalget. To moduser (se config.ALERT_MODE):
  - "endring"  – varsler ved ENHVER endring i statussetningen (standard)
  - "aapning"  – varsler kun når salget går fra STENGT til ÅPENT

Kjøring:
    python monitor.py                # evig overvåking
    python monitor.py --once         # sjekk status én gang og avslutt
    python monitor.py --test-notify  # send et test-varsel og avslutt
"""

import argparse
import logging
import sys
import time

import requests
from bs4 import BeautifulSoup

import config
import notify


# --- Logging-oppsett ---------------------------------------------------------
# Skriver både til konsoll og til loggfil, med tidsstempel.
def _setup_logging():
    # Tving UTF-8 på konsollen så norske tegn og emoji fra siden ikke krasjer
    # loggingen på Windows (cp1252).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=datefmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        ],
    )


log = logging.getLogger("ullevaal")


# --- Statusene vi opererer med ----------------------------------------------
OPEN = "ÅPENT"
CLOSED = "STENGT"


def fetch_status():
    """
    Hent siden og avgjør om salget er STENGT eller ÅPENT.

    Returnerer config-statusene OPEN/CLOSED. Kaster videre ved nettverks- eller
    parse-feil slik at kalleren kan logge og fortsette loopen.
    """
    headers = {"User-Agent": config.USER_AGENT}
    resp = requests.get(config.URL, headers=headers, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()

    # Hent ut ren sidetekst og match case-insensitivt på delstrengen.
    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True).lower()

    if config.MATCH_STRING.lower() in page_text:
        return CLOSED
    return OPEN


def _fetch_page_text():
    """Hent siden og returner ren, samlet sidetekst. Kaster videre ved feil."""
    headers = {"User-Agent": config.USER_AGENT}
    resp = requests.get(config.URL, headers=headers, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def fetch_status_text():
    """
    Hent siden og plukk ut statussetningen — setningen som inneholder ankerordet
    (f.eks. "Billettsalg ... er midlertidig stengt.").

    Returnerer setningen (trimmet) eller None hvis ankerordet ikke finnes — at
    setningen forsvinner er i seg selv en endring vi vil fange opp.
    """
    full = _fetch_page_text()
    anchor = config.STATUS_ANCHOR.lower()
    i = full.lower().find(anchor)
    if i == -1:
        return None
    # Fra ankerordet til neste punktum — gir akkurat statussetningen, uten
    # toppmeny og resten av siden.
    end = full.find(".", i)
    if end == -1:
        end = len(full)
    return full[i:end].strip()


def notify_change(title, message):
    """
    Send varsel på alle aktive kanaler (lokal toast + lyd, og ntfy hvis på).
    Hvert varsel er uavhengig: feiler ett, prøver vi fortsatt de andre.
    """
    # Lokale varsler rett på denne maskinen.
    notify.notify_local(
        title,
        message,
        url=config.URL,
        do_toast=config.NOTIFY_TOAST,
        do_sound=config.NOTIFY_SOUND,
    )

    # Push til ntfy (mobil/nettleser).
    if config.NOTIFY_NTFY:
        try:
            send_open_notification()
        except requests.RequestException as exc:
            log.error("Klarte ikke sende ntfy push-varsel: %s", exc)


def notify_open():
    """Varsel for "aapning"-modus: salget har gått fra STENGT til ÅPENT."""
    notify_change(
        "Fotballfesten billetter",
        "Billettsalget for Fotballfesten Ullevaal 2026 er ÅPENT nå!\n"
        f"Trykk her: {config.URL}",
    )


def send_open_notification():
    """Send push-varsel til ntfy om at salget har åpnet."""
    url = f"{config.NTFY_SERVER}/{config.NTFY_TOPIC}"
    message = (
        "Billettsalget for Fotballfesten Ullevaal 2026 er ÅPENT nå!\n"
        f"Trykk her: {config.URL}"
    )
    headers = {
        "Title": "Fotballfesten billetter",
        "Priority": "urgent",
        "Tags": "soccer",
        "Click": config.URL,  # gjør hele varselet klikkbart rett til siden
    }
    resp = requests.post(
        url,
        data=message.encode("utf-8"),
        headers=headers,
        timeout=config.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    log.info("Push-varsel sendt til ntfy-topic '%s'.", config.NTFY_TOPIC)


def send_test_notification():
    """Send et isolert test-varsel slik at du kan bekrefte at push når mobilen."""
    url = f"{config.NTFY_SERVER}/{config.NTFY_TOPIC}"
    headers = {
        "Title": "Fotballfesten billetter (TEST)",
        "Priority": "default",
        "Tags": "soccer,white_check_mark",
    }
    message = "Dette er en test. Hvis du ser dette på mobilen, funker varslingen."
    try:
        resp = requests.post(
            url,
            data=message.encode("utf-8"),
            headers=headers,
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        log.info("Test-varsel sendt til topic '%s'. Sjekk mobilen.", config.NTFY_TOPIC)
        return True
    except requests.RequestException as exc:
        log.error("Klarte ikke sende test-varsel: %s", exc)
        return False


def check_once():
    """Sjekk status én gang og logg resultatet (avhengig av modus)."""
    if config.ALERT_MODE == "aapning":
        status = fetch_status()
        log.info("Status nå: %s", status)
        return status
    # "endring"-modus: vis selve statussetningen vi overvåker.
    text = fetch_status_text()
    log.info("Statustekst nå: %s", text if text else "(fant ikke statussetningen)")
    return text


def _log_startup(interval):
    """Logg oppstartsinfo: side, modus og varslingskanaler."""
    log.info("Starter overvåking av %s", config.URL)
    log.info("Modus: %s", config.ALERT_MODE)
    aktive = []
    if config.NOTIFY_TOAST:
        aktive.append("toast")
    if config.NOTIFY_SOUND:
        aktive.append("lyd")
    if config.NOTIFY_NTFY:
        aktive.append(f"ntfy:{config.NTFY_TOPIC}")
    log.info("Intervall: %ss. Varslingskanaler: %s", interval, ", ".join(aktive) or "ingen")
    if config.NOTIFY_NTFY and config.NTFY_TOPIC.startswith("BYTT-MEG"):
        log.warning(
            "NTFY_TOPIC er fortsatt placeholder! Sett din egen i config.py "
            "eller via miljøvariabel, ellers når ikke varslene fram."
        )


def _loop_aapning(interval):
    """Loop som kun varsler ved STENGT -> ÅPENT."""
    last_status = None
    while True:
        try:
            status = fetch_status()
            if last_status is None:
                log.info("Første sjekk — status: %s", status)
            elif status != last_status:
                log.info("Tilstandsendring: %s -> %s", last_status, status)
                if last_status == CLOSED and status == OPEN:
                    notify_open()  # øyeblikket vi venter på
                # ÅPENT -> STENGT logges kun.
            else:
                log.info("Uendret status: %s", status)
            last_status = status
        except requests.RequestException as exc:
            log.error("Nettverksfeil ved henting: %s", exc)
        except Exception as exc:  # noqa: BLE001
            log.error("Uventet feil ved sjekk: %s", exc)
        time.sleep(interval)


def _loop_endring(interval):
    """Loop som varsler ved ENHVER endring i statussetningen."""
    last_text = None  # None = ikke sjekket ennå (etablerer utgangspunkt)
    while True:
        try:
            text = fetch_status_text()

            if last_text is None:
                log.info("Første sjekk — statustekst: %s",
                         text if text else "(fant ikke statussetningen)")
            elif text != last_text:
                # Statusteksten har endret seg — dette varsler vi om.
                log.info("ENDRING oppdaget:")
                log.info("  Før:  %s", last_text)
                log.info("  Nå:   %s", text if text else "(setningen forsvant)")
                notify_change(
                    "Fotballfesten: status endret!",
                    "Statusen på billettsiden har endret seg — sjekk om salget "
                    f"har åpnet!\n\nNå: {text or '(statusteksten forsvant)'}\n\n"
                    f"Trykk her: {config.URL}",
                )
            else:
                log.info("Uendret: %s", text if text else "(fant ikke statussetningen)")

            last_text = text
        except requests.RequestException as exc:
            log.error("Nettverksfeil ved henting: %s", exc)
        except Exception as exc:  # noqa: BLE001
            log.error("Uventet feil ved sjekk: %s", exc)
        time.sleep(interval)


def monitor_loop():
    """Evig overvåkingsloop med robust feilhåndtering."""
    # Håndhev nedre intervall-grense (liten arrangør-side — ikke hamre den).
    interval = max(config.INTERVAL, config.MIN_INTERVAL)
    if config.INTERVAL < config.MIN_INTERVAL:
        log.warning(
            "INTERVAL=%ss er under grensen — bruker %ss i stedet.",
            config.INTERVAL,
            config.MIN_INTERVAL,
        )

    _log_startup(interval)

    if config.ALERT_MODE == "aapning":
        _loop_aapning(interval)
    else:
        _loop_endring(interval)


def main():
    parser = argparse.ArgumentParser(
        description="Billettvarsler for Fotballfesten Ullevaal 2026."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Sjekk status én gang og avslutt (nyttig for feilsøking / cron).",
    )
    parser.add_argument(
        "--test-notify",
        action="store_true",
        help="Send et test-varsel til ntfy og avslutt.",
    )
    args = parser.parse_args()

    _setup_logging()

    if args.test_notify:
        # Test lokale PC-varsler (toast + lyd) ...
        log.info("Sender test-varsel lokalt (toast + lyd) ...")
        notify.notify_local(
            "Fotballfesten billetter (TEST)",
            "Dette er en test. Ser/hører du dette, funker PC-varslingen.",
            url=config.URL,
            do_toast=config.NOTIFY_TOAST,
            do_sound=config.NOTIFY_SOUND,
        )
        # ... og ntfy hvis det er skrudd på.
        ok = True
        if config.NOTIFY_NTFY:
            ok = send_test_notification()
        sys.exit(0 if ok else 1)

    if args.once:
        try:
            check_once()
            sys.exit(0)
        except requests.RequestException as exc:
            log.error("Nettverksfeil: %s", exc)
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            log.error("Uventet feil: %s", exc)
            sys.exit(1)

    try:
        monitor_loop()
    except KeyboardInterrupt:
        # Pen avslutning ved Ctrl+C.
        log.info("Avslutter overvåking (Ctrl+C). Ha det!")
        sys.exit(0)


if __name__ == "__main__":
    main()
