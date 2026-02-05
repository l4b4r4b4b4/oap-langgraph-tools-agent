import os
import time
import threading
import unittest
import tempfile
import json
import pickle
from unittest.mock import patch, mock_open
import shutil

# Import the cache implementation
from system_2.cache.cache import (
    ToolsetCache,
    CacheReference,
    ReturnOptions,
    ValueReturnType,
    ReferenceReturnType,
    PaginationParams,
    make_json_serializable,
)
from system_2.cache.return_types import InterpolationParams


class TestCacheBase(unittest.TestCase):
    """Base class for all cache tests with common setup and teardown logic."""

    def setUp(self):
        """Set up a clean test environment before each test."""
        # Create a temporary directory for test cache files
        self.temp_dir = tempfile.mkdtemp()

        # Set the base cache directory to our temporary directory
        self.original_base_dir = ToolsetCache.BASE_CACHE_DIR
        ToolsetCache.BASE_CACHE_DIR = self.temp_dir

        # Clear the cache registry before each test
        ToolsetCache._cache_registry = {}

        # Create a standard non-deterministic cache for testing
        self.cache = ToolsetCache(
            name="test_cache",
            deterministic=False,
            expiry_seconds=600,  # 10 minutes
            max_size=100,
        )

        # Create a deterministic cache for persistence tests
        self.det_cache = ToolsetCache(
            name="test_deterministic_cache", deterministic=True, max_size=100
        )

    def tearDown(self):
        """Clean up after each test."""
        # Reset the registry
        ToolsetCache._cache_registry = {}

        # Restore the original base directory
        ToolsetCache.BASE_CACHE_DIR = self.original_base_dir

        # Remove temporary directory
        shutil.rmtree(self.temp_dir)


class TestCacheBasicOperations(TestCacheBase):
    """Test basic cache operations (get, set, contains, clear)."""

    def test_01_set_and_get(self):
        """Test that values can be set and retrieved from the cache."""
        print("\n=== TEST SET AND GET ===")

        # Set a value
        test_key = "test_key"
        test_value = 42
        print(f"Setting key: '{test_key}' with value: '{test_value}'")
        self.cache.set(test_key, test_value)

        # Get the value
        print(f"Retrieving value for key: '{test_key}'")
        value, timestamp, ref_id = self.cache.get(test_key)
        print(f"Retrieved value: '{value}'")
        print(f"Timestamp: {timestamp}")
        print(f"Reference ID: {ref_id}")

        self.assertEqual(value, 42)
        self.assertIsInstance(timestamp, float)
        self.assertIsInstance(ref_id, str)

    def test_02_contains(self):
        """Test the `contains` method and the `in` operator."""
        print("\n=== TEST CONTAINS ===")

        # Set a value
        test_key = "test_key"
        test_value = 69
        print(f"Setting key: '{test_key}' with value: '{test_value}'")
        self.cache.set(test_key, test_value)

        # Check using contains method
        print(f"Checking if cache contains key: '{test_key}'")
        contains_result = self.cache.contains(test_key)
        print(f"Contains result: {contains_result}")
        self.assertTrue(contains_result)

        # Check using 'in' operator
        print(f"Checking if key '{test_key}' is in cache using 'in' operator")
        in_result = test_key in self.cache
        print(f"'in' operator result: {in_result}")
        self.assertTrue(in_result)

        # Check for non-existent key
        nonexistent_key = "nonexistent_key"
        print(f"Checking if cache contains non-existent key: '{nonexistent_key}'")
        contains_result = self.cache.contains(nonexistent_key)
        print(f"Contains result for non-existent key: {contains_result}")
        self.assertFalse(contains_result)

        print(
            f"Checking if non-existent key '{nonexistent_key}' is in cache using 'in' operator"
        )
        in_result = nonexistent_key in self.cache
        print(f"'in' operator result for non-existent key: {in_result}")
        self.assertFalse(in_result)

    def test_03_clear(self):
        """Test that the clear method empties the cache."""
        print("\n=== TEST CLEAR ===")

        # Set multiple values
        print("Setting multiple values in cache")
        self.cache.set("key1", 42)
        self.cache.set("key2", 69)
        print(f"Cache now contains {len(self.cache.cache)} items")

        # Clear the cache
        print("Clearing the cache")
        cleared_count = self.cache.clear()
        print(f"Cleared {cleared_count} items from cache")

        # Verify results
        print("Verifying cache is empty")
        print(f"Cache now contains {len(self.cache.cache)} items")
        self.assertEqual(cleared_count, 2)
        self.assertFalse(self.cache.contains("key1"))
        self.assertFalse(self.cache.contains("key2"))

        # Check stats are reset
        stats = self.cache.get_stats()
        print(f"Cache stats after clear: {stats}")
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)

    def test_04_get_nonexistent_key(self):
        """Test that getting a nonexistent key raises KeyError."""
        print("\n=== TEST GET NONEXISTENT KEY ===")

        nonexistent_key = "nonexistent_key"
        print(f"Attempting to get non-existent key: '{nonexistent_key}'")

        try:
            self.cache.get(nonexistent_key)
            print("ERROR: KeyError should have been raised")
            self.fail("KeyError was not raised")
        except KeyError as e:
            print(f"KeyError raised as expected: {e}")


class TestCacheReferences(TestCacheBase):
    """Test the creation and resolution of cache references."""

    def test_01_reference_creation(self):
        """Test that a reference is created when setting a value."""
        print("\n=== TEST REFERENCE CREATION ===")

        # Set a value
        test_key = "test_key"
        test_value = 42
        print(f"Setting key: '{test_key}' with value: '{test_value}'")
        self.cache.set(test_key, test_value)

        # Get the reference ID
        print(f"Getting reference ID for key: '{test_key}'")
        _, _, ref_id = self.cache.get(test_key)
        print(f"Reference ID: {ref_id}")

        # Verify the reference exists in the registry
        print("Checking if reference exists in registry")
        registry_contains_ref = ref_id in self.cache.reference_registry
        print(f"Registry contains reference: {registry_contains_ref}")
        self.assertIn(ref_id, self.cache.reference_registry)

        print("Checking if registry maps reference to correct key")
        registry_key = self.cache.reference_registry[ref_id]
        print(f"Registry maps reference to key: '{registry_key}'")
        self.assertEqual(registry_key, test_key)

    def test_02_reference_resolution(self):
        """Test resolving a reference to its value."""
        print("\n=== TEST REFERENCE RESOLUTION ===")

        # Set a value
        test_key = "test_key"
        test_value = 69
        print(f"Setting key: '{test_key}' with value: '{test_value}'")
        self.cache.set(test_key, test_value)

        # Get the reference ID
        print(f"Getting reference ID for key: '{test_key}'")
        _, _, ref_id = self.cache.get(test_key)
        print(f"Reference ID: {ref_id}")

        # Create a reference object
        print("Creating CacheReference object")
        ref = CacheReference(
            ref_id=ref_id, cache_name="test_cache", tool_name="test_tool"
        )
        print(f"Created reference: {ref}")

        # Resolve the reference
        print("Resolving reference to get value")
        resolved_value = ToolsetCache.resolve_reference(ref)
        print(f"Resolved value: '{resolved_value}'")

        # Verify the resolved value
        self.assertEqual(resolved_value, test_value)

    def test_03_reference_auto_resolution_simple(self):
        """Test reference auto-resolution in function arguments."""
        print("\n=== TEST REFERENCE AUTO-RESOLUTION (SIMPLE) ===")

        # Set a value
        test_key = "test_key"
        test_value = 42
        print(f"Setting key: '{test_key}' with value: '{test_value}'")
        self.cache.set(test_key, test_value)

        # Get the reference ID
        print(f"Getting reference ID for key: '{test_key}'")
        _, _, ref_id = self.cache.get(test_key)
        print(f"Reference ID: {ref_id}")

        # Test processing a reference in an argument
        print(f"Processing reference ID as argument: '{ref_id}'")
        processed_value = self.cache._process_reference_value(ref_id)
        print(f"Processed value: '{processed_value}'")

        # Verify the reference was resolved
        self.assertEqual(processed_value, test_value)

    def test_04_reference_auto_resolution_in_nested_structure(self):
        """Test auto-resolution when reference IDs are embedded in nested data structures."""
        print("\n=== TEST REFERENCE AUTO-RESOLUTION (NESTED) ===")

        # Set a value in the cache
        test_key = "test_key"
        test_value = 69
        print(f"Setting key: '{test_key}' with value: '{test_value}'")
        self.cache.set(test_key, test_value)

        # Get the reference ID
        print(f"Getting reference ID for key: '{test_key}'")
        _, _, ref_id = self.cache.get(test_key)
        print(f"Reference ID: {ref_id}")

        # Create a nested structure that might come from a typical API response
        print("Creating nested structure with embedded reference")
        nested_input = {
            "input_data": {
                "parameters": {"test": ref_id, "other_param": "some_value"},
                "metadata": {"source": "test_source"},
            },
            "options": {"process_mode": "standard"},
        }
        print(f"Nested structure: {json.dumps(nested_input, indent=2)}")

        # Process the nested structure with reference resolution
        print("Processing nested structure with reference resolution")
        processed_value = self.cache._process_reference_value(nested_input)
        print(f"Processed structure: {json.dumps(processed_value, indent=2)}")

        # Verify the reference was resolved within the nested structure
        resolved_value = processed_value["input_data"]["parameters"]["test"]
        print(f"Resolved value in nested structure: '{resolved_value}'")
        self.assertEqual(resolved_value, test_value)

        # Verify the rest of the structure remains unchanged
        self.assertEqual(
            processed_value["input_data"]["parameters"]["other_param"], "some_value"
        )
        self.assertEqual(
            processed_value["input_data"]["metadata"]["source"], "test_source"
        )
        self.assertEqual(processed_value["options"]["process_mode"], "standard")

    def test_05_reference_resolution_in_nested_structures(self):
        """Test resolving references in nested data structures."""
        print("\n=== TEST MULTIPLE REFERENCES IN NESTED STRUCTURE ===")

        # Set values
        print("Setting multiple values in cache")
        value1 = 42
        value2 = 69
        self.cache.set("key1", value1)
        self.cache.set("key2", value2)
        print(f"Set key1 = {value1}, key2 = {value2}")

        # Get reference IDs
        print("Getting reference IDs")
        _, _, ref_id1 = self.cache.get("key1")
        _, _, ref_id2 = self.cache.get("key2")
        print(f"Reference ID for key1: {ref_id1}")
        print(f"Reference ID for key2: {ref_id2}")

        # Create nested structure with references
        print("Creating nested structure with multiple references")
        nested = {
            "ref1": ref_id1,
            "list": [1, 2, ref_id2],
        }
        print(f"Nested structure: {json.dumps(nested, default=str, indent=2)}")

        # Process the nested structure
        print("Processing nested structure")
        processed = self.cache._process_reference_value(nested)
        print(f"Processed structure: {json.dumps(processed, default=str, indent=2)}")

        # Verify the references were resolved
        print(f"Checking if ref1 resolved to {value1}")
        self.assertEqual(processed["ref1"], value1)

        print(f"Checking if list[2] resolved to {value2}")
        self.assertEqual(processed["list"][2], value2)


