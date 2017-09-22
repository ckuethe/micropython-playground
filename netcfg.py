# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 syn=python

import sys
import network
import time


# "conf" is a dict which must have "client" and "ap" keys.
#
# "ap" is dict which must have 'ssid', 'psk', 'ip', 'nm', 'gw', and 'ns'
# keys. If unspecified, the default ('MicroPython-%06x') AP will be used.
#
# "client" is dict whose keys are the SSIDs of the networks to try, and the
# values are dicts of network settings. 'psk' is required. If 'ip' is None
# or absent, DHCP will be used to obtain an address. If 'ip' is given, then
# 'gw', 'nm', and 'ns' are also required.
#
# conf = {
#    "client": {
#        "example1": {"psk": "password1234"},
#        "example2": {
#            "psk": "5678password",
#            "ip":"172.31.1.75",
#            "nm":"255.255.255.0",
#            "gw":"172.31.1.1",
#            "ns":"8.8.8.8"
#        }
#    },
#
#    "ap": {
#       "ssid": "example_ssid",
#       "psk": "example_key",
#       "ip": "192.168.5.1",
#       "nm": "255.255.255.0",
#	    "gw":"192.168.5.1",
#	    "ns":"8.8.8.8"
#    }
# }

def write_default_netcfg():
    default_config = '''# Edit this file to match your network settings
conf = {
    "client": { },
    "ap": { }
}
    '''

    with open('./netcfg_settings.py', 'w') as fd:
        fd.write(default_config)

def autoconfig():
    # Wireless autoconfiguration. Attempts to connect to known networks; if
    # that fails a default AP is created (MicroPython-%06x / micropythoN)
    try:
        from netcfg_settings import conf
    except ImportError:
        write_default_netcfg()
        from netcfg_settings import conf

    # Turn up a station interface
    client = network.WLAN(network.STA_IF)
    client.active(True)

    # disable the AP if that was the last configuration
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)

    # this takes few seconds to complete, giving the firmware time to connect
    print("Scanning for networks")
    scan_result = set(map(lambda x: x[0].decode('utf-8'), client.scan()))

    if client.isconnected():
        # network configuration is persistent across soft reboot
        print("Cached network: {}".format(client.ifconfig()))
        return

    known_nets = set(conf['client'].keys())
    for ssid in known_nets.intersection(scan_result):
        print("Attempting to connect to {}".format(ssid))
        client.connect(ssid, conf['client'][ssid]['psk'])
        if conf['client'][ssid].get('ip', None):
            client.ifconfig((conf['client'][ssid]['ip'],
                             conf['client'][ssid]['nm'],
                             conf['client'][ssid]['gw'],
                             conf['client'][ssid]['ns'] ))
        for _ in range(5):
            time.sleep(2)
            if client.isconnected():
                print("Connected to {}: {}".format(ssid, client.ifconfig()))
                return

    print("Unable to find a known network, switching to AP mode")
    client.active(False)
    ap_if.active(True)

    if conf.get('ap', None) and conf['ap'].get('ssid', None):
        ap_if.config(essid=conf['ap']['ssid'],
                     password=conf['ap']['psk'],
                     authmode=network.AUTH_WPA_WPA2_PSK)
        ap_if.ifconfig((conf['ap']['ip'],
                        conf['ap']['nm'],
                        conf['ap']['gw'],
                        conf['ap']['ns']))
    else:
        from inisetup import wifi
        wifi()
