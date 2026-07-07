#!/usr/bin/env python3
"""
Frogner-varsler for Fotballfesten 2026 (Norge vs England, kvartfinale 11. juli).

Fokusert overvåker som varsler i det øyeblikket Frogner-billettene legges ut på
fanparks.fanparks.com. Kongens gate for samme kamp er allerede utsolgt, så her
gjelder det å være rask.

Tre typer mål (se FANPARK_TARGETS i config.py):
  - direct:   kandidat-URL-er som gir 404 nå og skal flippe til 200 + ekte
              booking-innhold ("Kjøp"/"Inngangstid")
  - catchall: fotballfesten.no-siden — varsler når en lenke mot
              fanparks.fanparks.com/booking/ dukker opp (fanger ukjent slug)
  - reference: kjent live side, brukes kun av --test. Varsler aldri.

Varsler kun på selve overgangen ikke-live -> live (én gang per mål); siste
kjente status ligger i en JSON-statusfil så scriptet er idempotent.

Kjøring:
    python fanpark_monitor.py            # evig overvåking (2,5 min ± jitter)
    python fanpark_monitor.py --once     # én sjekk-runde og avslutt (cron/Actions)
    python fanpark_monitor.py --test     # test-varsel + verifiser deteksjonen
                                         # mot Kongens gate-referansen
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
import keepawake
import notify


# --- Logging-oppsett (samme mønster som monitor.py) ---------------------------
def _setup_logging():
    # Tving UTF-8 på konsollen så norske tegn ikke krasjer loggingen på Windows.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.FANPARK_LOG_FILE, encoding="utf-8"),
        ],
    )


log = logging.getLogger("fanpark")

ALERT_TITLE = "Frogner LIVE: Norge vs England"

# /events/KODE — under-hendelser (enkeltkamper) på en booking-side.
EVENT_RE = re.compile(r"/events/[A-Za-z0-9]{6}\b")


# --- Henting med retry/backoff -------------------------------------------------
def fetch(url):
    """
    GET med retries og økende ventetid ved nettverksfeil.

    404 og andre HTTP-statuser er gyldige svar (404 = "ikke live ennå") og
    returneres som de er. Kaster requests.RequestException først når alle
    forsøkene er brukt opp.
    """
    headers = {"User-Agent": config.USER_AGENT}
    last_exc = None
    for attempt in range(1, config.FANPARK_RETRIES + 1):
        try:
            return requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < config.FANPARK_RETRIES:
                wait = 2 ** attempt  # 2s, 4s, ...
                log.warning(
                    "Henting feilet (forsøk %d/%d) for %s: %s — prøver igjen om %ds",
                    attempt, config.FANPARK_RETRIES, url, exc, wait,
                )
                time.sleep(wait)
    raise last_exc


def _looks_like_booking_page(html):
    """Er dette en ekte booking-side, ikke bare en tom/vedlikeholds-side med 200?"""
    lower = html.lower()
    return any(marker in lower for marker in config.FANPARK_LIVE_MARKERS)


# --- Sjekk av de ulike måltypene ------------------------------------------------
def check_direct(target):
    """
    Kandidat-URL: live når den svarer 200 OG kroppen ser ut som en booking-side.
    Returnerer (live, booking_url, html, detalj).
    """
    resp = fetch(target["url"])
    if resp.status_code != 200:
        return False, None, None, f"HTTP {resp.status_code}"
    if not _looks_like_booking_page(resp.text):
        return False, None, None, "200, men mangler booking-markører (tom/vedlikeholdsside?)"
    return True, target["url"], resp.text, "200 + booking-innhold"

def check_catchall(target):
    """
    Catch-all-side: live når det dukker opp en href mot
    fanparks.fanparks.com/booking/ (uansett slug). Kjente/irrelevante fanparks
    filtreres bort via "exclude"-lista på målet.
    """
    resp = fetch(target["url"])
    if resp.status_code != 200:
        return False, None, None, f"HTTP {resp.status_code}"
    soup = BeautifulSoup(resp.text, "html.parser")
    excludes = [x.lower() for x in target.get("exclude", [])]
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "fanparks.fanparks.com/booking/" not in href.lower():
            continue
        if any(x in href.lower() for x in excludes):
            continue
        booking_url = urljoin(target["url"], href)
        # Hent selve booking-siden også (best effort) så varselet kan få med
        # kampinfo og /events/-lenker.
        html = None
        try:
            booking_resp = fetch(booking_url)
            if booking_resp.status_code == 200:
                html = booking_resp.text
        except requests.RequestException as exc:
            log.warning("Fant booking-lenke, men klarte ikke hente den: %s", exc)
        return True, booking_url, html, f"ny booking-lenke funnet: {booking_url}"
    return False, None, None, "ingen booking-lenke på siden ennå"


def check_target(target):
    """Sjekk ett mål. Returnerer (live, booking_url, html, detalj)."""
    if target["type"] == "direct":
        return check_direct(target)
    if target["type"] == "catchall":
        return check_catchall(target)
    raise ValueError(f"Ukjent måltype: {target['type']}")


# --- Bonus: kampinfo fra booking-siden ------------------------------------------
def extract_match_info(html, base_url):
    """
    Best effort: finn "Norge vs England"-status og /events/KODE-lenker på en
    live booking-side. Returnerer liste med tekstlinjer til varselet — tom
    liste hvis ingenting ble funnet. Skal aldri kunne krasje kalleren.
    """
    lines = []
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Let etter selve kampen blant event-lenkene, og sjekk utsolgt-status.
        match_found = False
        for a in soup.find_all("a", href=True):
            if not EVENT_RE.search(a["href"]):
                continue
            text = a.get_text(" ", strip=True).lower()
            if all(k in text for k in config.FANPARK_MATCH_KEYWORDS):
                match_found = True
                event_url = urljoin(base_url, a["href"])
                if "utsolgt" in text:
                    lines.append(f"OBS: Norge vs England er merket UTSOLGT: {event_url}")
                else:
                    lines.append(f"Norge vs England funnet (ikke merket utsolgt): {event_url}")
                break

        page_text = soup.get_text(" ", strip=True).lower()
        if not match_found and all(k in page_text for k in config.FANPARK_MATCH_KEYWORDS):
            lines.append("Siden nevner Norge og England (fant ikke egen kamplenke).")

        # Alle under-hendelser på siden, som klikkbare URL-er.
        codes = list(dict.fromkeys(EVENT_RE.findall(html)))  # unike, i rekkefølge
        if codes:
            urls = [urljoin(base_url, c) for c in codes[:10]]
            lines.append("Under-hendelser: " + ", ".join(urls))
    except Exception as exc:  # noqa: BLE001 - bonusinfo skal aldri velte varselet
        log.warning("Klarte ikke hente kampinfo fra booking-siden: %s", exc)
    return lines


# --- Varsling --------------------------------------------------------------------
def send_ntfy(title, message, click_url, priority="urgent", tags="soccer,rotating_light"):
    """Send push til samme ntfy-topic som resten av prosjektet."""
    url = f"{config.NTFY_SERVER}/{config.NTFY_TOPIC}"
    headers = {
        "Title": title,
        "Priority": priority,
        "Tags": tags,
        "Click": click_url,  # gjør hele varselet klikkbart rett til booking-siden
    }
    resp = requests.post(
        url,
        data=message.encode("utf-8"),
        headers=headers,
        timeout=config.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    log.info("Push-varsel sendt til ntfy-topic '%s'.", config.NTFY_TOPIC)


def notify_live(target, booking_url, html):
    """
    Fyr av alle aktive varsler om at et mål har gått live. Kanalene er
    uavhengige: feiler én, prøver vi fortsatt de andre.
    """
    parts = [
        "Frogner-billettene (Norge vs England, kvartfinale 11. juli) ser ut til å være ute!",
        "",
        f"Kjøp her: {booking_url}",
    ]
    if html:
        info = extract_match_info(html, booking_url)
        if info:
            parts.append("")
            parts.extend(info)
    parts.append("")
    parts.append(f"(Oppdaget via mål: {target['name']})")
    message = "\n".join(parts)

    # Lokale varsler (toast + lyd) rett på denne maskinen.
    notify.notify_local(
        ALERT_TITLE,
        message,
        url=booking_url,
        do_toast=config.NOTIFY_TOAST,
        do_sound=config.NOTIFY_SOUND,
    )

    # Push til ntfy (mobil/nettleser).
    if config.NOTIFY_NTFY:
        try:
            send_ntfy(ALERT_TITLE, message, booking_url)
        except requests.RequestException as exc:
            log.error("Klarte ikke sende ntfy push-varsel: %s", exc)


# --- Statusfil (JSON) -------------------------------------------------------------
def load_state(path):
    """Les siste kjente status per mål. Tom dict hvis fila mangler/er korrupt."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001
        log.warning("Klarte ikke lese statusfila %s (%s) — starter blankt.", path, exc)
        return {}