class TestCacheReturnTypes(TestCacheBase):
    """Test different return type configurations."""

    def test_00_return_default_value(self):
        """Test returning the full value."""
        # Set a value
        test_value = 42
        print("\n=== TEST DEFAULT RETURN TYPE ===")
        print(f"Setting test value: {test_value} (type: {type(test_value).__name__})")

        self.cache.set("test_key", test_value)

        # Get the value with default ReturnOptions
        _, _, ref_id = self.cache.get("test_key")
        print(f"Generated reference ID: {ref_id}")

        options = ReturnOptions(value_type=ValueReturnType.DEFAULT)
        print(f"Return options: {options}")

        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )

        print(f"Result: {json.dumps(result, default=str, indent=2)}")

        # Verify default value is returned
        self.assertEqual(result["value"], test_value)

    def test_01_return_full_value(self):
        """Test returning the full value for all JSON-serializable types."""
        print("\n=== TEST FULL VALUE RETURN TYPE ===")

        # Test with primitive types
        primitive_values = [
            42,  # Integer
            3.14159,  # Float
            "test string",  # String
            True,  # Boolean
            False,  # Boolean
            None,  # None/null
        ]

        print("\n--- Testing primitive types ---")
        for value in primitive_values:
            # Set the value
            key = f"primitive_{type(value).__name__}"
            print(f"\nTesting primitive: {value} (type: {type(value).__name__})")
            self.cache.set(key, value)

            # Get the value with options for full return
            _, _, ref_id = self.cache.get(key)
            options = ReturnOptions(value_type=ValueReturnType.FULL)

            result = self.cache.handle_return_value(
                value, options, tool_name="test_tool", ref_id=ref_id
            )

            print(f"Reference ID: {ref_id[:8]}...")
            print(f"Result value: {result['value']}")

            # Verify full value is returned correctly
            self.assertEqual(result["value"], value)

        # Test with container types
        print("\n--- Testing container types ---")
        container_values = [
            [1, 2, 3, 4, 5],  # List of numbers
            ["a", "b", "c"],  # List of strings
            [True, False, None],  # List of mixed primitives
            {"a": 1, "b": 2, "c": 3},  # Dictionary
            [{"name": "item1"}, {"name": "item2"}],  # List of dictionaries
            {"items": [1, 2, 3], "count": 3},  # Dictionary with list
        ]

        for i, value in enumerate(container_values):
            # Set the value
            key = f"container_{i}"
            print(f"\nTesting container #{i}: {type(value).__name__}")
            print(f"Value: {value}")
            self.cache.set(key, value)

            # Get the value with options for full return
            _, _, ref_id = self.cache.get(key)
            options = ReturnOptions(value_type=ValueReturnType.FULL)

            result = self.cache.handle_return_value(
                value, options, tool_name="test_tool", ref_id=ref_id
            )

            print(f"Reference ID: {ref_id[:8]}...")
            print(f"Result matches original: {result['value'] == value}")

            # Verify full value is returned correctly
            self.assertEqual(result["value"], value)

        # Test with complex nested structure
        print("\n--- Testing complex nested structure ---")
        nested_dict = {
            "level1": {
                "level2": {
                    "level3": [1, 2, 3, 4, 5],
                    "data": {f"item_{i}": f"value_{i}" for i in range(10)},
                },
                "array": list(range(20)),
                "mixed": (1, "string", True, [7, 8, 9], {"nested": "value"}),
            },
            "tuple_data": tuple(range(15)),
            "list_data": list(range(25)),
            "set_data": {1, 2, 3, 4, 5},
            "enum_value": ValueReturnType.FULL,
            "pydantic_model": ReturnOptions(value_type=ValueReturnType.FULL),
        }

        print(f"Complex structure contains: {', '.join(nested_dict.keys())}")
        print(f"Tuple data type: {type(nested_dict['tuple_data']).__name__}")
        print(f"Set data type: {type(nested_dict['set_data']).__name__}")
        print(f"Enum value: {nested_dict['enum_value']}")
        print(f"Pydantic model: {nested_dict['pydantic_model']}")

        # Set the value
        self.cache.set("test_key_complex", nested_dict)

        # Get the value with options for full return
        _, _, ref_id = self.cache.get("test_key_complex")
        options = ReturnOptions(value_type=ValueReturnType.FULL)

        result = self.cache.handle_return_value(
            nested_dict, options, tool_name="test_tool", ref_id=ref_id
        )

        # Convert both to JSON serializable for comparison
        expected = make_json_serializable(nested_dict)

        print("\nTransformations after serialization:")
        print(f"- Tuple data became: {type(result['value']['tuple_data']).__name__}")
        print(f"- Set data became: {type(result['value']['set_data']).__name__}")
        print(f"- Enum value became: {result['value']['enum_value']}")

        # Check if the complex structure has the expected number of elements
        for key, count in [
            ("tuple_data", 15),
            ("list_data", 25),
            ("level1.array", 20),
        ]:
            actual_count = (
                len(result["value"]["tuple_data"])
                if key == "tuple_data"
                else len(result["value"]["list_data"])
                if key == "list_data"
                else len(result["value"]["level1"]["array"])
            )
            print(f"- {key} has {actual_count} elements (expected: {count})")

        # Verify full value is returned (complex structure should be preserved)
        self.assertEqual(result["value"], expected)

        # Verify some specific nested elements are present and correctly transformed
        self.assertIsInstance(result["value"]["tuple_data"], list)  # Tuple becomes list
        self.assertIsInstance(result["value"]["set_data"], list)  # Set becomes list
        self.assertEqual(len(result["value"]["tuple_data"]), 15)
        self.assertEqual(len(result["value"]["list_data"]), 25)
        self.assertEqual(len(result["value"]["level1"]["array"]), 20)
        self.assertEqual(
            result["value"]["enum_value"], "full"
        )  # Enum becomes its value

    def test_02_return_preview(self):
        """Test returning a preview of various JSON-serializable types."""
        print("\n=== TEST PREVIEW RETURN TYPE ===")

        # Test preview with different types of values
        test_values = [
            # Primitive values (these should be simple previews)
            42,  # Integer
            3.14159,  # Float
            "This is a test string",  # String
            True,  # Boolean
            # Container values
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # List
            {"a": 1, "b": 2, "c": 3},  # Small dict
            # Large values (these should be truncated in preview)
            "x" * 1000,  # Long string
            list(range(100)),  # Large list
            {f"key_{i}": f"value_{i}" for i in range(50)},  # Large dict
            # Complex nested structure
            {
                "users": [{"id": i, "name": f"User {i}"} for i in range(20)],
                "metadata": {
                    "created": "2023-01-01",
                    "tags": ["test", "preview", "cache"],
                },
                "stats": {"views": 1000, "likes": 750, "shares": 250},
            },
        ]

        print("\n--- Preview results by type ---")
        for i, value in enumerate(test_values):
            # Set the value
            key = f"preview_test_{i}"
            value_type = type(value).__name__

            # Prepare a displayable version of the value
            if isinstance(value, (dict, list)):
                size = len(value)
                sample = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"\n#{i}: {value_type} with {size} items")
                print(f"Sample: {sample}")
            else:
                sample = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"\n#{i}: {value_type}")
                print(f"Value: {sample}")

            self.cache.set(key, value)

            # Get the value with options for preview
            _, _, ref_id = self.cache.get(key)
            options = ReturnOptions(value_type=ValueReturnType.PREVIEW)

            result = self.cache.handle_return_value(
                value, options, tool_name="test_tool", ref_id=ref_id
            )

            # Display the preview
            preview_text = result["value"]["preview_text"]
            print(f"Preview: {preview_text}")
            print(f"Preview length: {len(preview_text)} chars")

            if isinstance(value, (str, list, dict)) and len(str(value)) > 100:
                original_len = len(str(value))
                preview_len = len(preview_text)
                print(
                    f"Original length: {original_len}, Preview: {preview_len}, Reduction: {original_len - preview_len} chars"
                )

            # Verify preview structure is correct
            self.assertIsInstance(result["value"], dict)
            self.assertEqual(result["value"]["type"], "cache_preview")
            self.assertIn("preview_text", result["value"])
            self.assertIn("tool_name", result["value"])
            self.assertEqual(result["value"]["tool_name"], "test_tool")

            # For large values, make sure preview is shorter than original
            if isinstance(value, (str, list, dict)) and len(str(value)) > 100:
                self.assertLess(len(result["value"]["preview_text"]), len(str(value)))

    def test_03_return_reference_types(self):
        """Test different reference return types."""
        print("\n=== TEST REFERENCE RETURN TYPES ===")

        # Set a value
        test_value = 69
        print(f"Test value: {test_value}")
        self.cache.set("test_key", test_value)

        # Get the reference ID
        _, _, ref_id = self.cache.get("test_key")
        print(f"Generated reference ID: {ref_id}")

        # Test default reference (just ID)
        print("\n--- Testing DEFAULT reference type ---")
        options = ReturnOptions(
            value_type=None, reference_type=ReferenceReturnType.DEFAULT
        )
        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )
        print(f"DEFAULT reference result: {json.dumps(result['reference'])}")
        self.assertEqual(result["reference"], {"ref_id": ref_id})

        # Test simple reference (ID and cache name)
        print("\n--- Testing SIMPLE reference type ---")
        options = ReturnOptions(
            value_type=None, reference_type=ReferenceReturnType.SIMPLE
        )
        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )
        print(f"SIMPLE reference result: {json.dumps(result['reference'])}")
        self.assertEqual(
            result["reference"], {"ref_id": ref_id, "cache_name": "test_cache"}
        )

        # Test full reference
        print("\n--- Testing FULL reference type ---")
        options = ReturnOptions(
            value_type=None, reference_type=ReferenceReturnType.FULL
        )
        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )
        print(f"FULL reference result: {json.dumps(result['reference'], default=str)}")
        self.assertEqual(result["reference"]["type"], "cache_reference")
        self.assertEqual(result["reference"]["ref_id"], ref_id)
        self.assertEqual(result["reference"]["cache_name"], "test_cache")
        self.assertEqual(result["reference"]["tool_name"], "test_tool")

    def test_04_no_options_specified(self):
        """Test behavior when no options are specified - should use defaults for both value and reference."""
        print("\n=== TEST: NO OPTIONS SPECIFIED ===")

        # Test with a primitive value (should be returned in full)
        test_primitive = 42
        print(f"Test primitive value: {test_primitive}")
        self.cache.set("test_primitive", test_primitive)
        _, _, primitive_ref_id = self.cache.get("test_primitive")

        # Test with a complex value that would be previewed (large list)
        test_complex = list(range(1000))  # List with 1000 items (should be previewed)
        print(f"Test complex value: list with {len(test_complex)} items")
        self.cache.set("test_complex", test_complex)
        _, _, complex_ref_id = self.cache.get("test_complex")

        # Case: No options specified at all (None passed as options) with primitive
        print("\n--- No options specified with primitive value ---")
        result = self.cache.handle_return_value(
            test_primitive, None, tool_name="test_tool", ref_id=primitive_ref_id
        )
        print(f"Result with no options (primitive): {json.dumps(result, default=str)}")

        # For primitive values: should return full value and simple reference
        self.assertIsNotNone(result["value"])
        self.assertEqual(
            result["value"], test_primitive
        )  # Primitive value should be returned in full
        self.assertIsNotNone(result["reference"])
        # Reference should be simple (DEFAULT = {"ref_id": ID})
        self.assertEqual(result["reference"], {"ref_id": primitive_ref_id})

        # Case: No options specified at all (None passed as options) with complex
        print("\n--- No options specified with complex value ---")
        result = self.cache.handle_return_value(
            test_complex, None, tool_name="test_tool", ref_id=complex_ref_id
        )
        print(
            f"Result with no options (complex): preview returned = {isinstance(result['value'], dict) and 'type' in result['value'] and result['value']['type'] == 'cache_preview'}"
        )

        # For complex value: should return a preview and simple reference
        self.assertIsNotNone(result["value"])
        self.assertIsInstance(result["value"], dict)
        self.assertEqual(
            result["value"]["type"], "cache_preview"
        )  # Complex value should be previewed
        self.assertIsNotNone(result["reference"])
        self.assertEqual(result["reference"], {"ref_id": complex_ref_id})

    def test_05_only_value_type_specified(self):
        """Test behavior when only value_type is specified - reference should still be included as simple."""
        print("\n=== TEST: ONLY VALUE_TYPE SPECIFIED ===")

        # Test value
        test_value = 42
        print(f"Test value: {test_value}")
        self.cache.set("test_key", test_value)
        _, _, ref_id = self.cache.get("test_key")

        # Case: Only value_type=FULL specified
        print("\n--- Only value_type=FULL specified ---")
        options = ReturnOptions(value_type=ValueReturnType.FULL, reference_type=None)
        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )
        print(f"Result with only value_type=FULL: {json.dumps(result, default=str)}")

        # Value should be returned as specified
        self.assertEqual(result["value"], test_value)  # Full value
        # Reference should still be returned as simple
        self.assertIsNotNone(result["reference"])
        self.assertEqual(result["reference"], {"ref_id": ref_id})

        # Case: Only value_type=PREVIEW specified
        print("\n--- Only value_type=PREVIEW specified ---")
        options = ReturnOptions(value_type=ValueReturnType.PREVIEW, reference_type=None)
        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )
        print(f"Result with only value_type=PREVIEW: {json.dumps(result, default=str)}")

        # Value should be returned as preview
        self.assertIsNotNone(result["value"])
        self.assertEqual(result["value"]["type"], "cache_preview")
        # Reference should still be returned as simple
        self.assertIsNotNone(result["reference"])
        self.assertEqual(result["reference"], {"ref_id": ref_id})

    def test_06_only_reference_type_specified(self):
        """Test behavior when only reference_type is specified - value should not be included."""
        print("\n=== TEST: ONLY REFERENCE_TYPE SPECIFIED ===")

        # Test value
        test_value = 42
        print(f"Test value: {test_value}")
        self.cache.set("test_key", test_value)
        _, _, ref_id = self.cache.get("test_key")

        # Case: Only reference_type=FULL specified
        print("\n--- Only reference_type=FULL specified ---")
        options = ReturnOptions(
            value_type=None, reference_type=ReferenceReturnType.FULL
        )
        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )
        print(
            f"Result with only reference_type=FULL: {json.dumps(result, default=str)}"
        )

        # Value should not be included
        self.assertIsNone(result["value"])
        # Reference should be returned as specified
        self.assertIsNotNone(result["reference"])
        self.assertEqual(result["reference"]["type"], "cache_reference")
        self.assertEqual(result["reference"]["ref_id"], ref_id)

        # Case: Only reference_type=SIMPLE specified
        print("\n--- Only reference_type=SIMPLE specified ---")
        options = ReturnOptions(
            value_type=None, reference_type=ReferenceReturnType.SIMPLE
        )
        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )
        print(
            f"Result with only reference_type=SIMPLE: {json.dumps(result, default=str)}"
        )

        # Value should not be included
        self.assertIsNone(result["value"])
        # Reference should be returned as simple
        self.assertIsNotNone(result["reference"])
        self.assertEqual(
            result["reference"], {"ref_id": ref_id, "cache_name": "test_cache"}
        )

    def test_07_both_options_specified(self):
        """Test behavior when both options are specified."""
        print("\n=== TEST: BOTH OPTIONS SPECIFIED ===")

        # Test value
        test_value = 42
        print(f"Test value: {test_value}")
        self.cache.set("test_key", test_value)
        _, _, ref_id = self.cache.get("test_key")

        # Case: Both value_type=PREVIEW and reference_type=SIMPLE specified
        print("\n--- Both value_type=PREVIEW and reference_type=SIMPLE specified ---")
        options = ReturnOptions(
            value_type=ValueReturnType.PREVIEW,
            reference_type=ReferenceReturnType.SIMPLE,
        )
        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )
        print(f"Result with both options specified: {json.dumps(result, default=str)}")

        # Both should be returned according to specifications
        self.assertIsNotNone(result["value"])
        self.assertEqual(result["value"]["type"], "cache_preview")
        self.assertIsNotNone(result["reference"])
        self.assertEqual(
            result["reference"], {"ref_id": ref_id, "cache_name": "test_cache"}
        )

        # Case: Both value_type=FULL and reference_type=FULL specified
        print("\n--- Both value_type=FULL and reference_type=FULL specified ---")
        options = ReturnOptions(
            value_type=ValueReturnType.FULL, reference_type=ReferenceReturnType.FULL
        )
        result = self.cache.handle_return_value(
            test_value, options, tool_name="test_tool", ref_id=ref_id
        )
        print(f"Result with both options specified: {json.dumps(result, default=str)}")

        # Both should be returned according to specifications
        self.assertEqual(result["value"], test_value)  # Full value
        self.assertIsNotNone(result["reference"])
        self.assertEqual(result["reference"]["type"], "cache_reference")
        self.assertEqual(result["reference"]["ref_id"], ref_id)


