"""Natural language interface for the Agentic Ritual Engine."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from anthropic import Anthropic


@dataclass
class NLCommand:
    """Represents a parsed natural language command."""

    intent: str
    parameters: Dict[str, Any]
    confidence: float
    raw_query: str


class NaturalLanguageInterface:
    """Processes natural language queries and maps them to ritual engine commands."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the natural language interface.

        Args:
            api_key: Anthropic API key. If not provided, will look for ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.conversation_history: List[Dict[str, str]] = []

        # Define available actions and their schemas
        self.available_actions = {
            "search_symbols": {
                "description": "Search for symbols in the knowledge base",
                "parameters": ["query", "tradition", "planet", "element", "deity_or_spirit"],
            },
            "get_context": {
                "description": "Get current celestial/ritual context for a location",
                "parameters": ["latitude", "longitude"],
            },
            "build_flipbook": {
                "description": "Generate an HTML flipbook of symbols",
                "parameters": ["query", "tradition", "output_file"],
            },
            "ingest_sources": {
                "description": "Ingest new ritual sources from manifest",
                "parameters": ["manifest_path"],
            },
            "detect_sigils": {
                "description": "Detect sigils in source materials",
                "parameters": ["source", "min_area", "max_area"],
            },
            "get_symbol_details": {
                "description": "Get detailed information about a specific symbol",
                "parameters": ["symbol_slug"],
            },
            "list_traditions": {
                "description": "List all available traditions in the knowledge base",
                "parameters": [],
            },
            "general_question": {
                "description": "Answer general questions about the ritual engine or occult topics",
                "parameters": ["question"],
            },
        }

    def parse_query(self, query: str) -> NLCommand:
        """Parse a natural language query into a structured command.

        Args:
            query: Natural language query from the user

        Returns:
            Parsed command with intent and parameters
        """
        system_prompt = self._build_system_prompt()

        messages = [
            *self.conversation_history,
            {"role": "user", "content": query}
        ]

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )

        # Extract the response text
        response_text = response.content[0].text

        # Parse JSON response
        try:
            parsed = json.loads(response_text)
            command = NLCommand(
                intent=parsed.get("intent", "general_question"),
                parameters=parsed.get("parameters", {}),
                confidence=parsed.get("confidence", 0.8),
                raw_query=query,
            )
        except json.JSONDecodeError:
            # Fallback to general question if parsing fails
            command = NLCommand(
                intent="general_question",
                parameters={"question": query},
                confidence=0.5,
                raw_query=query,
            )

        return command

    def chat(self, query: str, maintain_context: bool = True) -> Dict[str, Any]:
        """Process a conversational query with optional context maintenance.

        Args:
            query: Natural language query from the user
            maintain_context: Whether to maintain conversation history

        Returns:
            Response dictionary with intent, parameters, and response text
        """
        command = self.parse_query(query)

        if maintain_context:
            self.conversation_history.append({"role": "user", "content": query})

        # Build response based on intent
        response = {
            "intent": command.intent,
            "parameters": command.parameters,
            "confidence": command.confidence,
            "raw_query": query,
        }

        # Generate natural language response
        response_text = self._generate_response(command)
        response["response"] = response_text

        if maintain_context:
            self.conversation_history.append({"role": "assistant", "content": response_text})

        return response

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the LLM."""
        actions_desc = "\n".join([
            f"- {name}: {info['description']}\n  Parameters: {', '.join(info['parameters']) if info['parameters'] else 'none'}"
            for name, info in self.available_actions.items()
        ])

        return f"""You are an AI assistant for the Agentic Ritual Engine, a system for cataloging and exploring ritual symbols, sigils, and esoteric knowledge.

Available actions:
{actions_desc}

Your task is to:
1. Understand the user's natural language query
2. Determine the most appropriate action to take
3. Extract relevant parameters from the query
4. Return a JSON response with the following structure:

{{
  "intent": "action_name",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }},
  "confidence": 0.95
}}

Guidelines:
- For symbol searches, extract tradition, planet, element, deity/spirit names
- For location-based queries, try to extract or use default coordinates (Las Vegas: 36.1699, -115.1398)
- For flipbook requests, extract any filtering criteria
- Use "general_question" intent for questions about the system itself or general occult knowledge
- Be generous with parameter extraction - infer missing values when reasonable
- Return ONLY valid JSON, no additional text

Examples:
User: "Show me all Saturn seals"
Response: {{"intent": "search_symbols", "parameters": {{"planet": "Saturn"}}, "confidence": 0.95}}

User: "What's the current moon phase in Las Vegas?"
Response: {{"intent": "get_context", "parameters": {{"latitude": 36.1699, "longitude": -115.1398}}, "confidence": 0.9}}

