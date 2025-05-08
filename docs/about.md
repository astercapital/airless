## Modular Architecture

!!! note "Why Modularize Airless?"
    Airless’s modular design reflects three guiding principles:

    1. **Minimal Footprint**  
    Start with only the code you need—nothing more. By keeping the core package lean, you reduce memory usage, dependency conflicts and cold-start times in serverless environments.

    2. **Pluggable Integrations**  
    Instead of a monolithic bundle, each integration lives in its own package. You opt-in to the features you require and avoid pulling in unused dependencies.

    3. **Clear Separation of Concerns**  
    Core orchestration logic remains decoupled from cloud-provider or service-specific code. This isolation makes it easier to maintain, test and evolve each piece independently.

### Core Package: `airless-core`

`airless-core` contains the fundamental building blocks for any workflow:

- **Operator Abstractions**  
  Define task units that consume events, execute logic, and emit output.  
- **Hook Abstractions**  
  Standard interfaces for interacting with sources and sinks.  
- **Service Abstractions**  
  Standard interfaces for interacting with third-party services like APIs, databases, etc.
- **Utils**  
  Utilities for common tasks.

This package has **zero opinion** on which cloud provider or external service you use—it only cares about the shape of events and tasks.

### Optional Packages
Airless offers a growing ecosystem of add-ons. Install only what you need for your project:

- **`airless-captcha`**  
  Package that integrates CAPTCHA solving services (e.g. reCAPTCHA or hCaptcha) as part of your data-collection pipelines.

- **`airless-email`**  
  Package that sends emails from within your tasks, with many options to support.

- **`airless-google-cloud-core`**  
  Foundation for all Google Cloud extends `airless-core` abstractions to create classes that can run and interact with Google Cloud Infrastructure.

- **`airless-google-cloud-storage`**  
  Read/write blobs to Google Cloud Storage buckets.

- **`airless-google-cloud-secret-manager`**  
  Retrieve secrets (API keys, credentials) from Secret Manager at runtime.

- **`airless-google-cloud-bigquery`**  
  Load, query or stream data into BigQuery tables as part of your workflows.

- **`airless-google-cloud-vertexai`**  
  Submit jobs or online predictions to Vertex AI models within your pipelines.

- **`airless-pdf`**  
  Generate, merge or manipulate PDF documents on the fly.

- **`airless-slack`**  
  Post messages, alerts or interactive dialogs to Slack channels and users.

Each optional package extends the core operator/hook abstractions, so you can mix and match services to build **precisely** the workflow you need—no more, no less.
