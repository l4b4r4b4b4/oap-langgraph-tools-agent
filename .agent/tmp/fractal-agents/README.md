# UAI Agents

### Testing Your Toolsets with Effective Prompts

Here are comprehensive test prompts to verify your math toolset is working correctly. These tests cover a wide range of mathematical operations and edge cases.

# Comprehensive Test Prompts for Time Toolset

Here's a set of prompts to thoroughly test the time toolset and its caching capabilities:

## 1. Basic Current Time Functions

**Prompt:**
```
What time is it right now in UTC? Then, can you tell me what time it is in Tokyo, New York, and London? Finally, what's the current Unix timestamp?
```
*This tests basic current_time functionality with different timezones and the unix_timestamp tool.*

## 2. Parse Different Date Formats

**Prompt:**
```
I have several dates in different formats that I need to standardize. Can you parse these for me?
- 2023-06-15 14:30:45
- 06/15/2023 2:30 PM
- June 15, 2023
- 15-Jun-2023
- 2023-06-15T14:30:45Z
```
*This tests the parse_datetime tool with multiple date format variations.*

## 3. Format Timestamps

**Prompt:**
```
I have the Unix timestamp 1623765045. Can you format this in the following ways:
1. Standard date and time in UTC
2. As YYYY-MM-DD in Tokyo timezone
3. As "Month Day, Year" format in Los Angeles timezone
4. As DD/MM/YYYY HH:MM in Berlin timezone
```
*This tests the format_datetime tool with different output formats and timezones.*

## 4. Time Difference Calculations

**Prompt:**
```
I need to calculate the time difference between several date pairs:
1. From January 1, 2023 to December 31, 2023
2. From 2023-06-15 14:30:00 to 2023-06-16 09:45:30
3. From 12/31/1999 23:59:59 to 01/01/2000 00:00:01
```
*This tests the time_difference tool with different date ranges.*

## 5. Timezone List

**Prompt:**
```
Can you show me a list of available timezones? After that, tell me the current time in three random timezones from that list.
```
*This tests the list_timezones tool and verifies the timezone data is accessible.*

## 6. Caching Verification - Reference Mode

**Prompt:**
```
Lets test tool call by reference:
1. get the current time in Tokyo and the time in New York (use return_type="reference").
2. Then use that reference to calculate the time difference between the two again with (use return_type="reference"), s
3. then calculate what time it would be 12 hours later.

Finally, get all values by reference id using the cache toolset and check if everything was done and calculated correctly!
```
*This tests the reference return type and using a reference as input to another tool.*

## 7. Caching Verification - Preview Mode

**Prompt:**
```
Parse the date "December 25, 2023" with return_type="preview". Then parse "July 4, 1776" with return_type="full". Can you see the difference in how these results are displayed?
```
*This tests the preview return type functionality.*

## 8. Cross-Tool Caching

**Prompt:**
```
Calculate the time difference between "2023-01-01 00:00:00" and "2024-01-01 00:00:00". Then, without re-parsing the dates, calculate the time difference between "2023-01-01 00:00:00" and "2023-06-01 00:00:00". Has the system reused the parsed date information?
```
*This tests if the parse_datetime results are cached when used in time_difference calculations.*

## 9. Time Calculation Chain

**Prompt:**
```
Get the current time in UTC. Then, get the Unix timestamp for that exact time. Next, take that timestamp, add 86400 to it (seconds in a day), and format the resulting timestamp as a human-readable date. Finally, calculate the time difference between the original time and this new time.
```
*This tests a chain of time-related operations using results from previous steps.*

## 10. Cache Hit Verification

**Prompt:**
```
Get the current time in Tokyo. Then immediately get the current time in Tokyo again. Check if the second request used cached data (the timestamps should be identical if cached). Then wait 15 seconds and try a third time - the cache should have expired for the non-deterministic time cache.
```
*This tests cache hit and expiration for non-deterministic data.*

## 11. Deterministic Cache Test

**Prompt:**
```
Parse the date "1969-07-20" (Moon landing). Then parse it again and again. Check if all attempts use the cached result. Now let's parse "1969-07-21" and see if that's a separate cache entry.
```
*This tests deterministic caching for date parsing.*

