import logging
from typing import Dict, Any, Optional, List
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
        )
        self.model = settings.OPENAI_MODEL
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            raise
    
    def classify_reviews(self, reviews: List[str]) -> Dict[str, Any]:
        prompt = f"""
        Analyze the following app store reviews and identify key topics/issues.
        Return a JSON object with:
        1. "topics": array of objects with "name", "description", and "sample_count"
        2. "findings": array of objects with "topic", "finding", "confidence" (0-1), and "supporting_excerpts"
        
        Reviews:
        {chr(10).join(reviews[:20])}
        """
        
        messages = [
            {"role": "system", "content": "You are a product analyst specializing in app store review analysis."},
            {"role": "user", "content": prompt}
        ]
        
        return self.chat_completion(messages, response_format={"type": "json_object"})
    
    def generate_prd(self, findings: List[Dict], analysis_goal: str = "") -> Dict[str, Any]:
        prompt = f"""
        Based on the following analysis findings, generate a Product Requirements Document (PRD).
        Analysis Goal: {analysis_goal}
        
        Findings:
        {chr(10).join([f"- {f['finding']}" for f in findings])}
        
        Return a JSON object with:
        1. "requirements": array of objects with "text", "type", "priority", "source_finding"
        2. "versions": array of objects with "name", "description", "requirements"
        """
        
        messages = [
            {"role": "system", "content": "You are a product manager writing PRDs based on user feedback."},
            {"role": "user", "content": prompt}
        ]
        
        return self.chat_completion(messages, response_format={"type": "json_object"})
    
    def generate_test_cases(self, requirements: List[Dict]) -> Dict[str, Any]:
        prompt = f"""
        Based on the following product requirements, generate test cases.
        
        Requirements:
        {chr(10).join([f"{i+1}. {r['text']} (Priority: {r['priority']})" for i, r in enumerate(requirements)])}
        
        Return a JSON object with:
        "test_cases": array of objects with "requirement_index", "title", "description", "steps", "expected_result", "priority"
        """
        
        messages = [
            {"role": "system", "content": "You are a QA engineer generating test cases."},
            {"role": "user", "content": prompt}
        ]
        
        return self.chat_completion(messages, response_format={"type": "json_object"})

llm_client = LLMClient()