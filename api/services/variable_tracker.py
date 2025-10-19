# api/services/variable_tracker.py (NEW FILE)

"""
Variable history tracking for enhanced debugging.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List
import time


@dataclass
class VariableSnapshot:
    """Single snapshot of a variable's state."""
    line_number: int
    variable_name: str
    value: Any
    value_str: str
    type_name: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class VariableChange:
    """Represents a change in a variable's value."""
    line_number: int
    variable_name: str
    old_value: str
    new_value: str
    old_type: str
    new_type: str


class VariableTracker:
    """
    Track variable changes throughout code execution.
    
    Features:
    - Line-by-line variable state capture
    - Change detection
    - History tracking
    - Visualization data generation
    """
    
    def __init__(self):
        self.snapshots: List[VariableSnapshot] = []
        self.changes: List[VariableChange] = []
        self._previous_state: Dict[str, Any] = {}
    
    def track_line(self, line_number: int, variables: Dict[str, Any]):
        """
        Track variable state after executing a line.
        
        Args:
            line_number: Current line number
            variables: Current variable state (locals)
        """
        for var_name, value in variables.items():
            # Skip internal variables
            if var_name.startswith('_'):
                continue
            
            # Create snapshot
            snapshot = VariableSnapshot(
                line_number=line_number,
                variable_name=var_name,
                value=value,
                value_str=str(value),
                type_name=type(value).__name__
            )
            self.snapshots.append(snapshot)
            
            # Detect changes
            if var_name in self._previous_state:
                old_value = self._previous_state[var_name]
                if old_value != value:
                    change = VariableChange(
                        line_number=line_number,
                        variable_name=var_name,
                        old_value=str(old_value),
                        new_value=str(value),
                        old_type=type(old_value).__name__,
                        new_type=type(value).__name__
                    )
                    self.changes.append(change)
            
            # Update previous state
            self._previous_state[var_name] = value
    
    def get_variable_history(self, var_name: str) -> List[VariableSnapshot]:
        """Get all snapshots for a specific variable."""
        return [s for s in self.snapshots if s.variable_name == var_name]
    
    def get_variable_at_line(self, line_number: int) -> Dict[str, str]:
        """Get all variables at a specific line."""
        result = {}
        for snapshot in self.snapshots:
            if snapshot.line_number == line_number:
                result[snapshot.variable_name] = snapshot.value_str
        return result
    
    def get_changes_summary(self) -> Dict[str, List[Dict]]:
        """Get summary of all variable changes."""
        summary = {}
        for change in self.changes:
            if change.variable_name not in summary:
                summary[change.variable_name] = []
            summary[change.variable_name].append({
                'line': change.line_number,
                'old': change.old_value,
                'new': change.new_value,
                'old_type': change.old_type,
                'new_type': change.new_type
            })
        return summary
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return {
            'snapshots': [
                {
                    'line': s.line_number,
                    'variable': s.variable_name,
                    'value': s.value_str,
                    'type': s.type_name,
                    'timestamp': s.timestamp
                }
                for s in self.snapshots
            ],
            'changes': [
                {
                    'line': c.line_number,
                    'variable': c.variable_name,
                    'old': c.old_value,
                    'new': c.new_value,
                    'type_change': c.old_type != c.new_type
                }
                for c in self.changes
            ],
            'summary': self.get_changes_summary()
        }
