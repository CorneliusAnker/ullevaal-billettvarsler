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

# Hindre at PC-en sovner mens overvåkingen kjører (kun Windows). Skjermen kan
# fortsatt slå seg av — scriptet kjører videre uansett. Nullstilles ved avslutning.
PREVENT_SLEEP = _flag("PREVENT_SLEEP", "true")

# Send også push til ntfy.sh? Av som standard — du bruker PC-varsel (toast + lyd).
# Sett "true" igjen hvis du senere vil ha mobilvarsel via ntfy-appen.
NOTIFY_NTFY = _flag("NOTIFY_NTFY", "false")


# --- Logging -----------------------------------------------------------------
LOG_FILE = os.environ.get("LOG_FILE", "monitor.log")


# --- Frogner-varsler (fanpark_monitor.py) -------------------------------------
# Egen, fokusert overvåker for Frogner (Norge vs England, kvartfinale 11. juli
# 2026). Målene under er lette å endre — legg til/fjern rader etter behov.
#
# Måltyper:
#   "direct"    – kandidat-URL som gir 404 nå og skal flippe til 200 når salget
#                 åpner. Regnes som live først når kroppen også ser ut som en
#                 ekte booking-side (se FANPARK_LIVE_MARKERS).
#   "catchall"  – side som i dag IKKE lenker til fanparks-booking; varsler når
#                 en href mot fanparks.fanparks.com/booking/ dukker opp.
#                 "exclude": href-er som inneholder disse ordene ignoreres
#                 (andre fanparks som alt er live og kan dukke opp i meny/footer).
#   "reference" – kjent live side. Brukes KUN av --test til å verifisere at
#                 200-stien og markørene fungerer. Varsler aldri.
#   "textwatch" – vaktbikkje: varsler ved ENHVER endring i synlig sidetekst
#                 (f.eks. at "Billetter kommer snart" byttes ut) — også før en
#                 booking-lenke finnes. Kan pipe på uviktige endringer.
FANPARK_TARGETS = [
    {
        "name": "frogner-direkte",
        "type": "direct",
        "url": "https://fanparks.fanparks.com/booking/fotballfesten-frogner-2026",
    },
    {
        "name": "frognerstadion-direkte",
        "type": "direct",
        "url": "https://fanparks.fanparks.com/booking/fotballfesten-frognerstadion-2026",
    },
    {
        "name": "fotballfesten-catchall",
        "type": "catchall",
        "url": "https://www.fotballfesten.no/frognerstadion",
        "exclude": ["kongensgate", "ullevaal"],
    },
    {
        "name": "frognerstadion-tekstvakt",
        "type": "textwatch",
        "url": "https://www.fotballfesten.no/frognerstadion",
    },
    {
        # Returbillett-vakt: booking-siden er live, men viser "ingen kamper
        # tilgjengelig" etter at alt ble utsolgt paa sekunder 9. juli. Enhver
        # tekstendring her (returer, restsalg, nytt slipp) skal varsle.
        "name": "frogner-booking-tekstvakt",
        "type": "textwatch",
        "url": "https://fanparks.fanparks.com/booking/fotballfesten-frogner-2026",
    },
    {
        "name": "kongensgate-referanse",
        "type": "reference",
        "url": "https://fanparks.fanparks.com/booking/fotballfesten-kongensgate-2026",
    },
]

# En "direct"-side regnes som ekte booking-side når minst ett av disse ordene
# finnes i sideteksten (case-insensitivt). Verifisert mot Kongens gate-siden.
FANPARK_LIVE_MARKERS = ["kjøp", "inngangstid"]

# Nøkkelord som identifiserer selve kampen på booking-siden (bonus-info i varselet).
FANPARK_MATCH_KEYWORDS = ["norge", "england"]

# Sekunder mellom hver sjekk-runde, pluss/minus tilfeldig jitter. MIN_INTERVAL
# over gjelder også her — ikke hamre serveren.
FANPARK_INTERVAL = int(os.environ.get("FANPARK_INTERVAL", "150"))
FANPARK_JITTER = int(os.environ.get("FANPARK_JITTER", "30"))

# Antall forsøk per henting ved nettverksfeil (med økende ventetid mellom).
FANPARK_RETRIES = int(os.environ.get("FANPARK_RETRIES", "3"))

# Statusfil (JSON) med siste kjente status per mål — gjør scriptet idempotent
# så det bare varsler på selve overgangen ikke-live -> live.
FANPARK_STATE_FILE = os.environ.get("FANPARK_STATE_FILE", "state/fanpark_state.json")

FANPARK_LOG_FILE = os.environ.get("FANPARK_LOG_FILE", "fanpark_monitor.log")


# --- Lokale, private overstyringer -------------------------------------------
# Hvis det finnes en config_local.py ved siden av denne, importeres den til slutt
# og overstyrer verdiene over. Bruk den til hemmeligheter som IKKE skal i git
# (f.eks. ditt ntfy-topic) — config_local.py er git-ignorert.
try:
    from config_local import *  # noqa: F401,F403
except ImportError:
    pass
