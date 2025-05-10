"""Manages a library of prompt templates for AILF agents."""

import json
import os
from typing import Any, Dict, Optional, List

from ailf.schemas.prompt_engineering import PromptTemplateV1, PromptLibraryConfig

class PromptLibrary:
    """
    Manages loading, storing, and accessing versioned prompt templates.
    Templates can be loaded from a directory of JSON files or potentially other sources.
    """

    def __init__(self, config: PromptLibraryConfig):
        """
        Initializes the PromptLibrary.

        :param config: Configuration for the prompt library, including the path to template files.
        :type config: PromptLibraryConfig
        """
        self.config = config
        self._templates: Dict[str, PromptTemplateV1] = {}
        self._load_library()

    def _load_library(self) -> None:
        """
        Loads prompt templates from the configured source (e.g., directory).
        Currently supports loading from a directory of JSON files.
        Each JSON file should represent a PromptTemplateV1 schema.
        The filename (without .json) is used as the template_id if not present in the file.
        """
        if not self.config.library_path or not os.path.isdir(self.config.library_path):
            print(f"Warning: Prompt library path '{self.config.library_path}' is not a valid directory. No templates loaded.")
            return

        print(f"Loading prompt templates from: {self.config.library_path}")
        for filename in os.listdir(self.config.library_path):
            if filename.endswith(".json"):
                filepath = os.path.join(self.config.library_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        template_data = json.load(f)
                    
                    # Ensure template_id is present, using filename if necessary
                    if 'template_id' not in template_data:
                        template_data['template_id'] = filename[:-5] # Remove .json
                    
                    template = PromptTemplateV1(**template_data)
                    self.add_template(template, overwrite=True) # Overwrite if loaded template is newer or same
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from {filepath}: {e}")
                except Exception as e: # Catch Pydantic validation errors or other issues
                    print(f"Error loading template from {filepath}: {e}")
        print(f"Loaded {len(self._templates)} prompt templates.")

    def add_template(self, template: PromptTemplateV1, overwrite: bool = False) -> None:
        """
        Adds a new prompt template to the library or updates an existing one.
        If a template with the same id already exists, it's only updated if the new
        template has a higher version or if overwrite is True.

        :param template: The PromptTemplateV1 object to add.
        :type template: PromptTemplateV1
        :param overwrite: If True, always overwrite an existing template with the same ID,
                          regardless of version. Defaults to False.
        :type overwrite: bool
        """
        if template.template_id in self._templates:
            existing_template = self._templates[template.template_id]
            if overwrite or template.version > existing_template.version:
                self._templates[template.template_id] = template
                print(f"Updated template '{template.template_id}' to version {template.version}.")
            elif template.version < existing_template.version:
                print(f"Skipped adding template '{template.template_id}' version {template.version} (older than existing version {existing_template.version}).")
            else: # Same version, not overwriting
                print(f"Skipped adding template '{template.template_id}' version {template.version} (same as existing, overwrite=False).")
        else:
            self._templates[template.template_id] = template
            print(f"Added new template '{template.template_id}' version {template.version}.")

    def get_template(self, template_id: str, version: Optional[int] = None) -> Optional[PromptTemplateV1]:
        """
        Retrieves a specific prompt template by its ID and optionally by version.
        If version is not specified, it returns the latest version of the template.
        (Currently, only one version per ID is stored, so version parameter is for future use).

        :param template_id: The ID of the prompt template to retrieve.
        :type template_id: str
        :param version: The specific version of the template (currently not fully implemented for multiple versions).
        :type version: Optional[int]
        :return: The PromptTemplateV1 object if found, otherwise None.
        :rtype: Optional[PromptTemplateV1]
        """
        # Current implementation stores only one version (latest or explicitly added).
        # Version parameter is a placeholder for future multi-version support.
        if version is not None:
            # This part would need enhancement if multiple versions per ID are stored.
            # For now, it checks if the stored version matches the requested one.
            template = self._templates.get(template_id)
            if template and template.version == version:
                return template
            elif template: # Template exists but version mismatch
                print(f"Template '{template_id}' found, but version {template.version} does not match requested version {version}.")
                return None 
            return None # Template ID not found
        
        return self._templates.get(template_id)

    def get_default_template(self) -> Optional[PromptTemplateV1]:
        """
        Retrieves the default prompt template specified in the library configuration.

        :return: The default PromptTemplateV1 object if configured and found, otherwise None.
        :rtype: Optional[PromptTemplateV1]
        """
        if self.config.default_prompt_id:
            return self.get_template(self.config.default_prompt_id)
        return None

    def list_template_ids(self) -> List[str]:
        """
        Lists the IDs of all available prompt templates in the library.

        :return: A list of template IDs.
        :rtype: List[str]
        """
        return list(self._templates.keys())

# Example Usage (Illustrative - requires a directory with JSON template files)
# async def example_prompt_library_usage():
#     # 1. Create a dummy template file (e.g., /tmp/prompts/greeting_v1.json)
#     prompts_dir = "/tmp/ailf_prompts_example"
#     os.makedirs(prompts_dir, exist_ok=True)
#     greeting_template_content = {
#         "template_id": "greeting_simple_v1",
#         "version": 1,
#         "description": "A simple greeting prompt.",
#         "user_prompt_template": "Hello, {name}! How are you today?",
#         "placeholders": ["name"],
#         "tags": ["greeting"],
#         "expected_output_schema_name": "SimpleResponse"
#     }
#     with open(os.path.join(prompts_dir, "greeting_simple_v1.json"), 'w') as f:
#         json.dump(greeting_template_content, f, indent=2)

#     # 2. Configure and initialize the PromptLibrary
#     config = PromptLibraryConfig(library_path=prompts_dir, default_prompt_id="greeting_simple_v1")
#     library = PromptLibrary(config)

#     # 3. List available templates
#     print(f"\nAvailable templates: {library.list_template_ids()}")

#     # 4. Get a specific template
#     retrieved_template = library.get_template("greeting_simple_v1")
#     if retrieved_template:
#         print(f"\nRetrieved template '{retrieved_template.template_id}' (v{retrieved_template.version}):")
#         print(f"  Description: {retrieved_template.description}")
#         print(f"  User Prompt Template: {retrieved_template.user_prompt_template}")
        
#         # 5. Fill the template
#         try:
#             filled_prompt = retrieved_template.fill(name="Alice")
#             print(f"  Filled prompt: {filled_prompt}")
#         except KeyError as e:
#             print(f"  Error filling template: {e}")
#     else:
#         print("\nTemplate 'greeting_simple_v1' not found.")

#     # 6. Get the default template
#     default_temp = library.get_default_template()
#     if default_temp:
#         print(f"\nDefault template is '{default_temp.template_id}'. Filled: {default_temp.fill(name='Bob')}")
    
#     # Clean up dummy directory (optional)
#     # import shutil
#     # shutil.rmtree(prompts_dir)

# if __name__ == "__main__":
#     # asyncio.run(example_prompt_library_usage()) # Commented out
#     pass
