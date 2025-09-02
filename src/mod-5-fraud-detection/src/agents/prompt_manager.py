"""
Prompt Management System for CrewAI Fraud Detection
Handles loading, templating, and versioning of prompts from markdown files
"""

import os
import re
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
from string import Template
from datetime import datetime

logger = logging.getLogger(__name__)

class PromptManager:
    """Manages prompts for CrewAI fraud detection system"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize prompt manager
        
        Args:
            prompts_dir: Directory containing prompt markdown files
        """
        self.prompts_dir = Path(prompts_dir)
        self.prompt_cache = {}
        self.cache_enabled = True
        
        # Verify prompts directory exists
        if not self.prompts_dir.exists():
            logger.error(f"Prompts directory not found: {self.prompts_dir}")
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")
        
        logger.info(f"PromptManager initialized with directory: {self.prompts_dir}")
    
    def load_agent_prompt(self, agent_name: str) -> Dict[str, Any]:
        """
        Load agent configuration from markdown file
        
        Args:
            agent_name: Name of the agent (fraud_analyst, risk_assessor, etc.)
            
        Returns:
            Dictionary with agent configuration
        """
        cache_key = f"agent_{agent_name}"
        
        if self.cache_enabled and cache_key in self.prompt_cache:
            return self.prompt_cache[cache_key]
        
        agent_file = self.prompts_dir / "agents" / f"{agent_name}.md"
        
        if not agent_file.exists():
            logger.error(f"Agent prompt file not found: {agent_file}")
            raise FileNotFoundError(f"Agent prompt file not found: {agent_file}")
        
        try:
            content = agent_file.read_text(encoding='utf-8')
            parsed_config = self._parse_agent_markdown(content)
            
            # Cache the result
            if self.cache_enabled:
                self.prompt_cache[cache_key] = parsed_config
            
            logger.info(f"Loaded agent prompt for: {agent_name}")
            return parsed_config
            
        except Exception as e:
            logger.error(f"Error loading agent prompt for {agent_name}: {e}")
            raise
    
    def load_task_prompt(self, task_name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Load and template task prompt from markdown file
        
        Args:
            task_name: Name of the task (pattern_analysis, risk_assessment, etc.)
            variables: Variables to substitute in the template
            
        Returns:
            Formatted task prompt string
        """
        cache_key = f"task_{task_name}"
        
        # Load from cache or file
        if self.cache_enabled and cache_key in self.prompt_cache:
            template_content = self.prompt_cache[cache_key]
        else:
            task_file = self.prompts_dir / "tasks" / f"{task_name}.md"
            
            if not task_file.exists():
                logger.error(f"Task prompt file not found: {task_file}")
                raise FileNotFoundError(f"Task prompt file not found: {task_file}")
            
            try:
                template_content = task_file.read_text(encoding='utf-8')
                
                # Cache the template
                if self.cache_enabled:
                    self.prompt_cache[cache_key] = template_content
                    
            except Exception as e:
                logger.error(f"Error loading task prompt for {task_name}: {e}")
                raise
        
        # Apply variable substitution if provided
        if variables:
            try:
                # Extract the template section
                task_prompt = self._extract_task_prompt_template(template_content)
                formatted_prompt = self._substitute_variables(task_prompt, variables)
                
                logger.info(f"Loaded and formatted task prompt for: {task_name}")
                return formatted_prompt
                
            except Exception as e:
                logger.error(f"Error formatting task prompt for {task_name}: {e}")
                return template_content  # Return unformatted as fallback
        
        return template_content
    
    def load_tool_prompt(self, tool_name: str) -> str:
        """
        Load tool prompt from markdown file
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool prompt string
        """
        tool_file = self.prompts_dir / "tools" / f"{tool_name}.md"
        
        if not tool_file.exists():
            logger.warning(f"Tool prompt file not found: {tool_file}")
            return ""
        
        try:
            content = tool_file.read_text(encoding='utf-8')
            logger.info(f"Loaded tool prompt for: {tool_name}")
            return content
            
        except Exception as e:
            logger.error(f"Error loading tool prompt for {tool_name}: {e}")
            return ""
    
    def _parse_agent_markdown(self, content: str) -> Dict[str, Any]:
        """
        Parse agent markdown file into structured configuration
        
        Args:
            content: Markdown file content
            
        Returns:
            Parsed agent configuration
        """
        config = {
            "metadata": {},
            "role": "",
            "goal": "",
            "backstory": "",
            "tools": [],
            "configuration": {}
        }
        
        # Extract metadata from the beginning
        metadata_match = re.search(r'## Metadata\n(.*?)\n\n', content, re.DOTALL)
        if metadata_match:
            metadata_lines = metadata_match.group(1).split('\n')
            for line in metadata_lines:
                if line.strip().startswith('- **'):
                    key_value = line.strip()[4:].split('**: ')
                    if len(key_value) == 2:
                        key = key_value[0].lower().replace(' ', '_')
                        value = key_value[1]
                        config["metadata"][key] = value
        
        # Extract role
        role_match = re.search(r'### Role\n```\n(.*?)\n```', content, re.DOTALL)
        if role_match:
            config["role"] = role_match.group(1).strip()
        
        # Extract goal  
        goal_match = re.search(r'### Goal\n```\n(.*?)\n```', content, re.DOTALL)
        if goal_match:
            config["goal"] = goal_match.group(1).strip()
        
        # Extract backstory
        backstory_match = re.search(r'### Backstory\n```\n(.*?)\n```', content, re.DOTALL)
        if backstory_match:
            config["backstory"] = backstory_match.group(1).strip()
        
        # Extract tools available
        tools_match = re.search(r'## Tools Available\n(.*?)\n\n', content, re.DOTALL)
        if tools_match:
            tools_text = tools_match.group(1)
            tools = re.findall(r'- `([^`]+)`', tools_text)
            config["tools"] = tools
        
        return config
    
    def _extract_task_prompt_template(self, content: str) -> str:
        """
        Extract the task prompt template from markdown content
        
        Args:
            content: Full markdown content
            
        Returns:
            Task prompt template string
        """
        # Find the start and end of the markdown template block
        start_pattern = r'### Task Prompt Template\n```markdown\n'
        start_match = re.search(start_pattern, content)
        
        if start_match:
            # Find the start position after the opening ```markdown
            start_pos = start_match.end()
            
            # Find ALL ``` occurrences and look for the last one that closes the template
            closing_positions = []
            pos = start_pos
            
            while pos < len(content):
                # Look for next ``` occurrence
                next_code_block = content.find('```', pos)
                if next_code_block == -1:
                    break
                    
                # Check if it's on its own line
                line_start = content.rfind('\n', 0, next_code_block) + 1
                line_end = content.find('\n', next_code_block)
                if line_end == -1:
                    line_end = len(content)
                    
                line_content = content[line_start:line_end]
                
                # If it's just ``` on its own line, it could be a closing block
                if line_content.strip() == '```':
                    closing_positions.append(next_code_block)
                    
                pos = next_code_block + 3
            
            # Use the last closing position (should be the template closing)
            if closing_positions:
                template_end = closing_positions[-1]
                template_content = content[start_pos:template_end].strip()
                logger.info(f"Found {len(closing_positions)} potential closing blocks")
                logger.info(f"Using last closing ``` at position {template_end}")
                logger.info(f"Extracted template length: {len(template_content)}")
                logger.info(f"Template preview: {template_content[:200]}...")
                return template_content
            
        # Fallback patterns (simpler)
        patterns = [
            r'```markdown\n(.*?)\n```'
        ]
        
        for pattern in patterns:
            template_match = re.search(pattern, content, re.DOTALL)
            if template_match:
                template_content = template_match.group(1).strip()
                logger.info(f"Found template in simple code block, length: {len(template_content)}")
                return template_content
        
        # If no template found in code blocks, look for the actual template content
        # Extract everything after "## Analysis Requirements" if it exists
        analysis_match = re.search(r'## Analysis Requirements\n(.*)', content, re.DOTALL)
        if analysis_match:
            template_content = analysis_match.group(1).strip()
            logger.info(f"Using content after ## Analysis Requirements, length: {len(template_content)}")
            return template_content
        
        # Final fallback: return content as-is if it has variables
        if '{' in content and '}' in content:
            logger.info(f"Using full content as template, length: {len(content)}")
            return content
        
        # If no variables found, create a simple template
        logger.warning("No template variables found, using fallback template")
        return """
        Analyze the provided order data for fraud patterns:
        
        Order Data: {order_data}
        Orders Today: {orders_today}
        Account Age: {account_age_days} days
        Amount: ${total_amount}
        
        Provide comprehensive fraud pattern analysis with evidence and confidence scores.
        """
    
    def _substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Substitute variables in template string
        
        Args:
            template: Template string with {variable} placeholders
            variables: Dictionary of variables to substitute
            
        Returns:
            Formatted string with variables substituted
        """
        try:
            # Handle JSON formatting for complex objects
            formatted_vars = {}
            for key, value in variables.items():
                if isinstance(value, (dict, list)):
                    formatted_vars[key] = self._format_json(value)
                elif value is None:
                    formatted_vars[key] = "N/A"
                else:
                    formatted_vars[key] = str(value)
            
            logger.info(f"Substituting variables: {list(formatted_vars.keys())}")
            
            # Manual replacement approach for better control
            result = template
            for key, value in formatted_vars.items():
                placeholder = f"{{{key}}}"
                if placeholder in result:
                    result = result.replace(placeholder, str(value))
                    logger.debug(f"Replaced {placeholder} with {str(value)[:50]}...")
            
            # Verify substitution worked
            remaining_placeholders = len([match for match in re.findall(r'\{[^}]+\}', result)])
            logger.info(f"Substitution complete. Remaining placeholders: {remaining_placeholders}")
            
            return result
                
        except Exception as e:
            logger.error(f"Error in variable substitution: {e}")
            return template
    
    def _format_json(self, obj: Any, indent: int = 2) -> str:
        """Format object as JSON string"""
        try:
            import json
            return json.dumps(obj, indent=indent, ensure_ascii=False)
        except Exception:
            return str(obj)
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent prompt files"""
        agents_dir = self.prompts_dir / "agents"
        if not agents_dir.exists():
            return []
        
        agents = []
        for file_path in agents_dir.glob("*.md"):
            agent_name = file_path.stem
            agents.append(agent_name)
        
        return sorted(agents)
    
    def get_available_tasks(self) -> List[str]:
        """Get list of available task prompt files"""
        tasks_dir = self.prompts_dir / "tasks"
        if not tasks_dir.exists():
            return []
        
        tasks = []
        for file_path in tasks_dir.glob("*.md"):
            task_name = file_path.stem
            tasks.append(task_name)
        
        return sorted(tasks)
    
    def validate_prompts(self) -> Dict[str, Any]:
        """
        Validate all prompt files for correctness
        
        Returns:
            Validation results
        """
        results = {
            "valid": True,
            "agents": {},
            "tasks": {},
            "errors": []
        }
        
        # Validate agent prompts
        for agent_name in self.get_available_agents():
            try:
                config = self.load_agent_prompt(agent_name)
                results["agents"][agent_name] = {
                    "valid": True,
                    "has_role": bool(config.get("role")),
                    "has_goal": bool(config.get("goal")),
                    "has_backstory": bool(config.get("backstory")),
                    "tools_count": len(config.get("tools", []))
                }
            except Exception as e:
                results["valid"] = False
                results["agents"][agent_name] = {
                    "valid": False,
                    "error": str(e)
                }
                results["errors"].append(f"Agent {agent_name}: {e}")
        
        # Validate task prompts
        for task_name in self.get_available_tasks():
            try:
                # Try loading without variables
                content = self.load_task_prompt(task_name)
                results["tasks"][task_name] = {
                    "valid": True,
                    "length": len(content)
                }
            except Exception as e:
                results["valid"] = False
                results["tasks"][task_name] = {
                    "valid": False,
                    "error": str(e)
                }
                results["errors"].append(f"Task {task_name}: {e}")
        
        return results
    
    def clear_cache(self):
        """Clear the prompt cache"""
        self.prompt_cache.clear()
        logger.info("Prompt cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_enabled": self.cache_enabled,
            "cached_items": len(self.prompt_cache),
            "cache_keys": list(self.prompt_cache.keys())
        }