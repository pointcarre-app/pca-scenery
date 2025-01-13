from django.shortcuts import render
from django.http import HttpResponse


# def hello_http(request):
#     msg = "Hello, World!"
#     return HttpResponse(msg)

# def hello_rendered(request):
#     msg = "Hello, World!"
#     return render(request, 'some_app/hello.html', context={"msg": msg})

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def hello_http(request):
    if request.method == 'POST':
        # Get the new message from POST data, fallback to default if empty
        new_message = request.POST.get('message', 'No message provided')
        return HttpResponse(f"New message: {new_message}")
    # Default GET response
    msg = "Hello world!"
    return HttpResponse(msg)

@csrf_exempt
def hello_rendered(request):
    if request.method == 'POST':
        msg = request.POST.get('message', 'No message provided')
        # Return just the message container for HTMX to swap
        return HttpResponse(f'<p id="messageDisplay">{msg}</p>')
    msg = "Hello world!"
    return render(request, 'some_app/hello.html', context={"msg": msg})