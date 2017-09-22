# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 syn=python

import uos
import gc
import machine


def ls(x='/'):
    """List a directory"""
    for fn in uos.listdir(x):
        st = uos.stat(fn)

        t = '?'
        if st[0] & 0x8000:
            t = 'f'
        elif st[1] & 0x4000:
            t = 'd'

        sz = st[6]
        print('{} {:6d}    {}{}'.format(t, sz, x, fn))


def df():
    """Get free disk and memory"""
    st = uos.statvfs('/')
    _size = int(st[1] * st[2] / 1024)
    _free = int(st[1] * st[3] / 1024)
    _used = st[3] / st[2] * 100
    print('Flash  {:d} / {:d}kB ({:.1f}%)'.format(_free, _size, _used))

    gc.collect()
    _free = gc.mem_free()/1024
    _size = _free + gc.mem_alloc() / 1024
    _used = 100 * _free / _size
    print('RAM    {:.1f} / {:.1f}kB ({:.1f}%)'.format(_free, _size, _used))


def cat(f=None):
    """Print file contents to terminal"""
    with open(f, 'rU') as fd:
        print(fd.read())


def mki2c(scl=5, sda=4):
    """Create an i2c object for quick sensor hacking"""
    _bus = machine.I2C(scl=machine.Pin(scl), sda=machine.Pin(sda))
    print("Detected devices:", _bus.scan())
    return _bus
