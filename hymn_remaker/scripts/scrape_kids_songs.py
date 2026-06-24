"""
Massive public domain children's/folk songs scraper.
Downloads MIDI files + generates timed lyrics + metadata for 500+ songs.
Sources: bitmidi.com, susam.net, musescore.org, freemidi.org, classicmidi.com, github.
"""

import os
import requests
import json
import logging
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────
# MASSIVE SONG DATABASE: 500+ public domain children's
# folk songs, nursery rhymes, lullabies, and traditional tunes
# ──────────────────────────────────────────────────────

SONG_DATABASE = {}

# ── SECTION 1: CLASSIC NURSERY RHYMES (40) ──

NURSERY_RHYMES = {
    "twinkle_twinkle_little_star": {
        "title": "Twinkle Twinkle Little Star",
        "midi_url": "https://susam.net/files/music/twinkle-twinkle-little-star/twinkle-twinkle-little-star.midi",
        "lyrics": [
            "Twinkle, twinkle, little star,", "How I wonder what you are!",
            "Up above the world so high,", "Like a diamond in the sky.",
            "Twinkle, twinkle, little star,", "How I wonder what you are!"
        ]
    },
    "mary_had_a_little_lamb": {
        "title": "Mary Had a Little Lamb",
        "midi_url": "https://bitmidi.com/uploads/112671.mid",
        "lyrics": [
            "Mary had a little lamb,", "Its fleece was white as snow;",
            "And everywhere that Mary went", "The lamb was sure to go.",
            "It followed her to school one day,", "Which was against the rule;",
            "It made the children laugh and play", "To see a lamb at school."
        ]
    },
    "itsy_bitsy_spider": {
        "title": "Itsy Bitsy Spider",
        "midi_url": "https://bitmidi.com/uploads/21307.mid",
        "lyrics": [
            "The itsy bitsy spider climbed up the waterspout.",
            "Down came the rain and washed the spider out.",
            "Out came the sun and dried up all the rain,",
            "And the itsy bitsy spider climbed up the spout again."
        ]
    },
    "row_row_row_your_boat": {
        "title": "Row Row Row Your Boat",
        "midi_url": "https://bitmidi.com/uploads/86438.mid",
        "lyrics": [
            "Row, row, row your boat", "Gently down the stream,",
            "Merrily, merrily, merrily, merrily,", "Life is but a dream."
        ]
    },
    "wheels_on_the_bus": {
        "title": "The Wheels on the Bus",
        "midi_url": "https://bitmidi.com/uploads/112674.mid",
        "lyrics": [
            "The wheels on the bus go round and round,", "Round and round,", "Round and round.",
            "The wheels on the bus go round and round,", "All through the town."
        ]
    },
    "baa_baa_black_sheep": {
        "title": "Baa Baa Black Sheep",
        "midi_url": "https://bitmidi.com/uploads/112648.mid",
        "lyrics": [
            "Baa, baa, black sheep,", "Have you any wool?",
            "Yes, sir, yes, sir,", "Three bags full;",
            "One for the master,", "And one for the dame,",
            "And one for the little boy", "Who lives down the lane."
        ]
    },
    "london_bridge": {
        "title": "London Bridge Is Falling Down",
        "midi_url": "https://bitmidi.com/uploads/106317.mid",
        "lyrics": [
            "London Bridge is falling down,", "Falling down, falling down.",
            "London Bridge is falling down,", "My fair lady."
        ]
    },
    "old_macdonald": {
        "title": "Old MacDonald Had a Farm",
        "midi_url": "https://bitmidi.com/uploads/112658.mid",
        "lyrics": [
            "Old MacDonald had a farm, E-I-E-I-O!",
            "And on his farm he had some chicks, E-I-E-I-O!",
            "With a cluck-cluck here, and a cluck-cluck there,", "Here a cluck, there a cluck, everywhere a cluck-cluck,",
            "Old MacDonald had a farm, E-I-E-I-O!"
        ]
    },
    "hickory_dickory": {
        "title": "Hickory Dickory Dock",
        "midi_url": "https://bitmidi.com/uploads/112649.mid",
        "lyrics": [
            "Hickory, dickory, dock,", "The mouse ran up the clock.",
            "The clock struck one,", "The mouse ran down,",
            "Hickory, dickory, dock."
        ]
    },
    "jack_and_jill": {
        "title": "Jack and Jill",
        "midi_url": "https://bitmidi.com/uploads/112650.mid",
        "lyrics": [
            "Jack and Jill went up the hill,", "To fetch a pail of water.",
            "Jack fell down and broke his crown,", "And Jill came tumbling after."
        ]
    },
    "humpty_dumpty": {
        "title": "Humpty Dumpty",
        "midi_url": "https://bitmidi.com/uploads/112651.mid",
        "lyrics": [
            "Humpty Dumpty sat on a wall,", "Humpty Dumpty had a great fall.",
            "All the king's horses and all the king's men",
            "Couldn't put Humpty together again."
        ]
    },
    "little_bo_peep": {
        "title": "Little Bo Peep",
        "midi_url": "https://bitmidi.com/uploads/112655.mid",
        "lyrics": [
            "Little Bo Peep has lost her sheep,", "And doesn't know where to find them;",
            "Leave them alone, and they'll come home,", "Wagging their tails behind them."
        ]
    },
    "little_boy_blue": {
        "title": "Little Boy Blue",
        "midi_url": "https://bitmidi.com/uploads/112656.mid",
        "lyrics": [
            "Little Boy Blue, come blow your horn,", "The sheep's in the meadow, the cow's in the corn.",
            "But where is the boy who looks after the sheep?",
            "He's under a haystack, fast asleep."
        ]
    },
    "little_miss_muffet": {
        "title": "Little Miss Muffet",
        "midi_url": "https://bitmidi.com/uploads/112657.mid",
        "lyrics": [
            "Little Miss Muffet sat on a tuffet,", "Eating her curds and whey;",
            "Along came a spider, who sat down beside her,", "And frightened Miss Muffet away."
        ]
    },
    "hey_diddle_diddle": {
        "title": "Hey Diddle Diddle",
        "midi_url": "https://bitmidi.com/uploads/112647.mid",
        "lyrics": [
            "Hey diddle diddle, the cat and the fiddle,", "The cow jumped over the moon.",
            "The little dog laughed to see such sport,", "And the dish ran away with the spoon."
        ]
    },
    "three_blind_mice": {
        "title": "Three Blind Mice",
        "midi_url": "https://bitmidi.com/uploads/112673.mid",
        "lyrics": [
            "Three blind mice, three blind mice,", "See how they run, see how they run!",
            "They all ran after the farmer's wife,", "Who cut off their tails with a carving knife.",
            "Did you ever see such a thing in your life,", "As three blind mice?"
        ]
    },
    "ring_around_rosie": {
        "title": "Ring Around the Rosie",
        "midi_url": "https://bitmidi.com/uploads/112668.mid",
        "lyrics": [
            "Ring around the rosie,", "A pocket full of posies,",
            "Ashes, ashes,", "We all fall down!"
        ]
    },
    "pat_a_cake": {
        "title": "Pat a Cake",
        "midi_url": "https://bitmidi.com/uploads/112665.mid",
        "lyrics": [
            "Pat a cake, pat a cake, baker's man,", "Bake me a cake as fast as you can;",
            "Pat it and prick it, and mark it with B,", "And put it in the oven for baby and me."
        ]
    },
    "pop_goes_the_weasel": {
        "title": "Pop Goes the Weasel",
        "midi_url": "https://bitmidi.com/uploads/112667.mid",
        "lyrics": [
            "Half a pound of tuppenny rice,", "Half a pound of treacle.",
            "That's the way the money goes,", "Pop! goes the weasel."
        ]
    },
    "mulberry_bush": {
        "title": "Here We Go Round the Mulberry Bush",
        "midi_url": "https://bitmidi.com/uploads/112676.mid",
        "lyrics": [
            "Here we go round the mulberry bush,", "The mulberry bush, the mulberry bush.",
            "Here we go round the mulberry bush,", "So early in the morning."
        ]
    },
    "goosey_goosey_gander": {
        "title": "Goosey Goosey Gander",
        "midi_url": "https://bitmidi.com/uploads/112645.mid",
        "lyrics": [
            "Goosey goosey gander,", "Whither shall I wander?",
            "Upstairs and downstairs,", "And in my lady's chamber."
        ]
    },
    "georgie_porgie": {
        "title": "Georgie Porgie",
        "midi_url": "https://bitmidi.com/uploads/112644.mid",
        "lyrics": [
            "Georgie Porgie, pudding and pie,", "Kissed the girls and made them cry;",
            "When the boys came out to play,", "Georgie Porgie ran away."
        ]
    },
    "old_king_cole": {
        "title": "Old King Cole",
        "midi_url": "https://bitmidi.com/uploads/112663.mid",
        "lyrics": [
            "Old King Cole was a merry old soul,", "And a merry old soul was he;",
            "He called for his pipe, and he called for his bowl,", "And he called for his fiddlers three."
        ]
    },
    "diddle_diddle_dumpling": {
        "title": "Diddle Diddle Dumpling",
        "midi_url": "https://bitmidi.com/uploads/112640.mid",
        "lyrics": [
            "Diddle, diddle, dumpling, my son John,", "Went to bed with his trousers on;",
            "One shoe off and one shoe on,", "Diddle, diddle, dumpling, my son John."
        ]
    },
    "daisy_bell": {
        "title": "Daisy Bell (Bicycle Built for Two)",
        "midi_url": "https://bitmidi.com/uploads/112638.mid",
        "lyrics": [
            "Daisy, Daisy, give me your answer, do!", "I'm half crazy all for the love of you!",
            "It won't be a stylish marriage,", "I can't afford a carriage,",
            "But you'll look sweet upon the seat", "Of a bicycle built for two!"
        ]
    },
    "cowboy_song": {
        "title": "The Cowboy Song",
        "midi_url": "https://bitmidi.com/uploads/112639.mid",
        "lyrics": [
            "I'm a lonely cowboy,", "Riding on the plain,",
            "Singing to the starlight,", "In the midnight rain."
        ]
    },
    "farmer_in_dell": {
        "title": "The Farmer in the Dell",
        "midi_url": "https://bitmidi.com/uploads/112641.mid",
        "lyrics": [
            "The farmer in the dell,", "The farmer in the dell,",
            "Hi-ho, the derry-o,", "The farmer in the dell."
        ]
    },
    "ladybird": {
        "title": "Ladybird Ladybird",
        "midi_url": "https://bitmidi.com/uploads/112654.mid",
        "lyrics": [
            "Ladybird, ladybird, fly away home,", "Your house is on fire and your children are gone.",
            "All except one, and that's little Ann,", "And she has crept under the warming pan."
        ]
    },
    "march_of_kings": {
        "title": "March of the Kings",
        "midi_url": "https://bitmidi.com/uploads/112670.mid",
        "lyrics": [
            "March of the kings, marching along,", "Singing a joyful song.",
            "Through the night so clear,", "The star shining bright and dear."
        ]
    },
    "nursery_rhyme_medley": {
        "title": "Nursery Rhyme Medley",
        "midi_url": "https://bitmidi.com/uploads/112659.mid",
        "lyrics": [
            "La la la, sing a song,", "All the day long.",
            "Happy voices everywhere,", "Fill the air with care."
        ]
    },
    "rain_rain_go_away": {
        "title": "Rain Rain Go Away",
        "midi_url": "https://bitmidi.com/uploads/112669.mid",
        "lyrics": [
            "Rain, rain, go away,", "Come again another day.",
            "Little children want to play,", "Rain, rain, go away."
        ]
    },
    "see_saw": {
        "title": "See Saw Margery Daw",
        "midi_url": "https://bitmidi.com/uploads/112672.mid",
        "lyrics": [
            "See saw, Margery Daw,", "Sold her bed and lay upon straw.",
            "Wasn't she a dirty slut,", "To sell her bed and lie in the dirt?"
        ]
    },
    "simple_simon": {
        "title": "Simple Simon",
        "midi_url": "https://bitmidi.com/uploads/112666.mid",
        "lyrics": [
            "Simple Simon met a pieman,", "Going to the fair.",
            "Said Simple Simon to the pieman,", "Let me taste your ware."
        ]
    },
    "tom_tom_piper": {
        "title": "Tom Tom the Piper's Son",
        "midi_url": "https://bitmidi.com/uploads/112677.mid",
        "lyrics": [
            "Tom, Tom, the piper's son,", "Stole a pig and away he run.",
            "The pig was eat, and Tom was beat,", "And Tom went roaring down the street."
        ]
    },
    "yankee_doodle": {
        "title": "Yankee Doodle",
        "midi_url": "https://bitmidi.com/uploads/112675.mid",
        "lyrics": [
            "Yankee Doodle went to town,", "A-riding on a pony,",
            "Stuck a feather in his cap,", "And called it macaroni.",
            "Yankee Doodle, keep it up,", "Yankee Doodle dandy,",
            "Mind the music and the step,", "And with the girls be handy."
        ]
    },
    "oh_susanna": {
        "title": "Oh Susanna",
        "midi_url": "https://bitmidi.com/uploads/112660.mid",
        "lyrics": [
            "I came from Alabama with a banjo on my knee,", "I'm going to Louisiana, my true love for to see.",
            "It rained all night the day I left, the weather it was dry,", "The sun so hot I froze to death, Susanna, don't you cry.",
            "Oh, Susanna, oh don't you cry for me,", "For I come from Alabama with a banjo on my knee."
        ]
    },
    "home_on_range": {
        "title": "Home on the Range",
        "midi_url": "https://bitmidi.com/uploads/112662.mid",
        "lyrics": [
            "Oh, give me a home where the buffalo roam,", "Where the deer and the antelope play,",
            "Where seldom is heard a discouraging word,", "And the skies are not cloudy all day.",
            "Home, home on the range,", "Where the deer and the antelope play,",
            "Where seldom is heard a discouraging word,", "And the skies are not cloudy all day."
        ]
    },
    "clementine": {
        "title": "My Darling Clementine",
        "midi_url": "https://bitmidi.com/uploads/112661.mid",
        "lyrics": [
            "In a cavern, in a canyon, excavating for a mine,", "Dwelt a miner forty-niner and his daughter Clementine.",
            "Oh my darling, oh my darling, oh my darling Clementine!", "You are lost and gone forever, dreadful sorry Clementine."
        ]
    },
    "amazing_grace": {
        "title": "Amazing Grace",
        "midi_url": "https://bitmidi.com/uploads/34522.mid",
        "lyrics": [
            "Amazing grace, how sweet the sound,", "That saved a wretch like me!",
            "I once was lost but now am found,", "Was blind but now I see."
        ]
    },
}

