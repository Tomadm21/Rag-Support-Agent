from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state.state_manager import TicketState

class ResponseGenerator:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.7)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful and professional Customer Support Agent.
            Your goal is to draft a response to the user's inquiry based *strictly* on the provided context.
            
            Guidelines:
            - Tone: Friendly, empathetic, and professional.
            - Format: Clear, concise paragraphs. Use bullet points if listing steps.
            - If the context doesn't contain the answer, politely state that you will escalate the ticket.
            - Include links to relevant documentation if available in the context.
            
            Context:
            {context}
            """),
            ("human", "User Query: {query}")
        ])
        self.chain = self.prompt | self.llm

    async def run(self, state: TicketState) -> TicketState:
        """Draft a response."""
        query = state.get("customer_query", "")
        context = "\n".join(state.get("retrieved_context", []))
        
        response = await self.chain.ainvoke({
            "query": query,
            "context": context
        })
        
        return {"draft_response": response.content}
