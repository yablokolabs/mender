# Provider Script

> Provider: ElevenLabs v2 (eleven_multilingual_v2)
> Voice: Lily (pFZP5JQG7iQjIQuC4Bku), British English, female
> Style notes: Conversational, warm, steady. Numbers and units are written as words.

---

Mender takes a broken Kubernetes service and returns a verified fix. It finds the root cause, writes a patch, tests it in a sandbox, and prepares a pull request for a human to review. Mender never merges anything itself.

<break time="0.7s" />

We start with a healthy checkout service on a local cluster. All twenty-one checks pass.

<break time="0.7s" />

Then we inject a fault. The memory limit drops to sixty-four megabytes, below what the service needs to start. The pod is killed, again and again.

<break time="0.7s" />

Mender collects the evidence. The nano model cuts eleven thousand tokens of logs and events down to a short list of signals and suspects.

<break time="0.7s" />

The ultra model plans three web searches, runs them through Tavily, and writes the root cause report. The report carries numbered citations that a reviewer can open.

<break time="0.7s" />

The super model then writes the patch. It can only touch the files it was given. Here, it raises the memory limit back to five hundred and twelve megabytes.

<break time="0.7s" />

Before anything is proposed, the patch runs in a Docker container with no network. Twenty-one of twenty-one checks pass, on the first attempt.

<break time="0.7s" />

Mender prepares the pull request: root cause, evidence, the diff, the test results, and the sources. A person reviews it and merges it.

<break time="0.7s" />

From broken service to a verified fix in twenty-five seconds. Mender. It never merges without you.
