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

Scriptet ber automatisk Windows om å **holde systemet våkent** så lenge det kjører
(`PREVENT_SLEEP` i config, på som standard) — så maskinen sovner ikke fra deg midt i
overvåkingen. Skjermen kan fortsatt slå seg av; scriptet kjører videre uansett. Vinduet
må likevel stå åpent.

Vil du slippe å ha PC-en på i det hele tatt? Se neste seksjon — kjør den i GitHubs sky.

## Kjøre i skyen (GitHub Actions) — uten at PC-en din står på

> **Merk (juli 2026):** Ullevål-billettene er skaffet, så workflowen kjører nå **kun
> Frogner-varsleren** (se egen seksjon nedenfor) pluss et daglig heartbeat-ping.
> Ullevål-overvåkeren (`monitor.py`) kan fortsatt kjøres lokalt eller legges tilbake
> i workflowen ved behov — oppskriften under gjelder fortsatt.

Repoet inneholder en ferdig workflow ([`.github/workflows/monitor.yml`](.github/workflows/monitor.yml))
som kjører sjekkene **hvert 5. minutt** gratis i GitHubs sky, husker forrige status i
`state/`-filer (committes automatisk) og varsler via **ntfy** ved endring.

> ⚠️ I skyen finnes ingen skjerm eller høyttaler — så toast og lyd funker *ikke* der.
> Du **må** bruke ntfy (mobil-app eller bare `https://ntfy.sh/DITT-TOPIC` i en
> nettleserfane).

### Oppsett, steg for steg

1. **Lag et GitHub-repo og push koden.** Enten via [github.com/new](https://github.com/new),
   eller med GitHub CLI. Deretter, i prosjektmappa:

   ```bash
   git remote add origin https://github.com/DITT-BRUKERNAVN/REPO-NAVN.git
   git push -u origin master
   ```

   > 💡 Gjør gjerne repoet **public** — da er GitHub Actions helt gratis og uten
   > tidsgrense. (Private repo har en månedlig gratiskvote som et 5-min-intervall
   > spiser fort.) Det ligger ingenting hemmelig i koden; topic-navnet lagres som
   > en Secret, ikke i koden.

2. **Velg et hemmelig ntfy-topic** (f.eks. `ullevaal-billett-7Kq39xZ`) og legg det inn
   som en **Secret**: repoet → *Settings* → *Secrets and variables* → *Actions* →
   *New repository secret*. Navn: `NTFY_TOPIC`, verdi: ditt topic.

3. **Gi workflowen skrive-tilgang** (så den kan lagre status): *Settings* → *Actions*
   → *General* → *Workflow permissions* → velg **Read and write permissions** → *Save*.

4. **Abonner på samme topic** — enten i ntfy-appen, eller åpne `https://ntfy.sh/DITT-TOPIC`
   i en nettleserfane og la den stå.

5. **Ferdig.** Workflowen starter av seg selv. Vil du teste den med en gang: repoet →
   *Actions* → *Billettovervaaking* → *Run workflow*. Første kjøring etablerer bare
   utgangspunktet (ingen varsel); deretter varsler den ved endring.

### Verdt å vite

- **Intervall ~5 min:** GitHub tillater ikke tettere planlagte jobber, og kan av og til
  forsinke dem noen minutter under høy last. For et billettsalg som varer i timer/dager
  er det helt fint, men det er litt tregere enn PC-versjonen (60 sek).
- **Belte og bukseseler:** du kan kjøre PC-versjonen *og* skyversjonen samtidig — da har
  du PC-varsel (rask) og ntfy (uansett om PC-en er på).
- **Husk å skru av etterpå:** når du har fått billetter, deaktiver workflowen
  (*Actions* → *Billettovervaaking* → *⋯* → *Disable workflow*) så den ikke kjører i evig tid.

### En enklere cron (egen server) som alternativ

Har du en alltid-på server/VPS, kan du droppe GitHub og bare legge inn i `crontab`:

```cron
*/5 * * * * cd /sti/til/prosjekt && NTFY_TOPIC=ditt-topic NOTIFY_NTFY=true python3 monitor.py --ci-check
```

## Frogner-varsler (Norge vs England) — `fanpark_monitor.py`

Egen, fokusert overvåker som varsler **i det øyeblikket Frogner-billettene**
(Norge vs England, kvartfinale lør 11. juli 2026) legges ut på fanparks.fanparks.com.
Kongens gate for samme kamp er allerede utsolgt.

Den overvåker tre mål samtidig (lista `FANPARK_TARGETS` øverst i Frogner-seksjonen
av [`config.py`](config.py) — lett å endre):

| Mål | Hva den ser etter |
|-----|-------------------|
| `.../booking/fotballfesten-frogner-2026` | 404 → 200 **og** ekte booking-innhold («Kjøp»/«Inngangstid») |
| `.../booking/fotballfesten-frognerstadion-2026` | samme |
| `fotballfesten.no/frognerstadion` (catch-all) | en ny lenke mot `fanparks.fanparks.com/booking/` — fanger opp uansett slug |

Varselet («**Frogner LIVE: Norge vs England**») sendes med høy prioritet til samme
ntfy-topic som resten av prosjektet, pluss toast + lyd på PC-en. Hele varselet er
klikkbart og åpner booking-URL-en direkte. Er booking-siden oppe, følger også
eventuelle `/events/KODE`-lenker (enkeltkamper) og utsolgt-status med i meldingen.

Den varsler **kun på selve overgangen** ikke-live → live (én gang per mål) — siste
kjente status ligger i `state/fanpark_state.json`, så den spammer ikke.

### Starte og stoppe

```bash
python fanpark_monitor.py --test    # GJØR DETTE FØRST: test-varsel + verifiser
                                    # deteksjonen mot Kongens gate (som er live)
python fanpark_monitor.py           # start overvåkingen (2,5 min ± jitter) — la stå
python fanpark_monitor.py --once    # én sjekk-runde og avslutt (cron)
```

Eller dobbeltklikk **`start_fanpark.bat`**. Stopp med **Ctrl+C** (eller lukk vinduet).
Logger til konsoll + `fanpark_monitor.log`.

### Skydrift

Frogner-sjekken kjører også automatisk i den eksisterende GitHub Actions-workflowen
([`monitor.yml`](.github/workflows/monitor.yml)) **hvert 5. minutt**, med egen statusfil
(`state/fanpark_state_ci.json`) som committes automatisk. Ingen ekstra oppsett — den
bruker samme `NTFY_TOPIC`-secret. PC-versjonen er raskere (2,5 min); kjør gjerne begge.

**Heartbeat (dødmannsknapp):** workflowen sender ett lavprioritets ntfy-ping per dag
(«Overvåkingen lever»). GitHub-cron kan stoppe stille (f.eks. hvis workflowen deaktiveres,
eller GitHub slutter å fire schedulen) — **uteblir livstegnet en hel dag, sjekk
Actions-fanen.** Stillhet betyr altså *ikke* at alt er OK; det daglige pinget gjør.

**Når du har fått billetter:** stopp PC-scriptet og deaktiver workflowen
(*Actions* → *Billettovervaaking* → *⋯* → *Disable workflow*). Da stopper også
heartbeat-pinget — det er forventet.

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
