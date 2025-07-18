import os
from operator import itemgetter
from typing import List, Tuple

import langchain
from langchain.chains import create_sql_query_chain
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from sqlalchemy import create_engine

from utils.load_config import LoadConfig

from .extract_sql_query import extract_sql_query

langchain.debug = True

APPCFG = LoadConfig()


class ChatBot:
    """
    A ChatBot class capable of responding to messages using different modes of operation.
    It can interact with SQL databases, leverage language chain agents for Q&A,
    and use embeddings for Retrieval-Augmented Generation (RAG) with ChromaDB.
    """

    @staticmethod
    def respond(
        chatbot: List, message: str, chat_type: str, app_functionality: str
    ) -> Tuple:
        """
        Respond to a message based on the given chat and application functionality types.

        Args:
            chatbot (List): A list representing the chatbot's conversation history.
            message (str): The user's input message to the chatbot.
            chat_type (str): Describes the type of the chat (interaction with SQL DB or RAG).
            app_functionality (str): Identifies the functionality for which the chatbot is being used (e.g., 'Chat').

        Returns:
            Tuple[str, List, Optional[Any]]: A tuple containing an empty string, the updated chatbot conversation list,
                                             and an optional 'None' value. The empty string and 'None' are placeholder
                                             values to match the required return type and may be updated for further functionality.
                                             Currently, the function primarily updates the chatbot conversation list.
        """
        if app_functionality == "Chat":
            # If we want to use langchain agents for Q&A with our SQL DBs that was created from .sql files.
            if chat_type == "Q&A with stored SQL-DB":
                # directories
                if os.path.exists(APPCFG.sqldb_directory):
                    db = SQLDatabase.from_uri(f"sqlite:///{APPCFG.sqldb_directory}")
                    execute_query = QuerySQLDataBaseTool(db=db)
                    write_query = create_sql_query_chain(
                        APPCFG.google_generative_client, db
                    )
                    answer_prompt = PromptTemplate.from_template(
                        APPCFG.agent_llm_system_role
                    )
                    answer = (
                        answer_prompt
                        | APPCFG.google_generative_client
                        | StrOutputParser()
                    )
                    clean_query_output = RunnableLambda(extract_sql_query)
                    chain = (
                        RunnablePassthrough.assign(raw_query=write_query)
                        .assign(query=itemgetter("raw_query") | clean_query_output)
                        .assign(result=itemgetter("query") | execute_query)
                        | answer
                    )
                    response = chain.invoke({"question": message})

                else:
                    chatbot.append(
                        (
                            message,
                            "SQL DB does not exist. Please first create the 'sqldb.db'.",
                        )
                    )
                    return "", chatbot, None
            # If we want to use langchain agents for Q&A with our SQL DBs that were created from CSV/XLSX files.
            elif (
                chat_type == "Q&A with Uploaded CSV/XLSX SQL-DB"
                or chat_type == "Q&A with stored CSV/XLSX SQL-DB"
            ):
                if chat_type == "Q&A with Uploaded CSV/XLSX SQL-DB":
                    if os.path.exists(APPCFG.uploaded_files_sqldb_directory):
                        engine = create_engine(
                            f"sqlite:///{APPCFG.uploaded_files_sqldb_directory}"
                        )
                        db = SQLDatabase(engine=engine)
                        print(db.dialect)
                    else:
                        chatbot.append(
                            (
                                message,
                                "SQL DB from the uploaded csv/xlsx files does not exist. Please first upload the csv files from the chatbot.",
                            )
                        )
                        return "", chatbot, None
                elif chat_type == "Q&A with stored CSV/XLSX SQL-DB":
                    if os.path.exists(APPCFG.stored_csv_xlsx_sqldb_directory):
                        engine = create_engine(
                            f"sqlite:///{APPCFG.stored_csv_xlsx_sqldb_directory}"
                        )
                        db = SQLDatabase(engine=engine)
                    else:
                        chatbot.append(
                            (
                                message,
                                "SQL DB from the stored csv/xlsx files does not exist. Please first execute `src/prepare_csv_xlsx_sqlitedb.py` module.",
                            )
                        )
                        return "", chatbot, None
                print(db.dialect)
                print(db.get_usable_table_names())
                agent_executor = create_sql_agent(
                    APPCFG.google_generative_client,
                    db=db,
                    agent_type="openai-tools",
                    verbose=True,
                )
                response = agent_executor.invoke({"input": message})
                response = response["output"]

            elif chat_type == "RAG with stored CSV/XLSX ChromaDB":
                llm_response = APPCFG.nlp(message)
                query_embeddings = llm_response.vector  # 300-dim vector
                vectordb = APPCFG.chroma_client.get_collection(
                    name=APPCFG.collection_name
                )
                results = vectordb.query(
                    query_embeddings=query_embeddings, n_results=APPCFG.top_k
                )
                prompt = f"User's question: {message} \n\n Search results:\n {results}"

                system_role = SystemMessage(content=APPCFG.rag_llm_system_role)
                user_msg = HumanMessage(content=prompt)
                response = APPCFG.google_generative_client.invoke(
                    [system_role, user_msg]
                )
                response = response.content

            # Get the `response` variable from any of the selected scenarios and pass it to the user.
            chatbot.append((message, response))
            return "", chatbot
        else:
            pass
        return ((),)
