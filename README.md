# Space Protocol

A structured communication and routing protocol for modular A.I. services.

Space Protocol converts natural-language requests into validated, machine-readable intentions, determines which specialized service should handle the request, and sends a standardized protocol message to that service over HTTP.

The project demonstrates how an A.I. system can communicate reliably with independent tools and services instead of passing unstructured text between components.

## Overview

Modern A.I. applications often rely on multiple specialized services. One service may handle store orders, another may manage schedules, and another may retrieve documents.

Without a shared structure, each service must interpret arbitrary text independently. This makes communication inconsistent, difficult to validate, and harder to debug.

Space Protocol solves this by separating the process into four stages:

1. Interpret the user’s request.
2. Encode it as a structured intention.
3. Route the intention to the correct Space.
4. Exchange standardized request and response messages.

A **Space** is an independent service that exposes one or more supported actions.

## Example

A user submits:

```text
Give me the status of order 1152 and tell me when it will arrive.
```

The intention encoder produces:

```json
{
  "action": "check_order_status",
  "target": {
    "type": "order",
    "id": "1152"
  },
  "requested_output": [
    "current_status",
    "estimated_delivery"
  ],
  "needs_clarification": false,
  "clarification_question": null
}
```

The router selects the appropriate Space:

```json
{
  "space_id": "space://store-support",
  "endpoint": "http://127.0.0.1:8101/tasks"
}
```

The sender then constructs a Space Protocol request:

```json
{
  "protocol": "space/0.1",
  "message_type": "REQUEST",
  "task_id": "task-a849a49e-a712-4486-9edf-adcb20fdde29",
  "sender": "space://aiden",
  "receiver": "space://store-support",
  "action": "check_order_status",
  "target": {
    "type": "order",
    "id": "1152"
  },
  "requested_output": [
    "current_status",
    "estimated_delivery"
  ]
}
```

The receiving Space validates the message, performs the requested action, and returns a structured response.

## Architecture

```text
┌──────────────────────┐
│ Natural-Language     │
│ User Request         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Intention Encoder    │
│                      │
│ Extracts:            │
│ • action             │
│ • target             │
│ • requested outputs  │
│ • clarification need │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Schema Validation    │
│                      │
│ Rejects malformed or │
│ unsupported intents  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Space Registry       │
│ and Router           │
│                      │
│ Maps actions to      │
│ service endpoints    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Protocol Sender      │
│                      │
│ Builds and sends     │
│ an HTTP request      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Receiving Space      │
│                      │
│ Validates, executes, │
│ and responds         │
└──────────────────────┘
```

## Core Features

* Natural-language intention extraction
* Structured action and target representation
* Requested-output extraction
* Clarification detection
* Unsupported-action handling
* Registry-based service discovery
* Dynamic routing between Spaces
* Standardized request and response messages
* Unique task identifiers
* Sender and receiver identification
* HTTP-based service communication
* Message and schema validation
* Separation between A.I. interpretation and deterministic routing

## Design Principles

### Structured communication

Spaces exchange JSON messages instead of arbitrary natural-language strings. This makes messages easier to validate, test, log, and process.

### Separation of responsibilities

The intention encoder determines what the user wants.

The router determines where the request should go.

The receiving Space determines how the requested action should be completed.

No single component is responsible for the entire system.

### Explicit outputs

The `requested_output` field records exactly what information the user requested.

For example:

```json
[
  "current_status",
  "estimated_delivery"
]
```

This prevents the receiving Space from returning only part of the requested result.

### No invented information

The intention encoder does not fabricate missing identifiers or required values.

When important information is missing, it returns a clarification request instead of guessing.

### Deterministic routing

After an intention has been generated and validated, service selection is handled through a deterministic registry rather than leaving routing entirely to the A.I. model.

## Intention Schema

A structured intention contains the following fields:

| Field                    | Description                                      |
| ------------------------ | ------------------------------------------------ |
| `action`                 | The operation the user wants performed           |
| `target`                 | The resource the action applies to               |
| `requested_output`       | The information expected in the result           |
| `needs_clarification`    | Whether more user information is required        |
| `clarification_question` | The question that should be returned to the user |

