from django.shortcuts import get_object_or_404, get_list_or_404
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.core import serializers
from django.urls import reverse
from django.views import generic
from django.forms import inlineformset_factory
from .models import Query, ForceAPI
from .models import Report
from .forms import ParameterForm
# from .forms import QueryForm, DisplayColumnForm


class IndexView(generic.ListView):
    template_name = 'queryforce/index.html'
    context_object_name = 'report_list'

    def get_queryset(self):
        return Report.objects.order_by('-id')[:5]

class DetailView(generic.DetailView):
    model = Report
    template_name = 'queryforce/detail.html'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        report = kwargs['object']
        # Use this code after testing
        # if report.params_required():
        #     form = ParameterForm()
        # else:
        #     form = None

        context['form'] = None
        return context

def raw_results(request, pk):
    report = get_object_or_404(Report, pk=pk)
    data = report.json_result()
    return HttpResponse(data, content_type='application/json')

# def new_query(request):
#     if request.method == "POST":
#         form = QueryForm(request.POST)
#         if form.is_valid():
#             new_obj = form.save()
#             return redirect('queryforce:detail', pk=new_obj.pk)
#     else:
#         form = QueryForm()
#     return render(request, 'queryforce/query_edit.html', {'form': form})

# def query_edit(request, pk):
#     query = get_object_or_404(Query, pk=pk)
#     DisplayColumnFormSet = inlineformset_factory(
#         Query,
#         DisplayColumn,
#         fields=('label', 'name', 'position',))
#     if request.method == "POST":
#         formset = DisplayColumnFormSet(
#             request.POST,
#             request.FILES,
#             instance=query)
#         form = QueryForm(request.POST, instance=query)
#         if form.is_valid():
#             new_obj = form.save()
#             return redirect('queryforce:detail', pk=new_obj.pk)
#     else:
#         form = QueryForm(instance=query)
#         subforms = []
#         for dc in query.displaycolumn_set.objects.all():
#             subforms.append(DisplayColumnForm(instance=dc)
#     return render(request, 'queryforce/query_edit.html', {'form': form})

# def define(request, query_id):
#     query = get_object_or_404(Query, pk=query_id)
#     try:
#         selected_cred = query.api_set.get(pk=request.POST['cred'])
#     except (KeyError, ForceAPI.DoesNotExist):
#         cred = get_list_or_404(ForceAPI)
#         return render(
#             request,
#             'queryforce/detail.html',
#             {
#                 'query': query,
#                 'cred': cred,
#                 'error_message': "Selected Credential not valid"
#             }
#         )
#     else:
#         query.name = request.POST['q_name']
#         query.soql = request.POST['soql']
#         query.api = selected_cred
#         query.save()
#         return HttpResponseRedirect(reverse('queryforce:results', args=(query.id,)))
