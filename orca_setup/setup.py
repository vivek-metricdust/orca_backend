import ipaddress

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from log_manager.logger import get_backend_logger
from orca_setup.tasks import install_task, switch_image_task, scan_network_task

_logger = get_backend_logger()


@api_view(["PUT"])
def switch_sonic_image(request):
    result = []
    http_status = True
    if request.method == "PUT":
        req_data_list = (
            request.data if isinstance(request.data, list) else [request.data]
        )
        for req_data in req_data_list:
            device_ip = req_data.get("mgt_ip", "")
            if not device_ip:
                _logger.error("Required field device mgt_ip not found.")
                return Response(
                    {"status": "Required field device mgt_ip not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            image_name = req_data.get("image_name", "")
            if not req_data.get("image_name"):
                _logger.error("Required field image name not found.")
                return Response(
                    {"status": "Required field image name not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            task = switch_image_task.apply_async(
                kwargs={"device_ip": device_ip, "image_name": image_name, "http_path": request.path}
            )
            result.append(
                {
                    "message": f"{request.method}: request successful",
                    "status": "success",
                    "task_id": task.task_id
                }
            )
    return Response(
        {"result": result},
        status=(
            status.HTTP_202_ACCEPTED if http_status else status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
    )


@api_view(["PUT"])
def install_image(request):
    result = []
    http_status = True
    if request.method == "PUT":
        req_data_list = (
            request.data if isinstance(request.data, list) else [request.data]
        )
        for req_data in req_data_list:
            task_details = {}
            device_ips = req_data.get("device_ips", "")
            if not device_ips:
                _logger.error("Required field device_ips not found.")
                return Response(
                    {"status": "Required field device_ips not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            image_url = req_data.get("image_url", "")
            if not req_data.get("image_url"):
                _logger.error("Required field image url not found.")
                return Response(
                    {"status": "Required field image url not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            discover_also = req_data.get("discover_also", False)
            try:
                ips_to_install = []
                ips_to_scan = []
                for ip in device_ips:
                    network = ipaddress.ip_network(ip, strict=False)
                    if network.prefixlen == 32:
                        ips_to_install.append(ip)
                    else:
                        ips_to_scan.append(ip)
                if ips_to_scan:
                    scan_task_details = scan_network_task.apply_async(
                        kwargs={
                            "device_ips": ips_to_scan,
                            "image_url": image_url,
                            "discover_also": discover_also,
                            "username": req_data.get("username", None),
                            "password": req_data.get("password", None),
                            "http_path": request.path,
                        }
                    )
                    task_details["scan_task_id"] = scan_task_details.task_id
                if ips_to_install:
                    install_task_details = install_task.apply_async(
                        kwargs={
                            "device_ips": ips_to_install,
                            "image_url": image_url,
                            "discover_also": discover_also,
                            "username": req_data.get("username", None),
                            "password": req_data.get("password", None),
                            "http_path": request.path,
                        }
                    )
                    task_details["install_task_id"] = install_task_details.task_id
                result.append({**task_details, "message": f"{request.method}: request successful", "status": "success"})
            except Exception as err:
                result.append({"message": f"{request.method}: request failed with error: {err}", "status": "failed", })
                http_status = http_status and False
                _logger.error("Failed to install image. Error: %s", err)
    return Response(
        {"result": result},
        status=(
            status.HTTP_202_ACCEPTED if http_status else status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
    )
