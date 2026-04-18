import logging
import os
from music21 import converter

logger = logging.getLogger(__name__)

class MusicXMLParser:
    def __init__(self):
        pass

    def process(self, input_path, output_midi_path):
        """
        Parses a MusicXML file (.xml or .mxl), extracts metadata, and converts it to a standard MIDI file
        for the pipeline to render.

        Args:
            input_path (str): Path to the input .mxl or .xml file.
            output_midi_path (str): Path where the converted .mid file should be saved.

        Returns:
            dict: Extracted metadata, such as title, composer, and a string of lyrics.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        logger.info(f"Parsing MusicXML file: {input_path}")

        try:
            # Parse the score
            score = converter.parse(input_path)

            metadata = {
                "title": None,
                "composer": None,
                "lyrics": []
            }

            # Extract metadata
            if score.metadata is not None:
                if score.metadata.title:
                    metadata["title"] = score.metadata.title
                if score.metadata.composer:
                    metadata["composer"] = score.metadata.composer

            # Extract lyrics
            # We iterate through all notes in the score and extract lyric text
            # This is a simplified extraction; complex scores may have multiple lyric lines
            lyrics_text = []
            for n in score.flat.notes:
                if hasattr(n, 'lyric') and n.lyric is not None:
                    lyrics_text.append(n.lyric)

            if lyrics_text:
                # Clean up syllabic hyphens (e.g. "Hal" "-" "le" "-" "lu" "jah")
                # We'll just join them and replace '-' with empty string for now
                raw_lyrics = " ".join(lyrics_text)
                # In MusicXML, a hyphen often means a syllable break.
                # A basic cleanup:
                clean_lyrics = raw_lyrics.replace(" - ", "").replace("- ", "").replace(" -", "")
                metadata["lyrics"] = clean_lyrics

            # Convert to MIDI and save
            logger.info(f"Converting {input_path} to MIDI: {output_midi_path}")
            score.write('midi', fp=output_midi_path)

            return metadata

        except Exception as e:
            logger.error(f"Failed to parse MusicXML: {e}")
            raise e
