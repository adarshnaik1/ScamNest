"""
AI Agent service for generating human-like responses.
"""

import random
from typing import Optional, List
from ..models.schemas import SessionState, Message
from ..config import get_settings


class AgentService:
    """
    Generates human-like responses to engage with scammers.
    Uses OpenAI API if available, otherwise falls back to template responses.
    """
    
    #  Fallback Response templates for different scenarios when OPENAI api key is not available
    INITIAL_RESPONSES = [
        "Oh no, what happened to my account?",
        "What? This is very concerning! What do I need to do?",
        "I don't understand. Why would my account be blocked?",
        "Really? I didn't receive any other notification about this.",
        "This sounds serious. Can you explain what's happening?",
    ]
    
    CONFUSED_RESPONSES = [
        "I'm not sure I understand. Can you explain again?",
        "Wait, what exactly do you need from me?",
        "I'm a bit confused. What should I do?",
        "Can you clarify what you mean?",
        "I don't get it. Please explain in simple terms.",
    ]
    
    VERIFICATION_RESPONSES = [
        "How can I verify that you're really from the bank?",
        "This seems suspicious. How do I know this is legitimate?",
        "Can you prove you're authorized to ask for this?",
        "I'd like some proof before I share anything.",
        "My bank told me never to share these details. Are you sure?",
    ]
    
    ENGAGEMENT_RESPONSES = [
        "Okay, what do you need me to do?",
        "Alright, I want to resolve this. What's next?",
        "I'm worried about my money. Please help me.",
        "Tell me what information you need.",
        "I'll cooperate. Just help me fix this.",
    ]
    
    DELAY_RESPONSES = [
        "Give me a moment, I need to find my documents.",
        "Wait, let me check my bank app first.",
        "Hold on, I'm looking for the details you asked for.",
        "Just a minute, my phone is slow.",
        "I need to find my card. Please wait.",
    ]
    
    HESITATION_RESPONSES = [
        "I'm not comfortable sharing this over message.",
        "My son told me not to share such details. Is there another way?",
        "Can't I just visit the bank branch instead?",
        "I'd rather call the official helpline. What's the number?",
        "This doesn't feel right. Let me think about it.",
    ]
    
    UPI_QUESTION_RESPONSES = [
        "Why do you need my UPI ID?",
        "I usually only share this for receiving money. Are you sending me something?",
        "What will you do with my UPI ID?",
        "Is it safe to share my UPI?",
    ]
    
    OTP_QUESTION_RESPONSES = [
        "I thought we should never share OTP?",
        "My bank always says don't share OTP. Why do you need it?",
        "I'm getting an OTP message. Should I really share it?",
        "This OTP message says not to share with anyone...",
    ]
    
    def __init__(self):
        """Initialize agent service."""
        self.settings = get_settings()
        self._openai_client = None
        
    def _get_openai_client(self):
        """Lazily initialize OpenAI client."""
        if self._openai_client is None and self.settings.openai_api_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.settings.openai_api_key)
            except Exception:
                pass
        return self._openai_client
    
    def _build_conversation_context(self, session: SessionState) -> str:
        """Build conversation context for AI."""
        context_parts = []
        for msg in session.messages[-10:]:  # Last 10 messages
            role = "Scammer" if msg.sender.lower() == "scammer" else "You"
            context_parts.append(f"{role}: {msg.text}")
        return "\n".join(context_parts)
    
    def _get_ai_response(
        self, 
        session: SessionState, 
        current_message: Message
    ) -> Optional[str]:
        """Generate response using OpenAI API."""
        client = self._get_openai_client()
        if client is None:
            return None
        
        try:
            system_prompt = """You are playing the role of a naive, slightly confused person who has received a suspicious message. Your goal is to:
1. Act like a regular person who doesn't know about scams
2. Ask questions to keep the conversation going
3. Express concern and confusion naturally
4. Sometimes hesitate before sharing information
5. NEVER reveal that you know this is a scam
6. NEVER mention terms like "scam", "fraud", "honeypot", or "detection"
7. Keep responses short and natural (1-2 sentences)
8. Use casual language with occasional typos
9. Show emotions like worry, confusion, or slight trust

Remember: You're gathering information about the scammer while appearing to be a potential victim."""

            conversation = self._build_conversation_context(session)
            
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Conversation so far:\n{conversation}\n\nScammer's latest message: {current_message.text}\n\nGenerate a natural response as if you're a confused potential victim. Keep it short (1-2 sentences)."}
                ],
                max_tokens=100,
                temperature=0.8,
                timeout=10.0,
            )
            if response.choices[0].message.content is not None:
                return response.choices[0].message.content.strip()
            return None
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None
    
    #This part is only meant for generating template responses in case openai api keys are not available
    def _select_template_response(
        self, 
        session: SessionState, 
        current_message: Message
    ) -> str:
        """Select appropriate template response based on context."""
        text_lower = current_message.text.lower()
        msg_count = session.totalMessages
        
        # First message - show initial concern
        if msg_count <= 1:
            return random.choice(self.INITIAL_RESPONSES)
        
        # Check for specific requests
        if any(word in text_lower for word in ['upi', 'upi id', 'vpa']):
            return random.choice(self.UPI_QUESTION_RESPONSES)
        
        if any(word in text_lower for word in ['otp', 'code', 'pin', 'password']):
            return random.choice(self.OTP_QUESTION_RESPONSES)
        
        if any(word in text_lower for word in ['click', 'link', 'http', 'www']):
            return random.choice(self.VERIFICATION_RESPONSES)
        
        # Based on conversation length
        if msg_count <= 3:
            return random.choice(self.CONFUSED_RESPONSES + self.ENGAGEMENT_RESPONSES)
        elif msg_count <= 6:
            responses = self.ENGAGEMENT_RESPONSES + self.DELAY_RESPONSES
            if random.random() < 0.3:
                responses.extend(self.HESITATION_RESPONSES)
            return random.choice(responses)
        else:
            # Later in conversation - mix of engagement and hesitation
            if random.random() < 0.4:
                return random.choice(self.HESITATION_RESPONSES + self.VERIFICATION_RESPONSES)
            else:
                return random.choice(self.DELAY_RESPONSES + self.ENGAGEMENT_RESPONSES)
    
    def generate_response(
        self, 
        session: SessionState, 
        current_message: Message
    ) -> str:
        """
        Generate a response to the scammer's message.
        Uses AI if available, falls back to templates.
        """
        # Try AI response first
        ai_response = self._get_ai_response(session, current_message)
        if ai_response:
            print("LOGS_DATA : OPENAI response generated and it is {"+ ai_response +"}")
            return ai_response
        
        # Fall back to template responses
        return self._select_template_response(session, current_message)

    def generate_response_conditional(
        self,
        session: SessionState,
        current_message: Message,
        engage_llm: bool,
    ) -> str:
        """Generate a response only using the LLM when `engage_llm` is True.

        If `engage_llm` is False, this will always use the template selector
        and will not call the OpenAI API.
        """
        if engage_llm:
            ai_response = self._get_ai_response(session, current_message)
            if ai_response:
                print("LOGS_DATA : OPENAI response generated and it is {"+ ai_response +"}")
                return ai_response
            return self._select_template_response(session, current_message)

        # Do not call LLM; use template response only
        return self._select_template_response(session, current_message)
    
    def should_continue_engagement(self, session: SessionState) -> bool:
        """
        Determine if the agent should continue engaging.
        Returns False if engagement should end.
        """
        # Continue if scam not yet confirmed
        #This part may need to be updated once the ML based scam detection is utilized
        if not session.scamDetected:
            return True
        
        # Continue if not enough intelligence gathered
        if session.extractedIntelligence.is_empty():
            return True
        
        # Continue for at least minimum messages
        if session.totalMessages < self.settings.min_messages_for_callback:
            return True
        
        # Random chance to continue even after confirmation (30%)
        if random.random() < 0.3:
            return True
        
        return False
