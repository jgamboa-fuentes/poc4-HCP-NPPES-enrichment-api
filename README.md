# poc4-HCP-NPPES-enrichment-api
This project is a Python-based Flask API that automates the enrichment of Healthcare Provider (HCP) data. It serves as a scalable, web-based replacement for the original Excel VBA macro process. The API fetches real-time provider information from the official NPPES registry and uses OpenAI's GPT for intelligent data mapping and standardization.


- python3 -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
- flask run