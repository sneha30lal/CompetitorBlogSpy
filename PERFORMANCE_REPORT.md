# Performance and Detection-Time Report

## 1. Purpose

This report documents the performance and detection-time testing performed for Competitor Blog Spy.

The assignment requires measurement of actual detection time, comparison of monitoring strategies, multi-site monitoring, and investigation of performance at larger scale.

## 2. Detection Strategies Tested

The system supports and was tested with all three required monitoring strategies:

1. RSS/Atom feed monitoring
2. XML sitemap monitoring
3. Direct-page monitoring

The system automatically investigates a website and selects an available monitoring source.

## 3. Controlled Detection Testing

Controlled demonstration websites were used to test the three monitoring strategies.

### Sitemap Monitoring

An earlier controlled sitemap test recorded:

- Detection delay: 191.58 seconds
- Result: New article detected successfully

A later controlled sitemap test recorded:

- Publication time: 2026-10-05 15:02:27
- First discovery time: 2026-10-05 15:11:07.041714
- Detection delay: 520.04 seconds
- Result: New article detected successfully

The 520.04-second result is an actual measured detection delay. The system records the detection timestamp independently of when the dashboard is viewed.

### Direct-Page Monitoring

A controlled direct-page test recorded:

- Detection delay: 59.42 seconds
- Result: New content detected successfully

### RSS Monitoring

A controlled RSS test recorded:

- Detection delay: 2764.44 seconds
- Result: New article detected successfully

## 4. Detection Delay Analysis

Detection delay is calculated as:

Detection Delay = First Discovery Time - Publication Time

The measured results show that detection time depends on:

- The scheduled monitoring cycle
- The time at which an article is published relative to the next monitoring cycle
- Source response time
- Availability and response behavior of the monitored website

The system records the actual timestamps instead of assuming that every article will always be detected within five minutes.

Some controlled tests were below the five-minute target, while others exceeded five minutes. The measured values are retained to provide an accurate representation of system behavior.

## 5. Live Website Testing

The system was tested against public websites in addition to the controlled demonstration websites.

### NASA

NASA was automatically investigated and assigned RSS monitoring.

The live source was successfully monitored and returned article entries during scheduled checks.

### TechCrunch

TechCrunch was automatically investigated and assigned RSS monitoring.

A successful live monitoring check recorded:

- Strategy: RSS
- Articles found: 20
- New articles: 0
- Check result: Success
- Response time: approximately 21.3 seconds

The live tests demonstrate that the system can continuously monitor public websites in addition to controlled local demonstration sources.

## 6. Multi-Site Monitoring

The scheduler continuously monitors multiple active websites.

The project was successfully operated with:

- RSS demo website
- Sitemap demo website
- Direct-page demo website
- NASA
- TechCrunch

The monitoring dashboard records the status and results of individual website checks.

A failure affecting one website is isolated so that monitoring of other websites can continue.

## 7. 100-Site Scalability Test

A 100-site load test was performed using controlled concurrent monitoring.

Configuration:

- Websites tested: 100
- Maximum concurrency: 10

Observed results:

- Test duration: approximately 58.47 seconds
- Maximum observed concurrency: 10
- Monitoring checks recorded: 167
- Successful checks: 159
- Failed checks: 8
- Articles found: 477
- New duplicate detections: 0

The load test demonstrates that the scheduler can monitor multiple websites using controlled concurrency rather than creating unlimited simultaneous requests.

The load-test-only failure count was 0; the failures in the overall recorded test environment were associated with the simulated load-test environment.

## 8. Reliability Observations

The monitoring system records each monitoring check, including:

- Check time
- Success or failure
- Monitoring strategy
- Articles found
- New articles
- Response time
- Error information

The scheduler uses controlled concurrency and individual website isolation so that a problem with one source does not terminate the complete monitoring process.

The monitoring engine also includes retries and request timeouts for temporary network failures.

## 9. Performance Observations

The controlled tests demonstrate that different monitoring strategies can have different detection characteristics.

Direct-page monitoring produced a short measured detection delay in the controlled test.

Sitemap monitoring successfully detected newly added content, with measured delays both below and above five minutes.

RSS monitoring successfully detected new content, although the controlled RSS test produced a substantially longer measured delay.

Live websites can also have significantly higher response times than local demonstration sources. For example, the recorded TechCrunch check took approximately 21.3 seconds.

## 10. Limitations

Detection delay depends on the monitoring schedule and the behavior of the monitored source.

A five-minute monitoring interval is a target rather than a guarantee that every article will be detected in less than five minutes.

External websites can also introduce:

- Slow responses
- Temporary network failures
- Changes in page or feed structure
- Delayed publication metadata
- Rate limiting or access restrictions

These factors can affect actual detection performance.

## 11. Conclusion

The performance testing demonstrates that Competitor Blog Spy can:

- Monitor multiple websites continuously
- Use RSS/Atom, sitemap, and direct-page strategies
- Detect newly published or changed content
- Record actual publication and discovery timestamps
- Calculate detection delay
- Maintain monitoring history
- Isolate individual website failures
- Perform controlled concurrent monitoring at 100-site scale

The measured results provide actual detection-time evidence rather than assuming that all content will always meet the five-minute target.