## 12. Error Handling

**Prompt:**
```
Try parsing an invalid date like "February 30, 2023". What error message do you get? Now try getting the current time in an invalid timezone like "Atlantis". How does the system handle these errors?
```
*This tests error handling for invalid inputs.*

## 13. Cache Stats Tool

**Prompt:**
```
Run a few time operations of your choice. Then use the get_cache_stats tool to see information about cache usage. What's the hit/miss ratio? How many entries are stored in the cache?
```
*This tests the cache statistics reporting feature.*

## 14. Combined Functionality for Real Use Case

**Prompt:**
```
I'm planning a video conference with participants in Tokyo, New York, and London. The meeting is scheduled for 9:00 AM Eastern Time on December 15, 2023. Can you tell me what time that would be for participants in each location? Also, how many hours difference is there between each pair of locations?
```
*This tests a realistic use case combining multiple time toolset features.*

## 15. Long-Term Calculations

**Prompt:**
```
Calculate how many days there are between January 1, 1900 and January 1, 2000. Then calculate how many weeks that is. Finally, if someone was born on January 1, 1950, how old would they be in years as of today?
```
*This tests time_difference with longer time periods and different units.*

## Testing Procedure

For each prompt:
1. Execute the requested operations using the time toolset tools.
2. Verify that results are accurate and properly formatted.
3. For caching tests, check if the system properly reuses cached values.
4. For reference mode tests, confirm that references can be successfully used as inputs to other operations.
5. Monitor how the system handles edge cases and errors.

These prompts will help verify that your time toolset is functioning correctly and that the caching system is properly supporting the three key features:
1. Cross-tool and cross-toolset value caching
2. Different return modes (full, preview, reference)
3. Usage of cached value references as inputs to other tools

## Math Toolset Tests

Use the `calculate` tool to perform the following calculations:

### Basic Arithmetic
1. `2 + 3 * 4` - Tests order of operations
2. `(7 - 3) / 2` - Tests parentheses and division
3. `10 ** 2` - Tests exponentiation
4. `16 // 5` - Tests floor division
5. `17 % 5` - Tests modulo operation

### Trigonometric Functions
6. `sin(pi/2)` - Should return 1
7. `cos(0)` - Should return 1
8. `tan(pi/4)` - Should return approximately 1
9. `asin(0.5)` - Should return π/6 (approx. 0.5236)
10. `atan2(1, 1)` - Should return π/4 (approx. 0.7854)

### Other Mathematical Functions
11. `sqrt(16)` - Should return 4
12. `log(10)` - Should return natural logarithm (approx. 2.3026)
13. `exp(2)` - Should return e² (approx. 7.3891)
14. `log10(100)` - Should return 2
15. `factorial(5)` - Should return 120

### Complex Expressions
16. `2 * sin(pi/6) + 3 * cos(pi/3)` - Combined trig expressions
17. `sqrt(16) + log(exp(3))` - Combined operations with inverse functions
18. `(sin(pi/4) ** 2) + (cos(pi/4) ** 2)` - Trig identity (should be 1)
19. `floor(3.7) + ceil(2.2)` - Combined rounding operations
20. `(factorial(4) / factorial(2)) * sqrt(16)` - Combined factorial and roots

### Complex Number Operations
21. `sqrt(-1)` - Should return the imaginary unit i
22. `sqrt(-4)` - Should return 2i
23. `log(-10)` - Should return a complex number
24. `(3+4j) * (1+2j)` - Complex multiplication
25. `(3+4j) / (1+2j)` - Complex division

### Mathematical Constants
26. `pi` - Should return 3.141592...
27. `e` - Should return 2.718281...
28. `sin(pi)` - Should be very close to 0
29. `log(e)` - Should return 1
30. `pi**2` - Should return π²

### Combined Trigonometric Expressions
31. `sin(pi/6)**2 + cos(pi/6)**2` - Should return 1 (trig identity)
32. `sin(2*pi/3) / cos(2*pi/3)` - Should equal tan(2π/3)
33. `asin(sin(0.5))` - Should return 0.5
34. `degrees(pi/2)` - Should return 90
35. `radians(180)` - Should return π

