# coding: utf-8
import datetime

from ..models import Project, ProjectEvent
from ..constants import EventType
from ..models import ProjectEvent, Project


def get_recent_events_by_type(project: Project, event_type: EventType,
                              limit: int=10) -> "List[ProjectEvent]":
    return (
        ProjectEvent.query
        .join(Project)
        .filter(ProjectEvent.optional_event_type == event_type)
        .order_by(ProjectEvent.created_on.desc())
        .limit(10)
    )


def create_project_event(project: Project, text,
                         data_json=None, event_type=None) -> ProjectEvent:
    event = ProjectEvent(project=project, human_text=text)
    event.created_on = datetime.datetime.utcnow()

    if data_json:
        event.optional_data_json = data_json
    if event_type:
        event.optional_event_type = event_type

    return event
