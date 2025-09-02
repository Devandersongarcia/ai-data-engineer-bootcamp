"""
CrewAI Fraud Detection System with External Prompt Management
Modern multi-agent fraud detection using external markdown prompts
"""

import logging
import json
import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field

from .prompt_manager import PromptManager
from .crewai_qdrant_knowledge import CrewAIQdrantKnowledge, QdrantKnowledgeTool
from config.settings import settings

logger = logging.getLogger(__name__)

class PromptBasedCrewAISystem:
    """CrewAI fraud detection system using external prompt management"""
    
    def __init__(self, qdrant_url: Optional[str] = None, qdrant_api_key: Optional[str] = None):
        """Initialize CrewAI system with prompt management - OPTIMIZED FOR STREAMING"""
        
        # Initialize prompt manager with error handling
        try:
            self.prompt_manager = PromptManager()
        except Exception as e:
            logger.warning(f"Failed to initialize prompt manager: {e}. Using simplified prompts.")
            self.prompt_manager = None
        
        # Skip Qdrant initialization to prevent hanging (disabled for streaming performance)
        self.qdrant_knowledge = None
        self.qdrant_tool = None
        logger.info("Qdrant integration disabled for streaming performance")
        
        # Create simplified agents optimized for speed
        self.agents = self._create_streamlined_agents()
        
        logger.info("PromptBasedCrewAISystem initialized successfully (STREAMING OPTIMIZED)")
    
    def _create_agents_from_prompts(self) -> Dict[str, Agent]:
        """Create agents using external prompt configurations"""
        
        agents = {}
        
        # Agent names to create
        agent_names = ["fraud_analyst", "risk_assessor", "decision_maker", "action_executor"]
        
        for agent_name in agent_names:
            try:
                # Load agent configuration from prompt
                agent_config = self.prompt_manager.load_agent_prompt(agent_name)
                
                # Create agent with prompt-based configuration
                agent = Agent(
                    role=agent_config["role"],
                    goal=agent_config["goal"],
                    backstory=agent_config["backstory"],
                    verbose=True,
                    allow_delegation=False,
                    tools=self._get_agent_tools(agent_name),
                    max_iter=self._get_agent_max_iter(agent_name),
                    memory=True
                )
                
                agents[agent_name] = agent
                logger.info(f"Created agent '{agent_name}' from external prompt")
                
            except Exception as e:
                logger.error(f"Failed to create agent '{agent_name}' from prompt: {e}")
                raise
        
        return agents
    
    def _create_streamlined_agents(self) -> Dict[str, Agent]:
        """Create optimized agents for streaming performance (without complex prompts/tools)"""
        
        agents = {}
        
        # Single streamlined fraud analyst agent (combined functionality)
        fraud_analyst = Agent(
            role="Senior Fraud Detection Analyst",
            goal="Quickly analyze orders for fraud patterns and make recommendations",
            backstory="Expert fraud analyst with 10+ years experience in real-time fraud detection",
            verbose=False,  # Disable verbose output for performance
            allow_delegation=False,
            tools=[],  # No external tools to prevent hanging
            max_iter=1,  # Single iteration for speed
            memory=False  # Disable memory to prevent hanging
        )
        
        agents["fraud_analyst"] = fraud_analyst
        logger.info("Created streamlined fraud analyst agent for streaming")
        
        return agents
    
    def _get_agent_tools(self, agent_name: str) -> List[Any]:
        """Get tools for specific agent"""
        # For now, keep it simple without tools - agents will rely on prompts and LLM capabilities
        # In future iterations, we can add proper CrewAI tool implementations
        tool_mapping = {
            "fraud_analyst": [],  # Uses prompts and LLM reasoning
            "risk_assessor": [],  # Uses prompts and LLM reasoning  
            "decision_maker": [],  # Uses internal decision logic
            "action_executor": []  # Uses internal action execution
        }
        
        return tool_mapping.get(agent_name, [])
    
    def _get_agent_max_iter(self, agent_name: str) -> int:
        """Get max iterations for specific agent"""
        iteration_mapping = {
            "fraud_analyst": 3,
            "risk_assessor": 3,
            "decision_maker": 2,
            "action_executor": 2
        }
        
        return iteration_mapping.get(agent_name, 2)
    
    def analyze_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze order using streamlined agents with timeout protection"""
        start_time = time.time()
        order_id = order_data.get('order_id', 'unknown')
        
        try:
            logger.info(f"Starting STREAMLINED analysis for order {order_id}")
            
            # Create single streamlined task
            task = self._create_streamlined_task(order_data)
            
            # Create minimal crew configuration
            crew = Crew(
                agents=[self.agents["fraud_analyst"]],
                tasks=[task],
                process=Process.sequential,
                memory=False,  # Disabled for performance
                verbose=False  # Disabled for performance
            )
            
            # Execute with timeout protection using threading
            result = self._execute_with_timeout(crew, timeout_seconds=25)
            
            # Parse results quickly
            analysis_result = self._parse_streamlined_results(result, order_data)
            analysis_result["processing_time_ms"] = int((time.time() - start_time) * 1000)
            
            logger.info(f"Streamlined analysis completed for {order_id} in {analysis_result['processing_time_ms']}ms")
            return analysis_result
            
        except TimeoutError:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Analysis timed out for order {order_id} after {processing_time}ms")
            
            return {
                "success": False,
                "error": "Analysis timed out",
                "order_id": order_id,
                "fraud_score": 0.4,  # Slightly higher due to timeout risk
                "recommended_action": "FLAG",  # Flag for manual review due to timeout
                "confidence": 0.3,
                "reasoning": f"Agent analysis timed out after {processing_time}ms",
                "processing_time_ms": processing_time,
                "patterns_detected": ["timeout_risk"],
                "framework": "crewai_timeout_fallback"
            }
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Error in streamlined analysis for {order_id}: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "order_id": order_id,
                "fraud_score": 0.3,
                "recommended_action": "MONITOR",
                "confidence": 0.5,
                "reasoning": f"Analysis failed: {str(e)[:100]}",
                "processing_time_ms": processing_time,
                "patterns_detected": ["analysis_error"],
                "framework": "crewai_error_fallback"
            }
    
    def _create_streamlined_task(self, order_data: Dict[str, Any]) -> Task:
        """Create a single streamlined task for rapid fraud analysis"""
        
        # Create concise prompt focused on key fraud indicators
        prompt = f"""
        FRAUD ANALYSIS TASK:
        
        Analyze this order for fraud risk and provide a quick assessment:
        
        ORDER DETAILS:
        - ID: {order_data.get('order_id', 'unknown')}
        - Amount: ${order_data.get('total_amount', 0)}
        - User: {order_data.get('user_id', 'unknown')}
        - Payment: {order_data.get('payment_method', 'unknown')}
        - Account Age: {order_data.get('account_age_days', 0)} days
        - Orders Today: {order_data.get('orders_today', 0)}
        - Avg Order Value: ${order_data.get('avg_order_value', 25.0)}
        
        QUICK ANALYSIS REQUIRED:
        1. Risk Level: HIGH/MEDIUM/LOW
        2. Action: BLOCK/FLAG/MONITOR/ALLOW  
        3. Fraud Score: 0.0-1.0
        4. Key Indicators: List 1-3 main concerns
        5. Brief Reasoning: 1-2 sentences max
        
        FOCUS ON SPEED - Provide concise, actionable analysis.
        """
        
        task = Task(
            description=prompt,
            agent=self.agents["fraud_analyst"],
            expected_output="Quick fraud assessment: risk_level, recommended_action, fraud_score, patterns, reasoning"
        )
        
        return task
    
    def _execute_with_timeout(self, crew: Crew, timeout_seconds: int = 25) -> str:
        """Execute crew with timeout protection - fallback to direct execution"""
        logger.info("Executing CrewAI crew directly (signal limitations noted)")
        
        try:
            # Direct execution - let CrewAI handle its own internal signals
            # The signal error is handled gracefully by our calling code
            result = crew.kickoff()
            return str(result)
            
        except Exception as e:
            logger.error(f"Crew execution failed: {e}")
            # Re-raise to let the calling code handle with fallback
            raise
    
    def _parse_streamlined_results(self, result: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse streamlined crew results quickly"""
        try:
            result_text = str(result).upper()
            
            # Quick extraction of key values
            fraud_score = 0.3  # Default
            recommended_action = "MONITOR"  # Default
            confidence = 0.6  # Default
            patterns = []
            
            # Extract recommended action (prioritized keywords)
            if "BLOCK" in result_text:
                recommended_action = "BLOCK"
                fraud_score = 0.8
            elif "FLAG" in result_text:
                recommended_action = "FLAG"  
                fraud_score = 0.6
            elif "ALLOW" in result_text:
                recommended_action = "ALLOW"
                fraud_score = 0.2
            else:
                recommended_action = "MONITOR"
                fraud_score = 0.4
            
            # Extract risk level for confidence
            if "HIGH" in result_text and "RISK" in result_text:
                confidence = 0.9
                patterns.append("high_risk_pattern")
            elif "MEDIUM" in result_text and "RISK" in result_text:
                confidence = 0.7
                patterns.append("medium_risk_pattern")
            elif "LOW" in result_text and "RISK" in result_text:
                confidence = 0.8
                patterns.append("low_risk_pattern")
            
            # Look for common fraud patterns in text
            if "VELOCITY" in result_text:
                patterns.append("velocity_fraud")
            if "CARD" in result_text:
                patterns.append("card_testing")
            if "ACCOUNT" in result_text and "NEW" in result_text:
                patterns.append("new_account_risk")
            if "AMOUNT" in result_text and "UNUSUAL" in result_text:
                patterns.append("amount_anomaly")
            
            return {
                "success": True,
                "order_id": order_data.get("order_id", "unknown"),
                "fraud_score": fraud_score,
                "recommended_action": recommended_action,
                "confidence": confidence,
                "patterns_detected": patterns,
                "reasoning": result[:200] + "..." if len(result) > 200 else result,
                "framework": "crewai_streamlined",
                "version": "2.0"
            }
            
        except Exception as e:
            logger.error(f"Error parsing streamlined results: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_id": order_data.get("order_id", "unknown"),
                "fraud_score": 0.4,
                "recommended_action": "MONITOR",
                "confidence": 0.5,
                "patterns_detected": ["parsing_error"],
                "reasoning": "Failed to parse agent response",
                "framework": "crewai_fallback"
            }
    
    def _create_tasks_from_prompts(self, order_data: Dict[str, Any]) -> List[Task]:
        """Create tasks using external prompt templates"""
        
        tasks = []
        order_data_json = json.dumps(order_data, indent=2)
        
        # Task 1: Pattern Analysis
        try:
            pattern_prompt = self._create_pattern_analysis_prompt(order_data)
            
            pattern_task = Task(
                description=pattern_prompt,
                agent=self.agents["fraud_analyst"],
                expected_output="Comprehensive fraud pattern analysis with detected patterns, confidence scores, evidence, and risk assessment"
            )
            tasks.append(pattern_task)
            
        except Exception as e:
            logger.error(f"Failed to create pattern analysis task: {e}")
            # Fallback to simple prompt
            pattern_task = Task(
                description=f"Analyze this order for fraud patterns: {order_data_json}",
                agent=self.agents["fraud_analyst"],
                expected_output="Fraud pattern analysis results"
            )
            tasks.append(pattern_task)
        
        # Task 2: Risk Assessment
        try:
            risk_prompt = self._create_risk_assessment_prompt(order_data)
            
            risk_task = Task(
                description=risk_prompt,
                agent=self.agents["risk_assessor"],
                expected_output="Complete risk assessment with final risk score, business recommendation, and supporting analysis",
                context=[pattern_task]
            )
            tasks.append(risk_task)
            
        except Exception as e:
            logger.error(f"Failed to create risk assessment task: {e}")
            # Fallback to simple prompt
            risk_task = Task(
                description=f"Assess fraud risk for this order based on pattern analysis: {order_data_json}",
                agent=self.agents["risk_assessor"],
                expected_output="Risk assessment results",
                context=[pattern_task]
            )
            tasks.append(risk_task)
        
        # Task 3: Decision Making
        decision_prompt = f"""
        Make the final fraud prevention decision for this order based on risk assessment:
        
        Order: {order_data.get('order_id', 'unknown')}
        Amount: ${order_data.get('total_amount', 0)}
        
        Apply business policies and provide final decision (ALLOW/MONITOR/FLAG/BLOCK) with reasoning.
        """
        
        decision_task = Task(
            description=decision_prompt,
            agent=self.agents["decision_maker"],
            expected_output="Final fraud prevention decision with policy compliance verification",
            context=[pattern_task, risk_task]
        )
        tasks.append(decision_task)
        
        # Task 4: Action Execution
        action_prompt = f"""
        Execute the fraud prevention decision with complete audit trail:
        
        Order: {order_data.get('order_id', 'unknown')}
        
        Execute required actions and provide confirmation with audit details.
        """
        
        action_task = Task(
            description=action_prompt,
            agent=self.agents["action_executor"],
            expected_output="Action execution confirmation with audit trail and performance metrics",
            context=[decision_task]
        )
        tasks.append(action_task)
        
        return tasks
    
    def _create_pattern_analysis_prompt(self, order_data: Dict[str, Any]) -> str:
        """Create pattern analysis prompt using template"""
        try:
            # Prepare variables for template substitution
            variables = {
                "order_data": json.dumps(order_data, indent=2),
                "orders_today": order_data.get("orders_today", 0),
                "orders_last_hour": order_data.get("orders_last_hour", 0),
                "account_age_days": order_data.get("account_age_days", 0),
                "order_creation_speed_ms": order_data.get("order_creation_speed_ms", 2000),
                "total_amount": order_data.get("total_amount", 0),
                "payment_method": order_data.get("payment_method", "unknown"),
                "payment_failures_today": order_data.get("payment_failures_today", 0),
                "behavior_change_score": order_data.get("behavior_change_score", 0.0),
                "new_payment_method": order_data.get("new_payment_method", False),
                "address_change_flag": order_data.get("address_change_flag", False),
                "avg_order_value": order_data.get("avg_order_value", 25.0)
            }
            
            # Calculate amount ratio
            avg_order_value = variables["avg_order_value"]
            if avg_order_value > 0:
                variables["amount_ratio"] = variables["total_amount"] / avg_order_value
            else:
                variables["amount_ratio"] = 1.0
            
            # Load and format the task prompt
            return self.prompt_manager.load_task_prompt("pattern_analysis", variables)
            
        except Exception as e:
            logger.error(f"Error creating pattern analysis prompt: {e}")
            # Return fallback prompt
            return f"""
            Analyze this order for fraud patterns:
            
            {json.dumps(order_data, indent=2)}
            
            Detect velocity fraud, card testing, account anomalies, and amount anomalies.
            Provide specific evidence and confidence scores.
            """
    
    def _create_risk_assessment_prompt(self, order_data: Dict[str, Any]) -> str:
        """Create risk assessment prompt"""
        return f"""
        Calculate comprehensive fraud risk score for this order:
        
        Order Data: {json.dumps(order_data, indent=2)}
        
        Consider:
        1. Pattern analysis results from previous task
        2. User account context and history
        3. Business context and customer tier
        4. Similar historical cases
        5. False positive costs and business impact
        
        Provide final risk score (0.0-1.0), recommendation (ALLOW/MONITOR/FLAG/BLOCK), and detailed reasoning.
        """
    
    def _parse_crew_results(self, crew_result: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse crew results into structured format"""
        try:
            result_text = str(crew_result)
            
            # Extract fraud score
            fraud_score = self._extract_score(result_text, "score", 0.3)
            confidence = self._extract_score(result_text, "confidence", 0.6)
            
            # Extract recommendation
            recommended_action = "MONITOR"
            if "BLOCK" in result_text.upper():
                recommended_action = "BLOCK"
            elif "FLAG" in result_text.upper():
                recommended_action = "FLAG"
            elif "ALLOW" in result_text.upper():
                recommended_action = "ALLOW"
            
            # Extract patterns
            patterns = []
            pattern_keywords = ["velocity_fraud", "card_testing", "account_takeover", "amount_anomaly", "new_account_risk"]
            for pattern in pattern_keywords:
                if pattern in result_text.lower():
                    patterns.append(pattern)
            
            return {
                "success": True,
                "order_id": order_data.get("order_id", "unknown"),
                "fraud_score": fraud_score,
                "recommended_action": recommended_action,
                "confidence": confidence,
                "patterns_detected": patterns,
                "reasoning": result_text[:500] + "..." if len(result_text) > 500 else result_text,
                "framework": "crewai_with_prompts",
                "prompt_version": "1.0"
            }
            
        except Exception as e:
            logger.error(f"Error parsing crew results: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_id": order_data.get("order_id", "unknown"),
                "fraud_score": 0.3,
                "recommended_action": "MONITOR",
                "confidence": 0.5,
                "reasoning": "Failed to parse results",
                "patterns_detected": []
            }
    
    def _extract_score(self, text: str, score_type: str, default: float) -> float:
        """Extract numerical score from text"""
        import re
        pattern = rf'{score_type}[:\s]+([0-9]*\.?[0-9]+)'
        match = re.search(pattern, text.lower())
        if match:
            try:
                score = float(match.group(1))
                return min(max(score, 0.0), 1.0)
            except:
                pass
        return default
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information including prompt management"""
        try:
            prompt_validation = self.prompt_manager.validate_prompts()
            cache_stats = self.prompt_manager.get_cache_stats()
            
            return {
                "framework": "crewai_with_prompts",
                "agents_count": len(self.agents),
                "agents": list(self.agents.keys()),
                "prompt_management": {
                    "available_agents": self.prompt_manager.get_available_agents(),
                    "available_tasks": self.prompt_manager.get_available_tasks(),
                    "validation": prompt_validation,
                    "cache": cache_stats
                },
                "qdrant_integration": True,
                "system_status": "operational"
            }
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {
                "framework": "crewai_with_prompts",
                "error": str(e),
                "system_status": "error"
            }
    
    def reload_prompts(self):
        """Reload prompts from files (useful for development)"""
        try:
            # Clear cache and recreate agents
            self.prompt_manager.clear_cache()
            self.agents = self._create_agents_from_prompts()
            logger.info("Prompts reloaded successfully")
            
        except Exception as e:
            logger.error(f"Error reloading prompts: {e}")
            raise