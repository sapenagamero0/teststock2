from django.shortcuts import render_to_response, get_object_or_404, render
from market2.models import StockStatus2, Stock2, Order2, Position2, Portfolio2
from django.contrib.auth.models import User
from django.contrib import auth
from django.http import HttpResponseRedirect, HttpResponse, Http404
from market2.updater import update
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.template import loader, RequestContext

def index(request):
    if request.user.is_authenticated():
        portfolio2 = get_object_or_404(Portfolio2, user=request.user)
        hist = list(reversed(list(portfolio2.history.all())))[:5]
        return render_to_response('portfolio.html', 
            {'portfolio': portfolio2, 'hist': hist})
    else:
        return render_to_response('index Copy.html')

def registerPage(request):
        return render_to_response('SignUp.html')    

def loginPage(request):
        return render_to_response('LogIn.html')    


@csrf_exempt
def register(request):
    uname = request.POST["username"]
    passw = request.POST["password"]
    
    c = {'error': 'You did not fill out the form completely'}
    c.update(csrf(request))

    if request.POST["username"] == "" or request.POST["password"] == "":
        return render_to_response('SignUp.html',
            {'error': 'You did not fill out the form completely'}, context_instance=RequestContext(request))
    
    if User.objects.filter(username = request.POST["username"]).count() != 0:
        return render_to_response('SignUp.html',
           {'error':  'There is already a user with this username'}, context_instance=RequestContext(request)
           )
    
    User.objects.create_user(uname, '', passw)
    u = auth.authenticate(username=uname, password=passw)
    auth.login(request, u)
    
    p = Portfolio2(user = u, balance = 10000, value = 0)
    
    p.save()
    
    return HttpResponseRedirect('/')

@csrf_exempt
def login(request):
    # Will have username/password in request.POST
    uname = request.POST["username"]
    passw = request.POST["password"]
    # Authenticate User
    user = auth.authenticate(username = uname, password = passw)
    # If good, redirect to /
    if user is not None and user.is_active:
        auth.login(request, user)
        return HttpResponseRedirect('/')
    else:
        return render_to_response('index.html',
            {'error': 'There was an error with your login'})
    
def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/')

def help(request):
    return render_to_response('help.html')

@csrf_exempt
def search(request, query):
    if query is None:
        query = request.POST['q']
    query = query.upper()
    return HttpResponseRedirect('/stock/%s/' % query)

@csrf_exempt
def show_stock(request, symbol):
    stks = Stock2.objects.filter(symbol=symbol)
    if stks.count() == 0:
        stk = Stock2(symbol=symbol, price=0.0)
        stk.save()
    elif stks.count() == 1:
        stk = stks[0]
    else:
        return HttpResponse("%s" % stks.count())
    try:
        ss = stk.history.order_by('date')[0]
    except:
        update(stk)
        ss = stk.history.order_by('date')[0]
    return render_to_response('stock.html', {'stock': stk, 'status': ss})

@csrf_exempt
def handle_buy(request):
    
    if request.user.is_authenticated(): 
        p = Portfolio2.objects.get(user=request.user)
    else:
        return render_error(request, 'You don\'t seem to be logged in')
      
    symbol = request.POST["symbol"] 
    stk = Stock2.objects.get(symbol=symbol)
    
    try:
        share = int(request.POST['number_of_shares'])
    except:
        return render_error(request, 'Try entering a real number')
    
    if p.balance < share * stk.price:
        return render_error(request, "Insufficient funds deadbeat")
    
    o = Order2(type='buy', amount=share, stock=stk)
    o.save()
    
    p.history.add(o)
    p.save()
    
    pos = p.positions.filter(stock=stk)
    
    if pos.count() == 1:
        pos = pos[0]
        pos.amount = pos.amount + share
        pos.value = pos.amount * stk.price
        pos.save()
    
    else:
        pos = Position2(amount=share, stock=stk, value=share * stk.price)
        pos.save()
        p.positions.add(pos)
        p.save()
    
    p.value += share * stk.price
    p.balance -= share * stk.price
    p.save()
    
    return HttpResponseRedirect('/')

@csrf_exempt
def handle_sell(request):
    
    if request.user.is_authenticated(): #check if user is authenticate
        p = Portfolio2.objects.get(user=request.user)
    else:
        return render_error(request, 'You don\'t seem to be logged in')
    # Then find the stock symbol in request.POST    
    symbol = request.POST["symbol"] 
    stk = Stock2.objects.get(symbol=symbol)
    # And the number of shares in request.POST
    try:
        share = int(request.POST['number_of_shares'])
    except:
        return render_error(request, 'Try entering a real number')
    
    pos = p.positions.filter(stock=stk)
    if pos.count() == 0:
        return render_error(request, 'You don\'t own any of that stock')
    else:
        pos = pos[0]
        if pos.amount < share:
            return render_error(request, 'You don\'t own enough of that stock')
        pos.amount = pos.amount - share
        pos.save()
        pos.value = pos.amount * stk.price
        pos.save()
    p.value -= share * stk.price
    p.balance += share * stk.price
    p.save()
    
    o = Order(type='sell', amount=share, stock=stk)
    o.save()
    p.history.add(o)
    p.save()
    
    return HttpResponseRedirect('/')

@csrf_exempt
def show_leaders(request):
    plist = list(reversed(list(Portfolio2.objects.order_by('value'))))
    return render_to_response('leaderboard.html', {'portfolios': plist})
