__all__ = ('take',)

from functools import partial

class mock_self:
    def __init__(self):
        self.names = []
        self.call_attrs = None

    def __getattr__(self, name):
        _ = self.__class__()
        _.names = self.names + [name]
        return _

    def __call__(self, *args, **kwargs):
        self.call_attrs = (args, kwargs)
        return self

class Handler:

    def __init__(self, args, kwargs, taken, exec = True):
        self.args = args
        self.kwargs = kwargs
        self.taken = taken
        self.exec = exec

    def handle(self):
        if self.exec:
            for arg in self.args:
                self.handle_arg(arg)()

            for v in self.kwargs.values():
                self.handle_arg(v)
        else:
            args, kwargs = [], {}
            for arg in self.args:
                args.append(self.handle_arg(arg))

            for k, v in self.kwargs.items():
                kwargs[k] = self.handle_arg(v)

            return args, kwargs

    def handle_arg(self, _, outer=True):
        inst = partial(isinstance, _)
        
        if inst(tuple):
            return self.handle_arg(partial(*_), True)
        elif inst(partial):
            f = _.func
            args = _.args
            kwargs = _.keywords
            args = tuple(self.handle_arg(a, False) for a in args)
            kwargs = {k: self.handle_arg(v, False) for k, v in kwargs.items()}

            if args == _.args and kwargs == _.keywords:
                return partial(f, self.taken, *args, **kwargs)
            else:
                return partial(f, *args, **kwargs)
        elif inst(mock_self):
            dispatched = self.taken
            for attrname in _.names:
                dispatched = getattr(dispatched, attrname)

            if _.call_attrs is not None:
                args, kwargs = _.call_attrs

                args = tuple(self.handle_arg(a, False) for a in args)

                kwargs = {k: self.handle_arg(v, False) for k, v in kwargs.items()}

                if outer and self.exec:
                    return partial(dispatched, *args, **kwargs)
                elif outer and not self.exec:
                    return dispatched(*args, **kwargs)
                else:
                    return dispatched(*args, **kwargs)
            return dispatched

        else:
            if self.exec:
                if outer:
                    return partial(_, self.taken)
                else:
                    return _
            else:
                return _
            

class take:
    __slots__ = ('obj',)

    class mockmeth:
        def __init__(self, name, taken):
            self.name = name
            self.bounded = getattr(taken.obj, name)
            self.taken = taken

        def __call__(self, *args, **kwargs):
            args, kwargs = Handler(args, kwargs, self.taken.obj, False).handle()
            self.bounded(*args, **kwargs)
            return self.taken

    self = mock_self()

    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, name):
        return self.mockmeth(name, self)

    def __call__(self, *args, **names_values):
        obj = self.obj

        Handler(args, {}, obj).handle()

        for k, v in names_values.items():
            setattr(obj, k, v)

        return self

    def unwrap(self):
        return self.obj