class TestCachePagination(TestCacheBase):
    """Test pagination functionality for different data types."""

    def test_01_paginate_list(self):
        """Test paginating a list."""
        # Create a list
        test_list = list(range(100))
        print("\n=== TEST LIST PAGINATION ===")
        print(
            f"Original list: [0, 1, 2, ... {len(test_list)-1}] (length: {len(test_list)})"
        )

        # Paginate the list
        page = 2
        page_size = 10
        pagination = PaginationParams(page=page, page_size=page_size)
        print(f"Requesting page {page} with {page_size} items per page")

        paginated = self.cache._paginate_value(test_list, pagination)

        # Calculate expected range
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(test_list))
        expected_items = list(range(start_idx, end_idx))

        print("Pagination results:")
        print(f"- Page: {paginated.page}/{paginated.total_pages}")
        print(f"- Items per page: {paginated.page_size}")
        print(f"- Total items: {paginated.total_items}")
        print(f"- Has next page: {paginated.has_next}")
        print(f"- Has previous page: {paginated.has_prev}")
        print(f"- Items on this page: {paginated.items}")
        print(f"- Expected items: {expected_items}")

        # Verify pagination results
        self.assertEqual(paginated.page, 2)
        self.assertEqual(paginated.page_size, 10)
        self.assertEqual(paginated.total_items, 100)
        self.assertEqual(paginated.total_pages, 10)
        self.assertEqual(paginated.has_next, True)
        self.assertEqual(paginated.has_prev, True)
        self.assertEqual(paginated.items, list(range(10, 20)))

    def test_02_paginate_dict(self):
        """Test paginating a dictionary."""
        # Create a dictionary
        test_dict = {f"key_{i}": f"value_{i}" for i in range(100)}

        # These prints will show with -s flag
        print("\n=== TEST DICTIONARY PAGINATION ===")
        print(f"Original dictionary has {len(test_dict)} key-value pairs")
        print(f"Sample entries: {dict(list(test_dict.items())[:3])}...")

        # Paginate the dictionary
        page = 2
        page_size = 10
        pagination = PaginationParams(page=page, page_size=page_size)
        print(f"Requesting page {page} with {page_size} items per page")

        paginated = self.cache._paginate_value(test_dict, pagination)

        # Display the paginated result
        print("Pagination results:")
        print(f"- Page: {paginated.page}/{paginated.total_pages}")
        print(f"- Items per page: {paginated.page_size}")
        print(f"- Total items: {paginated.total_items}")
        print(f"- Has next page: {paginated.has_next}")
        print(f"- Has previous page: {paginated.has_prev}")
        print(f"- Number of items on this page: {len(paginated.items)}")
        print(f"- Items on this page: {paginated.items}")

        # Get the expected keys for this page
        keys = list(test_dict.keys())
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(keys))
        expected_keys = keys[start_idx:end_idx]
        expected_dict = {k: test_dict[k] for k in expected_keys}
        print(f"- Expected keys: {expected_keys}")
        print(f"- Keys match: {set(paginated.items.keys()) == set(expected_keys)}")

        # Use expected_dict in assertion to avoid linting warning
        self.assertEqual(paginated.items, expected_dict)

        # Other verifications
        self.assertEqual(paginated.page, 2)
        self.assertEqual(paginated.page_size, 10)
        self.assertEqual(paginated.total_items, 100)
        self.assertEqual(paginated.total_pages, 10)
        self.assertEqual(len(paginated.items), 10)  # 10 items in this page

    def test_03_paginate_with_return_options(self):
        """Test pagination through return options."""
        # Create a list
        test_list = list(range(100))
        print("\n=== TEST PAGINATION WITH RETURN OPTIONS ===")
        print(
            f"Original list: [0, 1, 2, ... {len(test_list)-1}] (length: {len(test_list)})"
        )

        # Set the value
        self.cache.set("test_key", test_list)

        # Get the reference ID
        _, _, ref_id = self.cache.get("test_key")
        print(f"Cache reference ID: {ref_id[:8]}...")

        # Create options with pagination
        page = 3
        page_size = 15
        options = ReturnOptions(
            value_type=ValueReturnType.FULL,
            pagination=PaginationParams(page=page, page_size=page_size),
        )
        print(
            f"Return options: value_type={options.value_type}, page={page}, page_size={page_size}"
        )

        # Get the paginated result
        result = self.cache.handle_return_value(
            test_list, options, tool_name="test_tool", ref_id=ref_id
        )

        # Calculate expected items
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(test_list))
        expected_items = list(range(start_idx, end_idx))

        # Verify the paginated result
        paginated = result["value"]
        print(f"Paginated result structure: {list(paginated.keys())}")
        print(f"Page: {paginated['page']}/{paginated['total_pages']}")
        print(f"Items per page: {paginated['page_size']}")
        print(f"Total items: {paginated['total_items']}")
        print(f"Has next page: {paginated['has_next']}")
        print(f"Has previous page: {paginated['has_prev']}")
        print(f"Items on this page: {paginated['items']}")
        print(f"Expected items: {expected_items}")
        print(f"Items match expected: {paginated['items'] == expected_items}")

        self.assertEqual(paginated["page"], 3)
        self.assertEqual(paginated["page_size"], 15)
        self.assertEqual(paginated["items"], list(range(30, 45)))


