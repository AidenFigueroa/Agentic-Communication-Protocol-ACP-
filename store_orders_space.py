from __future__ import annotations

import json
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from typing import Any


SPACE_ID = "space://store-orders"
HOST = "127.0.0.1"
PORT = 8102


# This is temporary in-memory test data.
ORDERS = {
    "1152": {
        "current_status": "processing",
    },
    "1842": {
        "current_status": "shipped",
    },
    "ABC-1842": {
        "current_status": "out_for_delivery",
    },
}


class StoreOrdersHandler(BaseHTTPRequestHandler):
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
                    "cancel_order",
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

            print("\nStore Orders Space received:")
            print(json.dumps(message, indent=2))

            if message.get("protocol") != "space/0.1":
                raise ValueError(
                    "Unsupported protocol version."
                )

            if message.get("receiver") != SPACE_ID:
                raise ValueError(
                    f"Message was not addressed to {SPACE_ID}."
                )

            if message.get("action") != "cancel_order":
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

            if order["current_status"] in {
                "shipped",
                "out_for_delivery",
            }:
                self.send_json(
                    409,
                    {
                        "protocol": "space/0.1",
                        "message_type": "ERROR",
                        "task_id": message.get("task_id"),
                        "sender": SPACE_ID,
                        "receiver": message.get("sender"),
                        "error": "order_cannot_be_cancelled",
                        "details": {
                            "order_id": order_id,
                            "current_status": order[
                                "current_status"
                            ],
                        },
                    },
                )
                return

            order["current_status"] = "cancelled"

            self.send_json(
                200,
                {
                    "protocol": "space/0.1",
                    "message_type": "RESULT",
                    "task_id": message.get("task_id"),
                    "sender": SPACE_ID,
                    "receiver": message.get("sender"),
                    "result": {
                        "order_id": order_id,
                        "cancellation_status": "cancelled",
                    },
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
    StoreOrdersHandler,
)

print(
    f"Store Orders Space running at "
    f"http://{HOST}:{PORT}"
)

server.serve_forever()