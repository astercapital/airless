# Getting started with Airless @ GCP

Integrating Airless with GCP provides a scalable, serverless solution for complex workflows and parallel processing tasks. Its modular architecture and use of hooks make it maintainable and adaptable to various use cases, outperforming traditional tools like Apache Airflow in specific scenarios.

By leveraging GCP services like Cloud Functions, Pub/Sub, and Cloud Scheduler, Airless enables you to build efficient, cost-effective, and dynamic workflows without the overhead of managing infrastructure.

## How It Works on GCP
Airless builds its workflows based on serverless functions, queues, and schedulers, all within GCP's ecosystem.

- Cloud Scheduler: Starts the process by publishing a message to a Pub/Sub topic on a cron schedule.
- Cloud Pub/Sub: Acts as a message queue that triggers Cloud Functions when a message is published.
- Cloud Functions: Executes the serverless functions with the message as input and can publish new messages to any number of Pub/Sub topics.
- Repeat: This process repeats, allowing for complex workflows without the need for dedicated servers.

## Set Up Your GCP Project

- Create a new GCP project or select an existing one.
- Enable billing for the project.
- Enable Required APIs
- Cloud Functions API
- Cloud Pub/Sub API
- Cloud Scheduler API
