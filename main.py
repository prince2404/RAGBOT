from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic_models import QueryInput, QueryResponse, DocumentInfo, DeleteFileRequest
from langchain_utils import get_rag_chain
from db_utils import (
    insert_application_logs,
    get_chat_history,
    get_all_documents,
    insert_document_record,
    delete_document_record,
)
from chroma_utils import index_document_to_chroma, delete_doc_from_chroma
from google_sheets_utils import save_chat_to_sheets
import os
import uuid
import logging
import shutil

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = FastAPI()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat", response_model=QueryResponse)
def chat(query_input: QueryInput):
    try:
        session_id = query_input.session_id or str(uuid.uuid4())
        logging.info(
            f"Session ID: {session_id}, User Query: {query_input.question}, Model: {query_input.model}"
        )

        chat_history = get_chat_history(session_id)
        rag_chain = get_rag_chain(query_input.model)

        result = rag_chain.invoke(
            {
                "input": query_input.question,
                "chat_history": chat_history,
            }
        )
        answer = result["answer"] if isinstance(result, dict) else str(result)

        insert_application_logs(session_id, query_input.question, answer, query_input.model)

        # Optional: will fail safely if Google Sheets env vars are not configured
        save_chat_to_sheets(question=query_input.question, answer=answer)

        logging.info(f"Session ID: {session_id}, AI Response: {answer}")
        return QueryResponse(answer=answer, session_id=session_id, model=query_input.model)

    except Exception as e:
        logging.exception(f"/chat failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/upload-doc")
async def upload_and_index_document(files: list[UploadFile] = File(...)):
    results = []
    allowed_extensions = [".pdf", ".docx", ".html", ".csv", ".txt"]

    for file in files:
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            results.append(
                {
                    "filename": file.filename,
                    "error": f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
                }
            )
            continue

        temp_file_path = f"temp_{file.filename}"

        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_id = insert_document_record(
                file.filename, file.size, file.content_type, temp_file_path
            )

            if file_id is None:
                results.append(
                    {
                        "filename": file.filename,
                        "error": "Failed to insert file record into database.",
                    }
                )
                continue

            success = index_document_to_chroma(temp_file_path, file_id)
            if success:
                results.append(
                    {
                        "filename": file.filename,
                        "message": "File uploaded and indexed successfully.",
                        "file_id": file_id,
                    }
                )
            else:
                delete_document_record(file_id)
                results.append({"filename": file.filename, "error": "Failed to index file."})

        except Exception as e:
            logging.exception(f"/upload-doc failed for {file.filename}: {e}")
            results.append({"filename": file.filename, "error": str(e)})
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    return results


@app.get("/list-docs", response_model=list[DocumentInfo])
def list_documents():
    try:
        return get_all_documents()
    except Exception as e:
        logging.exception(f"/list-docs failed: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving document list")


@app.post("/delete-doc")
def delete_document(request: DeleteFileRequest):
    try:
        chroma_delete_success = delete_doc_from_chroma(request.file_id)
        if not chroma_delete_success:
            return {"error": f"Failed to delete document with file_id {request.file_id} from Chroma."}

        db_delete_success = delete_document_record(request.file_id)
        if not db_delete_success:
            return {
                "error": f"Deleted from Chroma but failed to delete document with file_id {request.file_id} from DB."
            }

        return {"message": f"Successfully deleted document with file_id {request.file_id}."}

    except Exception as e:
        logging.exception(f"/delete-doc failed for {request.file_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting document")
