#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
from prometheus_client import start_http_server, Gauge
from prometheus_client.core import REGISTRY
from pyzabbix import ZabbixAPI


class ZabbixCollector(object):
    def __init__(self, url, username, password):
        zapi = ZabbixAPI(url)
        zapi.login(username, password)

        # Create metric objs
        self.trigger_state = Gauge('zabbix_trigger_state', 'Zabbix Trigger value (ok=0, problem=1)')

    def collect(self):
        # Get a list of all triggers
        triggers = zapi.trigger.get(
                                    monitored=1,
                                    active=1,
                                    output='extend',
                                    expandDescription=1,
                                    selectHosts=['host'],
                                    )

        for t in triggers:
            t['value']
            for host in t['hosts']:
                self.trigger_state.set(t['value'], labels={
                    'host': host['host'],
                    'trigger': t['description'],
                    'triggerid': t['triggerid'],
                    'templateid': t['templateid'],
                    })

        yield self.trigger_state


def main():
    # Config as environment variables
    url = os.environ.get('ZABBIX_EXP_URL', 'http://localhost/')
    username = os.environ.get('ZABBIX_EXP_USERNAME', 'Admin')
    password = os.environ.get('ZABBIX_EXP_PASSWORD', 'zabbix')

    collector = ZabbixCollector(url, username, password)

    try:
        # Start the webserver on the required port
        start_http_server(9288)
        REGISTRY.register(collector)
    except KeyboardInterrupt:
        print("Keyboard Interrupted")
        exit(0)


if __name__ == "__main__":
    main()
