
This page provides a quick overview and links to detailed tutorials on setting up and using Airless workflows on Google Cloud Platform.

<div class="grid cards" markdown>

-   :octicons-server-24:{ .lg .middle } __Core GCP Infrastructure (Terraform)__

    ---

    Learn how to deploy the essential Airless infrastructure (Cloud Functions, Pub/Sub topics, GCS buckets) on Google Cloud using Terraform. This guide explains the serverless architecture choices, the importance of Terraform for IaC, the role of core functions (Error, Delay, Redirect), and storage configuration.

    [:octicons-arrow-right-24: View Tutorial](core-infrastructure.md)

-   :octicons-rocket-24:{ .lg .middle } __Simple GCP Example (Weather API)__

    ---

    Follow a step-by-step quickstart to build and deploy a basic Airless workflow on GCP with Terraform. This example involves fetching weather data from an external API, demonstrating the operator/hook pattern, Cloud Function setup, deployment packaging, and triggering via Cloud Scheduler and Pub/Sub.

    [:octicons-arrow-right-24: View Tutorial](simple.md)

-   :octicons-list-ordered-24:{ .lg .middle } __Multi-step GCP Example (Geocode + Weather)__

    ---

    Deploy a multi-step Airless workflow on GCP using Terraform. This example shows how to chain tasks: first fetching geocoordinates for a city name, then using those coordinates to retrieve weather data. It illustrates handling different request types within a single Cloud Function triggered by Pub/Sub.

    [:octicons-arrow-right-24: View Tutorial](multistep.md)
</div>
