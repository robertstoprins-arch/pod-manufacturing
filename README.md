# Manufacture Suite Project

## Overview

Welcome to the Manufacture Suite project! This application is designed to streamline the process of configuring, quoting, designing, and manufacturing modular building components (pods). It automates various stages of the manufacturing workflow, from initial lead to final handover, providing tools for:

*   Creating and managing product specifications.
*   Generating detailed drawings.
*   Producing Bills of Materials (BOMs) and Material Take-Offs (MTOs).
*   Generating client-facing quotes and internal technical packs.

## Project Structure

This project follows a monorepo-like structure with a clear separation between the frontend and backend:

*   `./`: Project root, contains overall configuration, deployment files (`DEPLOY.md`, `vercel.json`), and general documentation (`README.md`).
*   `api/`: Vercel serverless entry point for the FastAPI backend. Acts as an ASGI middleware to route requests to the main backend application.
*   `backend/`: Contains the FastAPI Python backend application, including API definitions, business logic (`skills/`), database models, migrations, and seeding scripts.
*   `docs/`: Project documentation, including agent guardrails and architecture notes.
*   `public/`: Static assets for the frontend.
*   `scripts/`: Utility scripts for various project tasks.
*   `src/`: The React frontend application.
*   `tools/`: Additional development or utility tools.

## Technology Stack

*   **Frontend:** React, Vite, Tailwind CSS
*   **Authentication:** Clerk
*   **Backend:** FastAPI (Python), SQLAlchemy, Alembic
*   **Database:** PostgreSQL (Neon)
*   **Message Queue:** Redis (Upstash) with Celery
*   **Deployment:** Vercel (Frontend), Render (Backend)

## Local Development Setup

To get the Manufacture Suite running on your local machine, follow these steps:

### 1. Prerequisites

Ensure you have the following installed:

*   Node.js (LTS version recommended)
*   Python 3.11+
*   Poetry (for Python dependency management: `pip install poetry`)
*   Docker (optional, for local PostgreSQL and Redis if not using cloud services)

### 2. Environment Variables

Create `.env` files in the root and `backend/` directories based on the provided examples:

*   Copy `./.env.example` to `./.env`
*   Copy `./backend/.env.example` to `./backend/.env`

Edit these `.env` files with your local or development environment configurations. For database and Redis, you can either set up local instances with Docker or use free-tier cloud services like Neon and Upstash.

### 3. Backend Setup

Navigate to the `backend/` directory and install Python dependencies:

```bash
cd backend
poetry install
```

Apply database migrations and seed data (ensure your `DATABASE_URL` in `backend/.env` is configured):

```bash
bash -c "source ./.env && poetry run alembic upgrade head"
# Run manual migration scripts (refer to DEPLOY.md for the exact order and commands)
# Example:
# bash -c "source ./.env && poetry run python migrate_finish_catalogue.py"
bash -c "source ./.env && poetry run python seeds/finish_catalogue_seed.py"
```

Start the backend development server:

```bash
bash -c "source ./.env && poetry run uvicorn app.main:app --reload"
```

### 4. Frontend Setup

Navigate back to the project root and install Node.js dependencies:

```bash
cd .. # if you are in backend/
npm install
```

Start the frontend development server:

```bash
npm run dev
```

Your frontend application should now be accessible, typically at `http://localhost:5173`.

## Running Tests

### Backend Tests

Navigate to the `backend/` directory and run pytest:

```bash
cd backend
poetry run pytest
```

### Frontend Tests

(Coming Soon: Information on running frontend tests will be added here.)

## Deployment

Refer to the `DEPLOY.md` file for detailed instructions on deploying the Manufacture Suite to Vercel (frontend) and Render (backend) with Neon (PostgreSQL) and Upstash (Redis).

## Contributing

Guidelines for contributing to the project will be added here.