class TestCacheInterpolation(TestCacheBase):
    """Test interpolation functionality for different data types."""

    def test_01_interpolate_list(self):
        """Test interpolating a list."""
        # Create a list
        test_list = list(range(100))
        print("\n=== TEST LIST INTERPOLATION ===")
        print(
            f"Original list: [0, 1, 2, ... {len(test_list)-1}] (length: {len(test_list)})"
        )

        # Interpolate the list
        interpolation = InterpolationParams(
            enabled=True,
            sample_count=10,
            min_size_to_interpolate=20,
            include_endpoints=True,
        )
        print(
            f"Interpolation parameters: sample_count={interpolation.sample_count}, include_endpoints={interpolation.include_endpoints}"
        )

        interpolated = self.cache._interpolate_value(test_list, interpolation)

        print("Interpolation results:")
        print(f"- Original length: {len(test_list)}")
        print(f"- Interpolated length: {len(interpolated)}")
        print(f"- Interpolated items: {interpolated}")

        # Verify interpolation results
        self.assertEqual(len(interpolated), 10)
        self.assertEqual(interpolated[0], 0)  # First element
        self.assertEqual(interpolated[-1], 99)  # Last element

        # Check that elements are roughly evenly spaced
        expected_spacing = len(test_list) / (len(interpolated) - 1)
        for i in range(1, len(interpolated) - 1):
            expected_idx = i * expected_spacing
            self.assertAlmostEqual(
                interpolated[i], int(expected_idx), delta=expected_spacing / 2
            )

    def test_02_combined_interpolation_and_pagination(self):
        """Test combining interpolation with pagination."""
        # Create a list with 1000 elements
        test_list = list(range(1000))
        print("\n=== TEST COMBINED INTERPOLATION AND PAGINATION ===")
        print(f"Original list length: {len(test_list)}")

        # Set the list in the cache
        self.cache.set("test_combined", test_list)
        _, _, ref_id = self.cache.get("test_combined")

        # Create options with both interpolation and pagination
        options = ReturnOptions(
            value_type=ValueReturnType.FULL,
            interpolation=InterpolationParams(
                enabled=True,
                sample_count=100,  # Sample down to 100 items
                include_endpoints=True,
            ),
            pagination=PaginationParams(
                page=2,  # Get the second page
                page_size=10,  # 10 items per page
            ),
        )

        if options.interpolation is not None and options.pagination is not None:
            print(
                f"Options: interpolation={options.interpolation.sample_count} samples, page={options.pagination.page}, page_size={options.pagination.page_size}"
            )

        # Get the result
        result = self.cache.handle_return_value(
            test_list, options, tool_name="test_tool", ref_id=ref_id
        )

        # Verify the result structure
        paginated = result["value"]
        print(f"Result structure: {list(paginated.keys())}")
        print(f"Page: {paginated['page']}/{paginated['total_pages']}")
        print(f"Items per page: {paginated['page_size']}")
        print(f"Total items after interpolation: {paginated['total_items']}")
        print(f"Items on this page: {paginated['items']}")

        # We should have 100 total items after interpolation
        self.assertEqual(paginated["total_items"], 100)

        # We should have 10 items per page, so 10 total pages
        self.assertEqual(paginated["total_pages"], 10)

        # We requested page 2, so we should have items 10-19 of the interpolated list
        self.assertEqual(len(paginated["items"]), 10)

        # Verify the first item is approximately the expected value
        # For 100 samples from 1000 items, we'd expect indices at multiples of 10
        # Plus page 2 starts at index 10, so first item should be around 100
        self.assertTrue(90 <= paginated["items"][0] <= 110)

    def test_03_dict_interpolation(self):
        """Test interpolating a dictionary."""
        # Create a dictionary with 100 items
        test_dict = {f"key_{i}": f"value_{i}" for i in range(100)}
        print("\n=== TEST DICTIONARY INTERPOLATION ===")
        print(f"Original dictionary size: {len(test_dict)}")

        # Interpolate the dictionary
        interpolation = InterpolationParams(
            enabled=True, sample_count=5, include_endpoints=True
        )

        interpolated = self.cache._interpolate_value(test_dict, interpolation)

        print(f"Interpolated dictionary size: {len(interpolated)}")
        print(f"Interpolated keys: {list(interpolated.keys())}")

        # Verify the interpolated dictionary has the expected size
        self.assertEqual(len(interpolated), 5)

        # Verify first and last keys are preserved (if include_endpoints is True)
        self.assertIn("key_0", interpolated)
        self.assertIn("key_99", interpolated)

    def test_04_small_collection_handling(self):
        """Test interpolation behavior with small collections."""
        # Create a small list
        small_list = [1, 2, 3, 4, 5]
        print("\n=== TEST SMALL COLLECTION INTERPOLATION ===")
        print(f"Original list: {small_list}")

        # Set min_size_to_interpolate to 10 (larger than our list)
        interpolation = InterpolationParams(
            enabled=True,
            sample_count=3,
            min_size_to_interpolate=10,
            include_endpoints=True,
        )

        interpolated = self.cache._interpolate_value(small_list, interpolation)
        print(f"Interpolated result: {interpolated}")

        # Small list should be returned unchanged since it's below min_size_to_interpolate
        self.assertEqual(interpolated, small_list)

        # Now try with min_size_to_interpolate set to 3 (smaller than our list)
        interpolation = InterpolationParams(
            enabled=True,
            sample_count=3,
            min_size_to_interpolate=3,
            include_endpoints=True,
        )

        interpolated = self.cache._interpolate_value(small_list, interpolation)
        print(f"Interpolated result with lower threshold: {interpolated}")

        # Should now be interpolated to 3 items
        self.assertEqual(len(interpolated), 3)
        self.assertEqual(interpolated[0], 1)  # First element
        self.assertEqual(interpolated[-1], 5)  # Last element

    def test_06_advanced_interpolation_and_pagination(self):
        """Test advanced interpolation and pagination features with various data types."""
        print("\n=== TEST ADVANCED INTERPOLATION AND PAGINATION ===")

        # Create test data structures that will trigger untested code paths
        print("Creating test data structures for advanced interpolation/pagination...")

        # Test with Enum type (currently untested in pagination)
        from enum import Enum, auto

        class TestEnum(Enum):
            ONE = auto()
            TWO = auto()
            THREE = auto()

        enum_value = TestEnum.TWO
        print(f"Created Enum value: {enum_value}")

        # Test with a Pydantic model (triggers model_dump code path)
        from pydantic import BaseModel

        class TestModel(BaseModel):
            id: int
            name: str
            data: list

        model_value = TestModel(id=42, name="test", data=[1, 2, 3])
        print(f"Created Pydantic model: {model_value}")

        # Test with a custom iterable that's not a standard collection
        class CustomIterable:
            def __init__(self, items):
                self.items = items

            def __iter__(self):
                return iter(self.items)

        custom_iter = CustomIterable([4, 5, 6])
        print(f"Created custom iterable: {type(custom_iter).__name__}")

        # Test with other iterables
        from collections import deque

        deque_value = deque([7, 8, 9, 10, 11, 12])
        print(f"Created deque with {len(deque_value)} items")

        # Set all values in cache
        print("\nSetting values in cache...")
        self.cache.set("enum_value", enum_value)
        self.cache.set("model_value", model_value)
        self.cache.set("custom_iter", custom_iter)
        self.cache.set("deque_value", deque_value)

        # Test interpolation with different data types
        print("\nTesting interpolation...")
        interpolation_params = InterpolationParams(
            enabled=True,
            sample_count=2,
            min_size_to_interpolate=2,
            include_endpoints=True,
        )

        # Deque interpolation
        print("\n- Testing deque interpolation")
        deque_interpolated = self.cache._interpolate_value(
            deque_value, interpolation_params
        )
        print(f"  Original deque: {list(deque_value)}")
        print(f"  Interpolated result: {deque_interpolated}")
        self.assertIsInstance(deque_interpolated, list)
        self.assertEqual(len(deque_interpolated), 2)

        # Pydantic model interpolation
        print("\n- Testing Pydantic model interpolation")
        model_interpolated = self.cache._interpolate_value(
            model_value, interpolation_params
        )
        print(f"  Interpolated model result type: {type(model_interpolated).__name__}")
        print(f"  Interpolated model result: {model_interpolated}")
        self.assertIsInstance(model_interpolated, dict)

        # Custom iterable interpolation
        print("\n- Testing custom iterable interpolation")
        custom_interpolated = self.cache._interpolate_value(
            custom_iter, interpolation_params
        )
        print(f"  Interpolated custom iterable result: {custom_interpolated}")

        # Test pagination with different data types
        print("\nTesting pagination...")
        pagination_params = PaginationParams(page=1, page_size=2)

        # Enum pagination
        print("\n- Testing Enum pagination")
        enum_paginated = self.cache._paginate_value(enum_value, pagination_params)
        print(f"  Paginated enum result: {enum_paginated}")
        self.assertEqual(
            enum_paginated.total_items, 1
        )  # Enum is treated as a single item

        # Pydantic model pagination
        print("\n- Testing Pydantic model pagination")
        model_paginated = self.cache._paginate_value(model_value, pagination_params)
        print(f"  Paginated model result: {model_paginated}")
        self.assertEqual(model_paginated.page, 1)

        # Custom iterable pagination
        print("\n- Testing custom iterable pagination")
        custom_paginated = self.cache._paginate_value(custom_iter, pagination_params)
        print(f"  Paginated custom iterable result: {custom_paginated}")

        # Test non-iterable type
        print("\n- Testing non-iterable type pagination")
        non_iterable = 42
        non_iterable_paginated = self.cache._paginate_value(
            non_iterable, pagination_params
        )
        print(f"  Paginated non-iterable result: {non_iterable_paginated}")
        self.assertEqual(non_iterable_paginated.items, 42)  # Should be the value itself

        print("\nAdvanced interpolation and pagination tests passed")