### Nested Functions
36. `sqrt(sqrt(16))` - Should return 2
37. `log10(log10(10**10))` - Should return 1
38. `sin(cos(tan(0.1)))` - Nested trig functions
39. `floor(ceil(floor(3.7)))` - Nested rounding functions
40. `factorial(floor(2.7))` - Should compute factorial(2)

### Numerical Methods
41. `abs(-3.14)` - Should return 3.14
42. `gcd(1071, 462)` - Should return 21
43. `round(3.14159, 2)` - Should return 3.14
44. `exp(log(7))` - Should return 7
45. `log2(1024)` - Should return 10

### Expressions with Different Formats
46. `1+2 +3+ 4 +5` - Expression with irregular spacing
47. `(((3 + 4) * 2) / 7)` - Deeply nested parentheses
48. `3 * -4` - Negative numbers
49. `1 / (1 + exp(-5))` - Sigmoid function calculation
50. `1e3 + 2e2` - Scientific notation

### Edge Cases
51. `0 / 0` - Should raise division by zero error
52. `1 / 0` - Should raise division by zero error
53. `1 / (1e-100)` - Very small denominator
54. `sin(1e100) / 1e100` - Very large input with scaling
55. `factorial(0)` - Edge case for factorial (should return 1)
56. `0 ** 0` - Mathematically undefined but conventionally 1
57. `log(1e-100)` - Log of very small number

### Security Tests (Should Be Rejected)
58. `__import__('os').system('ls')` - Attempt to import module
59. `exec("print('hello')")` - Attempt to use exec function
60. `open('/etc/passwd').read()` - Attempt to open file
61. `eval("2+2")` - Attempt to use eval function
62. `globals()` - Attempt to access globals

## Testing Procedure

1. Use the `calculate` tool with each expression.
2. Verify that the result matches the expected output.
3. For error cases, verify that appropriate error messages are returned.
4. For security tests, verify that the validator correctly identifies and rejects unsafe expressions.

## Expected Results

- Basic arithmetic, trigonometric functions, and other standard mathematical operations should return precise numerical results.
- Complex number operations should return appropriate complex values when necessary.
- Edge cases should either return mathematically correct results or appropriate error messages.
- Security tests should be rejected with validation errors before execution.

These tests will help ensure that your `calculate` function handles a comprehensive range of mathematical operations correctly and securely.



## Comprehensive Test Prompts for Crypto API Toolset

This guide provides detailed test prompts to verify that your Cryptocurrency API toolset is functioning correctly. These tests cover all tools, edge cases, and practical usage scenarios.

### Testing `get_coin_info` Tool

1. **Basic Bitcoin Information**
   ```
   Use the get_coin_info tool to retrieve detailed information about Bitcoin.
   ```

2. **Ethereum Details**
   ```
   Get comprehensive information about Ethereum using the get_coin_info tool.
   ```

3. **Mid-Cap Altcoin**
   ```
   Use get_coin_info to show me detailed data about Solana (SOL).
   ```

4. **Lower Market Cap Token**
   ```
   Retrieve information for Chainlink using the get_coin_info tool.
   ```

5. **Edge Case: Non-existent Coin**
   ```
   Use get_coin_info to get data for "nonexistentcoin123456".
   ```

### Testing `get_coin_price` Tool

6. **Single Coin Price**
   ```
   Use get_coin_price to check the current price of Bitcoin in USD.
   ```

7. **Multiple Coins**
   ```
   Get the prices for Bitcoin, Ethereum, and Solana using get_coin_price.
   ```

8. **Multiple Currencies**
   ```
   Check Bitcoin's price in USD, EUR, and JPY using get_coin_price.
   ```

9. **Multiple Coins and Currencies**
   ```
   Use get_coin_price to retrieve prices for Bitcoin and Ethereum in both USD and EUR.
   ```

10. **Edge Case: Invalid Coins/Currencies**
    ```
    Get prices for "bitcoin,invalidcoin123" in "usd,xyz" using get_coin_price.
    ```

### Testing `get_trending_coins` Tool

11. **Basic Trending Data**
    ```
    Use get_trending_coins to show me which cryptocurrencies are currently trending.
    ```

