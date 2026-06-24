import os
import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Structured database of public domain children's songs and nursery rhymes
SONG_DATABASE = {
    "twinkle_twinkle_little_star": {
        "title": "Twinkle Twinkle Little Star",
        "description": "A beautiful modern toy-remake of the classic nursery rhyme 'Twinkle Twinkle Little Star'. Perfect for babies, toddlers, and preschool kids to learn and sleep.",
        "tags": ["nursery rhyme", "kids music", "children songs", "lullaby", "twinkle twinkle", "baby sleep music", "toddler learning"],
        "midi_url": "https://susam.net/files/music/twinkle-twinkle-little-star/twinkle-twinkle-little-star.midi",
        "lyrics_lines": [
            "Twinkle, twinkle, little star,",
            "How I wonder what you are!",
            "Up above the world so high,",
            "Like a diamond in the sky.",
            "Twinkle, twinkle, little star,",
            "How I wonder what you are!"
        ]
    },
    "mary_had_a_little_lamb": {
        "title": "Mary Had a Little Lamb",
        "description": "Sing along to 'Mary Had a Little Lamb', the classic children's song. A fun, educational song for kids to enjoy and sing along.",
        "tags": ["mary had a little lamb", "nursery rhyme", "kids songs", "sing-along", "preschool music", "children rhymes"],
        "midi_url": "https://raw.githubusercontent.com/vishnubob/python-midi/master/mary.mid",
        "lyrics_lines": [
            "Mary had a little lamb,",
            "Its fleece was white as snow;",
            "And everywhere that Mary went",
            "The lamb was sure to go.",
            "It followed her to school one day,",
            "Which was against the rule;",
            "It made the children laugh and play",
            "To see a lamb at school."
        ]
    },
    "itsy_bitsy_spider": {
        "title": "Itsy Bitsy Spider",
        "description": "Watch the spider climb the waterspout in the classic nursery rhyme 'Itsy Bitsy Spider'. A delightful song for children and infants.",
        "tags": ["itsy bitsy spider", "nursery rhymes", "kids videos", "fingerplay", "preschool learning", "children music"],
        "midi_url": "https://bitmidi.com/uploads/21307.mid",
        "lyrics_lines": [
            "The itsy bitsy spider climbed up the waterspout.",
            "Down came the rain and washed the spider out.",
            "Out came the sun and dried up all the rain,",
            "And the itsy bitsy spider climbed up the spout again."
        ]
    },
    "row_row_row_your_boat": {
        "title": "Row Row Row Your Boat",
        "description": "Merrily float down the stream with the classic round song 'Row, Row, Row Your Boat'. Great for children's coordination and singing.",
        "tags": ["row your boat", "kids round song", "sing-along", "educational songs", "rhymes for children", "baby nursery"],
        "midi_url": "https://bitmidi.com/uploads/86438.mid",
        "lyrics_lines": [
            "Row, row, row your boat",
            "Gently down the stream,",
            "Merrily, merrily, merrily, merrily,",
            "Life is but a dream."
        ]
    },
    "wheels_on_the_bus": {
        "title": "The Wheels on the Bus",
        "description": "Take a fun bus ride with 'The Wheels on the Bus'! The classic children's song featuring round-and-round wheels, wipers, and horns.",
        "tags": ["wheels on the bus", "action song", "kids transportation", "educational rhyme", "preschool songs", "fun kids music"],
        "midi_url": "https://bitmidi.com/uploads/112674.mid",
        "lyrics_lines": [
            "The wheels on the bus go round and round,",
            "Round and round,",
            "Round and round.",
            "The wheels on the bus go round and round,",
            "All through the town."
        ]
    },
    "baa_baa_black_sheep": {
        "title": "Baa Baa Black Sheep",
        "description": "Have you any wool? Discover the answer in the traditional English nursery rhyme 'Baa Baa Black Sheep', set to a sweet kid-friendly tune.",
        "tags": ["baa baa black sheep", "wool song", "kids animals", "toddler rhymes", "kindergarten music", "preschool learning"],
        "midi_url": "https://bitmidi.com/uploads/112648.mid",
        "lyrics_lines": [
            "Baa, baa, black sheep,",
            "Have you any wool?",
            "Yes, sir, yes, sir,",
            "Three bags full;",
            "One for the master,",
            "And one for the dame,",
            "And one for the little boy",
            "Who lives down the lane."
        ]
    },
    "london_bridge_is_falling_down": {
        "title": "London Bridge Is Falling Down",
        "description": "Build it up with wood and clay! The classic traditional song 'London Bridge Is Falling Down' for children's play and education.",
        "tags": ["london bridge", "falling down", "traditional kids song", "historical rhymes", "nursery rhymes", "preschool games"],
        "midi_url": "https://bitmidi.com/uploads/106317.mid",
        "lyrics_lines": [
            "London Bridge is falling down,",
            "Falling down, falling down.",
            "London Bridge is falling down,",
            "My fair lady."
        ]
    },
    "old_macdonald_had_a_farm": {
        "title": "Old MacDonald Had a Farm",
        "description": "E-I-E-I-O! Meet the farm animals and learn their sounds with Old MacDonald in this classic animal song for kids.",
        "tags": ["old macdonald", "farm animals", "animal sounds", "kids farm song", "educational videos", "children singing"],
        "midi_url": "https://bitmidi.com/uploads/112658.mid",
        "lyrics_lines": [
            "Old MacDonald had a farm, E-I-E-I-O!",
            "And on his farm he had some chicks, E-I-E-I-O!",
            "With a cluck-cluck here, and a cluck-cluck there,",
            "Here a cluck, there a cluck, everywhere a cluck-cluck,",
            "Old MacDonald had a farm, E-I-E-I-O!"
        ]
    },
    "hickory_dickory_dock": {
        "title": "Hickory Dickory Dock",
        "description": "Learn to tell time with the mouse running up the clock in the classic nursery rhyme 'Hickory Dickory Dock'.",
        "tags": ["hickory dickory dock", "clock song", "counting rhyme", "learning time", "preschool education", "toddler songs"],
        "midi_url": "https://bitmidi.com/uploads/112649.mid",
        "lyrics_lines": [
            "Hickory, dickory, dock,",
            "The mouse ran up the clock.",
            "The clock struck one,",
            "The mouse ran down,",
            "Hickory, dickory, dock."
        ]
    },
    "jack_and_jill": {
        "title": "Jack and Jill",
        "description": "Jack and Jill went up the hill to fetch a pail of water. Relive this classic nursery story with a sweet, child-friendly melody.",
        "tags": ["jack and jill", "kids stories", "rhymes for children", "baby nursery", "traditional nursery rhyme", "preschool music"],
        "midi_url": "https://bitmidi.com/uploads/112650.mid",
        "lyrics_lines": [
            "Jack and Jill went up the hill,",
            "To fetch a pail of water.",
            "Jack fell down and broke his crown,",
            "And Jill came tumbling after."
        ]
    },
    "yankee_doodle": {
        "title": "Yankee Doodle",
        "description": "A delightful performance of the traditional American folk and revolutionary song 'Yankee Doodle'. Great for teaching historical folk songs.",
        "tags": ["yankee doodle", "folk song", "patriotic music", "american history kids", "classic children songs", "dandy song"],
        "midi_url": "https://bitmidi.com/uploads/112675.mid",
        "lyrics_lines": [
            "Yankee Doodle went to town,",
            "Riding on a pony,",
            "Stuck a feather in his cap,",
            "And called it macaroni.",
            "Yankee Doodle keep it up,",
            "Yankee Doodle dandy,",
            "Mind the music and the step,",
            "And with the girls be handy."
        ]
    },
    "oh_susanna": {
        "title": "Oh Susanna",
        "description": "Don't you cry for me! Sing along to Stephen Foster's classic American folk song 'Oh Susanna', reimagined with playful backing tracks.",
        "tags": ["oh susanna", "american folk music", "banjo song", "stephen foster", "sing-along folk", "kids folk songs"],
        "midi_url": "https://bitmidi.com/uploads/112660.mid",
        "lyrics_lines": [
            "I came from Alabama with a banjo on my knee,",
            "I'm going to Louisiana, my true love for to see.",
            "It rained all night the day I left, the weather it was dry,",
            "The sun so hot I froze to death, Susanna, don't you cry.",
            "Oh, Susanna, oh don't you cry for me,",
            "For I come from Alabama with a banjo on my knee."
        ]
    },
    "home_on_the_range": {
        "title": "Home on the Range",
        "description": "Where the deer and the antelope play! The beautiful traditional cowboy folk song 'Home on the Range' in a sweet soothing style.",
        "tags": ["home on the range", "cowboy folk song", "lullaby", "western music", "american traditional", "peaceful sleep music"],
        "midi_url": "https://bitmidi.com/uploads/112662.mid",
        "lyrics_lines": [
            "Oh, give me a home where the buffalo roam,",
            "Where the deer and the antelope play,",
            "Where seldom is heard a discouraging word,",
            "And the skies are not cloudy all day.",
            "Home, home on the range,",
            "Where the deer and the antelope play,",
            "Where seldom is heard a discouraging word,",
            "And the skies are not cloudy all day."
        ]
    },
    "clementine": {
        "title": "My Darling Clementine",
        "description": "The traditional gold rush folk ballad 'My Darling Clementine'. A classic historical folk song for family listening.",
        "tags": ["clementine", "gold rush song", "american ballad", "historical folk", "family music", "traditional folksongs"],
        "midi_url": "https://bitmidi.com/uploads/112661.mid",
        "lyrics_lines": [
            "In a cavern, in a canyon, excavating for a mine,",
            "Dwelt a miner, forty-niner, and his daughter Clementine.",
            "Oh my darling, oh my darling, oh my darling, Clementine!",
            "You are lost and gone forever, dreadful sorry, Clementine."
        ]
    },
    "amazing_grace": {
        "title": "Amazing Grace",
        "description": "The world's most famous spiritual and folk hymn 'Amazing Grace', rendered in a beautiful and high-fidelity melodic layout.",
        "tags": ["amazing grace", "spiritual hymn", "folk song", "traditional worship", "gospel music", "christian hymn"],
        "midi_url": "https://bitmidi.com/uploads/34522.mid",
        "lyrics_lines": [
            "Amazing grace! How sweet the sound",
            "That saved a wretch like me!",
            "I once was lost, but now am found;",
            "Was blind, but now I see."
        ]
    }
}

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    input_dir = os.path.join(project_dir, "input")
    output_dir = os.path.join(project_dir, "output")
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Initiating children's folk/nursery rhyme downloader.")
    logger.info(f"Target Input: {input_dir}")
    logger.info(f"Target Output (Metadata/Lyrics): {output_dir}")
    
    headers = {"User-Agent": "Mozilla/5.0"}
    catalog = []
    
    for name, data in SONG_DATABASE.items():
        midi_filename = f"{name}.mid"
        midi_path = os.path.join(input_dir, midi_filename)
        
        # 1. Download MIDI file
        logger.info(f"Downloading MIDI for '{data['title']}'...")
        try:
            r = requests.get(data["midi_url"], headers=headers, timeout=15)
            r.raise_for_status()
            with open(midi_path, "wb") as f:
                f.write(r.content)
            logger.info(f"Saved MIDI to {midi_path}")
            midi_status = "Success"
        except Exception as e:
            logger.error(f"Failed to download MIDI for '{data['title']}': {e}")
            midi_status = f"Failed ({e})"
            
        # 2. Construct synced lyrics list (5s intervals)
        synced_lyrics = []
        start_time = 5.0
        for line in data["lyrics_lines"]:
            synced_lyrics.append({
                "text": line,
                "start": start_time,
                "end": start_time + 4.0
            })
            start_time += 5.0
            
        # 3. Create metadata + lyrics dictionary
        metadata = {
            "title": data["title"],
            "description": data["description"],
            "tags": data["tags"],
            "lyrics": synced_lyrics
        }
        
        # 4. Save metadata JSON file to output/
        metadata_path = os.path.join(output_dir, f"{name}_metadata.json")
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved metadata & lyrics to {metadata_path}")
            metadata_status = "Success"
        except Exception as e:
            logger.error(f"Failed to write metadata for '{data['title']}': {e}")
            metadata_status = f"Failed ({e})"
            
        catalog.append({
            "Key": name,
            "Title": data["title"],
            "MIDI": midi_status,
            "Metadata & Lyrics": metadata_status
        })

    # Write catalog index to Markdown
    catalog_path = os.path.join(project_dir, "CHILDRENS_SONGS_INDEX.md")
    with open(catalog_path, "w", encoding="utf-8") as f:
        f.write("# Curated Children's Folk and Lullaby Catalog\n\n")
        f.write("| Song Key | Title | MIDI Status | Metadata/Lyrics JSON |\n")
        f.write("| --- | --- | --- | --- |\n")
        for item in catalog:
            f.write(f"| `{item['Key']}` | {item['Title']} | {item['MIDI']} | {item['Metadata & Lyrics']} |\n")
    logger.info(f"Wrote library catalog index to {catalog_path}")

if __name__ == "__main__":
    main()