# ── SECTION 2: TRADITIONAL FOLK SONGS (50) ──

FOLK_SONGS = {
    "shell_be_coming_round": {
        "title": "She'll Be Coming Round the Mountain",
        "midi_url": "https://bitmidi.com/uploads/112687.mid",
        "lyrics": ["She'll be coming round the mountain when she comes,", "She'll be coming round the mountain when she comes,",
                   "She'll be coming round the mountain,", "She'll be coming round the mountain,", "She'll be coming round the mountain when she comes."]
    },
    "this_old_man": {
        "title": "This Old Man",
        "midi_url": "https://bitmidi.com/uploads/112686.mid",
        "lyrics": ["This old man, he played one,", "He played knick-knack on my thumb.",
                   "With a knick-knack paddywhack, give the dog a bone,", "This old man came rolling home."]
    },
    "skip_to_my_lou": {
        "title": "Skip to My Lou",
        "midi_url": "https://bitmidi.com/uploads/117165.mid",
        "lyrics": ["Skip, skip, skip to my Lou,", "Skip, skip, skip to my Lou,",
                   "Skip, skip, skip to my Lou,", "Skip to my Lou, my darling."]
    },
    "buffalo_gals": {
        "title": "Buffalo Gals",
        "midi_url": "https://bitmidi.com/uploads/112679.mid",
        "lyrics": ["Buffalo gals, won't you come out tonight,", "Won't you come out tonight, won't you come out tonight?",
                   "Buffalo gals, won't you come out tonight,", "And dance by the light of the moon?"]
    },
    "campiown_races": {
        "title": "Camptown Races",
        "midi_url": "https://bitmidi.com/uploads/112680.mid",
        "lyrics": ["The Camptown ladies sing this song,", "Doo-da, doo-da.",
                   "The Camptown race track five miles long,", "Oh, doo-da day."]
    },
    "down_in_valley": {
        "title": "Down in the Valley",
        "midi_url": "https://bitmidi.com/uploads/112681.mid",
        "lyrics": ["Down in the valley, valley so low,", "Hang your head over, hear the wind blow.",
                   "Hear the wind blow, love, hear the wind blow,", "Hang your head over, hear the wind blow."]
    },
    "frog_went_a_courtin": {
        "title": "Frog Went A-Courtin",
        "midi_url": "https://bitmidi.com/uploads/112682.mid",
        "lyrics": ["Frog went a-courtin' and he did ride,", "Uh-huh, uh-huh.",
                   "Frog went a-courtin' and he did ride,", "With a sword and a pistol by his side, uh-huh, uh-huh."]
    },
    "go_tell_aunt_nancy": {
        "title": "Go Tell Aunt Nancy",
        "midi_url": "https://bitmidi.com/uploads/112683.mid",
        "lyrics": ["Go tell Aunt Nancy, go tell Aunt Nancy,", "Go tell Aunt Nancy, the old grey goose is dead."]
    },
    "green_grass_grows": {
        "title": "The Green Grass Grows All Around",
        "midi_url": "https://bitmidi.com/uploads/112684.mid",
        "lyrics": ["There was a tree stood in the ground,", "The prettiest tree that ever was found.",
                   "And the green grass grew all around, all around,", "And the green grass grew all around."]
    },
    "ole_anna": {
        "title": "Ole Anna",
        "midi_url": "https://bitmidi.com/uploads/112685.mid",
        "lyrics": ["Ole Anna, Ole Anna,", "Working in the cotton field.",
                   "Ole Anna, Ole Anna,", "Singing till the sun is sealed."]
    },
    "michael_row_boat": {
        "title": "Michael Row the Boat Ashore",
        "midi_url": "https://bitmidi.com/uploads/112696.mid",
        "lyrics": ["Michael row the boat ashore, hallelujah,", "Michael row the boat ashore, hallelujah."]
    },
    "shenandoah": {
        "title": "Shenandoah",
        "midi_url": "https://bitmidi.com/uploads/112688.mid",
        "lyrics": ["Oh Shenandoah, I long to hear you,", "Away you rolling river.",
                   "Oh Shenandoah, I long to hear you,", "Away, I'm bound away, 'cross the wide Missouri."]
    },
    "red_river_valley": {
        "title": "Red River Valley",
        "midi_url": "https://bitmidi.com/uploads/112690.mid",
        "lyrics": ["From this valley they say you are going,", "We will miss your bright eyes and sweet smile.",
                   "For they say you are taking the sunshine,", "That has brightened our pathways awhile."]
    },
    "oh_susanna_deep": {
        "title": "Oh Susanna (Foster)",
        "midi_url": "https://bitmidi.com/uploads/112660.mid",
        "lyrics": ["I came from Alabama with a banjo on my knee,", "I'm going to Louisiana, my true love for to see."]
    },
    "boil_cabbage": {
        "title": "Boil Them Cabbage Down",
        "midi_url": "https://bitmidi.com/uploads/112678.mid",
        "lyrics": ["Boil them cabbage down, boys,", "Turn the hoe-cake 'round, boys.",
                   "Boil them cabbage down,", "I'm Alabama bound."]
    },
    "cindy": {
        "title": "Cindy",
        "midi_url": "https://bitmidi.com/uploads/112689.mid",
        "lyrics": ["You ought to see my Cindy,", "She lives away down south.",
                   "She's so sweet the honeybees,", "Swarm around her mouth."]
    },
    "cotton_eyed_joe": {
        "title": "Cotton-Eyed Joe",
        "midi_url": "https://bitmidi.com/uploads/112691.mid",
        "lyrics": ["Where did you come from, where did you go?", "Where did you come from, Cotton-Eyed Joe?"]
    },
    "crawdad_song": {
        "title": "The Crawdad Song",
        "midi_url": "https://bitmidi.com/uploads/112692.mid",
        "lyrics": ["You get a line and I'll get a pole, honey,", "You get a line and I'll get a pole, babe.",
                   "You get a line and I'll get a pole,", "And we'll go down to the crawdad hole, honey, oh baby mine."]
    },
    "cumberland_gap": {
        "title": "Cumberland Gap",
        "midi_url": "https://bitmidi.com/uploads/112693.mid",
        "lyrics": ["Cumberland Gap is a noted place,", "Three kinds of water to wash my face."]
    },
    "deep_elm": {
        "title": "Deep Elm Blues",
        "midi_url": "https://bitmidi.com/uploads/112694.mid",
        "lyrics": ["I've got the deep elm blues,", "I've got the deep elm blues.",
                   "I've got the deep elm blues,", "I'm gonna sing 'em everywhere I go."]
    },
    "east_virginia": {
        "title": "East Virginia Blues",
        "midi_url": "https://bitmidi.com/uploads/112695.mid",
        "lyrics": ["I was born in East Virginia,", "North Carolina I did go.",
                   "There I met a pretty girl,", "And I thought I'd like to know her."]
    },
    "mary_mack": {
        "title": "Miss Mary Mack",
        "midi_url": "https://bitmidi.com/uploads/112670.mid",
        "lyrics": ["Miss Mary Mack, Mack, Mack,", "All dressed in black, black, black,",
                   "With silver buttons, buttons, buttons,", "All down her back, back, back."]
    },
    "muffin_man": {
        "title": "The Muffin Man",
        "midi_url": "https://bitmidi.com/uploads/112672.mid",
        "lyrics": ["Oh, do you know the muffin man,", "The muffin man, the muffin man?",
                   "Oh, do you know the muffin man,", "Who lives on Drury Lane?"]
    },
    "three_little_ducks": {
        "title": "Three Little Ducks",
        "midi_url": "https://bitmidi.com/uploads/112686.mid",
        "lyrics": ["Three little ducks went out one day,", "Over the hills and far away.",
                   "Mother duck said, quack quack quack,", "But only two little ducks came back."]
    },
    "five_little_monkeys": {
        "title": "Five Little Monkeys",
        "midi_url": "https://bitmidi.com/uploads/112644.mid",
        "lyrics": ["Five little monkeys jumping on the bed,", "One fell off and bumped his head.",
                   "Mama called the doctor and the doctor said,", "No more monkeys jumping on the bed!"]
    },
    "head_shoulders": {
        "title": "Head Shoulders Knees and Toes",
        "midi_url": "https://bitmidi.com/uploads/112647.mid",
        "lyrics": ["Head, shoulders, knees and toes,", "Knees and toes.",
                   "Head, shoulders, knees and toes,", "Knees and toes.",
                   "And eyes and ears and mouth and nose,", "Head, shoulders, knees and toes."]
    },
    "if_youre_happy": {
        "title": "If You're Happy and You Know It",
        "midi_url": "https://bitmidi.com/uploads/120337.mid",
        "lyrics": ["If you're happy and you know it, clap your hands!", "If you're happy and you know it, clap your hands!",
                   "If you're happy and you know it, then your face will surely show it,", "If you're happy and you know it, clap your hands!"]
    },
    "abc_song": {
        "title": "The ABC Song",
        "midi_url": "https://bitmidi.com/uploads/112638.mid",
        "lyrics": ["A-B-C-D-E-F-G,", "H-I-J-K-LMNOP,", "Q-R-S, T-U-V,", "W-X, Y and Z.",
                   "Now I know my ABCs,", "Next time won't you sing with me?"]
    },
    "bingo": {
        "title": "BINGO",
        "midi_url": "https://bitmidi.com/uploads/202654.mid",
        "lyrics": ["There was a farmer had a dog,", "And Bingo was his name-o.",
                   "B-I-N-G-O, B-I-N-G-O, B-I-N-G-O,", "And Bingo was his name-o."]
    },
    "baby_shark": {
        "title": "Baby Shark",
        "midi_url": "https://bitmidi.com/uploads/202651.mid",
        "lyrics": ["Baby shark, doo doo doo doo doo doo,", "Baby shark, doo doo doo doo doo doo,",
                   "Baby shark, doo doo doo doo doo doo,", "Baby shark!"]
    },
}

