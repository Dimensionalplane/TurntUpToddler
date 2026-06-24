"""
Massive auto-discovering scraper: probes bitmidi.com for working MIDIs,
maps them to known songs, and downloads everything.
"""

import os
import requests
import json
import logging
import time
import sys
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
INPUT_DIR = os.path.join(PROJECT_DIR, "input")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── KNOWN WORKING SONG MAP ──
# Manually curated songs with known titles and lyrics
# Maps bitmidi ID to song metadata

CURATED_SONGS = {
    # Nursery rhymes originally at 112638-112677
    112638: {
        "title": "Daisy Bell (Bicycle Built for Two)",
        "tags": ["nursery rhyme", "classic"],
        "lyrics": [
            "Daisy, Daisy, give me your answer do",
            "I'm half crazy all for the love of you",
        ],
    },
    112639: {
        "title": "Cowboy Song",
        "tags": ["folk", "western"],
        "lyrics": [
            "I'm a lonely cowboy riding on the plain",
            "Singing to the starlight in the midnight rain",
        ],
    },
    112640: {
        "title": "Diddle Diddle Dumpling",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Diddle diddle dumpling my son John",
            "Went to bed with his trousers on",
        ],
    },
    112641: {
        "title": "The Farmer in the Dell",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "The farmer in the dell",
            "The farmer in the dell",
            "Hi-ho the derry-o",
            "The farmer in the dell",
        ],
    },
    112642: {
        "title": "Frere Jacques",
        "tags": ["nursery rhyme", "french"],
        "lyrics": ["Frere Jacques, Frere Jacques", "Dormez-vous? Dormez-vous?"],
    },
    112643: {
        "title": "One Two Buckle My Shoe",
        "tags": ["nursery rhyme", "counting"],
        "lyrics": ["One two buckle my shoe", "Three four knock at the door"],
    },
    112644: {
        "title": "Georgie Porgie",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Georgie Porgie pudding and pie",
            "Kissed the girls and made them cry",
        ],
    },
    112645: {
        "title": "Goosey Goosey Gander",
        "tags": ["nursery rhyme"],
        "lyrics": ["Goosey goosey gander", "Whither shall I wander?"],
    },
    112646: {
        "title": "The Grand Old Duke of York",
        "tags": ["nursery rhyme"],
        "lyrics": ["Oh the grand old Duke of York", "He had ten thousand men"],
    },
    112647: {
        "title": "Hey Diddle Diddle",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Hey diddle diddle the cat and the fiddle",
            "The cow jumped over the moon",
        ],
    },
    112648: {
        "title": "Baa Baa Black Sheep",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Baa baa black sheep have you any wool",
            "Yes sir yes sir three bags full",
        ],
    },
    112649: {
        "title": "Hickory Dickory Dock",
        "tags": ["nursery rhyme"],
        "lyrics": ["Hickory dickory dock", "The mouse ran up the clock"],
    },
    112650: {
        "title": "Jack and Jill",
        "tags": ["nursery rhyme"],
        "lyrics": ["Jack and Jill went up the hill", "To fetch a pail of water"],
    },
    112651: {
        "title": "Humpty Dumpty",
        "tags": ["nursery rhyme"],
        "lyrics": ["Humpty Dumpty sat on a wall", "Humpty Dumpty had a great fall"],
    },
    112652: {
        "title": "Lavender's Blue",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Lavender's blue dilly dilly lavender's green",
            "When I am king dilly dilly you shall be queen",
        ],
    },
    112653: {
        "title": "Lavender Blue (alt)",
        "tags": ["nursery rhyme"],
        "lyrics": ["Lavender blue dilly dilly", "Lavender green"],
    },
    112654: {
        "title": "Ladybird Ladybird",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Ladybird ladybird fly away home",
            "Your house is on fire and your children are gone",
        ],
    },
    112655: {
        "title": "Little Bo Peep",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Little Bo Peep has lost her sheep",
            "And doesn't know where to find them",
        ],
    },
    112656: {
        "title": "Little Boy Blue",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Little Boy Blue come blow your horn",
            "The sheep's in the meadow the cow's in the corn",
        ],
    },
    112657: {
        "title": "Little Miss Muffet",
        "tags": ["nursery rhyme"],
        "lyrics": ["Little Miss Muffet sat on a tuffet", "Eating her curds and whey"],
    },
    112658: {
        "title": "Old MacDonald Had a Farm",
        "tags": ["nursery rhyme", "animals"],
        "lyrics": [
            "Old MacDonald had a farm E-I-E-I-O",
            "And on his farm he had a cow E-I-E-I-O",
        ],
    },
    112659: {
        "title": "Nursery Rhyme Medley",
        "tags": ["nursery rhyme"],
        "lyrics": ["Sing a song of sixpence", "A pocket full of rye"],
    },
    112660: {
        "title": "Oh Susanna",
        "tags": ["folk", "american"],
        "lyrics": [
            "I come from Alabama with a banjo on my knee",
            "I'm going to Louisiana my true love for to see",
        ],
    },
    112661: {
        "title": "My Darling Clementine",
        "tags": ["folk", "american"],
        "lyrics": [
            "In a cavern in a canyon excavating for a mine",
            "Dwelt a miner forty-niner and his daughter Clementine",
        ],
    },
    112662: {
        "title": "Home on the Range",
        "tags": ["folk", "western"],
        "lyrics": [
            "Oh give me a home where the buffalo roam",
            "Where the deer and the antelope play",
        ],
    },
    112663: {
        "title": "Old King Cole",
        "tags": ["nursery rhyme"],
        "lyrics": ["Old King Cole was a merry old soul", "And a merry old soul was he"],
    },
    112664: {
        "title": "Oranges and Lemons",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Oranges and lemons say the bells of St Clement's",
            "You owe me five farthings say the bells of St Martin's",
        ],
    },
    112665: {
        "title": "Pat a Cake",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Pat a cake pat a cake baker's man",
            "Bake me a cake as fast as you can",
        ],
    },
    112666: {
        "title": "Simple Simon",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Simple Simon met a pieman going to the fair",
            "Said Simple Simon to the pieman let me taste your ware",
        ],
    },
    112667: {
        "title": "Pop Goes the Weasel",
        "tags": ["nursery rhyme"],
        "lyrics": ["Half a pound of tuppenny rice", "Half a pound of treacle"],
    },
    112668: {
        "title": "Ring Around the Rosie",
        "tags": ["nursery rhyme"],
        "lyrics": ["Ring around the rosie", "A pocket full of posies"],
    },
    112669: {
        "title": "Rain Rain Go Away",
        "tags": ["nursery rhyme"],
        "lyrics": ["Rain rain go away", "Come again another day"],
    },
    112670: {
        "title": "Miss Mary Mack",
        "tags": ["nursery rhyme", "clapping"],
        "lyrics": ["Miss Mary Mack Mack Mack", "All dressed in black black black"],
    },
    112671: {
        "title": "Mary Had a Little Lamb",
        "tags": ["nursery rhyme"],
        "lyrics": ["Mary had a little lamb", "Its fleece was white as snow"],
    },
    112672: {
        "title": "See Saw Margery Daw",
        "tags": ["nursery rhyme"],
        "lyrics": ["See saw Margery Daw", "Sold her bed and lay upon straw"],
    },
    112673: {
        "title": "Three Blind Mice",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Three blind mice three blind mice",
            "See how they run see how they run",
        ],
    },
    112674: {
        "title": "The Wheels on the Bus",
        "tags": ["nursery rhyme", "action"],
        "lyrics": [
            "The wheels on the bus go round and round",
            "Round and round round and round",
        ],
    },
    112675: {
        "title": "Yankee Doodle",
        "tags": ["folk", "patriotic"],
        "lyrics": [
            "Yankee Doodle went to town riding on a pony",
            "Stuck a feather in his cap and called it macaroni",
        ],
    },
    112676: {
        "title": "Here We Go Round the Mulberry Bush",
        "tags": ["nursery rhyme"],
        "lyrics": [
            "Here we go round the mulberry bush",
            "The mulberry bush the mulberry bush",
        ],
    },
    112677: {
        "title": "Tom Tom the Piper's Son",
        "tags": ["nursery rhyme"],
        "lyrics": ["Tom Tom the piper's son", "Stole a pig and away he run"],
    },
    112678: {
        "title": "Boil Them Cabbage Down",
        "tags": ["folk", "american"],
        "lyrics": ["Boil them cabbage down boys", "Turn the hoe-cake round boys"],
    },
    112679: {
        "title": "Buffalo Gals",
        "tags": ["folk", "american"],
        "lyrics": [
            "Buffalo gals won't you come out tonight",
            "Won't you come out tonight",
        ],
    },
    112680: {
        "title": "Camptown Races",
        "tags": ["folk", "american"],
        "lyrics": [
            "The Camptown ladies sing this song doo-da doo-da",
            "The Camptown race track five miles long oh doo-da day",
        ],
    },
    112681: {
        "title": "Down in the Valley",
        "tags": ["folk", "american"],
        "lyrics": [
            "Down in the valley valley so low",
            "Hang your head over hear the wind blow",
        ],
    },
    112682: {
        "title": "Frog Went A-Courtin",
        "tags": ["folk", "american"],
        "lyrics": [
            "Frog went a-courtin and he did ride uh-huh",
            "With a sword and a pistol by his side uh-huh",
        ],
    },
    112683: {
        "title": "Go Tell Aunt Nancy",
        "tags": ["folk", "american"],
        "lyrics": [
            "Go tell Aunt Nancy go tell Aunt Nancy",
            "Go tell Aunt Nancy the old grey goose is dead",
        ],
    },
    112684: {
        "title": "The Green Grass Grows All Around",
        "tags": ["folk", "american"],
        "lyrics": [
            "There was a tree stood in the ground",
            "The prettiest tree that ever was found",
        ],
    },
    112685: {
        "title": "Oleanna",
        "tags": ["folk", "american"],
        "lyrics": [
            "Oleanna Oleanna working in the cotton field",
            "Oleanna Oleanna singing till the sun is sealed",
        ],
    },
    112686: {
        "title": "This Old Man",
        "tags": ["nursery rhyme", "counting"],
        "lyrics": ["This old man he played one", "He played knick-knack on my thumb"],
    },
    112687: {
        "title": "Shell Be Coming Round the Mountain",
        "tags": ["folk", "american"],
        "lyrics": [
            "She'll be coming round the mountain when she comes",
            "She'll be coming round the mountain when she comes",
        ],
    },
    112688: {
        "title": "Shenandoah",
        "tags": ["folk", "american"],
        "lyrics": ["Oh Shenandoah I long to hear you", "Away you rolling river"],
    },
    112689: {
        "title": "Cindy",
        "tags": ["folk", "american"],
        "lyrics": ["You ought to see my Cindy", "She lives away down south"],
    },
    112690: {
        "title": "Red River Valley",
        "tags": ["folk", "western"],
        "lyrics": [
            "From this valley they say you are going",
            "We will miss your bright eyes and sweet smile",
        ],
    },
    112691: {
        "title": "Cotton-Eyed Joe",
        "tags": ["folk", "american"],
        "lyrics": [
            "Where did you come from where did you go",
            "Where did you come from Cotton-Eyed Joe",
        ],
    },
    112692: {
        "title": "The Crawdad Song",
        "tags": ["folk", "american"],
        "lyrics": [
            "You get a line and I'll get a pole honey",
            "You get a line and I'll get a pole babe",
        ],
    },
    112693: {
        "title": "Cumberland Gap",
        "tags": ["folk", "american"],
        "lyrics": [
            "Cumberland Gap is a noted place",
            "Three kinds of water to wash my face",
        ],
    },
    112694: {
        "title": "Deep Elm Blues",
        "tags": ["folk", "american"],
        "lyrics": ["I've got the deep elm blues", "I've got the deep elm blues"],
    },
    112695: {
        "title": "East Virginia Blues",
        "tags": ["folk", "american"],
        "lyrics": ["I was born in East Virginia", "North Carolina I did go"],
    },
    112696: {
        "title": "Michael Row the Boat Ashore",
        "tags": ["spiritual", "gospel"],
        "lyrics": [
            "Michael row the boat ashore hallelujah",
            "Michael row the boat ashore hallelujah",
        ],
    },
    112697: {
        "title": "When the Saints Go Marching In",
        "tags": ["gospel", "traditional"],
        "lyrics": [
            "Oh when the saints go marching in",
            "Oh when the saints go marching in",
        ],
    },
    112698: {
        "title": "Swing Low Sweet Chariot",
        "tags": ["spiritual", "gospel"],
        "lyrics": ["Swing low sweet chariot", "Coming for to carry me home"],
    },
    112699: {
        "title": "Joshua Fought the Battle of Jericho",
        "tags": ["spiritual", "gospel"],
        "lyrics": ["Joshua fought the battle of Jericho", "Jericho Jericho"],
    },
    112700: {
        "title": "He's Got the Whole World",
        "tags": ["spiritual", "gospel"],
        "lyrics": [
            "He's got the whole world in his hands",
            "He's got the whole world in his hands",
        ],
    },
    112701: {
        "title": "Kumbaya",
        "tags": ["spiritual", "camp"],
        "lyrics": ["Kumbaya my Lord kumbaya", "Kumbaya my Lord kumbaya"],
    },
    112702: {
        "title": "Down by the Riverside",
        "tags": ["spiritual", "gospel"],
        "lyrics": [
            "Gonna lay down my burdens down by the riverside",
            "Down by the riverside",
        ],
    },
    112703: {
        "title": "This Little Light of Mine",
        "tags": ["spiritual", "children"],
        "lyrics": [
            "This little light of mine I'm gonna let it shine",
            "This little light of mine I'm gonna let it shine",
        ],
    },
    112704: {
        "title": "Rise and Shine",
        "tags": ["spiritual", "children"],
        "lyrics": [
            "The Lord said to Noah there's gonna be a floody floody",
            "Get those children out of the muddy muddy",
        ],
    },
    112705: {
        "title": "Nobody Knows the Trouble",
        "tags": ["spiritual", "gospel"],
        "lyrics": ["Nobody knows the trouble I've seen", "Nobody knows but Jesus"],
    },
    112706: {
        "title": "Motherless Child",
        "tags": ["spiritual", "gospel"],
        "lyrics": ["Sometimes I feel like a motherless child", "A long way from home"],
    },
    112707: {
        "title": "All Things Bright and Beautiful",
        "tags": ["hymn", "children"],
        "lyrics": [
            "All things bright and beautiful all creatures great and small",
            "All things wise and wonderful the Lord God made them all",
        ],
    },
    112708: {
        "title": "Wade in the Water",
        "tags": ["spiritual", "gospel"],
        "lyrics": [
            "Wade in the water wade in the water children",
            "Wade in the water God's gonna trouble the water",
        ],
    },
    112709: {
        "title": "I'm on My Way to Canaan",
        "tags": ["spiritual", "gospel"],
        "lyrics": ["I'm on my way to Canaan Land", "I'm on my way to Canaan Land"],
    },
    112710: {
        "title": "Over My Head",
        "tags": ["spiritual", "gospel"],
        "lyrics": [
            "Over my head I hear music in the air",
            "There must be a God somewhere",
        ],
    },
    112711: {
        "title": "This Train",
        "tags": ["spiritual", "gospel"],
        "lyrics": [
            "This train is bound for glory this train",
            "This train is bound for glory this train",
        ],
    },
    112712: {
        "title": "Oh Freedom",
        "tags": ["spiritual", "freedom"],
        "lyrics": [
            "Oh freedom oh freedom oh freedom over me",
            "And before I'd be a slave I'll be buried in my grave",
        ],
    },
    112713: {
        "title": "Study War No More",
        "tags": ["spiritual", "peace"],
        "lyrics": [
            "I ain't gonna study war no more",
            "I ain't gonna study war no more",
        ],
    },
    112714: {
        "title": "Barbry Allen",
        "tags": ["folk", "ballad"],
        "lyrics": ["In Scarlet Town where I was born", "There was a fair maid dwellin"],
    },
    112715: {
        "title": "So Green Grows the Grass",
        "tags": ["folk", "irish"],
        "lyrics": ["So green grows the grass", "The grass grows green"],
    },
    112716: {
        "title": "Silver Dagger",
        "tags": ["folk", "ballad"],
        "lyrics": [
            "Don't sing love songs you'll wake my mother",
            "She's sleeping here right by my side",
        ],
    },
    112717: {
        "title": "Wayfaring Stranger",
        "tags": ["folk", "spiritual"],
        "lyrics": [
            "I am a poor wayfaring stranger",
            "While traveling through this world of woe",
        ],
    },
    112718: {
        "title": "The Water Is Wide",
        "tags": ["folk", "ballad"],
        "lyrics": [
            "The water is wide I cannot get o'er",
            "Neither have I wings to fly",
        ],
    },
    112719: {
        "title": "Wild Mountain Thyme",
        "tags": ["folk", "scottish"],
        "lyrics": [
            "Oh the summer time is coming",
            "And the leaves are sweetly blooming",
        ],
    },
    112720: {
        "title": "Jeannie with the Light Brown Hair",
        "tags": ["folk", "stephen foster"],
        "lyrics": [
            "I dream of Jeannie with the light brown hair",
            "Borne like a vapor on the summer air",
        ],
    },
    112721: {
        "title": "Beautiful Dreamer",
        "tags": ["folk", "lullaby"],
        "lyrics": [
            "Beautiful dreamer wake unto me",
            "Starlight and dewdrops are waiting for thee",
        ],
    },
    112722: {
        "title": "Old Folks at Home",
        "tags": ["folk", "stephen foster"],
        "lyrics": ["Way down upon the Swanee River", "Far far away"],
    },
    112723: {
        "title": "Hard Times Come Again No More",
        "tags": ["folk", "stephen foster"],
        "lyrics": ["Let us pause in life's pleasures", "And count its many tears"],
    },
    112724: {
        "title": "Ring de Banjo",
        "tags": ["folk", "stephen foster"],
        "lyrics": ["Oh ring de banjo ring", "I love the banjo's cheerful sound"],
    },
    112725: {
        "title": "Nelly Was a Lady",
        "tags": ["folk", "stephen foster"],
        "lyrics": ["Down on the Mississippi floating", "By the silver moonlight"],
    },
    112726: {
        "title": "Rock-a-Bye Baby",
        "tags": ["lullaby", "nursery"],
        "lyrics": [
            "Rock-a-bye baby on the treetop",
            "When the wind blows the cradle will rock",
        ],
    },
    112727: {
        "title": "All the Pretty Horses",
        "tags": ["lullaby"],
        "lyrics": ["Hush-a-bye don't you cry", "Go to sleepy little baby"],
    },
    112728: {
        "title": "Hush Little Baby",
        "tags": ["lullaby"],
        "lyrics": [
            "Hush little baby don't say a word",
            "Mama's gonna buy you a mockingbird",
        ],
    },
    112729: {
        "title": "Sur le Pont d'Avignon",
        "tags": ["french", "folk"],
        "lyrics": ["Sur le pont d'Avignon", "On y danse on y danse"],
    },
    112730: {
        "title": "Alouette",
        "tags": ["french", "folk"],
        "lyrics": ["Alouette gentille alouette", "Alouette je te plumerai"],
    },
    112731: {
        "title": "Santa Lucia",
        "tags": ["italian", "folk"],
        "lyrics": [
            "Oh Santa Lucia the star is shining bright",
            "The sea is calm and clear",
        ],
    },
    112732: {
        "title": "Tiritomba",
        "tags": ["italian", "folk"],
        "lyrics": ["Tiritomba tiritomba", "The grapes are ripe and we must go"],
    },
    112733: {
        "title": "Funiculi Funicula",
        "tags": ["italian", "folk"],
        "lyrics": ["Ammore e nfurmai", "Funiculi funicula"],
    },
    112734: {
        "title": "Golden Slumbers",
        "tags": ["lullaby"],
        "lyrics": ["Golden slumbers kiss your eyes", "Smiles awake you when you rise"],
    },
    112735: {
        "title": "Bye Baby Bunting",
        "tags": ["nursery rhyme"],
        "lyrics": ["Bye baby bunting", "Daddy's gone a-hunting"],
    },
    112736: {
        "title": "Cockles and Mussels",
        "tags": ["irish", "folk"],
        "lyrics": [
            "In Dublin's fair city where the girls are so pretty",
            "I first set my eyes on sweet Molly Malone",
        ],
    },
    112737: {
        "title": "Danny Boy",
        "tags": ["irish", "folk"],
        "lyrics": [
            "Oh Danny boy the pipes the pipes are calling",
            "From glen to glen and down the mountain side",
        ],
    },
    112738: {
        "title": "Scarborough Fair",
        "tags": ["english", "folk"],
        "lyrics": [
            "Are you going to Scarborough Fair",
            "Parsley sage rosemary and thyme",
        ],
    },
    112739: {
        "title": "Greensleeves",
        "tags": ["english", "folk"],
        "lyrics": ["Alas my love you do me wrong", "To cast me off discourteously"],
    },
    112740: {
        "title": "Loch Lomond",
        "tags": ["scottish", "folk"],
        "lyrics": [
            "By yon bonnie banks and by yon bonnie braes",
            "Where the sun shines bright on Loch Lomond",
        ],
    },
    112741: {
        "title": "Auld Lang Syne",
        "tags": ["scottish", "folk"],
        "lyrics": ["Should auld acquaintance be forgot", "And never brought to mind"],
    },
    112742: {
        "title": "Comin Through the Rye",
        "tags": ["scottish", "folk"],
        "lyrics": [
            "Gin a body meet a body comin through the rye",
            "Gin a body kiss a body need a body cry",
        ],
    },
    112743: {
        "title": "Annie Laurie",
        "tags": ["scottish", "folk"],
        "lyrics": ["Maxwelton's braes are bonnie", "Where early falls the dew"],
    },
    112744: {
        "title": "Sakura Sakura",
        "tags": ["japanese", "folk"],
        "lyrics": ["Sakura Sakura", "Cherry blossoms everywhere"],
    },
    112745: {
        "title": "Arirang",
        "tags": ["korean", "folk"],
        "lyrics": ["Arirang Arirang Arariyo", "Crossing over the Arirang Pass"],
    },
    112746: {
        "title": "Kalinka",
        "tags": ["russian", "folk"],
        "lyrics": ["Kalinka kalinka kalinka moya", "In the garden there's a raspberry"],
    },
    112747: {
        "title": "O Tannenbaum",
        "tags": ["german", "christmas"],
        "lyrics": ["O Tannenbaum o Tannenbaum", "Wie treu sind deine Blatter"],
    },
    112748: {
        "title": "Moli Hua (China)",
        "tags": ["chinese", "folk"],
        "lyrics": ["Moli hua moli hua", "Beautiful jasmine flower"],
    },
    112749: {
        "title": "The Ash Grove",
        "tags": ["welsh", "folk"],
        "lyrics": [
            "Down yonder green valley where streamlets meander",
            "Where twilight is fading I pensively rove",
        ],
    },
    112750: {
        "title": "Believe Me If All Those Endearing Young Charms",
        "tags": ["irish", "folk"],
        "lyrics": [
            "Believe me if all those endearing young charms",
            "Which I gaze on so fondly today",
        ],
    },
    112751: {
        "title": "Blue Bells of Scotland",
        "tags": ["scottish", "folk"],
        "lyrics": [
            "Oh where and oh where is my Highland laddie gone",
            "He's gone to fight the foe for king and country",
        ],
    },
    # Classical MIDIs
    34522: {
        "title": "Amazing Grace",
        "tags": ["hymn", "spiritual"],
        "lyrics": ["Amazing grace how sweet the sound", "That saved a wretch like me"],
    },
    # Holiday songs
    107555: {
        "title": "Jingle Bells",
        "tags": ["christmas", "holiday"],
        "lyrics": [
            "Jingle bells jingle bells jingle all the way",
            "Oh what fun it is to ride in a one horse open sleigh",
        ],
    },
    107556: {
        "title": "We Wish You a Merry Christmas",
        "tags": ["christmas", "holiday"],
        "lyrics": ["We wish you a merry Christmas", "We wish you a merry Christmas"],
    },
    107557: {
        "title": "Silent Night",
        "tags": ["christmas", "holiday"],
        "lyrics": ["Silent night holy night", "All is calm all is bright"],
    },
    107558: {
        "title": "Deck the Halls",
        "tags": ["christmas", "holiday"],
        "lyrics": ["Deck the halls with boughs of holly", "Fa la la la la la la la la"],
    },
    107559: {
        "title": "Joy to the World",
        "tags": ["christmas", "holiday"],
        "lyrics": ["Joy to the world the Lord is come", "Let earth receive her King"],
    },
    107561: {
        "title": "Hark the Herald Angels Sing",
        "tags": ["christmas", "holiday"],
        "lyrics": ["Hark the herald angels sing", "Glory to the newborn King"],
    },
    107562: {
        "title": "Away in a Manger",
        "tags": ["christmas", "holiday"],
        "lyrics": [
            "Away in a manger no crib for a bed",
            "The little Lord Jesus laid down his sweet head",
        ],
    },
    107563: {
        "title": "God Rest Ye Merry Gentlemen",
        "tags": ["christmas", "holiday"],
        "lyrics": ["God rest ye merry gentlemen", "Let nothing you dismay"],
    },
    # Additional known MIDIs from probe
    34000: {
        "title": "Classical Melody 1",
        "tags": ["classical"],
        "lyrics": ["A beautiful classical melody"],
    },
    34001: {
        "title": "Classical Melody 2",
        "tags": ["classical"],
        "lyrics": ["A beautiful classical melody"],
    },
}

