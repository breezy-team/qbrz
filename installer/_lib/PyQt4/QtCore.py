def __load():
    import os, imp
    path = os.path.join(os.path.dirname(__file__), '..', '..', '_ext', 'QtCore.pyd')
    imp.load_dynamic(__name__, path)
__load()
del __load
