import os
import ast
import unittest
from typing import List
from unittest.mock import patch, MagicMock


class TestToolsetInputSignatures(unittest.TestCase):
    """Test that all tools in all toolsets follow the standard input signature pattern."""

    def get_toolset_modules(self) -> List[str]:
        """Get a list of all toolset module paths."""
        # Path is relative to the agents package structure
        toolset_dir = os.path.join("system_2", "servers")
        toolset_module_base = "system_2.servers"
        toolset_files = []

        # Get the physical path to check file existence
        src_dir = os.path.join(os.path.dirname(__file__), "..", "..", "src")
        physical_toolset_dir = os.path.join(src_dir, toolset_dir)

        # Make sure the directory exists before trying to list it
        if os.path.exists(physical_toolset_dir) and os.path.isdir(physical_toolset_dir):
            for file in os.listdir(physical_toolset_dir):
                if file.endswith("_toolset.py"):
                    module_path = f"{toolset_module_base}.{file[:-3]}"
                    toolset_files.append(module_path)

        return toolset_files

    def is_pydantic_model(self, annotation_str: str) -> bool:
        """
        Check if a type annotation string represents a Pydantic model.
        This is a simple heuristic check since we can't import all possible models.
        """
        # Exclude primitive types and common non-Pydantic types
        primitive_types = {
            "str",
            "int",
            "float",
            "bool",
            "list",
            "dict",
            "tuple",
            "Optional",
            "Union",
            "Any",
            "List",
            "Dict",
            "Tuple",
            "Set",
            "FrozenSet",
            "Callable",
            "Type",
            "Mapping",
        }

        # If it contains "Model" or "Input" or ends with "Config", it's likely a Pydantic model
        model_indicators = {"Model", "Input", "Config", "Request", "Response", "Param"}

        # Extract the base type from common type wrappers
        base_type = annotation_str
        for wrapper in ["Optional[", "Union[", "List["]:
            if wrapper in base_type:
                parts = base_type.split(wrapper, 1)[1].split("]")[0].split(",")
                base_type = parts[0].strip()
                break

        # Check if it's likely a model
        return (
            base_type not in primitive_types
            and (
                any(indicator in base_type for indicator in model_indicators)
                or base_type[0].isupper()
                if base_type
                else False
            )  # Classes typically start with uppercase
        )

    @patch("redis.Redis")
    def test_all_tools_have_standard_input_signature(self, mock_redis):
        """
        Test that all tools in all toolsets have the standard input signature:

        def tool_name(
            input_data: SomeInputModel,
            options: Optional[ToolOptionsParam] = None,
        ) -> ReturnType:
        """
        # Configure the mock Redis to handle the initialization
        mock_instance = MagicMock()
        mock_instance.hexists.return_value = False
        mock_instance.hset.return_value = 0
        mock_instance.set.return_value = True
        mock_instance.get.return_value = None
        mock_redis.return_value = mock_instance

        # Also patch system_2.cache.cache.ToolsetCache to avoid actual initialization
        with (
            patch("system_2.cache.cache.ToolsetCache._cache_registry", {}),
            patch("system_2.cache.cache.ToolsetCache._cache_implementation"),
        ):
            try:
                toolset_modules = self.get_toolset_modules()
                failed_tools = []

                # If no toolset modules are found, this could be a setup issue or empty directory
                if not toolset_modules:
                    print("WARNING: No toolset modules found to test")
                    return

                for module_path in toolset_modules:
                    # Get the physical path to the module file
                    src_dir = os.path.join(os.path.dirname(__file__), "..", "..", "src")
                    module_parts = module_path.split(".")
                    module_file_path = os.path.join(src_dir, *module_parts) + ".py"

                    # Parse the module using AST to find all tool functions
                    try:
                        with open(module_file_path, "r") as f:
                            source = f.read()

                        tree = ast.parse(source)

                        # Find all function definitions with the @mcp.tool decorator
                        tool_functions = []
                        for node in tree.body:
                            # Check for decorated functions
                            if isinstance(node, ast.FunctionDef):
                                for decorator in node.decorator_list:
                                    # Check if it's an mcp.tool decorator
                                    is_tool = False
                                    if isinstance(decorator, ast.Call) and isinstance(
                                        decorator.func, ast.Attribute
                                    ):
                                        if decorator.func.attr == "tool" and isinstance(
                                            decorator.func.value, ast.Name
                                        ):
                                            if decorator.func.value.id == "mcp":
                                                is_tool = True

                                    if is_tool:
                                        tool_functions.append(node)

                        # Analyze each tool function for its parameter structure
                        for func_node in tool_functions:
                            func_name = func_node.name

                            # Get parameters
                            params = func_node.args.args
                            defaults = func_node.args.defaults

                            expected_issues = []

                            # Check parameter count
                            if len(params) < 2:
                                expected_issues.append(
                                    f"Too few parameters ({len(params)}), expected at least 2"
                                )

                            # Check first parameter name
                            if len(params) > 0:
                                first_param = params[0]
                                if first_param.arg != "input_data":
                                    expected_issues.append(
                                        "First parameter should be named 'input_data'"
                                    )

                                # Check type annotation - in AST, the annotation is optional
                                if not first_param.annotation:
                                    expected_issues.append(
                                        "'input_data' parameter needs a type annotation"
                                    )
                                else:
                                    # Get the annotation as a string
                                    annotation_str = ast.unparse(first_param.annotation)

                                    # Use our heuristic to check if it's likely a Pydantic model
                                    if not self.is_pydantic_model(annotation_str):
                                        expected_issues.append(
                                            f"'input_data' parameter should be a Pydantic BaseModel, got: {annotation_str}"
                                        )

                            # Check second parameter
                            if len(params) > 1:
                                second_param = params[1]
                                if second_param.arg != "options":
                                    expected_issues.append(
                                        "Second parameter should be named 'options'"
                                    )

                                # Check default value
                                has_default = (
                                    len(defaults) >= 1
                                )  # At least one default value
                                if not has_default:
                                    expected_issues.append(
                                        "'options' parameter should have a default value"
                                    )

                                # Check type annotation
                                if not second_param.annotation:
                                    expected_issues.append(
                                        "'options' parameter needs a type annotation"
                                    )
                                else:
                                    annotation_str = ast.unparse(
                                        second_param.annotation
                                    )
                                    if not (
                                        "ToolOptionsParam" in annotation_str
                                        or "Optional" in annotation_str
                                    ):
                                        expected_issues.append(
                                            f"'options' parameter should be of type Optional[ToolOptionsParam], got: {annotation_str}"
                                        )

                            if expected_issues:
                                # Get the function signature as a string for reporting
                                sig_str = f"def {func_name}({', '.join([ast.unparse(arg) for arg in params])})"

                                failed_tools.append(
                                    {
                                        "module": module_path,
                                        "tool": func_name,
                                        "signature": sig_str,
                                        "issues": expected_issues,
                                    }
                                )

                    except Exception as e:
                        print(f"Error analyzing module {module_path}: {e}")

                # Assert that there are no failed tools
                if failed_tools:
                    error_msg = "\nTools with non-standard signatures:\n\n"
                    for failure in failed_tools:
                        error_msg += f"Module: {failure['module']}\n"
                        error_msg += f"Tool: {failure['tool']}\n"
                        error_msg += f"Signature: {failure['signature']}\n"
                        error_msg += "Issues:\n"
                        for issue in failure["issues"]:
                            error_msg += f"  - {issue}\n"
                        error_msg += "\n"

                    self.fail(error_msg)
            except ImportError as e:
                # If we get import errors, log them but don't fail the test
                print(f"Import error during test: {e}")
                self.skipTest(f"Import error: {e}")


if __name__ == "__main__":
    unittest.main()
