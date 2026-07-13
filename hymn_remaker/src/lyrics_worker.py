"""Lyrics Workers — Automated web search and scraping for hymn lyrics.

Workers search multiple hymn lyrics websites, scrape lyrics, and store them
in the database. Supports concurrent operation with rate limiting.

Architecture:
  LyricsWorker orchestrates the pipeline:
  1. Query DB for hymns without lyrics
  2. Extract searchable hymn name from title (strip tune names, MIDI suffixes)
  3. Search via DuckDuckGo or direct URL construction
  4. Scrape lyrics from known sites (timelesstruths.org, hymnary.org, etc.)
  5. Validate and clean lyrics
  6. Update database with found lyrics + source URL
"""

import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# ── Known lyrics sites with their scraping selectors ─────────────────────

LYRICS_SITES = {
    "timelesstruths.org": {
        "url_template": "https://library.timelesstruths.org/music/{slug}/",
        "selectors": [".lyrics"],
        "direct_url": True,  # Can construct URLs directly
    },
    "hymnary.org": {
        "selectors": [],
        "regex_pattern": r"Representative Text\s*(.*?)(?:Tune|Author|Page Scans|Instances|FlexScore)",
        "direct_url": False,  # Must search to find the right page
    },
    "hymnallibrary.org": {
        "selectors": [".lyrics"],
        "direct_url": False,
    },
    "gccsatx.com": {
        "selectors": ["[class*='lyric']"],
        "direct_url": False,
    },
    "hymnary.org": {
        "selectors": ["#representative-text"],
        "direct_url": True,
    },
    "hymnal.net": {
        "selectors": [".lyrics"],
        "direct_url": False,
    },
}

# Priority order for search results (higher = preferred)
SITE_PRIORITY = {
    "timelesstruths.org": 10,
    "hymnary.org": 8,
    "hymnal.net": 7,
    "hymnallibrary.org": 6,
    "gccsatx.com": 5,
}

REQUESTS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}

# ── Title parsing ────────────────────────────────────────────────────────

# Common tune names that appear as suffixes in Cyber Hymnal titles
# These are NOT part of the hymn name — they're melody identifiers
KNOWN_TUNE_NAMES = {
    "Eventide",
    "New Britain",
    "Coronation",
    "St Theodulph",
    "Tallis Canon",
    "St Anne",
    "Fillmore",
    "Regent Square",
    "Gloria",
    "Monk",
    "Dix",
    "Hyfrydol",
    "Lasst Uns Erfreuen",
    "Valet Will Ich Dir Geben",
    "Ebeling",
    "Bonn",
    "Beach Spring",
    "Melismata",
    "Mueller",
    "Mueller 22",
    "Binghamton",
    "Nimrod",
    "Salut D Amour",
    "Rondeau",
    "Ein Ros Entsprungen",
    "Ist Ein Ros Entsprungen",
    "Ein Feste Burg",
    "Ein Feste Burg Isorhythmic",
    "Ein Feste Burg Rhythmic",
    "An Wasserfluessen Babylon",
    "An Wasserflaussen",
    "St Peter",
    "Crusaders Hymn",
    "St Flavian",
    "St Catherine",
    "Hanover",
    "Duke Street",
    "Old 100th",
    "Aurelia",
    "Webbe",
    "Pleyel",
    "Sicilian Mariners",
    "Russian Hymn",
    "Italian Hymn",
    "Lyra Davidica",
    "Easter Hymn",
    "Lancashire",
    "St Magnus",
    "Melita",
    "Unde et Memores",
    "Wolverton",
    "Hermas",
    "Undeet",
    "Magdalen",
    "Oriel",
    "Deerfield",
    "Rest",
    "Ratisbon",
    "Truro",
    "Yorkshire",
    "Warsaw",
    "Moscow",
    "Uxbridge",
    "Arlington",
    "Creditor",
    "Olivers",
    "Gethsemane",
    "Cross of Jesus",
    "Stabat Mater",
    "Passion Chorale",
    "Isorhythmic",
    "Rhythmic",
    "Redhead",
    "Abridge",
    "Bradbury",
    "Cooke",
    "Conkey",
    "Doane",
    "Fischer",
    "Hansom",
    "Hastings",
    "Horton",
    "Ithaca",
    "Kenosis",
    "Martyn",
    "Mendelssohn",
    "Meribah",
    "Miles Lane",
    "Nettleton",
    "Ortonville",
    "Sagina",
    "St Agnes",
    "St Bees",
    "St Croix",
    "St Denio",
    "St George",
    "St Gertrude",
    "St Kevin",
    "St Lawrence",
    "St Louis",
    "St Malo",
    "St Oswald",
    "St Paul",
    "St Sepulchre",
    "St Timothy",
    "Stephens",
    "Stockport",
    "Toplady",
    "University",
    "Vigils",
    "Webb",
    "Wells",
    "Wesley",
    "Wilmot",
    "Winchester New",
    "Winchester Old",
    "Woodworth",
    "Zerubbabel",
    # Common Cyber Hymnal tune names / arrangers
    "Sankey", "Kirkpatrick", "Granahan", "Mc Granahan", "Bliss", "Sweney",
    "Stebbins", "Towner", "Root", "Ogden", "Gabriel", "Lowry", "Hudson",
    "Stainer", "Perkins", "Jones", "Ackley", "Hoffman", "Mason", "Smith",
    "Lund", "Nilsen Lund", "Lindeman", "Belden", "Simpson", "Bradbury",
    "Doane", "Fischer", "Cooke", "Conkey", "Mainzer", "Stockton", "Hopkins",
    "Ahnfelt", "Ratany", "Abbey", "Raleigh", "Leveque", "Gweedore",
    "Barthelemon", "Woodbury", "Zinck", "Malan", "Cross", "Wesley",
    "Evening Hymn", "Morning Star", "Angels Song", "Crusaders Hymn",
    "Russian", "German", "Swedish", "American", "French", "Irish", "Welsh",
    "Old100th", "Old 100th", "Vom Himmel", "Herzliebster", "Wirksworth",
    "S Band", "Dix S Band", "Sagina", "Irish Melody", "Welsh Melody",
    "Praise", "Hymn", "Carol", "Song",
    # German tune names (CamelCase and spaced forms from Cyber Hymnal)
    "Allein Gott", "AlleinGott", "AlleinGottInDerHoechstenNoth",
    "Liebster Jesu", "LiebsterJesu", "Herzliebster",
    "O Mensch Sieh", "OMenschSieh",
    "Lasst Uns Erfreuen", "LasstUnsErfreuen",
    "Ein Feste Burg", "EinFesteBurg",
    "An Wasserfluessen Babylon", "Wasserfluesse", "Wasser Flusse",
    "Valet Will Ich Dir Geben", "ValetWillIchDirGeben",
    "Ein Ros Entsprungen", "Ist Ein Ros Entsprungen",
    "Gelobet Seist Du Jesu Christ", "Nun Danket Alle Gott",
    "Wachet Auf", "Wie Schoen Leuchtet", "Vom Himmel Hoch",
    "O Dass Ich", "ODassIch", "Meine Hoffnung", "Warum Sollt Ich",
    "O Welt Sieh Hier", "Ich Glaub An Gott", "Gott Sei Dank",
    "Lobe Den Herren", "Nun Freut Euch", "Befiehl Du Deine Wege",
    # More Cyber Hymnal tune names / arrangers (round 2)
    "Dykes", "Havergal", "Elvey", "Barnby", "Goss", "Smart", "Sullivan",
    "Calkin", "Turle", "Wesley", "Mendelssohn Bartholdy", "Bartholdy",
    "Gauntlett", "Elgar", "Parry", "Stanford", "Willan", "Farrant",
    "Gibbons", "Tallis", "Byrd", "Croft", "Clarke", "Attwood", "Boyce",
    "Walmisley", "Ouseley", "Stainer", "Parker", "Bach", "Handel",
    "Dies Est Laetitiae", "Das Ist Mein Freude", "Mauburn",
    "Nun Ruhen Alle Waelder", "Christ Lag Im Todesbanden",
    "Schmuecke Dich", "Liebster Jesu Wir Sind Hier",
}

