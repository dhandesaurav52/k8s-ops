import logging
from typing import Optional, Tuple
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger("SkyOps.K8sClient")


def get_k8s_clients(
    kubeconfig_path: Optional[str] = None,
) -> Tuple[client.CoreV1Api, client.ApiClient]:
    """
    Initialize Kubernetes API clients.
    Tries in-cluster config first if running inside K8s,
    otherwise falls back to local kubeconfig.
    """
    try:
        if kubeconfig_path:
            config.load_kube_config(config_file=kubeconfig_path)
            logger.info(f"Loaded kubeconfig from {kubeconfig_path}")
        else:
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            except config.ConfigException:
                config.load_kube_config()
                logger.info("Loaded local kubeconfig file")

        api_client = client.ApiClient()
        v1 = client.CoreV1Api(api_client)
        return v1, api_client
    except Exception as e:
        logger.error(f"Failed to initialize Kubernetes client: {e}")
        raise RuntimeError(
            f"Could not connect to Kubernetes API server. Reason: {e}"
        )


def get_all_k8s_apis(
    kubeconfig_path: Optional[str] = None,
) -> Tuple[client.CoreV1Api, client.AppsV1Api, client.StorageV1Api, client.ApiClient]:
    """
    Initialize CoreV1Api, AppsV1Api, StorageV1Api, and ApiClient.
    """
    try:
        if kubeconfig_path:
            config.load_kube_config(config_file=kubeconfig_path)
        else:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()

        api_client = client.ApiClient()
        v1 = client.CoreV1Api(api_client)
        apps_v1 = client.AppsV1Api(api_client)
        storage_v1 = client.StorageV1Api(api_client)
        return v1, apps_v1, storage_v1, api_client
    except Exception as e:
        logger.error(f"Failed to initialize Kubernetes API clients: {e}")
        raise RuntimeError(f"Could not connect to Kubernetes API server. Reason: {e}")



def check_connection(v1: client.CoreV1Api) -> bool:
    """
    Verify API connection by pinging Kubernetes API server.
    """
    try:
        v1.get_api_resources()
        return True
    except ApiException as e:
        logger.error(f"Kubernetes API connection test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Kubernetes connection error: {e}")
        return False
