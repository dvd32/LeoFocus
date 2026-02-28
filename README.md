# 🎨 LeoFocus

### *Observing your craft with keen eyes*

LeoFocus is an intelligent **focus-tracking and study-session analysis system** inspired by *Leonardo da Vinci*.
It monitors your real activity (apps, window switches, keystrokes, idle time) and uses an **LLM-powered reasoning engine** to provide **real-time feedback**, emotional reactions, and a **final performance report** at the end of each session.

Unlike simple app blockers, **LeoFocus observes how you actually work**.

---

## ✨ Features

### 🧠 Intelligent Focus Analysis

* Tracks **active windows**, **time spent per app**, and **window switching**
* Measures **keystrokes**, **mouse activity**, and **idle periods**
* Detects **distractions** context-aware (e.g. browser tabs, social media)

### 🎭 Leonardo Avatar (LLM-Driven)

* Acts as a **virtual mentor**
* Emotion changes dynamically:

  * 😊 *Happy* → high focus
  * 😐 *Observing* → moderate focus
  * 😠 *Angry* → high distraction
* Short, punchy feedback every 30 seconds

### 📊 Real-Time Session Metrics

* Live focus score
* Active application tracking
* Productivity status (good / warning / bad)
* Immediate alerts for heavy distraction

### 📜 Final “Session Codex” Report

At the end of a session, LeoFocus generates a **Markdown report** including:

* Final focus score and grade
* Deep work time
* Distraction analysis
* Trend detection (improving / stable / declining)
* Top applications used
* Actionable “Virtù Principles”
* A concrete target for the next session

---

## 🏗️ Architecture Overview

```
Flutter (UI)
   │
   │  JSON over stdout / stdin
   ▼
Python Backend (trackers.py)
   │
   ├── Activity Tracking (pynput, pygetwindow)
   ├── Focus & Distraction Logic
   ├── Session Memory (JSON)
   └── LLM Reasoning Engine
           ├── Groq (default)
```

### Why this architecture?

* ✅ Cross-platform (Windows, macOS, Linux)
* ✅ Real OS-level activity (not browser-only)
* ✅ LLM-powered reasoning without blocking the UI
* ✅ Clean IPC via JSON streams

---

## 🧪 How LeoFocus Works

1. **Start a session**

   * User provides a goal (e.g. *“studying maths”*)
   * Leonardo gives initial advice

2. **Live tracking**

   * Every second: activity metrics sent to Flutter
   * Every 30 seconds: LLM evaluates behavior and updates emotion + focus score

3. **Distraction detection**

   * App-based (e.g. WhatsApp, YouTube)
   * Browser-tab-based (e.g. Reddit, Netflix)
   * Context-aware overrides (allowed apps if mentioned in goal)

4. **End session**

   * Clean shutdown via stdin (cross-platform safe)
   * Final report generated using **real session data**

---

## 🖥️ Supported Platforms

| Platform    | Status                                  |
| ----------- | --------------------------------------- |
| Windows     | ✅ Fully supported                       |
| macOS       | ✅ Fully supported                       |
| Linux       | ✅ Fully supported                       |
| Flutter Web | ⚠️ UI works, backend still runs locally |

---

## 🔧 Installation & Setup

### 1️⃣ Prerequisites

#### System

* Python **3.9+**
* Flutter **3.19+**
* Git

#### Python packages

```bash
pip install pynput pygetwindow groq requests
```

> On Windows, you may also need:

```bash
pip install pywin32
```

---

### 2️⃣ Clone the repository

```bash
git clone https://github.com/your-username/leofocus.git
cd leofocus
```

---

### 3️⃣ Backend setup

```bash
cd leonardo_backend/trackers
python --version
```

---

### 4️⃣ LLM Configuration

LeoFocus supports different **LLM providers** but right now is using Groq:

#### 🟢 Groq

* Free
* Extremely fast

```bash
export GROQ_API_KEY="your_key_here"
```

Windows:

```powershell
setx GROQ_API_KEY "your_key_here"
```

### 5️⃣ Run the Flutter app

```bash
cd frontend
flutter pub get
flutter run
```

---

## 🧑‍🎓 Usage Guide

1. Launch LeoFocus
2. Enter your session goal
3. Read Leonardo’s advice
4. Click **Start Session**
5. Work normally
6. Observe real-time feedback
7. Click **End Session**
8. Review your **Session Codex**

---

## 📂 Project Structure

```
leofocus/
├── frontend/
├── leonardo_backend/
│   └── trackers/
│       ├── trackers.py
│       ├── llm_client_2.py
│       └── local_summarizer.py
└── README.md
```

---

## ⚠️ Notes & Limitations

* Requires OS-level permissions for activity tracking
* Antivirus software may flag monitoring behavior (false positives)
* Browser detection relies on window titles
* Designed for **self-improvement**, not surveillance

---

## 🚀 Future Improvements

* Session history dashboard
* Charts & analytics
* Cloud sync
* Mobile companion app

---

## 🎓 Academic Context

Developed as part of coursework at **Politecnico di Milano** for the CSI course, combining:

* Human-Computer Interaction
* LLM reasoning
* Cross-platform systems
* Real-time data processing

---

## 👤 Authors

**Pau Fernández**  
MSc Student @ Politecnico di Milano  
Artificial Intelligence · Human–Computer Interaction · Systems

- 💼 LinkedIn: https://www.linkedin.com/in/pau-fern%C3%A1ndez-cester-9b7053252/  
- 🧑‍💻 GitHub: https://github.com/PauFdz

**Filippo Galletta**  
MSc Student @ EIT Digital Master School (POLIMI, KTH) 

- 💼 LinkedIn: [linkedin.com/in/filippo-galletta/](https://www.linkedin.com/in/filippo-galletta/)
- 🧑‍💻 GitHub: [github.com/filippogalletta](https://github.com/filippogalletta)

**David Ravelli**  
Data Science @ EIT Digital Master School (POLIMI, AALTO) 

- 💼 LinkedIn: https://www.linkedin.com/in/david-ravelli-2900a6252/ 
- 🧑‍💻 GitHub: https://github.com/dvd32

---

> *“Details make perfection, and perfection is not a detail.”*
> — Leonardo da Vinci