12. **Analyze Trending Data**
    ```
    Retrieve trending coins using get_trending_coins and explain why they might be trending.
    ```

### Testing `get_global_market_data` Tool

13. **Overall Market Status**
    ```
    Use get_global_market_data to provide an overview of the current cryptocurrency market.
    ```

14. **Market Dominance Analysis**
    ```
    Check get_global_market_data to analyze Bitcoin's current market dominance.
    ```

15. **Market Capitalization Analysis**
    ```
    Use get_global_market_data to tell me the total cryptocurrency market capitalization and how it changed in the last 24 hours.
    ```

### Testing `get_historical_price` Tool

16. **Bitcoin 7-Day History**
    ```
    Use get_historical_price to show Bitcoin's price history for the past 7 days.
    ```

17. **Ethereum 30-Day History**
    ```
    Retrieve Ethereum's 30-day price history using get_historical_price.
    ```

18. **Long-Term History (365 Days)**
    ```
    Get Bitcoin's price data for the past year using get_historical_price with days=365.
    ```

19. **Alternative Currency History**
    ```
    Use get_historical_price to check Solana's price history for 14 days in EUR instead of USD.
    ```

20. **Edge Case: Exceeding Maximum Days**
    ```
    Try to get 500 days of historical data for Bitcoin using get_historical_price.
    ```

### Testing `search_coins` Tool

21. **Basic Search**
    ```
    Use search_coins to find cryptocurrencies related to "defi".
    ```

22. **Specific Coin Search**
    ```
    Search for coins with "bitcoin" in their name using search_coins.
    ```

23. **Partial Name Search**
    ```
    Use search_coins to find cryptocurrencies that contain "chain" in their name.
    ```

24. **Symbol Search**
    ```
    Search for coins with the symbol "ETH" using search_coins.
    ```

25. **Edge Case: Very Short Query**
    ```
    Use search_coins to search for coins with just the letter "a".
    ```

### Testing `get_top_coins` Tool

26. **Top 10 Coins**
    ```
    Use get_top_coins to show me the top 10 cryptocurrencies by market cap.
    ```

27. **Top 25 in EUR**
    ```
    Get the top 25 cryptocurrencies with prices in EUR using get_top_coins.
    ```

28. **Large Dataset (100+ Coins)**
    ```
    Retrieve the top 100 cryptocurrencies using get_top_coins and summarize the data.
    ```

29. **Edge Case: Maximum Count**
    ```
    Try to get the maximum allowed number of top coins (250) using get_top_coins.
    ```

30. **Alternative Base Currency**
    ```
    Use get_top_coins to show the top 10 cryptocurrencies with prices in BTC instead of USD.
    ```

### Combined Tool Tests

32. **Market Analysis Workflow**
    ```
    First, get global market data. Then, retrieve the top 10 coins. Finally, get detailed information about the #1 ranked coin.
    ```

33. **Coin Research Workflow**
    ```
    Search for coins containing "exchange" in their name, get detailed information about one of the results, then check its historical price for the last 30 days.
    ```

34. **Price Comparison Workflow**
    ```
    Get the current prices for the top 5 cryptocurrencies, and then compare their 24-hour price change percentages.
    ```

35. **Trending Coin Analysis**
    ```
    Get the list of trending coins, then for each of the top 3 trending coins, retrieve detailed information and 7-day price history.
    ```

### Error Handling Tests

36. **Rate Limit Testing**
    ```
    Make multiple rapid requests to test how the toolset handles rate limiting from the CoinGecko API.
    ```

37. **Invalid Input Handling**
    ```
    Test each tool with invalid inputs to verify proper error handling and informative error messages.
    ```

38. **Network Error Recovery**
    ```
    Test how the toolset behaves when network connectivity is intermittent (you may need to simulate this).
    ```

### Cache Testing

39. **Cache Hit Verification**
    ```
    Make the same request twice in quick succession to verify that the second request uses cached data.
    ```

40. **Cache Expiry Testing**
    ```
    Make a request, wait for the cache to expire (based on the cache settings), then make the same request again to verify fresh data is retrieved.
    ```

## Testing Procedure

