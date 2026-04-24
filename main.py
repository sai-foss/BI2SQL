from dotenv import load_dotenv
import os
import sys
import getpass

from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# Gemini uses GOOGLE_API_KEY (or GEMINI_API_KEY fallback). If not found, prompt for api key (in the terminal)
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google AI API key: ")



## was recommended a temperature of 0.0 for SQL agent tasks (by ChatGPT)
llm = ChatGoogleGenerativeAI(model="gemma-4-31b-it")

from pathlib import Path
import re

from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase


def check_csv_and_db_requirements():  # true -> build db. False -> skip db. no csv dir = raise exception
    """
    check if CSV folder exists and contains CSV files, and if the DuckDB database file already exists.
    """
    csv_dir = Path("./csv")
    db_file = Path("rag.duckdb")

    if not csv_dir.exists() and not db_file.exists():
        raise FileNotFoundError(
            "CSV folder './csv' not found and no existing 'rag.duckdb' database. "
            "Please add CSV files to ./csv directory."
        )

    elif not csv_dir.exists() and db_file.exists():
        return False  # you have the DB so skip DB build step

    elif csv_dir.exists() and not db_file.exists():
        return True  # no db but we have the csv so build the DB

    elif csv_dir.exists() and db_file.exists():
        return False  # this is the instance when both exist no need to build DB


# Check requirements and proceed only if validation passes
should_populate_db = check_csv_and_db_requirements()


# creating an instance of duckdb connection from the duckdb file
engine = create_engine("duckdb:///rag.duckdb")


# Only populate database if CSV folder exists AND database doesn't exist yet
if should_populate_db == True:
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
    print("Database already exists. Skipping database build.")

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
You are an agent designed to interact with a SQL database containing medical data.
Your primary function is strictly to answer questions related to healthcare, medical procedures, patients, and associated costs.

If the user asks a question that is completely unrelated to the medical domain or the provided dataset, do NOT attempt to query the database or answer the question. Instead, politely reply: "I am specifically designed to answer questions related to the synthetic medical dataset. I cannot answer unrelated queries."

Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

Queries might need to utilize DISTINCT keyword. If your query returns many of the same names you might have to use DISTINCT on the right column. Make sure to use Median for costs for prompts that ask for costs. Certain columns might have rows that have mismatches in case so normalize the cases in those cases. 

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

Here is the schema of the database you can query:
{schema}
""".format(
    dialect=db.dialect,
    top_k=5,
    schema=db.get_table_info()
)

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
)
