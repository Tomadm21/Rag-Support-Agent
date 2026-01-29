from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state.state_manager import TicketState
import json

class QueryClassifier:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior support routing agent with emotional intelligence.
            Analyze the incoming query and provide:
            1. Category - exactly one of: Billing, Technical, Feature, Bug
            2. Sentiment - exactly one of: Positive, Neutral, Negative
            3. Urgency - exactly one of: Low, Medium, High, Critical

            Format your response as JSON:
            {{
                "category": "category_name",
                "sentiment": "sentiment_name",
                "urgency": "urgency_level"
            }}

            Sentiment Guidelines:
            - Positive: Friendly, appreciative, patient tone
            - Neutral: Standard inquiry, no emotional indicators
            - Negative: Frustrated, angry, disappointed, urgent complaints

            Urgency Guidelines:
            - Critical: Service down, security issue, business blocking
            - High: Important feature broken, duplicate charges
            - Medium: Standard bugs, feature requests
            - Low: General questions, minor issues"""),
            ("human", "{query}")
        ])
        self.chain = self.prompt | self.llm

    async def run(self, state: TicketState) -> TicketState:
        """Categorize the ticket with sentiment and urgency analysis."""

        query = state.get("customer_query", "")
        response = await self.chain.ainvoke({"query": query})

        try:
            # Parse JSON response
            data = json.loads(response.content.strip())
            category = data.get("category", "Technical")
            sentiment = data.get("sentiment", "Neutral")
            urgency = data.get("urgency", "Medium")
        except json.JSONDecodeError:
            # Fallback to old behavior if JSON parsing fails
            print("Warning: Could not parse classifier response as JSON")
            category = "Technical"
            sentiment = "Neutral"
            urgency = "Medium"

        # Validation
        valid_categories = ["Billing", "Technical", "Feature", "Bug"]
        if category not in valid_categories:
            category = "Technical"

        valid_sentiments = ["Positive", "Neutral", "Negative"]
        if sentiment not in valid_sentiments:
            sentiment = "Neutral"

        valid_urgencies = ["Low", "Medium", "High", "Critical"]
        if urgency not in valid_urgencies:
            urgency = "Medium"

        print(f"📊 Classification: {category} | Sentiment: {sentiment} | Urgency: {urgency}")

        return {
            "category": category,
            "sentiment": sentiment,
            "urgency": urgency
        }
