#!/usr/bin/env python3
"""
Template script for rendering Graphviz DOT notation to PNG images.
This script receives a Graphviz DOT string and renders it to output.png.
"""

import os
import sys
from graphviz import Source

def render_graphviz(dot_content, output_path="output"):
    """
    Render Graphviz DOT content to PNG format.
    
    Args:
        dot_content (str): The Graphviz DOT notation string
        output_path (str): Output filename without extension (default: "output")
    """
    try:
        # Create a Graphviz Source object from the DOT content
        graph = Source(dot_content)
        
        # Render to PNG format
        graph.render(output_path, format='png', cleanup=True)
        
        print(f"Graphviz rendering completed successfully: {output_path}.png")
        return True
        
    except Exception as e:
        print(f"Error rendering Graphviz: {str(e)}")
        return False

if __name__ == "__main__":
    # The DOT content will be replaced by the template substitution
    dot_content = """{{GRAPHVIZ_CONTENT}}"""
    
    # Render the graph
    success = render_graphviz(dot_content)
    
    if not success:
        sys.exit(1)