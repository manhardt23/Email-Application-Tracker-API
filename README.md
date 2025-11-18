# 📬 Email Application Tracker API

### 🧠 Project Overview
The goal of this project is to build a backend system that automatically scans my **Comcast/Xfinity email inbox** for job application–related messages and organizes them into a structured, trackable format.  

Right now, it’s easy to lose track of where I’ve applied and what stage each application is at. This project aims to fix that by creating a service that functions like a **personal Applicant Tracking System (ATS)** — one that helps me visualize how many applications I’ve sent, what companies I’ve interacted with, and how far I’ve progressed in the process.

---

### 🎯 Desired Outcomes
By the end of this project, I want to have:
- A functioning API that connects securely to my Comcast email using IMAP.
- Logic that automatically parses incoming emails and identifies:
  - The **company name**
  - The **position applied for**
  - The **current stage** (e.g., Applied, Interview, Offer, Rejected)
  - The **date of the email**
- A database that stores this structured data for future reference.
- API endpoints that allow me to:
  - Retrieve all applications
  - Update statuses manually
  - View analytics such as total applications and success rates

Long-term, I’d like to extend this into a small dashboard where I can visualize trends over time — such as my interview-to-offer ratio or most frequently applied job types.

---

### 🧩 How I Plan to Achieve It

**1. Email Integration (IMAP)**  
Use Python’s built-in `imaplib` or a higher-level library to connect to `imap.comcast.net`.  
Fetch and parse job-related emails using regex and keyword-based classification.

**2. Data Extraction & Classification**  
Identify key phrases like:
- “Application received” → *Applied*  
- “Interview scheduled” → *Interview*  
- “Regret to inform” → *Rejected*  
- “Offer” → *Offer*  

Then extract company and position details where possible, storing them in a structured format.

**3. Database Layer**  
Store parsed data in a database such as **MongoDB** or **Firestore**, where each record represents an application with metadata (company, position, stage, date, notes).

**4. REST API**  
Build a simple API using **FastAPI** with endpoints to:
- Trigger new email scans
- Retrieve all applications
- Update individual records
- Generate statistics about overall application progress

**5. Analytics & Future Expansion**  
Add endpoints for data insights — e.g., total applications, interviews, and offers.  
Eventually, introduce support for Gmail or Outlook and add a web dashboard using React + TailwindCSS.

---

### ⚙️ Technologies Used
- **Python** – main backend language  
- **FastAPI** – API framework  
- **SQLAlchemy** – ORM for database operations  
- **SQLite/PostgreSQL** – database for structured records (via SQLAlchemy)  
- **imaplib** – email access via IMAP  
- **LLM (Llama3)** – intelligent email classification and extraction  
- **python-dotenv** – environment variable management  

---

### 📅 Current Phase
**API Development Complete** — The following features have been implemented:

✅ **Email Processing Pipeline**
- IMAP connection to Comcast email
- LLM-powered email analysis to extract company, position, and application stage
- Automatic database storage with confidence scoring
- Email deduplication and review flagging

✅ **Database Models**
- `Company` – stores company information
- `Application` – tracks job applications with stages (applied, interview, offer, rejected, etc.)
- `ApplicationEmail` – stores email metadata and LLM-extracted information

✅ **REST API Endpoints**
- `GET /api/v1/` – API root endpoint
- `GET /api/v1/emails` – retrieve all application emails
- `POST /api/v1/run` – trigger email processing pipeline with optional limit
- `GET /api/v1/config/limit` – get current default email processing limit
- `PUT /api/v1/config/limit` – update default email processing limit
- `GET /api/v1/status` – get API health and pipeline statistics

---

### 🚀 API Documentation

#### Run Email Tracker Pipeline
**POST** `/api/v1/run?limit=<number>`

Runs the email tracker pipeline to fetch, analyze, and store application emails.

- **Query Parameters:**
  - `limit` (optional): Number of emails to process. If not provided, uses default from config.

- **Response:**
```json
{
  "status": "success",
  "message": "Processed 10 emails",
  "statistics": {
    "total_emails_in_db": 45,
    "total_applications": 12,
    "total_companies": 8
  }
}
```

#### Get Default Email Limit
**GET** `/api/v1/config/limit`

Returns the current default email processing limit.

- **Response:**
```json
{
  "limit": 10
}
```

#### Update Default Email Limit
**PUT** `/api/v1/config/limit`

Updates the default email processing limit (persisted to `.env` file).

- **Request Body:**
```json
{
  "limit": 20
}
```

- **Response:**
```json
{
  "status": "success",
  "message": "Limit updated to 20",
  "limit": 20
}
```

#### Get System Status
**GET** `/api/v1/status`

Returns API health status and comprehensive pipeline statistics.

- **Response:**
```json
{
  "status": "healthy",
  "api": {
    "version": "v1",
    "status": "operational"
  },
  "statistics": {
    "total_emails": 45,
    "total_applications": 12,
    "total_companies": 8,
    "emails_needing_review": 3,
    "applications_by_stage": {
      "applied": 5,
      "interview": 4,
      "offer": 2,
      "rejected": 1
    },
    "emails_by_confidence": {
      "high": 30,
      "medium": 10,
      "low": 5
    }
  },
  "config": {
    "default_email_limit": 10
  }
}
```

#### Get All Emails
**GET** `/api/v1/emails`

Retrieves all application emails stored in the database.

- **Response:** Array of email objects or `{"message": "No emails found"}`

---

### 🐛 Recent Bug Fixes
- Fixed `needs_review()` method call to use correct `need_review()` method name
- Fixed SQLAlchemy query in `find_or_create_company()` to use `models.Company.name` instead of `models.Company`
- Added company filtering to `find_or_create_application()` to prevent cross-company position matching
- Updated `tracker.py` to use config-based default limit instead of hardcoded value  

---

### 🧑‍💻 Author
**Jacob Manhardt**  
📧 jemanhardt@comcast.net  
🔗 [LinkedIn](https://www.linkedin.com/in/jacob-manhardt-b9b75025b/)
