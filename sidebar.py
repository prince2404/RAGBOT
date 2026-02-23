import streamlit as st
from api_utils import upload_document, list_documents, delete_document

def display_sidebar():
    # Model selection - Using OpenRouter free models
    model_options = [
        "arcee-ai/trinity-large-preview:free",
        "deepseek/deepseek-chat:free",
        "google/gemma-2-9b-it:free",
        "mistralai/mistral-7b-instruct:free"
    ]
    st.sidebar.selectbox("Select Model", options=model_options, key="model")

    if "model" not in st.session_state:
        st.session_state.model = "arcee-ai/trinity-large-preview:free"

    # Document upload
    # sidebar.py
    uploaded_files = st.sidebar.file_uploader("Choose files", type=["pdf", "docx", "html", "csv", "txt"], accept_multiple_files=True)

    if uploaded_files and st.sidebar.button("Upload"): # Now handles a list of files
     with st.spinner("Uploading..."):
        for uploaded_file in uploaded_files: # loop through files
            upload_response = upload_document(uploaded_file) # existing logic, called for each file
            if upload_response: # add error handling to check if file was uploaded 
                 st.sidebar.success(f"File {uploaded_file.name} uploaded successfully with ID {upload_response.get('file_id', 'Unknown ID')}.")
            else:
                st.sidebar.error(f"Failed to upload file {uploaded_file.name}.")
        st.session_state.documents = list_documents()


    # List and delete documents
    st.sidebar.header("Uploaded Documents")
    if st.sidebar.button("Refresh Document List"):
        st.session_state.documents = list_documents()

    # Display document list and delete functionality
    if "documents" in st.session_state and st.session_state.documents:
        for doc in st.session_state.documents:
            file_size_kb = doc.get('file_size', 0) / 1024
            st.sidebar.text(f"{doc['filename']} (ID: {doc['id']}) size: {file_size_kb:.2f} KB, Type: {doc.get('content_type', 'N/A')}")

        selected_file_id = st.sidebar.selectbox("Select a document to delete", 
                                                options=[doc['id'] for doc in st.session_state.documents])
        if st.sidebar.button("Delete Selected Document"):
            delete_response = delete_document(selected_file_id)
            if delete_response:
                st.sidebar.success(f"Document deleted successfully.")
                st.session_state.documents = list_documents()
            else:
                st.sidebar.error("Failed to delete the document.")