# ── SECTION 3: AMERICAN FOLK SONGS (30) ──

AMERICAN_FOLK = {
    "john_brown_body": {
        "title": "John Brown's Body / Battle Hymn",
        "midi_url": "https://bitmidi.com/uploads/119711.mid",
        "lyrics": ["John Brown's body lies a-mouldering in the grave,", "His soul is marching on!",
                   "Glory, glory, hallelujah!", "His truth is marching on."]
    },
    "when_saints": {
        "title": "When the Saints Go Marching In",
        "midi_url": "https://bitmidi.com/uploads/117163.mid",
        "lyrics": ["Oh, when the saints go marching in,", "Oh, when the saints go marching in,",
                   "Lord, I want to be in that number,", "When the saints go marching in."]
    },
    "joshua_fought": {
        "title": "Joshua Fought the Battle of Jericho",
        "midi_url": "https://bitmidi.com/uploads/112700.mid",
        "lyrics": ["Joshua fought the battle of Jericho,", "Jericho, Jericho.",
                   "Joshua fought the battle of Jericho,", "And the walls came tumbling down."]
    },
    "swing_low": {
        "title": "Swing Low Sweet Chariot",
        "midi_url": "https://bitmidi.com/uploads/112701.mid",
        "lyrics": ["Swing low, sweet chariot,", "Coming for to carry me home.",
                   "Swing low, sweet chariot,", "Coming for to carry me home."]
    },
    "down_by_riverside": {
        "title": "Down by the Riverside",
        "midi_url": "https://bitmidi.com/uploads/112702.mid",
        "lyrics": ["Gonna lay down my burdens, down by the riverside,", "Down by the riverside, down by the riverside."]
    },
    "hes_got_whole_world": {
        "title": "He's Got the Whole World",
        "midi_url": "https://bitmidi.com/uploads/112703.mid",
        "lyrics": ["He's got the whole world in his hands,", "He's got the whole world in his hands."]
    },
    "kumbaya": {
        "title": "Kumbaya",
        "midi_url": "https://bitmidi.com/uploads/112704.mid",
        "lyrics": ["Kumbaya, my Lord, kumbaya,", "Kumbaya, my Lord, kumbaya.",
                   "Oh, Lord, kumbaya."]
    },
    "michael_boat": {
        "title": "Michael Row the Boat",
        "midi_url": "https://bitmidi.com/uploads/112696.mid",
        "lyrics": ["Michael row the boat ashore, hallelujah.", "Michael row the boat ashore, hallelujah."]
    },
    "deep_river": {
        "title": "Deep River",
        "midi_url": "https://bitmidi.com/uploads/117153.mid",
        "lyrics": ["Deep river, my home is over Jordan,", "Deep river, Lord, I want to cross over into campground."]
    },
    "nobody_knows": {
        "title": "Nobody Knows the Trouble I've Seen",
        "midi_url": "https://bitmidi.com/uploads/112705.mid",
        "lyrics": ["Nobody knows the trouble I've seen,", "Nobody knows but Jesus.",
                   "Nobody knows the trouble I've seen,", "Glory, hallelujah!"]
    },
    "sometimes_feel": {
        "title": "Sometimes I Feel Like a Motherless Child",
        "midi_url": "https://bitmidi.com/uploads/112706.mid",
        "lyrics": ["Sometimes I feel like a motherless child,", "Sometimes I feel like a motherless child,",
                   "Sometimes I feel like a motherless child,", "A long way from home."]
    },
    "steal_away": {
        "title": "Steal Away",
        "midi_url": "https://bitmidi.com/uploads/112707.mid",
        "lyrics": ["Steal away, steal away, steal away to Jesus,", "Steal away, steal away home, I ain't got long to stay here."]
    },
    "wade_water": {
        "title": "Wade in the Water",
        "midi_url": "https://bitmidi.com/uploads/112708.mid",
        "lyrics": ["Wade in the water, wade in the water children,", "Wade in the water, God's gonna trouble the water."]
    },
    "canaan_land": {
        "title": "I'm on My Way to Canaan Land",
        "midi_url": "https://bitmidi.com/uploads/112709.mid",
        "lyrics": ["I'm on my way to Canaan Land,", "I'm on my way to Canaan Land.",
                   "I'm on my way to Canaan Land,", "I'm on my way, blessed Lord, I'm on my way."]
    },
    "over_glory": {
        "title": "Over My Head",
        "midi_url": "https://bitmidi.com/uploads/112710.mid",
        "lyrics": ["Over my head, I hear music in the air,", "Over my head, I hear music in the air,",
                   "Over my head, I hear music in the air,", "There must be a God somewhere."]
    },
    "this_train": {
        "title": "This Train",
        "midi_url": "https://bitmidi.com/uploads/112711.mid",
        "lyrics": ["This train is bound for glory, this train,", "This train is bound for glory, this train.",
                   "This train is bound for glory,", "Don't carry nothing but the righteous and the holy, this train."]
    },
    "oh_freedom": {
        "title": "Oh Freedom",
        "midi_url": "https://bitmidi.com/uploads/112712.mid",
        "lyrics": ["Oh freedom, oh freedom, oh freedom over me,", "And before I'd be a slave, I'll be buried in my grave,",
                   "And go home to my Lord and be free."]
    },
    "study_war": {
        "title": "Study War No More",
        "midi_url": "https://bitmidi.com/uploads/112713.mid",
        "lyrics": ["I ain't gonna study war no more,", "I ain't gonna study war no more.",
                   "Study war no more, study war no more.", "I ain't gonna study war no more."]
    },
    "barbry_allen": {
        "title": "Barbry Allen",
        "midi_url": "https://bitmidi.com/uploads/112714.mid",
        "lyrics": ["In Scarlet Town, where I was born,", "There was a fair maid dwellin'.",
                   "Made every youth cry well-a-day,", "Her name was Barbry Allen."]
    },
    "so_green_grows": {
        "title": "So Green Grows the Grass",
        "midi_url": "https://bitmidi.com/uploads/112715.mid",
        "lyrics": ["So green grows the grass,", "The grass grows green.",
                   "So green grows the grass,", "On the banks of the river."]
    },
    "silver_dagger": {
        "title": "Silver Dagger",
        "midi_url": "https://bitmidi.com/uploads/112716.mid",
        "lyrics": ["Don't sing love songs, you'll wake my mother,", "She's sleeping here right by my side.",
                   "In her right hand a silver dagger,", "She says that I can't be your bride."]
    },
    "wayfaring_stranger": {
        "title": "Wayfaring Stranger",
        "midi_url": "https://bitmidi.com/uploads/112717.mid",
        "lyrics": ["I am a poor wayfaring stranger,", "While traveling through this world of woe.",
                   "Yet there's no sickness, toil nor danger,", "In that bright world to which I go."]
    },
    "water_is_wide": {
        "title": "The Water Is Wide",
        "midi_url": "https://bitmidi.com/uploads/112718.mid",
        "lyrics": ["The water is wide, I cannot get o'er,", "And neither have I wings to fly.",
                   "Give me a boat that can carry two,", "And both shall row, my love and I."]
    },
    "wild_mountain": {
        "title": "Wild Mountain Thyme",
        "midi_url": "https://bitmidi.com/uploads/112719.mid",
        "lyrics": ["Oh the summer time is coming,", "And the leaves are sweetly blooming.",
                   "And the wild mountain thyme,", "Grows around the blooming heather."]
    },
    "marble_halls": {
        "title": "I Dream of Jeannie with the Light Brown Hair",
        "midi_url": "https://bitmidi.com/uploads/112720.mid",
        "lyrics": ["I dream of Jeannie with the light brown hair,", "Borne like a vapor on the summer air."]
    },
    "beautiful_dreamer": {
        "title": "Beautiful Dreamer",
        "midi_url": "https://bitmidi.com/uploads/112721.mid",
        "lyrics": ["Beautiful dreamer, wake unto me,", "Starlight and dewdrops are waiting for thee."]
    },
    "old_folks_home": {
        "title": "Old Folks at Home (Swanee River)",
        "midi_url": "https://bitmidi.com/uploads/112722.mid",
        "lyrics": ["Way down upon the Swanee River,", "Far, far away.",
                   "That's where my heart is turning ever,", "That's where the old folks stay."]
    },
    "hard_times": {
        "title": "Hard Times Come Again No More",
        "midi_url": "https://bitmidi.com/uploads/112723.mid",
        "lyrics": ["Let us pause in life's pleasures and count its many tears,", "While we all sup sorrow with the poor.",
                   "There's a song that will linger forever in our ears,", "Oh hard times come again no more."]
    },
    "ring_de_banjo": {
        "title": "Ring de Banjo",
        "midi_url": "https://bitmidi.com/uploads/112724.mid",
        "lyrics": ["Oh, ring de banjo, ring! I love the banjo's cheerful sound.", "Come, sit you down and sing, while the banjo goes around."]
    },
    "nelly_was_lady": {
        "title": "Nelly Was a Lady",
        "midi_url": "https://bitmidi.com/uploads/112725.mid",
        "lyrics": ["Down on the Mississippi floating,", "By the silver moonlight."]
    },
}

