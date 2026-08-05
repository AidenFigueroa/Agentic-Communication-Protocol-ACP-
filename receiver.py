from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class SpaceMessageHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Find out how many bytes sender.py sent.
            content_length = int(self.headers["Content-Length"])

            # Read the actual bytes from the network connection.
            request_body = self.rfile.read(content_length)

            # Convert the JSON bytes into a Python dictionary.
            message = json.loads(request_body)

            print("Received message:")
            print(json.dumps(message, indent=2))

            action = message.get("action")
            task_id = message.get("task_id")

            if action == "check_order_status":
                order_id = message["parameters"]["order_id"]

                response = {
                    "protocol": "space/0.1",
                    "message_type": "RESULT",
                    "task_id": task_id,
                    "result": {
                        "order_id": order_id,
                        "order_status": "shipped"
                    }
                }

                status_code = 200

            else:
                response = {
                    "protocol": "space/0.1",
                    "message_type": "ERROR",
                    "task_id": task_id,
                    "error": "Unsupported action"
                }

                status_code = 400

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            response = {
                "protocol": "space/0.1",
                "message_type": "ERROR",
                "error": f"Invalid message: {error}"
            }

            status_code = 400

        # Convert the response dictionary into JSON bytes.
        response_bytes = json.dumps(response).encode("utf-8")

        # Send the HTTP response back to sender.py.
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()

        self.wfile.write(response_bytes)


server = HTTPServer(("localhost", 8000), SpaceMessageHandler)

print("Store Support Space running at http://localhost:8000")
server.serve_forever()