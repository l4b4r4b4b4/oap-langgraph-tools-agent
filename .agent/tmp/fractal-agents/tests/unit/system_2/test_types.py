import unittest
from unittest.mock import MagicMock
import pytest
from system_2.cache.return_types import (
    ValueReturnType,
    ReferenceReturnType,
    PaginationParams,
    InterpolationParams,
    ReturnOptions,
)


class TestValueReturnType(unittest.TestCase):
    def test_enum_values(self):
        self.assertEqual(ValueReturnType.DEFAULT, "default")
        self.assertEqual(ValueReturnType.PREVIEW, "preview")
        self.assertEqual(ValueReturnType.FULL, "full")


class TestReferenceReturnType(unittest.TestCase):
    def test_enum_values(self):
        self.assertEqual(ReferenceReturnType.DEFAULT, "default")
        self.assertEqual(ReferenceReturnType.SIMPLE, "simple")
        self.assertEqual(ReferenceReturnType.FULL, "full")


class TestPaginationParams(unittest.TestCase):
    def test_default_values(self):
        params = PaginationParams()
        self.assertEqual(params.page, 1)
        self.assertEqual(params.page_size, 20)

    def test_custom_values(self):
        params = PaginationParams(page=3, page_size=50)
        self.assertEqual(params.page, 3)
        self.assertEqual(params.page_size, 50)

    def test_validation(self):
        with pytest.raises(ValueError):
            PaginationParams(page=0)  # Page must be >= 1

        with pytest.raises(ValueError):
            PaginationParams(page_size=0)  # Page size must be >= 1


class TestInterpolationParams(unittest.TestCase):
    def test_default_values(self):
        params = InterpolationParams()
        self.assertEqual(params.enabled, True)
        self.assertEqual(params.sample_count, 10)
        self.assertEqual(params.min_size_to_interpolate, 20)
        self.assertEqual(params.include_endpoints, True)

    def test_custom_values(self):
        params = InterpolationParams(
            enabled=False,
            sample_count=5,
            min_size_to_interpolate=30,
            include_endpoints=False,
        )
        self.assertEqual(params.enabled, False)
        self.assertEqual(params.sample_count, 5)
        self.assertEqual(params.min_size_to_interpolate, 30)
        self.assertEqual(params.include_endpoints, False)

    def test_validation(self):
        with pytest.raises(ValueError):
            InterpolationParams(sample_count=1)  # sample_count must be >= 2


class TestReturnOptions(unittest.TestCase):
    def test_default_values(self):
        options = ReturnOptions()
        self.assertEqual(options.value_type, ValueReturnType.DEFAULT)
        self.assertEqual(options.reference_type, ReferenceReturnType.DEFAULT)
        self.assertIsNone(options.pagination)
        self.assertIsNone(options.interpolation)

    def test_custom_values(self):
        pagination = PaginationParams(page=2, page_size=15)
        interpolation = InterpolationParams(enabled=False)

        options = ReturnOptions(
            value_type=ValueReturnType.PREVIEW,
            reference_type=ReferenceReturnType.FULL,
            pagination=pagination,
            interpolation=interpolation,
        )

        self.assertEqual(options.value_type, ValueReturnType.PREVIEW)
        self.assertEqual(options.reference_type, ReferenceReturnType.FULL)
        self.assertEqual(options.pagination, pagination)
        self.assertEqual(options.interpolation, interpolation)


