#!/usr/bin/env python3
"""Generate collaborator archive pages for the Aster da Master site.

Output:
  circle/<slug>.html   - one page per title-credited collaborator (21)
  circle/index.html     - the circle index
  data/v1/circle.json    - machine-readable collaborator index
                          (registered in data/v1/index.json)

Per collaborator: shared tracks (titles/dates/plays, linked to release
pages), total shared plays, years active, era breakdown. Credits are
parsed from w//ft./feat. fragments in titles - as credited, verbatim,
nothing inferred. Producers are excluded (same rule as network.html).

Titles only - no lyrics anywhere. Idempotent: regenerates cleanly.
Re-run after any discography change. Also bumps data version to 0.13.0
and mirrors data/artist.json to data/v1/artist.json.

Wave 12 adds verified research notes to capoxxo/pvscale pages and a
"scene figures" section (Fish Narc) - public sources only, no lyrics,
no invented biography.
"""
import json
import re
import shutil
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import nav_data  # noqa: E402  (canonical nav data — scripts/nav_data.py)
from build_releases import slugify  # noqa: E402  (single source of truth)
from build_years import parse_collabs, era_for_year  # noqa: E402  (same parser as network.js)
from build_producer_deepdives import (  # noqa: E402  (wave 27 cross-links)
    parse_producers, producer_slug)

DATA = json.loads((ROOT / "data" / "artist.json").read_text())
OUT = ROOT / "circle"
API = ROOT / "data" / "v1"
NEW_VERSION = "0.19.0"  # wave 35: verified-data expansion - collaborator deep-enrichment (rounds 15-16)

# wave 27: producer slugs with as-credited productions (populated in main);
# circle members who also produce get a "Producer deep dive" cross-link.
PRODUCER_SLUGS = set()

NAV = nav_data.nav_chunk("../", "circle")

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Aster da Master</title>
  <meta name="description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{title} — Aster da Master">
  <meta property="og:description" content="{desc}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:image" content="../assets/og-card.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} — Aster da Master">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="../assets/og-card.png">
  <link rel="preload" href="../assets/fonts/anton-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="../assets/css/fonts.css">

  <link rel="stylesheet" href="../assets/css/tokens.css">
  <link rel="stylesheet" href="../assets/css/base.css">
  <link rel="stylesheet" href="../assets/css/layout.css">
  <link rel="stylesheet" href="../assets/css/components.css">
  <link rel="stylesheet" href="../assets/css/motifs.css">
  <link rel="stylesheet" href="../assets/css/layer2.css">
</head>
<body class="layer2">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="container header-bar">
      <a class="brand" href="../" aria-label="Aster da Master home">
        <span class="brand-mark" aria-hidden="true">A&#10022;</span>
        <span>ASTER DA MASTER</span>
      </a>
      """ + NAV + """
    </div>
  </header>
  <main id="main">
    <div class="container">
"""

FOOT = """    </div>
  </main>
  <footer class="site-footer">
    <div class="container footer-grid">
      <p>&copy; 2026 ASTER DA MASTER &mdash; ALL SIGNALS RESERVED</p>
      """ + nav_data.footer_block("../", "circle") + """
    </div>
  </footer>
  <script src="../assets/js/identity.js"></script>
