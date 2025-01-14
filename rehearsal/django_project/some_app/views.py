from django.shortcuts import render
from django.http import HttpResponse



def hello_http(request):
    if request.method == 'POST':
        new_message = request.POST.get('message', 'No message provided')
        return HttpResponse(f"New message: {new_message}")
    msg = "Hello world!"
    return HttpResponse(msg)


def hello_rendered(request):
    if request.method == 'POST':
        msg = request.POST.get('message', 'No message provided')
        return HttpResponse(f'<p id="messageDisplay">{msg}</p>')
    msg = "Hello world!"
    return render(request, 'some_app/hello.html', context={"msg": msg})