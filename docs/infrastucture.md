# Airless Runtime Infrastructure

Airless is a serverless orchestration framework designed for modular, event-driven workflows. To ensure seamless operation and interoperability between tasks, Airless requires a minimal set of foundational functions. These shared functions handle common concerns such as error handling, retries, delays, and notifications—enabling developers to focus on business logic while maintaining observability and resilience.

!!! note
    Each function lives in its own deployment unit (e.g. separate [Cloud Run Function](https://cloud.google.com/functions?hl=en) or [AWS Lambda](https://aws.amazon.com/pt/lambda/)).  
    This isolation ensures low memory footprint, faster cold starts, and independent scaling.

---

## 🧱 Core Runtime Functions

!!! tip
    - Deploy all functions using a infrastructure as code like [Terraform](https://developer.hashicorp.com/terraform) or [Pulumi](https://www.pulumi.com/).

### Error Function
- **Objective:** Centralize failure handling so that any downstream error is captured, logged, and retried without losing the original event.

### Delay Function
- **Objective:** Decouple time-based waiting from business logic by offloading “sleep” or cooldown periods to a dedicated function.

### Redirect Function
- **Objective:** Enable branching and parallel workflows by duplicating incoming messages and forwarding them to multiple topics.

### Email Notification
- **Objective:** Decouple email alerting from core tasks by providing a standalone function that handles all SMTP interactions.

### Slack Notification
- **Objective:** Provide real-time, chat-based alerts by centralizing Slack integration into one function.
