"""
Functions to help registering kong API Gateway services and routes.
"""
import os
import requests
from typing import List


class KongManagement:
    """Class to help registering API on Kong Gateway."""

    def __init__(self, api_gateway_url: str,
                 service_name: str = None,
                 service_url: str = None,
                 healthcheck_endpoint: str = None,
                 auth_static_service: str = None,
                 test_reloaddb_service: str = None,
                 connect_timeout: int = None,
                 write_timeout: int = None,
                 read_timeout: int = None):
        """
        __init__.

        Args:
            api_gateway_url (str)kong_statup_obj: IP for the gateway.

        Kwards:
            service_name (str): Name of the Kong service.
            service_url (str): Url of the Kong service.
            healthcheck_endpoint (str): Path to health check end-point.
            auth_static_service (str): Path to the services that serve static
                files for auth.
            test_reloaddb_service (str): Path to test database to reload db.
        """
        if api_gateway_url[-1] == '/':
            api_gateway_url = api_gateway_url[:-1]

        self.service_name = service_name
        self.service_url = service_url
        self.api_gateway_url = api_gateway_url
        self.healthcheck_endpoint = healthcheck_endpoint

        if service_name is not None:
            template_service = "{api_gateway_url}/services/{service_name}/"
            temp_service_url = template_service.format(
                api_gateway_url=self.api_gateway_url,
                service_name=self.service_name)
            payload = {
                'name': self.service_name,
                'url': self.service_url}

            # ajust timeouts
            if connect_timeout is not None:
                payload["connect_timeout"] = connect_timeout
            if write_timeout is not None:
                payload["write_timeout"] = write_timeout
            if read_timeout is not None:
                payload["read_timeout"] = read_timeout

            response = requests.put(
                temp_service_url, json=payload)
            response.raise_for_status()
            self.kong_service = response.json()

            routes_url_template = "{api_gateway_url}/routes/{route_name}"
            if self.healthcheck_endpoint is not None:
                response = requests.put(
                    routes_url_template.format(
                        api_gateway_url=self.api_gateway_url,
                        route_name=self.service_name + "--health-check"
                    ),
                    json={
                        "paths": [self.healthcheck_endpoint],
                        "strip_path": False,
                        "service": {"id": self.kong_service["id"]}
                    })
                response.raise_for_status()

            if auth_static_service is not None:
                # Create service para Auth Static
                temp_service_url = template_service.format(
                    api_gateway_url=self.api_gateway_url,
                    service_name=self.service_name + "--auth-static")
                response = requests.put(
                    temp_service_url, json={
                        'name': self.service_name + "--auth-static",
                        'url': auth_static_service})
                response.raise_for_status()
                static_service = response.json()

                # Add a rota para trazer os arquivos estaticos para auth
                auth_static_url = "/admin/{service_name}/static/".format(
                    service_name=self.service_name)
                response = requests.put(
                    routes_url_template.format(
                        api_gateway_url=self.api_gateway_url,
                        route_name=self.service_name + "--auth-static"
                    ),
                    json={
                        "paths": [auth_static_url],
                        "strip_path": False,
                        "service": {"id": static_service["id"]}
                    })
                response.raise_for_status()

                # Add a rota para trazer os arquivos gui para auth
                auth_gui_url = "/admin/{service_name}/gui/".format(
                    service_name=self.service_name)
                response = requests.put(
                    routes_url_template.format(
                        api_gateway_url=self.api_gateway_url,
                        route_name=self.service_name + "--auth-gui"
                    ),
                    json={
                        "paths": [auth_gui_url],
                        "strip_path": False,
                        "service": {"id": self.kong_service["id"]}
                    })
                response.raise_for_status()

            # test-db-pumpwood-auth
            if test_reloaddb_service is not None:
                # create service for db reload
                temp_service_url = template_service.format(
                    api_gateway_url=self.api_gateway_url,
                    service_name=self.service_name + "--reloaddb")
                response = requests.put(
                    temp_service_url, json={
                        'name': self.service_name + "--reloaddb",
                        'url': test_reloaddb_service})
                response.raise_for_status()
                reloaddb_service = response.json()
                #################################################

                # registers rotes for reload db
                template_reload_url = "/reload-db/{service_name}/"
                reload_url = template_reload_url.format(
                    service_name=self.service_name)

                response = requests.put(
                    routes_url_template.format(
                        api_gateway_url=self.api_gateway_url,
                        route_name=self.service_name + "--reloaddb"
                    ),
                    json={
                        "paths": [reload_url],
                        "strip_path": False,
                        "service": {"id": reloaddb_service["id"]}
                    })
                response.raise_for_status()

                # registers rotes for connection dispose
                template_dispose_url = \
                    "/pool-conections-dispose/{service_name}/"
                dispose_url = template_dispose_url.format(
                    service_name=self.service_name)
                response = requests.put(
                    routes_url_template.format(
                        api_gateway_url=self.api_gateway_url,
                        route_name=self.service_name + "--connection-dispose"
                    ),
                    json={
                        "paths": [dispose_url],
                        "strip_path": False,
                        "service": {"id": self.kong_service["id"]}
                    })
                response.raise_for_status()

    def register_models(self, models_names=List[str]):
        """
        Register end-points.

        Args:
            endpoints (list[str]): List of the end-points to be added to;
                kong. It must be full path end there will be no strip_path. Ex:
                    - /rest/descriptionmodel/
                    - /rest/registration/
        """
        # Get EndPoint Suffix if set
        suffix = os.getenv('ENDPOINT_SUFFIX', '')

        if self.service_name is None:
            raise Exception("Service name (service_name) is not set.")

        if len(models_names) != 0:
            routes_url_template = "{api_gateway_url}/routes/{route_name}"
            response = requests.put(
                routes_url_template.format(
                    api_gateway_url=self.api_gateway_url,
                    route_name=self.service_name + "--endpoints"
                ),
                json={
                    "paths": ["/rest/" + suffix.lower() + x.lower() + "/"
                              for x in models_names],
                    "strip_path": False,
                    "service": {"id": self.kong_service["id"]}
                })
            response.raise_for_status()

    def list_all_routes(self):
        """List all routes that have been registed to Kong."""
        routes_url_template = "{api_gateway_url}/routes/"
        services_url_template = "{api_gateway_url}/services/"

        # get services and routes avaiable on kong
        response_services = requests.get(
            services_url_template.format(api_gateway_url=self.api_gateway_url))
        response_routes = requests.get(
            routes_url_template.format(api_gateway_url=self.api_gateway_url))
        response_services.raise_for_status()
        response_routes.raise_for_status()

        data_services = response_services.json()
        dict_services = dict(
            [(s["id"], s["name"]) for s in data_services["data"]])
        data_routes = response_routes.json()

        dict_routes = {}
        for route in data_routes["data"]:
            service_name = dict_services[route["service"]["id"]]
            routes_in_service = dict_routes.get(service_name, [])
            for p in route["paths"]:
                routes_in_service.append(p)
            dict_routes[service_name] = routes_in_service

        for key, item in dict_routes.items():
            item.sort()

        for s in data_services["data"]:
            if s["name"] not in dict_routes.keys():
                dict_routes[s["name"]] = []
        return dict_routes