class TestCachePersistence(TestCacheBase):
    """Test disk operations for deterministic caches."""

    def test_01_flush_to_disk(self):
        """Test that flush_to_disk writes cache to disk."""
        print("\n=== TEST FLUSH TO DISK ===")

        # Set values in deterministic cache
        print("Setting test values in deterministic cache")
        self.det_cache.set("key1", "value1")
        self.det_cache.set("key2", "value2")
        print(f"Set {len(self.det_cache.cache)} values in cache")

        # Check cache directory
        cache_dir = self.det_cache.cache_dir
        print(f"Cache directory: {cache_dir}")

        # Get expected file paths
        cache_filepath = self.det_cache._get_cache_filepath()
        registry_filepath = self.det_cache._get_registry_filepath()
        print(f"Expected cache filepath: {cache_filepath}")
        print(f"Expected registry filepath: {registry_filepath}")

        # Mock open to verify file writing
        print("Mocking file operations to verify _flush_to_disk behavior")
        with patch("builtins.open", mock_open()) as mock_file:
            print("Calling _flush_to_disk method")
            self.det_cache._flush_to_disk()

            # Check that files were opened for writing
            print("Verifying files were opened for writing")
            mock_file.assert_any_call(cache_filepath, "wb")
            mock_file.assert_any_call(registry_filepath, "wb")
            print("Files were opened correctly")

    def test_02_load_from_disk(self):
        """Test that load_from_disk reads cache from disk."""
        print("\n=== TEST LOAD FROM DISK ===")

        # Create mock cache data
        print("Creating mock cache data")
        mock_timestamp = time.time()
        mock_cache = {"key1": ("value1", mock_timestamp, "ref1")}
        mock_registry = {"ref1": "key1"}
        print(f"Mock cache: {mock_cache}")
        print(f"Mock registry: {mock_registry}")

        # Create a cache first
        cache_name = "load_test_cache"
        cache_dir = os.path.join(self.temp_dir, "load_test")
        os.makedirs(cache_dir, exist_ok=True)

        # Create the test cache file with mock data
        print(f"Creating test cache files in {cache_dir}")
        with open(os.path.join(cache_dir, f"{cache_name}_cache.pkl"), "wb") as f:
            pickle.dump(mock_cache, f)
        with open(os.path.join(cache_dir, f"{cache_name}_registry.pkl"), "wb") as f:
            pickle.dump(mock_registry, f)

        # Create a cache with the same name
        print("Creating cache that should load from disk")
        cache = ToolsetCache(
            name=cache_name,
            deterministic=True,
            cache_dir=cache_dir,
        )

        # The cache should have loaded our mock data
        print("Verifying cache content was loaded correctly")
        print(f"Expected: {mock_cache}")
        print(f"Actual: {cache.cache}")
        self.assertEqual(cache.cache, mock_cache)
        self.assertEqual(cache.reference_registry, mock_registry)
        print("Cache content verified")

    def test_03_real_persistence(self):
        """Test actual file persistence with real files."""
        print("\n=== TEST REAL PERSISTENCE ===")

        # Create a real deterministic cache
        cache_name = "real_persistence_cache"
        print(f"Creating deterministic cache: {cache_name}")
        cache = ToolsetCache(
            name=cache_name,
            deterministic=True,
        )
        print(f"Cache directory: {cache.cache_dir}")

        # Add data to the cache
        test_key = "persist_key"
        test_value = "persist_value"
        print(f"Setting test data: {test_key}={test_value}")
        cache.set(test_key, test_value)

        # Flush to disk
        print("Manually flushing cache to disk")
        cache.flush()

        # Get the file paths
        cache_filepath = cache._get_cache_filepath()
        registry_filepath = cache._get_registry_filepath()
        print(f"Cache filepath: {cache_filepath}")
        print(f"Registry filepath: {registry_filepath}")

        # Verify files exist (only if paths are not None)
        print("Verifying that cache files exist on disk")
        self.assertIsNotNone(cache_filepath)
        self.assertIsNotNone(registry_filepath)

        if cache_filepath:
            file_exists = os.path.exists(cache_filepath)
            print(f"Cache file exists: {file_exists}")
            self.assertTrue(file_exists)

        if registry_filepath:
            registry_exists = os.path.exists(registry_filepath)
            print(f"Registry file exists: {registry_exists}")
            self.assertTrue(registry_exists)

        # Create a new cache with the same name to test loading
        print("Creating a new cache instance to test loading from existing files")
        new_cache = ToolsetCache(
            name=cache_name,
            deterministic=True,
        )

        # Verify data was loaded
        print(f"Checking if new cache loaded the key: {test_key}")
        key_exists = new_cache.contains(test_key)
        print(f"Key exists in new cache: {key_exists}")
        self.assertTrue(key_exists)

        value, timestamp, ref_id = new_cache.get(test_key)
        print(f"Retrieved value: {value}")
        print(f"Retrieved timestamp: {timestamp}")
        print(f"Retrieved reference ID: {ref_id}")
        self.assertEqual(value, test_value)
        print("Successfully verified persistence and loading")


