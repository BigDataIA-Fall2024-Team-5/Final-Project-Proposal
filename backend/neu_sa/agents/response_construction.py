class ResponseConstructionAgent:
    def construct_response(self, task, results):
        """Constructs a final response based on task type and results."""
        if task == "course description":
            return "\n".join([
                f"Course Code: {res['course_code']}\n"
                f"Course Name: {res['course_name']}\n"
                f"Description: {res['description']}\n"
                f"Prerequisites: {res['prerequisites']}\n"
                f"Credits: {res['credits']}\n"
                for res in results
            ])
        elif task == "sql query":
            return f"SQL Query Results:\n{results}"
        elif task == "general information":
            return f"General Information:\n{results}"
        return "Unknown task."
