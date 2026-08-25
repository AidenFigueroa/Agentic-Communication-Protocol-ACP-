from __future__ import annotations

import json
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from typing import Any

import os


SPACE_ID = "space://store-support"
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8101"))


# Mock store information for the proof of concept.
ORDERS = {
    "1152": {
        "current_status": "processing",
        "estimated_delivery": "2026-08-07",
        "tracking_number": None,
    },
    "1842": {
        "current_status": "shipped",
        "estimated_delivery": "2026-08-05",
        "tracking_number": "TRACK-1842",
    },
    "ABC-1842": {
        "current_status": "out_for_delivery",
        "estimated_delivery": "2026-08-03",
        "tracking_number": "TRACK-ABC-1842",
    },
}


class StoreSupportHandler(BaseHTTPRequestHandler):
    def send_json(
        self,
        status_code: int,
        payload: dict[str, Any],
    ) -> None:
        response_bytes = json.dumps(
            payload,
            indent=2,
        ).encode("utf-8")

        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            "application/json",
        )
        self.send_header(
            "Content-Length",
            str(len(response_bytes)),
        )
        self.end_headers()

        self.wfile.write(response_bytes)

    def do_GET(self) -> None:
        self.send_json(
            200,
            {
                "space_id": SPACE_ID,
                "status": "online",
                "capabilities": [
                    "check_order_status",
                ],
            },
        )

    def do_POST(self) -> None:
        message: dict[str, Any] = {}

        if self.path != "/tasks":
            self.send_json(
                404,
                {
                    "error": "endpoint_not_found",
                },
            )
            return

        try:
            content_length_header = self.headers.get(
                "Content-Length"
            )

            if content_length_header is None:
                raise ValueError(
                    "Content-Length header is missing."
                )

            content_length = int(content_length_header)

            request_body = self.rfile.read(content_length)

            message = json.loads(
                request_body.decode("utf-8")
            )

            print("\nStore Support Space received:")
            print(json.dumps(message, indent=2))

            if message.get("protocol") != "space/0.1":
                raise ValueError(
                    "Unsupported protocol version."
                )

            if message.get("receiver") != SPACE_ID:
                raise ValueError(
                    f"Message was not addressed to {SPACE_ID}."
                )

            if message.get("action") != "check_order_status":
                self.send_json(
                    400,
                    {
                        "protocol": "space/0.1",
                        "message_type": "ERROR",
                        "task_id": message.get("task_id"),
                        "sender": SPACE_ID,
                        "receiver": message.get("sender"),
                        "error": "unsupported_action",
                    },
                )
                return

            target = message.get("target")

            if not isinstance(target, dict):
                raise ValueError(
                    "Message target must be an object."
                )

            order_id = target.get("id")

            if not order_id:
                raise ValueError(
                    "Order ID is missing."
                )

            order = ORDERS.get(str(order_id))

            if order is None:
                self.send_json(
                    404,
                    {
                        "protocol": "space/0.1",
                        "message_type": "ERROR",
                        "task_id": message.get("task_id"),
                        "sender": SPACE_ID,
                        "receiver": message.get("sender"),
                        "error": "order_not_found",
                        "details": {
                            "order_id": order_id,
                        },
                    },
                )
                return

            requested_output = message.get(
                "requested_output",
                [],
            )

            result: dict[str, Any] = {
                "order_id": order_id,
            }

            if (
                not requested_output
                or "current_status" in requested_output
            ):
                result["current_status"] = order[
                    "current_status"
                ]

            if "estimated_delivery" in requested_output:
                result["estimated_delivery"] = order[
                    "estimated_delivery"
                ]

            if "tracking_number" in requested_output:
                result["tracking_number"] = order[
                    "tracking_number"
                ]

            self.send_json(
                200,
                {
                    "protocol": "space/0.1",
                    "message_type": "RESULT",
                    "task_id": message.get("task_id"),
                    "sender": SPACE_ID,
                    "receiver": message.get("sender"),
                    "result": result,
                },
            )

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:
            self.send_json(
                400,
                {
                    "protocol": "space/0.1",
                    "message_type": "ERROR",
                    "task_id": message.get("task_id"),
                    "sender": SPACE_ID,
                    "receiver": message.get("sender"),
                    "error": "invalid_message",
                    "details": str(error),
                },
            )


server = ThreadingHTTPServer(
    (HOST, PORT),
    StoreSupportHandler,
)

print(
    f"Store Support Space running at "
    f"http://{HOST}:{PORT}"
)

server.serve_forever()  