from pathlib import Path
from typing import List, Optional

from antx.utils import BASE_DIR
from fastapi import APIRouter, HTTPException, status
from openpecha import config as openpecha_config
from pedurma import (
    PageNumMissing,
    get_pedurma_text_edit_notes,
    get_pedurma_text_obj,
    get_preview_page,
    save_pedurma_text,
    update_text_pagination,
)
from pedurma.pecha import PedurmaText, ProofreadNotePage
from pedurma.proofreading import get_note_pages, update_note_page

from app import schemas
from app.schemas.pecha import PedurmaPreviewPage
from app.services.pedurma import create_text_release

router = APIRouter()


@router.get("/texts/{text_id}", response_model=PedurmaText)
def read_text(text_id: str, page_no: Optional[int] = None):
    """
    Retrieve text from pecha
    """
    text = get_pedurma_text_obj(text_id)
    return text


@router.put("/texts/{text_id}")
def update_text(text_id: str, text: PedurmaText):
    save_pedurma_text(text)
    return {"message": f"{text_id} saved successfully"}


@router.post("/preview", response_model=schemas.PedurmaPreviewPage)
def pedurma_page_preview(
    google_page: schemas.Page,
    google_page_notes: List[schemas.NotesPage],
    namsel_page: schemas.Page,
    namsel_page_notes: List[schemas.NotesPage],
):
    try:
        preview_page = get_preview_page(
            google_page, namsel_page, google_page_notes, namsel_page_notes
        )
    except PageNumMissing:
        raise HTTPException(status_code=422, detail="page number is missing in notes")
    return PedurmaPreviewPage(content=preview_page)


@router.get("/{text_id}/preview")
def pedurma_text_preview(text_id: str):
    download_url = create_text_release(text_id)
    return {"download_url": download_url}


@router.get("/{text_id}/notes", response_model=List[schemas.pecha.PedurmaNoteEdit])
def get_text_notes(text_id: str):
    notes = get_pedurma_text_edit_notes(text_id)
    return notes


@router.post("/{text_id}/notes")
def update_text_notes(text_id: str, notes: List[schemas.pecha.PedurmaNoteEdit]):
    update_text_pagination(text_id, notes)


@router.post("/{task_name}/completed", status_code=status.HTTP_201_CREATED)
def mark_text_completed(task_name: str, text_id: str):
    completed_texts_fn = Path.home() / ".openpecha" / task_name
    with completed_texts_fn.open("a") as fn:
        fn.write(f"{text_id}\n")
    return {"message": "Task marked as completed!"}


@router.get("/{task_name}/completed", response_model=List[Optional[str]])
def get_completed_texts(task_name: str):
    completed_texts_fn = Path.home() / ".openpecha" / task_name
    if not completed_texts_fn.is_file():
        return []
    return completed_texts_fn.read_text().splitlines()


@router.get("/{text_id}/notes/proofread", response_model=List[ProofreadNotePage])
def get_proofread_notes(text_id: str):
    data_path = openpecha_config.BASE_PATH / "proofread" / "proofread-nalanda-notes"
    pages = get_note_pages(text_id, data_path)
    return pages


@router.put("/{text_id}/notes/proofread")
def get_proofread_notes(text_id: str, page: ProofreadNotePage):
    data_path = openpecha_config.BASE_PATH / "proofread" / "proofread-nalanda-notes"
    update_note_page(text_id, page, repo_path=data_path)
    return {"success": True}
