# Enterprise ERP — Plugin System
# ================================
#
# Place your custom plugins in this directory.
#
# Each plugin should be a Python package (directory with __init__.py)
# or a single Python file that contains a class inheriting from
# ``src.core.plugin_manager.PluginBase``.
#
# Example plugin structure:
#
#     plugins/
#     └── my_plugin/
#         ├── __init__.py      # Must contain a class inheriting PluginBase
#         └── views.py         # Optional additional files
#
# Example plugin code (plugins/my_plugin/__init__.py):
#
#     from src.core.plugin_manager import PluginBase
#
#     class MyPlugin(PluginBase):
#         name = "My Plugin"
#         version = "1.0.0"
#         description = "A sample plugin"
#
#         def activate(self, app):
#             print(f"{self.name} activated!")
#
#         def deactivate(self):
#             print(f"{self.name} deactivated!")
#
#         def get_menu_items(self):
#             return []
#
#         def get_api_routes(self):
#             return []
