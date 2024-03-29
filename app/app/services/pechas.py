import shutil
import tempfile
from enum import Enum

from fastapi import HTTPException, UploadFile
from openpecha.blupdate import Blupdate, update_ann_layer
from openpecha.catalog.manager import CatalogManager
from openpecha.core.layer import Layer
from openpecha.core.pecha import OpenPechaFS
from openpecha.exceptions import PechaNotFound
from openpecha.formatters.editor import EditorParser
from openpecha.formatters.empty import EmptyEbook
from openpecha.github_utils import create_release, get_github_repo
from openpecha.serializers import EditorSerializer, EpubSerializer
from openpecha.serializers.docx import DocxSerializer
from openpecha.utils import download_pecha

from app.core.config import settings
from app.utils import save_upload_file_tmp


def get_pecha(pecha_id, branch="master"):
    try:
        pecha_path = download_pecha(pecha_id, branch=branch, needs_update=False)
    except PechaNotFound:
        raise HTTPException(status_code=404, detail="Pecha not found")

    pecha = OpenPechaFS(path=pecha_path)
    return pecha


async def create_opf_pecha(
    text_file: UploadFile,
    title: str,
    subtitle: str,
    author: str,
    collection: str,
    publisher: str,
    sku: str,
    front_cover_image: UploadFile,
    publication_data_image: UploadFile,
):
    front_cover_image_fn = save_upload_file_tmp(front_cover_image)
    publication_data_image_fn = save_upload_file_tmp(publication_data_image)

    metadata = {
        "title": title,
        "subtitle": subtitle,
        "authors": [author],
        "collection": collection,
        "publisher": publisher,
        "id": sku,
        "cover": front_cover_image_fn.name,
        "credit": publication_data_image_fn.name,
    }

    assets = {"image": [front_cover_image_fn, publication_data_image_fn]}

    catalog = CatalogManager(formatter=EmptyEbook(metadata=metadata, assets=assets))
    text = await text_file.read()
    catalog.add_empty_item(text.decode("utf-8"))
    catalog.update()
    return catalog.formatter.pecha_path.name, front_cover_image_fn


def get_old_base(pecha_id, base_id):
    pecha_path = download_pecha(pecha_id, needs_update=False)
    if base_id[0] == "v":
        base_fn = pecha_path / f"{pecha_id}.opf" / "base" / f"{base_id}.txt"
        return base_fn.read_text(encoding="utf-8")


def update_base_layer(pecha_id, base_name, new_base, layers):
    pecha = get_pecha(pecha_id)
    old_base = pecha.get_base(base_name)
    pecha.base[base_name] = new_base
    pecha.save_base()

    updater = Blupdate(old_base, new_base)
    for layer in layers:
        update_ann_layer(layer, updater)
        pecha.save_layer(
            base_name, layer["annotation_type"].value, Layer.parse_obj(layer)
        )
    return layers


class ExportFormat(str, Enum):
    epub = ".epub"
    docx = ".docx"


def get_serializer(pecha_path, format: ExportFormat):
    opf_path = pecha_path / f"{pecha_path.name}.opf"

    if format == ExportFormat.docx:
        serializer = DocxSerializer(opf_path=opf_path)
    else:
        serializer = EpubSerializer(opf_path=opf_path)
    return serializer


def create_export(pecha_id: str, branch: str, format: str):
    pecha_path = download_pecha(pecha_id, branch=branch, needs_update=False)
    serializer = get_serializer(pecha_path, format)

    with tempfile.TemporaryDirectory() as tmpdirname:
        export_fn = serializer.serialize(
            output_path=tmpdirname, toc_levels={"1": "sabche"}
        )
        download_url = create_release(
            pecha_id,
            prerelease=True if branch == "review" else False,
            asset_paths=[export_fn],
            token=settings.GITHUB_TOKEN,
        )
    return download_url


def update_pecha_with_editor_content(pecha_id, base_name, editor_content):
    parser = EditorParser()
    parser.parse(base_name, editor_content)

    pecha = get_pecha(pecha_id)
    pecha.update_base(base_name, parser.base[base_name])
    for layer_name, layer in parser.layers[base_name].items():
        pecha.update_layer(base_name, layer_name, layer)
    pecha.reset_layers(base_name, exclude=parser.layers[base_name])


def create_editor_content_from_pecha(pecha_id, base_name):
    pecha = get_pecha(pecha_id)
    serializer = EditorSerializer(pecha.opf_path)
    for serialized_base_name, result in serializer.serialize():
        if serialized_base_name == base_name:
            return result


def delete_opf_pecha(pecha_id: str):
    repo = get_github_repo(pecha_id, "OpenPecha", settings.GITHUB_TOKEN)
    repo.delete()


def update_pecha_assets(
    pecha: OpenPechaFS, asset_type: str, asset_name: str, file_obj: UploadFile
):
    asset_type_dir = pecha.assets_path / asset_type
    # delete the old asset
    old_asset_fn = asset_type / pecha.meta.source_metadata[asset_name]
    old_asset_fn.unlink()

    new_asset_fn = save_upload_file_tmp(file_obj)
    shutil.copyfile(str(new_asset_fn), str(asset_type_dir / new_asset_fn.name))
    return new_asset_fn.name