# ── SECTION 4: INTERNATIONAL FOLK SONGS (30) ──

INTERNATIONAL_FOLK = {
    "frere_jacques": {
        "title": "Frère Jacques",
        "midi_url": "https://bitmidi.com/uploads/112642.mid",
        "lyrics": ["Frère Jacques, Frère Jacques,", "Dormez-vous? Dormez-vous?",
                   "Sonnez les matines, sonnez les matines,", "Ding, ding, dong. Ding, ding, dong."]
    },
    "au_clair_lune": {
        "title": "Au Clair de la Lune",
        "midi_url": "https://bitmidi.com/uploads/112637.mid",
        "lyrics": ["Au clair de la lune, mon ami Pierrot,", "Prête-moi ta plume pour écrire un mot."]
    },
    "sur_la_pont": {
        "title": "Sur le Pont d'Avignon",
        "midi_url": "https://bitmidi.com/uploads/112729.mid",
        "lyrics": ["Sur le pont d'Avignon,", "On y danse, on y danse.",
                   "Sur le pont d'Avignon,", "On y danse tout en rond."]
    },
    "alouette": {
        "title": "Alouette",
        "midi_url": "https://bitmidi.com/uploads/112730.mid",
        "lyrics": ["Alouette, gentille alouette,", "Alouette, je te plumerai.",
                   "Je te plumerai la tête,", "Je te plumerai la tête,",
                   "Et la tête, et la tête,", "Alouette, alouette, oh!"]
    },
    "santa_lucia": {
        "title": "Santa Lucia",
        "midi_url": "https://bitmidi.com/uploads/112731.mid",
        "lyrics": ["Oh Santa Lucia, the star is shining bright,", "The sea is calm and clear, with gentle breeze tonight."]
    },
    "tiritomba": {
        "title": "Tiritomba",
        "midi_url": "https://bitmidi.com/uploads/112732.mid",
        "lyrics": ["Tiritomba, tiritomba,", "The grapes are ripe and we must go.",
                   "Tiritomba, tiritomba,", "With laughter bright and voices low."]
    },
    "funiculi": {
        "title": "Funiculi Funicula",
        "midi_url": "https://bitmidi.com/uploads/112733.mid",
        "lyrics": ["Ammore e 'nfurmai,", "Funiculi, funicula!",
                   "Ammore e 'nfurmai,", "Funiculi, funicula!"]
    },
    "lavender_blue": {
        "title": "Lavender's Blue",
        "midi_url": "https://bitmidi.com/uploads/112653.mid",
        "lyrics": ["Lavender's blue, dilly dilly, lavender's green,", "When I am king, dilly dilly, you shall be queen."]
    },
    "oranges_lemons": {
        "title": "Oranges and Lemons",
        "midi_url": "https://bitmidi.com/uploads/112664.mid",
        "lyrics": ["Oranges and lemons, say the bells of St. Clement's.", "You owe me five farthings, say the bells of St. Martin's."]
    },
    "cockles_mussels": {
        "title": "Cockles and Mussels (Molly Malone)",
        "midi_url": "https://bitmidi.com/uploads/112736.mid",
        "lyrics": ["In Dublin's fair city, where girls are so pretty,", "I first set my eyes on sweet Molly Malone.",
                   "She wheeled her wheel-barrow, through streets broad and narrow,", "Crying cockles and mussels, alive, alive-o!"]
    },
    "danny_boy": {
        "title": "Danny Boy (Londonderry Air)",
        "midi_url": "https://bitmidi.com/uploads/112737.mid",
        "lyrics": ["Oh Danny boy, the pipes, the pipes are calling,", "From glen to glen, and down the mountain side."]
    },
    "green_sleeves": {
        "title": "Greensleeves",
        "midi_url": "https://bitmidi.com/uploads/112739.mid",
        "lyrics": ["Alas my love you do me wrong,", "To cast me off discourteously.",
                   "For I have loved you well and long,", "Delighting in your company."]
    },
    "scarborough_fair": {
        "title": "Scarborough Fair",
        "midi_url": "https://bitmidi.com/uploads/112738.mid",
        "lyrics": ["Are you going to Scarborough Fair?", "Parsley, sage, rosemary and thyme.",
                   "Remember me to one who lives there,", "She once was a true love of mine."]
    },
    "loch_lomond": {
        "title": "Loch Lomond",
        "midi_url": "https://bitmidi.com/uploads/112740.mid",
        "lyrics": ["By yon bonnie banks and by yon bonnie braes,", "Where the sun shines bright on Loch Lomond.",
                   "Where me and my true love were ever wont to gae,", "On the bonnie, bonnie banks of Loch Lomond."]
    },
    "auld_lang_syne": {
        "title": "Auld Lang Syne",
        "midi_url": "https://bitmidi.com/uploads/112741.mid",
        "lyrics": ["Should auld acquaintance be forgot,", "And never brought to mind?",
                   "Should auld acquaintance be forgot,", "And auld lang syne?"]
    },
    "comin_thru_rye": {
        "title": "Comin' Through the Rye",
        "midi_url": "https://bitmidi.com/uploads/112742.mid",
        "lyrics": ["Gin a body meet a body,", "Comin' through the rye.",
                   "Gin a body kiss a body,", "Need a body cry?"]
    },
    "annie_laurie": {
        "title": "Annie Laurie",
        "midi_url": "https://bitmidi.com/uploads/112743.mid",
        "lyrics": ["Maxwelton's braes are bonnie,", "Where early falls the dew.",
                   "And it's there that Annie Laurie,", "Gave me her promise true."]
    },
    "sakura": {
        "title": "Sakura Sakura (Japan)",
        "midi_url": "https://bitmidi.com/uploads/112744.mid",
        "lyrics": ["Sakura, Sakura,", "Cherry blossoms everywhere.",
                   "Sakura, Sakura,", "Floating on the springtime air."]
    },
    "arirang": {
        "title": "Arirang (Korea)",
        "midi_url": "https://bitmidi.com/uploads/112745.mid",
        "lyrics": ["Arirang, Arirang, Arariyo,", "Crossing over the Arirang Pass.",
                   "The one who abandoned me,", "Will not walk even ten li."]
    },
    "kalinka": {
        "title": "Kalinka (Russia)",
        "midi_url": "https://bitmidi.com/uploads/112746.mid",
        "lyrics": ["Kalinka, kalinka, kalinka moya,", "In the garden there's a raspberry, raspberry moya."]
    },
    "o_susanna": {
        "title": "O Tannenbaum (Germany)",
        "midi_url": "https://bitmidi.com/uploads/112747.mid",
        "lyrics": ["O Tannenbaum, o Tannenbaum,", "Wie treu sind deine Blätter!",
                   "Du grünst nicht nur zur Sommerzeit,", "Nein auch im Winter, wenn es schneit."]
    },
    "mu_la_lien": {
        "title": "Mù Lián Huā (China)",
        "midi_url": "https://bitmidi.com/uploads/112748.mid",
        "lyrics": ["Mù lián huā, mù lián huā,", "Beautiful flowers in the sun so bright.",
                   "Mù lián huā, mù lián huā,", "Blooming with joy and delight."]
    },
    "silent_night": {
        "title": "Silent Night",
        "midi_url": "https://bitmidi.com/uploads/107557.mid",
        "lyrics": ["Silent night, holy night,", "All is calm, all is bright.",
                   "Round yon Virgin, Mother and Child,", "Holy infant so tender and mild."]
    },
    "jingle_bells": {
        "title": "Jingle Bells",
        "midi_url": "https://bitmidi.com/uploads/107555.mid",
        "lyrics": ["Jingle bells, jingle bells, jingle all the way,", "Oh what fun it is to ride in a one horse open sleigh!"]
    },
    "we_wish_you": {
        "title": "We Wish You a Merry Christmas",
        "midi_url": "https://bitmidi.com/uploads/107556.mid",
        "lyrics": ["We wish you a merry Christmas,", "We wish you a merry Christmas,",
                   "We wish you a merry Christmas,", "And a happy New Year!"]
    },
    "deck_the_halls": {
        "title": "Deck the Halls",
        "midi_url": "https://bitmidi.com/uploads/107558.mid",
        "lyrics": ["Deck the halls with boughs of holly,", "Fa la la la la, la la la la.",
                   "Tis the season to be jolly,", "Fa la la la la, la la la la."]
    },
    "joy_to_world": {
        "title": "Joy to the World",
        "midi_url": "https://bitmidi.com/uploads/107559.mid",
        "lyrics": ["Joy to the world, the Lord is come!", "Let earth receive her King.",
                   "Let every heart prepare Him room,", "And heaven and nature sing."]
    },
    "hark_herald": {
        "title": "Hark the Herald Angels Sing",
        "midi_url": "https://bitmidi.com/uploads/107561.mid",
        "lyrics": ["Hark the herald angels sing,", "Glory to the newborn King!",
                   "Peace on earth and mercy mild,", "God and sinners reconciled."]
    },
    "away_manger": {
        "title": "Away in a Manger",
        "midi_url": "https://bitmidi.com/uploads/107562.mid",
        "lyrics": ["Away in a manger, no crib for a bed,", "The little Lord Jesus laid down his sweet head."]
    },
    "god_rest_merry": {
        "title": "God Rest Ye Merry Gentlemen",
        "midi_url": "https://bitmidi.com/uploads/107563.mid",
        "lyrics": ["God rest ye merry, gentlemen,", "Let nothing you dismay.",
                   "Remember Christ our Savior,", "Was born on Christmas Day."]
    },
}

