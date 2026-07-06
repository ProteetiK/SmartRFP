from backend.services.pricing_service import PricingService
from backend.tools.calculator_tool import PricingCalculator
from backend.tools.tavily_tool import TavilyTool
from backend.rag.retriever import Retriever


class EstimationService:
    def __init__(self, db):
        self.pricing = PricingService(db)
        self.calculator = PricingCalculator()
        self.tavily = TavilyTool()
        self.retriever = Retriever()
