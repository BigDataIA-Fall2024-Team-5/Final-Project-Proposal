from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

class TaskDetectionAgent:
    def __init__(self, model="gpt-4"):
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a task detection agent that classifies queries into categories: 'General Information', 'Course Description', 'SQL Query'."),
            ("user", "{query}")
        ])
        self.model = ChatOpenAI(model=model, temperature=0)

    def detect_task(self, query):
        prompt = self.prompt_template.invoke({"query": query})
        response = self.model.invoke(prompt)
        return response.strip().lower()
