# 📄 AI Resume Analyzer

<p align="center">

An AI-powered resume analysis tool built with Python, Streamlit, and Google Gemini.

</p>

<p align="center">

<a href="https://airesumeanalyzer-axkhrauublkfzwoudgw8qt.streamlit.app/">
  🚀 <b>Try the Live Application</b>
</a>

</p>

---

## 📌 About the Project

**AI Resume Analyzer** is a Generative AI-powered application that analyzes resumes and provides structured, actionable feedback.

Users can upload a PDF resume and receive insights into their:

- ATS score
- Professional profile
- Key skills
- Work experience
- Strengths
- Areas for improvement
- Recommended job roles
- Resume improvement tips

The goal is to help candidates understand how their resume may be interpreted during the hiring process and identify areas that can be improved.

---

## 🚀 Live Demo

👉 **[Try AI Resume Analyzer](https://airesumeanalyzer-axkhrauublkfzwoudgw8qt.streamlit.app/)**

Upload a PDF resume and explore the analysis through the interactive dashboard.

---

## ✨ Key Features

### 📊 ATS Score

Provides an overall score from **0–100** based on the AI's analysis of the resume.

### 👤 Profile Summary

Generates a concise professional summary based on the candidate's resume content.

### 🛠️ Skill Detection

Identifies important technical and professional skills present in the resume.

### 💼 Experience Analysis

Summarizes the candidate's professional experience and background.

### 💪 Strengths

Highlights strong aspects of the resume.

### 🔍 Areas of Improvement

Identifies specific areas where the resume could be improved.

### 🎯 Recommended Roles

Suggests job roles that are relevant to the candidate's experience and skills.

### 💡 Improvement Tips

Provides actionable suggestions for improving the resume.

### 📑 PDF Report

Allows users to download the analysis as a PDF report.

---

## 🧠 How It Works

```text
             Resume PDF
                 │
                 ▼
        ┌─────────────────┐
        │  PDF Extraction │
        └────────┬────────┘
                 │
                 ▼
          Resume Text
                 │
                 ▼
        ┌─────────────────┐
        │  Google Gemini  │
        │   AI Analysis   │
        └────────┬────────┘
                 │
                 ▼
        Structured JSON
                 │
                 ▼
        ┌─────────────────┐
        │ Streamlit       │
        │ Dashboard       │
        └────────┬────────┘
                 │
                 ▼
      Resume Insights & Report
```
---

## 📊 Analysis Output

| Feature                  | Description                                    |
| ------------------------ | ---------------------------------------------- |
| **ATS Score**            | Overall resume score from 0–100                |
| **Profile Summary**      | Professional summary generated from the resume |
| **Key Skills**           | Skills detected from the resume                |
| **Experience Summary**   | Summary of professional experience             |
| **Strengths**            | Strong aspects identified in the resume        |
| **Areas of Improvement** | Specific areas that can be improved            |
| **Recommended Roles**    | Roles relevant to the candidate's profile      |
| **Tips to Improve**      | Actionable resume improvement suggestions      |

---

## 🛠️ Tech Stack

### Programming
- Python

### Generative AI
- Google Gemini
- Generative AI
- Prompt Engineering

### Web Application
- Streamlit

### PDF Processing
- pypdf
- PyPDF2

### Report Generation
- ReportLab

### Development Tools
- Git
- GitHub
- Python Virtual Environment

---

## 📁 Project Structure
AI_Resume_Analyzer/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
└── venv/

The venv/ directory is used only for local development and should not be uploaded to GitHub.

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Apeetha-Srinivasan/AI_Resume_Analyzer.git

2. Navigate to the Project
```bash
cd AI_Resume_Analyzer

3. Create a Virtual Environment
```bash
python -m venv venv

4. Activate the Environment
For Windows:
```bash
venv\Scripts\activate

5. Install Dependencies
```bash
pip install -r requirements.txt

```

## 🔑 API Key Configuration

This application uses the Google Gemini API for resume analysis.

The API key should never be hard-coded or committed to GitHub.

For the deployed Streamlit application, the API key is configured securely using Streamlit Secrets.

For local development, configure your Gemini API key using a secure environment variable or local secrets configuration.

## ▶️ Run Locally

After installing the dependencies, run:

streamlit run app.py

The application will open in your browser.

## 🌐 Deployment

The application is deployed using Streamlit Community Cloud.

The deployment is connected to the GitHub repository:

Apeetha-Srinivasan/AI_Resume_Analyzer

Changes pushed to the main branch can trigger an automatic redeployment of the application.

---

## 🎯 Project Objective

The objective of this project is to build a practical Generative AI application that helps job seekers understand their resumes and identify opportunities for improvement.

The project combines:

- 📄 PDF text extraction
- 🤖 Generative AI
- ✍️ Structured prompting
- 📋 JSON-based AI responses
- 🖥️ Streamlit
- 📑 PDF report generation

to create an end-to-end resume analysis application.

---

## 🔮 Future Improvements

Potential future enhancements include:

- 🔎 Job Description vs Resume matching
- 📊 Keyword analysis
- 🎯 Job-specific ATS analysis
- 🧠 More advanced skill extraction
- 📈 Resume analytics and visualizations
- 📄 Support for additional document formats
- 🔐 Improved privacy and data handling
- 🎯 More detailed role recommendations
  
## 👩‍💻 Author

**Apeetha Srinivasan**

- Data Science | Machine Learning | NLP | Generative AI
- Master of Computer Applications – Data Science
  
⭐ Feedback

If you find this project interesting, feel free to explore the repository and try the live application.

⭐ Star the repository if you find it useful!
