# Deployment Instructions

## Docker Compose (Recommended)
1. Ensure Docker Desktop is running.
2. In the project root, run: `docker compose up --build -d`
3. Access the Streamlit UI at `http://localhost:8501`.

## Local Virtual Environment
1. Ensure `ffmpeg` and `fluidsynth` are installed on your OS (`sudo apt install ffmpeg fluidsynth fluid-soundfont-gm`).
2. Run `pip install -r requirements.txt`.
3. Start the UI: `python -m streamlit run app.py`