Example:

```json
{
  "action": "cancel_order",
  "target": {
    "type": "order",
    "id": "1152"
  },
  "requested_output": [
    "cancellation_status"
  ],
  "needs_clarification": false,
  "clarification_question": null
}
```

## Protocol Message Schema

A request message uses the following structure:

```json
{
  "protocol": "space/0.1",
  "message_type": "REQUEST",
  "task_id": "task-<uuid>",
  "sender": "space://requesting-space",
  "receiver": "space://receiving-space",
  "action": "action_name",
  "target": {
    "type": "resource_type",
    "id": "resource_id"
  },
  "requested_output": [
    "requested_field"
  ]
}
```

### Fields

| Field              | Description                                 |
| ------------------ | ------------------------------------------- |
| `protocol`         | Space Protocol version                      |
| `message_type`     | Type of protocol message                    |
| `task_id`          | Unique identifier used to track the request |
| `sender`           | Identifier of the requesting Space          |
| `receiver`         | Identifier of the destination Space         |
| `action`           | Requested operation                         |
| `target`           | Resource involved in the operation          |
| `requested_output` | Information the receiver should return      |

## Message Types

The protocol is designed to support structured message types such as:

```text
REQUEST
RESPONSE
ERROR
CLARIFICATION_REQUIRED
```

### Request

Sent when one Space asks another Space to perform an action.

### Response

Returned after a request has been completed successfully.

Example:

```json
{
  "protocol": "space/0.1",
  "message_type": "RESPONSE",
  "task_id": "task-a849a49e-a712-4486-9edf-adcb20fdde29",
  "sender": "space://store-support",
  "receiver": "space://aiden",
  "status": "completed",
  "result": {
    "current_status": "shipped",
    "estimated_delivery": "2026-08-08"
  }
}
```

### Error

Returned when a request cannot be processed.

Example:

```json
{
  "protocol": "space/0.1",
  "message_type": "ERROR",
  "task_id": "task-a849a49e-a712-4486-9edf-adcb20fdde29",
  "sender": "space://store-support",
  "receiver": "space://aiden",
  "status": "failed",
  "error": {
    "code": "ORDER_NOT_FOUND",
    "message": "No order was found with ID 1152."
  }
}
```

### Clarification required

Returned when the original request does not contain enough information.

Example user request:

```text
Cancel my order.
```

Example intention:

```json
{
  "action": "cancel_order",
  "target": {
    "type": "order",
    "id": null
  },
  "requested_output": [
    "cancellation_status"
  ],
  "needs_clarification": true,
  "clarification_question": "What is the ID of the order you want to cancel?"
}
```

## Space Registry

The registry maps supported actions to Space identifiers and HTTP endpoints.

Example:

```json
{
  "check_order_status": {
    "space_id": "space://store-support",
    "endpoint": "http://127.0.0.1:8101/tasks"
  },
  "cancel_order": {
    "space_id": "space://store-support",
    "endpoint": "http://127.0.0.1:8101/tasks"
  }
}
```

The registry allows routing information to change without modifying the intention encoder.

## Supported Actions

The current prototype supports actions including:

```text
check_order_status
cancel_order
unsupported
```

Additional actions and Spaces can be added by:

1. Defining the action schema.
2. Registering the action with a Space.
3. Implementing the action in the receiving Space.
4. Adding validation and test cases.

## API Endpoints

### `POST /encode-intent`

Converts a natural-language request into a structured intention.

Example request:

```json
{
  "text": "Give me the status of order 1152 and tell me when it will arrive."
}
```

Example response:

```json
{
  "action": "check_order_status",
  "target": {
    "type": "order",
    "id": "1152"
  },
  "requested_output": [
    "current_status",
    "estimated_delivery"
  ],
  "needs_clarification": false,
  "clarification_question": null
}
```

### `POST /route-intent`

Validates an intention, selects the appropriate Space, constructs a protocol message, and forwards the request.

### `GET /docs`

Opens the automatically generated API documentation.

### `GET /`

Returns basic information about the running service.

