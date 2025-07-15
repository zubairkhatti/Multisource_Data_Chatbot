import os
import shutil

# from langchain.chat_models import AzureChatOpenAI
import chromadb
import spacy
import yaml
from dotenv import load_dotenv
# from openai import AzureOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from pyprojroot import here

print("Environment variables are loaded:", load_dotenv())


class LoadConfig:
    def __init__(self) -> None:
        with open(here("configs/app_config.yml")) as cfg:
            app_config = yaml.safe_load(cfg)

        self.load_directories(app_config=app_config)
        self.load_llm_configs(app_config=app_config)
        self.load_openai_models()
        self.load_chroma_client()
        self.load_embedding_model()
        self.load_rag_config(app_config=app_config)

        # Un comment the code below if you want to clean up the upload csv SQL DB on every fresh run of the chatbot. (if it exists)
        # self.remove_directory(self.uploaded_files_sqldb_directory)

    def load_directories(self, app_config):
        self.stored_csv_xlsx_directory = here(
            app_config["directories"]["stored_csv_xlsx_directory"]
        )
        self.sqldb_directory = str(here(app_config["directories"]["sqldb_directory"]))
        self.uploaded_files_sqldb_directory = str(
            here(app_config["directories"]["uploaded_files_sqldb_directory"])
        )
        self.stored_csv_xlsx_sqldb_directory = str(
            here(app_config["directories"]["stored_csv_xlsx_sqldb_directory"])
        )
        self.persist_directory = app_config["directories"]["persist_directory"]

    def load_llm_configs(self, app_config):
        self.model_name = os.getenv("gpt_deployment_name")
        self.agent_llm_system_role = app_config["llm_config"]["agent_llm_system_role"]
        self.rag_llm_system_role = app_config["llm_config"]["rag_llm_system_role"]
        self.temperature = app_config["llm_config"]["temperature"]
        self.embedding_model_name = os.getenv("embed_deployment_name")

    def load_openai_models(self):
        google_generative_api_key = os.getenv("GOOGLE_API_KEY")

        self.google_generative_client = ChatGoogleGenerativeAI(
            model=os.getenv("gpt_deployment_name"),
            temperature=0.7,
            google_api_key=google_generative_api_key,
        )

    def load_embedding_model(self):
        self.nlp = spacy.load("en_core_web_md")  # 300-dimensional embeddings

    def load_chroma_client(self):
        self.chroma_client = chromadb.PersistentClient(
            path=str(here(self.persist_directory))
        )

    def load_rag_config(self, app_config):
        self.collection_name = app_config["rag_config"]["collection_name"]
        self.top_k = app_config["rag_config"]["top_k"]

    def remove_directory(self, directory_path: str):
        """
        Removes the specified directory.

        Parameters:
            directory_path (str): The path of the directory to be removed.

        Raises:
            OSError: If an error occurs during the directory removal process.

        Returns:
            None
        """
        if os.path.exists(directory_path):
            try:
                shutil.rmtree(directory_path)
                print(
                    f"The directory '{directory_path}' has been successfully removed."
                )
            except OSError as e:
                print(f"Error: {e}")
        else:
            print(f"The directory '{directory_path}' does not exist.")
