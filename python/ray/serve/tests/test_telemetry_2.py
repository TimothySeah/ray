import sys
import time
from typing import List, Optional

import pytest

from ray import serve
from ray._common.test_utils import wait_for_condition
from ray.serve._private.request_router.common import (
    PendingRequest,
)
from ray.serve._private.request_router.replica_wrapper import (
    RunningReplica,
)
from ray.serve._private.request_router.request_router import (
    RequestRouter,
)
from ray.serve._private.test_utils import check_apps_running, check_telemetry
from ray.serve._private.usage import ServeUsageTag
from ray.serve.config import RequestRouterConfig
from ray.serve.context import _get_global_client
from ray.serve.schema import ServeDeploySchema


class CustomRequestRouter(RequestRouter):
    async def choose_replicas(
        self,
        candidate_replicas: List[RunningReplica],
        pending_request: Optional[PendingRequest] = None,
    ) -> List[List[RunningReplica]]:
        return [candidate_replicas]


@pytest.mark.parametrize("location", ["driver", "deployment", None])
def test_status_api_detected(manage_ray_with_telemetry, location):
    """Check that serve.status is detected correctly by telemetry."""

    # Check telemetry is not recorded before test starts
    check_telemetry(ServeUsageTag.SERVE_STATUS_API_USED, expected=None)

    @serve.deployment
    class Model:
        async def __call__(self):
            return serve.status()

    if location:
        if location == "deployment":
            handle = serve.run(Model.bind(), route_prefix="/model")
            handle.remote()
        elif location == "driver":
            serve.status()

        wait_for_condition(
            check_telemetry, tag=ServeUsageTag.SERVE_STATUS_API_USED, expected="1"
        )
    else:
        for _ in range(3):
            check_telemetry(ServeUsageTag.SERVE_STATUS_API_USED, expected=None)
            time.sleep(1)


@pytest.mark.parametrize("location", ["driver", "deployment", None])
def test_get_app_handle_api_detected(manage_ray_with_telemetry, location):
    """Check that serve.get_app_handle is detected correctly by telemetry."""

    # Check telemetry is not recorded before test starts
    check_telemetry(ServeUsageTag.SERVE_GET_APP_HANDLE_API_USED, expected=None)

    @serve.deployment
    class Model:
        async def __call__(self):
            serve.get_app_handle("telemetry")

    if location:
        if location == "deployment":
            handle = serve.run(Model.bind(), route_prefix="/model")
            handle.remote()
        elif location == "driver":
            serve.get_app_handle("telemetry")

        wait_for_condition(
            check_telemetry,
            tag=ServeUsageTag.SERVE_GET_APP_HANDLE_API_USED,
            expected="1",
        )
    else:
        for _ in range(3):
            check_telemetry(ServeUsageTag.SERVE_GET_APP_HANDLE_API_USED, expected=None)
            time.sleep(1)


@pytest.mark.parametrize("location", ["driver", "deployment", None])
def test_get_deployment_handle_api_detected(manage_ray_with_telemetry, location):
    """Check that serve.get_deployment_handle is detected correctly by telemetry."""

    check_telemetry(ServeUsageTag.SERVE_GET_DEPLOYMENT_HANDLE_API_USED, expected=None)

    @serve.deployment
    class Model:
        async def __call__(self):
            serve.get_deployment_handle("TelemetryReceiver", "telemetry")

    if location:
        if location == "deployment":
            handle = serve.run(Model.bind(), route_prefix="/model")
            handle.remote()
        elif location == "driver":
            serve.get_deployment_handle("TelemetryReceiver", "telemetry")

        wait_for_condition(
            check_telemetry,
            tag=ServeUsageTag.SERVE_GET_DEPLOYMENT_HANDLE_API_USED,
            expected="1",
        )
    else:
        for _ in range(3):
            check_telemetry(
                ServeUsageTag.SERVE_GET_DEPLOYMENT_HANDLE_API_USED, expected=None
            )
            time.sleep(1)


class Model:
    pass


app_model = serve.deployment(Model).bind()


@pytest.mark.parametrize("mode", ["deployment", "options", "config"])
def test_num_replicas_auto(manage_ray_with_telemetry, mode):
    check_telemetry(ServeUsageTag.AUTO_NUM_REPLICAS_USED, expected=None)

    if mode == "deployment":
        serve.run(serve.deployment(num_replicas="auto")(Model).bind())
    elif mode == "options":
        serve.run(serve.deployment(Model).options(num_replicas="auto").bind())
    elif mode == "config":
        config = {
            "applications": [
                {
                    "name": "default",
                    "import_path": "ray.serve.tests.test_telemetry_2.app_model",
                    "deployments": [{"name": "Model", "num_replicas": "auto"}],
                },
            ]
        }
        client = _get_global_client()
        client.deploy_apps(ServeDeploySchema(**config))
        wait_for_condition(check_apps_running, apps=["default"])

    wait_for_condition(
        check_telemetry, tag=ServeUsageTag.AUTO_NUM_REPLICAS_USED, expected="1"
    )


def test_custom_request_router_telemetry(manage_ray_with_telemetry):
    """Check that the custom request router telemetry is recorded."""

    check_telemetry(ServeUsageTag.CUSTOM_REQUEST_ROUTER_USED, expected=None)

    @serve.deployment(
        request_router_config=RequestRouterConfig(
            request_router_class=CustomRequestRouter,
        ),
    )
    class CustomRequestRouterApp:
        async def __call__(self) -> str:
            return "ok"

    handle = serve.run(CustomRequestRouterApp.bind())
    result = handle.remote().result()

    assert result == "ok"

    wait_for_condition(
        check_telemetry, tag=ServeUsageTag.CUSTOM_REQUEST_ROUTER_USED, expected="1"
    )


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "-s", __file__]))
