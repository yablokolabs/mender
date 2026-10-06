<p align="center">
  <img src="assets/mender-logo.png" width="120" alt="Mender logo">
</p>

# Mender: Kubernetes Incident-to-Fix Agent

Mender takes a broken Kubernetes service and returns a verified fix: it finds the root
cause, writes a patch, tests the patch in an isolated sandbox, and opens a pull request
with the evidence attached. A human reviews and merges — Mender never merges anything
itself.

> **Status: under construction.** Full documentation (architecture, quickstart,
> configuration, model usage, Tavily usage, eval results, limitations) lands with the
> release phase.

## License

Apache-2.0
