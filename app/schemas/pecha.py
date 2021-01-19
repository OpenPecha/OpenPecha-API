from typing import List, Optional

from pydantic import BaseModel


# Shared properties
class PageBase(BaseModel):
    id: str
    page_no: int
    content: str
    link: Optional[str] = None


class Page(PageBase):
    name: str
    notes_page_id: Optional[str]


class NotesPage(PageBase):
    pass


class Text(BaseModel):
    id: str
    pages: List[Page]
    notes: Optional[List[NotesPage]]


class PedurmaPreviewPage(BaseModel):
    content: str


class PedurmaNoteEdit(BaseModel):
    image_link: str
    image_no: int
    page_no: int
    ref_start_page_no: str
    ref_end_page_no: str
    vol: int