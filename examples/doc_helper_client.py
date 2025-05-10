#!/usr/bin/env python3
"""
Documentation Helper Client Example

This example demonstrates how to use the Documentation Helper MCP server
to get structured documentation for Python objects.
"""

import asyncio
from pprint import pprint

from ailf.documentation import get_documentation  # Changed from ailf import get_documentation
from ailf.base_mcp import Context


async def main():
    """Run the documentation helper client example."""
    print("Documentation Helper Client Example")
    print("==================================")
    
    # Create a simple context
    ctx = Context(None)
    
    # Example objects to document
    objects_to_document = [
        "json",
        "json.dumps",
        "os.path",
        "asyncio.gather"
    ]
    
    for obj_name in objects_to_document:
        print(f"\nGetting documentation for: {obj_name}")
        print("-" * 40)
        
        # Get documentation
        doc = await get_documentation(ctx, obj_name)
        
        # Print the structured documentation
        print(f"Object: {doc.object_name} ({doc.object_type})")
        print(f"Summary: {doc.summary}")
        
        if doc.signature:
            print(f"\nSignature: {doc.signature}")
        
        if doc.methods:
            print("\nMethods:")
            for method in doc.methods[:5]:  # Show only first 5 methods
                print(f"  - {method}")
            
            if len(doc.methods) > 5:
                print(f"  ... and {len(doc.methods) - 5} more")
        
        if doc.attributes:
            print("\nAttributes:")
            attrs = list(doc.attributes.items())[:5]  # Show only first 5 attributes
            for name, value in attrs:
                print(f"  - {name}: {value}")
            
            if len(doc.attributes) > 5:
                print(f"  ... and {len(doc.attributes) - 5} more")
        
        print("\n" + "=" * 40)


if __name__ == "__main__":
    asyncio.run(main())