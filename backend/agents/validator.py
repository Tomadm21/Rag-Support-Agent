from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from state.state_manager import TicketState

class ValidationOutput(BaseModel):
    confidence_score: float = Field(description="A score between 0.0 and 1.0 indicating confidence in the answer's accuracy.")
    needs_human_review: bool = Field(description="True if the score is below 0.8 or if the answer states it cannot help.")
    critique: str = Field(description="Brief explanation of the score.")

class QualityValidator:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=ValidationOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Quality Assurance Specialist for Customer Support.
            Review the draft response against the user query and context.
            
            Check for:
            1. Accuracy: Does the response directly answer the query using the context?
            2. Completeness: Are all parts of the question addressed?
            3. Tone: Is it professional?
            4. Hallucination: Does it invent facts not in the context?
            
            Output JSON matching the schema."""),
            ("human", """Query: {query}
            Context: {context}
            Draft Response: {draft}
            
            {format_instructions}""")
        ]).partial(format_instructions=self.parser.get_format_instructions())
        
        self.chain = self.prompt | self.llm | self.parser

    async def run(self, state: TicketState) -> TicketState:
        """Validate the draft response."""
        query = state.get("customer_query", "")
        context = "\n".join(state.get("retrieved_context", []))
        draft = state.get("draft_response", "")
        
        try:
            result = await self.chain.ainvoke({
                "query": query,
                "context": context,
                "draft": draft
            })
            return {
                "confidence_score": result["confidence_score"],
                "needs_human_review": result["needs_human_review"],
                "critique": result["critique"]
            }
        except Exception as e:
            # Fallback on error -> Human Loop
            print(f"Validation Error: {e}")
            return {
                "confidence_score": 0.0,
                "needs_human_review": True,
                "critique": "Validation failed, requiring manual review."
            }
