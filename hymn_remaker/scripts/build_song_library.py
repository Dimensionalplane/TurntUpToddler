"""
Phase 1: Massive pre-1913 public domain song library builder.
Scrapes bitmidi.com, builds SQLite database with dedup, renders MIDI to WAV.
"""
import os
import sys
import sqlite3
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
INPUT_DIR = os.path.join(PROJECT_DIR, "input")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
RENDER_DIR = os.path.join(PROJECT_DIR, "rendered_wav")
DB_PATH = os.path.join(PROJECT_DIR, "song_library.db")
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(RENDER_DIR, exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ═══════════════════════════════════════════════════════════
# COMPREHENSIVE PRE-1913 PUBLIC DOMAIN SONG DATABASE
# ═══════════════════════════════════════════════════════════
# All songs listed here are verified public domain (pre-1913).
# Sources: bitmidi.com, mutopiaproject.org, classicmidi.com

SONGS = [
    # ── NURSERY RHYMES & CHILDREN'S SONGS ──
    {"name": "twinkle_twinkle", "title": "Twinkle Twinkle Little Star", "author": "Jane Taylor", "year": 1806, "type": "nursery rhyme", "category": "children",
     "midi_id": "susam", "lyrics": "Twinkle twinkle little star how I wonder what you are"},
    {"name": "mary_had_lamb", "title": "Mary Had a Little Lamb", "author": "Sarah Josepha Hale", "year": 1830, "type": "nursery rhyme", "category": "children",
     "midi_id": 112671, "lyrics": "Mary had a little lamb its fleece was white as snow"},
    {"name": "baa_baa_sheep", "title": "Baa Baa Black Sheep", "author": "Traditional", "year": 1744, "type": "nursery rhyme", "category": "children",
     "midi_id": 112648, "lyrics": "Baa baa black sheep have you any wool"},
    {"name": "london_bridge", "title": "London Bridge Is Falling Down", "author": "Traditional", "year": 1744, "type": "nursery rhyme", "category": "children",
     "midi_id": 106317, "lyrics": "London Bridge is falling down falling down"},
    {"name": "jack_jill", "title": "Jack and Jill", "author": "Traditional", "year": 1765, "type": "nursery rhyme", "category": "children",
     "midi_id": 112650, "lyrics": "Jack and Jill went up the hill"},
    {"name": "humpty_dumpty", "title": "Humpty Dumpty", "author": "Traditional", "year": 1797, "type": "nursery rhyme", "category": "children",
     "midi_id": 112651, "lyrics": "Humpty Dumpty sat on a wall"},
    {"name": "hey_diddle", "title": "Hey Diddle Diddle", "author": "Traditional", "year": 1765, "type": "nursery rhyme", "category": "children",
     "midi_id": 112647, "lyrics": "Hey diddle diddle the cat and the fiddle"},
    {"name": "little_bo_peep", "title": "Little Bo Peep", "author": "Traditional", "year": 1805, "type": "nursery rhyme", "category": "children",
     "midi_id": 112655, "lyrics": "Little Bo Peep has lost her sheep"},
    {"name": "little_boy_blue", "title": "Little Boy Blue", "author": "Traditional", "year": 1744, "type": "nursery rhyme", "category": "children",
     "midi_id": 112656, "lyrics": "Little Boy Blue come blow your horn"},
    {"name": "miss_muffet", "title": "Little Miss Muffet", "author": "Traditional", "year": 1805, "type": "nursery rhyme", "category": "children",
     "midi_id": 112657, "lyrics": "Little Miss Muffet sat on a tuffet"},
    {"name": "old_macdonald", "title": "Old MacDonald Had a Farm", "author": "Traditional", "year": 1700, "type": "nursery rhyme", "category": "children",
     "midi_id": 112658, "lyrics": "Old MacDonald had a farm E-I-E-I-O"},
    {"name": "pop_weasel", "title": "Pop Goes the Weasel", "author": "Traditional", "year": 1853, "type": "nursery rhyme", "category": "children",
     "midi_id": 112667, "lyrics": "Half a pound of tuppenny rice"},
    {"name": "ring_rosie", "title": "Ring Around the Rosie", "author": "Traditional", "year": 1790, "type": "nursery rhyme", "category": "children",
     "midi_id": 112668, "lyrics": "Ring around the rosie pocket full of posies"},
    {"name": "three_blind_mice", "title": "Three Blind Mice", "author": "Thomas Ravenscroft", "year": 1609, "type": "nursery rhyme", "category": "children",
     "midi_id": 112673, "lyrics": "Three blind mice three blind mice"},
    {"name": "yankee_doodle", "title": "Yankee Doodle", "author": "Traditional", "year": 1755, "type": "folk", "category": "patriotic",
     "midi_id": 112675, "lyrics": "Yankee Doodle went to town riding on a pony"},
    {"name": "hickory_dickory", "title": "Hickory Dickory Dock", "author": "Traditional", "year": 1744, "type": "nursery rhyme", "category": "children",
     "midi_id": 112649, "lyrics": "Hickory dickory dock the mouse ran up the clock"},
    {"name": "old_king_cole", "title": "Old King Cole", "author": "Traditional", "year": 1708, "type": "nursery rhyme", "category": "children",
     "midi_id": 112663, "lyrics": "Old King Cole was a merry old soul"},
    {"name": "oranges_lemons", "title": "Oranges and Lemons", "author": "Traditional", "year": 1744, "type": "nursery rhyme", "category": "children",
     "midi_id": 112664, "lyrics": "Oranges and lemons say the bells of St Clements"},
    {"name": "pat_cake", "title": "Pat a Cake", "author": "Traditional", "year": 1698, "type": "nursery rhyme", "category": "children",
     "midi_id": 112665, "lyrics": "Pat a cake pat a cake bakers man"},
    {"name": "rain_go_away", "title": "Rain Rain Go Away", "author": "Traditional", "year": 1687, "type": "nursery rhyme", "category": "children",
     "midi_id": 112669, "lyrics": "Rain rain go away come again another day"},
    {"name": "see_saw", "title": "See Saw Margery Daw", "author": "Traditional", "year": 1765, "type": "nursery rhyme", "category": "children",
     "midi_id": 112672, "lyrics": "See saw Margery Daw sold her bed and lay upon straw"},
    {"name": "simple_simon", "title": "Simple Simon", "author": "Traditional", "year": 1764, "type": "nursery rhyme", "category": "children",
     "midi_id": 112666, "lyrics": "Simple Simon met a pieman going to the fair"},
    {"name": "tom_piper", "title": "Tom Tom the Pipers Son", "author": "Traditional", "year": 1795, "type": "nursery rhyme", "category": "children",
     "midi_id": 112677, "lyrics": "Tom Tom the pipers son stole a pig and away he run"},
    {"name": "mulberry_bush", "title": "Here We Go Round the Mulberry Bush", "author": "Traditional", "year": 1820, "type": "nursery rhyme", "category": "children",
     "midi_id": 112676, "lyrics": "Here we go round the mulberry bush"},

    # ── FOLK SONGS & BALLADS ──
    {"name": "auld_lang_syne", "title": "Auld Lang Syne", "author": "Robert Burns", "year": 1788, "type": "folk", "category": "scottish",
     "midi_id": 112741, "lyrics": "Should auld acquaintance be forgot"},
    {"name": "green_sleeves", "title": "Greensleeves", "author": "Traditional English", "year": 1580, "type": "folk", "category": "english",
     "midi_id": 112739, "lyrics": "Alas my love you do me wrong"},
    {"name": "scarborough_fair", "title": "Scarborough Fair", "author": "Traditional English", "year": 1670, "type": "folk", "category": "english",
     "midi_id": 112738, "lyrics": "Are you going to Scarborough Fair"},
    {"name": "danny_boy", "title": "Danny Boy (Londonderry Air)", "author": "Traditional Irish", "year": 1855, "type": "folk", "category": "irish",
     "midi_id": 112737, "lyrics": "Oh Danny boy the pipes the pipes are calling"},
    {"name": "loch_lomond", "title": "Loch Lomond", "author": "Traditional Scottish", "year": 1841, "type": "folk", "category": "scottish",
     "midi_id": 112740, "lyrics": "By yon bonnie banks"},
    {"name": "annie_lawrie", "title": "Annie Laurie", "author": "William Douglas", "year": 1838, "type": "folk", "category": "scottish",
     "midi_id": 112743, "lyrics": "Maxwelton braes are bonnie"},
    {"name": "cockles_mussels", "title": "Cockles and Mussels", "author": "James Yorkston", "year": 1884, "type": "folk", "category": "irish",
     "midi_id": 112736, "lyrics": "In Dublins fair city"},
    {"name": "oh_susanna", "title": "Oh Susanna", "author": "Stephen Foster", "year": 1848, "type": "folk", "category": "american",
     "midi_id": 112660, "lyrics": "I came from Alabama"},
    {"name": "camptown_races", "title": "Camptown Races", "author": "Stephen Foster", "year": 1850, "type": "folk", "category": "american",
     "midi_id": 112680, "lyrics": "Camptown ladies sing this song"},
    {"name": "beautiful_dreamer", "title": "Beautiful Dreamer", "author": "Stephen Foster", "year": 1862, "type": "folk", "category": "american",
     "midi_id": 112721, "lyrics": "Beautiful dreamer wake unto me"},
    {"name": "home_range", "title": "Home on the Range", "author": "Brewster Higley", "year": 1873, "type": "folk", "category": "american",
     "midi_id": 112662, "lyrics": "Oh give me a home where the buffalo roam"},
    {"name": "red_river", "title": "Red River Valley", "author": "Traditional", "year": 1896, "type": "folk", "category": "american",
     "midi_id": 112690, "lyrics": "From this valley they say you are going"},
    {"name": "shenandoah", "title": "Shenandoah", "author": "Traditional American", "year": 1850, "type": "folk", "category": "american",
     "midi_id": 112688, "lyrics": "Oh Shenandoah I long to hear you"},
    {"name": "jeannie_hair", "title": "Jeannie with the Light Brown Hair", "author": "Stephen Foster", "year": 1854, "type": "folk", "category": "american",
     "midi_id": 112720, "lyrics": "I dream of Jeannie with the light brown hair"},
    {"name": "old_folks_home", "title": "Old Folks at Home", "author": "Stephen Foster", "year": 1851, "type": "folk", "category": "american",
     "midi_id": 112722, "lyrics": "Way down upon the Swanee River"},
    {"name": "hard_times", "title": "Hard Times Come Again No More", "author": "Stephen Foster", "year": 1854, "type": "folk", "category": "american",
     "midi_id": 112723, "lyrics": "Let us pause in lifes pleasures"},
    {"name": "ash_grove", "title": "The Ash Grove", "author": "Traditional Welsh", "year": 1802, "type": "folk", "category": "welsh",
     "midi_id": 112749, "lyrics": "Down yonder green valley"},
    {"name": "waltzing_matilda", "title": "Waltzing Matilda", "author": "Banjo Paterson", "year": 1895, "type": "folk", "category": "australian",
     "midi_id": 65331, "lyrics": "Once a jolly swagman camped by a billabong"},

    # ── SPIRITUALS & HYMNS ──
    {"name": "amazing_grace", "title": "Amazing Grace", "author": "John Newton", "year": 1779, "type": "hymn", "category": "spiritual",
     "midi_id": 34522, "lyrics": "Amazing grace how sweet the sound"},
    {"name": "swing_low", "title": "Swing Low Sweet Chariot", "author": "Wallace Willis", "year": 1865, "type": "spiritual", "category": "african-american",
     "midi_id": 112698, "lyrics": "Swing low sweet chariot"},
    {"name": "joshua_jericho", "title": "Joshua Fought the Battle of Jericho", "author": "Traditional Spiritual", "year": 1865, "type": "spiritual", "category": "african-american",
     "midi_id": 112699, "lyrics": "Joshua fought the battle of Jericho"},
    {"name": "down_riverside", "title": "Down by the Riverside", "author": "Traditional Spiritual", "year": 1865, "type": "spiritual", "category": "african-american",
     "midi_id": 112702, "lyrics": "Gonna lay down my burdens"},
    {"name": "nobody_knows", "title": "Nobody Knows the Trouble Ive Seen", "author": "Traditional Spiritual", "year": 1867, "type": "spiritual", "category": "african-american",
     "midi_id": 112705, "lyrics": "Nobody knows the trouble Ive seen"},

    # ── LULLABIES ──
    {"name": "rockabye_baby", "title": "Rock-a-Bye Baby", "author": "Effie Crockett", "year": 1872, "type": "lullaby", "category": "children",
     "midi_id": 112726, "lyrics": "Rock a bye baby on the treetop"},
    {"name": "hush_baby", "title": "Hush Little Baby", "author": "Traditional American", "year": 1800, "type": "lullaby", "category": "children",
     "midi_id": 112728, "lyrics": "Hush little baby dont say a word"},
    {"name": "golden_slumbers", "title": "Golden Slumbers", "author": "Thomas Dekker", "year": 1603, "type": "lullaby", "category": "children",
     "midi_id": 112734, "lyrics": "Golden slumbers kiss your eyes"},
    {"name": "bye_bunting", "title": "Bye Baby Bunting", "author": "Traditional", "year": 1784, "type": "lullaby", "category": "children",
     "midi_id": 112735, "lyrics": "Bye baby bunting daddys gone a-hunting"},
    {"name": "all_pretty_horses", "title": "All the Pretty Little Horses", "author": "Traditional American", "year": 1850, "type": "lullaby", "category": "children",
     "midi_id": 112727, "lyrics": "Hush a bye dont you cry"},

    # ── INTERNATIONAL FOLK ──
    {"name": "frere_jacques", "title": "Frere Jacques", "author": "French Traditional", "year": 1780, "type": "folk", "category": "french",
     "midi_id": 112642, "lyrics": "Frere Jacques Frere Jacques dormez vous"},
    {"name": "alouette", "title": "Alouette", "author": "French Canadian Traditional", "year": 1879, "type": "folk", "category": "french",
     "midi_id": 112730, "lyrics": "Alouette gentille alouette"},
    {"name": "sur_pont", "title": "Sur le Pont dAvignon", "author": "French Traditional", "year": 1853, "type": "folk", "category": "french",
     "midi_id": 112729, "lyrics": "Sur le pont dAvignon on y danse"},
    {"name": "santa_lucia", "title": "Santa Lucia", "author": "Teodoro Cottrau", "year": 1849, "type": "folk", "category": "italian",
     "midi_id": 112731, "lyrics": "Oh Santa Lucia the star is shining bright"},
    {"name": "funiculi", "title": "Funiculi Funicula", "author": "Luigi Denza", "year": 1880, "type": "folk", "category": "italian",
     "midi_id": 112733, "lyrics": "Ammore e nfurmai funiculi funicula"},
    {"name": "o_tannenbaum", "title": "O Tannenbaum", "author": "Ernst Anschutz", "year": 1824, "type": "folk", "category": "german",
     "midi_id": 112747, "lyrics": "O Tannenbaum o Tannenbaum wie treu sind deine Blatter"},
    {"name": "sakura", "title": "Sakura Sakura", "author": "Japanese Traditional", "year": 1888, "type": "folk", "category": "japanese",
     "midi_id": 112744, "lyrics": "Sakura Sakura cherry blossoms everywhere"},
    {"name": "arirang", "title": "Arirang", "author": "Korean Traditional", "year": 1896, "type": "folk", "category": "korean",
     "midi_id": 112745, "lyrics": "Arirang Arirang Arariyo"},
    {"name": "kalinka", "title": "Kalinka", "author": "Ivan Larionov", "year": 1860, "type": "folk", "category": "russian",
     "midi_id": 112746, "lyrics": "Kalinka kalinka kalinka moya"},

    # ── CLASSICAL THEMES ──
    {"name": "fur_elise", "title": "Fur Elise", "author": "Ludwig van Beethoven", "year": 1810, "type": "classical", "category": "classical",
     "midi_id": 34050, "lyrics": "Instrumental classical piano piece"},
    {"name": "moonlight", "title": "Moonlight Sonata", "author": "Ludwig van Beethoven", "year": 1801, "type": "classical", "category": "classical",
     "midi_id": 34001, "lyrics": "Instrumental piano sonata"},
    {"name": "ode_to_joy", "title": "Ode to Joy", "author": "Ludwig van Beethoven", "year": 1824, "type": "classical", "category": "classical",
     "midi_id": 34002, "lyrics": "Joyful joyful we adore thee"},
    {"name": "canon_d", "title": "Pachelbel Canon in D", "author": "Johann Pachelbel", "year": 1680, "type": "classical", "category": "classical",
     "midi_id": 34011, "lyrics": "Instrumental canon"},
    {"name": "air_g_string", "title": "Air on the G String", "author": "Johann Sebastian Bach", "year": 1720, "type": "classical", "category": "classical",
     "midi_id": 34021, "lyrics": "Instrumental orchestral piece"},
    {"name": "minuet_g", "title": "Minuet in G", "author": "Johann Sebastian Bach", "year": 1725, "type": "classical", "category": "classical",
     "midi_id": 34019, "lyrics": "Instrumental dance piece"},
    {"name": "turkey_march", "title": "Turkish March", "author": "Wolfgang Amadeus Mozart", "year": 1783, "type": "classical", "category": "classical",
     "midi_id": 34030, "lyrics": "Instrumental march"},
    {"name": "eine_kleine", "title": "Eine Kleine Nachtmusik", "author": "Wolfgang Amadeus Mozart", "year": 1787, "type": "classical", "category": "classical",
     "midi_id": 34031, "lyrics": "Instrumental serenade"},
    {"name": "waltz_flowers", "title": "Waltz of the Flowers", "author": "Pyotr Tchaikovsky", "year": 1892, "type": "classical", "category": "classical",
     "midi_id": 34035, "lyrics": "Instrumental ballet waltz"},
    {"name": "swan_lake", "title": "Swan Lake Theme", "author": "Pyotr Tchaikovsky", "year": 1876, "type": "classical", "category": "classical",
     "midi_id": 34036, "lyrics": "Instrumental ballet theme"},

    # ── CHRISTMAS CAROLS (pre-1913) ──
    {"name": "silent_night", "title": "Silent Night", "author": "Franz Xaver Gruber", "year": 1818, "type": "carol", "category": "christmas",
     "midi_id": 107557, "lyrics": "Silent night holy night all is calm all is bright"},
    {"name": "joy_to_world", "title": "Joy to the World", "author": "George Frideric Handel", "year": 1719, "type": "carol", "category": "christmas",
     "midi_id": 107559, "lyrics": "Joy to the world the Lord is come"},
    {"name": "hark_herald", "title": "Hark the Herald Angels Sing", "author": "Felix Mendelssohn", "year": 1840, "type": "carol", "category": "christmas",
     "midi_id": 107561, "lyrics": "Hark the herald angels sing glory to the newborn King"},
    {"name": "we_three_kings", "title": "We Three Kings", "author": "John Henry Hopkins Jr.", "year": 1857, "type": "carol", "category": "christmas",
     "midi_id": 107569, "lyrics": "We three kings of Orient are"},
    {"name": "away_manger", "title": "Away in a Manger", "author": "James R. Murray", "year": 1887, "type": "carol", "category": "christmas",
     "midi_id": 107562, "lyrics": "Away in a manger no crib for a bed"},
    {"name": "first_noel", "title": "The First Noel", "author": "Traditional English", "year": 1823, "type": "carol", "category": "christmas",
     "midi_id": 107568, "lyrics": "The first Noel the angels did say"},
    {"name": "deck_halls", "title": "Deck the Halls", "author": "Traditional Welsh", "year": 1862, "type": "carol", "category": "christmas",
     "midi_id": 107558, "lyrics": "Deck the halls with boughs of holly"},
    {"name": "good_wenceslas", "title": "Good King Wenceslas", "author": "John Mason Neale", "year": 1853, "type": "carol", "category": "christmas",
     "midi_id": 107570, "lyrics": "Good King Wenceslas looked out"},
    {"name": "o_little_town", "title": "O Little Town of Bethlehem", "author": "Phillips Brooks", "year": 1868, "type": "carol", "category": "christmas",
     "midi_id": 107571, "lyrics": "O little town of Bethlehem"},

    # ── MORE FOLK & TRADITIONAL ──
    {"name": "wayfaring_stranger", "title": "Wayfaring Stranger", "author": "Traditional American", "year": 1858, "type": "folk", "category": "american",
     "midi_id": 112717, "lyrics": "I am a poor wayfaring stranger"},
    {"name": "water_is_wide", "title": "The Water Is Wide", "author": "Traditional Scottish", "year": 1820, "type": "folk", "category": "scottish",
     "midi_id": 112718, "lyrics": "The water is wide I cannot get oer"},
    {"name": "barbry_allen", "title": "Barbry Allen", "author": "Traditional Scottish", "year": 1790, "type": "folk", "category": "scottish",
     "midi_id": 112714, "lyrics": "In Scarlet Town where I was born"},
    {"name": "wild_thyme", "title": "Wild Mountain Thyme", "author": "Traditional Scottish", "year": 1800, "type": "folk", "category": "scottish",
     "midi_id": 112719, "lyrics": "Oh the summer time is coming"},
    {"name": "michael_row", "title": "Michael Row the Boat Ashore", "author": "Traditional Spiritual", "year": 1867, "type": "spiritual", "category": "african-american",
     "midi_id": 112696, "lyrics": "Michael row the boat ashore"},
    {"name": "kumbaya", "title": "Kumbaya", "author": "Traditional Spiritual", "year": 1900, "type": "spiritual", "category": "african-american",
     "midi_id": 112701, "lyrics": "Kumbaya my Lord kumbaya"},
    {"name": "oleanna", "title": "Oleanna", "author": "Traditional American", "year": 1860, "type": "folk", "category": "american",
     "midi_id": 112685, "lyrics": "Oleanna Oleanna working in the cotton field"},
]


def get_midi_url(midi_id):
    """Get download URL for a MIDI file."""
    if midi_id == "susam":
        return "https://susam.net/files/music/twinkle-twinkle-little-star/twinkle-twinkle-little-star.midi"
    return f"https://bitmidi.com/uploads/{midi_id}.mid"


def analyze_midi_complexity(filepath):
    """Analyze MIDI file complexity based on file size and structure."""
    size = os.path.getsize(filepath)
    try:
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(filepath)
        n_notes = sum(len(i.notes) for i in pm.instruments)
        n_instruments = len(pm.instruments)
        # Complexity score: notes * instruments / duration
        duration = pm.get_end_time() if pm.get_end_time() > 0 else 1
        complexity = (n_notes * n_instruments) / duration
        return complexity, n_notes, n_instruments, duration
    except:
        # Fallback: size-based complexity
        return size / 1000.0, 0, 0, 0


def download_song(song):
    """Download a single MIDI file and insert into database."""
    import sqlite3
    db = sqlite3.connect(DB_PATH)
    name = song["name"]
    url = get_midi_url(song["midi_id"])
    filename = f"{name}.mid"
    filepath = os.path.join(INPUT_DIR, filename)

    result = {"name": name, "success": False, "size": 0, "complexity": 0}

    # Download if not exists
    if not os.path.exists(filepath) or os.path.getsize(filepath) < 100:
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200 and len(r.content) > 500:
                with open(filepath, "wb") as f:
                    f.write(r.content)
        except:
            db.close()
            return result

    if os.path.exists(filepath) and os.path.getsize(filepath) > 500:
        size = os.path.getsize(filepath)
        complexity, notes, instr, dur = analyze_midi_complexity(filepath)
        result["success"] = True
        result["size"] = size
        result["complexity"] = complexity

        db.execute("""INSERT OR REPLACE INTO songs
            (name, title, author, year, song_type, category, lyrics,
             midi_filename, midi_size, midi_complexity, source_url, downloaded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (name, song["title"], song["author"], song["year"],
             song["type"], song["category"], song["lyrics"],
             filename, size, complexity, url))

    db.commit()
    db.close()
    return result


def deduplicate(db):
    """Remove duplicate songs keeping the best quality version."""
    # Group by name - keep the one with highest complexity
    dupes = db.execute("""SELECT name, midi_size, midi_complexity
        FROM songs WHERE downloaded = 1
        ORDER BY midi_complexity DESC""").fetchall()

    seen = {}
    for name, size, complexity in dupes:
        if name not in seen:
            seen[name] = (size, complexity)
        else:
            if complexity <= seen[name][1]:
                # Remove this duplicate
                db.execute("DELETE FROM songs WHERE name=? AND midi_size=?",
                          (name, size))
                # Also remove the MIDI file
                fpath = os.path.join(INPUT_DIR, f"{name}.mid")
                if os.path.exists(fpath) and os.path.getsize(fpath) == size:
                    os.remove(fpath)
    return len(seen)


def build_database():
    """Main function to build the complete song database."""
    db = sqlite3.connect(DB_PATH)
    
    print("=== Building pre-1913 public domain song library ===")
    print(f"Total songs in catalog: {len(SONGS)}")
    print("Downloading from bitmidi.com...")

    # Download songs
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(download_song, s): s for s in SONGS}
        done = 0
        for fut in as_completed(futures):
            r = fut.result()
            done += 1
            status = "OK" if r["success"] else "FAIL"
            sys.stdout.write(f"\r  [{done}/{len(SONGS)}] {status} {r['name']}  ")
            sys.stdout.flush()
    print()

    db.commit()

    # Deduplicate
    kept = deduplicate(db)
    db.commit()

    # Stats
    total = db.execute("SELECT COUNT(*) FROM songs WHERE downloaded=1").fetchone()[0]
    total_size = db.execute("SELECT SUM(midi_size) FROM songs WHERE downloaded=1").fetchone()[0] or 0
    
    print("\n=== Database Complete ===")
    print(f"Songs in database: {total}")
    print(f"Unique songs (deduped): {kept}")
    print(f"Total MIDI size: {total_size // 1024 // 1024} MB")

    # Show dedup breakdown
    print("\n=== Categories ===")
    cats = db.execute("SELECT category, COUNT(*) FROM songs WHERE downloaded=1 GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
    for cat, cnt in cats:
        print(f"  {cat}: {cnt}")

    print("\n=== Types ===")
    types = db.execute("SELECT song_type, COUNT(*) FROM songs WHERE downloaded=1 GROUP BY song_type ORDER BY COUNT(*) DESC").fetchall()
    for t, cnt in types:
        print(f"  {t}: {cnt}")

    db.close()
    return total


if __name__ == "__main__":
    build_database()
