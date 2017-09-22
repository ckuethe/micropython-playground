# This file is executed on every boot (including wake-boot from deepsleep)
import esp
esp.osdebug(None)

import webrepl
webrepl.start()

from unix import *

import netcfg
netcfg.autoconfig()

import gc
gc.collect()
