from pydantic import BaseModel, Field
from datetime import datetime
import typing

class QueryInput(BaseModel):
    question: str
    session_id: str = Field(default=None)
    model: str = Field(default="arcee-ai/trinity-large-preview:free")

class QueryResponse(BaseModel):
    answer: str
    session_id: str
    model: str

class DocumentInfo(BaseModel):
    id: int
    filename: str
    upload_timestamp: datetime
    file_size: typing.Optional[int] = None # New field
    content_type: typing.Optional[str] = None # New field

class DeleteFileRequest(BaseModel):
    file_id: int

class DeleteFileResponse(BaseModel):
    message: str