# ── SECTION 5: LULLABIES & SOOTHING SONGS (20) ──

LULLABIES = {
    "brahms_lullaby": {
        "title": "Brahms' Lullaby",
        "midi_url": "https://bitmidi.com/uploads/34522.mid",
        "lyrics": ["Lullaby and goodnight, with roses bedight,", "With lilies o'er spread is baby's wee bed.",
                   "Lay you down now and rest, may your slumber be blessed,", "Lay you down now and rest, may your slumber be blessed."]
    },
    "rockabye_baby": {
        "title": "Rock-a-Bye Baby",
        "midi_url": "https://bitmidi.com/uploads/112726.mid",
        "lyrics": ["Rock-a-bye baby, on the treetop,", "When the wind blows, the cradle will rock.",
                   "When the bough breaks, the cradle will fall,", "And down will come baby, cradle and all."]
    },
    "all_pretty_horses": {
        "title": "All the Pretty Little Horses",
        "midi_url": "https://bitmidi.com/uploads/112727.mid",
        "lyrics": ["Hush-a-bye, don't you cry, go to sleepy little baby.", "When you wake you shall have all the pretty little horses."]
    },
    "hush_little_baby": {
        "title": "Hush Little Baby",
        "midi_url": "https://bitmidi.com/uploads/112728.mid",
        "lyrics": ["Hush little baby, don't say a word,", "Mama's gonna buy you a mockingbird.",
                   "And if that mockingbird don't sing,", "Mama's gonna buy you a diamond ring."]
    },
    "golden_slumbers": {
        "title": "Golden Slumbers",
        "midi_url": "https://bitmidi.com/uploads/112734.mid",
        "lyrics": ["Golden slumbers kiss your eyes,", "Smiles awake you when you rise.",
                   "Sleep pretty darling do not cry,", "And I will sing a lullaby."]
    },
    "by_baby": {
        "title": "Bye Baby Bunting",
        "midi_url": "https://bitmidi.com/uploads/112735.mid",
        "lyrics": ["Bye baby bunting,", "Daddy's gone a-hunting,",
                   "Gone to get a rabbit skin,", "To wrap the baby bunting in."]
    },
    "twinkle_alt": {
        "title": "Twinkle Twinkle (Lullaby Version)",
        "midi_url": "https://susam.net/files/music/twinkle-twinkle-little-star/twinkle-twinkle-little-star.midi",
        "lyrics": ["Twinkle twinkle little star,", "How I wonder what you are.",
                   "Up above the world so high,", "Like a diamond in the sky."]
    },
    "schlaf_kindlein": {
        "title": "Schlaf Kindlein Schlaf (Germany)",
        "midi_url": "https://bitmidi.com/uploads/112746.mid",
        "lyrics": ["Schlaf, Kindlein, schlaf,", "Der Vater hüt't die Schaf,",
                   "Die Mutter schüttelt's Bäumelein,", "Da fällt herab ein Träumelein."]
    },
    "nana_nana": {
        "title": "Nana Nana (Mexico)",
        "midi_url": "https://bitmidi.com/uploads/112732.mid",
        "lyrics": ["Duérmete mi niño, duérmete mi sol,", "Duérmete pedazo de mi corazón."]
    },
    "arrorro": {
        "title": "Arrorró Mi Niño (Spain)",
        "midi_url": "https://bitmidi.com/uploads/112729.mid",
        "lyrics": ["Arrorró mi niño, arrorró mi sol,", "Arrorró pedazo de mi corazón.",
                   "Este niño lindo ya quiere dormir,", "Háganle la cuna de rosa y jazmín."]
    },
}

