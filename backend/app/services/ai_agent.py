from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool
from app.services.google_calendar import GoogleCalendarService
from app.core.config import settings
from datetime import datetime, timedelta

class AIAgentService:
    def __init__(self, business_id: int, db_session):
        self.business_id = business_id
        self.db = db_session
        self.llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=settings.OPENAI_API_KEY)
        
        # Define tools
        @tool
        def check_availability(date_str: str):
            """Checks availability for a specific date (YYYY-MM-DD)."""
            # Logic to check Google Calendar for free slots
            # For simplicity in this prototype, we'll return a mock or actual free slots
            return "Available slots: 10:00 AM, 2:00 PM, 4:00 PM"

        @tool
        def book_appointment(date_str: str, time_str: str):
            """Books an appointment for a specific date and time."""
            # Logic to call GoogleCalendarService.create_event
            return f"Appointment booked for {date_str} at {time_str}"

        self.tools = [check_availability, book_appointment]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant for a business. Your goal is to help clients schedule their recurring appointments. Be professional, friendly, and concise."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    def process_message(self, client_id: int, message_body: str, chat_history=None):
        if chat_history is None:
            chat_history = []
        
        response = self.agent_executor.invoke({
            "input": message_body,
            "chat_history": chat_history
        })
        return response["output"]
