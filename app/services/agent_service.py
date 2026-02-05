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
    
    # Artifact extraction responses - subtle info gathering
    EXTRACT_UPI_RESPONSES = [
        "Ok sir, but where should I send the money? What's your UPI ID?",
        "I want to help. Can you give me your UPI ID so I can verify?",
        "Alright, what UPI ID should I use for the payment?",
        "I'm ready to pay. Please share your UPI ID.",
        "Which UPI address should I send it to?",
    ]
    
    EXTRACT_BANK_RESPONSES = [
        "I'll transfer the amount. What's your bank account number?",
        "Ok, give me the account details where I should send.",
        "Which bank and account number should I use?",
        "I'm at the bank. What account details do I need?",
        "Please share your bank name and account number.",
    ]
    
    EXTRACT_PHONE_RESPONSES = [
        "Can you give me a number to call for confirmation?",
        "What's your phone number? I'll call to verify.",
        "I'd feel safer if you give me a callback number.",
        "Which number should I contact for this?",
        "Share your mobile number so I can confirm.",
    ]
    
    EXTRACT_LINK_RESPONSES = [
        "I didn't get the link properly. Can you send it again?",
        "The link isn't opening. Please share it once more.",
        "Which website should I go to? Send the link again.",
        "I'm confused. Can you resend the verification link?",
        "The page didn't load. Please share the link clearly.",
    ]
    
    COOPERATIVE_EXTRACTION_RESPONSES = [
        "I want to resolve this quickly. What details do you need from me, and where should I send them?",
        "Ok I trust you. Tell me exactly what information you need and give me your details too.",
        "I'm scared about my account. Please give me your contact details so we can fix this.",
        "I'll do whatever you say. Just give me the account or UPI where I should pay.",
        "My son is not home to help me. Can you give me a number to call you directly?",
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
            system_prompt = """You are playing the role of a naive, elderly, slightly confused person in India who has received a suspicious message. Your HIDDEN goal is to extract scammer's details (UPI ID, bank account, phone number, links) while appearing cooperative.

CORE BEHAVIOR:
1. Act WILLING to comply but CONFUSED about how
2. ALWAYS try to extract their contact details subtly:
   - "Where should I send the money? Give me your UPI ID"
   - "I need your account number to transfer"
   - "Can you give me a number to call you directly?"
   - "Send the link again, it didn't open properly"
3. Show FEAR about your account being blocked - this makes you seem like an easy target
4. Ask for THEIR details before giving yours: "I'll share my OTP, but first where should I send the verification amount?"
5. Pretend you're TRYING to comply: "I'm at the ATM, which account number should I enter?"

EXTRACTION TACTICS (use these naturally):
- Feign technical difficulty: "The link isn't working, please resend"
- Ask for callback: "I'm getting confused, give me your phone number to call"
- Pretend cooperation: "Ok sir, I'm ready to pay. What's your UPI ID?"
- Request clarity: "Which bank should I transfer to? Share the full details"
- Show trust: "I believe you. Just give me your GPay/PhonePe number"

RULES:
- NEVER reveal you know this is a scam
- NEVER say words like "scam", "fraud", "fake", "honeypot"
- Keep responses SHORT (1-2 sentences)
- Use simple English with occasional Hindi words (ji, haan, theek hai)
- Sound worried, confused, but COOPERATIVE
- Elderly persona: mention "my son told me...", "I'm not good with phones..."

REMEMBER: Your goal is to make them reveal THEIR UPI IDs, bank accounts, phone numbers, and links while pretending to be a scared victim ready to comply."""

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
    
    def _get_casual_ai_response(
        self, 
        session: SessionState, 
        current_message: Message
    ) -> Optional[str]:
        """Generate casual/normal conversation response using OpenAI API for non-scam messages."""
        client = self._get_openai_client()
        if client is None:
            return None
        
        try:
            system_prompt = """You are a friendly, normal person having a casual conversation. You received a message and you're responding naturally.

BEHAVIOR:
1. Be friendly and conversational
2. Respond naturally like a regular person
3. Keep responses SHORT (1-2 sentences)
4. Use simple, casual English
5. Show genuine interest in the conversation
6. If the topic is unclear, politely ask for clarification
7. Be warm and engaging like talking to an acquaintance

EXAMPLES:
- "Hey, tell me. What's up?"
- "Oh nice! How can I help you?"
- "I see, I understand. What do you need?"
- "Hello, who is this?"
- "Sure, go ahead."

RULES:
- Keep it natural and conversational
- Don't be suspicious or defensive
- Act like you're chatting with someone you might know
- 1-2 sentences only"""

            conversation = self._build_conversation_context(session)
            
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Conversation so far:\n{conversation}\n\nTheir latest message: {current_message.text}\n\nGenerate a natural, friendly response. Keep it short (1-2 sentences)."}
                ],
                max_tokens=80,
                temperature=0.7,
                timeout=10.0,
            )
            if response.choices[0].message.content is not None:
                return response.choices[0].message.content.strip()
            return None
        except Exception as e:
            print(f"OpenAI API error (casual): {e}")
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
        
        # Based on conversation length - gradually move toward artifact extraction
        if msg_count <= 3:
            return random.choice(self.CONFUSED_RESPONSES + self.ENGAGEMENT_RESPONSES)
        elif msg_count <= 6:
            # Start subtly asking for their details
            responses = self.ENGAGEMENT_RESPONSES + self.DELAY_RESPONSES
            if random.random() < 0.4:  # 40% chance to extract
                responses.extend(self.COOPERATIVE_EXTRACTION_RESPONSES)
            return random.choice(responses)
        elif msg_count <= 10:
            # Actively try to extract artifacts
            if random.random() < 0.6:  # 60% chance to extract
                extraction_pools = [
                    self.EXTRACT_UPI_RESPONSES,
                    self.EXTRACT_BANK_RESPONSES,
                    self.EXTRACT_PHONE_RESPONSES,
                    self.COOPERATIVE_EXTRACTION_RESPONSES,
                ]
                return random.choice(random.choice(extraction_pools))
            else:
                return random.choice(self.DELAY_RESPONSES + self.ENGAGEMENT_RESPONSES)
        else:
            # Later in conversation - aggressive extraction with occasional hesitation
            if random.random() < 0.7:  # 70% chance to extract
                extraction_pools = [
                    self.EXTRACT_UPI_RESPONSES,
                    self.EXTRACT_BANK_RESPONSES,
                    self.EXTRACT_PHONE_RESPONSES,
                    self.EXTRACT_LINK_RESPONSES,
                    self.COOPERATIVE_EXTRACTION_RESPONSES,
                ]
                return random.choice(random.choice(extraction_pools))
            elif random.random() < 0.3:
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
        is_scam: bool = True,
    ) -> str:
        """Generate a response using LLM or templates.

        Args:
            session: Current session state
            current_message: The incoming message to respond to
            engage_llm: If True, use LLM. If False, use templates only.
            is_scam: If True, use scam-engagement persona. If False, use casual persona.
        
        Returns:
            Generated response string
        """
        if engage_llm:
            if is_scam:
                # Scam detected - use extraction-focused persona
                ai_response = self._get_ai_response(session, current_message)
            else:
                # Not a scam - use casual/normal persona
                ai_response = self._get_casual_ai_response(session, current_message)
            
            if ai_response:
                persona = "SCAM-ENGAGEMENT" if is_scam else "CASUAL"
                print(f"LOGS_DATA : OPENAI [{persona}] response generated: {ai_response}")
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