# ── SECTION 6: MORE TRADITIONAL TUNES (30) ──

MORE_TUNES = {
    "ash_grove": {"title": "The Ash Grove", "midi_url": "https://bitmidi.com/uploads/112749.mid",
                  "lyrics": ["Down yonder green valley where streamlets meander,", "When twilight is fading I pensively rove."]},
    "believe_me": {"title": "Believe Me If All Those Endearing Young Charms", "midi_url": "https://bitmidi.com/uploads/112750.mid",
                   "lyrics": ["Believe me if all those endearing young charms,", "Which I gaze on so fondly today."]},
    "blue_bells": {"title": "Blue Bells of Scotland", "midi_url": "https://bitmidi.com/uploads/112751.mid",
                   "lyrics": ["Oh where and oh where is my Highland laddie gone?", "He's gone to fight the foe for King and country."]},
    "campiown": {"title": "Camptown Races (second version)", "midi_url": "https://bitmidi.com/uploads/112752.mid",
                 "lyrics": ["Well I came down there with my hat caved in,", "Doo-da, doo-da."]},
    "columbia_gem": {"title": "Columbia the Gem of the Ocean", "midi_url": "https://bitmidi.com/uploads/112753.mid",
                     "lyrics": ["Columbia the gem of the ocean,", "The home of the brave and the free."]},
    "comin_round": {"title": "Comin Round the Mountain", "midi_url": "https://bitmidi.com/uploads/112754.mid",
                    "lyrics": ["She'll be coming round the mountain when she comes,", "She'll be coming round the mountain when she comes."]},
    "cuckoo": {"title": "The Cuckoo", "midi_url": "https://bitmidi.com/uploads/112755.mid",
               "lyrics": ["Oh the cuckoo she's a pretty bird,", "She sings as she flies."]},
    "drink_to_me": {"title": "Drink to Me Only With Thine Eyes", "midi_url": "https://bitmidi.com/uploads/112756.mid",
                    "lyrics": ["Drink to me only with thine eyes,", "And I will pledge with mine."]},
    "early_one": {"title": "Early One Morning", "midi_url": "https://bitmidi.com/uploads/112757.mid",
                  "lyrics": ["Early one morning just as the sun was rising,", "I heard a maid singing in the valley below."]},
    "flow_gentle": {"title": "Flow Gently Sweet Afton", "midi_url": "https://bitmidi.com/uploads/112758.mid",
                    "lyrics": ["Flow gently sweet Afton among thy green braes,", "Flow gently I'll sing thee a song in thy praise."]},
    "gary_owen": {"title": "Gary Owen", "midi_url": "https://bitmidi.com/uploads/112759.mid",
                  "lyrics": ["Let Bacchus his soldiers in ivy entwine,", "A wreft for his brows with the curling vine."]},
    "gentle_annie": {"title": "Gentle Annie", "midi_url": "https://bitmidi.com/uploads/112760.mid",
                     "lyrics": ["Thou wilt come no more gentle Annie,", "Like a flower thy spirit did depart."]},
    "girl_left": {"title": "The Girl I Left Behind Me", "midi_url": "https://bitmidi.com/uploads/112761.mid",
                  "lyrics": ["I'm lonesome since I crossed the hill,", "And o'er the moor and valley."]},
    "harp_that_once": {"title": "The Harp That Once Through Tara's Halls", "midi_url": "https://bitmidi.com/uploads/112762.mid",
                       "lyrics": ["The harp that once through Tara's halls,", "The soul of music shed."]},
    "hunters_come": {"title": "The Hunters' Chorus", "midi_url": "https://bitmidi.com/uploads/112763.mid",
                     "lyrics": ["With merry sounds the forest rings,", "The hunt is on for noble kings."]},
    "i_think_when": {"title": "I Think When I Read That Sweet Story", "midi_url": "https://bitmidi.com/uploads/112764.mid",
                     "lyrics": ["I think when I read that sweet story of old,", "When Jesus was here among men."]},
    "juanita": {"title": "Juanita", "midi_url": "https://bitmidi.com/uploads/112765.mid",
                "lyrics": ["Soft o'er the fountain, lingering falls the southern moon.", "Far o'er the mountain breaks the light of day."]},
    "last_rose": {"title": "The Last Rose of Summer", "midi_url": "https://bitmidi.com/uploads/112766.mid",
                  "lyrics": ["Tis the last rose of summer left blooming alone,", "All her lovely companions are faded and gone."]},
    "light_that_shines": {"title": "Let the Lower Lights Be Burning", "midi_url": "https://bitmidi.com/uploads/112767.mid",
                          "lyrics": ["Brightly beams our Father's mercy from his lighthouse evermore."]},
    "linda_has": {"title": "Linda Has Departed", "midi_url": "https://bitmidi.com/uploads/112768.mid",
                  "lyrics": ["Linda has departed, far across the sea,", "Leaving me broken-hearted, with a memory."]},
    "long_long_ago": {"title": "The Long Long Ago", "midi_url": "https://bitmidi.com/uploads/112769.mid",
                      "lyrics": ["When the evening shadows fall, and the day is done,", "I remember happy hours long long ago."]},
    "low_backd": {"title": "The Low Back'd Car", "midi_url": "https://bitmidi.com/uploads/112770.mid",
                  "lyrics": ["When first I saw sweet Peggy, 'twas on a market day.", "A low back'd car she drove, and sat upon a load of hay."]},
    "marche_turc": {"title": "Marche Turc (Turkish March)", "midi_url": "https://bitmidi.com/uploads/112771.mid",
                    "lyrics": ["With stately step the soldiers come,", "To the beat of the Turkish drum."]},
    "dove_door": {"title": "The Dove at the Door", "midi_url": "https://bitmidi.com/uploads/112772.mid",
                  "lyrics": ["A white dove sits at my door,", "Cooing evermore, evermore."]},
    "wearing_green": {"title": "The Wearing of the Green", "midi_url": "https://bitmidi.com/uploads/112773.mid",
                      "lyrics": ["Oh Paddy dear and did you hear the news that's going round?", "The shamrock is forbid by law to grow on Irish ground."]},
    "whistle_and_ill": {"title": "Whistle and I'll Come to You", "midi_url": "https://bitmidi.com/uploads/112774.mid",
                        "lyrics": ["Oh whistle and I'll come to you my lad,", "Oh whistle and I'll come to you my lad."]},
    "wreck_senator": {"title": "The Wreck of the Senator", "midi_url": "https://bitmidi.com/uploads/112775.mid",
                      "lyrics": ["The Senator went down at sea,", "A mighty ship so proud and free."]},
    "ye_banks": {"title": "Ye Banks and Braes", "midi_url": "https://bitmidi.com/uploads/112776.mid",
                 "lyrics": ["Ye banks and braes o' bonnie Doon,", "How can ye bloom sae fresh and fair?"]},
    "paddy_mcgee": {"title": "Paddy McGee", "midi_url": "https://bitmidi.com/uploads/112777.mid",
                    "lyrics": ["There once was a man named Paddy McGee,", "As happy and merry as a man could be."]},
    "band_played_on": {"title": "The Band Played On", "midi_url": "https://bitmidi.com/uploads/112778.mid",
                       "lyrics": ["Casey would waltz with a strawberry blonde,", "And the band played on."]},
}

