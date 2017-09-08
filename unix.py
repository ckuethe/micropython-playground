from uos import stat, statvfs, listdir
from gc import mem_free, mem_alloc


def ls(x='/'):
    for fn in listdir(x):
        st = stat(fn)

        t = '?'
        if st[0] & 0x8000:
            t = 'f'
        elif st[1] & 0x4000:
            t = 'd'

        sz = st[6]
        print('{} {:6d}    {}{}'.format(t, sz, x, fn))


def df():
    st = statvfs('/')
    _size = int(st[1] * st[2] / 1024)
    _free = int(st[1] * st[3] / 1024)
    _used = st[3] / st[2] * 100
    print('Flash  {:d} / {:d}kB ({:.1f}%)'.format(_free, _size, _used))

    _free = mem_free()/1024
    _size = _free + mem_alloc() / 1024
    _used = 100 * _free / _size
    print('RAM    {:.1f} / {:.1f}kB ({:.1f}%)'.format(_free, _size, _used))
