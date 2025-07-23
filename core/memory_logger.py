"""
Memory logger module for managing agent memories and insights.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import random

class Memory:
    """Represents a single memory entry."""
    def __init__(self, content: str, importance: float, timestamp: Optional[str] = None):
        self.content = content
        self.importance = importance
        self.timestamp = timestamp or datetime.now().isoformat()
        self.references = 0  # How often this memory is accessed
        
    def to_dict(self) -> Dict:
        """Convert memory to dictionary."""
        return {
            "content": self.content,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "references": self.references
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'Memory':
        """Create memory from dictionary."""
        memory = cls(
            content=data["content"],
            importance=data["importance"],
            timestamp=data["timestamp"]
        )
        memory.references = data.get("references", 0)
        return memory

class MemoryLogger:
    """Manages agent memories and insights."""
    
    def __init__(self, agent_name: str, max_memories: int = 100):
        self.agent_name = agent_name
        self.max_memories = max_memories
        self.memories: List[Memory] = []
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Load existing memories
        self._load_memories()
        
    def _get_memory_file(self) -> Path:
        """Get the memory file path for this agent."""
        return self.logs_dir / f"{self.agent_name}_memories.json"
        
    def _load_memories(self) -> None:
        """Load memories from file."""
        memory_file = self._get_memory_file()
        if memory_file.exists():
            try:
                with open(memory_file, 'r') as f:
                    data = json.load(f)
                    self.memories = [Memory.from_dict(m) for m in data]
            except Exception as e:
                print(f"Error loading memories for {self.agent_name}: {e}")
                
    def _save_memories(self) -> None:
        """Save memories to file."""
        memory_file = self._get_memory_file()
        try:
            with open(memory_file, 'w') as f:
                json.dump([m.to_dict() for m in self.memories], f, indent=2)
        except Exception as e:
            print(f"Error saving memories for {self.agent_name}: {e}")
            
    def add_memory(self, content: str, importance: float) -> None:
        """Add a new memory."""
        memory = Memory(content, importance)
        self.memories.append(memory)
        
        # Curate memories if we exceed the limit
        if len(self.memories) > self.max_memories:
            self._curate_memories()
            
        self._save_memories()
        
    def _curate_memories(self) -> None:
        """Curate memories based on importance and references."""
        # Calculate memory scores
        scored_memories = []
        for memory in self.memories:
            # Score based on importance, recency, and references
            age = (datetime.now() - datetime.fromisoformat(memory.timestamp)).total_seconds()
            age_factor = 1.0 / (1 + age/86400)  # Decay over days
            score = memory.importance * (1 + memory.references/10) * age_factor
            scored_memories.append((memory, score))
            
        # Keep top memories
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        self.memories = [m for m, _ in scored_memories[:self.max_memories]]
        
    def get_relevant_memories(self, context: Dict, limit: int = 5) -> List[Memory]:
        """Get memories relevant to the current context."""
        relevant_memories = []
        
        # Extract key information from context
        strike_price = context.get("strike_price")
        spot_price = context.get("spot_price")
        recent_success = context.get("recent_success", False)
        
        for memory in self.memories:
            relevance = 0.0
            
            # Check if memory mentions similar prices
            if str(strike_price) in memory.content:
                relevance += 0.3
            if str(spot_price) in memory.content:
                relevance += 0.2
                
            # Success/failure context
            if recent_success and "success" in memory.content.lower():
                relevance += 0.2
            elif not recent_success and "fail" in memory.content.lower():
                relevance += 0.2
                
            # Add some randomness for exploration
            relevance += random.random() * 0.1
            
            if relevance > 0:
                relevant_memories.append((memory, relevance))
                memory.references += 1
                
        # Sort by relevance and return top memories
        relevant_memories.sort(key=lambda x: x[1], reverse=True)
        selected_memories = [m for m, _ in relevant_memories[:limit]]
        
        # Save updated reference counts
        self._save_memories()
        
        return selected_memories
        
    def summarize_insights(self) -> str:
        """Generate a summary of key insights from memories."""
        if not self.memories:
            return "No memories collected yet."
            
        # Group memories by importance
        high_importance = []
        medium_importance = []
        low_importance = []
        
        for memory in self.memories:
            if memory.importance >= 0.8:
                high_importance.append(memory)
            elif memory.importance >= 0.5:
                medium_importance.append(memory)
            else:
                low_importance.append(memory)
                
        # Generate summary
        summary = []
        summary.append(f"Agent {self.agent_name} Insights:")
        
        if high_importance:
            summary.append("\nKey Learnings:")
            for memory in sorted(high_importance, key=lambda m: m.references, reverse=True)[:3]:
                summary.append(f"- {memory.content} (referenced {memory.references} times)")
                
        if medium_importance:
            summary.append("\nUseful Patterns:")
            for memory in sorted(medium_importance, key=lambda m: m.references, reverse=True)[:3]:
                summary.append(f"- {memory.content}")
                
        return "\n".join(summary) 