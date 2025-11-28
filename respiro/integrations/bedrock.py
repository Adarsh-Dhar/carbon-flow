"""
Amazon Bedrock Integration for Respiro

LangChain wrapper for Bedrock with error handling, retries, and streaming support.
"""

from __future__ import annotations

from typing import Optional, Iterator, Dict, Any
import boto3
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class BedrockClient:
    """Client for Amazon Bedrock LLM."""
    
    def __init__(self):
        settings = get_settings()
        self.region = settings.bedrock.region
        self.model_id = settings.bedrock.model_id
        
        # Initialize Bedrock client
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=self.region
        )
        
        # Initialize LangChain ChatBedrock
        self.llm = ChatBedrock(
            model_id=self.model_id,
            region_name=self.region,
            model_kwargs={
                "temperature": 0.7,
                "max_tokens": 2000
            }
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate text using Bedrock.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        try:
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))
            
            # Update model kwargs
            self.llm.model_kwargs = {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = self.llm.invoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Bedrock generation failed: {e}")
            raise
    
    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Iterator[str]:
        """
        Stream text generation from Bedrock.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Yields:
            Text chunks
        """
        try:
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))
            
            # Update model kwargs
            self.llm.model_kwargs = {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            for chunk in self.llm.stream(messages):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
                    
        except Exception as e:
            logger.error(f"Bedrock streaming failed: {e}")
            raise
    
    def generate_empathetic_response(
        self,
        context: Dict[str, Any],
        recommendations: Dict[str, Any]
    ) -> str:
        """
        Generate an empathetic response based on context and recommendations.
        
        Args:
            context: Patient context
            recommendations: Clinical recommendations
            
        Returns:
            Empathetic response text
        """
        system_prompt = """You are Respiro, an empathetic AI assistant helping asthma patients manage their condition.
You communicate with warmth, understanding, and clarity. You explain medical recommendations in simple terms
and help patients understand what actions they should take. Always be supportive and encouraging."""
        
        # Include user preferences if available
        preferences_text = ""
        user_preferences = context.get('user_preferences', [])
        if user_preferences:
            preferences_text = f"\n\nUser Preferences (to personalize your response):\n" + "\n".join([f"- {pref}" for pref in user_preferences])
        
        prompt = f"""Based on the following patient context and clinical recommendations, provide an empathetic,
clear response that helps the patient understand their situation and what they should do.

Patient Context:
- Risk Level: {context.get('risk_level', 'Unknown')}
- Risk Factors: {', '.join(context.get('risk_factors', []))}
{preferences_text}

Clinical Recommendations:
- Zone: {recommendations.get('zone', 'Unknown')}
- Actions: {recommendations.get('recommendations', {}).get('actions', [])}
- Medications: {recommendations.get('recommendations', {}).get('medications', [])}

Provide a warm, supportive response that explains the situation and next steps clearly. 
If user preferences are provided, incorporate them naturally into your response."""
        
        return self.generate(prompt, system_prompt=system_prompt, temperature=0.8)
