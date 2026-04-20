##############################################################################################
# Modules, Global Variables & Config
##############################################################################################

import json
import requests
import logging

# Module-level logger used for structured logging throughout this module
logger = logging.getLogger(__name__)


##############################################################################################


# Client class responsible for interacting with the Prisma Access
# Egress IP API and handling request/response logic
# Encapsulates API configuration, request execution, and output formatting


class EgressIP:

    # Initialize an EgressIP client instance
    # Stores API endpoint details, authentication headers, and
    # a default request payload used for querying all egress IPs

    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key
        self.headers = {
            "header-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        self.payload = {"serviceType": "all", "addrType": "all", "location": "all"}

    # Developer-friendly object representation for debugging and logging
    def __repr__(self):
        return f"EgressIP(url={self.url})"

    # User-friendly string representation used in log messages
    def __str__(self):
        return f"EgressIP()"
    
    # Context manager entry point
    def __enter__(self):
        return self

    # Context manager exit point
    def __exit__(self, exc_type, exc_value, traceback):
        # Cleanup logic
        self.api_key = None
 
        if exc_type:
            logger.error(
                f"{self} - Exception occurred: {exc_type.__name__} - {exc_value}"
            )
        else:
            logger.debug(f"{self} - Exited Cleanly")

    def _handle_response(self, response):

        # Centralized HTTP response handler
        # Validates HTTP status codes, parses JSON responses,
        # and standardizes error handling and logging

        try:
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError:
            # Catch HTTP errors returned by the API (4xx / 5xx responses)
            # Logs detailed error information and returns a structured error object
            logger.error(
                f"{self} - HTTPError for Endpoint: Status Code {self.response.status_code}"
            )
            logger.debug(
                f"{self.__repr__()} - HTTPError for Endpoint: Message \n{response.json()}"
            )
            return {"Status Code": response.status_code, "Message": response.json()}

        except requests.exceptions.RequestException as e:
            # Catch lower-level request exceptions (network issues, timeouts, etc.)
            # Logs exception details and returns a fallback error structure
            logger.error(
                f"{self.__repr__()} - RequestException for Endpoint: Status Code {self.response.status_code}"
            )
            logger.debug(f"{self.__repr__()} - RequestException for Endpoint: Message \n{str(e)}")
            return {"Status Code": "N/A", "Message": str(e)}

    def fetch_egress_ips(self):

        # Execute the API request to fetch egress IP data
        # Sends a POST request, processes the response, and returns parsed results
        # Includes detailed logging for request lifecycle and response payloads

        try:
            logger.info(f"{self} - GET Request to Endpoint: {self.url}")
            self.response = requests.post(
                self.url, headers=self.headers, json=self.payload
            )
            handled_response = self._handle_response(self.response)
            logger.info(
                f"{self} - GET Request to Endpoint: {self.url} Status Code {self.response.status_code}"
            )
            logger.debug(
                f"{self.__repr__()} - Response: \n{json.dumps(handled_response, indent=2)}"
            )
            return handled_response["result"]

        except requests.exceptions.RequestException as e:
            # Handle request-level exceptions and return a safe error response
            logger.error(f"{self} - Error fetching egress IPs: {str(e)}")
            return {"Status Code": "N/A", "Message": str(e)}

    def print_egress_ips(self):

        # Retrieve egress IP data and print it in a readable, CSV-style format
        # Applies special formatting for remote network service types
        # Intended for command-line execution and human-readable output

        egress_ips = self.fetch_egress_ips()
        for zone in egress_ips:
            for address_detail in zone["address_details"]:
                if address_detail["serviceType"] == "remote_network":
                    print(
                        f"{zone['zone']}, {address_detail['serviceType']}, {' | '.join(address_detail['node_name'])}, {address_detail['address']}"
                    )
                else:
                    print(
                        f"{zone['zone']}, {address_detail['serviceType']}, , {address_detail['address']}"
                    )


##############################################################################################
# Run
##############################################################################################

if __name__ == "__main__":

    pass
