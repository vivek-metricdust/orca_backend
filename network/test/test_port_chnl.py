"""
This module contains tests for the Interface API.
"""
from orca_nw_lib.common import IFMode
from rest_framework import status

from network.test.test_common import TestORCA


class TestPortChnl(TestORCA):
    """
    This class contains tests for the Port Channel API.
    """

    def test_port_channel_config(self):
        """
        Test the port channel configuration.

        This function tests the configuration of the port channels. It sends a DELETE
        request to the device's port channel endpoint to remove any existing port
        channels. Then, it sends a series of GET requests to ensure that the port
        channels have been successfully removed. Next, it sends a PUT request to
        create new port channels with specific configurations. Finally, it sends
        additional GET requests to verify the creation and configuration of the
        port channels.

        Parameters:
        - self: The instance of the test class.

        Returns:
        None
        """
        device_ip = list(self.device_ips.keys())[0]

        # First delete mclag, if it exists.
        # port channel deletion will fail if port channel is found to be a member of mclag.
        self.remove_mclag(device_ip)

        request_body = [
            {
                "mgt_ip": device_ip,
                "lag_name": "PortChannel101",
                "mtu": 8000,
                "admin_status": "up",
            },
            {
                "mgt_ip": device_ip,
                "lag_name": "PortChannel102",
                "mtu": 9100,
                "admin_status": "up",
            },
        ]

        ## Better cleanup all port channels first may be there are existing
        # port channels with member interfaces which are of interest of this
        # test case.
        self.perform_del_port_chnl(request_body)

        # Now delete port channels
        self.perform_del_add_del_port_chnl(request_body)

    def test_port_chnl_mem_config(self):
        """
        Test the configuration of port channel members.
        """
        device_ip = list(self.device_ips.keys())[0]

        ether_1 = self.device_ips[device_ip]["interfaces"][0]
        ether_2 = self.device_ips[device_ip]["interfaces"][1]
        ether_3 = self.device_ips[device_ip]["interfaces"][2]
        ether_4 = self.device_ips[device_ip]["interfaces"][3]
        mtu = 9100

        request_body = [
            {
                "mgt_ip": device_ip,
                "lag_name": "PortChannel101",
                "mtu": mtu,
                "admin_status": "up",
                "members": [ether_1, ether_2],
            },
            {
                "mgt_ip": device_ip,
                "lag_name": "PortChannel102",
                "mtu": mtu,
                "admin_status": "up",
                "members": [ether_3, ether_4],
            },
        ]

        ## Better cleanup all port channels first, may be there are existing
        # port channels with the member interfaces which are of interest of this
        # test case.
        self.perform_del_port_chnl(request_body)

        ## Members of a port channel members should have same speed and mtu
        request_body_eth = [
            {"mgt_ip": device_ip, "name": ether_1, "mtu": mtu},
            {"mgt_ip": device_ip, "name": ether_2, "mtu": mtu},
            {"mgt_ip": device_ip, "name": ether_3, "mtu": mtu},
            {"mgt_ip": device_ip, "name": ether_4, "mtu": mtu},
        ]
        for req in request_body_eth:
            response_1 = self.assert_with_timeout_retry(
                lambda path, payload: self.get_req(path, payload),
                "device_interface_list",
                {"mgt_ip": device_ip, "name": req["name"]},
                status=status.HTTP_200_OK,
            )

            speed_1 = response_1.json()["speed"]
            req["speed"] = self.get_common_speed_to_set(speed_1)

            self.assert_with_timeout_retry(
                lambda path, payload: self.put_req(path, payload),
                "device_interface_list",
                req,
                status=status.HTTP_200_OK,
            )

            self.assert_with_timeout_retry(
                lambda path, payload: self.get_req(path, payload),
                "device_interface_list",
                req,
                status=status.HTTP_200_OK,
                speed=req["speed"],
                mtu=req["mtu"],
            )

        # delete mclag, if it exists.
        # port channel deletion will fail if port channel is found to be a member of mclag.
        self.remove_mclag(device_ip)

        ## If any portchannel member interface is also a member of vlan it wont be added to portchannel
        ## So better remove all vlans from Interfaces first.
        for req in request_body:
            for mem in req["members"]:
                self.assert_response_status(
                    self.del_req(
                        "device_interface_list", {"mgt_ip": device_ip, "name": mem}
                    ),
                    status.HTTP_200_OK,
                    "resource not found",
                )

        ## Delete MCLAG if exists, because if the port channel being deleted in the next steps is being used in MCLAG,
        # deletion will fail.
        self.assert_response_status(
            self.del_req("device_mclag_list", request_body),
            status.HTTP_200_OK,
            "resource not found",
        )

        self.perform_add_port_chnl(request_body)
        self.perform_add_port_chnl_mem_eth(request_body)
        self.perform_del_port_chnl(request_body)

    def test_port_chnl_static_attribute(self):
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        port_channel = "PortChannel103"

        # request body for adding port channel static as True
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "static": True,
        }
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        self.perform_add_port_chnl([request_body])
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["static"], True)

        # since static attribute cannot be updated delete port channel and then create it again
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        # request body for adding port channel static as False
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "static": False,
        }
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        self.perform_add_port_chnl([request_body])
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["static"], False)
        self.perform_del_port_chnl(request_body)

    def test_port_chnl_fallback_attribute(self):
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        port_channel = "PortChannel103"

        # testing fallback attribute on port channel with True
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "fallback": True,
        }

        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["fallback"], True)

        # updating fallback attribute to False
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "fallback": False,
        }
        response = self.put_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["fallback"], False)
        self.perform_del_port_chnl(request_body)

    def test_port_chnl_fast_rate_attribute(self):
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        port_channel = "PortChannel103"

        # testing fast_rate attribute on port channel creation with True
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "fast_rate": True,
        }
        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["fast_rate"], True)

        # updating fast_rate attribute to False
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "fast_rate": False,
        }
        response = self.put_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["fast_rate"], False)
        self.perform_del_port_chnl(request_body)

    def test_port_chnl_min_links_attribute(self):
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        port_channel = "PortChannel103"

        # testing min_links attribute on port channel creation
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "min_links": 2,
        }
        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["min_links"], 2)

        # updating min_links attribute with 4
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "min_links": 4,
        }
        response = self.put_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["min_links"], 4)
        self.perform_del_port_chnl(request_body)

    def test_port_chnl_description_attribute(self):
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        port_channel = "PortChannel103"

        # testing description attribute on port channel creation
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "description": "test",
        }
        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["description"], "test")

        # updating description attribute
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "description": "test2",
        }
        response = self.put_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["description"], "test2")
        self.perform_del_port_chnl(request_body)

    def test_port_chnl_grace_full_shutdown_attributes(self):
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        port_channel = "PortChannel103"

        # Test graceful_shutdown_mode attribute on port channel creation
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "graceful_shutdown_mode": "Enable",
        }
        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["graceful_shutdown_mode"], "ENABLE")

        # updating graceful_shutdown_mode attribute
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "graceful_shutdown_mode": "Disable",
        }
        response = self.put_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["graceful_shutdown_mode"], "DISABLE")
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

    def test_port_channel_ip_delete(self):
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        ip_address_1 = "192.10.10.9/24"
        port_channel = "PortChannel103"
        # Test ip_address attribute on port channel creation
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "ip_address": ip_address_1,
        }

        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["ip_address"], ip_address_1)

        # Testing delete ip_address with sending ip
        del_resp = self.del_req(
            "port_channel_ip_remove",
            {"mgt_ip": device_ip, "lag_name": port_channel},
        )
        self.assertEqual(del_resp.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["ip_address"], None)
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

    def test_port_channel_ip(self):
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        ip_address_1 = "192.10.10.9/24"
        ip_address_2 = "192.11.10.9/24"
        port_channel = "PortChannel103"
        # Test ip_address attribute on port channel creation
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "ip_address": ip_address_1,
        }

        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["ip_address"], ip_address_1)

        # updating ip_address attribute
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "ip_address": ip_address_2,
        }
        response = self.put_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["ip_address"], ip_address_2)

        # Testing delete ip_address
        del_resp = self.del_req(
            "port_channel_ip_remove",
            {"mgt_ip": device_ip, "lag_name": port_channel, "ip_address": ip_address_2},
        )
        self.assertEqual(del_resp.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "device_port_chnl", {"mgt_ip": device_ip, "lag_name": port_channel}
        )
        self.assertEqual(response.json()["ip_address"], None)
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

    def test_port_channel_vlan_members_access_vlan_members_update(self):
        # Creating vlan for testing
        device_ip = list(self.device_ips.keys())[0]
        vlan_1_name = "Vlan4"
        vlan_1_id = 4
        vlan_2_name = "Vlan5"
        vlan_2_id = 5
        vlan_3_name = "Vlan6"
        vlan_3_id = 6
        port_channel = "PortChannel103"
        req_payload = [
            {
                "mgt_ip": device_ip,
                "name": vlan_1_name,
                "vlanid": vlan_1_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_2_name,
                "vlanid": vlan_2_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_3_name,
                "vlanid": vlan_3_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
        ]

        response = self.put_req(
            "vlan_config",
            req_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing whether vlans are added or not
        response = self.get_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_1_id)
        self.assertEqual(response.json()["name"], vlan_1_name)
        response = self.get_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_2_id)
        self.assertEqual(response.json()["name"], vlan_2_name)
        response = self.get_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_3_id)
        self.assertEqual(response.json()["name"], vlan_3_name)

        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "vlan_members": {
                "if_mode": str(IFMode.ACCESS),
                "vlan_ids": [vlan_1_id]
            }
        }
        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])

        get_response = self.get_req(
            "device_port_chnl",
            request_body,
        )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members.get("if_mode"), str(IFMode.ACCESS))
        self.assertEqual(members.get("vlan_ids"), [vlan_1_id])

        # Test updating access vlan members
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "vlan_members": {
                "if_mode": str(IFMode.ACCESS),
                "vlan_ids": [vlan_2_id],
            }
        }
        member_update_response = self.put_req("device_port_chnl", req_json=request_body)
        self.assertEqual(member_update_response.status_code, status.HTTP_200_OK)
        get_response = self.get_req(
            "device_port_chnl",
            request_body,
        )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members.get("if_mode"), str(IFMode.ACCESS))
        self.assertEqual(members.get("vlan_ids"), [vlan_2_id])

        # deleting portchannel vlan members
        member_delete_response = self.del_req(
            "port_chnl_vlan_member_remove_all", req_json=request_body
        )
        self.assertEqual(member_delete_response.status_code, status.HTTP_200_OK)

        get_response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members, {})

        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_port_channel_vlan_members_trunk_members_update(self):
        # Creating vlan for testing
        device_ip = list(self.device_ips.keys())[0]
        vlan_1_name = "Vlan4"
        vlan_1_id = 4
        vlan_2_name = "Vlan5"
        vlan_2_id = 5
        vlan_3_name = "Vlan6"
        vlan_3_id = 6
        port_channel = "PortChannel103"
        req_payload = [
            {
                "mgt_ip": device_ip,
                "name": vlan_1_name,
                "vlanid": vlan_1_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_2_name,
                "vlanid": vlan_2_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_3_name,
                "vlanid": vlan_3_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
        ]

        response = self.put_req(
            "vlan_config",
            req_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing whether vlans are added or not
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_1_id)
        self.assertEqual(response.json()["name"], vlan_1_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_2_id)
        self.assertEqual(response.json()["name"], vlan_2_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_3_id)
        self.assertEqual(response.json()["name"], vlan_3_name)

        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "vlan_members": {
                "if_mode": str(IFMode.TRUNK),
                "vlan_ids": [vlan_2_id]
            }
        }
        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])

        get_response = self.get_req("device_port_chnl", request_body, )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members.get("if_mode"), str(IFMode.TRUNK))
        self.assertEqual(members.get("vlan_ids"), [vlan_2_id])

        # Test updating trunk vlan members
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "vlan_members": {
                "if_mode": str(IFMode.TRUNK),
                "vlan_ids": [vlan_1_id, vlan_3_id],
            }
        }
        member_update_response = self.put_req("device_port_chnl", req_json=request_body)
        self.assertEqual(member_update_response.status_code, status.HTTP_200_OK)
        get_response = self.get_req("device_port_chnl", request_body, )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members.get("if_mode"), str(IFMode.TRUNK))
        self.assertEqual(members.get("vlan_ids"), [vlan_1_id, vlan_2_id, vlan_3_id])

        # deleting portchannel vlan members
        member_delete_response = self.del_req("port_chnl_vlan_member_remove_all", req_json=request_body)
        self.assertEqual(member_delete_response.status_code, status.HTTP_200_OK)

        get_response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members, {})

        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_port_channel_vlan_members_in_series_with_dot(self):
        """
        Test case for adding vlan members in port channel in series with hyphen.
        eg . {trunk_vlans: [1, "3..5"], access_vlan: 4}
        """
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        port_channel = "PortChannel103"
        vlan_1_name = "Vlan3"
        vlan_1_id = 3
        vlan_2_name = "Vlan4"
        vlan_2_id = 4
        vlan_3_name = "Vlan5"
        vlan_3_id = 5

        req_payload = [
            {
                "mgt_ip": device_ip,
                "name": vlan_1_name,
                "vlanid": vlan_1_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_2_name,
                "vlanid": vlan_2_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan2",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_3_name,
                "vlanid": vlan_3_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan3",
            },
        ]

        response = self.put_req(
            "vlan_config",
            req_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing whether vlans are added or not
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_1_id)
        self.assertEqual(response.json()["name"], vlan_1_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_2_id)
        self.assertEqual(response.json()["name"], vlan_2_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_3_id)
        self.assertEqual(response.json()["name"], vlan_3_name)

        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "vlan_members": {
                "if_mode": str(IFMode.TRUNK),
                "vlan_ids": [f"{vlan_1_id}..{vlan_3_id}"]
            }
        }

        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl(request_body)
        response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("lag_name"), port_channel)
        self.assertEqual(response.json().get("mtu"), 9100)
        self.assertEqual(response.json().get("admin_sts"), "up")
        members = response.json().get("vlan_members")
        self.assertEqual(members.get("vlan_ids"), [vlan_1_id, vlan_2_id, vlan_3_id])
        self.assertEqual(members.get("if_mode"), str(IFMode.TRUNK))

        # deleting portchannel vlan members
        member_delete_response = self.del_req("port_chnl_vlan_member_remove_all", req_json=request_body)
        self.assertEqual(member_delete_response.status_code, status.HTTP_200_OK)

        get_response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members, {})

        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_port_channel_vlan_members_in_series_with_hyphen(self):
        """
        Test case for adding vlan members in port channel in series with hyphen.
        eg . {trunk_vlans: [1, "3-5"], access_vlan: 4}
        """
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        port_channel = "PortChannel103"
        vlan_1_name = "Vlan3"
        vlan_1_id = 3
        vlan_2_name = "Vlan4"
        vlan_2_id = 4
        vlan_3_name = "Vlan5"
        vlan_3_id = 5

        req_payload = [
            {
                "mgt_ip": device_ip,
                "name": vlan_1_name,
                "vlanid": vlan_1_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_2_name,
                "vlanid": vlan_2_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan2",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_3_name,
                "vlanid": vlan_3_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan3",
            },
        ]

        response = self.put_req(
            "vlan_config",
            req_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing whether vlans are added or not
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_1_id)
        self.assertEqual(response.json()["name"], vlan_1_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_2_id)
        self.assertEqual(response.json()["name"], vlan_2_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_3_id)
        self.assertEqual(response.json()["name"], vlan_3_name)

        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "vlan_members": {
                "if_mode": str(IFMode.TRUNK),
                "vlan_ids": [f"{vlan_1_id}-{vlan_3_id}"]
            }
        }

        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl(request_body)
        response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("lag_name"), port_channel)
        self.assertEqual(response.json().get("mtu"), 9100)
        self.assertEqual(response.json().get("admin_sts"), "up")
        members = response.json().get("vlan_members")
        self.assertEqual(members.get("vlan_ids"), [vlan_1_id, vlan_2_id, vlan_3_id])
        self.assertEqual(members.get("if_mode"), str(IFMode.TRUNK))

        # deleting portchannel vlan members
        member_delete_response = self.del_req("port_chnl_vlan_member_remove_all", req_json=request_body)
        self.assertEqual(member_delete_response.status_code, status.HTTP_200_OK)

        get_response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members, {})

        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_port_channel_given_vlan_members(self):
        device_ip = list(self.device_ips.keys())[0]
        self.remove_mclag(device_ip)
        port_channel = "PortChannel103"
        vlan_1_name = "Vlan3"
        vlan_1_id = 3
        vlan_2_name = "Vlan4"
        vlan_2_id = 4
        vlan_3_name = "Vlan5"
        vlan_3_id = 5

        req_payload = [
            {
                "mgt_ip": device_ip,
                "name": vlan_1_name,
                "vlanid": vlan_1_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_2_name,
                "vlanid": vlan_2_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan2",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_3_name,
                "vlanid": vlan_3_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan3",
            },
        ]

        response = self.put_req(
            "vlan_config",
            req_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing whether vlans are added or not
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_1_id)
        self.assertEqual(response.json()["name"], vlan_1_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_2_id)
        self.assertEqual(response.json()["name"], vlan_2_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_3_id)
        self.assertEqual(response.json()["name"], vlan_3_name)

        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "vlan_members": {
                "if_mode": str(IFMode.ACCESS),
                "vlan_ids": [vlan_2_id]
            }
        }

        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl(request_body)
        response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("lag_name"), port_channel)
        self.assertEqual(response.json().get("mtu"), 9100)
        self.assertEqual(response.json().get("admin_sts"), "up")
        members = response.json().get("vlan_members")
        self.assertEqual(members.get("vlan_ids"), [vlan_2_id])
        self.assertEqual(members.get("if_mode"), str(IFMode.ACCESS))

        # deleting access-vlan from port channel
        member_delete_response = self.del_req(
            "port_channel_member_vlan", req_json={
                "mgt_ip": device_ip,
                "lag_name": port_channel,
                "vlan_members": {
                    "if_mode": str(IFMode.ACCESS),
                    "vlan_ids": [vlan_2_id]
                }
            }
        )
        self.assertEqual(member_delete_response.status_code, status.HTTP_200_OK)
        response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        members = response.json().get("vlan_members")
        self.assertEqual(members, {})

        # deleting trunk_vlans from port channel

        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "vlan_members": {
                "if_mode": str(IFMode.TRUNK),
                "vlan_ids": [vlan_2_id, vlan_3_id]
            }
        }

        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl(request_body)
        response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("lag_name"), port_channel)
        self.assertEqual(response.json().get("mtu"), 9100)
        self.assertEqual(response.json().get("admin_sts"), "up")
        members = response.json().get("vlan_members")
        self.assertEqual(members.get("vlan_ids"), [vlan_2_id, vlan_3_id])
        self.assertEqual(members.get("if_mode"), str(IFMode.TRUNK))

        member_delete_response = self.del_req(
            "port_channel_member_vlan", req_json={
                "mgt_ip": device_ip,
                "lag_name": port_channel,
                "vlan_members": {
                    "vlan_ids": [vlan_2_id, vlan_3_id],
                    "if_mode": str(IFMode.TRUNK)
                }
            }
        )
        self.assertEqual(member_delete_response.status_code, status.HTTP_200_OK)
        response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        members = response.json().get("vlan_members")
        self.assertEqual(members, {})

        # cleaning up
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_port_channel_vlan_member_switch_from_access_to_trunk(self):
        # Creating vlan for testing
        device_ip = list(self.device_ips.keys())[0]
        vlan_1_name = "Vlan4"
        vlan_1_id = 4
        vlan_2_name = "Vlan5"
        vlan_2_id = 5
        vlan_3_name = "Vlan6"
        vlan_3_id = 6
        port_channel = "PortChannel103"
        req_payload = [
            {
                "mgt_ip": device_ip,
                "name": vlan_1_name,
                "vlanid": vlan_1_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_2_name,
                "vlanid": vlan_2_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_3_name,
                "vlanid": vlan_3_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
        ]

        response = self.put_req(
            "vlan_config",
            req_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing whether vlans are added or not
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_1_id)
        self.assertEqual(response.json()["name"], vlan_1_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_2_id)
        self.assertEqual(response.json()["name"], vlan_2_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_3_id)
        self.assertEqual(response.json()["name"], vlan_3_name)

        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "vlan_members": {
                "if_mode": str(IFMode.ACCESS),
                "vlan_ids": [vlan_3_id]
            }
        }
        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])

        get_response = self.get_req("device_port_chnl", request_body, )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members.get("if_mode"), str(IFMode.ACCESS))
        self.assertEqual(members.get("vlan_ids"), [vlan_3_id])

        # Test updating from access to trunk
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "vlan_members": {
                "if_mode": str(IFMode.TRUNK),
                "vlan_ids": [vlan_1_id, vlan_3_id],
            }
        }
        member_update_response = self.put_req("device_port_chnl", req_json=request_body)
        self.assertEqual(member_update_response.status_code, status.HTTP_200_OK)
        get_response = self.get_req("device_port_chnl", request_body, )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members.get("if_mode"), str(IFMode.TRUNK))
        self.assertEqual(members.get("vlan_ids"), [vlan_1_id, vlan_3_id])

        # deleting portchannel vlan members
        member_delete_response = self.del_req("port_chnl_vlan_member_remove_all", req_json=request_body)
        self.assertEqual(member_delete_response.status_code, status.HTTP_200_OK)

        get_response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members, {})

        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_port_channel_vlan_member_switch_from_trunk_to_access(self):
        # Creating vlan for testing
        device_ip = list(self.device_ips.keys())[0]
        vlan_1_name = "Vlan4"
        vlan_1_id = 4
        vlan_2_name = "Vlan5"
        vlan_2_id = 5
        vlan_3_name = "Vlan6"
        vlan_3_id = 6
        port_channel = "PortChannel103"
        req_payload = [
            {
                "mgt_ip": device_ip,
                "name": vlan_1_name,
                "vlanid": vlan_1_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_2_name,
                "vlanid": vlan_2_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
            {
                "mgt_ip": device_ip,
                "name": vlan_3_name,
                "vlanid": vlan_3_id,
                "mtu": 9000,
                "enabled": False,
                "description": "Test_Vlan1",
            },
        ]

        response = self.put_req(
            "vlan_config",
            req_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing whether vlans are added or not
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_1_id)
        self.assertEqual(response.json()["name"], vlan_1_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_2_id)
        self.assertEqual(response.json()["name"], vlan_2_name)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["vlanid"], vlan_3_id)
        self.assertEqual(response.json()["name"], vlan_3_name)

        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "mtu": 9100,
            "admin_status": "up",
            "vlan_members": {
                "if_mode": str(IFMode.TRUNK),
                "vlan_ids": [vlan_1_id, vlan_2_id, vlan_3_id]
            }
        }
        # cleaning up port channel if it exists
        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})

        # adding port channel
        self.perform_add_port_chnl([request_body])

        get_response = self.get_req("device_port_chnl", request_body, )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members.get("if_mode"), str(IFMode.TRUNK))
        self.assertEqual(members.get("vlan_ids"), [vlan_1_id, vlan_2_id, vlan_3_id])

        # Test updating trunk vlan members to access
        request_body = {
            "mgt_ip": device_ip,
            "lag_name": port_channel,
            "vlan_members": {
                "if_mode": str(IFMode.ACCESS),
                "vlan_ids": [vlan_1_id],
            }
        }
        member_update_response = self.put_req("device_port_chnl", req_json=request_body)
        self.assertEqual(member_update_response.status_code, status.HTTP_200_OK)
        get_response = self.get_req("device_port_chnl", request_body, )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members.get("if_mode"), str(IFMode.ACCESS))
        self.assertEqual(members.get("vlan_ids"), [vlan_1_id])

        # deleting portchannel vlan members
        member_delete_response = self.del_req("port_chnl_vlan_member_remove_all", req_json=request_body)
        self.assertEqual(member_delete_response.status_code, status.HTTP_200_OK)

        get_response = self.get_req("device_port_chnl", request_body)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        members = get_response.json().get("vlan_members")
        self.assertEqual(members, {})

        self.perform_del_port_chnl({"mgt_ip": device_ip, "lag_name": port_channel})
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_2_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_1_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.del_req(
            "vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.get_req("vlan_config", {"mgt_ip": device_ip, "name": vlan_3_name})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
