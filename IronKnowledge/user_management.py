from project import get_project_details, update_project_details


def add_user_to_project(user, project):
    # if user is an email address, then email user inviting them to register
    if '@' in user:
        print('Email user to invite them to register')
    if user not in project.users:
        project.users.append(user)
        db.session.commit()


def remove_user_from_project(user, project):
    if user in project.users:
        project.users.remove(user)
        db.session.commit()


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
