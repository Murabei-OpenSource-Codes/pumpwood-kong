"""Functions to help registering kong API Gateway services and routes."""
import requests
from pumpwood_communication import exceptions


template_service = "{api_gateway_url}/services/{service_name}/"
routes_url_template = "{api_gateway_url}/routes/{route_name}/"


class KongAPI:
    """Help setting routes on Kong Api."""

    def __init__(self, api_gateway_url: str, connect_timeout: int = 300000,
                 write_timeout: int = 300000, read_timeout: int = 300000):
        """
        __init__.

        Args:
            api_gateway_url [str]:
        Kwargs:
            connect_timeout [int]: Kong connect timeout.
            write_timeout [int]: Kong write timeout.
            read_timeout [int]: Kong read timeout.
        """
        if api_gateway_url[-1] == '/':
            api_gateway_url = api_gateway_url[:-1]

        self.api_gateway_url = api_gateway_url
        self.connect_timeout = connect_timeout
        self.write_timeout = write_timeout
        self.read_timeout = read_timeout

        self._url_services = "{api_gateway_url}/services".format(
            api_gateway_url=self.api_gateway_url)
        self._url_service = self._url_services + "/{service_id}"
        self._url_services_routes = self._url_service + "/routes"
        self._url_services_route = self._url_services_routes + "/{route_id}"

        self._url_routes = "{api_gateway_url}/routes".format(
            api_gateway_url=self.api_gateway_url)
        self._url_route = self._url_routes + "/{route_id}"

    def list_services(self) -> list:
        """
        List Kong services.

        Args:
            No Args.
        Return [list(dict)]:
            List of services avaiable at Kong
        Exceptions:
            Raise response status.
        """
        response = requests.get(self._url_services)
        response.raise_for_status()
        return response.json()["data"]

    def list_service_routes(self, service_id: str) -> list:
        """
        List service routes.

        Args:
            service_id [str]: Kong service id.
        Return [list(dict)]:
            Return a list of dictionaries with information of routes of the
            service.
        Exceptions:
            Raise response status.
        """
        response = requests.get(
            self._url_services_routes.format(service_id=service_id))
        response.raise_for_status()
        return response.json()["data"]

    def delete_service(self, service_id: str) -> list:
        """
        List service routes.

        Args:
            service_id [str]: Kong service id.
        Return [bool]:
            Return True
        Exceptions:
            Raise response status.
        """
        response = requests.delete(
            self._url_service.format(service_id=service_id))
        response.raise_for_status()
        return True

    def delete_route(self, route_id: str) -> bool:
        """
        List service routes.

        Args:
            route_id [str]: Kong id for the route.
        Return [bool]:
            Return True
        Exceptions:
            Raise response status.
        """
        response = requests.delete(
            self._url_route.format(route_id=route_id))
        response.raise_for_status()
        return True

    def delete_routes_and_service(self, list_service_id: list = None) -> bool:
        """
        Delete all kong services and associated routes.

        Services with names starting with 'test' are not removed as they may
        be used for testing.

        Args:
            service_ids [list]: List of service ids to remove from Kong.
        Return [bool]:
            Return True.
        """
        if list_service_id is None:
            list_services = self.list_services()

            # Do not delete services associated with testing, this is used
            # for regen databases
            list_service_id = [
                x["id"] for x in list_services
                if not (
                    x["name"].startswith("test") or
                    x["name"].startswith("reload-db"))]
        for service_id in list_service_id:
            list_routes = self.list_service_routes(service_id=service_id)
            for route in list_routes:
                self.delete_route(route_id=route["id"])
            self.delete_service(service_id=service_id)
        return True

    def register_service(self, service_name: str, service_url: str,
                         healthcheck_route: str = None,
                         service_kong_id: str = None):
        """
        Register a service at Kong.

        Args:
            service_name [str]: Name of the service to be created.
            service_url [str]: Url to redirect calls to this service.
        Kwargs:
            healthcheck_route [str]: A healthcheck end-point for the
                service if avaiable.
            service_kong_id [str]: ID of the service at kong.
        """
        temp_service_url = template_service.format(
            api_gateway_url=self.api_gateway_url,
            service_name=service_name)
        payload = {
            'name': service_name,
            'url': service_url,
            'connect_timeout': self.connect_timeout,
            'write_timeout': self.write_timeout,
            'read_timeout': self.read_timeout}
        response = requests.put(
            temp_service_url, json=payload)
        try:
            response.raise_for_status()
        except Exception as e:
            response_text = response.text
            msg = (
                "[{erro_type}] {error_msg}\n"
                "[Request Text] {request_text}")
            raise exceptions.PumpWoodException(
                message=msg,
                payload={
                    "erro_type": type(e).__name__,
                    "error_msg": str(e),
                    "request_text": response_text})

        kong_service = response.json()
        if healthcheck_route is not None:
            response = requests.put(
                routes_url_template.format(
                    api_gateway_url=self.api_gateway_url,
                    route_name=service_name + "--health-check"
                ),
                json={
                    "paths": [healthcheck_route],
                    "strip_path": False,
                    "service": {"id": kong_service["id"]}
                })
        return kong_service

    def register_route(self, route_url: str, route_name: str,
                       service_id: str = None, service_name: str = None,
                       strip_path: bool = False):
        """
        Register Route on Kong.

        Args:
            service_id [str]: Kong service id.
            route_url [str]: End-point route to be registred service by Kong.
            route_name [str]: Name of the route.
        Kwargs:
            service_id: str: Kong Service ID.
            service_name: str = Kong Service Name.
        """
        # Raise erros if parameters does not make sense
        is_none_service_id = service_id is None
        is_none_service_name = service_name is None
        if is_none_service_id and is_none_service_name:
            msg = (
                "'service_id' and 'service_name' are None. "
                "It is necessary that one is not None")
            raise exceptions.PumpWoodException(
                message=msg,
                payload={})

        if not is_none_service_id and not is_none_service_name:
            msg = (
                "'service_id' and 'service_name' are not None. "
                "It is necessary that one is None")
            raise exceptions.PumpWoodException(
                message=msg,
                payload={})

        if not is_none_service_id:
            response = requests.put(
                routes_url_template.format(
                    api_gateway_url=self.api_gateway_url,
                    route_name=route_name
                ),
                json={
                    "paths": [route_url],
                    "strip_path": strip_path,
                    "id": {"id": service_id}
                })

            try:
                response.raise_for_status()
            except Exception as e:
                response_text = response.text
                msg = (
                    "[{erro_type}] {error_msg}\n"
                    "[Request Text] {request_text}")
                raise exceptions.PumpWoodException(
                    message=msg,
                    payload={
                        "erro_type": type(e).__name__,
                        "error_msg": str(e),
                        "request_text": response_text})
            return response.json()

        else:
            response = requests.put(
                routes_url_template.format(
                    api_gateway_url=self.api_gateway_url,
                    route_name=route_name
                ),
                json={
                    "paths": [route_url],
                    "strip_path": strip_path,
                    "service": {"name": service_name}
                })

            try:
                response.raise_for_status()
            except Exception as e:
                response_text = response.text
                msg = (
                    "[{erro_type}] {error_msg}\n"
                    "[Request Text] {request_text}")
                raise exceptions.PumpWoodException(
                    message=msg,
                    payload={
                        "erro_type": type(e).__name__,
                        "error_msg": str(e),
                        "request_text": response_text})
            return response.json()

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
