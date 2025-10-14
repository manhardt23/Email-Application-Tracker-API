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

### ⚙️ Technologies I Plan to Use
- **Python** – main backend language  
- **FastAPI** – API framework  
- **MongoDB** / **Firestore** – database for structured records  
- **imaplib / mailparser** – email access and parsing  
- **Render / Railway** – for hosting the backend  

---

### 📅 Current Phase
Currently in the **planning and prototyping** stage — focusing on:
- Establishing secure IMAP connection with Comcast  
- Designing data model and parsing logic  
- Structuring FastAPI endpoints  

---

### 🧑‍💻 Author
**Jacob Manhardt**  
📧 jemanhardt@comcast.net  
🔗 [LinkedIn](https://www.linkedin.com/in/jacob-manhardt-b9b75025b/)
