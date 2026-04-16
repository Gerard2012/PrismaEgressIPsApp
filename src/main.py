#!/usr/bin/env python3

##############################################################################################
# Modules, Global Variables & Config #########################################################
##############################################################################################

import os
import logging
from pprint import pprint
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from pathlib import Path
from egress_ips import EgressIP
from prisma_api_clients import PrismaAccessAPIClient, PrismaSDWANAPIClient


##############################################################################################
# Run
##############################################################################################

if __name__ == "__main__":

    # Configure logging to output to console with a specific format and also to a file for persistence
    log_dir = Path("src/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{Path(__file__).stem}.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # STDOUT → docker logs
            logging.FileHandler(log_file),  # FILE → persisted
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info("Application started")

    keyvault_url = os.getenv("KEYVAULT_URL")
    prisma_row_egress_ip_url = os.getenv("PRISMA_ROW_EGRESS_IP_URL")
    prisma_cn_egress_ip_url = os.getenv("PRISMA_CN_EGRESS_IP_URL")
    prisma_row_egress_ip_api_key_name = os.getenv("PRISMA_ROW_EGRESS_IP_API_KEY")
    prisma_cn_egress_ip_api_key_name = os.getenv("PRISMA_CN_EGRESS_IP_API_KEY")
    prisma_row_tenant_tsg_id = os.getenv("PRISMA_ROW_TENANT_TSG_ID")
    netops_prisma_client_id_name = os.getenv("NETOPS_PRISMA_CLIENT_ID")

    # Authenticate using system-assigned managed identity
    credential = DefaultAzureCredential()

    # Create a SecretClient to interact with Key Vault
    secret_client = SecretClient(vault_url=keyvault_url, credential=credential)

    # Retrieve Egress IP API keys from Key Vault
    prisma_row_egress_ip_api_key_secret = secret_client.get_secret(
        prisma_row_egress_ip_api_key_name
    )
    prisma_cn_egress_ip_api_key_secret = secret_client.get_secret(
        prisma_cn_egress_ip_api_key_name
    )

    # Retrieve Netops Prisma API credentials from Key Vault
    netops_prisma_client_id_secret = secret_client.get_secret(
        os.getenv("NETOPS_PRISMA_SECRET")
    )

    with EgressIP(
        prisma_row_egress_ip_url, prisma_row_egress_ip_api_key_secret.value
    ) as row_egress_ip_client:
        row_egress_ip_response = row_egress_ip_client.fetch_egress_ips()
        logger.info(
            f"Prisma Access ROW Egress IPs: {len(row_egress_ip_response)} IPs retrieved"
        )

    with EgressIP(
        prisma_cn_egress_ip_url, prisma_cn_egress_ip_api_key_secret.value
    ) as cn_egress_ip_client:
        cn_egress_ip_response = cn_egress_ip_client.fetch_egress_ips()
        logger.info(
            f"Prisma Access CN Egress IPs: {len(cn_egress_ip_response)} IPs retrieved"
        )

    with PrismaAccessAPIClient(
        prisma_row_tenant_tsg_id,
        netops_prisma_client_id_name,
        netops_prisma_client_id_secret.value,
    ) as prisma_access_client:

        prisma_access_response = prisma_access_client.get_addresses()
        logger.info(
            f"Prisma Access API Client: {len(prisma_access_response)} IPs retrieved"
        )
