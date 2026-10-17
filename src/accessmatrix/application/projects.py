"""Project application services."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from accessmatrix.api.schemas.projects import ProjectCreate
from accessmatrix.persistence.models import Project


class ProjectNotFoundError(LookupError):
    """Raised when a project does not exist."""


def list_projects(session: Session) -> list[Project]:
    """Return all projects ordered by creation date."""

    statement = select(Project).order_by(Project.created_at.desc())

    return list(session.scalars(statement).all())


def get_project(session: Session, project_id: str) -> Project:
    """Return one project or raise a not-found error."""

    project = session.get(Project, project_id)

    if project is None:
        raise ProjectNotFoundError(f"Project {project_id!r} was not found.")

    return project


def create_project(
    session: Session,
    payload: ProjectCreate,
) -> Project:
    """Create and persist a project."""

    project = Project(
        name=payload.name,
        description=payload.description,
        base_url=payload.base_url,
    )

    session.add(project)
    session.commit()
    session.refresh(project)

    return project


def delete_project(
    session: Session,
    project_id: str,
) -> Project:
    """Delete a project from the database."""

    project = get_project(session, project_id)

    session.delete(project)
    session.commit()

    return project
