# 2021-12-12 0.1.18

1. In the previous version, we send X amount of HEAD HTTP requests and wait for them, then we send X amount of GET requests
to the websites that respond to the HEAD responses. This is blocking because some threads are being idle after they're done working
and we are blocking the Jericho until the complete results have been returned. To mitigate this issue Jericho is now sending the domain list
to threaded_async_http that will send the HEAD HTTP requests but will save the result directly to the work queue where a GET request is issued
immediately to an available thread.

# 2021-12-06 0.1.15

1. Added experimental support for web scraping
2. Replaced loop.run_until_complete with asyncio.run in the tests

# 2021-12-06 0.0.15

1. Added http and https adding when its needed instead of bulk to avoid overhead
2. Added a cli argument so http and https is added automatically to missing hosts
3. Moved code where text strings are checked in the result content for better speed

## 2021-12-05 - 0.0.14

1. Added a check which compares the content type of the 404 page and the result page, only run text analysis if the content types are the same

## 2021-12-05 - 0.0.12

1. Fixed a bug where replica servers used its own endpoint repository instead of the source supplied endpoints
2. Changed terminology from master/slave to source/replica
3. Changed terminology from blacklist to excluded

## 2021-12-05 - 0.0.11

1. Check if the domain list exists before processing
2. Fixed a bug where the batch size was too large
3. Added a new CLI argument where you can specify the domain batch size
4. Added Final through typing to better keep track of "constants" which can be changed dynamically in Python

## 2021-12-05 - 0.0.10

1. Added log level override through CLI

## 2021-12-05 - 0.0.9

1. Added automatic upgrade through CLI

## 2021-12-03 - 0.0.8

1. Added asyncio.run instead of run_until_complete
2. Fixed Scanned() log count
3. Added info as default log instead of debug
4. Removed legacy cli argument

## 2021-12-03 - 0.0.7

1. Fixed a bug where the private method _chunks could crash if the list is empty (E.g from no online results)
2. Improved the log formatter so it only display cluster information if clustering is enabled
3. Moved hard-coded user agent to a property
4. Changed private method _send to work with async instead of running it explicitly in a newly created event loop