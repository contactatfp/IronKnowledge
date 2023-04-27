from app import db

# Import your Project model here
# from models import Project

# You can store project data in a dictionary for this example
projects = {}


def create_project(project_name, users):
    project_id = str(len(projects) + 1)
    projects[project_id] = {
        'name': project_name,
        'users': users,
        'summary': '',
    }
    return project_id


def get_project_details(project_id):
    return projects.get(project_id, None)


def update_project_details(project_id, updated_info):
    project = projects.get(project_id, None)
    if project:
        project['name'] = updated_info.get('name', project['name'])
        # Update any other project details here


def delete_project(project_id):
    projects.pop(project_id, None)