def save_state(path, state):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# --- Sjekk-runde -------------------------------------------------------------------
def run_checks(state_path):
    """
    Én full sjekk-runde over alle målene. Varsler kun på overgang
    ikke-live -> live, og skriver statusfila bare når noe faktisk endret seg
    (viktig i CI: ellers ville hver kjøring laget en ny commit).
    """
    state = load_state(state_path)
    changed = False

    for target in config.FANPARK_TARGETS:
        if target["type"] == "reference":
            continue  # brukes kun av --test

        name = target["name"]
        try:
            live, booking_url, html, detail = check_target(target)
        except requests.RequestException as exc:
            log.error("Nettverksfeil for %s (beholder forrige status): %s", name, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            log.error("Uventet feil for %s (beholder forrige status): %s", name, exc)
            continue

        was_live = state.get(name, {}).get("live", False)
        if live and not was_live:
            log.info(">>> LIVE! %s: %s", name, detail)
            notify_live(target, booking_url, html)
        elif not live and was_live:
            # Gikk tilbake til ikke-live — nullstill så en ny åpning varsler igjen.
            log.warning("%s var live, men er det ikke lenger (%s) — nullstiller.", name, detail)
        else:
            log.info("Uendret (%s): %s", name, detail)

        new_entry = {"live": live, "booking_url": booking_url}
        if state.get(name) != new_entry:
            state[name] = new_entry
            changed = True

        # Liten pust mellom målene — ikke hamre serveren.
        time.sleep(random.uniform(1.0, 2.5))

    if changed:
        save_state(state_path, state)
    return changed


# --- Moduser ------------------------------------------------------------------------
def monitor_loop(state_path):
    """Evig overvåking med jitter mellom rundene. Krasjer aldri på nett-/parsefeil."""
    interval = max(config.FANPARK_INTERVAL, config.MIN_INTERVAL)
    if config.FANPARK_INTERVAL < config.MIN_INTERVAL:
        log.warning(
            "FANPARK_INTERVAL=%ss er under grensen — bruker %ss i stedet.",
            config.FANPARK_INTERVAL, config.MIN_INTERVAL,
        )

    watched = [t for t in config.FANPARK_TARGETS if t["type"] != "reference"]
    log.info("Starter Frogner-overvåking av %d mål:", len(watched))
    for t in watched:
        log.info("  [%s] %s", t["type"], t["url"])
    log.info(
        "Intervall: %ss ± %ss jitter. Statusfil: %s. ntfy: %s",
        interval, config.FANPARK_JITTER,
        state_path,
        config.NTFY_TOPIC if config.NOTIFY_NTFY else "av",
    )

    if config.PREVENT_SLEEP and keepawake.prevent_sleep():
        log.info("Hindrer at PC-en sovner så lenge overvåkingen kjører.")

    try:
        while True:
            try:
                run_checks(state_path)
            except Exception as exc:  # noqa: BLE001 - loopen skal aldri dø
                log.error("Uventet feil i sjekk-runden: %s", exc)
            sleep = interval + random.uniform(-config.FANPARK_JITTER, config.FANPARK_JITTER)
            time.sleep(max(sleep, config.MIN_INTERVAL))
    finally:
        keepawake.allow_sleep()


def run_test():
    """
    --test: verifiser at deteksjonen fungerer mot den kjente live-referansen
    (Kongens gate), og send et test-varsel. Returnerer True hvis alt er OK.
    """
    ok = True

    ref = next((t for t in config.FANPARK_TARGETS if t["type"] == "reference"), None)
    if ref is None:
        log.error("Ingen 'reference'-mål i FANPARK_TARGETS — kan ikke teste 200-stien.")
        ok = False
    else:
        log.info("Tester 200-stien mot referansen: %s", ref["url"])
        try:
            resp = fetch(ref["url"])
            if resp.status_code != 200:
                log.error("Referansen ga HTTP %s — forventet 200!", resp.status_code)
                ok = False
            elif not _looks_like_booking_page(resp.text):
                log.error(
                    "Referansen ga 200, men markørene %s ble ikke funnet — "
                    "deteksjonen ville IKKE slått ut!", config.FANPARK_LIVE_MARKERS,
                )
                ok = False
            else:
                log.info("OK: referansen gir 200 og gjenkjennes som booking-side.")
                for line in extract_match_info(resp.text, ref["url"]):
                    log.info("Kampinfo fra referansen: %s", line)
        except requests.RequestException as exc:
            log.error("Klarte ikke hente referansesiden: %s", exc)
            ok = False

    log.info("Sender test-varsel ...")
    notify.notify_local(
        "Frogner-varsler (TEST)",
        "Dette er en test. Ser/hører du dette, funker varslingen.",
        url=config.FANPARK_TARGETS[0]["url"],
        do_toast=config.NOTIFY_TOAST,
        do_sound=config.NOTIFY_SOUND,
    )
    if config.NOTIFY_NTFY:
        try:
            send_ntfy(
                "Frogner-varsler (TEST)",
                "Dette er en test. Hvis du ser dette på mobilen, funker varslingen.",
                config.FANPARK_TARGETS[0]["url"],
                priority="default",
                tags="soccer,white_check_mark",
            )
        except requests.RequestException as exc:
            log.error("Klarte ikke sende test-varsel til ntfy: %s", exc)
            ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(
        description="Frogner-varsler for Fotballfesten 2026 (Norge vs England)."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Kjør én sjekk-runde og avslutt (cron/GitHub Actions).",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send test-varsel og verifiser deteksjonen mot Kongens gate-referansen.",
    )
    parser.add_argument(
        "--state-file",
        default=config.FANPARK_STATE_FILE,
        help="JSON-fil med siste kjente status per mål (default: %(default)s).",
    )
    args = parser.parse_args()

    _setup_logging()

    if args.test:
        sys.exit(0 if run_test() else 1)

    if args.once:
        try:
            run_checks(args.state_file)
            sys.exit(0)
        except Exception as exc:  # noqa: BLE001
            log.error("Uventet feil: %s", exc)
            sys.exit(1)

    try:
        monitor_loop(args.state_file)
    except KeyboardInterrupt:
        log.info("Avslutter Frogner-overvåking (Ctrl+C). Ha det!")
        sys.exit(0)


if __name__ == "__main__":
    main()