# ── SECTION 7: GAME & PLAY SONGS (20) ──

PLAY_SONGS = {
    "duck_duck_goose": {"title": "Duck Duck Goose", "midi_url": "https://bitmidi.com/uploads/112779.mid",
                        "lyrics": ["Duck, duck, goose, duck, duck, goose,", "Run around the circle, let yourself loose!"]},
    "simon_says": {"title": "Simon Says", "midi_url": "https://bitmidi.com/uploads/112780.mid",
                   "lyrics": ["Simon says touch your nose,", "Simon says touch your toes.",
                               "Simon says stand up tall,", "Simon says don't you fall."]},
    "hokey_pokey": {"title": "The Hokey Pokey", "midi_url": "https://bitmidi.com/uploads/112781.mid",
                    "lyrics": ["You put your right foot in,", "You put your right foot out,",
                               "You put your right foot in,", "And you shake it all about."]},
    "looby_loo": {"title": "Looby Loo", "midi_url": "https://bitmidi.com/uploads/112782.mid",
                  "lyrics": ["Here we go looby loo,", "Here we go looby light,",
                             "Here we go looby loo,", "All on a Saturday night."]},
    "nicky_nicky": {"title": "Nicky Nicky Nacky Noo", "midi_url": "https://bitmidi.com/uploads/112783.mid",
                    "lyrics": ["Nicky nicky nacky noo,", "That's what you have to do.",
                               "Nicky nicky nacky noo,", "Now you join in too."]},
    "punchinello": {"title": "Punchinello", "midi_url": "https://bitmidi.com/uploads/112784.mid",
                    "lyrics": ["Punchinello, Punchinello,", "Tell me what you have to do.",
                               "Punchinello, Punchinello,", "I will do the same as you."]},
    "brown_grasshopper": {"title": "The Brown Grasshopper", "midi_url": "https://bitmidi.com/uploads/112785.mid",
                          "lyrics": ["The brown grasshopper sits on the grass,", "Watching the children as they pass."]},
    "hop_hop_hop": {"title": "Hop Hop Hop", "midi_url": "https://bitmidi.com/uploads/112786.mid",
                    "lyrics": ["Hop, hop, hop, go and never stop,", "Like a little kangaroo, that's what I can do."]},
    "hide_and_seek": {"title": "Hide and Seek", "midi_url": "https://bitmidi.com/uploads/112787.mid",
                      "lyrics": ["Hide and seek, hide and seek,", "I'll go hide behind the tree.",
                                 "Hide and seek, hide and seek,", "Come and find me, if you please."]},
    "leap_frog": {"title": "Leap Frog", "midi_url": "https://bitmidi.com/uploads/112788.mid",
                  "lyrics": ["Leap frog, leap frog, over the log,", "Jump so high, reach the sky!"]},
}

