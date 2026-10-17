"""Project management API routes."""

import shutil
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from accessmatrix.api.schemas.operations import (
    OperationParameterRead,
    OperationRead,
    ProjectOperationsRead,
)
from accessmatrix.api.schemas.projects import (
    ProjectCreate,
    ProjectRead,
)
from accessmatrix.application.projects import (
    ProjectNotFoundError,
    create_project,
    delete_project,
    get_project,
    list_projects,
)
from accessmatrix.openapi.loader import (
    OpenAPIImportError,
    OpenAPIMetadata,
    parse_openapi_document,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
    discover_operations,
)
from accessmatrix.persistence.database import (
    get_session,
)
from accessmatrix.persistence.models import Project
from accessmatrix.persistence.storage import (
    get_storage_root,
)

MAX_OPENAPI_FILE_SIZE = 10 * 1024 * 1024

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Projects"],
)

SessionDependency = Annotated[
    Session,
    Depends(get_session),
]

StorageDependency = Annotated[
    Path,
    Depends(get_storage_root),
]


def project_or_404(
    session: Session,
    project_id: str,
) -> Project:
    """Return a project or raise an HTTP 404 response."""

    try:
        return get_project(
            session,
            project_id,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


def resolve_project_specification_path(
    project: Project,
    storage_root: Path,
) -> Path:
    """Resolve and validate a project's stored specification path."""

    if not project.spec_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("This project does not have an OpenAPI document."),
        )

    resolved_storage_root = storage_root.resolve()

    specification_path = (resolved_storage_root / project.spec_path).resolve()

    if not specification_path.is_relative_to(resolved_storage_root):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("The stored OpenAPI path is invalid."),
        )

    if not specification_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("The stored OpenAPI document could not be found."),
        )

    return specification_path


def load_project_openapi_document(
    project: Project,
    storage_root: Path,
) -> tuple[
    dict[str, Any],
    OpenAPIMetadata,
]:
    """Read and validate a project's OpenAPI document."""

    specification_path = resolve_project_specification_path(
        project,
        storage_root,
    )

    try:
        content = specification_path.read_bytes()
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("The stored OpenAPI document could not be read."),
        ) from exc

    try:
        return parse_openapi_document(
            content,
            specification_path.name,
        )
    except OpenAPIImportError as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail=str(exc),
        ) from exc


def build_operation_response(
    operation: OpenAPIOperation,
) -> OperationRead:
    """Convert a discovered operation into an API response."""

    return OperationRead(
        key=operation.key,
        method=operation.method,
        path=operation.path,
        operation_id=operation.operation_id,
        summary=operation.summary,
        description=operation.description,
        tags=list(operation.tags),
        deprecated=operation.deprecated,
        security_required=(operation.security_required),
        parameters=[
            OperationParameterRead(
                name=parameter.name,
                location=parameter.location,
                required=parameter.required,
                schema_type=parameter.schema_type,
                description=parameter.description,
            )
            for parameter in operation.parameters
        ],
        request_content_types=list(operation.request_content_types),
        response_codes=list(operation.response_codes),
    )


@router.get(
    "",
    response_model=list[ProjectRead],
)
def read_projects(
    session: SessionDependency,
) -> list[ProjectRead]:
    """List all AccessMatrix projects."""

    projects = list_projects(session)

    return [ProjectRead.model_validate(project) for project in projects]


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_new_project(
    payload: ProjectCreate,
    session: SessionDependency,
) -> ProjectRead:
    """Create a new AccessMatrix project."""

    project = create_project(
        session,
        payload,
    )

    return ProjectRead.model_validate(project)


@router.get(
    "/{project_id}/operations",
    response_model=ProjectOperationsRead,
)
def read_project_operations(
    project_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> ProjectOperationsRead:
    """Discover operations from an imported OpenAPI document."""

    project = project_or_404(
        session,
        project_id,
    )

    document, metadata = load_project_openapi_document(
        project,
        storage_root,
    )

    operations = discover_operations(document)

    return ProjectOperationsRead(
        project_id=project.id,
        openapi_title=metadata.title,
        openapi_version=metadata.version,
        operation_count=len(operations),
        operations=[build_operation_response(operation) for operation in operations],
    )


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
)
def read_project(
    project_id: str,
    session: SessionDependency,
) -> ProjectRead:
    """Read one project."""

    project = project_or_404(
        session,
        project_id,
    )

    return ProjectRead.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_project(
    project_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> Response:
    """Delete a project and its locally stored files."""

    try:
        delete_project(
            session,
            project_id,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    project_directory = storage_root / "projects" / project_id

    shutil.rmtree(
        project_directory,
        ignore_errors=True,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.post(
    "/{project_id}/openapi",
    response_model=ProjectRead,
)
async def upload_openapi_document(
    project_id: str,
    file: Annotated[
        UploadFile,
        File(
            description=("OpenAPI YAML or JSON document"),
        ),
    ],
    session: SessionDependency,
    storage_root: StorageDependency,
) -> ProjectRead:
    """Upload and validate an OpenAPI specification."""

    project = project_or_404(
        session,
        project_id,
    )

    original_filename = Path(
        file.filename or "openapi.yaml",
    ).name

    try:
        content = await file.read(
            MAX_OPENAPI_FILE_SIZE + 1,
        )
    finally:
        await file.close()

    if not content:
        raise HTTPException(
            status_code=(status.HTTP_400_BAD_REQUEST),
            detail=("The uploaded OpenAPI file is empty."),
        )

    if len(content) > MAX_OPENAPI_FILE_SIZE:
        raise HTTPException(
            status_code=(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
            detail=("The OpenAPI file exceeds the 10 MiB limit."),
        )

    try:
        _, metadata = parse_openapi_document(
            content,
            original_filename,
        )
    except OpenAPIImportError as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail=str(exc),
        ) from exc

    suffix = Path(
        original_filename,
    ).suffix.lower()

    stored_filename = f"openapi{suffix}"

    project_directory = storage_root / "projects" / project.id

    project_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for existing_name in (
        "openapi.yaml",
        "openapi.yml",
        "openapi.json",
    ):
        existing_path = project_directory / existing_name

        if existing_path.exists():
            existing_path.unlink()

    destination = project_directory / stored_filename

    temporary_destination = destination.with_suffix(
        f"{destination.suffix}.tmp",
    )

    temporary_destination.write_bytes(content)
    temporary_destination.replace(destination)

    project.openapi_version = metadata.version
    project.openapi_title = metadata.title
    project.spec_filename = original_filename
    project.spec_path = str(
        destination.relative_to(storage_root),
    )
    project.operation_count = metadata.operation_count

    session.add(project)
    session.commit()
    session.refresh(project)

    return ProjectRead.model_validate(project)
