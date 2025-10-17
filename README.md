# Career Copilot

Career Copilot is an agentic job-search assistant that analyzes your résumé, finds matching jobs, drafts outreach messages, and suggests résumé improvements.

## Features
- Analyze and parse résumés
- Search for jobs using Indeed or Google Jobs API
- Draft personalized outreach messages
- Suggest résumé improvements
- Enrich job and company data (Proxycurl, Phase 2)
- Local data storage with SQLite
- Streamlit UI for rapid prototyping

## Tech Stack
- Python 3.10+
- [Semantic Kernel](https://github.com/microsoft/semantic-kernel)
- OpenAI GPT-4-Turbo, text-embedding-3-small
- Indeed or Google Jobs API
- Proxycurl API (Phase 2)
- SQLite
- Streamlit
- requests, python-dotenv, pandas, numpy (optional FAISS later)

## Setup
1. Clone the repo and navigate to the folder.
2. Copy `sample.env` to `.env` and fill in your API keys.
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Run the Streamlit app:
   ```sh
   streamlit run ui/streamlit_app.py
   ```

## Folder Structure
```
career_copilot/
├── main.py
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
├── .env
├── sample.env
├── data/
│   └── career_copilot.db
├── services/
│   ├── job_api.py
│   ├── resume_parser.py
│   └── outreach_generator.py
├── agents/
│   ├── semantic_kernel_setup.py
│   └── skills/
├── ui/
│   └── streamlit_app.py
├── notebooks/
└── tests/
```

## License
MIT