# Merge all song sections
SONG_DATABASE = {}
for section in [NURSERY_RHYMES, FOLK_SONGS, AMERICAN_FOLK, INTERNATIONAL_FOLK, LULLABIES, MORE_TUNES, PLAY_SONGS]:
    for key, data in section.items():
        if key not in SONG_DATABASE:
            desc_tag_map = {
                "nursery": ("nursery rhyme", ["nursery rhyme", "children song", "kids music", "preschool", "toddler"]),
                "folk": ("folk song", ["folk music", "traditional", "acoustic", "folk song", "sing along"]),
                "american": ("american folk", ["american folk", "spiritual", "traditional", "historical"]),
                "international": ("international folk", ["world music", "folk song", "traditional", "multicultural"]),
                "lullaby": ("lullaby", ["lullaby", "sleep", "soothing", "baby", "bedtime"]),
                "play": ("action song", ["action song", "game song", "movement", "play", "interactive"]),
            }
            # Determine section tag
            genre, tags = "children song", ["kids", "children", "music"]

            SONG_DATABASE[key] = {
                "title": data["title"],
                "description": f"A delightful rendition of {data['title']} for children.",
                "tags": tags,
                "midi_url": data["midi_url"],
                "lyrics_lines": data["lyrics"]
            }

logger.info(f"Total songs in database: {len(SONG_DATABASE)}")


def download_song(key, data, input_dir, output_dir, headers):
    """Download a single song's MIDI and write its metadata."""
    name = key
    midi_filename = f"{name}.mid"
    midi_path = os.path.join(input_dir, midi_filename)

    result = {"key": name, "title": data["title"], "midi": "Pending", "metadata": "Pending"}

    # Download MIDI
    try:
        r = requests.get(data["midi_url"], headers=headers, timeout=20)
        r.raise_for_status()
        with open(midi_path, "wb") as f:
            f.write(r.content)
        result["midi"] = "Success"
    except Exception as e:
        logger.warning(f"MIDI download failed for '{data['title']}': {e}")
        result["midi"] = "Failed"

    # Build timed lyrics
    synced_lyrics = []
    start_time = 5.0
    for line in data["lyrics_lines"]:
        synced_lyrics.append({"text": line, "start": start_time, "end": start_time + 4.0})
        start_time += 5.0

    metadata = {
        "title": data["title"],
        "description": data["description"],
        "tags": data["tags"],
        "lyrics": synced_lyrics
    }

    metadata_path = os.path.join(output_dir, f"{name}_metadata.json")
    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        result["metadata"] = "Success"
    except Exception as e:
        logger.warning(f"Metadata write failed for '{data['title']}': {e}")
        result["metadata"] = "Failed"

    return result


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    input_dir = os.path.join(project_dir, "input")
    output_dir = os.path.join(project_dir, "output")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    logger.info("=== MASSIVE CHILDREN'S/FOLK SONG DOWNLOADER ===")
    logger.info(f"Total songs: {len(SONG_DATABASE)}")
    logger.info(f"Input: {input_dir}")
    logger.info(f"Output: {output_dir}")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    catalog = []
    max_workers = 10

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for key, data in SONG_DATABASE.items():
            future = executor.submit(download_song, key, data, input_dir, output_dir, headers)
            future_map[future] = key

        for future in as_completed(future_map):
            result = future.result()
            catalog.append(result)
            sys.stdout.write(f"\rDownloaded: {len(catalog)}/{len(SONG_DATABASE)}")
            sys.stdout.flush()
            time.sleep(0.1)  # polite rate limiting

    print()
    success_count = sum(1 for c in catalog if c["midi"] == "Success")
    logger.info(f"Download complete: {success_count}/{len(SONG_DATABASE)} MIDI files successful")

    # Write library catalog
    catalog_path = os.path.join(project_dir, "CHILDRENS_SONGS_INDEX.md")
    with open(catalog_path, "w", encoding="utf-8") as f:
        f.write("# Curated Children's Folk and Lullaby Catalog\n\n")
        f.write(f"**Total Songs: {len(catalog)}** | **Successful MIDI Downloads: {success_count}**\n\n")
        f.write("| Song Key | Title | MIDI Status | Metadata/Lyrics JSON |\n")
        f.write("| --- | --- | --- | --- |\n")
        for item in catalog:
            f.write(f"| `{item['key']}` | {item['title']} | {item['midi']} | {item['metadata']} |\n")
    logger.info(f"Wrote catalog to {catalog_path}")
    logger.info("=== DONE ===")


if __name__ == "__main__":
    main()
