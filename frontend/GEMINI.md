# Project Overview

This is a full-stack web application called "InfraChat", designed as an AI-powered assistant for interacting with infrastructure. The project consists of a Next.js frontend and a Python backend.

## Frontend

The frontend is a Next.js application that provides a chat interface for interacting with the AI assistant. It uses NextAuth.js for authentication, Prisma for the ORM, and a local SQLite database for storing user data and chat sessions. The UI is built with Tailwind CSS and the shadcn/ui component library. A key feature is the dynamic pane system, which displays structured data (like URLs, credentials, or SSH commands) in side panels.

## Backend

The backend is a Python-based Retrieval-Augmented Generation (RAG) system that provides the AI capabilities for the application. It uses a combination of technologies to ingest and process data from various sources, including:

*   **Prometheus:** For collecting metrics.
*   **Loki:** For aggregating logs.
*   **Network Scans:** For discovering network devices.

The backend uses a Qdrant vector database to store and search for information, and a local LLM via Ollama for generating responses. The entire backend is containerized and can be run using Docker Compose.

# Building and Running

## Frontend

To run the frontend, you will need to have Node.js (version 18 or higher) and npm installed.

1.  **Install dependencies:**
    ```bash
    npm install
    ```

2.  **Set up environment variables:**
    Create a `.env` file and add the following:
    ```
    DATABASE_URL="file:./db/custom.db"
    NEXTAUTH_URL="http://localhost:3001"
    NEXTAUTH_SECRET="your-secret-key-here"
    ```

3.  **Push database schema:**
    ```bash
    npm run db:push
    ```

4.  **Start the development server:**
    ```bash
    npm run dev
    ```

The application will be available at `http://localhost:3001`.

## Backend

To run the backend, you will need to have Docker and Docker Compose installed.

1.  **Start the services:**
    ```bash
    cd backend
    docker-compose up -d
    ```

2.  **Pull an LLM model:**
    ```bash
    docker-compose exec ollama ollama pull llama2
    ```

3.  **Run an initial scan:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/scan \
      -H "Content-Type: application/json" \
      -d '{"mode": "full"}'
    ```

The backend API will be available at `http://localhost:8000`.

# Development Conventions

## Frontend

*   The frontend code is located in the `src` directory.
*   The code is written in TypeScript.
*   The project uses ESLint for linting. You can run the linter with `npm run lint`.
*   The project uses Prisma for database migrations. You can create a new migration with `npm run db:migrate`.

## Backend

*   The backend code is located in the `backend` directory.
*   The code is written in Python.
*   The project uses FastAPI for the web framework.
*   The project uses Docker and Docker Compose for deployment.
*   The project uses pytest for testing. You can run the tests with `pytest`.
