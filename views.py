from django.shortcuts import get_object_or_404, get_list_or_404
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.views import generic
from .models import Query, ForceAPI
from .forms import QueryForm


class IndexView(generic.ListView):
    template_name = 'queryforce/index.html'
    context_object_name = 'latest_query_list'

    def get_queryset(self):
        return Query.objects.order_by('-id')[:5]

class DetailView(generic.DetailView):
    model = Query
    template_name = 'queryforce/detail.html'


class ResultsView(generic.DetailView):
    model = Query
    template_name = 'queryforce/results.html'

def new_query(request):
    if request.method == "POST":
        form = QueryForm(request.POST)
        if form.is_valid():
            new_obj = form.save()
            return redirect('queryforce:detail', pk=new_obj.pk)
    else:
        form = QueryForm()
    return render(request, 'queryforce/query_edit.html', {'form': form})

def query_edit(request, pk):
    query = get_object_or_404(Query, pk=pk)
    if request.method == "POST":
        form = QueryForm(request.POST, instance=query)
        if form.is_valid():
            new_obj = form.save()
            return redirect('queryforce:detail', pk=new_obj.pk)
    else:
        form = QueryForm(instance=query)
    return render(request, 'queryforce/query_edit.html', {'form': form})

def define(request, query_id):
    query = get_object_or_404(Query, pk=query_id)
    try:
        selected_cred = query.api_set.get(pk=request.POST['cred'])
    except (KeyError, ForceAPI.DoesNotExist):
        cred = get_list_or_404(ForceAPI)
        return render(
            request,
            'queryforce/detail.html',
            {
                'query': query,
                'cred': cred,
                'error_message': "Selected Credential not valid"
            }
        )
    else:
        query.name = request.POST['q_name']
        query.soql = request.POST['soql']
        query.api = selected_cred
        query.save()
        return HttpResponseRedirect(reverse('queryforce:results', args=(query.id,)))
