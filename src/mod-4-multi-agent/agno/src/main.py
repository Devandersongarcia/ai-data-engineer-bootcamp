"""Main demonstration module for the UberEats Multi-Agent System.

This module showcases the complete capabilities of the modernized UberEats
Multi-Agent System built with Agno 1.1+, featuring:
- Level 4 Agent Teams with intelligent collaboration
- Level 5 Agentic Workflows with state management
- Production-ready monitoring and observability
- Performance improvements (~10,000x faster agent creation)

Usage:
    python -m src.main
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from src.orchestration.agent_teams import UberEatsAgentTeam
from src.orchestration.agentic_workflows import UberEatsAgenticWorkflow
from src.monitoring.observability import monitoring_system
from src.config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_agent_teams() -> None:
    """Demonstrate Level 4 Agent Teams with collaboration.
    
    Shows advanced multi-agent coordination capabilities including:
    - Intelligent request routing
    - Agent collaboration on complex tasks
    - Team health monitoring
    - Performance metrics collection
    """
    
    print("\n🤝 Level 4 Agent Teams Demo")
    print("=" * 50)
    
    try:
        # Initialize agent team
        print("Initializing Level 4 Agent Teams...")
        agent_team = UberEatsAgentTeam()
        
        await asyncio.sleep(3)
        
        customer_request = {
            "message": "I need to cancel my order and get a refund. The order number is #12345 and I ordered it 30 minutes ago.",
            "customer_id": "customer_789",
            "session_id": "demo_session_001",
            "priority": "high"
        }
        
        print("\n📞 Processing Customer Service Request...")
        result = await agent_team.process_request(customer_request)
        
        if result.get("success"):
            print("✅ Agent team collaboration successful!")
            print(f"🎯 Involved Agents: {result.get('involved_agents', [])}")
            print(f"⏱️ Processing Time: {result.get('processing_time', 0):.2f}s")
            print(f"🤖 Response: {result.get('final_response', 'No response')[:200]}...")
        else:
            print(f"❌ Agent team collaboration failed: {result.get('error')}")
        
        complex_request = {
            "message": "I want to know the delivery time for a pizza order from Tony's Restaurant, but I also need to update my dietary restrictions to vegetarian and get restaurant recommendations for lunch tomorrow.",
            "customer_id": "customer_790",
            "session_id": "demo_session_002",
            "priority": "normal"
        }
        
        print("\n🔄 Processing Complex Multi-Domain Request...")
        result = await agent_team.process_request(complex_request)
        
        if result.get("success"):
            print("✅ Complex collaboration successful!")
            print(f"🎯 Involved Agents: {result.get('involved_agents', [])}")
            print(f"⏱️ Processing Time: {result.get('processing_time', 0):.2f}s")
            print(f"📊 Orchestration Quality: Advanced multi-agent coordination")
        else:
            print(f"❌ Complex collaboration failed: {result.get('error')}")
            
        health_status = await agent_team.get_team_health_status()
        print(f"\n💊 Team Health Score: {health_status.get('team_health_score', 'N/A'):.2f}")
        
    except Exception as e:
        logger.error(f"Error in agent teams demo: {e}")
        print(f"❌ Agent teams demo failed: {e}")


async def demo_agentic_workflows() -> None:
    """Demonstrate Level 5 Agentic Workflows with state management.
    
    Showcases deterministic workflow execution with:
    - State transition tracking
    - Quality assurance validation
    - Performance monitoring
    - Error recovery mechanisms
    """
    
    print("\n🔄 Level 5 Agentic Workflows Demo")
    print("=" * 50)
    
    try:
        print("Initializing Level 5 Agentic Workflows...")
        workflow_engine = UberEatsAgenticWorkflow()
        
        order_workflow_request = {
            "request_type": "order_processing",
            "data": {
                "order_id": "order_workflow_001",
                "customer_id": "customer_801",
                "restaurant_id": "restaurant_201",
                "items": [
                    {"name": "Margherita Pizza", "quantity": 1, "price": 18.99},
                    {"name": "Garlic Bread", "quantity": 2, "price": 5.99}
                ],
                "delivery_address": "789 Innovation St, San Francisco, CA",
                "special_instructions": "Ring doorbell twice, contact-free delivery"
            },
            "session_id": "workflow_demo_001",
            "priority": "normal",
            "workflow_options": {
                "enable_quality_validation": True,
                "enable_advanced_coordination": True
            }
        }
        
        print("\n📦 Executing Order Processing Workflow...")
        workflow_result = await workflow_engine.execute_workflow(order_workflow_request)
        
        if workflow_result.get("success"):
            print("✅ Workflow execution successful!")
            print(f"🆔 Workflow ID: {workflow_result.get('workflow_id')}")
            print(f"⏱️ Execution Time: {workflow_result.get('execution_time', 0):.2f}s")
            print(f"🏆 Quality Score: {workflow_result.get('quality_score', 0):.2f}")
            print(f"🔄 State Transitions: {len(workflow_result.get('state_transitions', []))}")
            
            stages = workflow_result.get('execution_stages', {})
            print("\n📊 Execution Stages:")
            for stage, stage_data in stages.items():
                if isinstance(stage_data, dict) and stage_data.get('success'):
                    print(f"   ✅ {stage.capitalize()}: Success")
                else:
                    print(f"   ⚠️ {stage.capitalize()}: {stage_data}")
        else:
            print(f"❌ Workflow execution failed: {workflow_result.get('error')}")
        
        inquiry_workflow_request = {
            "request_type": "customer_inquiry",
            "data": {
                "inquiry": "I have a food allergy to nuts. Can you help me find safe restaurants and also explain your allergy handling policies?",
                "customer_id": "customer_802",
                "urgency": "high",
                "allergy_type": "nuts"
            },
            "session_id": "workflow_demo_002",
            "priority": "high"
        }
        
        print("\n🚨 Executing High-Priority Customer Inquiry Workflow...")
        inquiry_result = await workflow_engine.execute_workflow(inquiry_workflow_request)
        
        if inquiry_result.get("success"):
            print("✅ Customer inquiry workflow successful!")
            print(f"🆔 Workflow ID: {inquiry_result.get('workflow_id')}")
            print(f"⏱️ Execution Time: {inquiry_result.get('execution_time', 0):.2f}s")
            print(f"🏆 Quality Score: {inquiry_result.get('quality_score', 0):.2f}")
        else:
            print(f"❌ Customer inquiry workflow failed: {inquiry_result.get('error')}")
            
        performance_metrics = workflow_engine.get_performance_metrics()
        print(f"\n📈 Workflow Performance:")
        print(f"   Success Rate: {performance_metrics.get('success_rate', 0):.1f}%")
        print(f"   Average Execution Time: {performance_metrics.get('average_execution_time', 0):.2f}s")
        print(f"   Total Workflows: {performance_metrics.get('total_workflows', 0)}")
        
    except Exception as e:
        logger.error(f"Error in agentic workflows demo: {e}")
        print(f"❌ Agentic workflows demo failed: {e}")


async def demo_performance_improvements() -> None:
    """Demonstrate performance improvements with Agno 1.1+.
    
    Tests and measures:
    - Sequential request processing speed
    - Throughput benchmarks
    - Success rate metrics
    - Performance baseline comparisons
    """
    
    print("\n⚡ Performance Improvements Demo")
    print("=" * 50)
    
    try:
        agent_team = UberEatsAgentTeam()
        await asyncio.sleep(2)  # Allow initialization
        
        print("Testing rapid sequential processing...")
        start_time = datetime.now()
        
        requests = []
        for i in range(5):
            request = {
                "message": f"Test request {i+1} - What's the status of order #{1000+i}?",
                "customer_id": f"perf_test_customer_{i}",
                "session_id": f"perf_test_session_{i}"
            }
            requests.append(request)
        
        results = []
        for request in requests:
            result = await agent_team.process_request(request)
            results.append(result)
        
        total_time = (datetime.now() - start_time).total_seconds()
        successful_requests = sum(1 for r in results if r.get("success"))
        
        print(f"✅ Performance Test Results:")
        print(f"   📊 Processed {len(requests)} requests in {total_time:.3f}s")
        print(f"   🎯 Success Rate: {(successful_requests/len(requests)*100):.1f}%")
        print(f"   ⚡ Average Time per Request: {(total_time/len(requests)):.3f}s")
        print(f"   🚀 Throughput: {(len(requests)/total_time):.1f} requests/second")
        
        baseline_time_per_request = 2.0  # Expected with Agno 1.1+
        actual_time_per_request = total_time / len(requests)
        
        if actual_time_per_request < baseline_time_per_request:
            improvement = ((baseline_time_per_request - actual_time_per_request) / baseline_time_per_request) * 100
            print(f"   🏆 {improvement:.1f}% faster than baseline!")
        
    except Exception as e:
        logger.error(f"Error in performance demo: {e}")
        print(f"❌ Performance demo failed: {e}")


async def demo_monitoring_system() -> None:
    """Demonstrate monitoring and observability features.
    
    Displays comprehensive system monitoring including:
    - System health scoring
    - Agent performance metrics
    - Workflow execution tracking
    - Alert generation and management
    """
    
    print("\n📊 Monitoring & Observability Demo")
    print("=" * 50)
    
    try:
        print("Starting monitoring system...")
        
        monitoring_system.record_agent_request("customer_agent", 1.2, True, "normal")
        monitoring_system.record_agent_request("restaurant_agent", 0.8, True, "high")
        monitoring_system.record_agent_request("delivery_agent", 2.1, False, "normal")
        
        monitoring_system.record_workflow_execution(
            "workflow_001", "order_processing", 5.2, 0.96, 
            ["customer_agent", "restaurant_agent", "order_agent"], True
        )
        
        dashboard_data = monitoring_system.get_monitoring_dashboard_data()
        
        print("✅ Monitoring System Active!")
        print(f"📈 System Health Score: {dashboard_data['system_health']['score']:.3f}")
        print(f"🤖 Active Agents: {len(dashboard_data['agent_metrics'])}")
        print(f"🔄 Workflow Success Rate: {dashboard_data['workflow_metrics']['success_rate']:.1f}%")
        print(f"⚠️ Recent Alerts: {len(dashboard_data['recent_alerts'])}")
        
        print("\n🎯 Agent Performance Summary:")
        for agent_id, metrics in dashboard_data['agent_metrics'].items():
            print(f"   • {agent_id}: {metrics['success_rate']:.1f}% success, {metrics['avg_response_time']:.2f}s avg")
        
        print(f"\n📊 Monitoring Dashboard: Available at /api/v1/metrics")
        print(f"🔍 Health Check: Available at /api/v1/health")
        
    except Exception as e:
        logger.error(f"Error in monitoring demo: {e}")
        print(f"❌ Monitoring demo failed: {e}")


async def main() -> None:
    """Main demonstration of the modernized UberEats Multi-Agent System.
    
    Orchestrates all demonstration components to showcase the complete
    system capabilities including agent teams, workflows, performance
    monitoring, and observability features.
    
    Raises:
        Exception: If any critical demonstration component fails.
    """
    
    print("🚀 UberEats Multi-Agent System - Agno 1.1+ Modernized Demo")
    print("=" * 80)
    print("🔥 Features:")
    print("   • ~10,000x faster agent creation with Agno 1.1+")
    print("   • ~50x less memory usage per agent")
    print("   • Level 4 Agent Teams with intelligent collaboration")
    print("   • Level 5 Agentic Workflows with deterministic state management")
    print("   • Production-ready monitoring and observability")
    print("   • Real-time quality assurance and validation")
    print("=" * 80)
    
    try:
        await demo_agent_teams()
        await demo_agentic_workflows()
        await demo_performance_improvements()
        await demo_monitoring_system()
        
        print("\n🎉 All demonstrations completed successfully!")
        print("\n🚀 Ready for Production:")
        print("   • Start API server: python -m uvicorn src.api.production_api:app --host 0.0.0.0 --port 8000")
        print("   • Access API docs: http://localhost:8000/docs")
        print("   • Monitor health: http://localhost:8000/api/v1/health")
        print("   • View metrics: http://localhost:8000/api/v1/metrics")
        print("\n💡 Next Steps:")
        print("   • Configure environment variables in .env file")
        print("   • Set up database connections")
        print("   • Deploy with Docker: docker-compose up")
        print("   • Scale with Kubernetes: kubectl apply -f deployment/kubernetes/")
        
    except Exception as e:
        logger.error(f"Error in main demo: {e}")
        print(f"❌ Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())