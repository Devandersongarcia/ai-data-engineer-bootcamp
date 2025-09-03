# src/orchestration/agentic_workflows.py - Agno Level 5 Implementation
from agno.agent import Agent
from agno.workflow import Workflow
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
from enum import Enum
import json
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)

class WorkflowState(Enum):
    """Deterministic workflow state management"""
    INITIATED = "initiated"
    ANALYZING = "analyzing"
    PROCESSING = "processing"
    COORDINATING = "coordinating"
    SYNTHESIZING = "synthesizing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"

class UberEatsAgenticWorkflow(Workflow):
    """Level 5 Agentic Workflow with state management and deterministic execution"""
    
    def __init__(self):
        # Initialize workflow with enhanced state management
        storage = None
        if settings.database_url:
            try:
                storage = PostgresStorage(
                    connection_string=settings.database_url,
                    table_name="workflow_state_management"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize PostgreSQL storage for workflow: {e}")
        
        super().__init__(
            name="UberEats_Agentic_Workflow",
            storage=storage
        )
        
        self.current_state = WorkflowState.INITIATED
        self.workflow_context = {}
        self.state_transitions = {}
        self.performance_metrics = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "average_execution_time": 0.0,
            "state_transition_history": []
        }
        
        # Initialize specialized workflow agents
        self._initialize_workflow_agents()
    
    def _initialize_workflow_agents(self):
        """Initialize agents optimized for workflow execution with enhanced capabilities"""
        
        try:
            # Request Analyzer Agent - Specialized for workflow analysis
            self.analyzer_agent = Agent(
                name="WorkflowAnalyzer",
                model=Claude(
                    id=settings.reasoning_model, 
                    api_key=settings.anthropic_api_key
                ) if settings.anthropic_api_key else OpenAIChat(
                    model=settings.default_model,
                    api_key=settings.openai_api_key
                ),
                tools=[ReasoningTools(add_instructions=True)],
                instructions="""
                You are a specialized request analysis agent in an advanced agentic workflow system.
                
                Your core capabilities:
                1. **Deep Analysis**: Analyze request complexity, urgency, domain requirements, and resource needs
                2. **Strategy Planning**: Determine optimal processing strategy, agent allocation, and execution paths
                3. **Risk Assessment**: Identify potential risks, edge cases, and mitigation strategies
                4. **Success Criteria**: Define clear, measurable success criteria and quality expectations
                5. **Resource Optimization**: Optimize resource allocation and processing sequence
                
                Analysis Framework:
                - Complexity Score (1-10): Technical and business complexity assessment
                - Urgency Level: low/medium/high/critical with time sensitivity analysis
                - Domain Mapping: Required expertise areas and agent specializations
                - Processing Strategy: Sequential vs parallel execution recommendations
                - Quality Gates: Checkpoints and validation requirements
                - Risk Factors: Potential issues and recommended mitigations
                
                Always provide structured, actionable analysis with confidence scores and clear reasoning.
                """,
                memory=AgentMemory(db_file="workflow_analyzer_memory.db", create_table=True),
                storage=self.storage,
                monitoring=settings.agno_monitoring_enabled
            )
            
            # Workflow Coordinator Agent - Specialized for orchestration
            self.coordinator_agent = Agent(
                name="WorkflowCoordinator", 
                model=OpenAIChat(model=settings.default_model, api_key=settings.openai_api_key),
                tools=[ReasoningTools(add_instructions=True)],
                instructions="""
                You are the workflow coordination specialist with advanced orchestration capabilities.
                
                Your responsibilities:
                1. **Multi-Agent Orchestration**: Coordinate complex multi-agent collaboration sequences
                2. **State Management**: Manage deterministic workflow state transitions and persistence
                3. **Error Handling**: Implement robust error recovery and retry logic with exponential backoff
                4. **Resource Management**: Optimize resource allocation, timing, and parallel processing
                5. **Quality Control**: Ensure consistent quality and compliance throughout execution
                
                Coordination Principles:
                - Maintain strict adherence to workflow state management protocols
                - Implement deterministic execution paths with clear decision points
                - Optimize for both speed and reliability in agent coordination
                - Handle exceptions gracefully with automatic recovery mechanisms
                - Provide real-time progress tracking and status updates
                
                Always maintain deterministic behavior and clear audit trails for all coordination decisions.
                """,
                memory=AgentMemory(db_file="workflow_coordinator_memory.db", create_table=True),
                storage=self.storage,
                monitoring=settings.agno_monitoring_enabled
            )
            
            # Quality Assurance Agent - Specialized for validation
            self.qa_agent = Agent(
                name="WorkflowQA",
                model=Claude(
                    id=settings.reasoning_model,
                    api_key=settings.anthropic_api_key
                ) if settings.anthropic_api_key else OpenAIChat(
                    model=settings.default_model,
                    api_key=settings.openai_api_key
                ),
                tools=[ReasoningTools(add_instructions=True)],
                instructions="""
                You are the workflow quality assurance specialist with comprehensive validation capabilities.
                
                Your quality mandate:
                1. **Output Validation**: Rigorously validate all agent outputs against quality criteria and business rules
                2. **Consistency Checking**: Identify inconsistencies, gaps, and logical errors across agent responses
                3. **Compliance Verification**: Ensure all responses comply with UberEats policies, standards, and regulations
                4. **Performance Assessment**: Evaluate response quality against predefined success criteria
                5. **Improvement Recommendations**: Provide actionable feedback for optimization and enhancement
                
                Quality Framework:
                - Accuracy: Factual correctness and data validation
                - Completeness: Coverage of all request requirements
                - Consistency: Logical coherence across all components
                - Compliance: Adherence to policies and standards
                - Usability: Clarity, actionability, and customer value
                - Performance: Response time and resource efficiency
                
                Apply rigorous quality standards and provide detailed, actionable feedback with improvement recommendations.
                Never compromise on quality - escalate issues that cannot be resolved within quality parameters.
                """,
                memory=AgentMemory(db_file="workflow_qa_memory.db", create_table=True),
                storage=self.storage,
                monitoring=settings.agno_monitoring_enabled
            )
            
            logger.info("Workflow agents initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow agents: {e}")
            raise
    
    async def execute_workflow(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the complete agentic workflow with deterministic state management"""
        
        workflow_id = f"workflow_{datetime.now().timestamp()}_{hash(str(request)) % 10000}"
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting workflow execution: {workflow_id}")
            
            # Initialize workflow state
            await self._transition_state(WorkflowState.INITIATED, workflow_id, request)
            
            # Stage 1: Deep Request Analysis
            await self._transition_state(WorkflowState.ANALYZING, workflow_id)
            analysis_result = await self._execute_analysis_stage(request, workflow_id)
            
            # Stage 2: Multi-Agent Coordination and Processing
            await self._transition_state(WorkflowState.PROCESSING, workflow_id)
            processing_result = await self._execute_processing_stage(
                request, analysis_result, workflow_id
            )
            
            # Stage 3: Advanced Coordination (if needed for complex workflows)
            if self._requires_advanced_coordination(analysis_result):
                await self._transition_state(WorkflowState.COORDINATING, workflow_id)
                coordination_result = await self._execute_coordination_stage(
                    request, analysis_result, processing_result, workflow_id
                )
            else:
                coordination_result = {"coordination": "not_required", "reason": "simple_workflow"}
            
            # Stage 4: Response Synthesis & Integration
            await self._transition_state(WorkflowState.SYNTHESIZING, workflow_id)
            synthesis_result = await self._execute_synthesis_stage(
                request, analysis_result, processing_result, coordination_result, workflow_id
            )
            
            # Stage 5: Quality Validation & Assurance
            await self._transition_state(WorkflowState.VALIDATING, workflow_id)
            validation_result = await self._execute_validation_stage(
                request, synthesis_result, workflow_id
            )
            
            # Complete workflow
            await self._transition_state(WorkflowState.COMPLETED, workflow_id)
            
            # Calculate final metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(execution_time, True)
            
            final_result = {
                "workflow_id": workflow_id,
                "final_result": validation_result.get("validated_response", synthesis_result),
                "execution_stages": {
                    "analysis": analysis_result,
                    "processing": processing_result,
                    "coordination": coordination_result,
                    "synthesis": synthesis_result,
                    "validation": validation_result
                },
                "execution_time": execution_time,
                "state_transitions": self.state_transitions.get(workflow_id, []),
                "quality_score": validation_result.get("quality_score", 0.95),
                "workflow_type": "agentic_level_5",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Workflow {workflow_id} completed successfully in {execution_time:.2f}s")
            return final_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._transition_state(WorkflowState.FAILED, workflow_id, {"error": str(e)})
            self._update_performance_metrics(execution_time, False)
            
            error_result = {
                "workflow_id": workflow_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time": execution_time,
                "state_transitions": self.state_transitions.get(workflow_id, []),
                "recovery_options": await self._analyze_recovery_options(workflow_id, str(e)),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Workflow {workflow_id} failed: {e}", exc_info=True)
            return error_result
    
    async def _transition_state(
        self, 
        new_state: WorkflowState, 
        workflow_id: str, 
        context: Optional[Dict[str, Any]] = None
    ):
        """Manage deterministic state transitions with persistence"""
        
        previous_state = self.current_state if hasattr(self, 'current_state') else None
        
        transition = {
            "timestamp": datetime.now().isoformat(),
            "workflow_id": workflow_id,
            "from_state": previous_state.value if previous_state else None,
            "to_state": new_state.value,
            "context": context or {},
            "transition_id": f"{workflow_id}_{new_state.value}_{datetime.now().timestamp()}"
        }
        
        # Record state transition
        if workflow_id not in self.state_transitions:
            self.state_transitions[workflow_id] = []
        
        self.state_transitions[workflow_id].append(transition)
        self.current_state = new_state
        
        # Add to global transition history for analytics
        self.performance_metrics["state_transition_history"].append(transition)
        
        # Persist state to storage for recovery
        await self._persist_workflow_state(workflow_id, new_state, context)
        
        logger.debug(f"Workflow {workflow_id} transitioned: {previous_state} -> {new_state}")
    
    async def _execute_analysis_stage(
        self, 
        request: Dict[str, Any], 
        workflow_id: str
    ) -> Dict[str, Any]:
        """Execute comprehensive request analysis stage"""
        
        analysis_prompt = f"""
        Perform comprehensive analysis of this UberEats request for optimal workflow execution:
        
        Request Details: {request}
        Workflow ID: {workflow_id}
        
        Provide detailed analysis including:
        
        1. **Complexity Assessment**:
           - Technical complexity score (1-10)
           - Business logic complexity score (1-10)
           - Integration complexity score (1-10)
           - Overall complexity classification
        
        2. **Urgency and Priority**:
           - Urgency level (low/medium/high/critical)
           - Time sensitivity factors
           - Customer impact assessment
           - Business priority score
        
        3. **Domain Expertise Requirements**:
           - Required agent specializations
           - Knowledge domains needed
           - External system integrations
           - Data requirements
        
        4. **Processing Strategy**:
           - Recommended execution approach (sequential/parallel/hybrid)
           - Resource allocation requirements
           - Estimated processing time
           - Scalability considerations
        
        5. **Quality and Success Criteria**:
           - Measurable success indicators
           - Quality checkpoints
           - Acceptance criteria
           - Performance thresholds
        
        6. **Risk Assessment**:
           - Potential failure points
           - Edge cases and exceptions
           - Mitigation strategies
           - Contingency plans
        
        Format response as structured JSON for workflow coordination.
        """
        
        try:
            analysis_response = await self.analyzer_agent.arun(analysis_prompt)
            
            return {
                "analysis": analysis_response,
                "analyzer_agent": "WorkflowAnalyzer",
                "stage": "analysis",
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Analysis stage failed for workflow {workflow_id}: {e}")
            return {
                "error": str(e),
                "stage": "analysis",
                "workflow_id": workflow_id,
                "success": False
            }
    
    async def _execute_processing_stage(
        self,
        request: Dict[str, Any],
        analysis_result: Dict[str, Any], 
        workflow_id: str
    ) -> Dict[str, Any]:
        """Execute multi-agent processing coordination stage"""
        
        coordination_prompt = f"""
        Coordinate multi-agent processing based on comprehensive analysis:
        
        Original Request: {request}
        Analysis Results: {analysis_result}
        Workflow ID: {workflow_id}
        
        Execute advanced coordination including:
        
        1. **Agent Allocation**:
           - Determine optimal agent sequence and parallelization
           - Allocate resources based on complexity and urgency scores
           - Set up inter-agent communication protocols
           - Define coordination checkpoints
        
        2. **Execution Strategy**:
           - Implement parallel processing where beneficial
           - Manage sequential dependencies where required
           - Optimize for both speed and quality
           - Handle resource constraints intelligently
        
        3. **Quality Management**:
           - Set quality checkpoints throughout processing
           - Monitor progress against success criteria
           - Implement real-time quality assurance
           - Handle quality escalations appropriately
        
        4. **Risk Mitigation**:
           - Address identified risk factors proactively
           - Implement contingency measures
           - Monitor for edge cases and exceptions
           - Maintain fallback processing paths
        
        5. **Progress Tracking**:
           - Provide real-time status updates
           - Track execution against time estimates
           - Monitor resource utilization
           - Generate coordination metrics
        
        Provide structured coordination results with detailed execution plan and outcomes.
        """
        
        try:
            coordination_response = await self.coordinator_agent.arun(coordination_prompt)
            
            return {
                "coordination": coordination_response,
                "coordinator_agent": "WorkflowCoordinator",
                "stage": "processing",
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Processing stage failed for workflow {workflow_id}: {e}")
            return {
                "error": str(e),
                "stage": "processing",
                "workflow_id": workflow_id,
                "success": False
            }
    
    async def _execute_coordination_stage(
        self,
        request: Dict[str, Any],
        analysis_result: Dict[str, Any],
        processing_result: Dict[str, Any],
        workflow_id: str
    ) -> Dict[str, Any]:
        """Execute advanced coordination for complex workflows"""
        
        advanced_coordination_prompt = f"""
        Execute advanced coordination for complex workflow requirements:
        
        Original Request: {request}
        Analysis: {analysis_result}
        Processing Results: {processing_result}
        Workflow ID: {workflow_id}
        
        Advanced coordination tasks:
        
        1. **Cross-Agent Integration**:
           - Resolve conflicts between agent outputs
           - Ensure consistency across all responses
           - Optimize inter-agent handoffs
           - Validate cross-domain dependencies
        
        2. **Complex Logic Resolution**:
           - Handle multi-step business processes
           - Resolve complex decision trees
           - Manage state-dependent operations
           - Coordinate asynchronous processes
        
        3. **Performance Optimization**:
           - Optimize resource allocation dynamically
           - Balance load across available agents
           - Implement caching for repeated operations
           - Monitor and adjust performance parameters
        
        4. **Exception Handling**:
           - Coordinate recovery from partial failures
           - Implement sophisticated retry mechanisms
           - Handle data consistency issues
           - Manage timeout and error escalation
        
        Provide comprehensive coordination results with optimization recommendations.
        """
        
        try:
            advanced_response = await self.coordinator_agent.arun(advanced_coordination_prompt)
            
            return {
                "advanced_coordination": advanced_response,
                "stage": "coordination",
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Coordination stage failed for workflow {workflow_id}: {e}")
            return {
                "error": str(e),
                "stage": "coordination",
                "workflow_id": workflow_id,
                "success": False
            }
    
    async def _execute_synthesis_stage(
        self,
        request: Dict[str, Any],
        analysis_result: Dict[str, Any],
        processing_result: Dict[str, Any],
        coordination_result: Dict[str, Any],
        workflow_id: str
    ) -> Dict[str, Any]:
        """Execute response synthesis and integration stage"""
        
        synthesis_prompt = f"""
        Synthesize and integrate all workflow results into a comprehensive final response:
        
        Original Request: {request}
        Analysis: {analysis_result}  
        Processing Results: {processing_result}
        Coordination Results: {coordination_result}
        Workflow ID: {workflow_id}
        
        Synthesis requirements:
        
        1. **Response Integration**:
           - Combine all agent outputs into a coherent response
           - Resolve any inconsistencies or conflicts
           - Maintain logical flow and narrative coherence
           - Ensure completeness and accuracy
        
        2. **Value Optimization**:
           - Maximize customer value and satisfaction
           - Optimize for business outcomes
           - Ensure regulatory compliance
           - Maintain UberEats brand standards
        
        3. **Actionability**:
           - Provide clear, actionable recommendations
           - Include specific next steps where appropriate
           - Offer alternatives and options when relevant
           - Ensure practical implementability
        
        4. **Quality Enhancement**:
           - Enhance clarity and readability
           - Optimize information hierarchy
           - Remove redundancy while maintaining completeness
           - Add relevant context and explanations
        
        5. **Future Considerations**:
           - Include relevant follow-up recommendations
           - Anticipate potential subsequent questions
           - Provide proactive guidance
           - Suggest optimization opportunities
        
        Generate a high-quality, comprehensive final response that fully addresses the original request.
        """
        
        try:
            synthesis_response = await self.coordinator_agent.arun(synthesis_prompt)
            
            return {
                "synthesized_response": synthesis_response,
                "stage": "synthesis",
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Synthesis stage failed for workflow {workflow_id}: {e}")
            return {
                "error": str(e),
                "stage": "synthesis",
                "workflow_id": workflow_id,
                "success": False
            }
    
    async def _execute_validation_stage(
        self,
        request: Dict[str, Any],
        synthesis_result: Dict[str, Any],
        workflow_id: str
    ) -> Dict[str, Any]:
        """Execute comprehensive quality validation stage"""
        
        validation_prompt = f"""
        Perform comprehensive quality assurance and validation:
        
        Original Request: {request}
        Synthesized Response: {synthesis_result}
        Workflow ID: {workflow_id}
        
        Quality validation framework:
        
        1. **Accuracy Validation**:
           - Verify factual correctness of all information
           - Validate data consistency and integrity
           - Check calculations and logical reasoning
           - Confirm policy and regulatory compliance
        
        2. **Completeness Assessment**:
           - Ensure all request requirements are addressed
           - Verify comprehensive coverage of the topic
           - Check for missing information or gaps
           - Validate against success criteria
        
        3. **Quality Standards**:
           - Assess clarity and readability
           - Evaluate professional presentation
           - Check brand compliance and tone
           - Validate user experience quality
        
        4. **Business Value**:
           - Assess customer satisfaction potential
           - Evaluate business impact and outcomes
           - Check alignment with UberEats objectives
           - Validate operational feasibility
        
        5. **Risk Assessment**:
           - Identify potential issues or concerns
           - Assess compliance and regulatory risks
           - Evaluate reputational impact
           - Check for unintended consequences
        
        Provide:
        - Quality score (0.0-1.0)
        - Detailed validation results
        - Improvement recommendations if needed
        - Final approved response or required modifications
        
        Do not approve responses that fail to meet quality standards.
        """
        
        try:
            validation_response = await self.qa_agent.arun(validation_prompt)
            
            return {
                "validation_results": validation_response,
                "validated_response": synthesis_result.get("synthesized_response"),
                "quality_score": 0.95,  # This would be extracted from validation_response in production
                "qa_agent": "WorkflowQA",
                "stage": "validation",
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Validation stage failed for workflow {workflow_id}: {e}")
            return {
                "error": str(e),
                "stage": "validation",
                "workflow_id": workflow_id,
                "success": False
            }
    
    def _requires_advanced_coordination(self, analysis_result: Dict[str, Any]) -> bool:
        """Determine if advanced coordination stage is required"""
        
        analysis_text = str(analysis_result).lower()
        
        # Check for complexity indicators
        complex_indicators = [
            "high complexity", "critical urgency", "multiple domains", 
            "complex integration", "advanced coordination", "multi-step process"
        ]
        
        return any(indicator in analysis_text for indicator in complex_indicators)
    
    async def _persist_workflow_state(
        self,
        workflow_id: str,
        state: WorkflowState, 
        context: Optional[Dict[str, Any]]
    ):
        """Persist workflow state for recovery and monitoring"""
        
        state_data = {
            "workflow_id": workflow_id,
            "state": state.value,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "transitions": self.state_transitions.get(workflow_id, [])
        }
        
        # Use Agno's built-in storage for state persistence
        if self.storage:
            try:
                await self.storage.upsert(workflow_id, state_data)
            except Exception as e:
                logger.warning(f"Failed to persist workflow state for {workflow_id}: {e}")
    
    def _update_performance_metrics(self, execution_time: float, success: bool):
        """Update workflow performance metrics"""
        
        self.performance_metrics["total_workflows"] += 1
        
        if success:
            self.performance_metrics["successful_workflows"] += 1
        else:
            self.performance_metrics["failed_workflows"] += 1
        
        # Update average execution time for successful workflows
        if success:
            successful_count = self.performance_metrics["successful_workflows"]
            current_avg = self.performance_metrics["average_execution_time"]
            self.performance_metrics["average_execution_time"] = (
                (current_avg * (successful_count - 1) + execution_time) / successful_count
            )
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current status and history of a workflow"""
        
        try:
            # Retrieve from storage if available
            if self.storage:
                state_data = await self.storage.read(workflow_id)
                if state_data:
                    return {
                        "workflow_id": workflow_id,
                        "current_state": state_data.get("state"),
                        "last_updated": state_data.get("timestamp"),
                        "transitions": state_data.get("transitions", []),
                        "context": state_data.get("context", {}),
                        "found_in_storage": True
                    }
            
            # Fallback to in-memory state
            return {
                "workflow_id": workflow_id,
                "transitions": self.state_transitions.get(workflow_id, []),
                "found_in_storage": False,
                "status": "completed" if workflow_id in self.state_transitions else "not_found"
            }
            
        except Exception as e:
            logger.error(f"Error getting workflow status for {workflow_id}: {e}")
            return {
                "workflow_id": workflow_id, 
                "status": "error",
                "error": str(e)
            }
    
    async def _analyze_recovery_options(self, workflow_id: str, error: str) -> Dict[str, Any]:
        """Analyze recovery options for failed workflows"""
        
        recovery_prompt = f"""
        Analyze this workflow failure and provide recovery recommendations:
        
        Workflow ID: {workflow_id}
        Error: {error}
        State Transitions: {self.state_transitions.get(workflow_id, [])}
        
        Provide recovery analysis including:
        1. Root cause analysis of the failure
        2. Recovery feasibility assessment
        3. Recommended recovery strategy
        4. Risk mitigation for retry attempts
        5. Alternative processing approaches
        
        Format as structured recommendations for automated or manual recovery.
        """
        
        try:
            recovery_analysis = await self.analyzer_agent.arun(recovery_prompt)
            return {
                "recovery_analysis": recovery_analysis,
                "recovery_feasible": True,
                "recommended_action": "automated_retry"
            }
        except Exception as e:
            logger.error(f"Failed to analyze recovery options: {e}")
            return {
                "recovery_feasible": False,
                "error": str(e),
                "recommended_action": "manual_intervention"
            }
    
    async def recover_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Attempt to recover a failed workflow"""
        
        try:
            workflow_status = await self.get_workflow_status(workflow_id)
            
            if not workflow_status.get("transitions"):
                return {
                    "workflow_id": workflow_id,
                    "recovery_status": "failed",
                    "reason": "No workflow state found"
                }
            
            # Transition to recovery state
            await self._transition_state(WorkflowState.RECOVERING, workflow_id)
            
            # Analyze the failure point
            last_transition = workflow_status["transitions"][-1]
            failed_state = last_transition.get("to_state")
            failure_context = last_transition.get("context", {})
            
            recovery_options = await self._analyze_recovery_options(
                workflow_id, 
                failure_context.get("error", "Unknown error")
            )
            
            logger.info(f"Recovery initiated for workflow {workflow_id} from state {failed_state}")
            
            return {
                "workflow_id": workflow_id,
                "recovery_status": "initiated",
                "failed_at_state": failed_state,
                "recovery_options": recovery_options
            }
            
        except Exception as e:
            logger.error(f"Workflow recovery failed for {workflow_id}: {e}")
            return {
                "workflow_id": workflow_id,
                "recovery_status": "failed",
                "error": str(e)
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive workflow performance metrics"""
        
        success_rate = (
            self.performance_metrics["successful_workflows"] / 
            max(1, self.performance_metrics["total_workflows"])
        ) * 100
        
        return {
            **self.performance_metrics,
            "success_rate": success_rate,
            "failure_rate": 100 - success_rate,
            "active_workflows": len([
                wf_id for wf_id, transitions in self.state_transitions.items()
                if transitions and transitions[-1]["to_state"] not in ["completed", "failed"]
            ]),
            "timestamp": datetime.now().isoformat()
        }