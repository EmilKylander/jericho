## 2021-12-03 - 0.0.7

1. Fixed a bug where the private method _chunks could crash if the list is empty (E.g from no online results)
2. Improved the log formatter so it only display cluster information if clustering is enabled
3. Moved hard-coded user agent to a property
4. Changed private method _send to work with async instead of running it explicitly in a newly created event loop