</body>
</html>
"""

def fmt(n):
    return f"{n:,}"

# --- Wave 12 (2026-10-11) research enrichment ---------------------------------
# Verified public findings ONLY. Every fact below is backed by a public source;
# nothing is invented (no real names, ages beyond what's public, personal
# history), and no lyrics appear anywhere. Keyed by collaborator key
# (lowercased display name as stored in `collabs`).
ENRICH = {
    "capoxxo": {
        "facts": [
            "Named by Pitchfork's Kieran Press-Reynolds in "
            '"A Deeply Incomplete Canon of Hyperpop-Digicore" - '
            "an independent digicore/hyperpop internet artist.",
            "Released the collab tape 'Persona' with mayh3mp on "
            "Cult Love Sound Tapes (2022): 5 tracks, limited cassette run of 100.",
            "The two Aster Da Master tracks carrying a capoxxo title credit are "
            "'candy' (2019-10-04, prod. razorwrist) and 'getting colder' "
            "(2019-12-22, prod. pvscale x asa41).",
            # Wave 35 (2026-10-12): rounds 15-16 research integration.
            # Every claim from the 2026-10-12 scene research passes;
            # single-source flagged, never confirmed press.
            "Streaming-metrics layer (musicmetricsvault, data ~2 months "
            "old, single-source): 53,275 monthly listeners, 29,890 "
            "followers, 36.6M total streams, 119 releases. Most-streamed: "
            "'Perfect' (Apr 18, 2020, 6.2M streams), 'Ouueeoueou' "
            "(Mar 19, 2019, 2.6M), 'wait 4 it' (Aug 7, 2020, 2.3M), "
            "'Monster' (Mar 19, 2020, 2.2M), 'IDLY' (Dec 29, 2023, 2.1M). "
            "Related artists: dreamcache, 5v, Pitfall, Senses, mayh3mp, "
            "Hinoni, RudeClub, bliiiss, Boofbby, Peake, mental, bodyGaard, "
            "Kid Trash, tropes, dxsh, emorave archive, Dion, kid sora, "
            "Crystal Statues.",
            "'dont sleep (feat. bliiiss)' - released by Hinoni, 22 Oct "
            "2023; explicit feature credit on the primary-artist Qobuz "
            "page (single-source, direct open).",
            "'Perfect' trio: last.fm's track page lists 'Perfect Capoxxo, "
            "Oaf1 & Dreamcache' (index snapshot, crawl ~10 days) and "
            "musicmetricsvault prints 'Perfect (feat. Oaf1 & Dreamcache)' "
            "- two single-sources, two rounds, never presented as "
            "confirmed press.",
            "First verifiable live appearances: Oct 28 Seattle @ Arch "
            "Rivals Studios (116 S Washington St), doors 7:30 PM, $25.63; "
            "Oct 29 Portland @ 211 SE Madison St, doors 7 PM, $28.52 - a "
            "Korpsebunny support bill with mayh3mp and Scarly (Portland "
            "also Eunhae + DJ sets from B3xtac33, DJ Shortstop, Sora Boyd) "
            "(Eventbrite listings, direct open, single-source each). "
            "Songkick still reads 'Off tour' - headliner data; mainstream "
            "trackers don't list the support slots.",
            "Qobuz catalog: 46 albums; newest single 'nostalgia' "
            "(30 Jun 2026, Hinoni) (direct open). 'Sorry' - releasing "
            "entity printed as 'Teo Laza & Capoxxo' (9 May 2023, "
            "single-source); association-level, never published as a "
            "confirmed collab.",
            "last.fm index snapshots (direct pages blocked 11 rounds "
            "running): top tracks 'perfect' (394 listeners), 'ouueeoueou' "
            "(148), 'it was beautiful' (133), 'sequence' (94), 'monster' "
            "(90) - crawl ~5 days; similar artists oaf1 and 'Capoxxo, "
            "mayh3mp' (368 listeners); 'Wett Brain, Capoxxo' page tracks "
            "'Fxcked Up Bad' (59), 'IDLY' (55) (single-source, index "
            "snapshots).",
            "mayh3mp - recent activity: '# madeira funchal' (4 Sep 2026) "
            "and '# i kno u' on Last.fm's recently-popular view "
            "(single-source).",
            "'Lullaby' distributor evidence: a scraped nhaccuatui page "
            "lists 'Lullaby (Single), phonewifey, mayh3mp, Capoxxo' and "
            "states 'Uploaded by The Orchard' (single-source); the DMY "
            "smart link dmy.ffm.to/lullaby (single-source); Trackify "
            "streaming metadata (159.9 BPM, key B, single-source). No "
            "exact release date on record.",
            "'Torn Ft Capoxxo & Lil Yu Prod Truss' appears on mayh3mp's "
            "'mylifeasahorse' cassette (Cult Love Sound Tapes, ~2022-era "
            "catalog, single-source) - a capoxxo x lil yu x mayh3mp scene "
            "link new to the graph.",
        ],
        "sources": [
            ("The Pitchfork digicore canon (via Wikipedia: Digicore)",
             "https://en.wikipedia.org/wiki/Digicore"),
            ("'Persona' - Cult Love Sound Tapes (Bandcamp)",
             "https://cultlovesoundtapes.bandcamp.com/album/persona"),
            # Wave 35 (2026-10-12): rounds 15-16 research sources.
            ("capoxxo streaming metrics + related artists - musicmetricsvault",
             "https://www.musicmetricsvault.com/artists/capoxxo/"
             "4lDzMjsz7xLw4CFmfWJmWJ"),
            ("'mylifeasahorse' - Cult Love Sound Tapes (Bandcamp)",
             "https://cultlovesoundtapes.bandcamp.com/album/mylifeasahorse"),
            ("mayh3mp - Last.fm recently popular",
             "https://www.last.fm/music/mayh3mp/+albums"),
            ("'Lullaby' - DMY smart link", "https://dmy.ffm.to/lullaby"),
        ],
    },
    "pvscale": {
        "facts": [
            "Produced 'fly like me' (2019-12-22) and co-produced "
            "'getting colder' with asa41 (2019-12-22), per title credits.",
            "Also produces for capoxxo ('angels watch me'; "
            "'Summer Days [prod. pvscale]' for spiff x capoxxo), lil koi, "
            "lil yu ('i miss you (feat. pvscale)'), and "
            "kevinhilfiger/kidtrashpop ('buy It !') - per public tracklistings.",
            # Wave 35 (2026-10-12): independent catalog corroboration.
            "An undated mp3 index for pvscale independently catalogs "
            "'ASTER DA MASTER \u2600\ufe0f - getting colder w/ capoxxo "
            "(prod. pvscale x asa41)' - corroborating the archive's own "
            "credit; the index gives no date, so it documents the "
            "collaboration, not its timeline (single-source, uncertain "
            "date).",
        ],
        "sources": [
            ("pvscale catalog mirror (mp3.pm)",
             "https://s-pvscale.mp3.pm/"),
            ("Aster Da Master - title credits (sonichits)",
             "https://sonichits.com/artist/Aster_Da_Master"),
        ],
    },
    # Wave 32 (2026-10-11) research enrichment: the D1 line, GothBoiClique
    # orbit, and two thin-but-verified producer credits. Same evidence
    # standard as wave 12: public sources only, no lyrics, no invented bio.
    "lil wintr": {
        "facts": [
            "Raps as Lil Wintr under his birth name Christian Baello; "
            "a rapper from Lake Elsinore, California (The FADER, 2019-06-04).",
            "Produces under the alias Ginseng — the same alias carrying "
            "the archive's 'master key' production credit (The FADER).",
            "Guitarist and percussionist in the band dream, ivory, "
            "alongside his brother Louie Baello (Peso Talk) (The FADER).",
            "Member of the D1 SoundCloud supergroup with Despair, Shiro, "
            "Marcelo, and Hella Sketchy (The FADER; NTS).",
            "Both archive tracks carry Marcelo alongside: 'Master Key "
            "(feat. Lil Wintr & Marcelo)' and 'master key ft. Lil Wintr x "
            "Marcelo (prod. ginseng)' (2019-12-06) — the second produced "
            "under his own producer alias (archive cross-reference).",
        ],
        "sources": [
            ("The many faces of Ginseng - The FADER, 2019-06-04",
             "https://www.thefader.com/2019/06/04/"
             "ginseng-lil-wintr-dream-ivory-interview"),
            ("D1 - NTS artist page",
             "https://www.nts.live/artists/32421-d1"),
        ],
    },
    "marcelo": {
        "facts": [
            "Producer, singer, and rapper; a member of Hollow Squad, a "
            "sub-collective of Seshollowaterboyz (Underground Underdogs, "
            "2018-08-27).",
            "Debut album 'Outta Luck' (Underground Underdogs, 2018).",
            "Production credits beyond his own work: Lil Wintr, cholopunx, "
            "and an Xavier Wulf x madeintyo track (Underground Underdogs).",
            "Member of the D1 SoundCloud supergroup (formed summer 2017) "
            "with Lil Wintr, Despair, Shiro, and Hella Sketchy (NTS).",
            "Shares both archive title credits — and the D1 line — with "
            "Lil Wintr (archive cross-reference).",
        ],
        "sources": [
            ("Marcelo is 'Outta Luck' but Rich in Talent - "
             "Underground Underdogs, 2018-08-27",
             "https://undergroundunderdogs.com/2018/08/27/"
             "marcelo-is-outta-luck-but-rich-in-talent/"),
            ("D1 - NTS artist page",
             "https://www.nts.live/artists/32421-d1"),
        ],
    },
    "yung cortex": {
        "facts": [
            "Friend and collaborator of Lil Peep ('Gus'); co-produced "
            "Lil Peep x Lil Tracy's 'Witchblades' with BigHead — the credit "
            "is carried on the GothBoiClique SoundCloud (Underground "
            "Underdogs interview, 2018-02-23).",
            "Makes his own vocal music ('fast car (faster)') alongside "
            "albums of instrumentals (same interview).",
            "Both produces and features on his archive track: 'All Alone "
            "ft. Yung Cortex (prod. Yung Cortex)' (2019-12-30) "
            "(archive cross-reference).",
            "The 'Witchblades' credit sits in the GothBoiClique orbit — "
            "the same collective scene figure Fish Narc belongs to "
            "(archive cross-reference).",
        ],
        "sources": [
            ("A Conversation with Yung Cortex - Underground Underdogs, "
             "2018-02-23",
             "https://undergroundunderdogs.com/2018/02/23/yung-cortex/"),
        ],
    },
    "griimxo": {
        "facts": [
            "Shazam's artist page catalogs GriimXO under Hip-Hop/Rap and "
            "lists related artists MotionPaxk, BabyPlugg, and sal raxkz "
            "(single-source).",
            "Videography credit: 'SHOT BY GRiiMXO' on the 'VALENTINE' "
            "video with WhoisZoha? (YouTube description, single-source).",
            "The record is thin: no interview, bio, or press coverage "
            "found as of 2026-10-11 — the catalog entries above are the "
            "whole public record (flagged, not filled).",
        ],
        "sources": [
            ("GrimXo! - Shazam artist page",
             "https://www.shazam.com/artist/grimxo/1754777698"),
            ("VALENTINE - GriimXO & WhoisZoha? - YouTube",
             "https://www.youtube.com/watch?v=sfOuoaHwDHc"),
        ],
    },
    "keyblayde808": {
        "facts": [
            "Producer with an active beat storefront on Traktrain "
            "(single-source).",
            "Co-produced capoxxo & dxsh's 'CAPODXSH' with 4am "
            "(archived video description, single-source).",
            "Co-produced Nettspend's 'Swish' with 4evr (December 2023) "
            "(video description, single-source).",
            "Both produces and features on his archive track: 'White Noise "
            "ft. Keyblayde808 (prod. Keyblayde808)' (2019-12-30) "
            "(archive cross-reference).",
            "Thin record beyond these credits: no interview or press "
            "coverage found as of 2026-10-11 (flagged, not filled).",
        ],
        "sources": [
            ("Beats by Keyblayde808 - Traktrain",
             "https://traktrain.com/keyblade808"),
            ("capoxxo & dxsh - CAPODXSH (music video + extended) - YouTube",
             "https://www.youtube.com/watch?v=U5qQMf8NwcM"),
        ],
    },
}

# Producers and scene figures are excluded from the 21-collaborator circle by
# the title-credit rule ("producers excluded"), but wave 12 keeps the most
# documented one visible with the same evidence standard, clearly labeled.
SCENE_FIGURES = {
    "fish-narc": {
        "name": "Fish Narc",
        "kind": "scene figure \u2014 producer credit",
        "standing": (
            "Fish Narc enters this archive through producer credits on two "
            "SoundCloud tracks, not through title features. He is not one of "
            "the 21 title-credited collaborators and stands outside the "
            "circle count. The circle's title-credit rule is unchanged."
        ),
        "tracks": [
            {"title": "Pavement (prod. Fish Narc)", "date": "2019-12-30",
             "plays": 733, "type": "SoundCloud-only",
             "page": "pavement-prod-fish-narc.html"},
            {"title": "Soul Shaking (prod. Fish Narc)", "date": "2018-01-03",
             "plays": 12944, "type": "SoundCloud-only",
             "page": "soul-shaking-prod-fish-narc.html"},
        ],
        "facts": [
            "Born 1992; Seattle/Olympia, Washington.",
            "Member of Thraxxhouse and GothBoiClique.",
            "Produced Lil Peep's 'Goth Angel Sinner' LP.",
            "Worked with Wicca Phase Springs Eternal, Lil Tracy, Horse Head, "
            "and Cold Hart; production noted for live guitar instead of samples.",
            "Solo LPs: 'WiLDFiRE' (2020), 'Camouflage' (2022), "
            "'fruiting body' [KLP295] (2023), 'frog song' (2025, K Records).",
            "Fifth solo LP 'Uncle' announced (Stereogum, August 2026): "
            "11 tracks on K Records [KLP313], scheduled release 2026-10-16; "
            "produced by Asheville's Alex Farrar "
            "(Wednesday, MJ Lenderman, Fiddlehead).",
            "Tracklist: 'Untitled', 'Much Less Me', 'Emma', 'Student Driver', "
            "'One Hand On The Sword', 'In The Woods', 'Big Dumb World', "
            "'Not To Guess', \"Wouldn't You Know\", 'Umtanum', 'Yakima Canyon'.",
            "Lead singles 'Much Less Me' (Super 8 video by Jolie M-A) and "
            "'Big Dumb World' (video by James Hyson); fall tour 2026-10-29 "
            "Los Angeles (Gold Diggers), 2026-11-06 Kingston NY (Tubby's), "
            "2026-11-07 Ridgewood NY (Stone Circle Theatre).",
            "Status as of research pass 2026-10-11: announced / pre-release "
            "— release listings this week still carry 2026-10-16 as upcoming; "
            "the archive records 'announced' until a release is confirmed.",
            # wave 30 merge: new verified facts (2026-10-11 pass)
            "Real name: Ben Funkhouser (verified — named in the Stereogum "
            "announcement interview and the Release Wave artist profile).",
            "On the title 'Uncle': the artist's own framing (Stereogum "
            "interview) — saying 'uncle', giving up, as a tongue-in-cheek "
            "nod; the record reflects on the last ten years, expectations, "
            "and aging, made from a mid-30s vantage point as a best-shot "
            "project rather than a youth-lane chase.",
            "Vinyl LP pre-order open through K Records (Faygoluvers).",
            "Same release-day shelf 2026-10-16 (AltPress October calendar): "
            "@ – Autosmile (4AD); The Avalanches – No Bad Memories; "
            "Dummy – do you love the color of the sky?; "
            "Fontaines D.C. – Dopamine Chamber; N8NOFACE – "
            "Tomorrow's World; They Are Gutting a Body of Water – "
            "KOOL FAITH/LOOSIES II; Taking Back Sunday – Louder Now "
            "(20th Anniversary Edition).",
            # wave 32 (2026-10-11): same-evening re-verification pass
            "'Big Dumb World' video: posted by its maker James Logan Hyson "
            "on Vimeo — corroborating Stereogum's 'James Hyson's video' "
            "credit (single-source).",
            "K Records' label copy (via upcomingvinyl): recently relocated "
            "to Los Angeles; tours the US and Europe this autumn with a "
            "full band (single-source).",
            "Release Wave artist profile's comparison line: fans of Gin "
            "Blossoms, The Replacements, Yuck, and Superdrag "
            "(single-source).",
            "The August 18, 2026 'new songs out today' roundup (Our Culture "
            "Mag) covers 'Much Less Me' as the lead single with Alex "
            "Farrar's production (single-source — corroborates the "
            "Stereogum announcement).",
            # Wave 35 (2026-10-12): rounds 15-16 research integration.
            "Listening party: Thu Oct 15, 7 PM, FREE, RSVP — re-verified "
            "live on the venue calendar (roadhouse.permanentrecordsla.com, "
            "verified). No third single, no advance reviews, no 'Uncle' "
            "interviews as of 2026-10-12 (normal 4 days out).",
            "Europe leg upgraded one notch: upcomingvinyl's promo copy now "
            "includes an autumn US+Europe tour line — promo text only, no "
            "dates (stays uncertain).",
            "Sputnikmusic: 'Uncle' listed with no rating yet; 'frog song' "
            "at 3.5/5 on 1 vote (single-source).",
            "The Reconnoiter's weekly playlist #152 (Oct 9, 2026) includes "
            "'Big Dumb World' — playlist placement, not a review "
            "(single-source).",
            "RIFF Magazine's Sept 22 'Tuesday Tracks' capsule carries 'Big "
            "Dumb World' as second single — first press (single-source).",
        ],
        "sources": [
            ("Fish Narc - Wikipedia", "https://en.wikipedia.org/wiki/Fish_Narc"),
            ("'frog song' - Darkside Records",
             "https://shop.darksiderecords.com/products/fish-narc-frog-song"),
            ("fish narc announces new album 'Uncle' — Stereogum",
             "https://stereogum.com/2508537/fish-narc-announces-new-album-uncle-hear-much-less-me/music"),
            ("Fish Narc announces 'Uncle' on K Records — Faygoluvers",
             "https://www.faygoluvers.net/v5/2026/09/fish-narc-announces-new-album-uncle-on-k-records/"),
            ("fish narc - 'Big Dumb World' (second single) — Stereogum",
             "https://stereogum.com/2511545/fish-narc-big-dumb-world/music/"),
            ("Fish Narc — upcoming releases — upcomingvinyl",
             "https://upcomingvinyl.com/record/fish-narc-uncle"),
            ("Fish Narc artist profile — Release Wave",
             "https://releasewave.com/artists/fish-narc"),
            # wave 30 merge: new sources for the same-day shelf + re-verification
            ("2026 album releases (October calendar) — AltPress",
             "https://www.altpress.com/2026-album-releases/"),
            ("Upcoming album releases — Consequence",
             "http://consequence.net/upcoming-releases/"),
            # wave 32: same-evening re-verification (still pre-release)
            ("'Big Dumb World' — video by James Logan Hyson (Vimeo)",
             "https://vimeo.com/1229703961"),
            ("16 New Songs Out Today (Aug 18, 2026) — Our Culture Mag",
             "https://ourculturemag.com/2026/08/18/16-new-songs-out-today-"
             "to-listen-to-gang-of-youths-fontaines-d-c-and-more/"),
            # Wave 35 (2026-10-12): rounds 15-16 research sources.
            ("Fish Narc — listening party (Permanent Records Roadhouse)",
             "https://roadhouse.permanentrecordsla.com/"),
            ("Weekly playlist #152 — The Reconnoiter",
             "https://areconnoiter.wordpress.com/2026/10/09/"
             "this-weeks-playlist-152/"),
            ("Fish Narc — Sputnikmusic",
             "http://www.sputnikmusic.com/bands/Fish-Narc/128081/"),
        ],
        "watch": {
            "label": "'Uncle' — fifth solo LP",
            "status": "announced",
            "expected": "2026-10-16",
            "as_of": "2026-10-13",
            "note": ("Pre-release as of this research pass (2026-10-12; "
                     "re-verified 2026-10-13 — the Oct 16 date stands, "
                     "Faygoluvers still carries it, and the Oct 15 listening "
                     "party and Oct 29 Gold Diggers date held). "
                     "A release-week readiness pass later on 2026-10-13 "
                     "opened the venue calendar, Bandsintown, Stereogum, "
                     "upcomingvinyl and both capoxxo Eventbrite listings "
                     "again — every date held a second time. "
                     "No third single, no advance reviews, no interviews "
                     "(normal 4 days out). A listening party is listed for "
                     "Thu Oct 15, 7 PM at Permanent Records Roadhouse "
                     "(free, RSVP — verified on the venue calendar). "
                     "upcomingvinyl's promo copy now adds an autumn "
                     "US+Europe tour line (no dates — stays uncertain). "
                     "The archive records a release as 'released' only after "
                     "a research pass confirms it; the watch never claims the "
                     "LP is out early."),
            # wave 30 merge: re-verified pre-release 2026-10-11
            # wave 32: same-evening pass, still pre-release 2026-10-11
            # wave 35: re-verified pre-release 2026-10-12 (listening party
            # added; Europe leg one notch up, still uncertain)
            # signal 2.1: re-verified pre-release 2026-10-13 (all dates held)
            # rotation 5: readiness pass later 2026-10-13 (held a 2nd time)
            "last_reverified": "2026-10-13",
            "reverify_sources": [
                "https://upcomingvinyl.com/artists/fish-narc",
                "https://www.faygoluvers.net/v5/2026/09/"
                "fish-narc-announces-new-album-uncle-on-k-records/",
                "http://consequence.net/upcoming-releases/",
                "https://www.altpress.com/2026-album-releases/",
            ],
        },
        # wave 30 merge: highlighted scene section on the fish-narc page
        "scene_section": {
            "kicker": "the scene record \u2014 wave 30",
            "heading": "New verified facts (2026-10-11 pass)",
            "facts": [
                "Real name: Ben Funkhouser (verified \u2014 Stereogum "
                "announcement interview + Release Wave artist profile).",
                "On the title 'Uncle': the artist's own framing \u2014 "
                "saying 'uncle', giving up, as a tongue-in-cheek nod; the "
                "record reflects on the last ten years, expectations, and "
                "aging, made from a mid-30s vantage point.",
                "Vinyl LP pre-order open through K Records.",
                "Same release-day shelf 2026-10-16 (AltPress): @, "
                "The Avalanches, Dummy, Fontaines D.C., N8NOFACE, They Are "
                "Gutting a Body of Water, Taking Back Sunday.",
            ],
            "link_href": "../scene/fish-narc-uncle.html",
            "link_text": "'Uncle' \u2014 the full fact-block \u2192",
            "link_sub": "the dedicated scene page with tracklist, "
                        "singles, tour dates, and the live watch.",
        },
    },
}

# Wave 32 (2026-10-11): the honest gaps. Collaborators whose public record
# ends at the archive's title credits. Stated as-is on the circle index —
# the archive flags thin records, never fills them with invention.
GAPS = [
    "Max Ferrari — 8 shared transmissions, the circle's most frequent voice: "
    "no public bio, interview, or catalog page found as of 2026-10-12. The "
    "eight title credits are the whole public record.",
    "Yung Vetta: no verifiable public record beyond the title credits — "
    "search returns unrelated same-name artists (Young Vetta, Vetta Borne); "
    "nothing attributable.",
    "jax, vetty, lil soda boi, lil yu, lilvicbxi, ammi $age, shola, "
    "phil is lonely, offline_hp, jo$e dripp, max: no public record found "
    "beyond the archive's title credits as of 2026-10-12.",
    "lilrareboy: catalog-level only — Shazam carries the 'World/War/Rare "
    "Interlude' single (composition & lyrics credited); no bio or press.",
    "pvscale: no new 2026 activity found across 60+ days of searching — his "
    "name collides with the K-pop group PLAVE, drowning web search. The "
    "as-credited productions are the archive record (flagged, not filled).",
    "lil koi is a scene-page figure, not a circle member — the "
    "verified-minimum record lives at scene/lil-koi.html.",
    "The SomeLowLifes member roster still has no public coverage — see the "
    "unknowns register in method.html.",
]

def render_gaps_section():
    """Wave 32: the honest gaps — thin records stated, never filled."""
    items = "".join(f"<li>{escape(g)}</li>" for g in GAPS)
    return f"""
      <section class="section" aria-labelledby="ci-gaps">
        <span class="kicker"><span class="numeral">&#10022;</span>The honest gaps</span>
        <h2 id="ci-gaps">Where the record is thin</h2>
        <p>The archive flags what it could not verify instead of inventing it. Every gap below was searched on 2026-10-12 and came back empty or catalog-level.</p>
        <ul class="fact-list">{items}</ul>
      </section>