## Technology Stack

* Python
* FastAPI
* Pydantic
* HTTP
* JSON
* UUID task identifiers
* A.I.-assisted natural-language intention extraction

## Running the Project

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the receiving Store Support Space

```bash
uvicorn store_support:app --host 127.0.0.1 --port 8101
```

### 5. Start the intention encoder and router

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 6. Open the API documentation

```text
http://127.0.0.1:8000/docs
```

## Example End-to-End Request

```bash
curl -X POST "http://127.0.0.1:8000/route-intent" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Give me the status of order 1152 and tell me when it will arrive."
  }'
```

Expected flow:

```text
User request
    ↓
Structured intention
    ↓
Schema validation
    ↓
Registry lookup
    ↓
Space Protocol REQUEST
    ↓
Store Support Space
    ↓
Space Protocol RESPONSE
```

## Validation and Error Handling

The system should reject or safely handle:

* Missing actions
* Missing required target IDs
* Unsupported actions
* Invalid message types
* Unknown receiving Spaces
* Malformed targets
* Empty requested-output fields
* Multiple conflicting actions
* Invalid protocol versions
* Unavailable service endpoints
* Request timeouts
* Invalid responses from receiving Spaces

## Testing

Recommended test categories include:

### Intention extraction tests

* Correct action extraction
* Correct order-ID extraction
* Multiple requested outputs
* Missing identifiers
* Ambiguous requests
* Unsupported requests

### Routing tests

* Known action routes to the correct Space
* Unknown action is rejected
* Missing registry entry is handled safely
* Correct sender and receiver identifiers are assigned

### Protocol validation tests

* Required fields are present
* Invalid message types are rejected
* Invalid protocol versions are rejected
* Malformed targets are rejected
* Task IDs are unique

### Integration tests

* End-to-end request and response
* Receiving Space unavailable
* Receiving Space returns an error
* Receiving Space returns malformed JSON
* Request timeout
* Clarification flow

Run the test suite with:

```bash
pytest
```

## Project Structure

A possible project structure is:

```text
space-protocol/
│
├── main.py
├── encoder.py
├── router.py
├── registry.py
├── protocol.py
├── models.py
├── requirements.txt
├── README.md
│
├── spaces/
│   └── store_support.py
│
└── tests/
    ├── test_encoder.py
    ├── test_router.py
    ├── test_protocol.py
    └── test_integration.py
```

## What This Project Demonstrates

This project demonstrates experience with:

* A.I. system architecture
* Agent and tool orchestration
* Natural-language intent extraction
* Structured outputs
* Distributed service communication
* API design
* Schema validation
* Service discovery
* Message routing
* Failure handling
* Modular software design
* Testing communication boundaries

Unlike a basic chatbot wrapper, Space Protocol places the A.I. model inside a larger deterministic system with explicit interfaces and validation rules.

## Current Limitations

Space Protocol is currently a prototype and is not intended for production use.

Current limitations may include:

* A limited number of registered Spaces
* A limited action vocabulary
* Local HTTP communication
* No persistent task database
* No authentication between Spaces
* No encrypted service-to-service identity
* No distributed registry
* No retry or message-queue system
* No load testing at production scale

These limitations are intentionally documented rather than hidden behind the traditional software-development strategy of hoping nobody asks.

## Future Improvements

Potential future additions include:

* More specialized Spaces
* Asynchronous task execution
* Task-status polling
* Retry and timeout policies
* Message queues
* Streaming responses
* Persistent task history
* Authentication and authorization
* Signed protocol messages
* Rate limiting
* Distributed service discovery
* Protocol version negotiation
* Response caching
* Metrics and tracing
* WebSocket communication
* Multi-step task orchestration
* Dependency graphs between tasks

## Project Status

The current version is a completed prototype demonstrating end-to-end:

* Intention extraction
* Schema validation
* Registry-based routing
* Standardized protocol messaging
* Communication with an independent receiving Space
* Structured responses and errors

## Author

**Aiden Figueroa**

Built as an exploration of modular A.I. systems, structured agent communication, and deterministic service orchestration.
