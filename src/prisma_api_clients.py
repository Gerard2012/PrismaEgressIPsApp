#!/usr/bin/env python3

##############################################################################################
# Modules, Global Variables & Config #########################################################
##############################################################################################

import requests
import base64
import json
import logging

# Module-level logger used for structured logging throughout this module
logger = logging.getLogger(__name__)


##############################################################################################
# Classes ####################################################################################
##############################################################################################


class BaseAPIClient:

    # Class-level cache
    _auth_token = None

    # Todo: Improve security around secret handling
    # |-- secret handling improvements to consider:
    # |   - Environment Variables
    # |   - Encrypted Storage
    # |   - Secure Vaults
    # |-- Pass tenant id as argument to init method
    def __init__(self, tsg_id, client_id, secret):
        self.client_id = client_id
        self.secret = secret

        # Only prompt for secret if token hasn't been retrieved yet -- fix later | redundant? | always instantiated with token = None
        if BaseAPIClient._auth_token is None:
            self.credentials = f"{self.client_id}:{self.secret}"
            self.encoded_credentials = base64.b64encode(
                self.credentials.encode()
            ).decode()
            self.auth_url = (
                "https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token"
            )
            self.auth_payload = f"grant_type=client_credentials&scope=tsg_id:{tsg_id}"
            self.auth_headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Authorization": f"Basic {self.encoded_credentials}",
            }

            try:
                logger.info(f"{self} - Authenticating Client ID: {self.client_id}")
                self.auth_response = requests.post(
                    self.auth_url, headers=self.auth_headers, data=self.auth_payload
                )
                self.auth_response.raise_for_status()

                auth_data = self.auth_response.json()
                if "access_token" not in auth_data:
                    logger.error(
                        f"{self} - Authentication failed: 'access_token' not found in response."
                    )
                    raise ValueError(
                        "Authentication failed: 'access_token' not found in response."
                    )

                BaseAPIClient._auth_token = auth_data["access_token"]

            except (requests.exceptions.HTTPError, ValueError) as e:
                logger.error(
                    f"{self} - Authentication HTTPError - Status Code: {self.auth_response.status_code} - Response Text: {self.auth_response.text}"
                )
                raise SystemExit(1)

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"{self} - Authentication RequestException Error - Message: {str(e)}"
                )
                raise SystemExit(1)

        self.auth_token = BaseAPIClient._auth_token
        logger.info(f"{self} - Auth Token Retrieved for Client ID: {self.client_id}")

    def __repr__(self):
        return f"BaseAPIClient(client_id={self.client_id})"

    def __str__(self):
        return f"BaseAPIClient()"

    def get_auth_token(self):
        return self.auth_token

    # Context manager entry point
    def __enter__(self):
        return self

    # Context manager exit point
    def __exit__(self, exc_type, exc_value, traceback):
        # Cleanup logic
        self.auth_token = None
        self.secret = None
        self.credentials = None
        self.encoded_credentials = None
        BaseAPIClient._auth_token = None

        if exc_type:
            logger.error(
                f"{self} - Exception occurred: {exc_type.__name__} - {exc_value}"
            )
        else:
            logger.debug(f"{self} - Exited Cleanly")


##############################################################################################
#### PRISMA ACCESS API CLIENT ################################################################
##############################################################################################


