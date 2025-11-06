from ..models.change_request import ChangeRequest


def create_change_request(title, description, created_by=None):
    cr = ChangeRequest(title=title, description=description, created_by=created_by)
    return cr
