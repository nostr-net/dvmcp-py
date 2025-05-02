"""
Prompts implementation for DVMCP

This module provides base classes and utilities for implementing MCP prompts.
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable, List, Union

from dvmcp.logging import get_logger
from dvmcp.models.capabilities import Prompt, PromptArgument

logger = get_logger("capabilities.prompts")

class PromptRegistry:
    """Registry for prompt implementations"""
    
    def __init__(self):
        """Initialize prompt registry"""
        self.prompts: Dict[str, 'PromptImplementation'] = {}
    
    def register(self, prompt_impl: 'PromptImplementation') -> None:
        """
        Register a prompt implementation
        
        Args:
            prompt_impl: Prompt implementation to register
        """
        self.prompts[prompt_impl.prompt.name] = prompt_impl
        logger.debug(f"Registered prompt: {prompt_impl.prompt.name}")
    
    def get(self, name: str) -> Optional['PromptImplementation']:
        """
        Get prompt implementation by name
        
        Args:
            name: Prompt name
            
        Returns:
            Prompt implementation or None if not found
        """
        return self.prompts.get(name)
    
    def list_prompts(self) -> List[Prompt]:
        """
        Get list of all registered prompts
        
        Returns:
            List of prompt definitions
        """
        return [impl.prompt for impl in self.prompts.values()]

class PromptImplementation:
    """Base class for prompt implementations"""
    
    def __init__(self, prompt: Prompt):
        """
        Initialize prompt implementation
        
        Args:
            prompt: Prompt definition
        """
        self.prompt = prompt
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute prompt with arguments
        
        Args:
            arguments: Prompt arguments
            
        Returns:
            Prompt execution result
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Prompt execution not implemented")
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """
        Validate prompt arguments
        
        Args:
            arguments: Prompt arguments
            
        Raises:
            ValueError: If arguments are invalid
        """
        # Check required arguments
        for arg in self.prompt.arguments:
            if arg.required and arg.name not in arguments:
                raise ValueError(f"Missing required argument: {arg.name}")

class WeatherReportPrompt(PromptImplementation):
    """Example weather report prompt implementation"""
    
    def __init__(self):
        """Initialize weather report prompt"""
        super().__init__(Prompt(
            name="weather-report",
            description="Generate a weather report",
            arguments=[
                PromptArgument(
                    name="location",
                    description="Location for the weather report",
                    required=True
                ),
                PromptArgument(
                    name="days",
                    description="Number of days for the forecast",
                    required=False
                )
            ]
        ))
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a weather report
        
        Args:
            arguments: Prompt arguments with location and optional days
            
        Returns:
            Generated weather report
        """
        self.validate_arguments(arguments)
        
        location = arguments["location"]
        days = arguments.get("days", 1)
        
        logger.debug(f"Generating weather report for {location} ({days} days)")
        
        # In a real implementation, this would call a weather API
        # For this example, we'll generate a mock report
        
        # Mock weather data
        weather_types = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Thunderstorms"]
        import random
        
        # Generate forecast for each day
        forecast = []
        for i in range(int(days)):
            forecast.append({
                "day": i + 1,
                "weather": random.choice(weather_types),
                "temperature": {
                    "min": random.randint(10, 20),
                    "max": random.randint(21, 35)
                },
                "precipitation": random.randint(0, 100),
                "wind": random.randint(0, 30)
            })
        
        # Generate report text
        report_text = f"Weather Report for {location}:\n\n"
        
        for day in forecast:
            report_text += f"Day {day['day']}: {day['weather']}\n"
            report_text += f"  Temperature: {day['temperature']['min']}°C to {day['temperature']['max']}°C\n"
            report_text += f"  Precipitation: {day['precipitation']}%\n"
            report_text += f"  Wind: {day['wind']} km/h\n\n"
        
        return {
            "report": report_text,
            "forecast": forecast
        }

class CodeReviewPrompt(PromptImplementation):
    """Example code review prompt implementation"""
    
    def __init__(self):
        """Initialize code review prompt"""
        super().__init__(Prompt(
            name="code-review",
            description="Review code for issues",
            arguments=[
                PromptArgument(
                    name="code",
                    description="Code to review",
                    required=True
                ),
                PromptArgument(
                    name="language",
                    description="Programming language",
                    required=True
                )
            ]
        ))
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review code for issues
        
        Args:
            arguments: Prompt arguments with code and language
            
        Returns:
            Code review results
        """
        self.validate_arguments(arguments)
        
        code = arguments["code"]
        language = arguments["language"]
        
        logger.debug(f"Reviewing {language} code ({len(code)} chars)")
        
        # In a real implementation, this would use a code analysis tool or LLM
        # For this example, we'll do some basic checks
        
        issues = []
        
        # Check for common issues
        if "TODO" in code:
            issues.append({
                "type": "todo",
                "message": "TODO comments found in code",
                "severity": "info"
            })
        
        if "print(" in code and language.lower() in ["python", "py"]:
            issues.append({
                "type": "debugging",
                "message": "Print statements found in code",
                "severity": "warning"
            })
        
        if "catch (Exception" in code and language.lower() in ["java", "c#", "csharp"]:
            issues.append({
                "type": "error-handling",
                "message": "Catching generic Exception is not recommended",
                "severity": "warning"
            })
        
        # Generate review text
        review_text = f"Code Review for {language} code:\n\n"
        
        if issues:
            review_text += f"Found {len(issues)} issues:\n\n"
            
            for i, issue in enumerate(issues):
                review_text += f"{i+1}. [{issue['severity'].upper()}] {issue['message']}\n"
        else:
            review_text += "No issues found. Good job!\n"
        
        return {
            "review": review_text,
            "issues": issues,
            "issue_count": len(issues)
        }

# Create global prompt registry
registry = PromptRegistry()

# Register built-in prompts
registry.register(WeatherReportPrompt())
registry.register(CodeReviewPrompt())