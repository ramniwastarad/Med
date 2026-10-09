# MediBridge — Unified Medical Records

A HealthTech hackathon prototype for patient-owned medical history, selective temporary sharing, and explainable continuity-of-care checks.

## What works
- Demo patient sign-in (clearly marked synthetic demo account)
- Medical records timeline with search/type filters
- Add structured medical records
- Allergy/current medication summary
- ContextPass: select records, create expiring share link/QR, revoke access
- Read-only clinician view
- Server-side share token hashing, expiry/revocation validation, selected-record filtering
- Continuity Guard rules for duplicate-test candidates, stale medication data, and recorded allergy review
- PostgreSQL support, SQLite local fallback
- Seeded fictional patient and records
- Responsive React UI

> **Prototype only:** Synthetic data only. Not for clinical use, diagnosis, prescribing, or real patient data. Alerts require clinician review and are not medical advice.

## Quick start (local)
Requirements: Python 3.11+ and Node.js 20+.

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

### 2. Frontend (new terminal)
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open http://localhost:5173

### Demo
The demo app offers a **synthetic demo workspace**; no real patient data is used. Click “Enter demo workspace”. Share a few records, open the generated share URL in a private window, then revoke it and refresh to verify access is denied.

## Deployment
A `render.yaml` Blueprint is included for deployment on Render. Push this repository to GitHub, then create a new Blueprint from the repository. The Blueprint provisions a Python API and PostgreSQL database. Deploy the frontend as a static site with root `frontend`, build command `npm install && npm run build`, publish directory `dist`, and set `VITE_API_URL` to the backend URL. Set `FRONTEND_ORIGIN` on the backend to the deployed frontend URL.

A hosted URL cannot be embedded in this package until it is deployed into an account you control.

## API overview
- `GET /api/health`
- `GET /api/demo`
- `GET /api/records`
- `POST /api/records`
- `GET /api/summary`
- `GET /api/continuity`
- `POST /api/shares`
- `GET /api/shared/{token}`
- `POST /api/shares/{share_id}/revoke`
- `GET /api/audit`

## Security notes
- Share tokens are generated using Python's `secrets` module; only SHA-256 hashes are stored.
- Every shared-record request checks expiry, revocation, and selected record IDs on the server.
- Share tokens are bearer links: anyone possessing a live link can access the records selected for that grant. Do not share real medical information.
- The demo workspace is intentionally frictionless and is not authentication suitable for real health data.
- Set `FRONTEND_ORIGIN` to the exact deployed origin in production. Use HTTPS.
- Add a proper identity provider, rate limiting, audit retention policy, and security review before any real-world use.

## Third-party libraries
FastAPI, Uvicorn, SQLAlchemy, Pydantic, React, Vite, TypeScript, qrcode.react, Lucide React. Review each library's license before redistribution.

## Submission checklist
- [ ] Push repository to GitHub
- [ ] Deploy frontend and backend and verify live URLs
- [ ] Record a real 2–5 minute walkthrough of the deployed app and put it in `demo/`
- [ ] Update this README with actual URLs and demo video link
- [ ] Submit through the official hackathon Google Form before deadline
