# Changelog

All notable changes to this project will be documented in this file.

## [V1.0.1]

- Added GitHub Actions workflow (`.github/workflows/ping.yml`) to:
  - Ping `/health` endpoint every 10 minutes to prevent backend cold starts
  - Run on push and pull requests to all branches
  - Provide detailed logs with response body and status code
  - Fail the job if backend health check returns a non-200 status
  
## [V1.0.0]

- Project initialized with FastAPI backend structure
- Integrated Neo4j graph database client for advanced querying
- Integrated OpenAI client for LLM and TTS features
- Implemented core API endpoints:
  - `/health` for service status
  - `/qa` for question answering and part lookup
  - `/actions` for timeline resolution and narration
- Added OpenAI Whisper TTS support for text-to-speech
- Created initial graph seeding script for Neo4j
