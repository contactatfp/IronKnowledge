import requests
from project import get_project_details

def search_living_document(project_id, search_query):
    project = get_project_details(project_id)

    if not project:
        return None

    living_document = project['summary']
    attachments = project.get('attachments', [])

    # Generate a search prompt using GPT-4
    openai_secret = get_secret("openai")
    api_key = openai_secret["api_key"]

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    data = {
        "model": "gpt-4",
        "max_tokens": 1970,
        "temperature": 0,
        "top_p": 1,
        "n": 1,
        "stream": False,
        "messages": [
            {"role": "user", "content": f"Search the living document with the query: {search_query}"}
        ]
    }

    response = requests.post('https://api.openai.com/v1/engines/davinci-codex/completions', json=data, headers=headers)
    response_data = response.json()
    search_results = response_data.get('choices', [])[0].get('text', '').strip()

    # You can modify the search results formatting and include attachments if needed

    return search_results
