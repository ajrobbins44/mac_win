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

## Request pacing
- Permit no more than one active request to MAC.BID at a time.
- Wait at least one second between consecutive requests.
- Enable AutoThrottle so delays may increase when response latency rises.
- AutoThrottle may never reduce the delay below one second.

### Retries and stopping behavior
- Do not retry 400, 401, 403, or 404 responses.
- Permit no more than one retry for connection failures, timeouts,
  and designated transient server errors.
- On a 401 or 403 response, stop requests to the affected endpoint
  and review the access policy before continuing.
- On a 429 response, honor Retry-After when present and pause collection.
- If a second 429 occurs during the same run, terminate the run and
  revise the request rate before restarting.
- Stop the run if repeated 5xx responses suggest service instability.

### Collection scope
- Collect data from only the Henderson and North Las Vegas locations.
- Generate a candidate list before each collection run that enables targeted data collection.
- Retain only fields relevant to the application purpose and research goals. 
- Exclude customer-level fields, such as `bidder_id` and `winning_bidder_id` (although both are already anonymized). No truly sensitive information pertaining to bidders will be parsed and then retained. 

### Identification and records
- Include a descriptive User-Agent in the request header which contains the project purpose and contact email.
- Keep detailed logs of all requests, containing information such as the request counts, response status codes, retry counts, cache usage, start and stop times, and the reason behind an interrupted run. 
- Record the collection timestamp and requested URL separately from the response data.