Problem Statement: 

Given a basic mock of a server that simulates an exchange, the task is to maximise the number of requests sent to the server, while ensuring that the rate limit is not exceeded.
The server has a rate limit of 20 requests per second per API key, and will return a 429 error if the rate limit is exceeded. To simulate network latency, the server will randomly delay each request by up to 50ms.
The goal is to implement a rate limiter on the client side that ensures that the rate limit is not exceeded, while maximising the number of requests sent to the server.

Server Mock:
- The server mock is a simple Flask server that simulates an exchange. 
- It has a rate limit of 20 requests per second per API key, and will return a 429 error if the rate limit is exceeded. 
- It also contains a stubbed list of API keys which it will accept and throws a 401 error if the API key is not in the list.
- To simulate network latency, the server will randomly delay each request by up to 50ms.

Approach:

1. How do I benchmark the performance of the code?

Used the number of successful HTTP Requests sent by the client to the server over the course of 10 seconds as a benchmark for the performance of the code.

Results of the original implementation:

Benefits:
- Simple to implement: Have the event loop run for 10 seconds, while keeping a count of the number of successful HTTP requests sent by the client to the server (along with the number of failed and skipped requests) and output the results
into an output.txt file for ease of tracking.
- Short feedback loop, but sufficiently long to notice any improvements (if any), outside of random chance due to network latency or simulated delays.

Considerations: 
- Balance between maximising API calls, while not overloading the server with too many requests, incurring error 429 responses. If the number of error 429 responses sent with a particular API key exceeds 10, the API key can no longer be used.
- How do we handle Requests objects that have been created and added to the queue more than 1 second ago from the time it is being processed - do we add them back into the queue with the goal of sending as many requests generated as possible to the server, or do we simply drop them as they are now outdated? Given that the task at hand is to simulate an exchange, I have chosen to drop them, as sending an order to the exchange after a certain time has passed can result in unexpected behaviour, such as the order causing unexpected returns due to the price of the asset possibly having changed significantly since the order was created.

2. Are there any significant bottleneck in the existing client implementation?

Approach: Install the cProfile module and run the client code with the cProfile module to identify any significant bottlenecks in the existing client implementation.

Findings: I was unable to find any significant bottlenecks in the existing client implementation. This suggests to me that the existing client implementation is already quite efficient, and that that, if there is any improvements to be made to the throughput, it would have to be on the implementation of the rate limiter itself, as opposed to any form of optimisation.

3. Can the rate limiter design be improved?

Thoughts: The original rate limiter design was overly "safe" to avoid hitting the API limit. Specifically the choice to not allow two consecutive requests to be sent to the server with the same API key if they are less than 50ms apart. 

Approach 1: A more intuitive implementation of a rate limiter

I opted to create a rate limiter class, DequeRateLimiter, that uses a deque to store the time of requests sent. The original design pops from the left all requests that are older than 1 second, and then checks if the number of requests left in the queue is less than the maximum number of requests allowed per second. If it is, the request is sent, and the time of the request is added to the right of the deque. If it is not, we check the time difference between this current request and the oldest request, and sleep for the difference in time.

This implementation greatly improved throughput, but also incurred frequent 429 errors. A solution that I came up with was to instead limit the number of requests allowed within that deque to be one less than the maximum number of requests allowed per second. This implementation also greatly improved throughput, and incurred no 429 errors in my 10 second benchmark, or subsequent longer running tests.

Results of this implementation:



Approach 2: A revised version of the original circular array implementation

This is because I mistakenly assumed that the time difference between the xth request and the (x-19)th request logged on the client side would be the same as that of the server side. This is not true. Due to the randomised delay on the server end, the time difference between the xth request and the (x-19)th request logged on the server side is not guaranteed to be 1 second. 

Consider the following case whereby the (x-19)th request incurs the maximum 50 ms delay, while the xth request incurs no delay at all. This means that the time difference between the xth request and the (x-19)th request logged on the server side is only 950ms.

As such, I tweaked the original implementation to check whether the time difference and the earliest time request (found in the circular array) is greater than 1000 ms + 50 ms (maximum delay) + 1 ms (buffer for any potential latency in the transmission of data from the client to the server). If it is, the request is sent, and the time of the request is added to the circular array. If it is not, we sleep for the difference in time.

This implementation also greatly improved throughput, and incurred no 429 errors in my 10 second benchmark, or subsequent longer running tests.

Results of this implementation:

4. Asyncio vs Multiprocess


Attempt at using the multiprocessing package to recreate a similar client implementation.
- Create a process to handle request generation, and 5 others to handle request sending using each of the respective API keys.
- Tweak Counter class to use locks to ensure that the counter is updated atomically.
- Tweak the rate limiter to not use an asynchronous context manager, and instead use a regular context manager.

Results of this implementation:

Findings: The multiprocessing package does not perform as well for this task, as the overhead of creating and managing the processes is too high, and the performance of the code is worse than the original asyncio implementation. This is likely due to the fact that the task at hand is I/O bound, and not CPU bound, and that the overhead of creating and managing the processes is too high to justify the performance gains.

A possible choke area:
- Having to access the counter object in the rate limiter class or the shared Queue of generated requests, which is shared across all processes. This results in overhead as the processes have to wait for the lock to be released before they can access the counter object or the shared Queue of generated requests.