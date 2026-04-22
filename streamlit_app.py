import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
import os

# Set up environment variables for API key if not already present.
# In a production Streamlit app, consider using Streamlit's secrets management (`st.secrets`).
# If GOOGLE_API_KEY is not set before running the Streamlit app, `main.py` might
# try to use `getpass.getpass()`, which is not suitable for Streamlit's web environment.
# Ensure your GOOGLE_API_KEY is set in your environment variables or in a .env file
# accessible to the Streamlit process.

# Import the initialized agent from main.py
# This will execute the main.py script once upon import, setting up the database and agent.
try:
    from main import agent, llm
except ImportError as e:
    st.error(f"Failed to import agent from main.py. Make sure main.py is correctly set up and no interactive prompts (like getpass) are preventing import. Error: {e}")
    st.stop()

st.set_page_config(page_title="SQL Agent Chat", page_icon="💬")
st.title("SQL Agent Chat")

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
            st.markdown(message.content)

# Accept user input
# Example question: Tell me 10 most expensive procedures between 2013 and 2018 for people with normal pregnancy
if prompt := st.chat_input("What is your question?"):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        try:
            with st.spinner("Thinking..."):
                for chunk in agent.stream({"messages": st.session_state.messages}, stream_mode="values"):
                    msg = chunk["messages"][-1]
                    
                    # Print the agent's full thought process/actions to the terminal
                    msg.pretty_print()

                    # Only update the Streamlit UI with the AI's actual text content
                    if isinstance(msg, AIMessage) and msg.content:
                        if isinstance(msg.content, list):
                            full_response = "".join(
                                block.get("text", "") if isinstance(block, dict) else str(block)
                                for block in msg.content
                            )
                        else:
                            full_response = str(msg.content)
                        
                        # Add markdown backticks around SQL if the model forgot them
                        if "```" not in full_response:
                            if "\nsql\n" in full_response:
                                full_response = full_response.replace("\nsql\n", "\n```sql\n")
                            elif full_response.startswith("sql\n"):
                                full_response = full_response.replace("sql\n", "```sql\n", 1)
                                
                            if "```sql\n" in full_response and not full_response.strip().endswith("```"):
                                full_response += "\n```"

                        response_placeholder.markdown(full_response)
        except Exception as e:
            # Print only up to the error message (omitting the full traceback)
            print(f"Error encountered: {e}")
            st.error("An error occurred while processing your request. Please check the terminal for details.")
            
        if full_response:
            st.session_state.messages.append(AIMessage(content=full_response))
