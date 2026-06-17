import logging
import os
import subprocess

logger = logging.getLogger(__name__)

class OMRProcessor:
    def __init__(self):
        pass

    def is_available(self):
        """Check if the oemer CLI tool is installed and available."""
        try:
            subprocess.run(["oemer", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def process(self, image_path, output_dir):
        """
        Run Optical Music Recognition on a given image/PDF file and output a MusicXML file.

        Args:
            image_path (str): Path to the input sheet music image (png, jpg, pdf).
            output_dir (str): Directory to place the generated MusicXML file.

        Returns:
            str: The path to the generated .mxl file.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"OMR input file not found: {image_path}")

        filename = os.path.basename(image_path)
        name_no_ext = os.path.splitext(filename)[0]
        output_mxl_path = os.path.join(output_dir, f"{name_no_ext}.mxl")

        logger.info(f"Running OMR (oemer) on {image_path}...")

        # oemer usually outputs the file in the same directory as the input,
        # or takes an output path depending on its CLI options.
        # Its default behavior is `oemer <image_path>`, which produces `<image_path_no_ext>.musicxml`
        try:
            # We run oemer
            cmd = ["oemer", image_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0:
                logger.error(f"oemer failed: {result.stderr}")
                raise RuntimeError(f"OMR processing failed: {result.stderr}")

            # Locate the output file. oemer typically generates a .musicxml file in the same directory as the input.
            input_dir = os.path.dirname(image_path)
            expected_output = os.path.join(input_dir, f"{name_no_ext}.musicxml")

            if os.path.exists(expected_output):
                # Move/Rename it to our output directory as .mxl so the rest of the pipeline picks it up
                import shutil
                shutil.move(expected_output, output_mxl_path)
                logger.info(f"OMR successful. Generated: {output_mxl_path}")
                return output_mxl_path
            else:
                logger.error(f"oemer succeeded but output file {expected_output} was not found.")
                raise FileNotFoundError(f"Expected OMR output not found: {expected_output}")

        except Exception as e:
            logger.error(f"OMR Processor encountered an error: {e}")
            raise e

    def transfer_style(self, mxl_path, style_name):
        """
        Apply a musical style transfer to a generated MusicXML file using Music21.

        Args:
            mxl_path (str): Path to the source .mxl or .musicxml file.
            style_name (str): Name of the target style (e.g., 'Swing', 'Lullaby').
        """
        if not style_name or style_name.lower() == "original":
            return mxl_path

        logger.info(f"Applying style transfer '{style_name}' to {mxl_path}...")

        try:
            from music21 import converter, tempo, midi

            score = converter.parse(mxl_path)

            if style_name.lower() == "swing":
                # Implement basic swing: lengthen first 8th, shorten second
                for p in score.parts:
                    for n in p.recurse().notes:
                        if n.quarterLength == 0.5: # 8th note
                            # Position-dependent swing: lengthen 8ths on beats 1, 2, 3, 4
                            if n.beat == int(n.beat):
                                n.quarterLength = 0.67
                            else:
                                n.quarterLength = 0.33

            elif style_name.lower() == "arpeggio":
                # Convert chords to arpeggios
                for p in score.parts:
                    for n in p.recurse().notes:
                        if n.isChord:
                            # Simple arpeggio logic: spread the chord notes
                            pass # TODO: Implement complex arpeggio expansion

            elif style_name.lower() == "lullaby":
                # Slow down and soften
                for p in score.parts:
                    for m in p.getElementsByClass('Measure'):
                        m.insert(0, tempo.MetronomeMark(number=60))
                        for n in m.recurse().notes:
                            n.volume.velocity = 50

            # Save the modified score
            base, ext = os.path.splitext(mxl_path)
            output_path = f"{base}_{style_name.lower()}{ext}"
            score.write('musicxml', fp=output_path)
            return output_path

        except Exception as e:
            logger.error(f"Style transfer failed: {e}")
            return mxl_path
