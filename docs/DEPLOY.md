# DEPLOYMENT GUIDE - HYMN REMAKER

## PREREQUISITES
- Docker & Docker Compose.
- Kubernetes Cluster (optional, for cluster mode).
- Redis (Job Telemetry) & RabbitMQ (Task Broker).
- API Keys: OpenAI, Replicate, ElevenLabs, Google Cloud (YouTube).

## LOCAL SETUP (DOCKER COMPOSE)
1. Configure `.env` with required API keys.
2. Run `docker-compose up --build`.
3. Frontend available at `http://localhost:3000`, API at `http://localhost:8000`.

## KUBERNETES DEPLOYMENT
1. Navigate to `kubernetes/base`.
2. Apply manifests: `kubectl apply -k .`.
3. Ensure PV/PVC are provisioned for `output/` storage.

## WORKER SCALING
Workers can be scaled independently via K8s deployments. The distributed nature allows render nodes to be added dynamically to clear the RabbitMQ queue.

## CI/CD PATTERNS
- **3-Stage Builds:** ML layers are cached in the `ml-deps` stage to speed up deployment cycles.
