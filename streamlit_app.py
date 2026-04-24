import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.callbacks import BaseCallbackHandler
import os
import pandas as pd
import re
import streamlit.components.v1 as components

# Set up environment variables for API key if not already present.
# In a production Streamlit app, consider using Streamlit's secrets management (`st.secrets`).
# If GOOGLE_API_KEY is not set before running the Streamlit app, `main.py` might
# try to use `getpass.getpass()`, which is not suitable for Streamlit's web environment.
# Ensure your GOOGLE_API_KEY is set in your environment variables or in a .env file
# accessible to the Streamlit process.

# Import the initialized agent from main.py
# This will execute the main.py script once upon import, setting up the database and agent.
try:
    from main import agent, llm, engine, db
except ImportError as e:
    st.error(f"Failed to import agent from main.py. Make sure main.py is correctly set up and no interactive prompts (like getpass) are preventing import. Error: {e}")
    st.stop()

# Callback handler to count API calls to the LLM
class APICallCounter(BaseCallbackHandler):
    def __init__(self):
        self.call_count = 0
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        
    def on_chat_model_start(self, *args, **kwargs):
        self.call_count += 1
        
    def on_llm_end(self, response, **kwargs):
        # Extract token usage from standard llm_output or message usage_metadata
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            self.total_tokens += usage.get("total_tokens", 0)
            self.prompt_tokens += usage.get("prompt_tokens", 0)
            self.completion_tokens += usage.get("completion_tokens", 0)
        elif response.generations:
            for generations in response.generations:
                for generation in generations:
                    if hasattr(generation, "message") and hasattr(generation.message, "usage_metadata") and generation.message.usage_metadata:
                        usage = generation.message.usage_metadata
                        self.total_tokens += usage.get("total_tokens", 0)
                        self.prompt_tokens += usage.get("input_tokens", 0)
                        self.completion_tokens += usage.get("output_tokens", 0)

st.set_page_config(page_title="BI 2 SQL", page_icon="📊")
st.title("BI 2 SQL Chat")

