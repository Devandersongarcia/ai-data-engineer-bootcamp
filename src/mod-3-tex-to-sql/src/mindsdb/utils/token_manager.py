"""
Simplified token management for MindsDB chat application
Basic token counting and conversation limits
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TokenManager:
    """Manages token counting and message truncation for chat applications"""
    
    def __init__(self, model: str = "gpt-3.5-turbo", max_tokens: int = 14000):
        """
        Initialize token manager
        
        Args:
            model: OpenAI model name 
            max_tokens: Maximum tokens to allow (leaving buffer for response)
        """
        self.model = model
        self.max_tokens = max_tokens
        logger.info(f"TokenManager initialized for {model} with limit {max_tokens}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string (simplified estimation)"""
        # Simple estimation: ~4 chars per token for most text
        return len(text) // 4
    
    def count_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count total tokens in a list of messages (simplified)"""
        total_chars = 0
        for message in messages:
            for value in message.values():
                if isinstance(value, str):
                    total_chars += len(value)
        # Simple estimation: ~4 chars per token + overhead
        return (total_chars // 4) + len(messages) * 10
    
    def optimize_conversation(self, messages: List[Dict[str, str]], target_ratio: float = 0.8) -> List[Dict[str, str]]:
        """Keep only recent messages if conversation gets too long"""
        if not messages:
            return messages
            
        current_tokens = self.count_message_tokens(messages)
        target_tokens = int(self.max_tokens * target_ratio)
        
        if current_tokens <= target_tokens:
            return messages
        
        # Keep only the most recent messages
        recent_messages = []
        current_tokens = 0
        
        for message in reversed(messages):
            message_tokens = self.count_message_tokens([message])
            if current_tokens + message_tokens > target_tokens:
                break
            recent_messages.insert(0, message)
            current_tokens += message_tokens
        
        logger.info(f"Optimized conversation: {len(messages)} -> {len(recent_messages)} messages")
        return recent_messages
    
    def truncate_text(self, text: str, max_chars: int = 4000) -> str:
        """Truncate text to reasonable length"""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."

def create_token_manager(model: str = "gpt-3.5-turbo") -> TokenManager:
    """Create a simplified token manager"""
    # Use conservative limits for MindsDB chat
    return TokenManager(model, 10000)  # Safe limit for most cases