class TestCacheExpiration(TestCacheBase):
    """Test expiration and LRU eviction policies."""

    def test_01_expiration(self):
        """Test that entries expire after the specified time."""
        print("\n=== TEST CACHE EXPIRATION ===")

        # Create a cache with short expiry time
        expiry_time = 0.1  # 100ms
        print(f"Creating cache with short expiry time: {expiry_time}s")
        short_cache = ToolsetCache(
            name="short_expiry_cache",
            deterministic=False,
            expiry_seconds=expiry_time,
        )

        # Set a value
        test_key = "temp_key"
        test_value = "temp_value"
        print(f"Setting test value: {test_key}={test_value}")
        short_cache.set(test_key, test_value)

        # Verify it exists
        print("Verifying key exists immediately after setting")
        key_exists = short_cache.contains(test_key)
        print(f"Key exists: {key_exists}")
        self.assertTrue(key_exists)

        # Wait for expiration
        wait_time = 0.2  # 200ms
        print(f"Waiting {wait_time}s for key to expire...")
        time.sleep(wait_time)

        # Verify it's expired
        print("Checking if key has expired")
        key_exists_after = short_cache.contains(test_key)
        print(f"Key exists after waiting: {key_exists_after}")
        self.assertFalse(key_exists_after)

        # Verify expiration count increased
        expirations = short_cache.stats["expirations"]
        print(f"Expiration count: {expirations}")
        self.assertEqual(expirations, 1)
        print("Expiration test passed")

    def test_02_lru_eviction(self):
        """Test the Least Recently Used (LRU) eviction policy."""
        print("\n=== TEST LRU EVICTION ===")

        # Create a cache with small max size
        max_size = 5
        print(f"Creating cache with max size: {max_size}")
        small_cache = ToolsetCache(
            name="small_cache", deterministic=False, max_size=max_size
        )

        # Add 6 items (exceeding max_size)
        num_items = 6
        print(f"Adding {num_items} items to cache (exceeding max_size of {max_size})")
        for i in range(num_items):
            key = f"key_{i}"
            value = f"value_{i}"
            print(f"Setting {key}={value}")
            small_cache.set(key, value)

        # First key should be evicted (LRU)
        first_key = "key_0"
        print(f"Checking if first key '{first_key}' was evicted")
        first_key_exists = small_cache.contains(first_key)
        print(f"First key exists: {first_key_exists}")
        self.assertFalse(first_key_exists)

        # Other keys should still exist
        print("Checking if other keys still exist")
        for i in range(1, num_items):
            key = f"key_{i}"
            key_exists = small_cache.contains(key)
            print(f"Key '{key}' exists: {key_exists}")
            self.assertTrue(key_exists)

        print("LRU eviction test passed")


class TestCacheThreadSafety(TestCacheBase):
    """Test thread-safe operations of the cache."""

    def test_01_concurrent_access(self):
        """Test that concurrent access doesn't cause data corruption."""
        print("\n=== TEST CONCURRENT ACCESS ===")

        # Number of threads and operations per thread
        num_threads = 10
        ops_per_thread = 100
        print(
            f"Creating {num_threads} threads with {ops_per_thread} operations per thread"
        )

        # Create a cache with a larger max_size to avoid trimming during the test
        thread_safe_cache = ToolsetCache(
            name="thread_test_cache",
            deterministic=False,
            expiry_seconds=600,
            max_size=num_threads * ops_per_thread * 2,  # Double the size we need
        )

        # Track any exceptions that occur in threads
        exceptions = []

        def worker(thread_id):
            try:
                print(f"Thread {thread_id} starting")
                # Each thread sets and gets its own keys
                for i in range(ops_per_thread):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_value_{i}"

                    # Set value
                    thread_safe_cache.set(key, value)

                    # Get value and verify
                    stored_value, _, _ = thread_safe_cache.get(key)
                    assert (
                        stored_value == value
                    ), f"Value mismatch: {stored_value} != {value}"
                print(f"Thread {thread_id} completed successfully")
            except Exception as e:
                print(f"Thread {thread_id} encountered exception: {e}")
                exceptions.append(e)

        # Create and start threads
        print("Starting worker threads")
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        print("Waiting for all threads to complete...")
        for t in threads:
            t.join()
        print("All threads completed")

        # Check for exceptions
        print(f"Checking for exceptions (count: {len(exceptions)})")
        self.assertEqual(len(exceptions), 0, f"Exceptions in threads: {exceptions}")

        # Verify all data is intact - we expect some keys might be trimmed due to LRU eviction
        # Only check keys that still exist in the cache
        print("Verifying data integrity for keys that still exist...")
        verified_count = 0
        keys_not_found = 0

        for thread_id in range(num_threads):
            for i in range(ops_per_thread):
                key = f"thread_{thread_id}_key_{i}"
                expected_value = f"thread_{thread_id}_value_{i}"

                # Only verify if the key still exists in the cache
                if thread_safe_cache.contains(key):
                    actual_value, _, _ = thread_safe_cache.get(key)
                    self.assertEqual(actual_value, expected_value)
                    verified_count += 1
                else:
                    keys_not_found += 1

        print(f"Successfully verified {verified_count} key-value pairs")
        if keys_not_found > 0:
            print(
                f"{keys_not_found} keys were trimmed from the cache (expected with LRU policy)"
            )

        # The key test is that we had no exceptions during concurrent operations
        print("Concurrent access test passed - no thread exceptions")


