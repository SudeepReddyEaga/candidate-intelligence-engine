# Candidate Intelligence Engine

Welcome to the **Candidate Intelligence Engine**! This is a state-of-the-art data pipeline designed to ingest candidate profiles from diverse sources (PDFs, CSVs, JSON), validate and merge them natively, and project them into a highly reliable canonical JSON schema.

## 🚀 Quick Start

This project is built purely in Python and runs locally without the need for complex DevOps setups (like Docker). 

To run the unified backend API and frontend dashboard:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the application
python -m uvicorn candidate_transformer.api.app:create_app --factory
```
Then, open your web browser and navigate to `http://127.0.0.1:8000` to access the interactive Candidate Dashboard!

## 📄 Documentation

For detailed technical architecture and step-by-step evaluation workflows, please refer to the beautiful PDF documentation included in this repository:

* **[README.pdf](./README.pdf)** - Full project overview, architectural flow, and feature list.
* **[instructions.pdf](./instructions.pdf)** - Step-by-step setup and dashboard evaluation instructions.
