from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
try:
    from langchain.chains.history_aware_retriever import create_history_aware_retriever
    from langchain.chains.retrieval import create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
except ImportError:
    from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
    from langchain_classic.chains.retrieval import create_retrieval_chain
    from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from typing import List
from langchain_core.documents import Document
import os
from chroma_utils import get_vectorstore

output_parser = StrOutputParser()


contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question, "
    "just reformulate it if needed and otherwise return it as is."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages([
    ("system", contextualize_q_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant. Use the following context to answer the user's question. 
                Follow these specific instructions:

                1. *Disease Diagnosis:* If the user describes animal health problems, follow this format:
                    * Ask for a list of symptoms.
                    * Provide a possible disease list.
                    * Mention other potential symptoms.
                    * Outline treatment steps, including medications.
                    * List available medicines from the database (especially ID 19 for cow, bull, horse, dog).
                    * Suggest precautions.

                2.  * Animal Adoption: * If the user expresses interest in adopting an animal:
                    * Ask for preferences (location, age, type).
                    * Provide a list of matching animals from the database. 

                3. *Data Entry for Adoption: * If the user says they want to give an animal up for adoption:
                    * Collect the animal's name, type, gender, age and location.
                    * Confirm that you have received the information and will pass it on for processing.
                    * Tell the user that they will be contacted by the adoption agency.

                4. *General Queries: * For all other questions, use the provided context to give helpful answers in the user's language."""),  
    ("system", "Context: {context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])


def get_rag_chain(model="arcee-ai/trinity-large-preview:free"):
    llm = ChatOpenAI(
        model=model,
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1"
    )
    try:
        retriever = get_vectorstore().as_retriever(search_kwargs={"k": 15})
        history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        return rag_chain
    except Exception:
        fallback_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        return (fallback_prompt | llm | StrOutputParser() | RunnableLambda(lambda x: {"answer": x}))
