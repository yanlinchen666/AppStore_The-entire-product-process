import logging
import json
import os
from typing import Dict, Any, Optional, List
from app.config import settings
import httpx

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        
        if self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "siliconflow":
            self._init_siliconflow()
        else:
            logger.error(f"Unknown LLM provider: {self.provider}")
            raise ValueError(f"Unknown LLM provider: {self.provider}")
    
    def _init_gemini(self):
        try:
            from google.genai import Client, types
            
            proxy_url = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", ""))
            
            http_options = None
            if proxy_url:
                transport = httpx.HTTPTransport(proxy=proxy_url)
                custom_client = httpx.Client(transport=transport)
                http_options = types.HttpOptions(httpx_client=custom_client)
                logger.info(f"Gemini API configured with proxy: {proxy_url}")
            
            self.client = Client(api_key=settings.GEMINI_API_KEY, http_options=http_options)
            self.model_name = settings.GEMINI_MODEL
            logger.info(f"Using Gemini provider: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise
    
    def _init_siliconflow(self):
        try:
            from openai import OpenAI
            
            self.client = OpenAI(
                api_key=settings.SILICONFLOW_API_KEY,
                base_url=settings.SILICONFLOW_BASE_URL
            )
            self.model_name = settings.SILICONFLOW_LLM_MODEL
            logger.info(f"Using SiliconFlow provider: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SiliconFlow client: {str(e)}")
            raise
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            if self.provider == "gemini":
                return self._gemini_chat_completion(messages, **kwargs)
            else:
                return self._siliconflow_chat_completion(messages, **kwargs)
                
        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            raise
    
    def _gemini_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg["content"])
        
        contents = []
        if system_message:
            contents.append({"role": "user", "parts": [{"text": system_message}]})
        
        for msg in user_messages:
            contents.append({"role": "user", "parts": [{"text": msg}]})
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            **kwargs
        )
        
        return response.text.strip()
    
    def _siliconflow_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
        
        return response.choices[0].message.content.strip()
    
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
            {"role": "system", "content": "You are a product analyst specializing in app store review analysis. Return only JSON format."},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat_completion(messages)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response from LLM")
            return {"topics": [], "findings": []}
    
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
            {"role": "system", "content": "You are a product manager writing PRDs based on user feedback. Return only JSON format."},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat_completion(messages)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response from LLM")
            return {"requirements": [], "versions": []}
    
    def generate_test_cases(self, requirements: List[Dict]) -> Dict[str, Any]:
        prompt = f"""
        Based on the following product requirements, generate test cases.
        
        Requirements:
        {chr(10).join([f"{i+1}. {r['text']} (Priority: {r['priority']})" for i, r in enumerate(requirements)])}
        
        Return a JSON object with:
        "test_cases": array of objects with "requirement_index", "title", "description", "steps", "expected_result", "priority"
        """
        
        messages = [
            {"role": "system", "content": "You are a QA engineer generating test cases. Return only JSON format."},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat_completion(messages)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response from LLM")
            return {"test_cases": []}

llm_client = LLMClient()