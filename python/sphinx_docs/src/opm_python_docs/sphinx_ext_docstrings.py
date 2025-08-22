"""
OPM Sphinx Documentation Extension

This Sphinx extension automatically generates Python API documentation from JSON docstring files.
It provides custom directives that convert JSON configurations into reStructuredText for Sphinx.

Integration with Sphinx:
- Loaded in docs/conf.py: extensions = ["opm_python_docs.sphinx_ext_docstrings"]
- JSON paths configured in conf.py: opm_simulators_docstrings_path, opm_common_docstrings_path
- Used in .rst files via directives: .. opm_simulators_docstrings:: and .. opm_common_docstrings::

Supported JSON Formats:
1. TEMPLATE FORMAT (New): Uses "simulators", "constructors", "common_methods" with {{name}}/{{class}} expansion
2. FLAT FORMAT (Legacy): Direct key-value pairs with "signature", "doc", "type" fields

Format Detection: Automatic based on presence of "simulators" AND "common_methods" keys

Relationship to generate_docstring_hpp.py:
- This file: JSON → Sphinx documentation (online docs)
- generate_docstring_hpp.py: JSON → C++ headers (pybind11 docstrings)
- Both process the same JSON files but generate different outputs

Usage in .rst files:
  .. opm_simulators_docstrings::  # Generates simulator API docs
  .. opm_common_docstrings::      # Generates common API docs
"""

import json
from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList
from sphinx.util.docutils import SphinxDirective
from docutils import nodes

def expand_template(template_dict, simulator_config):
    """Recursively replace {{name}} and {{class}} placeholders"""
    if isinstance(template_dict, dict):
        result = {}
        for key, value in template_dict.items():
            result[key] = expand_template(value, simulator_config)
        return result
    elif isinstance(template_dict, str):
        return (template_dict
                .replace("{{name}}", simulator_config["name"])
                .replace("{{class}}", simulator_config["class"]))
    else:
        return template_dict

def process_template_docstrings(directive, config):
    """Process template-based docstring configuration"""
    result = []

    for sim_key, sim_config in config.get("simulators", {}).items():
        # Create ViewList for class documentation
        rst = ViewList()
        signature = f"opm.simulators.{sim_config['name']}"
        rst.append(f".. py:class:: {signature}", source="")
        rst.append("", source="")
        if sim_config.get("doc"):
            for line in sim_config["doc"].split('\n'):
                rst.append(f"   {line}", source="")
        rst.append("", source="")

        # Process constructors
        for constructor_key, constructor_template in config.get("constructors", {}).items():
            expanded = expand_template(constructor_template, sim_config)
            signature = expanded.get("signature_template", "")
            if signature:
                # Constructor signatures are methods of the class
                rst.append(f"   .. py:method:: {signature}", source="")
                rst.append("", source="")
                doc = expanded.get("doc", "")
                if doc:
                    for line in doc.split('\\n'):  # Handle escaped newlines
                        rst.append(f"      {line}", source="")
                rst.append("", source="")

        # Process methods
        for method_name, method_template in config.get("common_methods", {}).items():
            expanded = expand_template(method_template, sim_config)
            signature = expanded.get("signature_template", "")
            if signature:
                rst.append(f"   .. py:method:: {signature}", source="")
                rst.append("", source="")
                doc = expanded.get("doc", "")
                if doc:
                    for line in doc.split('\\n'):  # Handle escaped newlines
                        rst.append(f"      {line}", source="")
                rst.append("", source="")

        # Parse all RST content for this simulator
        node = nodes.section()
        node.document = directive.state.document
        nested_parse_with_titles(directive.state, rst, node)
        result.extend(node.children)

    return result

def read_doc_strings(directive, docstrings_path):
    print(docstrings_path)
    with open(docstrings_path, 'r') as file:
        docstrings = json.load(file)

    # Check if this is template format
    if "simulators" in docstrings and "common_methods" in docstrings:
        return process_template_docstrings(directive, docstrings)

    # Otherwise process as flat format (existing code for backward compatibility)
    sorted_docstrings = sorted(docstrings.items(), key=lambda item: item[1].get('signature', item[0]))
    result = []
    for name, item in sorted_docstrings:
        # Create a ViewList instance for the function signature and docstring
        rst = ViewList()

        # Check if signature exists and prepend it to the docstring
        signature = item.get('signature', '')
        item_type = item.get('type', 'method')
        signature_line = f".. py:{item_type}:: {signature}" if signature else f".. py:{item_type}:: {name}()"
        rst.append(signature_line, source="")
        rst.append("", source="")

        # Add the docstring text if it exists
        docstring = item.get('doc', '')
        if docstring:
            for line in docstring.split('\n'):
                rst.append(f"   {line}", source="")

        # Create a node that will be populated by nested_parse_with_titles
        node = nodes.section()
        node.document = directive.state.document
        # Parse the rst content
        nested_parse_with_titles(directive.state, rst, node)

        result.extend(node.children)
    return result

class SimulatorsDirective(SphinxDirective):
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        return read_doc_strings(self, self.state.document.settings.env.app.config.opm_simulators_docstrings_path)

class CommonDirective(SphinxDirective):
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        return read_doc_strings(self, self.state.document.settings.env.app.config.opm_common_docstrings_path)

def setup(app):
    app.add_config_value('opm_simulators_docstrings_path', None, 'env')
    app.add_config_value('opm_common_docstrings_path', None, 'env')
    app.add_directive("opm_simulators_docstrings", SimulatorsDirective)
    app.add_directive("opm_common_docstrings", CommonDirective)

    # Return extension metadata for Sphinx (best practice)
    # - version: Extension version for debugging/compatibility
    # - parallel_read_safe: Enable parallel reading optimization
    # - parallel_write_safe: Enable parallel writing optimization
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
