from datetime import datetime

from project import get_project_details, update_project_details


def create_version(project_id):
    project = get_project_details(project_id)

    if not project:
        return None

    if 'versions' not in project:
        project['versions'] = []

    version = {
        'version_number': len(project['versions']) + 1,
        'summary': project['summary'],
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    project['versions'].append(version)
    update_project_details(project_id, project)
    return version['version_number']


def get_version_history(project_id):
    project = get_project_details(project_id)
    if project:
        return project.get('versions', [])
    return None


def compare_versions(project_id, version_number_1, version_number_2):
    versions = get_version_history(project_id)

    if not versions:
        return None

    version_1 = None
    version_2 = None

    for version in versions:
        if version['version_number'] == version_number_1:
            version_1 = version
        if version['version_number'] == version_number_2:
            version_2 = version
        if version_1 and version_2:
            break

    if not (version_1 and version_2):
        return None

    # Add your logic to compare the two versions and highlight the differences
    # This could involve using a library like difflib or implementing your own comparison algorithm

    differences = "Sample differences between version {} and version {}".format(version_number_1, version_number_2)
    return differences