# Inject custom CSS to make the sidebar expand (>>) icon more prominent
st.markdown("""
    <style>
        /* Target the collapsed sidebar > icon */
        [data-testid="collapsedControl"] svg {
            width: 40px !important;
            height: 40px !important;
            color: #ff4b4b !important; /* Prominent primary color */
        }
        [data-testid="collapsedControl"]:hover svg {
            transform: scale(1.1);
            transition: transform 0.2s ease-in-out;
        }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.subheader("Database Info")
    if st.button("Show Database Schema", width='stretch'):
        with st.spinner("Generating schema..."):
            try:
                from eralchemy import render_er
                render_er("duckdb:///rag.duckdb", "schema.png")
                if "messages" not in st.session_state:
                    st.session_state["messages"] = [AIMessage(content="Hello! How can I help you with your database today?")]
                st.session_state.messages.append(AIMessage(content="Here is the current database schema:\n\n[SCHEMA_IMAGE]"))
                st.session_state["collapse_sidebar"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Failed to generate schema: {e}")
                
    st.divider()
    st.subheader("Available Tables")
    for table_name in db.get_usable_table_names():
        if st.button(f"🗂️ {table_name}", width='stretch', key=f"preview_{table_name}"):
            if "messages" not in st.session_state:
                st.session_state["messages"] = [AIMessage(content="Hello! How can I help you with your database today?")]
            st.session_state.messages.append(HumanMessage(content=f"Show me a preview of the {table_name} table."))
            st.session_state.messages.append(AIMessage(content=f"Here is a preview of the `{table_name}` table:\n\n[TABLE_PREVIEW:{table_name}]"))
            st.session_state["collapse_sidebar"] = True
            st.rerun()

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        AIMessage(content="Hello! How can I help you with your database today?"),
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            if "[SCHEMA_IMAGE]" in str(message.content):
                st.markdown(str(message.content).replace("[SCHEMA_IMAGE]", ""))
                if os.path.exists("schema.png"):
                    # width='stretch' ensures the image is scaled to the chat bubble width
                    st.image("schema.png")
            elif "[TABLE_PREVIEW:" in str(message.content):
                match = re.search(r"\[TABLE_PREVIEW:(.*?)\]", str(message.content))
                if match:
                    t_name = match.group(1)
                    st.markdown(str(message.content).replace(match.group(0), ""))
                    try:
                        df_preview = pd.read_sql(f"SELECT * FROM {t_name} LIMIT 15", engine)
                        st.dataframe(df_preview, width='stretch')
                    except Exception as e:
                        st.error(f"Failed to load preview: {e}")
            else:
                st.markdown(message.content)

# JS injection to collapse the sidebar when requested
if st.session_state.get("collapse_sidebar"):
    components.html(
        """
        <script>
        const closeBtn = window.parent.document.querySelector('[data-testid="stSidebarCollapseButton"] button');
        if (closeBtn) { closeBtn.click(); }
        </script>
        """,
        height=0,
    )
    st.session_state["collapse_sidebar"] = False

# Accept user input
# Example question: Tell me 10 most expensive procedures between 2013 and 2018 for people with normal pregnancy
if prompt := st.chat_input("Tell me 10 most expensive procedures (Distinct) between 2013 and 2018 ?"):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Intercept specific schema-related requests to skip the LLM and render the diagram
        if prompt.strip().lower() in ["schema", "show schema", "show database schema", "draw schema"]:
            with st.spinner("Generating schema..."):
                try:
                    from eralchemy import render_er
                    render_er("duckdb:///rag.duckdb", "schema.png")
                    response = "Here is the current database schema:"
                    st.markdown(response)
                    st.image("schema.png")
                    st.session_state.messages.append(AIMessage(content=f"{response}\n\n[SCHEMA_IMAGE]"))
                except Exception as e:
                    st.error(f"Failed to generate schema: {e}")
            
            # Halt execution so the agent doesn't also try to formulate a SQL query
            st.stop()

        response_placeholder = st.empty()
        full_response = ""
        api_call_counter = APICallCounter()
        
        try:
            with st.spinner("Thinking..."):
                for chunk in agent.stream({"messages": st.session_state.messages}, stream_mode="values", config={"callbacks": [api_call_counter]}):
                    msg = chunk["messages"][-1]
                    
                    # Print the agent's full thought process/actions to the terminal
                    msg.pretty_print()

                    # Reconstruct the full response from all new messages
                    new_messages = chunk["messages"][len(st.session_state.messages):]
                    
                    full_response = ""
                    for m in new_messages:
                        if isinstance(m, AIMessage):
                            # Extract SQL query from tool calls
                            if hasattr(m, "tool_calls") and m.tool_calls:
                                for tool_call in m.tool_calls:
                                    if tool_call["name"] == "sql_db_query":
                                        query = tool_call["args"].get("query")
                                        if query:
                                            full_response += f"```sql\n{query}\n```\n\n"
                            
                            # Extract text content
                            if m.content:
                                if isinstance(m.content, list):
                                    full_response += "".join(
                                        block.get("text", "") if isinstance(block, dict) else str(block)
                                        for block in m.content
                                    ) + "\n\n"
                                else:
                                    full_response += str(m.content) + "\n\n"
                    
                    full_response = full_response.strip()
                    if full_response:
                        response_placeholder.markdown(full_response)
                
                # Print the final count to the terminal after the stream is finished
                print(f"\n--- Total LLM API calls made in this request: {api_call_counter.call_count} ---")
                print(f"--- Total Tokens: {api_call_counter.total_tokens} (Prompt: {api_call_counter.prompt_tokens}, Completion: {api_call_counter.completion_tokens}) ---\n")
        except Exception as e:
            # Print only up to the error message (omitting the full traceback)
            print(f"Error encountered: {e}")
            st.error("An error occurred while processing your request. Please check the terminal for details.")
            
        if full_response:
            st.session_state.messages.append(AIMessage(content=full_response))
