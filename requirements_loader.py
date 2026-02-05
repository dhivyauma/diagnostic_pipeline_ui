# requirements_loader.py
import json
import os
from typing import Dict, Any, Optional
from enum import Enum


class ModelType(str, Enum):
    PD = "PD"
    LGD = "LGD"
    EAD = "EAD"


class Purpose(str, Enum):
    IFRS9 = "IFRS9"
    AIRB = "AIRB"
    ADJUDICATION = "Adjudication"


class RequirementsLoader:
    """
    Step 2 - Diagnostic Context Lookup
    
    Responsible for determining the mandatory modeling inputs required for a given 
    model configuration selected in Step 1.
    """
    
    def __init__(self, requirements_file_path: str = "requirements_context.json"):
        """
        Initialize the RequirementsLoader with the path to the requirements context file.
        
        Args:
            requirements_file_path: Path to the requirements_context.json file
        """
        self.requirements_file_path = requirements_file_path
        self._requirements_cache: Optional[Dict[str, Any]] = None
    
    def _load_requirements_file(self) -> Dict[str, Any]:
        """
        Load and parse the requirements context file from disk.
        
        Returns:
            Dict containing the parsed requirements context
            
        Raises:
            FileNotFoundError: If the requirements file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        if self._requirements_cache is not None:
            return self._requirements_cache
        
        if not os.path.exists(self.requirements_file_path):
            raise FileNotFoundError(
                f"Requirements context file not found: {self.requirements_file_path}"
            )
        
        try:
            with open(self.requirements_file_path, 'r', encoding='utf-8') as file:
                self._requirements_cache = json.load(file)
                return self._requirements_cache
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in requirements file: {self.requirements_file_path}",
                e.doc,
                e.pos
            )
    
    def _build_lookup_key(self, purpose: str, model_type: str) -> str:
        """
        Build the lookup key for the requirements context file.
        
        Args:
            purpose: The selected purpose (e.g., "AIRB", "IFRS9")
            model_type: The selected model type (e.g., "PD", "LGD")
            
        Returns:
            String representing the lookup key in format: {PURPOSE}_{MODEL_TYPE}_Requirements
        """
        # Normalize inputs to match the enum values
        # Handle display formatting like "AIRB (Advanced Internal Ratings-Based)" -> "AIRB"
        purpose_normalized = purpose.upper().split(" ")[0].split("(")[0].strip()
        model_type_normalized = model_type.upper().split(" ")[0].split("(")[0].strip()
        
        # Special case: "IFRS 9" should become "IFRS9"
        if purpose_normalized == "IFRS":
            purpose_normalized = "IFRS9"
        
        return f"{purpose_normalized}_{model_type_normalized}_Requirements"
    
    def get_active_requirements(self, purpose: str, model_type: str) -> Dict[str, Any]:
        """
        Extract active requirements for the given model configuration.
        
        Args:
            purpose: The selected purpose (e.g., "AIRB", "IFRS9")
            model_type: The selected model type (e.g., "PD", "LGD")
            
        Returns:
            Dictionary containing the active requirements for the session
            
        Raises:
            ValueError: If no requirements are defined for the selected configuration
        """
        # Step 1: Build lookup key
        lookup_key = self._build_lookup_key(purpose, model_type)
        
        # Step 2: Load and parse the context file
        requirements_data = self._load_requirements_file()
        
        # Step 3: Extract active requirements
        if lookup_key not in requirements_data:
            available_keys = list(requirements_data.keys())
            raise ValueError(
                f"No requirements defined for configuration: {lookup_key}\n"
                f"Available configurations: {available_keys}"
            )
        
        active_requirements = requirements_data[lookup_key]
        
        # Convert mandatory strings to boolean for consistency
        for field_name, field_config in active_requirements.items():
            if isinstance(field_config, dict) and 'mandatory' in field_config:
                if isinstance(field_config['mandatory'], str):
                    field_config['mandatory'] = field_config['mandatory'].lower() == 'true'
        
        return active_requirements
    
    def validate_configuration(self, purpose: str, model_type: str) -> bool:
        """
        Validate that a configuration has defined requirements.
        
        Args:
            purpose: The selected purpose
            model_type: The selected model type
            
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            lookup_key = self._build_lookup_key(purpose, model_type)
            requirements_data = self._load_requirements_file()
            return lookup_key in requirements_data
        except (FileNotFoundError, json.JSONDecodeError):
            return False
    
    def get_available_configurations(self) -> Dict[str, Dict[str, str]]:
        """
        Get all available configurations from the requirements file.
        
        Returns:
            Dictionary mapping configuration keys to their parsed components
        """
        try:
            requirements_data = self._load_requirements_file()
            configurations = {}
            
            for key in requirements_data.keys():
                if key.endswith("_Requirements"):
                    # Parse the key to extract purpose and model_type
                    parts = key[:-12].split("_")  # Remove "_Requirements" suffix
                    if len(parts) >= 2:
                        purpose = parts[0]
                        model_type = parts[1]  # Take only the second part for simple model types
                        # Handle cases where there might be more parts (unlikely for current setup)
                        if len(parts) > 2:
                            # If there are more parts, join them with underscore
                            model_type = "_".join(parts[1:])
                        
                        # Clean up any trailing underscores
                        model_type = model_type.rstrip("_")
                        
                        configurations[key] = {
                            "purpose": purpose,
                            "model_type": model_type
                        }
            
            return configurations
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def clear_cache(self):
        """Clear the internal requirements cache."""
        self._requirements_cache = None
