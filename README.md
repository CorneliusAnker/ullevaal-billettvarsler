# Billettvarsler — Fotballfesten Ullevaal 2026

Liten Python-app som overvåker billettsiden og sender et **push-varsel til mobilen**
i det øyeblikket salget åpner.

Appen henter HTML fra siden hvert minutt og overvåker **statussetningen** på siden
(«Billettsalg for … er midlertidig stengt»). Den varsler ved **enhver endring** i
denne setningen — enten den forsvinner, blir til «utsolgt», «kjøp nå» e.l. Slik går
du ikke glipp av en åpning selv om arrangøren formulerer det annerledes enn ventet.

### Modus (`ALERT_MODE` i config.py)

| Modus | Når varsler den | Standard |
|-------|-----------------|----------|
| `endring` | ved **enhver endring** i statussetningen | ✅ |
| `aapning` | **kun** når «midlertidig stengt» forsvinner (STENGT → ÅPENT) | |

`endring` er bredere og tryggere mot uventede formuleringer. Men den overvåker kun
*statussetningen* — ikke hele siden — så du slipper falske varsler fra menyer,
bannere og annet som endrer seg uten betydning.

## Hva du trenger

- Python 3.8+
- **Enten** PC-varsel (toast-popup + lyd) — funker rett ut av boksen, ingen app
- **eller** ntfy for mobilvarsel (gratis app, App Store / Google Play)

Du kan bruke begge samtidig. PC-varsel er på som standard.

## Varslingskanaler

Appen kan varsle på tre måter når salget åpner — skru av/på i [`config.py`](config.py):

| Kanal | Config-flagg | Krever | Standard |
|-------|--------------|--------|----------|
| Windows toast-popup | `NOTIFY_TOAST` | pakken `winotify` | på |
| Lyd-alarm | `NOTIFY_SOUND` | innebygd (winsound) | på |
| ntfy push (mobil/nettleser) | `NOTIFY_NTFY` | ntfy-topic | på |

Vil du **kun** ha PC-varsel uten ntfy: sett `NOTIFY_NTFY = False` (eller miljøvariabel
`NOTIFY_NTFY=false`). Da slipper du å sette opp topic i det hele tatt.

## Oppsett

1. **Installer avhengigheter:**

   ```bash
   pip install -r requirements.txt
   ```

   (Anbefalt: bruk et virtuelt miljø først — `python -m venv venv` og aktiver det.)

2. **Sett ditt eget `NTFY_TOPIC`.**
   Åpne `config.py` og bytt ut placeholderen:

   ```python
   NTFY_TOPIC = "ullevaal-billett-7Kq39xZ"   # bruk noe unikt og vanskelig å gjette
   ```

   > ⚠️ **Viktig:** Alle som kjenner topic-navnet kan abonnere og se varslene dine.
   > Velg noe tilfeldig og hemmelig — ikke bare `ullevaal`.

   Alternativt kan du sette det som miljøvariabel uten å endre koden:

   ```bash
   # PowerShell
   $env:NTFY_TOPIC = "ullevaal-billett-7Kq39xZ"
   ```

3. **Installer ntfy på mobilen og abonner på samme topic.**
   Åpne ntfy-appen → *Subscribe to topic* → skriv inn **nøyaktig samme** topic-navn
   som i `config.py`.

## Test at varslingen funker (gjør dette FØR du stoler på overvåkingen)

```bash
python monitor.py --test-notify
```

Du skal få et varsel på mobilen i løpet av sekunder. Kommer det ikke, se feilsøking nedenfor.

## Kjøring

```bash
python monitor.py            # evig overvåking — kjør og la stå
python monitor.py --once     # sjekk status én gang og avslutt (feilsøking / cron)
```

Avslutt med **Ctrl+C** — appen stenger pent.

## Konfigurasjon

All konfig ligger øverst i [`config.py`](config.py):

| Variabel         | Default | Forklaring |
|------------------|---------|------------|
| `URL`            | billettsiden | Siden som overvåkes (uten sporings-parametere) |
| `INTERVAL`       | `60`    | Sekunder mellom hver sjekk |
| `MIN_INTERVAL`   | `30`    | Nedre grense — appen tvinger minst 30s. **Ikke fjern.** Dette er en liten arrangør-side og skal ikke hamres. |
| `NTFY_TOPIC`     | placeholder | Ditt hemmelige ntfy-topic |
| `MATCH_STRING`   | `midlertidig stengt` | Teksten som betyr "stengt" |

Alle verdiene kan også overstyres med miljøvariabler.

## Logging

Alt logges både til konsoll og til `monitor.log` med tidsstempel. Loggfila er
git-ignorert.

## Driftsnote

PC-en må være **våken** så lenge scriptet kjører — sover maskinen, stopper
overvåkingen. Siden målsiden er statisk, kan en skyhostet variant settes opp senere
(f.eks. en `cron`-jobb som kjører `python monitor.py --once` hvert minutt på en liten
server). Da slipper du å holde PC-en på.

## Feilsøking

**Ingen varsler kommer:**

1. Kjør `python monitor.py --test-notify` — får du test-varselet?
   - **Nei:** Sjekk at topic-navnet i appen er *identisk* med `NTFY_TOPIC` i config
     (skiller stor/liten bokstav). Sjekk at mobilen har nett og at ntfy-appen får
     lov til å vise varsler.
   - **Ja:** Da funker push. Appen pusher kun ved STENGT → ÅPENT-overgang, så hvis
     salget allerede er åpent (eller allerede stengt uten å åpne), kommer det ikke
     noe varsel før neste faktiske åpning.

2. Sjekk `monitor.log` for feilmeldinger (nettverksfeil logges, men krasjer ikke appen).

3. Test at statusoppdagingen virker: `python monitor.py --once` skriver ut om siden
   tolkes som ÅPENT eller STENGT akkurat nå.

**"NTFY_TOPIC er fortsatt placeholder"-advarsel:**
Du har ikke byttet ut topic-navnet. Se oppsett-steg 2.