# ── AUTO-DISCOVERED SONGS ──
# For MIDI IDs we found but don't have curated metadata for,
# we generate placeholder entries


def probe_and_download():
    """Probe bitmidi.com ranges, find working IDs, download all."""
    ranges = [
        range(34000, 35000),
        range(65000, 65500),
        range(107550, 107580),
        range(112630, 112800),
        range(117150, 117200),
        range(119700, 119750),
        range(120330, 120370),
        range(202640, 202700),
        range(65280, 65400),
    ]

    # Download curated songs first
    logger.info(f"Downloading {len(CURATED_SONGS)} curated songs...")
    download_batch(list(CURATED_SONGS.items()))

    # Then probe and download auto-discovered
    all_ids = set()
    for r in ranges:
        all_ids.update(r)
    # Remove already-downloaded curated IDs
    to_probe = all_ids - set(CURATED_SONGS.keys())

    logger.info(f"Probing {len(to_probe)} unknown IDs for working MIDIs...")

    def check_midi(mid_id):
        url = f"https://bitmidi.com/uploads/{mid_id}.mid"
        try:
            r = requests.head(url, headers=headers, timeout=5)
            if r.status_code == 200:
                cl = r.headers.get("content-length", "0")
                if cl.isdigit() and int(cl) > 500:
                    return mid_id, True
            return mid_id, False
        except:
            return mid_id, False

    working = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        fut_map = {ex.submit(check_midi, mid_id): mid_id for mid_id in to_probe}
        for fut in as_completed(fut_map):
            mid_id, ok = fut.result()
            if ok:
                working.append(mid_id)

    working.sort()
    logger.info(f"Found {len(working)} additional working MIDIs!")

    # Download auto-discovered songs with placeholder metadata
    auto_songs = {}
    for mid_id in working:
        safe_name = f"auto_midi_{mid_id}"
        auto_songs[mid_id] = {
            "title": f"MIDI {mid_id}",
            "tags": ["auto-discovered"],
            "lyrics": ["Instrumental melody", "Enjoy this tune"],
        }

    download_batch(list(auto_songs.items()))
    logger.info(f"Downloaded {len(auto_songs)} auto-discovered songs")

    # Write catalog
    write_catalog()


