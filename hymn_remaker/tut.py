"""tut.py — TurntUpToddler master pipeline runner.

Usage:
    python tut.py render twinkle_twinkle              # Step 2: render WAVs
    python tut.py render --all                        # render all songs
    python tut.py generate twinkle_twinkle             # Step 3: generate Suno tracks
    python tut.py generate twinkle_twinkle --genre goa # one genre
    python tut.py cover twinkle_twinkle                # Step 4: melody-faithful covers
    python tut.py cover --all --genre goa              # all songs, one genre
    python tut.py full twinkle_twinkle                 # Steps 2+4: render + cover
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("tut")


def cmd_render(args):
    from tut_pipeline.tut_render import main as render_main
    import sys as _sys

    _sys.argv = ["tut_render.py"] + args.split() if args else ["tut_render.py", "--all"]
    render_main()


def cmd_generate(args):
    from tut_pipeline.tut_generate import main as gen_main
    import sys as _sys

    _sys.argv = ["tut_generate.py"] + args.split() if args else []
    gen_main()


def cmd_cover(args):
    from tut_pipeline.tut_cover import main as cover_main
    import sys as _sys

    _sys.argv = ["tut_cover.py"] + args.split() if args else []
    cover_main()


def main():
    import sys as _sys

    if len(_sys.argv) < 2:
        print(__doc__)
        return

    cmd = _sys.argv[1]
    rest = " ".join(_sys.argv[2:])

    if cmd == "render":
        cmd_render(rest)
    elif cmd == "generate":
        cmd_generate(rest)
    elif cmd == "cover":
        cmd_cover(rest)
    elif cmd == "full":
        cmd_render(rest)
        cmd_cover(rest)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
