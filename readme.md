# BI 2 SQL Analytics App (Medical Data) 📊

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white)](https://langchain.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## Overview

**BI 2 SQL** is an intelligent Business Intelligence analytics application that bridges the gap between natural language questions and complex SQL database queries. Built with a robust architecture leveraging **Google Gemini (gemma-4-31b-it)** via **LangChain**, the app enables users to converse seamlessly with tabular medical data.

The application is fully dynamic: it automatically ingests local CSV files, builds a local **DuckDB** instance, extracts the database schema, and dynamically generates, validates, and executes syntactically correct SQL queries.

## Features

* **Natural Language to SQL**: Ask questions in plain English and let the LangChain agent construct and execute the proper DuckDB dialect SQL queries.
* **Automated Database Creation**: Drop your files in the `./csv` directory, and the app automatically provisions a `rag.duckdb` relational database on the fly.
* **Dynamic Schema Visualization**: Generates and displays an Entity-Relationship (ER) diagram of your database schema natively in the Streamlit chat using `eralchemy`.
* **Instant Table Previews**: Quickly peek at the top rows of available tables directly from the application sidebar.
* **Token & Cost Tracking**: Built-in API callback handler to meticulously track LLM token usage (Total, Prompt, and Completion tokens) for observability.
* **Secure & Sandboxed**: Uses a read-only SQL agent prompt guardrail preventing destructive DML operations (INSERT, UPDATE, DELETE, DROP) and is specifically scoped to answer medical domain questions.

## Architecture

1. **Backend (`main.py`)**: 
   * Validates the presence of the `./csv` folder and automatically transforms CSVs into safely named DuckDB tables.
   * Wraps the database with LangChain's `SQLDatabase` utility.
   * Instantiates a `ChatGoogleGenerativeAI` LLM (configured for accurate SQL generation) and connects it to the DB using `SQLDatabaseToolkit`.
   * Initializes a LangChain agent using a secure system prompt scoped to healthcare and medical procedures.
2. **Frontend (`streamlit_app.py`)**:
   * Provides a responsive, chat-based UI using Streamlit.
   * Handles special user commands (e.g., intercepting "show schema" to render visual diagrams).
   * Streams the agent's chain-of-thought reasoning and SQL output directly to the UI.

## Installation & Setup

### Prerequisites
* Python 3.9+
* A valid Google AI/Gemini API Key
* Graphviz (required on your system for `eralchemy` to generate schema images)

### Step-by-Step Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/sai-foss/BI2SQL
   cd BI2SQL
   ```

2. **Install Dependencies**
   ```bash
   pip install streamlit langchain langchain-google-genai langchain-community sqlalchemy duckdb-engine eralchemy pandas python-dotenv
   ```

3. **Add your Data**
   Create a `csv` folder in the project root and add your dataset files:
   ```bash
   mkdir csv
   # Copy your medical .csv files into the ./csv directory
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the root directory and add your Google API key:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   ```
   *(Alternatively, the terminal will prompt you to enter the key if it is not found).*

## Usage

Start the Streamlit application by running:

```bash
streamlit run streamlit_app.py
```

1. Open the provided Local URL (usually `http://localhost:8501`).
2. Wait for the initial database build if you are running it for the first time.
3. Use the **sidebar** to inspect the database schema or preview table data.
4. Use the **chat interface** to ask analytical questions (e.g., *"Tell me 10 most expensive unique procedures between 2013 and 2018"*).

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. See the LICENSE file for details.