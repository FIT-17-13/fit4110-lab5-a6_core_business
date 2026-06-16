.PHONY: install lint build run compose-up compose-down logs test-compose

# Install Node dependencies for Prism/Spectral/Newman
install:
	npm install

# Lint OpenAPI contracts with Spectral
lint:
	npx spectral lint contracts/*.yaml

# Build Docker image for Core Business API only
build:
	docker build -t fit4110/core-business:v0.1.0-team-core .

# Run API container standalone (not via compose)
run:
	docker run --rm --name fit4110-core-lab05 -p 8000:8000 --env-file .env.example fit4110/core-business:v0.1.0-team-core

# Compose commands
compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

logs:
	docker compose logs -f

# Run Newman tests on compose stack
test-compose:
	npm run test:compose
