"""
Highway Segmentation GA - Analysis Method Plugins Package

This package contains self-contained plugins for different optimization methods.
Each plugin is responsible for extracting method-specific statistics and 
contributing specialized analysis to JSON output.

Plugin Architecture Benefits:
- Self-contained: Each method completely encapsulated in its own file
- Extensible: New methods can be added without modifying core system
- Independent: Plugins can be developed, tested, and versioned separately  
- Optional: Plugins are loaded on-demand based on method requirements
- Third-party friendly: External developers can create plugins

Available Plugins:
- single_objective_plugin.py: Single-objective GA optimization methods
- multi_objective_plugin.py: Multi-objective (NSGA-II) optimization methods  
- constrained_plugin.py: Constraint-aware optimization methods
- custom_plugin_template.py: Template for creating new method plugins

Plugin Discovery:
The system automatically discovers and loads plugins from this directory.
Each plugin should implement AnalysisMethodPlugin interface and provide
PLUGIN_METADATA for discovery.

Usage:
    # Plugins are auto-discovered and registered
    from plugins import discover_plugins
    discover_plugins()
    
    # Or manual plugin loading
    from plugins.single_objective_plugin import SingleObjectivePlugin
    registry.register_plugin(SingleObjectivePlugin())

Author: Highway Segmentation GA Team  
Date: April 2026
"""

import os
import importlib.util
import logging
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from extensible_results_manager import AnalysisMethodPlugin

logger = logging.getLogger(__name__)

def discover_plugins() -> List['AnalysisMethodPlugin']:
    """
    Automatically discover and load plugins from the plugins directory.
    
    Scans for Python files in the plugins directory, imports them, and
    attempts to extract plugin classes that implement AnalysisMethodPlugin.
    
    Returns:
        List of discovered plugin instances ready for registration
    """
    plugins = []
    plugin_dir = os.path.dirname(__file__)
    
    # Scan for Python plugin files
    for filename in os.listdir(plugin_dir):
        if filename.endswith('_plugin.py') and not filename.startswith('__'):
            plugin_name = filename[:-3]  # Remove .py extension
            
            try:
                # Dynamic import of plugin module
                plugin_path = os.path.join(plugin_dir, filename)
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Try to get plugin class
                    if hasattr(module, 'get_plugin_class'):
                        plugin_class = module.get_plugin_class()
                        plugin_instance = plugin_class()
                        plugins.append(plugin_instance)
                        logger.info("Discovered plugin: %s", plugin_class.__name__)
                        
                    elif hasattr(module, 'PLUGIN_METADATA'):
                        metadata = module.PLUGIN_METADATA
                        if 'plugin_class' in metadata:
                            plugin_class = metadata['plugin_class']
                            plugin_instance = plugin_class()
                            plugins.append(plugin_instance)
                            logger.info("Discovered plugin via metadata: %s", plugin_class.__name__)
                            
            except Exception as e:
                logger.warning("Could not load plugin %s: %s", filename, e)
    
    return plugins


def get_available_plugins() -> Dict[str, Dict[str, Any]]:
    """
    Get metadata about all available plugins without loading them.
    
    Returns:
        Dict mapping plugin names to their metadata
    """
    plugins_info = {}
    plugin_dir = os.path.dirname(__file__)
    
    for filename in os.listdir(plugin_dir):
        if filename.endswith('_plugin.py') and not filename.startswith('__'):
            plugin_name = filename[:-3]
            
            try:
                # Import just to get metadata
                plugin_path = os.path.join(plugin_dir, filename) 
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'PLUGIN_METADATA'):
                        plugins_info[plugin_name] = module.PLUGIN_METADATA
                        
            except Exception as e:
                logger.warning("Could not read plugin metadata %s: %s", filename, e)
    
    return plugins_info


# Export discovery functions
__all__ = ['discover_plugins', 'get_available_plugins']