<div align="center">
<h1>The Jericho</h1>
<h3>Scalable & Reliable Endpoint Scanning</h3>

![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=EmilKylander_jericho&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=EmilKylander_jericho)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=EmilKylander_jericho&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=EmilKylander_jericho)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=EmilKylander_jericho&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=EmilKylander_jericho)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=EmilKylander_jericho&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=EmilKylander_jericho)
</div>

1. What is The Jericho?
2. How to install
3. How to add endpoints
4. How to use in standalone
5. How to use in a cluster
6. Notifications
7. FAQ
   - How does it know if an endpoint exists?
8. Development topics
   - Installing from source
   - How are you enforcing quality?
   - Unit-testing
   - Static Code Analysis
   - Acceptance Tests

## What is The Jericho?

The Jericho is a program written in Python 3.8.10 with clustering capabilities through
```Message Passing Interface``` (MPI). The purpose is to have a scanner that checks a list of
domains for a list of exposed configuration files, git directory, development files et cetera.

The problem that I had while performing such a task was the enormous volume of data that was
flowing into my workflow. For instance, 100,000 domains is not an uncommon amount of domains
to check. If you have a list of 250 endpoints whilst checking both HTTP and HTTPS that is 
```50,000,000``` requests.

To solve this problem I needed scalability and resilience, yet the program
needed to be simple so my time does not lie in maintenance. The program is therefore created in
such a manner that there's not much difference in running it standalone and in a cluster. 
The second problem that Jericho attempts to solve is the various ways that web developers
respond with "not found" pages and how to properly identify the real result.

## How to install

### Pip

```$ sudo apt install libopenmpi-dev && pip3 install jericho```

### From source

```$ sudo apt install libopenmpi-dev && pip3 install .```

## How to add endpoints

You can add endpoints by running:

```jericho --import-endpoints data/endpoints.json```

*Note*: You can run this with new entries, it will not duplicate or replace any old data.

## How to use in standalone

Simply add the --input flag to jericho containing all of the domains:
```jericho --input your_domains.txt```

## How to use in a cluster

The fundamental task for getting this to work in a cluster is installing
Message Passing Interface (MPI). Once this is installed you're pretty much finished.

Run the following to run it in a cluster:
```mpirun -n *server amount* -hostfile *host file* jericho --input your_domains.txt```

That's it!

## Notifications

Jericho does not save results until after the program is finished, this is because of the
scatter-gather architecture. To solve this we have added the capability of running HTTP calls when a result
has been found. This is configurable in your configuration file.

This is an example of sending a request to Slack:

```notifications:
  slack:
      type: POST
      url: https://hooks.slack.com/services/aaa/asd/123
      data:
        myfield: asd
        mysecondfield: test
        text: we found endpoint *url*
      headers:
        Content-Type: application/json
```


In this example you see the "*url*", this is a form of template variable that is replaced with the actual endpoint URL
when a result is found. Another feature to look out for is the ```content-type: application/json``` header because it will
automatically json encode the payload when it's present.

## FAQ

### How does it know if an endpoint exists?

During my analysis, I have found "not found" pages with a status of 200
(most likely due to misconfigured proxies). I have also found "not found" pages with dynamic content, and pages texts
written in other languages than English.

This leads to the question - how do you know if the content of the endpoint is actual real result?
I have tackled this by using two methods.

**1.) Content types and content strings**

We analyze the content of the endpoint and try to identify what we're looking at - e.g is it HTML/XML/JSON?
Then you can specify in the configuration what the desired file is. E.g /package.json should type JSON.

You can also check for strings, e.g /phpinfo.php should contain "phpinfo()"

The current types of content are:

```
XML
YLM
JSON
TEXT
NO_SPACES
HTML
```

**2.) Gathering of a real 404 page and calculating the percentage difference**

We also do more advanced analysis for pages that could be just about anything.
For instance - what does "/test.php" contain? If we don't know what we're looking for,
how are we supposed to find it?

The solution for this is to check what a real 404 page is and cache its content.
E.g the program saves the content of /page_not_found and stores it in a database. 

Then it sends a request to the endpoint (in our example /test.php) and it uses Levensthein's
text algorithm to analyze the difference between our 404 page and the result page. If the text is
more than 60% the same it will treat that page as a 404 instead and continue to the next endpoint.

## Development topics

### How are you enforcing quality?

You can't have problem-free software, but we wanted to make a good attempt at making it
as reliable as we could. That's why we have utilized the following methods.

1. Acceptance tests (Docker)
2. Unit tests (pytest, >= 80% coverage)
3. Linting (pylint)
4. Formatting (Black)
5. Static code analysis (SonarQube)
6. Type Hinting (mypy)

### Unit-testing

The tests are located in the directory ```tests```. You can run them with ```make test```

To create a coverage run ```make coverage```

NOTE: If you run this in a CI (Or Sonarqube in Docker) you need to replace the ```source``` in coverage.xml to ```/usr/src/jericho```

### Static Code Analysis

We use SonarQube for static code analysis. Install:

```
ip link add name docker0 type bridge
ip addr add dev docker0 172.17.0.1/16
systemctl start docker
docker run -d \
     --name sonarqube \
     -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true  \
     -p 9000:9000 sonarqube:latest
```

Now put your SonarQube access token and put it in ```.env``` like so:

```SONARQUBE_API=aaaaaaaaaaaaaa```


Run static code analysis:

```
make analyze
```

### UAT Automation

Docker-compose files test the application in a standalone environment, and a cluster environment.
This is to simulate that the business case is working.

To test the program standalone you can

```
cd tests/integration/test-standalone
docker-compose up --build --abort-on-container-exit
```

You can test the cluster by running

```
cd tests/integration/test-cluster
docker-compose up --build --abort-on-container-exit
```