class PrismaAccessAPIClient(BaseAPIClient):

    def __init__(self, tsg_id, client_id, secret):
        super().__init__(tsg_id, client_id, secret)
        self.base_url = "https://api.sase.paloaltonetworks.com"

    def __repr__(self):
        return f"PrismaAccessAPIClient(client_id={self.client_id})"

    def __str__(self):
        return f"PrismaAccessAPIClient()"

    # Small methods to return useful data
    def get_endpoint_url(self):
        return self.url

    def get_reponse_status(self):
        return self.response.status_code

    def get_response_headers(self):
        return self.response_headers

    # Contructs the URL for the API call from arguments provided
    def _build_url(self, endpoint="", folder="", name="", offset=0, limit=0):

        url = f"{self.base_url}{endpoint}"

        if folder:
            url = f"{url}?folder={folder}"

        if name:
            url = f"{url}&name={name}"

        if offset > 0:
            url = f"{url}&offset={offset}"

        if limit > 0:
            url = f"{url}&limit={limit}"

        return url

    # Handles the response from the API call
    def _handle_response(self, response):

        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            logger.error(
                f"{self} - HTTPError for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            logger.debug(
                f"{self} - HTTPError for Endpoint[{self.endpoint}]: Message \n{response.json()}"
            )
            return {"Status Code": response.status_code, "Message": response.json()}
        except requests.exceptions.RequestException as e:
            logger.error(
                f"{self} - RequestException for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            logger.debug(
                f"{self} - RequestException for Endpoint[{self.endpoint}]: Message \n{str(e)}"
            )
            return {"Status Code": "N/A", "Message": str(e)}

    #### << BASE METHODS >> ##################################################################

    def get_endpoint(self, endpoint="", folder="", name="", offset=0, limit=5000):

        # |--endpoint
        # |   string
        # |   required
        # |   The specific endpoint you want to query.
        # |
        # |--folder
        # |   string
        # |   required
        # |   Default: Null
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want to query.
        # |
        # |--offset
        # |   integer
        # |   Default: 0
        # |   The starting point within the collection of resource results.
        # |
        # |--limit
        # |   integer
        # |   Default: 5000
        # |   The maximum number of resource results to return.

        self.client_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.get_auth_token()}",
        }

        self.endpoint = endpoint
        self.url = self._build_url(
            endpoint=endpoint, folder=folder, name=name, offset=offset, limit=limit
        )

        try:
            logger.info(f"{self} - GET Request to Endpoint[{self.endpoint}]")
            self.response = requests.get(self.url, headers=self.client_headers)
            self.response_headers = self.response.headers
            handled_response = self._handle_response(self.response)
            logger.info(
                f"{self} - GET Request Successful for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            logger.debug(
                f"{self} - Response: \n{json.dumps(handled_response, indent=2)}"
            )
            return handled_response

        except Exception as e:
            logger.error(
                f"{self} - GET Request Error for Endpoint[{self.endpoint}]: {str(e)}"
            )
            return {"Error": str(e)}

    def post_endpoint(self, endpoint="", folder="Shared", api_payload=""):

        # |--endpoint
        # |   string
        # |   required
        # |   The specific endpoint you want to query.
        # |
        # |--folder
        # |   string
        # |   required
        # |   Default: Null
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        self.endpoint = endpoint
        self.api_payload = api_payload
        self.url = self._build_url(endpoint=endpoint, folder=folder)

        self.client_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.get_auth_token()}",
        }

        try:
            logger.info(f"{self} - POST Request to Endpoint[{self.endpoint}]")
            self.response = requests.post(
                self.url, headers=self.client_headers, json=self.api_payload
            )
            self.response_headers = self.response.headers
            handled_response = self._handle_response(self.response)
            logger.info(
                f"{self} - POST Request Successful for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            return handled_response

        except Exception as e:
            logger.error(
                f"{self} - POST Request Error for Endpoint[{self.endpoint}]: {str(e)}"
            )
            return {"Error": str(e)}

    def put_endpoint(self, endpoint="", folder="Shared", api_payload=""):

        # |--endpoint
        # |   string
        # |   required
        # |   The specific endpoint you want to query.
        # |
        # |--folder
        # |   string
        # |   required
        # |   Default: Null
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        self.endpoint = endpoint
        self.api_payload = api_payload
        self.url = self._build_url(endpoint=endpoint, folder=folder)

        self.client_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.get_auth_token()}",
        }

        try:
            logger.info(f"{self} - PUT Request to Endpoint[{self.endpoint}]")
            self.response = requests.put(
                self.url, headers=self.client_headers, json=self.api_payload
            )
            self.response_headers = self.response.headers
            handled_response = self._handle_response(self.response)
            logger.info(
                f"{self} - PUT Request Successful for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            return handled_response

        except Exception as e:
            logger.error(
                f"{self} - PUT Request Error for Endpoint[{self.endpoint}]: {str(e)}"
            )
            return {"Error": str(e)}

    def delete_endpoint(self, endpoint="", folder="Shared", name=""):

        # |--endpoint
        # |   string
        # |   required
        # |   The specific endpoint you want to query.
        # |
        # |--folder
        # |   string
        # |   required
        # |   Default: Null
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        self.endpoint = endpoint
        self.url = self._build_url(endpoint=endpoint, folder=folder, name=name)

        self.client_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.get_auth_token()}",
        }

        try:
            logger.info(f"{self} - DELETE Request to Endpoint[{self.endpoint}]")
            self.response = requests.delete(self.url, headers=self.client_headers)
            self.response_headers = self.response.headers
            handled_response = self._handle_response(self.response)
            logger.info(
                f"{self} - DELETE Request Successful for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            return handled_response

        except Exception as e:
            logger.error(
                f"{self} - DELETE Request Error for Endpoint[{self.endpoint}]: {str(e)}"
            )
            return {"Error": str(e)}

    #### <<< ADDRESSES >> ####################################################################

    def get_addresses(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/addresses", folder=folder, name=name
        )

    def create_addresses(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/addresses", folder=folder, api_payload=api_payload
        )

    def update_addresses(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/addresses", folder=folder, api_payload=api_payload
        )

    def delete_addresses(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/addresses", folder=folder, name=name
        )

    #### << ADDRESSES GROUPS >> ##############################################################

    def get_address_groups(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/address-groups", folder=folder, name=name
        )

    def create_address_groups(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/address-groups",
            folder=folder,
            api_payload=api_payload,
        )

    def update_address_groups(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/address-groups",
            folder=folder,
            api_payload=api_payload,
        )

    def delete_address_groups(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/address-groups", folder=folder, name=name
        )

    #### << URL CATEGORIES >> ################################################################

    def get_url_categories(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/url-categories", folder=folder, name=name
        )

    def create_url_categories(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/url-categories",
            folder=folder,
            api_payload=api_payload,
        )

    def update_url_categories(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/url-categories",
            folder=folder,
            api_payload=api_payload,
        )

    def delete_url_categories(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/url-categories", folder=folder, name=name
        )

    #### << GP TUNNELL PROFILES >> ###########################################################

    def get_gp_tunnel_profiles(self, folder="Mobile Users", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Mobile Users
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/mobile-agent/tunnel-profiles",
            folder=folder,
            name=name,
        )

    def create_gp_tunnel_profile(self, folder="Mobile Users", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Mobile Users
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/mobile-agent/tunnel-profiles",
            folder=folder,
            api_payload=api_payload,
        )

    def update_gp_tunnel_profile(self, folder="Mobile Users", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Mobile Users
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/mobile-agent/tunnel-profiles",
            folder=folder,
            api_payload=api_payload,
        )

    def delete_gp_tunnel_profile(self, folder="Mobile Users", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Mobile Users
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/mobile-agent/tunnel-profiles",
            folder=folder,
            name=name,
        )

    #### << IKE GATEWAYS >> ##################################################################

    def get_ike_gateways(self, folder="Remote Networks", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/ike-gateways", folder=folder, name=name
        )

    def create_ike_gateways(self, folder="Remote Networks", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/ike-gateways",
            folder=folder,
            api_payload=api_payload,
        )

    def update_ike_gateways(self, folder="Remote Networks", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/ike-gateways",
            folder=folder,
            api_payload=api_payload,
        )

    def delete_ike_gateways(self, folder="Remote Networks", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/ike-gateways", folder=folder, name=name
        )

    #### << IPSEC TUNNELS >> #################################################################

    def get_ipsec_tunnels(self, folder="Remote Networks", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/ipsec-tunnels", folder=folder, name=name
        )

    def create_ipsec_tunnels(self, folder="Remote Networks", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/ipsec-tunnels",
            folder=folder,
            api_payload=api_payload,
        )

    def update_ipsec_tunnels(self, folder="Remote Networks", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/ipsec-tunnels",
            folder=folder,
            api_payload=api_payload,
        )

    def delete_ipsec_tunnels(self, folder="Remote Networks", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/ipsec-tunnels", folder=folder, name=name
        )

    #### << REMOTE NETWORKS >> ###############################################################

    def get_remote_networks(self, folder="Remote Networks", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/remote-networks", folder=folder, name=name
        )

    def create_remote_networks(self, folder="Remote Networks", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/remote-networks",
            folder=folder,
            api_payload=api_payload,
        )

    def update_remote_networks(self, folder="Remote Networks", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/remote-networks",
            folder=folder,
            api_payload=api_payload,
        )

    def delete_remote_networks(self, folder="Remote Networks", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Remote Networks
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/remote-networks", folder=folder, name=name
        )

    #### << SERVICE CONNECTIONS >> ###########################################################

    def get_service_connections(self, folder="Service Connections", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Service Connections
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/service-connections", folder=folder, name=name
        )

    def create_service_connections(self, folder="Service Connections", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Service Connections
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/service-connections",
            folder=folder,
            api_payload=api_payload,
        )

    def update_service_connections(self, folder="Service Connections", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Service Connections
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/service-connections",
            folder=folder,
            api_payload=api_payload,
        )

    def delete_service_connections(self, folder="Service Connections", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Service Connections
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/service-connections", folder=folder, name=name
        )

    #### << DECRYPTION PROFILES >> ###########################################################
    
    def get_decryption_profiles(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/decryption-profiles", folder=folder, name=name
        )
    
    def create_decryption_profiles(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/decryption-profiles", folder=folder, api_payload=api_payload
        )
    
    def update_decryption_profiles(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/decryption-profiles", folder=folder, api_payload=api_payload
        )
    
    def delete_decryption_profiles(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/decryption-profiles", folder=folder, name=name
        )
    
    #### << REGIONS >> #######################################################################
    
    def get_regions(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   name
        # |   string
        # |   Default: Null
        # |   The name of the specific object you want query.

        return self.get_endpoint(
            endpoint="/sse/config/v1/regions", folder=folder, name=name
        )
    
    def create_regions(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the POST request.

        return self.post_endpoint(
            endpoint="/sse/config/v1/regions", folder=folder, api_payload=api_payload
        )
    
    def update_regions(self, folder="Shared", api_payload=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        return self.put_endpoint(
            endpoint="/sse/config/v1/regions", folder=folder, api_payload=api_payload
        )
    
    def delete_regions(self, folder="Shared", name=""):

        # |--folder
        # |   string
        # |   required
        # |   Default: Shared
        # |   Possible values: Shared, Mobile Users, Remote Networks, Service Connections, Mobile Users Container, Mobile Users Explicit Proxy
        # |   The folder on which you want to perform this operation.
        # |
        # |--name
        # |   string
        # |   required
        # |   Default: Null
        # |   The name of the specific object you want to delete.

        return self.delete_endpoint(
            endpoint="/sse/config/v1/regions", folder=folder, name=name
        )


##############################################################################################
#### PRISMA SD-WAN API CLIENT ################################################################
##############################################################################################


class PrismaSDWANAPIClient(BaseAPIClient):

    def __init__(self, tsg_id, client_id, secret):
        super().__init__(tsg_id, client_id, secret)
        self.tsg_id = tsg_id
        self.base_url = "https://api.sase.paloaltonetworks.com"
        self.client_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.get_auth_token()}",
        }

        self._profile_url = (
            f"https://api.sase.paloaltonetworks.com/sdwan/v2.1/api/profile"
        )
        self._response = requests.request(
            "GET", self._profile_url, headers=self.client_headers
        )

        if self._response.status_code != 200:
            return_message = {
                "Class": self.__repr__,
                "Status Code": f"{self._response.status_code}",
                "Message": self._response.json(),
            }
            print(json.dumps(return_message, indent=2))
            raise Exception("Prisma SD-WAN API Client Initialization Failed")

    def __repr__(self):
        return f"<PrismaSDWANAPIClient(client_id={self.client_id})>"

    def __str__(self):
        return f"PrismaSDWANAPIClient()"

    # Contructs the URL for the API call from arguments provided
    def _build_url(self, endpoint="", suffix=""):
        return f"{self.base_url}{endpoint}{suffix}"

    # Handles the response from the API call
    def _handle_response(self, response):

        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            logger.error(
                f"{self} - HTTPError for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            logger.debug(
                f"{self} - HTTPError for Endpoint[{self.endpoint}]: Message \n{response.json()}"
            )
            return {"Status Code": response.status_code, "Message": response.json()}
        except requests.exceptions.RequestException as e:
            logger.error(
                f"{self} - RequestException for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            logger.debug(
                f"{self} - RequestException for Endpoint[{self.endpoint}]: Message \n{str(e)}"
            )
            return {"Status Code": "N/A", "Message": str(e)}

    #### << BASE METHODS >> ##################################################################

    def get_endpoint(self, endpoint="", suffix=""):

        # |--endpoint
        # |   string
        # |   required
        # |   The specific endpoint you want to query.
        # |
        # |--suffix
        # |   string
        # |   optional
        # |   The suffix to append to the endpoint for the GET request.

        self.client_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.get_auth_token()}",
        }

        self.endpoint = endpoint
        self.url = self._build_url(endpoint=endpoint, suffix=suffix)

        try:
            logger.info(f"{self} - GET Request to Endpoint[{self.endpoint}]")
            self.response = requests.get(self.url, headers=self.client_headers)
            self.response_headers = self.response.headers
            handled_response = self._handle_response(self.response)
            logger.info(
                f"{self} - GET Request Successful for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            logger.debug(
                f"{self} - Response: \n{json.dumps(handled_response, indent=2)}"
            )
            return handled_response

        except Exception as e:
            logger.error(
                f"{self} - GET Request Error for Endpoint[{self.endpoint}]: {str(e)}"
            )
            return {"Error": str(e)}

    def post_endpoint(self, endpoint="", suffix="", api_payload=""):

        # |--endpoint
        # |   string
        # |   required
        # |   The specific endpoint you want to query.
        # |
        # |--suffix
        # |   string
        # |   optional
        # |   The suffix to append to the endpoint for the GET request.

        self.endpoint = endpoint
        self.api_payload = api_payload
        self.url = self._build_url(endpoint=endpoint, suffix=suffix)

        self.client_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.get_auth_token()}",
        }

        try:
            logger.info(f"{self} - POST Request to Endpoint[{self.endpoint}]")
            self.response = requests.post(
                self.url, headers=self.client_headers, json=self.api_payload
            )
            self.response_headers = self.response.headers
            handled_response = self._handle_response(self.response)
            logger.info(
                f"{self} - POST Request Successful for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            return handled_response

        except Exception as e:
            logger.error(
                f"{self} - POST Request Error for Endpoint[{self.endpoint}]: {str(e)}"
            )
            return {"Error": str(e)}

    def put_endpoint(self, endpoint="", suffix="", api_payload=""):

        # |--endpoint
        # |   string
        # |   required
        # |   The specific endpoint you want to query.
        # |
        # |--suffix
        # |   string
        # |   optional
        # |   The suffix to append to the endpoint for the GET request.
        # |
        # |--api_payload
        # |   string
        # |   required
        # |   The JSON payload to send with the PUT request.

        self.endpoint = endpoint
        self.api_payload = api_payload
        self.url = self._build_url(endpoint=endpoint, suffix=suffix)

        self.client_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.get_auth_token()}",
        }

        try:
            logger.info(f"{self} - PUT Request to Endpoint[{self.endpoint}]")
            self.response = requests.put(
                self.url, headers=self.client_headers, json=self.api_payload
            )
            self.response_headers = self.response.headers
            handled_response = self._handle_response(self.response)
            logger.info(
                f"{self} - PUT Request Successful for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            return handled_response

        except Exception as e:
            logger.error(
                f"{self} - PUT Request Error for Endpoint[{self.endpoint}]: {str(e)}"
            )
            return {"Error": str(e)}

    def delete_endpoint(self, endpoint="", suffix=""):

        # |--endpoint
        # |   string
        # |   required
        # |   The specific endpoint you want to query.
        # |
        # |--suffix
        # |   string
        # |   optional
        # |   The suffix to append to the endpoint for the GET request.

        self.endpoint = endpoint
        self.url = self._build_url(endpoint=endpoint, suffix=suffix)

        self.client_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.get_auth_token()}",
        }

        try:
            logger.info(f"{self} - DELETE Request to Endpoint[{self.endpoint}]")
            self.response = requests.delete(self.url, headers=self.client_headers)
            self.response_headers = self.response.headers
            handled_response = self._handle_response(self.response)
            logger.info(
                f"{self} - DELETE Request Successful for Endpoint[{self.endpoint}]: Status Code {self.response.status_code}"
            )
            return handled_response

        except Exception as e:
            logger.error(
                f"{self} - DELETE Request Error for Endpoint[{self.endpoint}]: {str(e)}"
            )
            return {"Error": str(e)}

    #### << SITES >> #########################################################################

    def get_sdwan_sites(self, site_id=""):

        # |--site_id
        # |   string
        # |   optional
        # |   The site_id of a specific site.

        return self.get_endpoint(
            endpoint="/sdwan/v4.12/api/sites", suffix=f"/{site_id}" if site_id else ""
        )
    
    #### << SITE WAN INTERFACES >> ###########################################################
    
    def get_site_wan_interfaces(self, site_id, interface_id=""):

        # |--site_id
        # |   string
        # |   required
        # |   The site_id of a specific site.
        #
        # |--interface_id
        # |   string
        # |   optional
        # |   The interface_id of a specific interface. Corresponds to the Circuits configured at the site.

        return self.get_endpoint(
            endpoint=f"/sdwan/v2.10/api/sites/{site_id}/waninterfaces",
            suffix=f"/{interface_id}" if interface_id else "",
        )

    #### << ELEMENTS >> ######################################################################

    def get_elements(self, element_id=""):

        # |--suffix
        # |   string
        # |   optional
        # |   The element_id of a specific element.

        return self.get_endpoint(
            endpoint="/sdwan/v3.2/api/elements",
            suffix=f"/{element_id}" if element_id else "",
        )

    #### << ELEMENT STATUS >> ################################################################
    
    def get_element_status(self, element_id):

        # |--element_id
        # |   string
        # |   required
        # |   The element_id of a specific element.

        return self.get_endpoint(
            endpoint=f"/sdwan/v2.6/api/elements/{element_id}/status"
        )
    
    #### << GLOBAL PREFIXES >> ###############################################################

    def get_globalprefixes(self, prefix_id=""):

        # |--prefix_id
        # |   string
        # |   optional
        # |   The prefix_id of a specific prefix.

        return self.get_endpoint(
            endpoint="/sdwan/v2.1/api/networkpolicyglobalprefixes",
            suffix=f"/{prefix_id}" if prefix_id else "",
        )

    def create_globalprefix(self, api_payload):

        # | api_payload format:
        # | {
        # |   "id": "string",
        # |   "ipv4_prefixes": [
        # |     "string"
        # |   ],
        # |   "ipv6_prefixes": [
        # |     "string"
        # |   ],
        # |   "name": "string",
        # |   "tags": [
        # |     "string"
        # |   ]
        # | }

        return self.post_endpoint(
            endpoint="/sdwan/v2.1/api/networkpolicyglobalprefixes",
            api_payload=api_payload,
        )

    def update_globalprefix(self, prefix_id, api_payload):

        # | api_payload format:
        # | {
        # |   "_etag": integer (must match _etag of existing object),
        # |   "_schema": 1,
        # |   "id": "string",
        # |   "ipv4_prefixes": [
        # |     "string"
        # |   ],
        # |   "ipv6_prefixes": [
        # |     "string"
        # |   ],
        # |   "name": "string",
        # |   "tags": [
        # |     "string"
        # |   ]
        # | }

        return self.put_endpoint(
            endpoint="/sdwan/v2.1/api/networkpolicyglobalprefixes",
            suffix=f"/{prefix_id}",
            api_payload=api_payload,
        )

    def delete_globalprefix(self, prefix_id):

        # |--prefix_id
        # |   string
        # |   required
        # |   The prefix_id of a specific prefix.

        return self.delete_endpoint(
            endpoint="/sdwan/v2.1/api/networkpolicyglobalprefixes",
            suffix=f"/{prefix_id}",
        )


##############################################################################################
# Run
##############################################################################################

if __name__ == "__main__":

    pass
