"""
Konfigurasjon for billettvarsleren.

All konfig er samlet her. De fleste verdiene kan overstyres med miljøvariabler
slik at du slipper å endre koden (nyttig for cron/server senere).
"""

import os

# --- Målside -----------------------------------------------------------------
# Billettsiden vi overvåker. Sporings-parametere (?_gl=...) er fjernet — de
# trengs ikke og gjør bare URL-en stygg.
URL = os.environ.get(
    "URL",
    "https://fanparks.fanparks.com/booking/fotballfesten-ullevaal-2026",
)

# Teksten som betyr at salget er STENGT. Matches case-insensitivt som delstreng.
# Brukes kun i ALERT_MODE = "aapning".
MATCH_STRING = os.environ.get("MATCH_STRING", "midlertidig stengt")

# Hvordan appen avgjør at noe har skjedd:
#   "endring" – overvåk selve statussetningen og varsle ved ENHVER endring i den
#               (anbefalt: fanger åpning, "utsolgt", ombygd side osv.)
#   "aapning" – varsle kun når MATCH_STRING forsvinner (STENGT -> ÅPENT)
ALERT_MODE = os.environ.get("ALERT_MODE", "endring").lower()

# Ankerord som identifiserer statussetningen i "endring"-modus. Vi plukker ut
# setningen som inneholder dette ordet og overvåker den for endringer.
# På denne siden står det: "Billettsalg for ... er midlertidig stengt."
STATUS_ANCHOR = os.environ.get("STATUS_ANCHOR", "billettsalg")


# --- Polling -----------------------------------------------------------------
# Hvor ofte vi sjekker siden, i sekunder. Default 60s.
INTERVAL = int(os.environ.get("INTERVAL", "60"))

# Nedre grense for intervallet. Dette er en liten arrangør-side — vi skal IKKE
# hamre den med forespørsler. Ikke fjern denne grensen.
MIN_INTERVAL = 30

# Timeout på alle HTTP-forespørsler (sekunder). Hindrer at appen henger.
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "15"))

# Vanlig User-Agent — uten denne kan forespørselen bli avvist av serveren.
USER_AGENT = os.environ.get(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36",
)


# --- Varsling (ntfy.sh) ------------------------------------------------------
# VIKTIG: Bytt dette til noe unikt og vanskelig å gjette FØR du starter!
# Alle som kjenner topic-navnet kan abonnere og se varslene dine. Bruk f.eks.
# noen tilfeldige ord + tall: "ullevaal-billett-7Kq39xZ".
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "BYTT-MEG-til-noe-unikt-og-hemmelig")

# Base-URL for ntfy. Endre kun hvis du kjører din egen ntfy-server.
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")


# --- Lokale PC-varsler -------------------------------------------------------
# Varsle rett på denne maskinen når salget åpner — i tillegg til ntfy. Nyttig
# hvis du ikke har ntfy-appen. "1"/"true" = på, "0"/"false" = av.
def _flag(name, default):
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


# Windows toast-popup (krever pakken 'winotify' — se requirements.txt).
NOTIFY_TOAST = _flag("NOTIFY_TOAST", "true")

# Lyd-alarm (innebygd winsound — ingen ekstra pakke).
NOTIFY_SOUND = _flag("NOTIFY_SOUND", "true")

# Send også push til ntfy.sh? Av som standard — du bruker PC-varsel (toast + lyd).
# Sett "true" igjen hvis du senere vil ha mobilvarsel via ntfy-appen.
NOTIFY_NTFY = _flag("NOTIFY_NTFY", "false")


# --- Logging -----------------------------------------------------------------
LOG_FILE = os.environ.get("LOG_FILE", "monitor.log")
