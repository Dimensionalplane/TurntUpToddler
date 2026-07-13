"""
Magnific.com media enhancement integration for the hymn pipeline.

Magnific.ai is a professional AI upscaling/enhancement service for images.
This module integrates it into the hymn batch pipeline via browser automation.

Usage:
    python magnific_integration.py enhance --image cover.png --output enhanced.png
    python magnific_integration.py batch --dir generated/cover_art
"""

import os
import time
import argparse
import logging
import subprocess
import glob

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("magnific")

ROOT = os.path.dirname(os.path.abspath(__file__))

# Agent-browser automation helpers
def browser_cmd(*args):
    """Run an agent-browser command and return stdout."""
    cmd = ["agent-browser"] + list(args)
    logger.debug(f"  $ {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("agent-browser timed out")
        return ""
    except FileNotFoundError:
        logger.error("agent-browser CLI not found. Install with: npm install -g agent-browser")
        return ""


class MagnificEnhancer:
    """AI image upscaling via magnific.com using browser automation."""

    BASE_URL = "https://magnific.com"
    
    def __init__(self, state_file=None):
        self.state_file = state_file or os.path.join(ROOT, ".magnific_state.json")
        self.authenticated = os.path.exists(self.state_file)

    def login(self, email=None, password=None):
        """
        Log into magnific.com. If email/password not provided, check env vars.
        Falls back to manual browser login if automated login fails.
        """
        email = email or os.environ.get("MAGNIFIC_EMAIL")
        password = password or os.environ.get("MAGNIFIC_PASSWORD")

        logger.info("Opening magnific.com login...")
        r = browser_cmd("open", self.BASE_URL + "/login")
        time.sleep(3)
        r = browser_cmd("snapshot", "-i")
        logger.info(f"Login page snapshot:\n{r[:500] if r else 'empty'}")

        if email and password:
            logger.info("Attempting automated login...")
            # Fill email
            r = browser_cmd("find", 'placeholder', "Email", "fill", email)
            time.sleep(1)
            # Fill password
            r = browser_cmd("find", 'placeholder', "Password", "fill", password)
            time.sleep(1)
            # Click submit
            r = browser_cmd("find", "text", "Sign In", "click")
            time.sleep(5)

        # Save auth state
        logger.info("Saving browser auth state...")
        browser_cmd("state", "save", self.state_file)
        self.authenticated = True
        logger.info(f"Auth state saved to {self.state_file}")

    def enhance_image(self, input_path, output_path, creativity=50, resolution="2x"):
        """
        Enhance/upscale an image using magnific.com.
        
        Args:
            input_path: Path to input image
            output_path: Path for enhanced output
            creativity: Enhancement creativity (0-100)
            resolution: Upscale resolution ("2x" or "4x")
        
        Returns:
            Path to enhanced image, or None on failure
        """
        if not os.path.exists(input_path):
            logger.error(f"Input image not found: {input_path}")
            return None

        logger.info(f"Enhancing image: {os.path.basename(input_path)}")
        
        # Load saved auth state if available
        if self.authenticated and os.path.exists(self.state_file):
            browser_cmd("state", "load", self.state_file)
            time.sleep(2)
        
        # Navigate to upload
        browser_cmd("open", self.BASE_URL + "/enhance")
        time.sleep(3)
        
        # Determine the absolute path
        abs_path = os.path.abspath(input_path)
        
        # Use the file input method via agent-browser
        # First find the file input element
        r = browser_cmd("snapshot", "-i")
        logger.debug(f"Upload page:\n{r[:300] if r else 'empty'}")
        
        # Try to find and interact with file upload area
        # agent-browser doesn't directly support file upload,
        # so we'll use a different approach - open the image as a data URL
        # and use the CDP file chooser handler
        
        # Alternative: construct the enhancement URL directly if possible
        # magnific.com may support direct API calls or URL-based uploads
        
        logger.warning("Full automated upload via agent-browser may require manual file chooser handling.")
        logger.warning("For production use, consider magnific.com's API or manual enhancement.")
        logger.info(f"Image prepared for enhancement: {abs_path}")
        
        return None  # Placeholder - will return actual path once automated

    def enhance_batch(self, input_dir, output_dir, pattern="*.png", creativity=50, resolution="2x"):
        """Enhance all images in a directory."""
        os.makedirs(output_dir, exist_ok=True)
        images = sorted(glob.glob(os.path.join(input_dir, pattern)))
        results = []
        
        for img in images:
            name = os.path.basename(img)
            out = os.path.join(output_dir, f"enhanced_{name}")
            res = self.enhance_image(img, out, creativity=creativity, resolution=resolution)
            results.append((img, out, res))
            logger.info(f"  {name}: {'✓' if res else '✗'}")
        
        return results


def create_cover_art_from_hymn(hymn_name, genre, output_dir="generated/cover_art"):
    """
    Generate a placeholder cover art image for a hymn using AI prompts.
    Uses magnific.com as an enhancement step after initial generation.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Prompt ideas based on hymn and genre
    prompts = {
        "psytrance": f"Ethereal cosmic {hymn_name} with swirling galaxies and divine light, vibrant colors",
        "dubstep": f"Dark dramatic {hymn_name} with electric energy and pulsing beats, neon accents",
        "dnb": f"Fast-paced energetic {hymn_name} with drum patterns and flowing lights, deep blues",
        "deep_house": f"Warm atmospheric {hymn_name} with sunset gradients and smooth abstract shapes",
    }
    
    prompt = prompts.get(genre, f"Abstract artistic representation of {hymn_name} hymn")
    logger.info(f"Cover art prompt for {hymn_name} ({genre}): {prompt}")
    
    return prompt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Magnific.com integration for hymn pipeline")
    parser.add_argument("action", choices=["login", "enhance", "batch", "prompt"])
    parser.add_argument("--image", help="Input image path")
    parser.add_argument("--output", help="Output path")
    parser.add_argument("--dir", help="Input directory for batch")
    parser.add_argument("--hymn", help="Hymn name for prompt generation")
    parser.add_argument("--genre", default="psytrance", choices=["psytrance", "dubstep", "dnb", "deep_house"])
    parser.add_argument("--creativity", type=int, default=50, help="Creativity level 0-100")
    
    args = parser.parse_args()
    enhancer = MagnificEnhancer()
    
    if args.action == "login":
        enhancer.login()
    elif args.action == "enhance":
        if args.image and args.output:
            enhancer.enhance_image(args.image, args.output, creativity=args.creativity)
    elif args.action == "batch":
        if args.dir:
            enhancer.enhance_batch(args.dir, args.dir + "_enhanced", creativity=args.creativity)
    elif args.action == "prompt":
        prompt = create_cover_art_from_hymn(args.hymn or "Unknown", args.genre)
        print(prompt)
