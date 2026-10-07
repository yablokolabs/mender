# Mender demo: from a broken service to a verified pull request

## intro
Mender takes a broken Kubernetes service and returns a verified fix. It finds the root cause, writes a patch, tests it in a sandbox, and prepares a pull request for a human to review. Mender never merges anything itself.

## setup
We start with a healthy checkout service on a local cluster. All twenty-one checks pass.

## fault
Then we inject a fault. The memory limit drops to sixty-four megabytes, below what the service needs to start. The pod is killed, again and again.

## triage
Mender collects the evidence. The nano model reads about eleven thousand tokens of logs and events, and returns a short list of signals and suspects.

## diagnosis
The ultra model plans three web searches, runs them through Tavily, and writes the root cause report. The report carries numbered citations that a reviewer can open.

## patch
The super model then writes the patch. It can only touch the files it was given. Here, it raises the memory limit back to five hundred and twelve megabytes.

## sandbox
Before anything is proposed, the tests run on the patched files in a Docker container with no network. Twenty-one of twenty-one checks pass, on the first attempt.

## pr
Mender prepares the pull request: root cause, evidence, the diff, the test results, and the sources. A person reviews it and merges it.

## outro
From evidence to a verified fix in twenty-five seconds. Mender. It never merges without you.