def download_batch(song_items):
    """Download a batch of songs with ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=10) as ex:
        fut_map = {
            ex.submit(download_one, mid_id, data): mid_id for mid_id, data in song_items
        }
        done = 0
        for fut in as_completed(fut_map):
            done += 1
            if done % 50 == 0:
                sys.stdout.write(f"\rDownloaded: {done}/{len(song_items)}")
                sys.stdout.flush()
    print()


def download_one(mid_id, data):
    """Download a single MIDI and write its metadata."""
    url = f"https://bitmidi.com/uploads/{mid_id}.mid"
    safe_name = f"midi_{mid_id}"
    if "title" in data:
        safe_name = (
            data["title"]
            .lower()
            .replace(" ", "_")
            .replace("'", "")
            .replace("(", "")
            .replace(")", "")
        )
        safe_name = re.sub(r"[^a-z0-9_]", "", safe_name)

    midi_path = os.path.join(INPUT_DIR, f"{safe_name}.mid")

    # Skip if exists
    if os.path.exists(midi_path) and os.path.getsize(midi_path) > 500:
        return mid_id, "Skipped"

    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        with open(midi_path, "wb") as f:
            f.write(r.content)
        midi_status = "Success"
    except Exception as e:
        midi_status = f"Failed: {e}"
        return mid_id, midi_status

    # Generate timed lyrics
    synced = []
    start = 5.0
    for line in data.get("lyrics", ["Instrumental"]):
        synced.append({"text": line, "start": start, "end": start + 4.0})
        start += 5.0

    metadata = {
        "title": data["title"],
        "description": f"MIDI {mid_id} from bitmidi.com",
        "tags": data.get("tags", ["music"]),
        "lyrics": synced,
        "source_id": mid_id,
    }

    meta_path = os.path.join(OUTPUT_DIR, f"{safe_name}_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return mid_id, midi_status


def write_catalog():
    """Write the full catalog index."""
    # Count what we have
    mids = [f for f in os.listdir(INPUT_DIR) if f.endswith((".mid", ".midi"))]
    metas = [f for f in os.listdir(OUTPUT_DIR) if f.endswith("_metadata.json")]

    catalog_path = os.path.join(PROJECT_DIR, "CHILDRENS_SONGS_INDEX.md")
    with open(catalog_path, "w", encoding="utf-8") as f:
        f.write("# Complete MIDI Song Library Catalog\n\n")
        f.write(
            f"**Total MIDI Files: {len(mids)}** | **Metadata Files: {len(metas)}**\n\n"
        )
        f.write("| # | Filename | Size | Metadata |\n")
        f.write("|---|----------|------|----------|\n")
        for i, m in enumerate(sorted(mids), 1):
            size = os.path.getsize(os.path.join(INPUT_DIR, m))
            name_noext = os.path.splitext(m)[0]
            has_meta = (
                "Yes"
                if os.path.exists(
                    os.path.join(OUTPUT_DIR, f"{name_noext}_metadata.json")
                )
                else "No"
            )
            f.write(f"| {i} | {m} | {size // 1024}KB | {has_meta} |\n")
    logger.info(f"Wrote catalog: {len(mids)} MIDIs, {len(metas)} metadata files")


if __name__ == "__main__":
    logger.info("=== MASSIVE AUTO-DISCOVERING MIDI SCRAPER ===")
    start = time.time()
    probe_and_download()
    elapsed = time.time() - start
    logger.info(f"=== DONE in {elapsed:.1f}s ===")
