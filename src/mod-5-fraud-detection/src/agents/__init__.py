"""
Fraud Detection Agents Package  
CrewAI-based multi-agent system for fraud detection with Qdrant cloud integration
"""

# Active CrewAI-based system (only include existing files)
from .crewai_qdrant_knowledge import CrewAIQdrantKnowledge, QdrantKnowledgeTool
from .crewai_with_prompts import PromptBasedCrewAISystem
from .prompt_manager import PromptManager

# Default exports (active system)
QdrantKnowledge = CrewAIQdrantKnowledge           # Knowledge base
PromptSystem = PromptBasedCrewAISystem            # Main prompt system
PromptManager = PromptManager                     # Prompt manager

__all__ = [
    # Active CrewAI system
    "CrewAIQdrantKnowledge",
    "QdrantKnowledgeTool",
    "PromptBasedCrewAISystem",
    "PromptManager",
    
    # Convenience aliases
    "QdrantKnowledge",
    "PromptSystem"
]