"""

def render_sources(sources):
    links = " &middot; ".join(
        f'<a href="{escape(u)}" target="_blank" rel="noopener">{escape(label)}</a>'
        for label, u in sources
    )
    return f'<p class="chart-sub">Sources: {links}</p>'

def render_verified_section(info):
    facts = "".join(f"<li>{escape(f)}</li>" for f in info["facts"])
    return f"""
      <section class="section" aria-labelledby="cv-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The scene record</span>
        <h2 id="cv-h">Verified beyond the titles</h2>
        <p class="chart-sub">Research pass 2026-10-12 &mdash; public sources only, no biographical invention, no lyrics.</p>
        <ul class="fact-list">{facts}</ul>
        {render_sources(info["sources"])}
      </section>
"""

def render_scene_section(info):
    """Wave-30 merge: highlighted "new verified facts" section for a scene
    figure. Only rendered when the figure carries a 'scene_section' block."""
    s = info.get("scene_section")
    if not s:
        return ""
    facts = "".join(f"<li>{escape(f)}</li>" for f in s["facts"])
    return f"""
      <section class="section" aria-labelledby="sn-h">
        <span class="kicker"><span class="numeral">&#10022;</span>{escape(s["kicker"])}</span>
        <h2 id="sn-h">{escape(s["heading"])}</h2>
        <ul class="fact-list">{facts}</ul>
        <p class="chart-sub"><a href="{escape(s["link_href"])}">{escape(s["link_text"])}</a> {escape(s["link_sub"])}</p>
      </section>
