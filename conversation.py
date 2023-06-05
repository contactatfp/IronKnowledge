from collections import deque
from models import Project


class Conversation:
    def __init__(self, project_id, max_length=10):
        self.project_id = project_id
        self.company_name = Project.query.get_or_404(project_id).name
        self.messages = deque(maxlen=max_length)
        self.messages.append(
            {"role": "system", "content": f"You are answering questions about the {self.company_name}."})

    def add_user_message(self, content):
        self.messages.append({"role": "user", "content": content})

    def add_model_message(self, content):
        self.messages.append({"role": "assistant", "content": content})
