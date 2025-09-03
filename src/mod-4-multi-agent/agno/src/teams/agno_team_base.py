"""
Agno Team Base Implementation - Phase 1
Modern team architecture using Agno's native Team class
"""
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.storage.postgres import PostgresStorage
from agno.tools.reasoning import ReasoningTools
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
import asyncio
from ..config.settings import settings
from ..agents.base_agent import UberEatsBaseAgent

logger = logging.getLogger(__name__)


class AgnoTeamBase:
    """
    Base class for Agno Teams with enhanced features
    Replaces custom orchestration with native Agno Team functionality
    """
    
    def __init__(
        self,
        team_name: str,
        team_role: str,
        team_mode: str = "coordinate",  # route, coordinate, collaborate
        enable_memory: bool = True,
        enable_knowledge: bool = True
    ):
        self.team_name = team_name
        self.team_role = team_role
        self.team_mode = team_mode
        self.enable_memory = enable_memory
        self.enable_knowledge = enable_knowledge
        
        # Team components
        self.team: Optional[Team] = None
        self.team_members: List[Union[Agent, Team]] = []
        self.team_leader: Optional[Agent] = None
        
        # Team metrics
        self.team_metrics = {
            "total_requests": 0,
            "successful_collaborations": 0,
            "average_response_time": 0.0,
            "member_utilization": {},
            "team_mode_distribution": {
                "route": 0,
                "coordinate": 0,
                "collaborate": 0
            }
        }
        
        # Configuration
        self.is_initialized = False
        
        logger.info(f"🚀 Initializing Agno Team: {team_name} in {team_mode} mode")
    
    def _create_team_leader_model(self) -> Union[OpenAIChat, Claude]:
        """Create optimized model for team leader"""
        # Use reasoning model for team coordination
        model_name = settings.reasoning_model
        
        if "claude" in model_name.lower() and settings.anthropic_api_key:
            return Claude(
                id=model_name,
                api_key=settings.anthropic_api_key
            )
        else:
            return OpenAIChat(
                id=model_name or settings.default_model,
                api_key=settings.openai_api_key,
                max_tokens=settings.max_tokens,
                temperature=0.3  # Lower temperature for coordination
            )
    
    def _create_member_model(self) -> OpenAIChat:
        """Create model for team members"""
        return OpenAIChat(
            id=settings.default_model,
            api_key=settings.openai_api_key,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature
        )
    
    async def create_team_leader(self, leader_instructions: str) -> Agent:
        """Create intelligent team leader with coordination capabilities"""
        model = self._create_team_leader_model()
        
        # Enhanced team leader instructions
        enhanced_instructions = f"""
        You are the Team Leader for {self.team_name}.
        Team Role: {self.team_role}
        Team Mode: {self.team_mode}
        
        {leader_instructions}
        
        Team Coordination Guidelines:
        - Route Mode: Direct requests to the most appropriate team member
        - Coordinate Mode: Orchestrate multiple members and synthesize responses
        - Collaborate Mode: Facilitate collective problem-solving
        
        Your coordination responsibilities:
        1. Analyze incoming requests and determine optimal team response strategy
        2. Select appropriate team members based on their expertise
        3. Coordinate member interactions and information flow
        4. Synthesize member outputs into coherent team responses
        5. Ensure team efficiency and quality standards
        
        Always provide clear reasoning for team coordination decisions.
        """
        
        # Initialize storage if available
        storage = None
        if settings.database_url:
            try:
                storage = PostgresStorage(
                    connection_string=settings.database_url,
                    table_name=f"{self.team_name.lower()}_leader_storage"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize storage for team leader: {e}")
        
        self.team_leader = Agent(
            name=f"{self.team_name}_Leader",
            model=model,
            instructions=enhanced_instructions,
            tools=[ReasoningTools(add_instructions=True)],
            storage=storage,
            markdown=True,
            debug_mode=settings.log_level == "DEBUG",
            monitoring=settings.agno_monitoring_enabled
        )
        
        logger.info(f"✅ Team leader created for {self.team_name}")
        return self.team_leader
    
    def add_team_member(
        self,
        member: Union[Agent, Team, UberEatsBaseAgent],
        member_name: str,
        member_role: str
    ) -> bool:
        """Add member to the team"""
        try:
            # If it's a UberEatsBaseAgent, convert to standard Agent format
            if isinstance(member, UberEatsBaseAgent):
                # Create a new Agent instance with the enhanced agent's configuration
                enhanced_member = Agent(
                    name=member_name,
                    model=member.model,
                    instructions=member.instructions,
                    tools=member.tools,
                    storage=member.storage,
                    memory=member.memory,
                    markdown=True,
                    debug_mode=settings.log_level == "DEBUG",
                    monitoring=settings.agno_monitoring_enabled
                )
                self.team_members.append(enhanced_member)
            else:
                # Standard Agent or Team
                if hasattr(member, 'name'):
                    member.name = member_name
                if hasattr(member, 'role') and not hasattr(member, 'instructions'):
                    member.role = member_role
                
                self.team_members.append(member)
            
            # Initialize utilization tracking
            self.team_metrics["member_utilization"][member_name] = 0
            
            logger.info(f"✅ Added team member: {member_name} to {self.team_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add team member {member_name}: {e}")
            return False
    
    def create_specialized_agent(
        self,
        agent_name: str,
        agent_role: str,
        agent_instructions: str,
        specialized_tools: List = None
    ) -> Agent:
        """Create a specialized agent for the team"""
        model = self._create_member_model()
        
        tools = []
        if specialized_tools:
            tools.extend(specialized_tools)
        
        # Add reasoning capabilities for complex agents
        if "complex" in agent_role.lower() or "analysis" in agent_role.lower():
            tools.append(ReasoningTools(add_instructions=True))
        
        agent = Agent(
            name=agent_name,
            role=agent_role,
            model=model,
            instructions=agent_instructions,
            tools=tools,
            markdown=True,
            debug_mode=settings.log_level == "DEBUG",
            monitoring=settings.agno_monitoring_enabled
        )
        
        return agent
    
    async def initialize_team(self) -> bool:
        """Initialize the Agno Team with all members"""
        try:
            if not self.team_leader:
                raise ValueError("Team leader must be created before initializing team")
            
            if not self.team_members:
                raise ValueError("Team must have at least one member")
            
            # Create the native Agno Team
            self.team = Team(
                name=self.team_name,
                role=self.team_role,
                members=self.team_members,
                # Add team-specific configuration
                **self._get_team_config()
            )
            
            self.is_initialized = True
            
            logger.info(f"✅ Team {self.team_name} initialized successfully with {len(self.team_members)} members")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize team {self.team_name}: {e}")
            return False
    
    def _get_team_config(self) -> Dict[str, Any]:
        """Get team-specific configuration"""
        config = {}
        
        # Add memory configuration if enabled
        if self.enable_memory:
            config["memory"] = True
        
        # Add knowledge configuration if enabled
        if self.enable_knowledge:
            config["knowledge"] = True
        
        return config
    
    async def process_request(
        self,
        request: Dict[str, Any],
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process request using the Agno Team"""
        if not self.is_initialized:
            raise ValueError(f"Team {self.team_name} not initialized")
        
        start_time = datetime.now()
        request_mode = mode or self.team_mode
        session_id = request.get("session_id", f"session_{int(start_time.timestamp())}")
        
        try:
            logger.info(f"Processing request in {request_mode} mode for team {self.team_name}")
            
            # Use native Agno Team processing
            if isinstance(request, dict) and "message" in request:
                message = request["message"]
            else:
                message = str(request)
            
            # Process with the team
            response = await self.team.arun(message)
            
            # Calculate metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_team_metrics(processing_time, request_mode, True)
            
            result = {
                "session_id": session_id,
                "team_name": self.team_name,
                "team_mode": request_mode,
                "response": response,
                "processing_time": processing_time,
                "members_count": len(self.team_members),
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Request processed successfully by team {self.team_name} in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_team_metrics(processing_time, request_mode, False)
            
            error_msg = f"Error in team {self.team_name} processing: {e}"
            logger.error(error_msg, exc_info=True)
            
            return {
                "session_id": session_id,
                "team_name": self.team_name,
                "team_mode": request_mode,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": processing_time,
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
    
    def _update_team_metrics(
        self,
        processing_time: float,
        mode: str,
        success: bool
    ):
        """Update team performance metrics"""
        self.team_metrics["total_requests"] += 1
        
        if success:
            self.team_metrics["successful_collaborations"] += 1
            
            # Update average response time
            total_requests = self.team_metrics["total_requests"]
            current_avg = self.team_metrics["average_response_time"]
            self.team_metrics["average_response_time"] = (
                (current_avg * (total_requests - 1) + processing_time) / total_requests
            )
        
        # Update mode distribution
        if mode in self.team_metrics["team_mode_distribution"]:
            self.team_metrics["team_mode_distribution"][mode] += 1
    
    async def get_team_status(self) -> Dict[str, Any]:
        """Get comprehensive team status"""
        status = {
            "team_name": self.team_name,
            "team_role": self.team_role,
            "team_mode": self.team_mode,
            "is_initialized": self.is_initialized,
            "members_count": len(self.team_members),
            "has_leader": self.team_leader is not None,
            "team_metrics": self.team_metrics,
            "health_score": self._calculate_health_score(),
            "configuration": {
                "memory_enabled": self.enable_memory,
                "knowledge_enabled": self.enable_knowledge,
                "reasoning_enabled": True
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Add member details
        status["members"] = []
        for i, member in enumerate(self.team_members):
            member_info = {
                "index": i,
                "name": getattr(member, 'name', f'member_{i}'),
                "type": type(member).__name__,
                "role": getattr(member, 'role', 'unknown')
            }
            status["members"].append(member_info)
        
        return status
    
    def _calculate_health_score(self) -> float:
        """Calculate team health score (0.0 to 1.0)"""
        if self.team_metrics["total_requests"] == 0:
            return 1.0
        
        success_rate = (
            self.team_metrics["successful_collaborations"] / 
            self.team_metrics["total_requests"]
        )
        
        # Factor in response time (assume 30s is slow)
        avg_time = self.team_metrics["average_response_time"]
        time_score = max(0, min(1, (30 - avg_time) / 30))
        
        # Combine metrics
        return (success_rate * 0.8) + (time_score * 0.2)
    
    async def reset_team_metrics(self):
        """Reset team performance metrics"""
        self.team_metrics = {
            "total_requests": 0,
            "successful_collaborations": 0,
            "average_response_time": 0.0,
            "member_utilization": {name: 0 for name in self.team_metrics["member_utilization"]},
            "team_mode_distribution": {
                "route": 0,
                "coordinate": 0,
                "collaborate": 0
            }
        }
        
        logger.info(f"Team metrics reset for {self.team_name}")
    
    def __repr__(self):
        return f"AgnoTeamBase(name='{self.team_name}', mode='{self.team_mode}', members={len(self.team_members)})"