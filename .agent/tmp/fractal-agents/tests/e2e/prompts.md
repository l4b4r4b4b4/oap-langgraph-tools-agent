# Test Prompts for Math, Time, and Caching Tools

Below are comprehensive test prompts to verify the functionality of math and time toolsets, covering various response types, cross-tool usage, and reference handling patterns.

## Basic Time Tool Tests

### Current Time - Basic Usage
```
Show me the current time in UTC using the time tools.
```

### Current Time - Different Timezone
```
What time is it currently in Tokyo (timezone Asia/Tokyo)?
```

### List All Timezones
```
Show me a list of all available timezones.
```

### Convert Time - Basic
```
Convert 2023-01-01 12:00:00 from UTC to America/New_York timezone.
```

## Basic Math Tool Tests

### Simple Calculator
```
Use the calculate tool to compute 2 * (3 + 4) - 5.
```

### Using Mathematical Functions
```
Calculate the sine of π/2 using the math toolset.
```

### Complex Number Handling
```
Calculate the square root of -16 using the math toolset.
```

### Matrix Operations
```
Perform a matrix multiplication of [[1,2],[3,4]] and [[5,6],[7,8]].
```

### Random Number Generation
```
Generate 5 random numbers from a normal distribution with mean 50 and standard deviation 10.
```

### Sequence Generation
```
Generate the first 10 numbers in the Fibonacci sequence.
```
{
  "value": [
    0,
    1,
    1,
    2,
    3,
    5,
    8,
    13,
    21,
    34
  ],
  "reference": {
    "ref_id": "61a169b82721e0e3ebcdd2b94051e5915cba393bb4fb9f69370474665c93410a"
  }
}
## Value Type Tests

### Default Value Type
```
Get the current time in Los Angeles (America/Los_Angeles) with default return options.
```

### Full Value Type
```
Generate the first 30 Fibonacci numbers with options set to return the full value.
```

### Preview Value Type
```
List all timezones with options set to only show a preview of the results.
```

### Null Value Type (Reference Only)
```
Calculate π to 10 decimal places but only return a reference, not the value itself.
```

## Reference Type Tests

### Default Reference Type
```
Get the current time in London (Europe/London) and show the default reference format.
```

### Simple Reference Type
```
Calculate e^2 and return a simple reference (just the ref_id and cache_name).
```

### Full Reference Type
```
Get the current time in Sydney (Australia/Sydney) and return the full reference details.
```

### Null Reference Type (Value Only)
```
Calculate log(100) but don't return any reference, just the value.
```

## Cross-Tool Reference Usage

### Math-Only Reference Example
```
First, generate a random number between 1 and 10 using the random_generator tool and store it as a reference only.
Then, use that reference in the calculate tool to square the random number and return the value.
```

### Basic Reference Passing
```
First, calculate π using the math tool and store it as a reference with a full reference type.
Then, create a time at 2023-01-01 π:00:00 in UTC using that reference and convert it to Tokyo time.
```

### Chained References
```
First, get the current time in UTC and store just the reference.
Then, convert that time reference to Eastern time (America/New_York).
Finally, convert the Eastern time reference to Pacific time (America/Los_Angeles).
```

### Math to Time Reference
```
Calculate 12 * 3600 (seconds in 12 hours) and store it as a reference.
Then, get the current time in UTC.
Finally, add your 12 hours calculation reference to the current time and convert it to Tokyo time.
```

### Time to Math Reference
```
Get the current UNIX timestamp (using current_time in UTC and extracting the timestamp value) and store it as a reference.
Then use that timestamp reference in a calculation to convert it to hours by dividing by 3600.
```

## Simple vs. Complex Reference Passing

### Pass Simple Reference ID
```
Calculate π and get its reference ID.
Then calculate 2 * [the reference ID of π] using just the simple reference ID.
```

### Pass Reference Dictionary
```
Calculate e and store it with a simple reference.
Then calculate log([reference dictionary of e]) using the reference dictionary with ref_id and cache_name.
```

### Pass Full Reference Object
```
Get the current time in UTC with a full reference.
Then convert that time to Tokyo using the complete reference object.
```

## Nested Reference Usage

### Nested Math References
```
First, calculate π and store it as a reference A.
Then, calculate e and store it as a reference B.
Finally, calculate the expression: (reference A)^2 + (reference B)^2
```

### Nested Time and Math References
```
Get the current hour from UTC time (extract just the hour part) and store it as reference A.
Calculate 2^(reference A) and store the result as reference B.
Generate reference B random numbers between 1 and 100.
```

### Matrix with References
```
Calculate π and store it as a reference.
Create a matrix where the first element is the π reference and the rest are: [[π, 2], [3, 4]].
Then calculate the determinant of this matrix.
```

## Combined Tools Complex Workflows

### Time Difference Calculation
```
Get the current time in New York (America/New_York) and store it as reference A.
Get the current time in Tokyo (Asia/Tokyo) and store it as reference B.
Extract the timestamps from both references.
Calculate the time difference in hours between these two locations.
```

### Statistical Timing
```
Generate 10 random numbers using a normal distribution with options to store just a reference.
Get the current time before and after a complex math operation like calculating the first 50 Fibonacci numbers.
Calculate the time difference to see how long the operation took.
```

### Reference Chain Across Tools
```
Calculate π and store it as reference A.
Create a vector [π, 1, 2] using reference A.
Get the current time and store it as reference B.
Create a combined result showing both the vector and the formatted time.
```

## Error Handling Tests

### Invalid Timezone
```
Try to get the current time in an invalid timezone like "Moon/Dark_Side".
```

### Reference That Doesn't Exist
```
Try to convert a time using a reference ID that doesn't exist, like "nonexistent123".
```

### Type Mismatch in Reference Usage
```
Calculate π and store its reference.
Then try to use that numeric reference as a timezone in the current_time function.
```

### Invalid Mathematical Expression
```
Try to calculate "2 + * 3" which contains a syntax error.
```

## Pagination Tests

### Paginated Timezone List
```
List all timezones with pagination parameters set to page 2 with 10 items per page.
```

### Large Matrix with Pagination
```
Create a large 10x10 matrix filled with random numbers, then view just the first page of 5 rows.
```

## Complex Combined Workflows

### Time-based Random Seed
```
Get the current UNIX timestamp and use it as a seed for generating random numbers.
Generate 5 random numbers using this timestamp-based seed.
```

### Timezone Conversion Chain
```
Get the current time in UTC.
Convert it to New York time.
Convert the New York time to Tokyo time.
Convert the Tokyo time to London time.
Finally, convert the London time back to UTC and verify it matches the original time.
```

### Mathematical Time Series
```
Get the current hour (0-23) from UTC time.
Generate a sequence of prime numbers with a count equal to the current hour.
Create a matrix where each element is a prime number from your sequence.
Calculate the determinant of this time-based matrix.
```

### Reference Resolution Depth Test
```
Calculate π and store as reference A.
Calculate 2 * reference A and store as reference B.
Calculate reference B^2 and store as reference C.
Calculate √(reference C) and see if it resolves back to 2π.
```

### Cross-toolset Cache Verification
```
Calculate π with the math toolset and store its reference.
Get the current time and store its reference.
Verify that both references have different cache names (math_toolset vs time_toolset).
Try to use the time reference in a math calculation and the math reference in a time operation.
```

These test prompts cover a wide range of functionality for both math and time toolsets, testing various response types, cross-tool usage, and reference handling patterns. They should help you verify that your tools are functioning correctly across different usage scenarios.