# MIDI variant suffixes from Cyber Hymnal
MIDI_SUFFIX_RE = re.compile(
    r"\s*(?:(?:BMidi|CAM|DMidi|Piano|Organ|Guitar|Choir|Quartet|Solo|"
    r"Strings|Brass|Woodwind|Orchestra|Descant|Harmony|Unison|"
    r"2v|3v|4v|5v|SAB|SATB|TTBB|Descant|Verse|Full|Last)"
    r"\s*(?:\d{1,2})?\s*)+\s*$",
    re.IGNORECASE,
)


def extract_hymn_name(raw_title: str) -> str:
    """Extract the primary searchable hymn name from a raw database title.

    This is the "best guess" — for the full set of search candidates,
    use generate_search_candidates() instead.
    """
    candidates = generate_search_candidates(raw_title)
    return candidates[0] if candidates else raw_title


def extract_hymn_name_from_filename(filename: str) -> str:
    """Extract hymn name from MIDI filename (more reliable than title parsing).

    Cyber Hymnal filenames: HymmName-TuneName.mid or HymnName-TuneName-Variant.mid
    CamelCase variants: JesuJoyOfMansDesiring.mid
    Mixed case with underscores: face_to_face_with_Christ_my_Savior.mid
    LDS filenames: simpler format like "A Mighty Fortress Is Our God.mid"
    """
    # Remove extension
    base = filename.rsplit(".", 1)[0] if "." in filename else filename

    # Split on first dash — hymn name is before the dash
    # Some have multiple dashes: HymnName-TuneName-Variant
    # The hymn name is always the first segment
    parts = base.split("-")
    hymn_part = parts[0]

    # Replace underscores with spaces
    hymn_name = hymn_part.replace("_", " ")

    # Handle numbered hymns: "110 - A Mighty Fortress" → use the full title after the number
    if re.match(r"^\d+\s*$", hymn_name.strip()) and len(parts) > 1:
        # First segment is just a number — rejoin all parts as the hymn name
        hymn_name = base.replace("-", " ").replace("_", " ")
        # Strip the leading number
        hymn_name = re.sub(r"^\d+\s+", "", hymn_name)
    elif len(hymn_name) < 4 and len(parts) > 1:
        # If the result is suspiciously short (< 4 chars), try second segment too
        hymn_name = (parts[0] + " " + parts[1]).replace("_", " ")

    # Handle CamelCase: insert spaces before capital letters that follow lowercase
    # e.g., "JesuJoyOfMansDesiring" → "Jesu Joy Of Mans Desiring"
    # Also handles "AMightyFortress" → "A Mighty Fortress"
    if (
        re.match(r"^[a-z]+[A-Z]", hymn_name)
        or re.match(r"^[A-Z][a-z]+[A-Z]", hymn_name)
        or re.match(r"^[A-Z][A-Z][a-z]", hymn_name)
    ):
        # Split lowercase→uppercase: "JesuJoy" → "Jesu Joy"
        hymn_name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", hymn_name)
        # Split uppercase→uppercase+lowercase: "AFortress" → "A Fortress"
        hymn_name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", hymn_name)

    # Title-case the result (for better search matching)
    # Only if the name is currently all lowercase or mixed case
    if hymn_name.islower() or any(c.isupper() for c in hymn_name[1:] if c.isalpha()):
        # Smart title case: keep minor words lowercase
        minor_words = {
            "a",
            "an",
            "the",
            "and",
            "but",
            "or",
            "for",
            "nor",
            "of",
            "in",
            "on",
            "at",
            "to",
            "by",
            "with",
            "from",
            "as",
            "into",
            "upon",
        }
        words = hymn_name.split()
        result = []
        for i, word in enumerate(words):
            if i > 0 and i < len(words) - 1 and word.lower() in minor_words:
                result.append(word.lower())
            else:
                result.append(word.capitalize())
        hymn_name = " ".join(result)

    return hymn_name.strip()


