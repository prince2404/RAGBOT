from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from pydantic_models import QueryInput, QueryResponse, DocumentInfo, DeleteFileRequest
from langchain_utils import get_rag_chain
from db_utils import insert_application_logs, get_chat_history, get_all_documents, insert_document_record, delete_document_record
from chroma_utils import index_document_to_chroma, delete_doc_from_chroma
import os
import uuid
import logging
import shutil
from google_sheets_utils import save_chat_to_sheets
# import test  # Commented out to avoid ollama import error on deployment

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def index_documents_on_startup():
    try:
        documents = get_all_documents()
        for doc in documents:
            if 'filepath' in doc and os.path.exists(doc['filepath']):  # Check if filepath exists and is valid
                index_document_to_chroma(doc['filepath'], doc['id'])
            elif 'content' in doc:  # Fallback to 'content' if filepath is missing or invalid
                index_document_to_chroma(doc['content'], doc['id'])
            else:
                logging.error(f"Neither 'filepath' nor 'content' found for document ID: {doc['id']}. Skipping this document.")

    except Exception as e:
        logging.error(f"Error indexing documents on startup: {e}")    
#         index_document_to_chroma(doc['content'], doc['id'])  # Index directly using the content from the DB

# index_documents_on_startup()  # Call the function on app startup

# Initialize FastAPI app
app = FastAPI()

@app.post("/chat", response_model=QueryResponse)
def chat(query_input: QueryInput):
    session_id = query_input.session_id or str(uuid.uuid4())
    logging.info(f"Session ID: {session_id}, User Query: {query_input.question}, Model: {query_input.model}")

    chat_history = get_chat_history(session_id)
    rag_chain = get_rag_chain(query_input.model)
    result = rag_chain.invoke({
        "input": query_input.question,
        "chat_history": chat_history
    })
    answer = result["answer"] if isinstance(result, dict) else str(result)

    # Save to database
    insert_application_logs(session_id, query_input.question, answer, query_input.model)
    
    # Save to Google Sheets
    save_chat_to_sheets(
        # session_id=session_id,
        question=query_input.question,
        answer=answer,
        # model=query_input.model
    )

    logging.info(f"Session ID: {session_id}, AI Response: {answer}")
    return QueryResponse(answer=answer, session_id=session_id, model=query_input.model)


@app.post("/upload-doc")
async def upload_and_index_document(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        allowed_extensions = ['.pdf', '.docx', '.html', '.csv', '.txt']
        file_extension = os.path.splitext(file.filename)[1].lower()

        if file_extension not in allowed_extensions:
            results.append({"filename": file.filename, "error": f"Unsupported file type. Allowed types are: {', '.join(allowed_extensions)}"})
            continue  # Skip to the next file

        temp_file_path = f"temp_{file.filename}"  # Use unique temp file names

        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_id = insert_document_record(file.filename, file.size, file.content_type, temp_file_path)  # Pass filepath

            if file_id is not None:  # Check for successful database insertion
                success = index_document_to_chroma(temp_file_path, file_id)

                if success:
                    results.append({"filename": file.filename, "message": "File uploaded and indexed successfully.", "file_id": file_id})
                else:
                    delete_document_record(file_id)  # Clean up DB if indexing fails
                    results.append({"filename": file.filename, "error": "Failed to index file."})
            else:
                results.append({"filename": file.filename, "error": "Failed to insert file record into database."})

        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})  # Catch and report specific errors
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    return results  # Return all results
       

@app.get("/list-docs", response_model=list[DocumentInfo])
def list_documents():
    try:
        documents = get_all_documents()
        return documents
    except Exception as e:
        logging.error(f"Error retrieving document list: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving document list: {e}")  # More helpful error


@app.post("/delete-doc")
def delete_document(request: DeleteFileRequest):
    chroma_delete_success = delete_doc_from_chroma(request.file_id)

    if chroma_delete_success:
        db_delete_success = delete_document_record(request.file_id)
        if db_delete_success:
            return {"message": f"Successfully deleted document with file_id {request.file_id} from the system."}
        else:
            return {"error": f"Deleted from Chroma but failed to delete document with file_id {request.file_id} from the database."}
    else:
        return {"error": f"Failed to delete document with file_id {request.file_id} from Chroma."}


