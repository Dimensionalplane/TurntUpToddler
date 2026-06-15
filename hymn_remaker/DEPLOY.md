# Deployment Instructions

## Docker Compose (Recommended)
1. Ensure Docker Desktop is running.
2. In the project root, run: `docker compose up --build -d`
3. Access the Next.js Frontend at `http://localhost:3000` and FastAPI at `http://localhost:8000`.

## Kubernetes
1. Configure `kustomization.yaml` in `kubernetes/base`.
2. Apply: `kubectl apply -k kubernetes/base`.

## Local Virtual Environment (Dev)
1. Ensure `ffmpeg` and `fluidsynth` are installed on your OS.
2. Run `pip install -r requirements.txt`.
3. Start the API: `python hymn_remaker/api.py`.
4. Start the Frontend: `cd frontend && npm install && npm run dev`.