def generate_search_candidates(raw_title: str) -> list[str]:
    """Generate multiple hymn name candidates for search.

    Returns a list ordered from most likely to least likely.
    Each candidate is tried in order until lyrics are found.
    """
    title = raw_title.strip()
    candidates = []

    # Step 1: Remove MIDI variant suffixes (BMidi CAM, 2v, etc.)
    title = MIDI_SUFFIX_RE.sub("", title).strip()

    # Step 2: Handle CamelCase titles
    if re.match(r"^[A-Z][a-z]*[A-Z]", title):
        title = re.sub(r"(?<!['\u2019])([A-Z])", r" \1", title)
        title = re.sub(r"\s+", " ", title).strip()
    # Step 2.5: Separate numbers from adjacent letters (Old100th -> Old 100th)
    title = re.sub(r"(?<=[a-zA-Z])(?=\d)", " ", title)
    title = re.sub(r"(?<=\d)(?=[A-Z])", " ", title)
    title = re.sub(r"\s+", " ", title).strip()


    # Step 3: Try to strip known tune name suffixes (iteratively)
    words = title.split()
    stripped = list(words)
    changed = True
    while changed and len(stripped) > 2:
        changed = False
        for end_pos in range(len(stripped), max(1, len(stripped) - 6), -1):
            suffix = " ".join(stripped[end_pos:])
            if suffix in KNOWN_TUNE_NAMES:
                candidate = " ".join(stripped[:end_pos])
                if len(candidate.split()) >= 2:
                    stripped = stripped[:end_pos]
                    changed = True
                    break
    tune_stripped = " ".join(stripped)

    # Step 4: German/Latin tune name detection
    # These always contain lowercase German function words
    # that never appear in English hymn names mid-sentence
    PURE_GERMAN_WORDS = re.compile(
        r"\b(?:ist|ein|eine|und|der|die|das|es|von|zu|auf|aus|mit|f\u00fcr|"
        r"soll|kann|wird|haben|war|hat|dem|den|des|im|am|um|nach|\u00fcber|"
        r"unter|durch|gegen|ohne|seit|werden|wurde|gelobet|seist|segen|"
        r"gottes|gnade|heil|feste|burg|entsprungen|wasserfl\u00fcssen|"
        r"wasserfluessen|gerechtigkeit|freuden|leben|segens|"
        r"lobet|geht|steht|liegt|herz|himmel|erde)\b",
        re.IGNORECASE,
    )

    # Find the earliest German marker word (after position 2 to skip
    # short English words like "An", "Das")
    german_cut = None
    for i, word in enumerate(words):
        if i < 2:
            continue
        # Only match lowercase German words (not capitalized English words)
        if word[0].islower() and PURE_GERMAN_WORDS.search(word):
            # But skip common English words that match
            if word.lower() in {
                "an",
                "am",
                "as",
                "at",
                "is",
                "in",
                "on",
                "or",
                "so",
                "to",
                "up",
                "us",
                "we",
                "he",
                "be",
                "do",
                "if",
                "no",
            }:
                # Only cut if surrounded by other German indicators
                prev_german = i > 0 and PURE_GERMAN_WORDS.search(words[i - 1])
                next_german = i < len(words) - 1 and PURE_GERMAN_WORDS.search(
                    words[i + 1]
                )
                if not (prev_german or next_german):
                    continue
            candidate = " ".join(words[:i])
            if len(candidate.split()) >= 2:
                german_cut = i
                break

    # Also check for "St" prefix before a tune name
    st_cut = None
    for i in range(2, len(words) - 1):
        if words[i] in {"St", "St."} and i + 1 < len(words):
            if words[i + 1] in KNOWN_TUNE_NAMES or any(
                w[0].isupper() for w in words[i + 1 :]
            ):
                candidate = " ".join(words[:i])
                if len(candidate.split()) >= 2:
                    st_cut = i
                    break

    # Build candidate list (ordered by specificity)
    if german_cut is not None:
        german_stripped = " ".join(words[:german_cut])
        candidates.append(german_stripped)

    if tune_stripped != title:
        candidates.append(tune_stripped)

    # St-prefix cut
    if st_cut is not None:
        st_candidate = " ".join(words[:st_cut])
        if st_candidate not in candidates:
            candidates.append(st_candidate)

    # Add original as last resort (with MIDI suffix stripped)
    if title not in candidates:
        candidates.append(title)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    return unique if unique else [title]


# Shared session for connection pooling
_SESSION = requests.Session()
_SESSION.headers.update(REQUESTS_HEADERS)


def _urllib_get(
    url: str, timeout: int = 8, allow_redirects: bool = False
) -> Optional[str]:
    """HTTP GET using requests session (with connection pooling)."""
    try:
        r = _SESSION.get(url, timeout=timeout, allow_redirects=allow_redirects)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def make_url_slug(hymn_name: str) -> str:
    """Convert a hymn name to a URL slug for timelesstruths.org.
    timelesstruths uses AP-style title case: major words capitalized,
    minor words (the, of, in, etc.) lowercase.
    e.g., "All Hail The Power Of Jesus Name" → "All_Hail_the_Power_of_Jesus_Name"
    """
    minor_words = {
        "a",
        "an",
        "the",
        "and",
        "but",
        "or",
        "for",
        "nor",
        "of",
        "in",
        "on",
        "at",
        "to",
        "by",
        "with",
        "from",
        "as",
        "into",
        "upon",
    }
    words = hymn_name.split()
    result = []
    for i, word in enumerate(words):
        if i > 0 and i < len(words) - 1 and word.lower() in minor_words:
            result.append(word.lower())
        else:
            result.append(word)
    return "_".join(result)


# ── Scraping functions ───────────────────────────────────────────────────


