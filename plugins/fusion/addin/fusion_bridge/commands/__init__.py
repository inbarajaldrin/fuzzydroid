# Derived from Autodesk Fusion 360 Add-In Sample commands/ scaffolding pattern
# Copyright 2022 Autodesk, Inc. — Autodesk Sample License
# Modifications: fuzzydroid contributors — Apache-2.0

from .tcpServer import entry as tcpServer

commands = [
    tcpServer,
]


def start():
    for command in commands:
        command.start()


def stop():
    for command in commands:
        command.stop()
