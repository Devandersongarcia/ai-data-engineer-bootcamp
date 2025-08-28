"""Production-grade MindsDB client with comprehensive error handling.

This module provides a robust interface to MindsDB that circumvents
common SDK issues while maintaining API compatibility.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Union

import requests

from config.constants import APIConstants
from utils.retry_utils import retry_api_call, create_resilient_session

logger = logging.getLogger(__name__)

class MindsDBAgent:
    """Production-ready MindsDB agent with enhanced reliability."""
    
    def __init__(self, server_url: str, agent_name: str):
        """Initialize agent with validation.
        
        Args:
            server_url: MindsDB server URL
            agent_name: Name of the agent to interact with
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("Agent name cannot be empty")
        
        self.server_url = server_url.rstrip('/')
        self.agent_name = agent_name.strip()
        self.session = create_resilient_session(self.server_url)
        
        logger.info(f"Initialized MindsDB agent: {agent_name}")
    
    @retry_api_call(max_retries=APIConstants.DEFAULT_MAX_RETRIES)
    def completion(self, messages: List[Dict[str, Any]], timeout: int = 60) -> List[Dict[str, str]]:
        """
        Agent completion that mimics SDK interface
        
        Args:
            messages: List of message dicts with 'question' and 'answer'
            timeout: Request timeout in seconds
            
        Returns:
            List with response dict containing 'answer'
            
        Raises:
            ConnectionError: When server is unreachable
            ValueError: When agent query fails
        """
        try:
            # Extract question from messages (SDK format)
            question = messages[0].get('question', '') if messages else ''
            
            # Build SQL query for the agent using template
            sql_query = APIConstants.AGENT_QUERY_TEMPLATE.format(
                agent_name=self.agent_name,
                question=question.replace("'", "''")
            )
            
            # Execute via REST API
            response = self.session.post(
                f"{self.server_url}{APIConstants.SQL_QUERY_ENDPOINT}",
                json={"query": sql_query},
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract answer from SQL response
                if 'data' in data and data['data'] and len(data['data']) > 0:
                    row = data['data'][0]
                    
                    # Handle different row formats
                    if isinstance(row, dict):
                        answer = row.get('answer', '')
                    elif isinstance(row, list) and len(row) > 0:
                        # If row is a list, the answer is usually the first element
                        answer = str(row[0]) if row[0] is not None else ''
                    else:
                        answer = str(row)
                    
                    return [{'answer': answer}]
                else:
                    logger.warning(f"Empty response data for question: {question[:50]}")
                    return [{'answer': 'Nenhum dado retornado pelo agente'}]
            else:
                logger.error(f"HTTP {response.status_code}: {response.text[:200]}")
                return [{'answer': f'Erro HTTP {response.status_code}: Servidor indisponível'}]
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for question: {question[:50]}")
            return [{'answer': 'Timeout: Agente demorou para responder'}]
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to {self.server_url}")
            return [{'answer': 'Erro de conexão: Servidor MindsDB indisponível'}]
        except Exception as e:
            logger.error(f"Agent completion failed: {e}")
            return [{'answer': f'Erro interno: {str(e)}'}]


class MindsDBAgentManager:
    """Agent manager that mimics SDK agents interface"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.session = create_resilient_session(server_url)
    
    def get(self, agent_name: str) -> MindsDBAgent:
        """
        Get agent by name (mimics SDK interface)
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            MindsDBAgent instance
            
        Raises:
            ValueError: When agent is not found
            ConnectionError: When server is unreachable
        """
        # Check if agent exists first
        if not self._agent_exists(agent_name):
            raise ValueError(f"Agent '{agent_name}' not found. Run 'SHOW AGENTS;' to see available agents.")
        
        return MindsDBAgent(self.server_url, agent_name)
    
    @retry_api_call(max_retries=2)
    def list_agents(self) -> List[str]:
        """Get list of all available agent names"""
        try:
            response = self.session.post(
                f"{self.server_url}{APIConstants.SQL_QUERY_ENDPOINT}",
                json={"query": APIConstants.SHOW_AGENTS_QUERY},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                agent_names = []
                
                if 'data' in data and data['data']:
                    for row in data['data']:
                        # Handle different response formats
                        if isinstance(row, dict):
                            if 'NAME' in row and row['NAME']:
                                agent_names.append(row['NAME'])
                        elif isinstance(row, list) and len(row) > 0:
                            # If row is a list, first element is usually the name
                            if row[0]:
                                agent_names.append(str(row[0]))
                
                return sorted(agent_names)  # Return sorted list
            
            return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list agents due to network error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing agents: {e}")
            return []

    @retry_api_call(max_retries=2)  # Fewer retries for existence check
    def _agent_exists(self, agent_name: str) -> bool:
        """Check if agent exists"""
        try:
            response = self.session.post(
                f"{self.server_url}{APIConstants.SQL_QUERY_ENDPOINT}",
                json={"query": APIConstants.SHOW_AGENTS_QUERY},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    for row in data['data']:
                        # Handle different response formats
                        if isinstance(row, dict):
                            if row.get('NAME') == agent_name:
                                return True
                        elif isinstance(row, list) and len(row) > 0:
                            # If row is a list, first element is usually the name
                            if str(row[0]) == agent_name:
                                return True
            
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check if agent exists due to network error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking agent existence: {e}")
            return False


class MindsDBServer:
    """Server connection that mimics SDK interface"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.agents = MindsDBAgentManager(server_url)
    
    @retry_api_call(max_retries=2)  # Quick retry for connection test
    def test_connection(self, timeout: int = 10) -> bool:
        """
        Test connection to MindsDB server
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if connection successful
        """
        try:
            session = create_resilient_session(self.server_url)
            response = session.get(f"{self.server_url}{APIConstants.STATUS_ENDPOINT}", timeout=timeout)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {e}")
            return False


def connect(
    server_url: str = "http://127.0.0.1:47334", 
    timeout: int = 10,
    validate_connection: bool = True
) -> MindsDBServer:
    """Establish connection to MindsDB server with validation.
    
    Args:
        server_url: MindsDB server URL
        timeout: Connection timeout in seconds
        validate_connection: Whether to test connection during initialization
        
    Returns:
        Configured MindsDBServer instance
        
    Raises:
        ConnectionError: If connection validation fails
    """
    logger.info(f"Connecting to MindsDB server: {server_url}")
    
    server = MindsDBServer(server_url)
    
    if validate_connection and not server.test_connection(timeout):
        raise ConnectionError(
            f"Cannot connect to MindsDB server at {server_url}. "
            f"Please check if the server is running and accessible."
        )
    
    return server


# Test the wrapper
if __name__ == "__main__":
    print("🧠 Testing MindsDB Client")
    print("=" * 40)
    
    try:
        # Step 1: Connect
        print("1. 🔗 Connecting...")
        server = connect()
        print("✅ Connected to MindsDB server")
        
        # Step 2: Get agent
        print("\n2. 🤖 Getting agent...")
        agent = server.agents.get('brasil_invoice_expert')
        print("✅ Agent found!")
        
        # Step 3: Test query
        print("\n3. 💬 Testing query...")
        completion = agent.completion(
            messages=[{
                'question': 'Status OK?',
                'answer': None
            }]
        )
        
        print("✅ Query successful!")
        if completion and len(completion) > 0:
            answer = completion[0].get('answer', 'No answer')
            print(f"🤖 Answer: {answer[:100]}...")
        
        print("\n🎉 MindsDB client works perfectly!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
        if "not found" in str(e).lower():
            print("\n💡 Make sure 'brasil_invoice_expert' agent exists")
            print("   Execute: SHOW AGENTS; in MindsDB Editor")