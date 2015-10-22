# coding: utf-8
import datetime

from ..models import ProjectEvent, Project


def create_project_event(project: Project, text,
                         data_json: dict=None, event_type: str=None) -> ProjectEvent:
    event = ProjectEvent(project=project, human_text=text)
    event.created_on = datetime.datetime.utcnow()

    if data_json:
        event.optional_data_json = data_json
    if event_type:
        event.optional_event_type = event_type

    return event
