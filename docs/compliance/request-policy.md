# Request Policy

Project: Historical Auction Price Prediction  
Researcher: Amber J. Robbins  
Initial review date: 2026-10-07  
Last reviewed: 2026-10-17

## Purpose
Defines the measures taken when sending requests to the MAC.BID API to ensure that the data collection process remains ethical and polite.

### Access boundaries
- Access only publicly available, unauthenticated API endpoints.
- No usage of login credentials, authentication tokens, session cookies, or private API keys.
- Do not attempt to bypass any responses which indicate that authentication or authorization is required.
- Avoid repeated API calls as much as possible.
- Do not use any tools, like proxy rotation, meant to evade measures like rate limits.

### Request pacing
- Permit no more than one active request to MAC.BID at a time.
- Wait at least one second between consecutive requests.
- Enable AutoThrottle so delays may increase when response latency rises.
- AutoThrottle may never reduce the delay below one second.

### Retries and stopping behavior
- Retry connection failures, timeouts, and HTTP 500, 502, 503, and 504 responses at most once. 
- Never retry other error responses (including 400, 401, 403, 404, and 429).
- Log every error response and failed request.
- Review the log after each collection run. After any 401, 403, or 429 response, do not start another run until I have reviewed the cause (and waited at least the Retry-After time, for a 429).
- Stop collecting if errors repeat, or if MAC.BID asks me to stop.
- Apply the normal one-second delay to retries.


### Collection scope
- Collect data from only the Henderson and North Las Vegas locations.
- Generate a candidate list before each collection run that enables targeted data collection.
- Retain only fields relevant to the application purpose and research goals. 
- Exclude customer-level fields, such as `bidder_id` and `winning_bidder_id` (although both are already anonymized). No truly sensitive information pertaining to bidders will be parsed and then retained. 

### Identification and records
- Include a descriptive User-Agent in the request header which contains the project purpose and contact email.
- Keep detailed logs of all requests, containing information such as the request counts, response status codes, retry counts, cache usage, start and stop times, and the reason behind an interrupted run. 
- Record the collection timestamp and requested URL separately from the response data.