# Online Plagiarism Checker

## Overview

A full-stack web application that analyzes submitted text and uploaded TXT, PDF, and DOCX documents for potential public-web content similarity using Google Programmable Search, TF-IDF, and cosine similarity.

## Features

- Text analysis and TXT/PDF/DOCX uploads
- Text extraction and whitespace normalization
- Google Programmable Search discovery, followed by accessible-page TF-IDF and cosine-similarity matching
- Overall plagiarism percentage and Low/Medium/High similarity levels
- Source information for meaningful matches
- Django REST API and responsive React interface

## Architecture

```text
React
  ↓
Axios
  ↓
Django REST API
  ↓
Text extraction
  ↓
TF-IDF
  ↓
Cosine similarity
  ↓
Plagiarism report
```

## Tech Stack

**Frontend:** React, Vite, JavaScript, CSS, Axios

**Backend:** Python, Django, Django REST Framework

**ML/Text processing:** scikit-learn, TF-IDF, cosine similarity

**Document processing:** pdfplumber, python-docx

## API

- `GET /api/health/`
- `POST /api/check-plagiarism/` — accepts JSON `{ "text": "..." }` or multipart form data with a `file` field.

## Local Setup

### Backend

From the project root in PowerShell:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/api`.

### Frontend

In a second terminal, from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/`.

## Environment Variables

Backend variables belong in `backend/.env` locally and in Render's environment settings for deployment. Start from `backend/.env.example`.

- `DJANGO_SECRET_KEY` — a unique, private Django secret key. Required when `DEBUG=False`.
- `DEBUG` — use `True` locally and `False` in production.
- `ALLOWED_HOSTS` — comma-separated hostnames, such as `your-service.onrender.com`.
- `CORS_ALLOWED_ORIGINS` — comma-separated frontend origins. Include `http://localhost:5173` locally and the deployed Netlify URL in production.

Frontend variables belong in `frontend/.env` locally and in Netlify's environment settings. Start from `frontend/.env.example`.

- `VITE_API_URL` — the backend API base URL, for example `http://127.0.0.1:8000/api` locally or `https://your-service.onrender.com/api` on Netlify.

## Deployment Commands

For a Render web service with `backend` set as the root directory:

```text
Build command: pip install -r requirements.txt && python manage.py collectstatic --noinput
Start command: gunicorn config.wsgi:application
```

## Limitations

The application uses Google Programmable Search to discover potentially matching public web sources and compares submitted content with accessible result pages using TF-IDF and cosine similarity. Each analysis makes at most five search queries and fetches at most ten unique result pages, so Google API quota and pages that block normal HTTP access can limit coverage. This is a similarity analysis tool, not a definitive plagiarism or academic-integrity verdict, and it does not claim complete internet coverage.

## Future Enhancements

- Larger, replaceable source corpus
- Persistent analysis history
- Authentication
- Improved similarity algorithms
