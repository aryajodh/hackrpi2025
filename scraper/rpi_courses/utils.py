import collections

# CRITICAL CHANGE 1: logger import is assumed to be correct in Py3
from .config import logger


def safeInt(n, warn_only=False):
    """Throws an exception if the number starts with a 0 (may be significant).

    If the value cannot be converted to an int, it is returned as is.
    """
    # Python 3 string methods are compatible
    if str(n).startswith('0'):
        if not warn_only:
            # Python 3 exception raising is identical
            raise TypeError("Unsafe Int: " + str(n))
        
        # CRITICAL CHANGE 2: Python 2 'print' statement -> Python 3 'print()' function
        print("Unsafe Int: %s" % n)
        
        # int(n) works identically
        return int(n)
    try:
        # int(n) works identically
        return int(n)
    except ValueError:
        return n


# from SO: http://stackoverflow.com/questions/2703599/what-would-be-a-frozen-dict
# CRITICAL CHANGE 3: collections.Mapping is deprecated in Py3 and replaced by collections.abc.Mapping
class FrozenDict(collections.abc.Mapping): 
    """Defines an immutable dict type."""

    FROZEN_TYPES = {
        set: frozenset,
        list: tuple,
    }

    def __init__(self, *args, **kwargs):
        # Python 3 super() is typically used for safer inheritance
        # super(FrozenDict, self).__init__() # Not strictly necessary here as Mapping has no state to init
        
        self._hash = None
        self._d = {}
        # CRITICAL CHANGE 4: Python 2 'dict.items()' -> Python 3 'dict.items()' (This is fine)
        for key, vals in dict(*args, **kwargs).items():
            self._d[self._freeze(key)] = self._freeze(vals)

    def _freeze(self, value):
        # Python 3 dict methods and type checking are fine
        return self.FROZEN_TYPES.get(type(value), lambda x: x)(value)

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __setitem__(self, key, value):
        raise TypeError("FrozenDict is immutable.")

    def __repr__(self):
        # Python 3 repr is fine
        return "FrozenDict(%r)" % self._d

    def __hash__(self):
        if self._hash is None:
            self._hash = 0
            # CRITICAL CHANGE 5: Python 2 'dict.iteritems()' -> Python 3 'dict.items()'
            for key, value in self._d.items(): 
                self._hash ^= hash(key)
                self._hash ^= hash(value)
        return self._hash

# CRITICAL CHANGE 6: collections.Mapping is now collections.abc.Mapping
# The import collections line at the top should be changed to: import collections.abc
# However, for brevity, we assume the import remains 'collections' and use the fully qualified name.
if hasattr(collections, 'abc'):
    FrozenDict.FROZEN_TYPES[dict] = FrozenDict
else:
    # If using Py2/older Py3, keep original structure
    FrozenDict.FROZEN_TYPES[dict] = FrozenDict