1. Use each tool with the provided test prompts.
2. Verify that the results match expected outputs and formats.
3. For error cases, verify that appropriate error messages are returned.
4. For combined workflows, ensure that data flows correctly between tools.
5. Examine the logs to verify caching behavior is working as expected.

## Expected Results

- Basic information retrieval should return well-structured data with current market information.
- Price data should include current prices and related metrics (market cap, volume, etc.).
- Historical data should show price trends over the requested period.
- Search functionality should return relevant coins based on the query.
- Top coins listing should accurately reflect market capitalization rankings.
- All tools should handle invalid inputs gracefully with informative error messages.
- Caching should work effectively to minimize API calls while keeping data reasonably fresh.

These tests will help ensure your Cryptocurrency API toolset handles a comprehensive range of scenarios correctly, responds appropriately to valid and invalid inputs, and makes efficient use of API resources through proper caching.

## 1. Video Search

**Prompt:**
```
I'm hosting a 90s nostalgia party this weekend and need the perfect playlist. Can you find some iconic music videos from the 1990s that everyone will recognize? Maybe include some Backstreet Boys, Spice Girls, or Nirvana?
```

*This tests the basic video search functionality with a fun theme.*

## 2. Transcript Preview

**Prompt:**
```
I heard there's this hilarious TED Talk by Tim Urban where he talks about procrastination and a 'panic monster.' Can you find it and show me a preview of the transcript so I can see if it's the one I'm thinking of?
```

*This tests the transcript preview feature with a specific, recognizable video.*

## 3. Full Transcript

**Prompt:**
```
I'm studying rhetoric and public speaking. Can you find a clip of the top 10 moments of Donald Trump on Joe Rogan's podcast from YouTube, get the full transcript and use it to do a analysis of his language patterns and memorable phrases?
```

*This tests the full transcript feature with an iconic historical speech.*

## 4. Transcript Chunk

**Prompt:**
```
Could you just pull out the segments where Trump discusses his views on a rigged election and free speech?
```

*This tests the transcript chunk functionality with a practical use case.*

## 5. Video Comments

**Prompt:**
```
I'd like to see how viewers responded to these specific points. Can you show me the top comments from that Joe Rogan podcast clip where people are specifically discussing Trump's stance on free speech and platform censorship? I'm curious if the audience generally agrees or disagrees with his perspective.
```

*This tests the comments functionality with a well-known viral video.*

## 6. Channel Information

**Prompt:**
```
I've been hearing a lot about Lex Fridman's podcast recently. Can you search for his YouTube channel and tell me about him? I'd like to know how many subscribers he has, what kind of content he makes, and when he started his channel.
```
*This tests the channel info functionality with a popular creator.*

## 7. List Available Transcripts

**Prompt:**
```
I'm learning languages and like to watch videos with different subtitles. Can you find a popular TED Talk and tell me what languages are available for its transcript? I'm especially hoping for Spanish and French options.
```

*This tests the transcript language listing feature.*

## 8. Video Details

**Prompt:**
```
My friend keeps talking about this 'Gangnam Style' video that apparently broke YouTube's view counter years ago. Can you find it and tell me exactly how many views it has now, when it was published, and other interesting stats?
```

*This tests the detailed video information functionality with a record-breaking video.*

## 9. Combination Test

**Prompt:**
```
I'm doing research on social media. Can you search for videos from the 'Kurzgesagt' channel about it, then show me the channel information, get the transcript of their most viewed video, and show me some of the top comments to see how people are responding to the content?
```

*This tests multiple features working together in a realistic research scenario.*

## 10. Bonus Fun Challenge

**Prompt:**
```
Find the most popular youtube video exactly 10 years ago by day and hour, pull video details, top comments and a preview of availoable transcripts. Ping me with @User once you're ready!
```

Does the caching solution enable the folloinwg:
1. cross tool & toolset value caching,
2. return mode as full, preview or as reference
3. use cached value reference by structured and hased id as input argument to a tool.

the chached wrapper hence hase to:
1. enable cross tool & toolset caching with a structured id string convention
2. pick up on response mode and return the right value(s)
3. pick up on reference ids in the input args, retrieve value from cache and parse it in before fowarding the input args obj to the underlaying tool funciton.