def scrape_timelesstruths(hymn_name: str) -> Optional[tuple]:
    """Try to scrape lyrics from timelesstruths.org via direct URL.
    Tries both title-case and all-lowercase-minor-words slug formats.
    """
    # Try AP-style slug first (most common)
    slug = make_url_slug(hymn_name)
    url = f"https://library.timelesstruths.org/music/{slug}/"
    html = _urllib_get(url)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        lyrics_el = soup.select_one(".lyrics")
        if lyrics_el:
            text = lyrics_el.get_text(separator="\n").strip()
            text = re.sub(r"\n{3,}", "\n\n", text)
            if len(text) > 30:
                return text, url

    # Try fully capitalized slug (original DB title format)
    slug2 = hymn_name.replace(" ", "_")
    if slug2 != slug:
        url2 = f"https://library.timelesstruths.org/music/{slug2}/"
        html2 = _urllib_get(url2)
        if html2:
            soup2 = BeautifulSoup(html2, "html.parser")
            lyrics_el2 = soup2.select_one(".lyrics")
            if lyrics_el2:
                text2 = lyrics_el2.get_text(separator="\n").strip()
                text2 = re.sub(r"\n{3,}", "\n\n", text2)
                if len(text2) > 30:
                    return text2, url2

    return None


def scrape_gccsatx(hymn_name: str) -> Optional[tuple]:
    """Try to scrape lyrics from gccsatx.com/hymns via direct URL.
    URL format: https://gccsatx.com/hymns/{lowercase-with-dashes}/
    """
    slug = hymn_name.lower().replace(" ", "-").replace("'", "")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    url = f"https://gccsatx.com/hymns/{slug}/"
    html = _urllib_get(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for sel in ["[class*='lyric']", "article", ".hymn-text"]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n").strip()
            # Remove metadata prefix (author, key, etc.)
            text = re.sub(r"^[^V]*?(Verse \d)", r"\1", text, flags=re.DOTALL)
            if len(text) > 50:
                text = re.sub(r"\n{3,}", "\n\n", text)
                return text, url
    return None


def scrape_hymnary(hymn_name: str) -> Optional[tuple]:
    """Try to scrape lyrics from hymnary.org/text/ via direct URL.
    Hymnary uses the first line as slug (lowercase, underscores).
    Many hymns have title = first line, so we try the title as slug.
    Also tries common first-line extensions and variant spellings.
    """
    # Build slug variations to try
    slugs = []

    # 1. Title as-is (most common hit)
    base_slug = hymn_name.lower().replace(" ", "_").replace("'", "")
    base_slug = re.sub(r"[^a-z0-9_]", "", base_slug)
    base_slug = re.sub(r"_{2,}", "_", base_slug).strip("_")
    slugs.append(base_slug)

    # 2. Common variant spellings (O vs Oh, etc.)
    variant_slugs = []
    if base_slug.startswith("oh_"):
        variant_slugs.append(base_slug.replace("oh_", "o_", 1))
    if base_slug.startswith("o_"):
        variant_slugs.append(base_slug.replace("o_", "oh_", 1))
    # Remove trailing apostrophe-s
    if base_slug.endswith("s"):
        variant_slugs.append(base_slug[:-1])
    slugs.extend(variant_slugs)

    # 3. Common first-line extensions for abbreviated titles
    # Only try for short titles (likely truncated first lines), limit to 10
    extensions = [
        "_throne",
        "_with_gladness",
        "_name_most_holy",
        "_for_spacious_skies",
        "_lord",
        "_o_lord",
        "_my_soul",
        "_my_god",
        "_to_me",
        "_to_thee",
    ]
    # Only add extensions if the title is short (likely abbreviated)
    words = hymn_name.split()
    if len(words) <= 3:
        for ext in extensions:
            slugs.append(base_slug + ext)

    # Try each slug
    for slug in slugs:
        url = f"https://hymnary.org/text/{slug}"
        html = _urllib_get(url, allow_redirects=True)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("body")
        if body:
            text = body.get_text()
            match = re.search(
                r"Representative Text(.*?)(?:Tune|Author|Page Scans|Instances|FlexScore)",
                text,
                re.DOTALL,
            )
            if match:
                lyrics = match.group(1).strip()
                lyrics = re.sub(r"\s+", " ", lyrics).strip()
                lyrics = re.sub(r"\s*(\d+)\.", r"\n\1.", lyrics)
                if len(lyrics) > 50:
                    return lyrics, url
    return None


# ── Hymnal.net index-based matching ──────────────────────────────────────
_HYMNAL_NET_INDEX: Optional[dict] = None
_HYMNAL_NET_INDEX_PATH = Path(__file__).parent.parent / "hymnal_net_index.json"


def _load_hymnal_net_index() -> dict:
    """Load the hymnal.net title→URL index (lazy-loaded)."""
    global _HYMNAL_NET_INDEX
    if _HYMNAL_NET_INDEX is None:
        try:
            with open(_HYMNAL_NET_INDEX_PATH) as f:
                raw = json.load(f)
            # Normalize all titles for matching
            _HYMNAL_NET_INDEX = {}
            for title, url in raw.items():
                norm = re.sub(r"[^a-z0-9 ]", "", title.lower().strip())
                norm = re.sub(r"\s+", " ", norm).strip()
                _HYMNAL_NET_INDEX[norm] = url
            # Build word-level index (first 3 significant words)
            for title, url in raw.items():
                norm = re.sub(r"[^a-z0-9 ]", "", title.lower().strip())
                norm = re.sub(r"\s+", " ", norm).strip()
                words = [w for w in norm.split() if len(w) > 2][:3]
                key = " ".join(words)
                if key not in _HYMNAL_NET_INDEX:
                    _HYMNAL_NET_INDEX[key] = url
        except FileNotFoundError:
            logger.warning(
                "hymnal_net_index.json not found — hymnal.net matching disabled"
            )
            _HYMNAL_NET_INDEX = {}
    return _HYMNAL_NET_INDEX


def scrape_hymnalnet(hymn_name: str) -> Optional[tuple]:
    """Match a hymn name against the hymnal.net index and scrape lyrics.

    Strategy:
    1. Exact match on normalized title
    2. Prefix match: find index entries that START WITH our query
       (Cyber Hymnal titles are abbreviated; hymnal.net has full first lines)
    3. Validate: the found lyrics must contain significant words from the title
    """
    index = _load_hymnal_net_index()
    if not index:
        return None

    norm = re.sub(r"[^a-z0-9 ]", "", hymn_name.lower().strip())
    norm = re.sub(r"\s+", " ", norm).strip()

    if not norm or len(norm) < 3:
        return None

    # Extract significant words from the query for validation
    query_words = set(w for w in norm.split() if len(w) > 2)

    # Strategy 1: Exact match
    url = None
    if norm in index:
        url = index[norm]
    else:
        # Strategy 2: Prefix match — find index entries that start with our query
        # E.g. query="all glory be" matches index key="all glory be to god the father"
        candidates = []
        for idx_title, idx_url in index.items():
            if len(idx_title) < 3:
                continue
            # Our query is a PREFIX of the index entry (abbreviated title -> full title)
            if idx_title.startswith(norm + " ") or idx_title == norm:
                # Score: prefer shorter titles (closer match)
                candidates.append((len(idx_title), idx_title, idx_url))
            # Index entry is a PREFIX of our query (unusual but possible)
            elif norm.startswith(idx_title + " ") and len(idx_title) >= 6:
                candidates.append((len(idx_title), idx_title, idx_url))

        # Sort by title length (shortest first = closest match)
        candidates.sort()
        if candidates:
            url = candidates[0][2]

    if not url:
        return None

    # Scrape lyrics from hymnal.net
    html = _urllib_get(url, allow_redirects=True)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    lyrics_el = soup.select_one(".lyrics")
    if lyrics_el:
        text = lyrics_el.get_text(separator="\n").strip()
        if len(text) < 50:
            return None

        # Validate: check that significant query words appear in the lyrics
        # This prevents false matches (e.g., "Ah Holy Jesus" matching "Go on in the Lord")
        text_lower = text.lower()
        significant_query = {w for w in query_words if len(w) > 2}
        if significant_query:
            found_in_lyrics = sum(1 for w in significant_query if w in text_lower)
            # At least 1 significant word must appear, or skip validation for very short titles
            if found_in_lyrics == 0 and len(significant_query) >= 2:
                return None

        return text, url
    return None


def scrape_tune_hymnalnet(tune_name: str) -> Optional[tuple]:
    """Look up a hymn tune name on hymnary.org, find associated hymn titles,
    then match against the hymnal.net index to find lyrics.
    Works for entries where the title is just a tune name (e.g., 'harlech', 'martyrdom').
    """
    import re as _re

    # Normalize tune name for hymnary.org URL
    slug = tune_name.lower().strip().replace(" ", "_")
    slug = _re.sub(r"[_ ]+o$", "", slug)  # Remove trailing 'o'
    slug = _re.sub(r"\d+$", "", slug).strip("_")

    if len(slug) < 3:
        return None

    # Fetch the tune page from hymnary.org
    tune_url = f"https://hymnary.org/tune/{slug}"
    html = _urllib_get(tune_url, allow_redirects=True)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    text_links = soup.select('a[href*="/text/"]')
    if not text_links:
        return None

    # Load hymnal.net index for matching
    hnet_index = _load_hymnal_net_index()
    if not hnet_index:
        return None

    # Try each associated hymn title against hymnal.net
    for link in text_links[:5]:
        hymn_title = link.get_text().strip()
        if not hymn_title or hymn_title == "Go to text page...":
            continue

        norm = _re.sub(r"[^a-z0-9 ]", "", hymn_title.lower().strip())
        norm = _re.sub(r"\s+", " ", norm).strip()

        # Exact match
        matched_url = hnet_index.get(norm)

        # Prefix match
        if not matched_url:
            for idx_t, idx_url in hnet_index.items():
                if idx_t.startswith(norm) or norm.startswith(idx_t):
                    matched_url = idx_url
                    break

        # Word-level fuzzy match
        if not matched_url:
            words = [w for w in norm.split() if len(w) > 2][:3]
            key = " ".join(words)
            # Check if any index key starts with these 3 words
            for idx_t, idx_url in hnet_index.items():
                if idx_t.startswith(key):
                    matched_url = idx_url
                    break

        if matched_url:
            # Scrape lyrics from hymnal.net
            lhtml = _urllib_get(matched_url, allow_redirects=True)
            if lhtml:
                lsoup = BeautifulSoup(lhtml, "html.parser")
                lyrics_el = lsoup.select_one(".lyrics")
                if lyrics_el:
                    text = lyrics_el.get_text(separator="\n").strip()
                    if len(text) > 50:
                        return text, matched_url

    return None


def scrape_generic(url: str) -> Optional[str]:
    """Scrape lyrics from a known site URL using CSS selectors and regex fallbacks."""
    html = _urllib_get(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    # Try CSS selectors
    for sel in [
        ".lyrics",
        "[class*='lyric']",
        ".verse",
        "[class*='verse']",
        ".hymn-text",
        ".stanza",
        ".poem",
    ]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n").strip()
            if len(text) > 30:
                text = re.sub(r"\n{3,}", "\n\n", text)
                return text

    # Regex fallback for hymnary.org "Representative Text"
    body = soup.find("body")
    if body:
        body_text = body.get_text()
        match = re.search(
            r"Representative Text\s*(.*?)(?:Tune|Author|Page Scans|Instances|FlexScore)",
            body_text,
            re.DOTALL,
        )
        if match:
            text = match.group(1).strip()
            # Clean up numbered verses
            text = re.sub(r"\s+", " ", text)
            if len(text) > 30:
                return text


def search_hymnary_first_line(query: str) -> Optional[str]:
    """Search hymnary.org by query and return the full first line of the first result.
    This helps bridge Cyber Hymnal abbreviated titles to full first lines.
    """
    try:
        url = f"https://hymnary.org/search?qu={query.replace(' ', '+')}"
        html = _urllib_get(url, allow_redirects=True)
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select('a[href*="/hymn/"]'):
            href = link.get("href", "")
            if "/hymn/" in href and href.startswith("/"):
                first_line = link.get_text(strip=True)
                if len(first_line) > 10 and len(first_line) < 100:
                    # Clean up common artifacts
                    first_line = re.sub(r"\s+", " ", first_line).strip()
                    return first_line
    except Exception as e:
        logger.debug(f"hymnary search failed for '{query}': {e}")
    return None


def search_and_scrape(hymn_name: str) -> Optional[tuple]:
    """Search DuckDuckGo for hymn lyrics and scrape from results.

    Returns (lyrics_text, source_url) or None.
    """
    search_query = f'"{hymn_name}" hymn lyrics'
    try:
        results = list(DDGS().text(search_query, max_results=10))
    except Exception as e:
        logger.warning(f"Search failed for '{hymn_name}': {e}")
        return None

    # Sort results by site priority
    scored = []
    for result in results:
        href = result.get("href", "")
        priority = 0
        for domain, pri in SITE_PRIORITY.items():
            if domain in href:
                priority = pri
                break
        scored.append((priority, href, result))

    scored.sort(key=lambda x: -x[0])  # Highest priority first

    for priority, href, result in scored:
        if priority == 0:
            continue  # Skip unknown sites
        lyrics = scrape_generic(href)
        if lyrics and len(lyrics) > 30:
            return lyrics, href

    return None


# ── Lyrics validation ────────────────────────────────────────────────────


def validate_lyrics(text: str, hymn_name: str) -> bool:
    """Basic validation that scraped text looks like hymn lyrics."""
    if not text or len(text) < 30:
        return False
    # Must have at least some word overlap with the hymn name
    name_words = set(re.findall(r"[a-zA-Z]+", hymn_name.lower()))
    lyrics_words = set(re.findall(r"[a-zA-Z]+", text.lower()))
    if not name_words:
        return True  # Can't check, assume OK
    overlap = name_words & lyrics_words
    # At least one significant word from the title should appear in lyrics
    significant = {w for w in name_words if len(w) > 2}
    if significant and not (significant & lyrics_words):
        return False
    # Check it doesn't look like navigation/UI text
    if text.count("<") > 5:  # HTML leaked through
        return False
    if len(text) < 50:
        return False
    return True


def clean_lyrics(text: str) -> str:
    """Clean up scraped lyrics text."""
    # Normalize whitespace
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove verse numbers at start of lines (optional, keep for structure)
    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    # Remove any embedded navigation text
    text = re.sub(r"(?:Home|Explore|Create|Studio|Library|About|Search).*?\n", "", text)
    return text.strip()


# ── Worker class ─────────────────────────────────────────────────────────


@dataclass
class LyricsWorkerStats:
    total_attempted: int = 0
    found: int = 0
    not_found: int = 0
    errors: int = 0
    skipped: int = 0
    elapsed: float = 0.0

    def summary(self) -> str:
        rate = (self.found / self.total_attempted * 100) if self.total_attempted else 0
        return (
            f"Lyrics search: {self.found}/{self.total_attempted} found ({rate:.1f}%), "
            f"{self.not_found} not found, {self.errors} errors, "
            f"{self.skipped} skipped in {self.elapsed:.1f}s"
        )


class LyricsWorker:
    """Orchestrates automated hymn lyrics search and scraping.

    Usage:
        worker = LyricsWorker("hymn_database.db")
        stats = worker.run(limit=100)       # Process 100 hymns
        stats = worker.run(source="lds")    # Only LDS hymns
    """

    def __init__(
        self,
        db_path: str = "hymn_database.db",
        rate_limit: float = 1.5,
        max_workers: int = 3,
    ):
        self.db_path = db_path
        self.rate_limit = rate_limit  # Seconds between requests to same site
        self.max_workers = max_workers
        self._last_request_time: dict[str, float] = {}

    def _rate_wait(self, domain: str):
        """Enforce rate limiting per domain."""
        last = self._last_request_time.get(domain, 0)
        elapsed = time.time() - last
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request_time[domain] = time.time()

    def _get_hymns_needing_lyrics(
        self, limit: int = 100, source: Optional[str] = None, offset: int = 0
    ) -> list[dict]:
        """Query database for hymns that need lyrics."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = """
            SELECT id, title, filename, tags, lyrics_source
            FROM hymns
WHERE (lyrics IS NULL OR lyrics = '')
    AND (lyrics_attempted IS NULL OR lyrics_attempted = 0)
"""
        params: list = []

        if source:
            query += " AND tags LIKE ?"
            params.append(f"%{source}%")

        # Skip instrumentals/Bach/classical pieces (unlikely to have lyrics)
        # Also skip non-hymn MIDI files (drum tracks, samples, etc.)
        query += """
            AND title NOT LIKE 'Book1%'
            AND title NOT LIKE 'Book2%'
            AND title NOT LIKE 'Bach %'
            AND title NOT LIKE 'Brahms %'
            AND title NOT LIKE 'Cpe Bach%'
            AND title NOT LIKE 'Vivaldi %'
            AND title NOT LIKE 'Acoustic %'
            AND title NOT LIKE 'Arp %'
            AND title NOT LIKE 'Sample %'
            AND title NOT LIKE 'Notebook%'
            AND title NOT LIKE 'Toccata%'
            AND title NOT LIKE 'Fugue%'
            AND title NOT LIKE 'Prelude%'
            AND title NOT LIKE 'Sonata%'
            AND title NOT LIKE 'Concerto%'
            AND title NOT LIKE 'Mutopia File%'
            AND title NOT LIKE 'Leyenda%'
            AND title NOT LIKE 'Osterreichische%'
            AND filename NOT LIKE 'Take%'
            AND filename NOT LIKE 'Guitar%'
            AND filename NOT LIKE 'Bass%'
            AND filename NOT LIKE '%Kick%'
            AND filename NOT LIKE '%Snare%'
            AND filename NOT LIKE '%Cymbal%'
            AND filename NOT LIKE '%HiHat%'
            AND filename NOT LIKE 'Tom%'
            AND filename NOT LIKE 'Crash%'
            AND filename NOT LIKE 'Ride%'
            AND filename NOT LIKE 'Take6%'
            AND filename NOT LIKE '%FX%'
            AND filename NOT LIKE '%Kit%'
            AND filename NOT LIKE '%Loop%'
            AND filename NOT LIKE '%Fill%'
            AND filename NOT LIKE '%Drum%'
            AND filename NOT LIKE 'Arp%'
            AND filename NOT LIKE 'Piano%'
            AND filename NOT LIKE 'Sample%'
            AND LENGTH(title) > 3
            AND LENGTH(filename) > 8
            AND (
                filename LIKE '%-%'
                OR LENGTH(title) > 8
            )
        """

        query += " ORDER BY id LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _update_lyrics(self, hymn_id: int, lyrics: str, source_url: str):
        """Store found lyrics in the database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """UPDATE hymns
               SET lyrics = ?, lyrics_source = ?, updated_at = strftime('%s','now')
               WHERE id = ?""",
            (lyrics, source_url, hymn_id),
        )
        conn.commit()
        conn.close()

    def _mark_attempted(self, hymn_id: int):
        """Mark a hymn as attempted (lyrics search failed)."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE hymns SET lyrics_attempted = 1 WHERE id = ?", (hymn_id,))
        conn.commit()
        conn.close()

    def _process_hymn(self, hymn: dict, no_search: bool = False) -> Optional[tuple]:
        """Search for and scrape lyrics for a single hymn.

        Strategy (optimized order -- most reliable sources first):
        1. Extract hymn name from filename + title candidates
        2. Try hymnal.net FIRST (index-based, ~50% hit rate, fast)
        3. Try timelesstruths.org (direct URL, no search needed)
        4. Try gccsatx.com and hymnary.org (direct URLs)
        5. Tune-name lookup (for short/tune-name titles)
        6. DDG search fallback (slow, rarely useful)

        Returns (hymn_id, lyrics, source_url) or None.
        """
        hymn_id = hymn["id"]
        raw_title = hymn["title"]
        filename = hymn.get("filename", "")

        # Build candidates: filename-based first (most reliable), then title-based
        candidates = []
        if filename:
            fn_name = extract_hymn_name_from_filename(filename)
            if fn_name and fn_name not in candidates:
                candidates.append(fn_name)
        title_candidates = generate_search_candidates(raw_title)
        for c in title_candidates:
            if c not in candidates:
                candidates.append(c)

        # Phase 1: Try hymnal.net FIRST (index-based matching, highest hit rate)
        for hymn_name in candidates[:3]:
            result = scrape_hymnalnet(hymn_name)
            if result:
                lyrics, url = result
                lyrics = clean_lyrics(lyrics)
                if validate_lyrics(lyrics, hymn_name):
                    logger.info(f"[{hymn_id}] Found via hymnalnet: {hymn_name}")
                    return hymn_id, lyrics, url

        # Phase 2: Try timelesstruths.org (direct URL, no search)
        for hymn_name in candidates[:3]:
            self._rate_wait("timelesstruths.org")
            result = scrape_timelesstruths(hymn_name)
            if result:
                lyrics, url = result
                lyrics = clean_lyrics(lyrics)
                if validate_lyrics(lyrics, hymn_name):
                    logger.info(f"[{hymn_id}] Found via timelesstruths: {hymn_name}")
                    return hymn_id, lyrics, url

        # Phase 3: Try gccsatx.com (fast direct URL)
        for hymn_name in candidates[:2]:
            self._rate_wait("gccsatx.com")
            result = scrape_gccsatx(hymn_name)
            if result:
                lyrics, url = result
                lyrics = clean_lyrics(lyrics)
                if validate_lyrics(lyrics, hymn_name):
                    logger.info(f"[{hymn_id}] Found via gccsatx: {hymn_name}")
                    return hymn_id, lyrics, url

        # Phase 4: Try hymnary.org (direct URL)
        for hymn_name in candidates[:2]:
            self._rate_wait("hymnary.org")
            result = scrape_hymnary(hymn_name)
            if result:
                lyrics, url = result
                lyrics = clean_lyrics(lyrics)
                if validate_lyrics(lyrics, hymn_name):
                    logger.info(f"[{hymn_id}] Found via hymnary: {hymn_name}")
                    return hymn_id, lyrics, url

        # Phase 5: Tune-name lookup via hymnal.net (for short/tune-name titles)
        if len(raw_title.strip()) <= 20:
            result = scrape_tune_hymnalnet(raw_title.strip())
            if result:
                lyrics, url = result
                lyrics = clean_lyrics(lyrics)
                if validate_lyrics(lyrics, raw_title):
                    logger.info(f"[{hymn_id}] Found via tune-lookup: {raw_title}")
                    return hymn_id, lyrics, url

        # Phase 5.5: hymnary.org search -> find first line -> match hymnal.net
        # This bridges Cyber Hymnal abbreviated titles to full first lines
        primary = candidates[0] if candidates else raw_title
        if len(primary.split()) >= 2:
            self._rate_wait("hymnary.org")
            first_line = search_hymnary_first_line(primary)
            if first_line and first_line != primary:
                # Try matching the first line against hymnal.net
                result = scrape_hymnalnet(first_line)
                if result:
                    lyrics, url = result
                    lyrics = clean_lyrics(lyrics)
                    if validate_lyrics(lyrics, first_line):
                        logger.info(f"[{hymn_id}] Found via hymnary-search->hymnalnet: {first_line}")
                        return hymn_id, lyrics, url
                # Also try timelesstruths with the first line
                self._rate_wait("timelesstruths.org")
                result = scrape_timelesstruths(first_line)
                if result:
                    lyrics, url = result
                    lyrics = clean_lyrics(lyrics)
                    if validate_lyrics(lyrics, first_line):
                        logger.info(f"[{hymn_id}] Found via hymnary-search->timelesstruths: {first_line}")
                        return hymn_id, lyrics, url

        # Phase 6: Search DDG for the best candidate only (slow fallback)
        if not no_search:
            primary = candidates[0] if candidates else raw_title
            self._rate_wait("duckduckgo.com")
            result = search_and_scrape(primary)
            if result:
                lyrics, url = result
                lyrics = clean_lyrics(lyrics)
                if validate_lyrics(lyrics, primary):
                    logger.info(f"[{hymn_id}] Found via search: {primary}")
                    return hymn_id, lyrics, url

        logger.debug(f"[{hymn_id}] Lyrics not found: tried {candidates}")
        self._mark_attempted(hymn_id)
        return None


    def run(
        self,
        limit: int = 100,
        source: Optional[str] = None,
        offset: int = 0,
        dry_run: bool = False,
        no_search: bool = False,
    ) -> LyricsWorkerStats:
        """Run the lyrics search pipeline.

        Args:
            limit: Maximum number of hymns to process.
            source: Filter by source tag (e.g., 'cyberhymnal', 'lds').
            offset: Skip this many hymns.
            dry_run: If True, search but don't update database.
            no_search: If True, skip DDG search (only use direct URLs).
        """
        start_time = time.time()
        stats = LyricsWorkerStats()

        hymns = self._get_hymns_needing_lyrics(
            limit=limit, source=source, offset=offset
        )
        logger.info(
            f"Found {len(hymns)} hymns needing lyrics "
            f"(source={source or 'all'}, offset={offset})"
        )

        if not hymns:
            return stats

        for hymn in hymns:
            stats.total_attempted += 1
            try:
                result = self._process_hymn(hymn, no_search=no_search)
                if result:
                    hymn_id, lyrics, source_url = result
                    stats.found += 1
                    if not dry_run:
                        self._update_lyrics(hymn_id, lyrics, source_url)
                else:
                    stats.not_found += 1
            except Exception as e:
                logger.error(f"[{hymn['id']}] Error processing '{hymn['title']}': {e}")
                stats.errors += 1

            # Progress logging
            if stats.total_attempted % 10 == 0:
                logger.info(
                    f"Progress: {stats.total_attempted}/{len(hymns)} "
                    f"({stats.found} found, {stats.not_found} miss, {stats.errors} err)"
                )

        stats.elapsed = time.time() - start_time
        logger.info(stats.summary())
        return stats

    def run_batch(
        self,
        batch_size: int = 100,
        max_hymns: int = 1000,
        source: Optional[str] = None,
        no_search: bool = False,
    ) -> LyricsWorkerStats:
        """Run in batches to process many hymns with periodic stats.

        Args:
            batch_size: Number of hymns per batch.
            max_hymns: Total maximum to process.
            source: Filter by source tag.
            no_search: If True, skip DDG search (only use direct URLs).
        """
        total_stats = LyricsWorkerStats()
        offset = 0

        while offset < max_hymns:
            limit = min(batch_size, max_hymns - offset)
            logger.info(f"\n=== Batch starting at offset {offset} ===")
            stats = self.run(
                limit=limit, source=source, offset=offset, no_search=no_search
            )
            total_stats.total_attempted += stats.total_attempted
            total_stats.found += stats.found
            total_stats.not_found += stats.not_found
            total_stats.errors += stats.errors
            total_stats.elapsed += stats.elapsed

            if stats.total_attempted == 0:
                break  # No more hymns to process

            offset += stats.total_attempted

            # Save checkpoint
            logger.info(f"Running total: {total_stats.summary()}")

        return total_stats


# ── CLI entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="Hymn Lyrics Worker")
    parser.add_argument("--db", default="hymn_database.db", help="Database path")
    parser.add_argument("--limit", type=int, default=50, help="Max hymns to process")
    parser.add_argument("--offset", type=int, default=0, help="Offset into hymn list")
    parser.add_argument("--source", default=None, help="Filter by source tag")
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Batch size for batch mode"
    )
    parser.add_argument("--max", type=int, default=500, help="Max total in batch mode")
    parser.add_argument("--batch", action="store_true", help="Run in batch mode")
    parser.add_argument("--dry-run", action="store_true", help="Search but don't save")
    parser.add_argument("--test", action="store_true", help="Test title parsing only")
    parser.add_argument("--rate", type=float, default=1.5, help="Rate limit (seconds)")
    parser.add_argument(
        "--no-search", action="store_true", help="Skip DDG search (direct URLs only)"
    )
    args = parser.parse_args()

    worker = LyricsWorker(db_path=args.db, rate_limit=args.rate)

    if args.test:
        # Test title parsing
        import sqlite3

        conn = sqlite3.connect(args.db)
        for row in conn.execute("""SELECT id, title FROM hymns
            WHERE (lyrics IS NULL OR lyrics = '')
            AND tags LIKE '%cyberhymnal%' LIMIT 30""").fetchall():
            parsed = extract_hymn_name(row[1])
            changed = " <-- " + parsed if parsed != row[1] else ""
            print(f"  [{row[0]}] '{row[1]}' -> '{parsed}'{changed}")
        conn.close()
    elif args.batch:
        stats = worker.run_batch(
            batch_size=args.batch_size,
            max_hymns=args.max,
            source=args.source,
            no_search=args.no_search,
        )
        print(f"\nFinal: {stats.summary()}")
    else:
        stats = worker.run(
            limit=args.limit,
            source=args.source,
            offset=args.offset,
            dry_run=args.dry_run,
            no_search=args.no_search,
        )
        print(f"\nFinal: {stats.summary()}")
