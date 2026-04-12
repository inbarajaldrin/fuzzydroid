# fusion_bridge — TCP bridge add-in for Autodesk Fusion 360
#
# This file follows the Autodesk Fusion 360 Add-In Sample scaffolding pattern
# (run/stop entry points, commands module, lib/fusionAddInUtils).
# Original scaffolding: Copyright 2022 Autodesk, Inc. — Autodesk Sample License
# TCP server logic and modifications: fuzzydroid contributors — Apache-2.0
# See NOTICES.md at the repository root.

from . import commands
from .lib import fusionAddInUtils as futil


def run(context):
    try:
        commands.start()
    except:
        futil.handle_error('run')


def stop(context):
    try:
        futil.clear_handlers()
        commands.stop()
    except:
        futil.handle_error('stop')