"""

def render_watch_section(info):
    """The 'Uncle watch': honest release-status widget driven by data.
    Only rendered when a figure carries a 'watch' block."""
    w = info["watch"]
    return f"""
      <section class="section" aria-labelledby="uw-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The watch</span>
        <h2 id="uw-h">{escape(w["label"])} — watch</h2>
        <p class="chart-sub" id="uncle-watch-status" aria-live="polite"
           data-status="{escape(w["status"])}"
           data-expected="{escape(w["expected"])}"
           data-asof="{escape(w["as_of"])}">Announced — expected {escape(w["expected"])}.</p>
        <p class="chart-sub">{escape(w["note"])} Status as of research pass {escape(w["as_of"])}.</p>
      </section>
"""

def years_active(tracks):
    yrs = sorted({t["date"][:4] for t in tracks if t.get("date")})
    if not yrs:
        return "dates unknown"
    return yrs[0] if len(yrs) == 1 else f"{yrs[0]}–{yrs[-1]}"

def collab_page(name, slug, tracks, slug_of, eras, prev_s, next_s, ckey=None):
    total_plays = sum(t.get("plays") or 0 for t in tracks)
    enrich_html = render_verified_section(ENRICH[ckey]) if ckey in ENRICH else ""
    era_counts = {}
    for t in tracks:
        y = (t.get("date") or "")[:4]
        era = era_for_year(int(y), eras) if y.isdigit() else None
        key = era["name"] if era else "Unplaced"
        era_counts[key] = era_counts.get(key, 0) + 1
    era_html = "".join(
        f"<li><span>{escape(e)}</span><span class=\"top-n\">&times;{n}</span></li>"
        for e, n in sorted(era_counts.items(), key=lambda kv: -kv[1])
    )

    rows = "".join(
        f'<li><a href="../releases/{slug_of[id(t["_r"])]}.html">{escape(t["title"])}</a>'
        f' <span class="dim">{escape(t.get("date") or "date unknown")}'
        + (f" &middot; {fmt(t['plays'])} plays" if t.get("plays") else "")
        + f" &middot; {escape(t['type'])}</span></li>"
        for t in sorted(tracks, key=lambda t: t.get("date") or "")
    )

    prev_link = (
        f'<a class="btn btn-sm" href="{prev_s}.html" rel="prev">&larr; Prev</a>'
        if prev_s else '<span class="btn btn-sm" aria-disabled="true">&larr;</span>'
    )
    next_link = (
        f'<a class="btn btn-sm" href="{next_s}.html" rel="next">Next &rarr;</a>'
        if next_s else '<span class="btn btn-sm" aria-disabled="true">&rarr;</span>'
    )
    # wave 27: circle members who also produce link to their deep dive
    pd_slug = producer_slug(name)
    pd_link = (
        f'<p class="chart-sub"><a href="../producers/{pd_slug}.html">Producer deep dive &rarr;</a> '
        f'{escape(name)}\u2019s as-credited productions, fingerprint, and scene context.</p>'
        if pd_slug in PRODUCER_SLUGS else ""
    )

    body = f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <a href="../network.html">Network</a>
        <a href="../decoder.html">Decoder</a>
        <a href="../api-playground.html">API</a> / <a href="./">Circle</a> / <span aria-current="page">{escape(name)}</span>
      </nav>
      <section class="section" aria-labelledby="cc-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The circle</span>
        <h1 id="cc-h">{escape(name)}</h1>
        <div class="stat-grid">
          <div class="stat"><div class="stat-value">{len(tracks)}</div><div class="stat-label">Shared transmissions</div></div>
          <div class="stat"><div class="stat-value">{fmt(total_plays)}</div><div class="stat-label">Shared plays</div></div>
          <div class="stat"><div class="stat-value">{escape(years_active(tracks))}</div><div class="stat-label">Years active</div></div>
        </div>
        <p class="chart-sub">Play counts are the 2026-10-11 vault snapshot. Credits parsed from <em>w/</em> and <em>ft.</em> fragments in titles &mdash; as credited, verbatim; producers excluded.</p>
      </section>

      <section class="section" aria-labelledby="ce-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Era breakdown</span>
        <h2 id="ce-h">Where the collaborations landed</h2>
        <ol class="top-list">{era_html}</ol>
      </section>

      <section class="section" aria-labelledby="ct-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The shared record</span>
        <h2 id="ct-h">Every shared transmission, in order</h2>
        <ol class="year-list">{rows}</ol>
      </section>
{enrich_html}
{pd_link}
      <nav class="year-pager" aria-label="Collaborator navigation">
        {prev_link}
        <a class="btn btn-sm" href="./">The full circle</a>
        {next_link}
      </nav>
"""
    return HEAD.format(
        title=f"{name} — collaborator",
        desc=f"{name} and Aster da Master: {len(tracks)} shared transmissions, {fmt(total_plays)} plays.",
        canonical=f"/circle/{slug}.html",
    ) + body + FOOT

