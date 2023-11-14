from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from orca_nw_lib.port_chnl import (
    get_port_chnl,
    add_port_chnl,
    del_port_chnl,
    get_port_chnl_members,
    add_port_chnl_mem,
    del_port_chnl_mem,
)


@api_view(["GET", "PUT", "DELETE"])
def device_port_chnl_list(request):
    result = []
    http_status = True
    if request.method == "GET":
        device_ip = request.GET.get("mgt_ip", "")
        if not device_ip:
            return Response(
                {"status": "Required field device mgt_ip not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        port_chnl_name = request.GET.get("chnl_name", "")
        data = get_port_chnl(device_ip, port_chnl_name)

        for chnl in data if isinstance(data, list) else [data] if data else []:
            chnl["members"] = [
                intf["name"]
                for intf in get_port_chnl_members(device_ip, chnl["lag_name"])
            ]
        return JsonResponse(data, safe=False)

    if request.method == "PUT":
        req_data_list = (
            request.data if isinstance(request.data, list) else [request.data]
        )
        for req_data in req_data_list:
            device_ip = req_data.get("mgt_ip", "")
            if not device_ip:
                return Response(
                    {"status": "Required field device mgt_ip not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not req_data.get("chnl_name"):
                return Response(
                    {"status": "Required field device chnl_name not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                add_port_chnl(
                    device_ip,
                    req_data.get("chnl_name"),
                    admin_status=req_data.get("admin_status"),
                    mtu=int(req_data.get("mtu")) if "mtu" in req_data else None,
                )
                if members := req_data.get("members"):
                    add_port_chnl_mem(
                        device_ip,
                        req_data.get("chnl_name"),
                        members,
                    )
                result.append(f"{request.method} request successful :\n {req_data}")
                http_status = http_status and True
            except Exception as err:
                result.append(
                    f"{request.method} request failed :\n {req_data} \n {str(err)}"
                )
                http_status = http_status and False

    elif request.method == "DELETE":
        req_data_list = (
            request.data if isinstance(request.data, list) else [request.data]
        )
        for req_data in req_data_list:
            device_ip = req_data.get("mgt_ip", "")
            if not device_ip:
                return Response(
                    {"status": "Required field device mgt_ip not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not req_data.get("chnl_name"):
                return Response(
                    {"status": "Required field device chnl_name not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                # If member are given in the request body
                # Delete the members only, otherwise request is considered
                # to be for deleting the whole port channel
                if members := req_data.get("members"):
                    for mem in members:
                        del_port_chnl_mem(
                            device_ip,
                            req_data.get("chnl_name"),
                            mem,
                        )
                else:
                    del_port_chnl(device_ip, req_data.get("chnl_name"))

                result.append(f"{request.method} request successful :\n {req_data}")
                http_status = http_status and True
            except Exception as err:
                result.append(
                    f"{request.method} request failed :\n {req_data} \n {str(err)}"
                )
                http_status = http_status and False

    return Response(
        {"result": result},
        status=status.HTTP_200_OK
        if http_status
        else status.HTTP_500_INTERNAL_SERVER_ERROR,
    )