User: "Generate a flipbook of Solomonic tradition symbols"
Response: {{"intent": "build_flipbook", "parameters": {{"tradition": "Solomonic"}}, "confidence": 0.95}}

User: "What is this system for?"
Response: {{"intent": "general_question", "parameters": {{"question": "What is this system for?"}}, "confidence": 1.0}}
"""

    def _generate_response(self, command: NLCommand) -> str:
        """Generate a natural language response based on the parsed command.

        Args:
            command: Parsed natural language command

        Returns:
            Natural language response text
        """
        intent = command.intent
        params = command.parameters

        # Build context-aware response
        if intent == "search_symbols":
            filters = []
            if "query" in params:
                filters.append(f"query: {params['query']}")
            if "tradition" in params:
                filters.append(f"tradition: {params['tradition']}")
            if "planet" in params:
                filters.append(f"planet: {params['planet']}")
            if "element" in params:
                filters.append(f"element: {params['element']}")
            if "deity_or_spirit" in params:
                filters.append(f"deity/spirit: {params['deity_or_spirit']}")

            filter_desc = ", ".join(filters) if filters else "all symbols"
            return f"Searching for symbols with {filter_desc}. Use the REST API at /symbols?{self._build_query_string(params)} or CLI to retrieve results."

        elif intent == "get_context":
            lat = params.get("latitude", 36.1699)
            lon = params.get("longitude", -115.1398)
            return f"Calculating celestial context for coordinates ({lat}, {lon}). Use /context?lat={lat}&lon={lon} to retrieve the current moon phase, planetary hour, and solar data."

        elif intent == "build_flipbook":
            filter_desc = params.get("tradition", "all symbols")
            output = params.get("output_file", "flipbook.html")
            return f"Generating flipbook for {filter_desc}. Output will be saved to {output}. Use CLI: python -m agentic_ritual_engine.main make-flipbook --filter '{{\"tradition\": \"{params.get('tradition', '')}\"}}'"

        elif intent == "get_symbol_details":
            slug = params.get("symbol_slug", "")
            return f"Retrieving details for symbol '{slug}'. Use /symbols/{slug} endpoint to get full metadata, images, and source information."

        elif intent == "list_traditions":
            return "To list all traditions, query the /symbols endpoint and aggregate unique tradition values, or use the Streamlit dashboard for interactive browsing."

        elif intent == "ingest_sources":
            manifest = params.get("manifest_path", "data/sources.yaml")
            return f"To ingest sources from {manifest}, use CLI: python -m agentic_ritual_engine.main ingest-sources --from {manifest}"

        elif intent == "detect_sigils":
            source = params.get("source", "")
            return f"To detect sigils in source '{source}', use CLI: python -m agentic_ritual_engine.main detect-sigils --source {source}"

        else:
            # General question - provide helpful context
            question = params.get("question", command.raw_query)
            return self._answer_general_question(question)

    def _answer_general_question(self, question: str) -> str:
        """Answer general questions about the system using the LLM.

        Args:
            question: The user's question

        Returns:
            Natural language answer
        """
        context = """The Agentic Ritual Engine is a system for cataloging and exploring ritual symbols, sigils, and esoteric knowledge from various traditions including:
- Solomonic grimoires
- Enochian archives
- Renaissance occult philosophy
- Kabbalistic currents
- Folk and magical practices

It provides:
- PDF ingestion and sigil detection
- Image cleaning and processing
- SQLite-based symbol knowledge base
- REST API for programmatic access
- Streamlit dashboard for interactive exploration
- Celestial context calculation (moon phases, planetary hours)
- HTML flipbook generation
- Command-line interface for all operations

The system is designed for scholars, practitioners, and researchers working with historical magical texts and symbols."""

        messages = [
            {"role": "user", "content": f"Context about the system:\n{context}\n\nUser question: {question}\n\nProvide a helpful, concise answer."}
        ]

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=512,
            messages=messages,
        )

        return response.content[0].text

    def _build_query_string(self, params: Dict[str, Any]) -> str:
        """Build a URL query string from parameters.

        Args:
            params: Parameter dictionary

        Returns:
            URL query string
        """
        parts = []
        for key, value in params.items():
            if key == "tradition" or key == "planet" or key == "element" or key == "deity_or_spirit":
                parts.append(f'filters={{"{ key}": "{value}"}}')
            elif key == "query":
                parts.append(f"query={value}")
        return "&".join(parts) if parts else ""

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.conversation_history = []


def create_nl_interface(api_key: Optional[str] = None) -> NaturalLanguageInterface:
    """Factory function to create a natural language interface.

    Args:
        api_key: Optional Anthropic API key

    Returns:
        Configured NaturalLanguageInterface instance
    """
    return NaturalLanguageInterface(api_key=api_key)