def index_page(entries):
    cards = "".join(
        f'<a class="year-card" href="{e["slug"]}.html">'
        f'<span class="year-card-y">{escape(e["name"])}</span>'
        f'<span class="year-card-n">{e["n"]} shared &middot; {fmt(e["plays"])} plays</span>'
        f'<span class="year-card-e">{escape(e["years"])}</span>'
        f"</a>"
        for e in entries
    )
    sf_cards = "".join(
        f'<a class="year-card" href="{s}.html">'
        f'<span class="year-card-y">{escape(info["name"])}</span>'
        f'<span class="year-card-n">{len(info["tracks"])} producer credits'
        f" &middot; {fmt(sum(t.get('plays') or 0 for t in info['tracks']))} plays</span>"
        f'<span class="year-card-e">{escape(info["kind"])}</span>'
        f"</a>"
        for s, info in SCENE_FIGURES.items()
    )
    body = f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <span aria-current="page">Circle</span>
      </nav>
      <section class="section" aria-labelledby="ci-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The circle</span>
        <h1 id="ci-h">Everyone he summoned, one page each</h1>
        <p>Every collaborator credited in a title across 219 transmissions. Counts and plays are data, not editorial. Producers are excluded by rule &mdash; the documented scene figures below are kept separately.</p>
        <div class="year-grid">{cards}</div>
      </section>

      <section class="section" aria-labelledby="ci-beyond">
        <span class="kicker"><span class="numeral">&#10022;</span>Beyond the circle</span>
        <h2 id="ci-beyond">Scene figures, not collaborators</h2>
        <p>Producer and scene credits the title-credit rule excludes &mdash; kept visible with the same evidence standard, and outside the collaborator count.</p>
        <div class="year-grid">{sf_cards}</div>
      </section>
{render_gaps_section()}
"""
    return HEAD.format(
        title="The circle — collaborator archive",
        desc="Every Aster da Master collaborator: shared tracks, plays, years active.",
        canonical="/circle/index.html",
    ) + body + FOOT

def scene_figure_page(slug, info):
    tracks = info["tracks"]
    total_plays = sum(t.get("plays") or 0 for t in tracks)
    yrs = sorted({t["date"][:4] for t in tracks if t.get("date")})
    span = yrs[0] if len(yrs) == 1 else f"{yrs[0]}\u2013{yrs[-1]}"
    rows = "".join(
        f'<li><a href="../releases/{t["page"]}">{escape(t["title"])}</a>'
        f' <span class="dim">{escape(t["date"])} &middot; {fmt(t["plays"])} plays'
        f" &middot; {escape(t['type'])}</span></li>"
        for t in sorted(tracks, key=lambda t: t["date"])
    )
    facts = "".join(f"<li>{escape(f)}</li>" for f in info["facts"])
    watch = render_watch_section(info) if info.get("watch") else ""
    scene = render_scene_section(info)
    body = f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <a href="../network.html">Network</a>
        <a href="../decoder.html">Decoder</a>
        <a href="../api-playground.html">API</a> / <a href="./">Circle</a> / <span aria-current="page">{escape(info["name"])}</span>
      </nav>
      <section class="section" aria-labelledby="cc-h">
        <span class="kicker"><span class="numeral">&#10022;</span>{escape(info["kind"])}</span>
        <h1 id="cc-h">{escape(info["name"])}</h1>
        <div class="stat-grid">
          <div class="stat"><div class="stat-value">{len(tracks)}</div><div class="stat-label">Producer-credited tracks</div></div>
          <div class="stat"><div class="stat-value">{fmt(total_plays)}</div><div class="stat-label">Shared plays</div></div>
          <div class="stat"><div class="stat-value">{escape(span)}</div><div class="stat-label">Years active</div></div>
        </div>
        <p class="chart-sub">{escape(info["standing"])}</p>
      </section>

      <section class="section" aria-labelledby="ct-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The shared record</span>
        <h2 id="ct-h">Producer credits in the archive, in order</h2>
        <ol class="year-list">{rows}</ol>
      </section>

      <section class="section" aria-labelledby="cv-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The scene record</span>
        <h2 id="cv-h">Verified beyond the titles</h2>
        <p class="chart-sub">Research pass 2026-10-12 &mdash; public sources only, no biographical invention, no lyrics.</p>
        <ul class="fact-list">{facts}</ul>
        {render_sources(info["sources"])}
      </section>
{watch}
{scene}
      <p class="chart-sub"><a href="../producers/{slug}.html">Producer deep dive &rarr;</a> {escape(info["name"])}&rsquo;s as-credited productions, fingerprint, and scene context.</p>
      <nav class="year-pager" aria-label="Scene figure navigation">
        <a class="btn btn-sm" href="./">The full circle</a>
      </nav>
"""
    html = HEAD.format(
        title=f"{info['name']} \u2014 {info['kind']}",
        desc=f"{info['name']} in the Aster da Master archive: {len(tracks)} producer credits, {fmt(total_plays)} plays.",
        canonical=f"/circle/{slug}.html",
    ) + body + FOOT
    if info.get("watch"):
        html = html.replace(
            "</body>",
            '  <script src="../assets/js/uncle-watch.js"></script>\n</body>',
            1,
        )
    return html