class TestCacheStats(TestCacheBase):
    """Test statistics collection and reporting."""

    def test_01_hit_and_miss_stats(self):
        """Test that hit and miss statistics are accurately tracked."""
        print("\n=== TEST HIT AND MISS STATS ===")

        # Set initial values
        initial_stats = self.cache.get_stats()
        initial_hits = initial_stats["hits"]
        initial_misses = initial_stats["misses"]
        print(f"Initial stats - hits: {initial_hits}, misses: {initial_misses}")

        # Create a missing key situation (should increment misses)
        print("Attempting to get a nonexistent key (should trigger a miss)")
        with self.assertRaises(KeyError):
            self.cache.get("nonexistent_key")
        print("KeyError raised as expected for nonexistent key")

        # Set a key
        test_key = "stats_key"
        test_value = "stats_value"
        print(f"Setting key: '{test_key}' with value: '{test_value}'")
        self.cache.set(test_key, test_value)

        # Get the key (should increment hits)
        print(f"Getting key: '{test_key}' twice")
        self.cache.get(test_key)
        self.cache.get(test_key)  # Second hit
        print(f"Successfully retrieved key: '{test_key}'")

        # Check updated stats
        updated_stats = self.cache.get_stats()
        print(
            f"Updated stats - hits: {updated_stats['hits']}, misses: {updated_stats['misses']}"
        )
        print(f"Expected hits: {initial_hits} (direct get doesn't increment hits)")
        print(
            f"Expected misses: {initial_misses} (direct get doesn't increment misses)"
        )

        # The direct get() method doesn't update the hits or misses stats
        # Only the cached() decorator does that
        self.assertEqual(updated_stats["hits"], initial_hits)
        self.assertEqual(updated_stats["misses"], initial_misses)
        print("Hit and miss stats test passed")

    def test_02_reference_usage_stats(self):
        """Test that reference usage statistics are accurately tracked."""
        print("\n=== TEST REFERENCE USAGE STATS ===")

        # Get initial reference usage count
        initial_stats = self.cache.get_stats()
        initial_refs_used = initial_stats["references_used"]
        print(f"Initial references used: {initial_refs_used}")

        # Set a value
        test_key = "ref_key"
        test_value = "ref_value"
        print(f"Setting key: '{test_key}' with value: '{test_value}'")
        self.cache.set(test_key, test_value)

        # Get the reference ID
        print(f"Getting reference ID for key: '{test_key}'")
        _, _, ref_id = self.cache.get(test_key)
        print(f"Retrieved reference ID: {ref_id}")

        # Create a reference object
        print("Creating CacheReference object")
        ref = CacheReference(
            ref_id=ref_id, cache_name="test_cache", tool_name="test_tool"
        )
        print(f"Created reference: {ref}")

        # Resolve the reference
        print("Resolving reference to get value")
        resolved_value = ToolsetCache.resolve_reference(ref)
        print(f"Resolved value: '{resolved_value}'")

        # Check stats
        stats = self.cache.get_stats()
        print(f"Final references used: {stats['references_used']}")
        print(f"Expected references used: {initial_refs_used + 1}")

        self.assertEqual(stats["references_used"], initial_refs_used + 1)
        print("Reference usage stats test passed")

    def test_03_complete_stats(self):
        """Test that all statistics fields are present and valid."""
        print("\n=== TEST COMPLETE STATS ===")

        # Perform some operations to generate stats
        print("Setting and getting keys to generate stats")
        self.cache.set("stats_key1", "stats_value1")
        self.cache.set("stats_key2", "stats_value2")
        self.cache.get("stats_key1")
        print("Operations completed")

        # Get stats
        print("Retrieving complete cache stats")
        stats = self.cache.get_stats()
        print(f"Stats retrieved: {json.dumps(stats, indent=2, default=str)}")

        # Verify all expected fields exist
        expected_fields = [
            "name",
            "deterministic",
            "hits",
            "misses",
            "expirations",
            "references_used",
            "total_entries",
            "total_references",
            "max_size",
            "expiry_seconds",
        ]

        print("Checking that all expected stat fields are present:")
        for field in expected_fields:
            print(f"- Field '{field}' present: {field in stats}")
            self.assertIn(field, stats)

        # Verify values make sense
        print("Verifying specific stat values:")
        print(f"- name: expected='test_cache', actual='{stats['name']}'")
        print(f"- deterministic: expected=False, actual={stats['deterministic']}")
        print(f"- total_entries: expected=2, actual={stats['total_entries']}")
        print(f"- max_size: expected=100, actual={stats['max_size']}")
        print(f"- expiry_seconds: expected=600, actual={stats['expiry_seconds']}")

        self.assertEqual(stats["name"], "test_cache")
        self.assertEqual(stats["deterministic"], False)
        self.assertEqual(stats["total_entries"], 2)
        self.assertEqual(stats["max_size"], 100)
        self.assertEqual(stats["expiry_seconds"], 600)
        print("Complete stats test passed")


