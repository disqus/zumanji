from django.shortcuts import render


class Interface(object):
    template = None

    def __init__(self, data):
        self.data = data

    def render(self):
        if self.template is None:
            raise NotImplementedError

        return render(self.template, {
            'data': self.data,
        })