def main():
    releases = DATA["discography"]
    eras = DATA.get("eras", [])

    # wave 27: producer slugs (as-credited) for the deep-dive cross-links
    sess = json.loads((ROOT / "data" / "sessions.json").read_text())["sessions"]
    for s in sess:
        for t in s["tracks"]:
            for p in parse_producers(t["title"]):
                PRODUCER_SLUGS.add(producer_slug(p))

    # Release slugs: identical algorithm to build_search_index.py.
    used, slugs = set(), []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used:
            n += 1
            s = f"{base}-{n}"
        used.add(s)
        slugs.append(s)
    assert len(set(slugs)) == len(releases), "release slug collision"
    slug_of = {id(r): s for r, s in zip(releases, slugs)}

    collabs = {}
    for r in releases:
        for n in parse_collabs(r["title"]):
            k = n.lower()
            if k not in collabs:
                collabs[k] = {"display": n, "tracks": []}
            if len(n) >= len(collabs[k]["display"]):
                collabs[k]["display"] = n
            collabs[k]["tracks"].append(
                {"title": r["title"], "date": r.get("date"), "plays": r.get("plays"),
                 "type": r["type"], "_r": r}
            )

    ordered = sorted(collabs.items(), key=lambda kv: (-len(kv[1]["tracks"]), kv[1]["display"].lower()))

    # Collaborator slugs (deduped; single source of truth for JS deep links).
    cused, entries = set(), []
    for key, info in ordered:
        s = slugify(info["display"])
        base, n = s, 1
        while s in cused:
            n += 1
            s = f"{base}-{n}"
        cused.add(s)
        tracks = info["tracks"]
        entries.append({
            "key": key, "name": info["display"], "slug": s,
            "tracks": tracks,
            "n": len(tracks),
            "plays": sum(t.get("plays") or 0 for t in tracks),
            "years": years_active(tracks),
        })
    assert len({e["slug"] for e in entries}) == len(entries), "collaborator slug collision"
    # Rotation 19 (duplicate-<h1>-text census): every page this generator
    # writes into circle/ carries its person's name as the <h1> — the
    # collaborator pages plus the scene-figure page — so two pages of
    # this family sharing a name would share an <h1> text: unshippable
    # from this generator. (The same name as an <h1> in producers/ or
    # scene/ is the same person from a different section; that cross-
    # family set is pinned by scripts/test_h1_census.py.)
    circle_h1_names = [e["name"] for e in entries] + \
        [info["name"] for info in SCENE_FIGURES.values()]
    assert len(set(circle_h1_names)) == len(circle_h1_names), \
        "circle name collision: two circle pages would share an <h1>"

    OUT.mkdir(exist_ok=True)
    for i, e in enumerate(entries):
        prev_s = entries[i - 1]["slug"] if i > 0 else None
        next_s = entries[i + 1]["slug"] if i < len(entries) - 1 else None
        (OUT / f'{e["slug"]}.html').write_text(
            collab_page(e["name"], e["slug"], e["tracks"], slug_of, eras, prev_s, next_s,
                        ckey=e["key"]),
            encoding="utf-8",
        )

    for s, info in SCENE_FIGURES.items():
        (OUT / f"{s}.html").write_text(scene_figure_page(s, info), encoding="utf-8")

    (OUT / "index.html").write_text(index_page(entries), encoding="utf-8")

    api_circle = {
        e["slug"]: {
            "name": e["name"], "page": f"circle/{e['slug']}.html",
            "shared_transmissions": e["n"], "shared_plays": e["plays"],
            "years_active": e["years"],
            "tracks": [
                {"title": t["title"], "date": t.get("date"), "plays": t.get("plays"), "type": t["type"]}
                for t in sorted(e["tracks"], key=lambda t: t.get("date") or "")
            ],
            **({"verified_notes": {
                "research_pass": "2026-10-12",
                "facts": ENRICH[e["key"]]["facts"],
                "sources": [
                    {"label": label, "url": url}
                    for label, url in ENRICH[e["key"]]["sources"]
                ],
            }} if e["key"] in ENRICH else {}),
        }
        for e in entries
    }
    (API / "circle.json").write_text(
        json.dumps(api_circle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    api_figures = {
        s: {
            "name": info["name"], "kind": info["kind"], "page": f"circle/{s}.html",
            "standing": info["standing"],
            "research_pass": "2026-10-12",
            "tracks": info["tracks"],
            "facts": info["facts"],
            "sources": [{"label": label, "url": url} for label, url in info["sources"]],
            **({"watch": info["watch"]} if info.get("watch") else {}),
        }
        for s, info in SCENE_FIGURES.items()
    }
    (API / "scene-figures.json").write_text(
        json.dumps(api_figures, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Version bump + mirror (same convention as build_codex.py).
    DATA["version"] = NEW_VERSION
    (ROOT / "data" / "artist.json").write_text(
        json.dumps(DATA, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    shutil.copyfile(ROOT / "data" / "artist.json", API / "artist.json")
    idx = json.loads((API / "index.json").read_text())
    idx["version"] = NEW_VERSION
    from api_manifest import render_manifest
    render_manifest(idx, ROOT)
    print(f"circle: {len(entries)} pages + {len(SCENE_FIGURES)} scene figures + index + data/v1/circle.json + data/v1/scene-figures.json; version -> {NEW_VERSION}")

if __name__ == "__main__":
    main()