class TestCacheEdgeCases(TestCacheBase):
    """Test behavior with edge cases and unusual inputs."""

    def test_01_empty_cache(self):
        """Test operations on an empty cache."""
        print("\n=== TEST EMPTY CACHE ===")

        # First, ensure the cache is actually empty by clearing it
        print("Clearing cache to ensure it's empty")
        self.cache.clear()

        # Get stats for empty cache
        print("Getting stats for empty cache")
        stats = self.cache.get_stats()
        print(f"Stats for empty cache: {json.dumps(stats, indent=2, default=str)}")

        print(f"Checking total_entries (expected: 0, actual: {stats['total_entries']})")
        self.assertEqual(stats["total_entries"], 0)

        print(
            f"Checking total_references (expected: 0, actual: {stats['total_references']})"
        )
        self.assertEqual(stats["total_references"], 0)

        # Clear an empty cache
        print("Clearing an already empty cache")
        cleared = self.cache.clear()
        print(f"Number of items cleared: {cleared}")
        self.assertEqual(cleared, 0)
        print("Empty cache operations test passed")

    def test_02_large_values(self):
        """Test caching large values."""
        print("\n=== TEST LARGE VALUES ===")

        # Create a large value
        size_mb = 1
        size_bytes = size_mb * 1000000
        print(f"Creating a large string value of size {size_mb}MB ({size_bytes} bytes)")
        large_value = "x" * size_bytes

        # Cache the large value
        print("Setting large value in cache with key 'large_key'")
        self.cache.set("large_key", large_value)
        print("Large value successfully set in cache")

        # Retrieve the large value
        print("Retrieving large value from cache")
        retrieved, timestamp, ref_id = self.cache.get("large_key")
        print(f"Retrieved value with timestamp: {timestamp}, ref_id: {ref_id[:8]}...")

        # Verify integrity
        original_len = len(large_value)
        retrieved_len = len(retrieved)
        print(f"Checking length - original: {original_len}, retrieved: {retrieved_len}")
        self.assertEqual(retrieved_len, original_len)

        print("Verifying content matches exactly")
        values_match = retrieved == large_value
        print(f"Values match: {values_match}")
        self.assertEqual(retrieved, large_value)
        print("Large value caching test passed")

    def test_03_complex_data_structures(self):
        """Test caching complex nested data structures."""
        print("\n=== TEST COMPLEX DATA STRUCTURES ===")

        # Create a complex nested structure
        print("Creating complex nested data structure with various types")
        complex_value = {
            "string": "value",
            "number": 123,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3, ["nested", "list"]],
            "dict": {"nested": {"deep": ["very", "deep", {"extremely": "deep"}]}},
            "tuple": (1, 2, 3),
            "set": {1, 2, 3},
        }
        print(f"Complex structure contains: {', '.join(complex_value.keys())}")
        print(f"Tuple data type: {type(complex_value['tuple']).__name__}")
        print(f"Set data type: {type(complex_value['set']).__name__}")

        # Cache the complex value
        print("Setting complex structure in cache with key 'complex_key'")
        self.cache.set("complex_key", complex_value)
        print("Complex structure successfully set in cache")

        # Retrieve the complex value
        print("Retrieving complex structure from cache")
        retrieved, timestamp, ref_id = self.cache.get("complex_key")
        print(
            f"Retrieved structure with timestamp: {timestamp}, ref_id: {ref_id[:8]}..."
        )
        print(f"Retrieved structure contains: {', '.join(retrieved.keys())}")

        # Since tuples become lists and sets become lists during serialization,
        # we need to validate key components instead of direct equality
        print("\nVerifying individual components of the complex structure:")

        print("- string (expected: 'value')")
        self.assertEqual(retrieved["string"], "value")

        print("- number (expected: 123)")
        self.assertEqual(retrieved["number"], 123)

        print("- boolean (expected: True)")
        self.assertEqual(retrieved["boolean"], True)

        print("- none (expected: None)")
        self.assertIsNone(retrieved["none"])

        print("- list (expected: [1, 2, 3, ['nested', 'list']])")
        self.assertEqual(retrieved["list"], [1, 2, 3, ["nested", "list"]])

        print("- dict.nested.deep (expected nested path exists)")
        self.assertEqual(
            retrieved["dict"]["nested"]["deep"], ["very", "deep", {"extremely": "deep"}]
        )

        print("- tuple (expected to be converted to list)")
        tuple_result = retrieved.get("tuple")
        print(
            f"  Original: tuple(1, 2, 3), Retrieved: {tuple_result} (type: {type(tuple_result).__name__})"
        )

        print("- set (expected to be converted to list)")
        set_result = retrieved.get("set")
        print(
            f"  Original: {1, 2, 3}, Retrieved: {set_result} (type: {type(set_result).__name__})"
        )

        print("Complex data structure caching test passed")

    def test_04_invalid_reference_resolution(self):
        """Test that resolving invalid references raises appropriate errors."""
        print("\n=== TEST INVALID REFERENCE RESOLUTION ===")

        # Try to resolve a non-existent reference
        invalid_ref = "nonexistent_ref_id"
        print(f"Attempting to resolve invalid reference ID: '{invalid_ref}'")

        try:
            with self.assertRaises(ValueError) as context:
                ToolsetCache.resolve_reference(invalid_ref)
            print(f"ValueError raised as expected: {context.exception}")
        except AssertionError:
            print("ERROR: ValueError was not raised as expected")
            raise

        print("Invalid reference resolution test passed")

    def test_05_cached_decorator(self):
        """Test the cached decorator functionality."""
        print("\n=== TEST CACHED DECORATOR ===")

        # Define a function to be cached
        print("Defining function with @cached decorator")

        @self.cache.cached
        def test_function(input_data, options=None):
            print(f"  Function executed with input: '{input_data}'")
            return f"Processed: {input_data}"

        # Call the function twice with the same input
        print("\nCalling function first time with 'test_input'")
        result1 = test_function("test_input")
        print(f"First call result ref_id: {result1['reference']['ref_id'][:8]}...")

        print("\nCalling function second time with same input (should use cache)")
        result2 = test_function("test_input")
        print(f"Second call result ref_id: {result2['reference']['ref_id'][:8]}...")

        # Verify both calls returned the same reference ID
        print("\nVerifying both calls returned the same reference ID")
        refs_match = result1["reference"]["ref_id"] == result2["reference"]["ref_id"]
        print(f"Reference IDs match: {refs_match}")
        self.assertEqual(result1["reference"]["ref_id"], result2["reference"]["ref_id"])

        # Verify the cached function handles different inputs correctly
        print("\nCalling function with different input 'different_input'")
        result3 = test_function("different_input")
        print(f"Third call result ref_id: {result3['reference']['ref_id'][:8]}...")

        print("\nVerifying different input produces different reference ID")
        refs_different = (
            result1["reference"]["ref_id"] != result3["reference"]["ref_id"]
        )
        print(f"Reference IDs are different: {refs_different}")
        self.assertNotEqual(
            result1["reference"]["ref_id"], result3["reference"]["ref_id"]
        )

        print("Cached decorator test passed")

    def test_06_error_paths_and_edge_cases(self):
        """Test error handling paths and edge cases in the cache implementation."""
        print("\n=== TEST ERROR PATHS AND EDGE CASES ===")

        # Test loading from a corrupted file
        print("\n- Testing corrupted file handling")

        # Create a test deterministic cache
        test_cache_name = "error_test_cache"
        test_cache = ToolsetCache(
            name=test_cache_name,
            deterministic=True,
        )

        # Create invalid cache files
        if test_cache.cache_dir:
            cache_filepath = test_cache._get_cache_filepath()
            registry_filepath = test_cache._get_registry_filepath()

            print(f"  Creating corrupted cache file at: {cache_filepath}")
            if cache_filepath:
                with open(cache_filepath, "w") as f:
                    f.write("This is not valid pickle data")

            print(f"  Creating corrupted registry file at: {registry_filepath}")
            if registry_filepath:
                with open(registry_filepath, "w") as f:
                    f.write("This is not valid pickle data either")

            # Force reload, which should handle the corruption gracefully
            print("  Attempting to load from corrupted files")
            test_cache._load_from_disk()
            print("  Cache handled corrupted files without crashing")

            # Clean up the test files
            print("  Cleaning up test files")
            if cache_filepath and os.path.exists(cache_filepath):
                os.remove(cache_filepath)
            if registry_filepath and os.path.exists(registry_filepath):
                os.remove(registry_filepath)

        # Test reference ID ambiguity
        print("\n- Testing reference ID ambiguity handling")

        # Create similar reference IDs
        ref_value1 = "value1"
        ref_value2 = "value2"

        # Force specific reference IDs (this is a hack for testing)
        self.cache.cache.clear()
        self.cache.reference_registry.clear()

        print("  Creating references with ambiguous prefixes")
        ref_id1 = "abcdef1234"
        ref_id2 = "abcdef5678"

        # Manually insert into registry with similar IDs
        self.cache.reference_registry[ref_id1] = "key1"
        self.cache.reference_registry[ref_id2] = "key2"
        self.cache.cache["key1"] = (ref_value1, time.time(), ref_id1)
        self.cache.cache["key2"] = (ref_value2, time.time(), ref_id2)

        print(f"  Created ambiguous references: {ref_id1} and {ref_id2}")

        # Try to resolve with ambiguous prefix
        ambiguous_prefix = "abcdef"
        print(f"  Trying to resolve ambiguous prefix: {ambiguous_prefix}")
        try:
            ToolsetCache.resolve_reference(ambiguous_prefix)
            print("  ERROR: Should have raised ValueError for ambiguous prefix")
            self.fail("ValueError not raised for ambiguous reference prefix")
        except ValueError as e:
            print(f"  Correctly raised ValueError: {e}")

        # Test invalid reference formats
        print("\n- Testing invalid reference formats")
        invalid_ref_dict = {"missing_fields": True}
        print(f"  Testing with invalid reference dict: {invalid_ref_dict}")
        try:
            ToolsetCache.resolve_reference(invalid_ref_dict)
            print("  ERROR: Should have raised ValueError for invalid reference dict")
            self.fail("ValueError not raised for invalid reference dict")
        except ValueError as e:
            print(f"  Correctly raised ValueError: {e}")

        # Test cross-cache resolution
        print("\n- Testing cross-cache reference resolution")

        # Create a second cache
        second_cache = ToolsetCache(
            name="second_test_cache",
            deterministic=False,
        )

        # Set a value in second cache
        second_value = "value in second cache"
        second_cache.set("second_key", second_value)
        _, _, second_ref_id = second_cache.get("second_key")
        print(f"  Created value in second cache with ref_id: {second_ref_id[:8]}...")

        # Try to resolve from first cache (should find in registry)
        print("  Attempting cross-cache resolution from first cache")
        first_result = self.cache._process_reference_value(second_ref_id)
        print(f"  Cross-cache resolution result: {first_result}")
        self.assertEqual(first_result, second_value)

        # Test with reference in a deeply nested structure
        print("\n- Testing deep nested structure reference resolution")
        deep_nested = {"level1": {"level2": {"level3": {"ref": second_ref_id}}}}
        print("  Created deeply nested structure with reference at level3.ref")
        resolved_nested = self.cache._process_reference_value(deep_nested)
        print(
            f"  Resolved structure has value at level3.ref: {resolved_nested['level1']['level2']['level3']['ref']}"
        )
        self.assertEqual(
            resolved_nested["level1"]["level2"]["level3"]["ref"], second_value
        )

        # Test cache normalization with various input types
        print("\n- Testing cache key normalization with different input types")

        # Create a function to test against
        def test_normalize_func(a, b=None, input_data=None):
            return f"{a}_{b}_{input_data}"

        # Test with a Pydantic model
        from pydantic import BaseModel

        class TestInputModel(BaseModel):
            field1: str
            field2: int

        model_input = TestInputModel(field1="test", field2=123)
        print(f"  Testing normalization with Pydantic model: {model_input}")
        model_key = self.cache._normalize_cache_key("test_func", [model_input], {})
        print(f"  Normalized key: {model_key[:30]}...")
        self.assertIn("field1", model_key)
        self.assertIn("field2", model_key)

        # Test with input_data parameter
        print("  Testing normalization with input_data parameter")
        input_data_key = self.cache._normalize_cache_key(
            "test_func", [], {"input_data": {"test": 123}}
        )
        print(f"  Normalized key: {input_data_key[:30]}...")
        self.assertIn("input_data", input_data_key)

        print("\nError paths and edge cases test passed")


if __name__ == "__main__":
    unittest.main()
