import re


def with_tool_options(*, pagination=False, interpolation=False):
    """
    Decorator that adds standardized documentation for tool options.

    Parameters:
    - pagination: Whether this tool supports pagination
    - interpolation: Whether this tool supports interpolation

    This decorator preserves existing docstring sections and only
    replaces or augments the options-related documentation.
    """

    def decorator(func):
        # Start with the original docstring
        original_doc = func.__doc__ or ""

        # Parse the original docstring to identify sections
        sections = {}
        current_section = "main"
        lines = original_doc.split("\n")
        sections[current_section] = []

        for line in lines:
            stripped = line.strip()
            if stripped.endswith(":") and not line.startswith("    "):
                # This looks like a section header
                current_section = stripped[:-1].lower()  # remove the colon
                sections[current_section] = [line]
            else:
                sections[current_section].append(line)

        # Prepare the options section
        options_section = ["    Options:"]
        options_section.append(
            "    This tool supports the following options parameter configurations:"
        )

        # Always include value return types documentation
        options_section.extend(
            [
                "",
                "    - value_type: Controls how the value is returned",
                '      - "default": Smart return - full for small results, preview for large ones (default)',
                '      - "full": Always return the complete value',
                '      - "preview": Always return a preview',
                "      - None: Don't return a value (reference only)",
            ]
        )

        # Always include reference return types documentation
        options_section.extend(
            [
                "",
                "    - reference_type: Controls how the reference is returned",
                '      - "default": Return minimal reference ID (default)',
                '      - "simple": Return reference ID and cache name',
                '      - "full": Return complete reference details',
                "      - None: Don't return a reference",
            ]
        )

        # Add pagination documentation if this tool supports it
        if pagination:
            options_section.extend(
                [
                    "",
                    "    - pagination: Optional pagination parameters for value-returning responses",
                    "      - page: Page number to retrieve (starting from 1)",
                    "      - page_size: Number of items per page",
                    "",
                    "      Example:",
                    "      ```python",
                    "      result = tool_name(",
                    '          input_data={"param": "value"},',
                    '          options={"pagination": {"page": 2, "page_size": 10}}',
                    "      )",
                    "      ```",
                ]
            )

        # Add interpolation documentation if this tool supports it
        if interpolation:
            options_section.extend(
                [
                    "",
                    "    - interpolation: Optional interpolation parameters for sampling large collections",
                    "      - enabled: Whether interpolation is enabled (default: True)",
                    "      - sample_count: Number of items to sample (default: 10)",
                    "      - min_size_to_interpolate: Minimum collection size to trigger interpolation (default: 20)",
                    "      - include_endpoints: Whether to include first and last elements (default: True)",
                    "",
                    "      Example:",
                    "      ```python",
                    "      result = tool_name(",
                    '          input_data={"param": "value"},',
                    '          options={"interpolation": {"sample_count": 5, "include_endpoints": True}}',
                    "      )",
                    "      ```",
                ]
            )

        # Build the new docstring
        new_sections = []

        # Add main section first
        if "main" in sections:
            new_sections.extend(sections["main"])

        # Add parameters section with our options documentation
        if "parameters" in sections:
            # Find where the options parameter is documented
            options_pattern = re.compile(r"^\s*-\s*options:", re.MULTILINE)
            param_lines = "\n".join(sections["parameters"])

            if options_pattern.search(param_lines):
                # Replace the existing options documentation
                lines = []
                options_started = False
                next_param_started = False

                for line in sections["parameters"]:
                    if options_started and (
                        line.strip().startswith("-") or line.strip() == ""
                    ):
                        # We've reached the next parameter or the end of the params
                        next_param_started = True

                    if options_pattern.search(line):
                        # Found start of options documentation
                        options_started = True
                        lines.append(line)  # Keep the "- options:" line
                        lines.extend(options_section)
                    elif not options_started or next_param_started:
                        # Keep lines that are not part of options or after options section
                        lines.append(line)

                new_sections.extend(lines)
            else:
                # Options parameter not found, add it after other parameters
                new_sections.extend(sections["parameters"])
                # Make sure there's a blank line before options
                if new_sections[-1].strip() != "":
                    new_sections.append("")
                new_sections.append(
                    "    - options: Optional parameter to control how results are returned:"
                )
                new_sections.extend(options_section)

        # Add remaining sections in their original order
        for section_name, section_lines in sections.items():
            if section_name not in ["main", "parameters"]:
                # Add a blank line before the section if needed
                if new_sections and new_sections[-1].strip() != "":
                    new_sections.append("")
                new_sections.extend(section_lines)

        # Update the docstring
        func.__doc__ = "\n".join(new_sections)

        # Add flags for runtime introspection
        func._supports_pagination = pagination
        func._supports_interpolation = interpolation

        return func

    return decorator
