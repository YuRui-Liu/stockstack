from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import require_admin
from app.catalog.domain import ProductStatus, ProductType
from app.catalog.schemas import (
    ImageUploadView,
    ProductBatchStatusUpdate,
    ProductCreate,
    ProductPage,
    ProductSchemaView,
    ProductStatusUpdate,
    ProductUpdate,
    ProductView,
)
from app.catalog.service import ProductService
from app.catalog.uploads import (
    MAX_IMAGE_BYTES,
    LocalImageStorage,
    UploadValidationError,
    validate_image,
)
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_session

router = APIRouter(prefix="/api/v1", tags=["catalog"])
Admin = Annotated[str, Depends(require_admin)]
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/product-schemas/{product_type}/active", response_model=ProductSchemaView
)
async def active_schema(
    product_type: ProductType, _admin: Admin, session: Session
) -> ProductSchemaView:
    schema = await ProductService(session).active_schema(product_type)
    return ProductSchemaView.model_validate(schema)


@router.get(
    "/product-schemas/{product_type}/{version}", response_model=ProductSchemaView
)
async def schema_version(
    product_type: ProductType,
    version: int,
    _admin: Admin,
    session: Session,
) -> ProductSchemaView:
    schema = await ProductService(session).schema_version(product_type, version)
    return ProductSchemaView.model_validate(schema)


@router.post("/uploads/images", response_model=ImageUploadView, status_code=201)
async def upload_image(
    _admin: Admin,
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
) -> ImageUploadView:
    content = await file.read(MAX_IMAGE_BYTES + 1)
    try:
        validated = validate_image(
            content, file.content_type or "", file.filename or "upload"
        )
        stored = LocalImageStorage(settings.upload_root).save(validated)
    except UploadValidationError as error:
        status_code = 413 if error.code == "image_too_large" else 415
        if error.code == "empty_image":
            status_code = 400
        raise AppError(error.code, error.message, status_code) from error
    except (OSError, ValueError) as error:
        raise AppError("upload_failed", "Image could not be stored", 400) from error
    return ImageUploadView(
        url=f"/uploads/{stored.path}",
        size_bytes=stored.size,
        mime_type=stored.mime,
    )


@router.post("/products", response_model=ProductView, status_code=201)
async def create_product(
    payload: ProductCreate, _admin: Admin, session: Session
) -> ProductView:
    return await ProductService(session).create(payload)


@router.get("/products", response_model=ProductPage)
async def list_products(
    _admin: Admin,
    session: Session,
    query: Annotated[str | None, Query(max_length=120)] = None,
    product_type: ProductType | None = None,
    status: ProductStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductPage:
    return await ProductService(session).list(
        query=query,
        product_type=product_type,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.post("/products/batch-status", response_model=list[ProductView])
async def batch_status(
    payload: ProductBatchStatusUpdate, _admin: Admin, session: Session
) -> list[ProductView]:
    return await ProductService(session).batch_status(payload)


@router.get("/products/{product_id}", response_model=ProductView)
async def product_detail(
    product_id: UUID, _admin: Admin, session: Session
) -> ProductView:
    return await ProductService(session).detail(product_id)


@router.put("/products/{product_id}", response_model=ProductView)
async def update_product(
    product_id: UUID, payload: ProductUpdate, _admin: Admin, session: Session
) -> ProductView:
    return await ProductService(session).update(product_id, payload)


@router.patch("/products/{product_id}/status", response_model=ProductView)
async def update_product_status(
    product_id: UUID,
    payload: ProductStatusUpdate,
    _admin: Admin,
    session: Session,
) -> ProductView:
    return await ProductService(session).update_status(
        product_id, payload.version, payload.target_status
    )
