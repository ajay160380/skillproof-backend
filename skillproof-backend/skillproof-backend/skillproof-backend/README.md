<div align="center">
  
# 🚀 SkillProof

**An AI-Verified Practical Skill Portfolio Platform**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://reactjs.org/)
[![Django](https://img.shields.io/badge/Django-5.0-092E20.svg)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A.svg)](https://docs.celeryq.dev/)

*Prove what you can do. Get verified credentials through AI-monitored practical tests.*

[Live Frontend (Vercel)](https://skillproof-eight.vercel.app) · [Backend API (Render)](https://skillproof-backend-3857.onrender.com)

</div>

---

## 📖 Table of Contents
- [About the Project](#-about-the-project)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [License](#-license)

---

## 🌟 About the Project

SkillProof bridges the gap between claims on a resume and actual capabilities. By utilizing advanced AI monitoring and real-time code evaluation, SkillProof provides an undeniable, cryptographically verified portfolio of a candidate's practical skills.

### 🎯 Why SkillProof?
- **For Candidates:** Stop relying on static resumes. Show actual proof of your coding abilities.
- **For Recruiters:** Hire with confidence knowing the candidate's skills are verified in a proctored environment.

---

## ✨ Key Features

- 🤖 **AI-Observed Assessments:** Real-time monitoring and scoring of practical tests.
- 📜 **Verified Portfolios:** Shareable, tamper-proof credentials for recruiters.
- 💻 **Live Code Evaluation:** Secure execution and semantic analysis of submitted code.
- 🎨 **Premium UI/UX:** Built with Framer Motion and Tailwind for a rich, dynamic experience.
- ⚡ **Asynchronous Processing:** Celery & Redis backed AI scoring for non-blocking operations.

---

## 🏗 System Architecture

The application follows a decoupled microservices-inspired architecture:

```mermaid
graph TD
    %% Styling
    classDef frontend fill:#3b82f6,stroke:#1d4ed8,stroke-width:2px,color:#fff;
    classDef backend fill:#10b981,stroke:#047857,stroke-width:2px,color:#fff;
    classDef db fill:#f59e0b,stroke:#b45309,stroke-width:2px,color:#fff;
    classDef external fill:#6366f1,stroke:#4338ca,stroke-width:2px,color:#fff;

    Client([🌐 User Browser])

    subgraph "Frontend Layer (Vercel)"
        React[⚛️ React 19 + Vite App]:::frontend
        State[Zustand State]:::frontend
        React --> State
    end
    
    subgraph "Backend Layer (Render)"
        Django[🐍 Django REST API]:::backend
        Celery[⚙️ Celery Workers]:::backend
        AI[🧠 AI Scoring Engine]:::backend
        Django -.->|Queues Tasks| Celery
        Celery -->|Processes| AI
    end
    
    subgraph "Data Layer"
        DB[(🐘 PostgreSQL)]:::db
        Redis[(🔴 Redis / Upstash)]:::db
    end
    
    Client == HTTPS ==> React
    React == REST API ==> Django
    Django <== Reads/Writes ==> DB
    Django == Publishes ==> Redis
    Redis == Subscribes ==> Celery
```

### 🔄 User Assessment Workflow

This sequence diagram illustrates how a candidate is evaluated in real-time:

```mermaid
sequenceDiagram
    autonumber
    participant U as 🧑‍💻 Candidate
    participant F as ⚛️ Frontend
    participant B as 🐍 Backend API
    participant AI as 🧠 AI Engine
    
    U->>F: Starts Practical Assessment
    F->>B: Fetch Coding Challenge
    B-->>F: Returns Challenge Details
    U->>F: Writes & Submits Code
    F->>B: Sends Code Payload
    B->>AI: Trigger Async Analysis (via Celery)
    AI-->>B: Returns Final Score & Feedback
    B-->>F: Updates Assessment Status
    F-->>U: Issues Verified Skill Badge
```

---

## 💻 Tech Stack

<details>
<summary><b>Frontend Details</b></summary>

- **Core:** React 19, TypeScript, Vite
- **Styling:** Tailwind CSS 4, Framer Motion
- **State Management:** Zustand
- **Editor:** Monaco Editor (`@monaco-editor/react`)
- **Routing:** React Router v7
- **Deployment:** Vercel
</details>

<details>
<summary><b>Backend Details</b></summary>

- **Core:** Python 3.11+, Django, Django REST Framework
- **Database:** PostgreSQL (Production: Supabase) / SQLite (Local)
- **Background Tasks:** Celery, Redis (Production: Upstash)
- **Deployment:** Render
</details>

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

<p align="center">
  Built with ❤️ by Ajay Vishwakarma
</p>
