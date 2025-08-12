# DB-LLM Chat

A full-stack app that lets you connect to a database, ask **natural-language** questions, and get **SQL + results** from an LLM.

Backend: **FastAPI (Python)** · Frontend: **React (Vite)** · Keys encrypted with **Fernet**.

---
## Project Structure

```text
db_llm/
├─ app.py                       # FastAPI app & routes
├─ core/
│  ├─ db.py                     # DB registry + resolver for LangChain SQLDatabase
│  ├─ llm.py                    # LLM -> SQL + execution + pagination
│  ├─ api_keys.py               # encrypt/decrypt, save/delete provider keys
│  ├─ auth_utils.py             # current user helpers
│  ├─ s3_utils.py               # saved queries (S3)
├─ db/
│  ├─ model.py                  # SQLModel models: User, Connection, APIKey
│  └─ main.py                   # (legacy helpers if present)
├─ data/
│  ├─ db_llm.sqlite3            # app DB for users/connections/keys
│  └─ northwind_small.sqlite    # sample data
└─ frontend/
   ├─ index.html
   └─ src/
      ├─ api.js                 # Axios client
      ├─ App.jsx                # main UI
      └─ components/
         ├─ ChatLayout.jsx
         └─ Message.jsx
```
## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm**
- (Optional) **AWS** credentials if you want S3 save/load

## Backend — Setup & Run

### 1. Create venv & install dependencies

```bash
cd db_llm
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

```
### 2. Ensure data files exist

- `data/northwind_small.sqlite` — sample DB (already in `data/`)

> **Windows tip:** the backend looks for SQLite files under the repo’s `data/` directory.  
> If you see “file not found,” make sure the filename you pick in the UI **exactly** matches the file in `data/`.
---
### 3. (Optional) S3 environment

Create a `.env` in the repo root if you’ll use **Save Query**:

```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=your-bucket-name-here
```
### 4. Run the API

```bash
uvicorn app:app --reload --port 8000
- **Docs:** http://127.0.0.1:8000/docs  
- **CORS:** allows `http://localhost:5173` for the frontend
```
## Frontend — Setup & Run

### 1. Install dependencies
```bash
cd frontend
npm i
```
### 2. Point frontend to the API

Create `frontend/.env.local`:

```ini
VITE_API_BASE_URL=http://127.0.0.1:8000
```
### 3. Run the dev server

```bash
npm run dev
```
## How to Use

1) **Register → Login**  
   Enter any name/email/password. On login the frontend stores your bearer token.

2) **Generate Fernet Key**  
   Click **Generate Fernet Key** (saves to your user row). Used to encrypt provider API keys.

3) **Save a Provider API Key**  
   Choose provider (**openai** or **together**) → paste key → **Save API Key**.

4) **Add a DB Connection**
   - **DB Type:** `sqlite`  
   - **Connection Name:** for the sample DB use **`northwind_small.sqlite`**  
   - **Save Connection**, then select it in “Choose connection”.

5) **Load Models**  
   Choose provider → pick a model from **Models** (e.g., `gpt-4o`, or a Together Llama model).

6) **Ask a Question**  
   Example: “Show all customers”. The UI displays:
   - your **Question**
   - generated **SQL** (formatted)
   - **paginated table** (Prev/Next, page size)
   - record count summary

7) **(Optional) Save Query**  
   If S3 is configured, save queries (via button/flow in UI).

## Security Model (Dev)

- Each user has a **Fernet key** (stored in `User`).
- Provider keys are **encrypted with that Fernet key** and stored in `APIKey`.
- If you **regenerate the Fernet key**, you must **re-save provider keys** so they decrypt correctly.
---
## Pretty Results (Optional Enhancements)

- SQL formatting (e.g., `sql-formatter`) + syntax highlighting (`highlight.js`)
- **Copy SQL** button
- “**Showing X–Y of N**” and a **page size selector** (10/25/50/100)
- **Sortable** table headers
- **Export** to CSV/JSON

> These are UI concerns and do not change backend contracts.
---
## Extending to Postgres / MySQL

The `Connection` model supports:
`db_type`, `db_host`, `db_port`, `db_user`, `db_password`, `connection_name`.

**SQLAlchemy URIs:**
- `postgresql://user:pass@host:port/dbname`
- `mysql+pymysql://user:pass@host:port/dbname`

Ensure the DB is reachable from where FastAPI runs.
