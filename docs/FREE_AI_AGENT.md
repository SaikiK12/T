# Free AI coding agent from a phone

This repository is configured to run OpenCode inside GitHub Actions. Your phone only sends commands through GitHub issue/PR comments; the coding work runs on GitHub's cloud runner.

## Required secrets

Add one or both secrets in:

`Repository -> Settings -> Secrets and variables -> Actions -> New repository secret`

### Gemini (recommended primary)

- Secret name: `GEMINI_API_KEY`
- Create a free API key in Google AI Studio: https://aistudio.google.com/app/apikey
- Model: `gemini-3.8-flash`
- Commands: `/gemini ...`, `/oc ...`, or `/opencode ...`

### Cohere (backup)

- Secret name: `COHERE_API_KEY`
- Create a key: https://dashboard.cohere.com/api-keys
- Model: `north-mini-code-1-0`
- Command: `/cohere ...`

Never paste API keys into issues, commits, files, or pull requests.

## How to use it from a phone

1. Open a GitHub Issue in this repository and describe the task clearly.
2. Add a comment such as:

   `/gemini implement this issue, run the relevant tests, fix failures, and open a pull request`

3. If Gemini's free quota is unavailable, retry with:

   `/cohere implement this issue, run the relevant tests, fix failures, and open a pull request`

The workflow is restricted to comments made by the repository owner, so other people cannot consume your model quota by posting trigger commands.

## Notes

- OpenCode itself is the agent/harness; the model API is supplied directly by Google or Cohere.
- OpenCode's own free-tier models are not being used by this workflow.
- GitHub's built-in `GITHUB_TOKEN` is used for branches, commits, issue comments, and pull requests, so the OpenCode GitHub App is not required.
- The workflow has a 180-minute maximum runtime per task to prevent runaway jobs.
