# Competitions Service (Backend + Frontend + Worker + Cron)

This project provides a minimal competitions platform:
- Organizers create events
- Participants register
- A worker processes post-registration jobs (confirmation, outbox email)
- A cron-like job schedules reminder jobs 24h before events
- Simple React frontend for basic interaction

## Run locally (without Docker)
- Backend: FastAPI on 8000 (uses MongoDB)
- Frontend: Vite React on 3000

1. Set environment
```
export DATABASE_URL="mongodb://localhost:27017"
export DATABASE_NAME="competitions"
```
2. Start backend: `python backend/main.py`
3. Start worker: `python backend/worker.py`
4. Start cron: `python backend/cron.py` (or schedule via cron)
5. Frontend: `npm --prefix frontend run dev`

## Run with docker-compose
```
docker-compose up --build
```
Services:
- mongo: MongoDB
- api: FastAPI backend
- worker: background worker polling jobs collection
- cron: periodic scheduler adding reminder jobs
- web: Vite React frontend

## API Sketch
- POST /organizers {name, email, organization?}
- GET /organizers
- POST /events {organizer_id, title, description?, location?, start_at?, end_at?, capacity?, is_published?}
- GET /events?organizer_id=&published=
- GET /events/{id}
- POST /events/{id}/register {participant_name, participant_email}
- GET /events/{id}/registrations

## Notes
- Schemas defined in backend/schemas.py
- Worker consumes jobs of type `post_registration` to confirm and create outbox emails
- Cron enqueues `send_reminder` jobs for upcoming events; you can extend worker to handle them