class TestReturnOptionsFromDict(unittest.TestCase):
    def test_empty_dict(self):
        options = ReturnOptions.from_dict({})
        self.assertEqual(options.value_type, ValueReturnType.DEFAULT)
        self.assertEqual(options.reference_type, ReferenceReturnType.DEFAULT)
        self.assertIsNone(options.pagination)
        self.assertIsNone(options.interpolation)

    def test_none_dict(self):
        options = ReturnOptions.from_dict(None)
        self.assertEqual(options.value_type, ValueReturnType.DEFAULT)
        self.assertEqual(options.reference_type, ReferenceReturnType.DEFAULT)
        self.assertIsNone(options.pagination)
        self.assertIsNone(options.interpolation)

    def test_valid_dict(self):
        data = {
            "value_type": "preview",
            "reference_type": "simple",
            "pagination": {"page": 3, "page_size": 25},
            "interpolation": {
                "enabled": False,
                "sample_count": 15,
                "min_size_to_interpolate": 50,
                "include_endpoints": False,
            },
        }

        options = ReturnOptions.from_dict(data)

        self.assertEqual(options.value_type, ValueReturnType.PREVIEW)
        self.assertEqual(options.reference_type, ReferenceReturnType.SIMPLE)
        # Check pagination is not None before accessing its attributes
        self.assertIsNotNone(options.pagination, "Pagination should not be None")
        if options.pagination is not None:  # Type guard
            self.assertEqual(options.pagination.page, 3)
            self.assertEqual(options.pagination.page_size, 25)

        # Check interpolation is not None before accessing its attributes
        self.assertIsNotNone(options.interpolation, "Interpolation should not be None")
        if options.interpolation is not None:  # Type guard
            self.assertEqual(options.interpolation.enabled, False)
            self.assertEqual(options.interpolation.sample_count, 15)
            self.assertEqual(options.interpolation.min_size_to_interpolate, 50)
            self.assertEqual(options.interpolation.include_endpoints, False)

    def test_invalid_enum_values(self):
        data = {
            "value_type": "invalid_value_type",
            "reference_type": "invalid_reference_type",
        }

        options = ReturnOptions.from_dict(data)

        # Should fall back to defaults
        self.assertEqual(options.value_type, ValueReturnType.DEFAULT)
        self.assertEqual(options.reference_type, ReferenceReturnType.DEFAULT)

    def test_null_enum_values(self):
        data = {"value_type": None, "reference_type": None}

        options = ReturnOptions.from_dict(data)

        self.assertIsNone(options.value_type)
        self.assertIsNone(options.reference_type)

    def test_pagination_object(self):
        # Test with an object that has the necessary attributes but isn't a dict
        mock_pagination = MagicMock()
        mock_pagination.page = 5
        mock_pagination.page_size = 30

        data = {"pagination": mock_pagination}

        options = ReturnOptions.from_dict(data)
        self.assertIsNotNone(options.pagination, "Pagination should not be None")
        if options.pagination is not None:  # Type guard
            self.assertEqual(options.pagination.page, 5)
            self.assertEqual(options.pagination.page_size, 30)

    def test_invalid_pagination(self):
        data = {"pagination": "not a valid pagination object"}
        options = ReturnOptions.from_dict(data)
        self.assertIsNone(options.pagination)

    def test_interpolation_object(self):
        # Test with an object that has the necessary attributes but isn't a dict
        mock_interpolation = MagicMock()
        mock_interpolation.enabled = False
        mock_interpolation.sample_count = 5

        data = {"interpolation": mock_interpolation}

        options = ReturnOptions.from_dict(data)
        self.assertIsNotNone(options.interpolation, "Interpolation should not be None")
        if options.interpolation is not None:  # Type guard
            self.assertEqual(options.interpolation.enabled, False)
            self.assertEqual(options.interpolation.sample_count, 5)
            self.assertEqual(
                options.interpolation.min_size_to_interpolate, 20
            )  # Default
            self.assertEqual(options.interpolation.include_endpoints, True)  # Default

    def test_interpolation_boolean(self):
        data = {"interpolation": False}
        options = ReturnOptions.from_dict(data)
        self.assertIsNotNone(options.interpolation)
        if options.interpolation is not None:  # Type guard
            self.assertEqual(options.interpolation.enabled, False)
            self.assertEqual(options.interpolation.sample_count, 10)  # Default

    def test_invalid_interpolation(self):
        data = {"interpolation": "not a valid interpolation object"}
        options = ReturnOptions.from_dict(data)
        self.assertIsNone(options.interpolation)

    # Add the new test methods here
    def test_exception_handling_pagination(self):
        # Test exception handling in pagination processing
        # Create a mock that raises an exception when accessed
        class ExceptionPagination:
            @property
            def page(self):
                raise Exception("Test exception")

            @property
            def page_size(self):
                raise Exception("Test exception")

        data = {"pagination": ExceptionPagination()}
        options = ReturnOptions.from_dict(data)
        # Should gracefully handle the exception and set pagination to None
        self.assertIsNone(options.pagination)

    def test_exception_handling_interpolation(self):
        # Test exception handling in interpolation processing
        # Create a mock that raises an exception when 'enabled' is accessed
        mock_interpolation = MagicMock()
        # Define a property that raises an exception
        type(mock_interpolation).__getattribute__ = MagicMock(
            side_effect=Exception("Test exception")
        )

        data = {"interpolation": mock_interpolation}
        options = ReturnOptions.from_dict(data)
        # Should gracefully handle the exception and set interpolation to None
        self.assertIsNone(options.interpolation)

    def test_partial_interpolation_object(self):
        # Test with a simple object with just an enabled attribute
        class PartialInterpolation:
            def __init__(self):
                self.enabled = True
                # No other attributes

        partial_obj = PartialInterpolation()
        data = {"interpolation": partial_obj}
        options = ReturnOptions.from_dict(data)
        self.assertIsNotNone(options.interpolation)
        if options.interpolation is not None:
            self.assertEqual(options.interpolation.enabled, True)
            # Should use defaults for missing attributes
            self.assertEqual(options.interpolation.sample_count, 10)
            self.assertEqual(options.interpolation.min_size_to_interpolate, 20)
            self.assertEqual(options.interpolation.include_endpoints, True)

    def test_enum_type_direct_instances(self):
        # Test passing actual enum instances instead of strings
        data = {
            "value_type": ValueReturnType.FULL,
            "reference_type": ReferenceReturnType.SIMPLE,
        }

        options = ReturnOptions.from_dict(data)
        self.assertEqual(options.value_type, ValueReturnType.FULL)
        self.assertEqual(options.reference_type, ReferenceReturnType.SIMPLE)


if __name__ == "__main__":
    unittest.main()
