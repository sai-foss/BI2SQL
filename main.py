from dotenv import load_dotenv
import os
import sys
import getpass

from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# Gemini uses GOOGLE_API_KEY (or GEMINI_API_KEY fallback). If not found, prompt.
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google AI API key: ")

llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview")

from pathlib import Path
import re

from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase


def check_csv_and_db_requirements():
    """
    Validate that either CSV folder exists or DuckDB file exists.
    Returns True only if CSV folder exists AND DuckDB file does NOT exist (proceed with population).
    Returns False if DuckDB file already exists (skip population) or only CSV exists but DB exists.
    Raises FileNotFoundError if neither exists.

    CSV exists + DB doesn't exist → builds database from CSVs
    CSV exists + DB exists → skips rebuild (reuses existing DB)
    CSV doesn't exist + DB exists → skips build, uses existing DB
    Neither exists → error with guidance
    """
    csv_dir = Path("./csv")
    db_file = Path("rag.duckdb")

    csv_exists = csv_dir.exists() and csv_dir.is_dir()
    db_exists = db_file.exists() and db_file.is_file()

    if not csv_exists and not db_exists:
        raise FileNotFoundError(
            "CSV folder './csv' not found and no existing 'rag.duckdb' database. "
            "Please add CSV files to ./csv directory."
        )

    # Only populate if CSV exists AND DB doesn't exist yet
    return csv_exists and not db_exists


# Check requirements and proceed only if validation passes
should_populate_db = check_csv_and_db_requirements()

engine = create_engine("duckdb:///rag.duckdb")


# Only populate database if CSV folder exists AND database doesn't exist yet
if should_populate_db:
    ###########################################################
    #### CSV FOLDER EXISTS & DB DOESN'T - BUILDING DATABASE ##########
    ###########################################################
    csv_dir = Path("./csv")
    csv_files = sorted(csv_dir.glob("*.csv"))

    def to_table_name(filename: str) -> str:
        """
        Convert a filename to a safe DuckDB table name.
        - strips extension
        - lowercases
        - replaces non [a-z0-9_] with _
        - prefixes with 't_' if it starts with a digit
        """
        stem = Path(filename).stem.lower()
        stem = re.sub(r"[^a-z0-9_]+", "_", stem).strip("_")
        if not stem:
            stem = "t"
        if stem[0].isdigit():
            stem = f"t_{stem}"
        return stem

    with engine.begin() as conn:
        for csv_path in csv_files:
            table_name = to_table_name(csv_path.name)

            # deterministic reruns during dev
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {table_name} AS
                    SELECT * FROM read_csv_auto('{csv_path.as_posix()}')
                """
                )
            )
            print(f"Loaded {csv_path.name} -> {table_name}")
else:
    print("Database already exists or CSV folder missing. Skipping database build.")

# Refresh LangChain wrapper after tables exist
db = SQLDatabase(engine)

print(f"Dialect:{db.dialect}")
# we checking if the langchain framework recognizes the database dialect

print(f"available tables{db.get_usable_table_names()}")

from langchain_community.agent_toolkits import SQLDatabaseToolkit


toolkit = SQLDatabaseToolkit(db=db, llm=llm)

tools = toolkit.get_tools()

for tool in tools:
    print(f"{tool.name}: {tool.description}\n")


from langchain.agents import create_agent

system_prompt = """
You are an agent designed to interact with a SQL database. Given an input question, create a syntactically correct {dialect} query to run. Then return the query to the user.
Unless the user specifies the number of examples they wish to return always default to {top_k} results.
""".format(
    dialect=db.dialect,
    top_k=5,
)

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
)