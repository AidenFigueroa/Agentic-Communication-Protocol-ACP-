from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


INTENT_API_URL = (
    "http://127.0.0.1:8000/route-intent"
)


def post_json(
    url: str,
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    """
    Send a JSON POST request and return the decoded JSON response.
    """

    request_body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=request_body,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            response_body = response.read()

            return json.loads(
                response_body.decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        response_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        try:
            error_data = json.loads(response_body)
            formatted_error = json.dumps(
                error_data,
                indent=2,
            )
        except json.JSONDecodeError:
            formatted_error = response_body

        raise RuntimeError(
            f"HTTP {error.code} from {url}:\n"
            f"{formatted_error}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not connect to {url}: {error}"
        ) from error


def main() -> None:
    user_message = input(
        "What do you want your Space to do? "
    ).strip()

    if not user_message:
        print("A message is required.")
        return

    try:
        # =================================================
        # Step 1 and Step 2:
        # Encode the intention and select a destination.
        # =================================================

        routing_result = post_json(
            url=INTENT_API_URL,
            payload={
                "message": user_message,
            },
            timeout=120,
        )

        print("\nParsed intention:")
        print(
            json.dumps(
                routing_result["parsed_intent"],
                indent=2,
            )
        )

        print("\nSelected route:")
        print(
            json.dumps(
                routing_result["selected_route"],
                indent=2,
            )
        )

        print("\nProtocol message:")
        print(
            json.dumps(
                routing_result["protocol_message"],
                indent=2,
            )
        )

        # =================================================
        # Send the message to the selected receiving Space.
        # =================================================

        selected_endpoint = routing_result[
            "selected_route"
        ]["endpoint"]

        protocol_message = routing_result[
            "protocol_message"
        ]

        space_response = post_json(
            url=selected_endpoint,
            payload=protocol_message,
            timeout=15,
        )

        print("\nResponse from receiving Space:")
        print(
            json.dumps(
                space_response,
                indent=2,
            )
        )

    except RuntimeError as error:
        print(f"\nCommunication failed:\n{error}")


if __name__ == "__main__":
    main()