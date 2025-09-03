# src/orchestration/agent_teams.py - Agno Level 4 Implementation
from agno.agent import Agent
from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime
from ..config.settings import settings
# Removed CustomerAgent - not needed for delivery optimization
from ..agents.base_agent import UberEatsBaseAgent

logger = logging.getLogger(__name__)

class UberEatsAgentTeam:
    """Level 4 Agent Team with reasoning and collaboration capabilities"""
    
    def __init__(self):
        self.team_lead = None
        self.specialized_agents = {}
        self.collaboration_context = {}
        self.active_sessions = {}
        self.team_metrics = {
            "total_requests": 0,
            "successful_collaborations": 0,
            "average_response_time": 0.0,
            "agent_utilization": {}
        }
        
        # Initialize the team
        asyncio.create_task(self._initialize_team())
        
    async def _initialize_team(self):
        """Initialize the agent team with orchestrator and specialized agents"""
        try:
            await self._create_orchestrator_agent()
            await self._create_specialized_agents()
            logger.info("UberEats Agent Team initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent team: {e}")
            raise
    
    async def _create_orchestrator_agent(self):
        """Create the main orchestrator agent with full reasoning capabilities"""
        
        try:
            # Select the best model for orchestration (Claude for reasoning)
            model = Claude(
                id=settings.reasoning_model, 
                api_key=settings.anthropic_api_key
            ) if settings.anthropic_api_key else OpenAIChat(
                model=settings.default_model,
                api_key=settings.openai_api_key
            )
            
            # Initialize storage for orchestrator
            storage = None
            if settings.database_url:
                storage = PostgresStorage(
                    connection_string=settings.database_url,
                    table_name="orchestrator_storage"
                )
            
            self.team_lead = Agent(
                name="UberEats_Orchestrator",
                model=model,
                tools=[ReasoningTools(add_instructions=True)],
                instructions="""
                You are the UberEats Multi-Agent System Orchestrator with advanced reasoning capabilities.
                
                Your core responsibilities:
                1. **Request Analysis**: Analyze incoming requests and determine optimal agent involvement
                2. **Agent Coordination**: Route tasks to appropriate specialized agents and coordinate their collaboration
                3. **Context Synthesis**: Combine responses from multiple agents into coherent, comprehensive solutions
                4. **Quality Assurance**: Ensure responses meet UberEats quality standards and customer expectations
                5. **Performance Optimization**: Monitor and optimize agent team performance and resource allocation
                
                Available Specialized Agents:
                - CustomerAgent: Customer service, policies, refunds, complaints, recommendations
                - RestaurantAgent: Menu management, preparation times, kitchen operations, availability
                - DeliveryAgent: Route optimization, driver coordination, logistics, delivery tracking
                - OrderAgent: Order processing, payment handling, status management, validation
                - AnalyticsAgent: Data insights, recommendations, performance analytics, reporting
                
                Advanced Capabilities:
                - Use structured reasoning for complex multi-step problems
                - Maintain context across agent interactions
                - Adapt coordination strategy based on request complexity and urgency
                - Provide clear, actionable responses with supporting reasoning
                - Handle edge cases and error scenarios gracefully
                
                Always coordinate effectively with specialized agents and provide comprehensive solutions.
                """,
                memory=AgentMemory(db_file="orchestrator_memory.db", create_table=True),
                storage=storage,
                markdown=True,
                debug_mode=settings.log_level == "DEBUG",
                monitoring=settings.agno_monitoring_enabled
            )
            
            logger.info("Orchestrator agent created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create orchestrator agent: {e}")
            raise
    
    async def _create_specialized_agents(self):
        """Create specialized agents with domain expertise"""
        
        try:
            # Customer Service Agent
            self.specialized_agents['customer'] = CustomerAgent(
                model=OpenAIChat(model=settings.default_model, api_key=settings.openai_api_key)
            )
            
            # Restaurant Operations Agent
            self.specialized_agents['restaurant'] = UberEatsBaseAgent(
                agent_id="restaurant_agent",
                instructions="""
                You are a restaurant operations expert for UberEats with advanced reasoning capabilities.
                
                Your expertise includes:
                - Menu management and item availability optimization
                - Kitchen workflow and preparation time estimation
                - Food quality standards and compliance monitoring
                - Peak hour management and capacity planning
                - Integration with delivery logistics for end-to-end optimization
                
                Use data-driven reasoning for accurate estimates and recommendations.
                Collaborate with delivery agents for optimal customer experience.
                """,
                model_name=settings.default_model,
                enable_reasoning=True,
                enable_memory=True
            )
            
            # Delivery Logistics Agent
            self.specialized_agents['delivery'] = UberEatsBaseAgent(
                agent_id="delivery_agent",
                instructions="""
                You are a delivery logistics optimization expert with advanced reasoning capabilities.
                
                Your specializations:
                - Route optimization and traffic analysis
                - Driver allocation and workload balancing
                - Real-time delivery tracking and ETA prediction
                - Weather and external factor impact assessment
                - Cost-efficient logistics planning
                
                Use advanced reasoning for complex logistics challenges and multi-variable optimization.
                Coordinate with restaurant agents for seamless order-to-delivery flow.
                """,
                model_name=settings.reasoning_model if settings.anthropic_api_key else settings.default_model,
                enable_reasoning=True,
                enable_memory=True
            )
            
            # Order Processing Agent
            self.specialized_agents['order'] = UberEatsBaseAgent(
                agent_id="order_agent",
                instructions="""
                You are an order processing specialist with comprehensive system knowledge.
                
                Your responsibilities:
                - Order validation and fraud detection
                - Payment processing and billing coordination
                - Order status tracking and customer communication
                - Inventory coordination with restaurants
                - Exception handling and error resolution
                
                Ensure order accuracy and smooth processing workflow.
                Coordinate with all other agents for comprehensive order management.
                """,
                model_name=settings.default_model,
                enable_reasoning=True,
                enable_memory=True
            )
            
            # Analytics and Insights Agent
            self.specialized_agents['analytics'] = UberEatsBaseAgent(
                agent_id="analytics_agent",
                instructions="""
                You are a data analytics expert providing insights and recommendations.
                
                Your analytical capabilities:
                - Performance metrics analysis and reporting
                - Customer behavior pattern recognition
                - Operational efficiency optimization recommendations
                - Predictive analytics for demand forecasting
                - Data-driven decision support for all business areas
                
                Provide actionable insights with clear reasoning and supporting data.
                Support other agents with analytical recommendations and trend analysis.
                """,
                model_name=settings.reasoning_model if settings.anthropic_api_key else settings.default_model,
                enable_reasoning=True,
                enable_memory=True
            )
            
            logger.info(f"Created {len(self.specialized_agents)} specialized agents")
            
        except Exception as e:
            logger.error(f"Failed to create specialized agents: {e}")
            raise
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through intelligent agent team collaboration"""
        
        session_id = request.get("session_id", f"session_{datetime.now().timestamp()}")
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing request for session {session_id}")
            
            # Step 1: Orchestrator analyzes the request and creates collaboration plan
            orchestration_prompt = f"""
            Analyze this UberEats request and create an optimal agent collaboration strategy:
            
            Request Details: {request}
            Session ID: {session_id}
            
            Please analyze and provide:
            1. Request complexity assessment (1-10 scale)
            2. Urgency level (low/medium/high/critical)
            3. Required specialized agents (from: customer, restaurant, delivery, order, analytics)
            4. Optimal collaboration sequence (parallel vs sequential processing)
            5. Expected processing time and resource requirements
            6. Quality checkpoints and success criteria
            7. Risk factors and mitigation strategies
            
            Provide a structured collaboration plan for the agent team.
            """
            
            orchestration_response = await self.team_lead.arun(orchestration_prompt)
            
            # Step 2: Determine agent involvement based on orchestration plan
            involved_agents = await self._determine_agent_involvement(request, orchestration_response)
            
            # Step 3: Execute collaborative agent processing
            agent_results = await self._execute_collaborative_processing(
                request, involved_agents, orchestration_response, session_id
            )
            
            # Step 4: Orchestrator synthesizes final response
            synthesis_prompt = f"""
            Synthesize the responses from specialized agents into a comprehensive solution:
            
            Original Request: {request}
            Orchestration Plan: {orchestration_response}
            Agent Results: {agent_results}
            Session ID: {session_id}
            
            Create a unified, high-quality response that:
            1. Addresses all aspects of the original request
            2. Integrates insights from all involved agents
            3. Provides clear, actionable recommendations
            4. Maintains consistency and coherence
            5. Includes relevant follow-up suggestions
            
            Ensure the response meets UberEats quality standards and customer expectations.
            """
            
            final_response = await self.team_lead.arun(synthesis_prompt)
            
            # Calculate processing metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_team_metrics(processing_time, len(involved_agents), True)
            
            result = {
                "session_id": session_id,
                "final_response": final_response,
                "orchestration_plan": orchestration_response,
                "involved_agents": involved_agents,
                "agent_contributions": agent_results,
                "processing_time": processing_time,
                "collaboration_type": "agent_team_level_4",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully processed request {session_id} in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_team_metrics(processing_time, 0, False)
            
            error_msg = f"Error in agent team processing for session {session_id}: {e}"
            logger.error(error_msg, exc_info=True)
            
            return {
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": processing_time,
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _determine_agent_involvement(self, request: Dict[str, Any], orchestration_plan: str) -> List[str]:
        """Intelligently determine which agents should be involved"""
        
        request_text = str(request).lower()
        involved_agents = []
        
        # Primary involvement based on keywords
        keyword_mapping = {
            'customer': ['complaint', 'refund', 'support', 'help', 'policy', 'cancel', 'service'],
            'restaurant': ['menu', 'restaurant', 'preparation', 'kitchen', 'cooking', 'availability', 'food'],
            'delivery': ['delivery', 'driver', 'route', 'logistics', 'tracking', 'eta', 'location'],
            'order': ['order', 'payment', 'checkout', 'process', 'status', 'billing', 'receipt'],
            'analytics': ['analytics', 'report', 'insight', 'trend', 'recommend', 'optimize', 'performance']
        }
        
        # Check for keyword matches
        for agent_type, keywords in keyword_mapping.items():
            if any(keyword in request_text for keyword in keywords):
                involved_agents.append(agent_type)
        
        # Secondary involvement based on orchestration plan analysis
        if "high complexity" in orchestration_plan.lower() or "critical" in orchestration_plan.lower():
            # Include analytics for complex requests
            if 'analytics' not in involved_agents:
                involved_agents.append('analytics')
        
        # Ensure customer agent is included for any customer-facing request
        if not involved_agents or any(term in request_text for term in ['customer', 'user', 'help', 'issue']):
            if 'customer' not in involved_agents:
                involved_agents.append('customer')
        
        # Default fallback
        if not involved_agents:
            involved_agents = ['customer']
        
        logger.info(f"Determined agent involvement: {involved_agents}")
        return involved_agents
    
    async def _execute_collaborative_processing(
        self, 
        request: Dict[str, Any],
        involved_agents: List[str],
        orchestration_plan: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Execute collaborative processing with involved agents"""
        
        agent_results = {}
        
        # Determine if agents should work in parallel or sequence
        parallel_processing = len(involved_agents) <= 3 and "sequential" not in orchestration_plan.lower()
        
        if parallel_processing:
            # Execute agents in parallel for faster processing
            tasks = []
            for agent_name in involved_agents:
                if agent_name in self.specialized_agents:
                    task = self._process_with_agent(
                        agent_name, request, agent_results, orchestration_plan, session_id
                    )
                    tasks.append(task)
            
            # Wait for all agents to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                agent_name = involved_agents[i]
                if isinstance(result, Exception):
                    logger.error(f"Agent {agent_name} failed: {result}")
                    agent_results[agent_name] = {"error": str(result), "success": False}
                else:
                    agent_results[agent_name] = result
        else:
            # Execute agents sequentially for complex workflows
            for agent_name in involved_agents:
                if agent_name in self.specialized_agents:
                    try:
                        result = await self._process_with_agent(
                            agent_name, request, agent_results, orchestration_plan, session_id
                        )
                        agent_results[agent_name] = result
                        logger.info(f"Agent {agent_name} completed processing for session {session_id}")
                    except Exception as e:
                        logger.error(f"Agent {agent_name} failed: {e}")
                        agent_results[agent_name] = {"error": str(e), "success": False}
        
        return agent_results
    
    async def _process_with_agent(
        self,
        agent_name: str,
        request: Dict[str, Any],
        previous_results: Dict[str, Any],
        orchestration_plan: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Process request with a specific agent including context from other agents"""
        
        agent = self.specialized_agents[agent_name]
        
        # Prepare context-aware prompt for the agent
        context_prompt = f"""
        Original Request: {request}
        Session ID: {session_id}
        Orchestration Plan: {orchestration_plan}
        Previous Agent Results: {previous_results}
        
        As the {agent_name} agent, provide your specialized contribution to address this request.
        Consider the context from other agents and focus on your domain expertise.
        Ensure your response complements and integrates with other agent contributions.
        
        Your specific task: {request.get('message', request)}
        """
        
        # Process with the specialized agent
        if hasattr(agent, 'process_request_with_metrics'):
            # Use enhanced base agent processing
            result = await agent.process_request_with_metrics({"message": context_prompt})
        else:
            # Fallback to basic processing
            response = await agent.arun(context_prompt)
            result = {
                "response": response,
                "agent_name": agent_name,
                "success": True
            }
        
        # Update agent utilization metrics
        self.team_metrics["agent_utilization"][agent_name] = (
            self.team_metrics["agent_utilization"].get(agent_name, 0) + 1
        )
        
        return result
    
    def _update_team_metrics(self, processing_time: float, agents_involved: int, success: bool):
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
    
    async def get_team_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the entire agent team"""
        
        team_status = {
            "orchestrator": {
                "status": "healthy",
                "agent_type": "orchestrator",
                "model": self.team_lead.model.__class__.__name__ if self.team_lead else "not_initialized",
                "capabilities": {
                    "memory_enabled": hasattr(self.team_lead, 'memory') and self.team_lead.memory is not None,
                    "storage_enabled": hasattr(self.team_lead, 'storage') and self.team_lead.storage is not None,
                    "reasoning_enabled": True
                }
            } if self.team_lead else {"status": "not_initialized"},
            "specialized_agents": {}
        }
        
        # Get health status from each specialized agent
        for agent_name, agent in self.specialized_agents.items():
            if hasattr(agent, 'get_health_status'):
                agent_health = await asyncio.create_task(
                    asyncio.coroutine(agent.get_health_status)()
                ) if asyncio.iscoroutinefunction(agent.get_health_status) else agent.get_health_status()
                team_status["specialized_agents"][agent_name] = agent_health
            else:
                team_status["specialized_agents"][agent_name] = {
                    "status": "healthy",
                    "agent_type": agent_name,
                    "model": agent.model.__class__.__name__ if hasattr(agent, 'model') else "unknown"
                }
        
        # Add team-level metrics
        team_status["team_metrics"] = self.team_metrics
        team_status["team_health_score"] = self._calculate_team_health_score()
        team_status["timestamp"] = datetime.now().isoformat()
        
        return team_status
    
    def _calculate_team_health_score(self) -> float:
        """Calculate overall team health score (0.0 to 1.0)"""
        
        total_requests = self.team_metrics["total_requests"]
        if total_requests == 0:
            return 1.0
        
        success_rate = self.team_metrics["successful_collaborations"] / total_requests
        avg_response_time = self.team_metrics["average_response_time"]
        
        # Health score based on success rate and response time
        time_score = max(0, min(1, (30 - avg_response_time) / 30))  # 30s is considered slow
        
        return (success_rate * 0.7) + (time_score * 0.3)
    
    async def reset_team_metrics(self):
        """Reset team performance metrics"""
        
        self.team_metrics = {
            "total_requests": 0,
            "successful_collaborations": 0,
            "average_response_time": 0.0,
            "agent_utilization": {}
        }
        
        # Reset individual agent metrics
        for agent in self.specialized_agents.values():
            if hasattr(agent, 'reset_metrics'):
                await agent.reset_metrics()
        
        logger.info("Team metrics reset successfully")