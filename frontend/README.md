# 🧭 Career Advisor — Next.js Frontend

A modern Next.js 16 + React 19 + TypeScript frontend for the Career Advisor AI platform, with full feature parity from the Python Streamlit UI and enhanced animations, glassmorphism, and responsive interactivity.

---

## 🚀 Features Ported from Python UI

1. **✦ AI Career Agent (Chat Workspace)**:
   - Real-time conversational AI powered by Google Gemini
   - Interactive Quick Action cards for instant career questions
   - Grounded RAG citations with expandable source excerpts and relevance scores
   - Custom-rendered Markdown output with syntax highlighting, badges, and lists
   - Animated floating Mascot component with pulsating antenna and blinking eyes

2. **📄 Resume Analyzer**:
   - Client & server-side document upload (`.pdf`, `.docx`, `.txt`)
   - Automated skill extraction with interactive skill badges
   - Strengths and growth gap identification
   - ATS summary and recommended target roles with 1-click selection

3. **🎯 Skill Gap Matrix**:
   - Compare current skills against industry standard competencies
   - High / Medium / Low readiness evaluation badge
   - 3-column structured matrix: Matched Skills, Partial/Developing, and Missing Gaps
   - Direct bridges to generate custom roadmaps and search matching jobs

4. **🧭 Learning Roadmap Generator**:
   - Milestone-by-milestone structured curriculum
   - Customizable timeframe (3, 6, 9, 12 months)
   - Interactive action item checkboxes with persistent completion strike-through
   - Focus skills tags and sequential progress indicators

5. **💼 Live Job Matcher**:
   - Live job search powered by Adzuna API + local verified dataset
   - Role, Location, Key Skills, and Experience Level filters
   - Job cards with direct source tags, skill badges, descriptions, and application links

6. **⚡ Knowledge & Context Hub (Sidebar)**:
   - Reference PDF upload and indexing into ChromaDB vector store
   - Resume file status indicator
   - Student profile and background customization
   - Conversation clearing

---

## 🛠️ Getting Started

### 1. Start the FastAPI Backend
Ensure your `.env` contains your `GOOGLE_API_KEY`:
```bash
# In the root directory:
python run.py api
# Or directly:
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Start the Next.js Frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🏗️ Tech Stack
- **Framework**: Next.js 16 (App Router)
- **UI & Components**: React 19, Lucide Icons, Vanilla CSS Design System
- **Styling**: Cyberpunk dark mode with glassmorphic cards, dynamic CSS gradients, and revolving edge glow lighting
- **Backend API**: FastAPI (`server.py`)
