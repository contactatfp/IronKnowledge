from project import get_project_details, update_project_details


def add_user_to_project(user_id, project_id):
    project = get_project_details(project_id)
    if project and user_id not in project['users']:
        project['users'].append(user_id)
        update_project_details(project_id, project)


def remove_user_from_project(user_id, project_id):
    project = get_project_details(project_id)
    if project and user_id in project['users']:
        project['users'].remove(user_id)
        update_project_details(project_id, project)


def get_user_permissions(user_id, project_id):
    project = get_project_details(project_id)
    if project:
        # Assuming the permissions are stored in the 'users' dictionary
        return project['users'].get(user_id, None)
    return None


def update_user_permissions(user_id, project_id, new_permissions):
    project = get_project_details(project_id)
    if project:
        project['users'][user_id] = new_permissions
        update_project_details(project_id, project)
