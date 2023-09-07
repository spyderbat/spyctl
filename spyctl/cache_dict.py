#
# cache_dict.py
#
# >>> import cache_dict
# >>> c = cache_dict.CacheDict(cache_len=2)
# >>> c[1] = 1
# >>> c[2] = 2
# >>> c[3] = 3
# >>> c
# CacheDict([(2, 2), (3, 3)])
# >>> c[2]
# 2
# >>> c[4] = 4
# >>> c
# CacheDict([(2, 2), (4, 4)])
# >>>
#

from collections import OrderedDict

# From https://gist.github.com/davesteele/44793cd0348f59f8fadd49d7799bd306


# -------------------------------------------------------------
class CacheDict(OrderedDict):
    """Dict with a limited length, ejecting LRUs as needed."""

    def __init__(self, *args, cache_len=None, on_del=None, **kwargs):
        self.cache_len = cache_len
        self.on_del = on_del
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().move_to_end(key)

        if self.cache_len is not None:
            while len(self) > self.cache_len:
                oldkey = next(iter(self))
                if self.on_del:
                    oldvalue = super().__getitem__(oldkey)
                    super().__delitem__(oldkey)
                    self.on_del(oldkey, oldvalue)
                else:
                    super().__delitem__(oldkey)

    def peek(self, key):
        return super().get(key)

    def get(self, key):
        if key in self:
            super().move_to_end(key)
        return super().get(key)

    def __getitem__(self, key):
        val = super().__getitem__(key)
        try:
            super().move_to_end(key)
        except KeyError:
            pass
        return val

    def contract(self, delta):
        self.cache_len -= delta
        self.cache_len = max(self.cache_len, 100)

    def expand(self, delta):
        self.cache_len += delta

    def flush(self):
        if self.on_del:
            for key, value in self.items():
                self.on_del(key, value)
