from django.db import models
from .auth import ForceAPI
from django.core.files.base import ContentFile
from django.conf import settings
import os.path as path
import json
import psycopg2
from psycopg2 import extras
from decimal import Decimal


def data_type_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return int(obj)
    else:
        return obj


# class Source(models.Model):
#     name = models.CharField(
#         max_length=80)

#     def __str__(self):
#         return self.name()


# class Api_Source(Source):
#     api = models.ForeignKey(
#         ForceAPI,
#         on_delete=models.CASCADE)


# class Postgre_Source(Source):
#     dbname = models.CharField(
#         max_length=60)
#     host = models.CharField(
#         max_length=255)
#     user_id = models.CharField(
#         max_length=60)
#     password = models.CharField(
#         max_length=60)
#     conn = None

#     def make_dsn(self):
#         rtn = []
#         rtn.append("dbname='%s' " % self.dbname)
#         rtn.append("user='%s' " % self.user_id)
#         rtn.append("host='%s' " % self.host)
#         rtn.append("password='%s'" % self.password)
#         return " ".join(rtn)

#     def connect(self):
#         dsn = self.make_dsn()
#         self.conn = psycopg2.connect(
#             dsn,
#             cursor_factory=psycopg2.extras.RealDictCursor)
#         return


class Query(models.Model):
    name = models.CharField(
        max_length=80)
    soql = models.TextField(
        null=True,
        blank=True)
    table = models.CharField(
        max_length=80,
        null=True,
        blank=True)
    api = models.ForeignKey(
        ForceAPI,
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    conn = None

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Query, self).save(*args, **kwargs)
        self.auto_cols()

    def scarchive_conn(self):
        dbname = "hc_ms_scarchival"
        host = "VDCALP03640.ics.cloud.ge.com"
        user = "Global_Report"
        connection = psycopg2.connect(
            "dbname='%s' user='%s' host='%s' password='%s'" %
            (dbname, user, host, user),
            cursor_factory=psycopg2.extras.RealDictCursor)
        self.conn = connection

    def auto_cols(self):
        acq = self.soql.split('limit')
        if len(acq) > 1:
            acq.pop()
        acq = 'limit'.join(acq).strip() + ' limit 20'
        rslt = self.make_result(acq)
        if not rslt:
            return False
        elif 'errorCode' in rslt[0].keys():
            return rslt[0]
        for colname in rslt[0].keys():
            skipit = self.displaycolumn_set.filter(name=colname).exists()
            skipit = skipit or (type(rslt[0][colname]) is dict)
            if not skipit:
                col = DisplayColumn(
                    query=self,
                    label=colname,
                    name=colname,
                    position=self.next_pos())
                col.save()
        return self.next_pos() - 1

    def next_pos(self):
        rtn = self.displaycolumn_set.count()
        return rtn + 1

    def apiqs(self, qs=None):
        if qs is None:
            qs = self.soql
        txt = '+'.join(qs.split(' '))
        return 'query?q=' + txt

    def make_result(self, qs=None):        
        if "?" in self.soql:
            if qs is None:
                return None
        rslt = None
        if self.api is None:
            # handle archive query
            if self.conn is None:
                self.scarchive_conn()
            cur = self.conn.cursor()
            if qs is None:
                qs = self.soql
            cur.execute(qs)
            recs = cur.fetchall()
            jrecs = json.dumps(recs, default=data_type_handler)
            rslt = json.loads(jrecs)
        else:
            # handle api call
            qs = self.apiqs(qs)
            req = self.api.get_data(qs)
            if type(req) is dict:
                if 'records' in req.keys():
                    rslt = req['records']
                    if not(req['done']):
                        nqs = req['nextRecordsUrl'][21:]
                        rslt.append(self.sf_recs(nqs))
            else:
                rslt = req
        return rslt

    def json_result(self):
        jr = {'data': self.make_result()}
        return json.dumps(jr)

    def display_rules(self):
        rtn = []
        for col in self.displaycolumn_set.all().order_by('position'):
            rule = {
                'data': col.name,
                'name': col.label
            }
            rtn.append(rule)
        return rtn

    def has_params(self):
        return self.parameter_set.count() > 0


class DisplayColumn(models.Model):
    query = models.ForeignKey(
        Query,
        on_delete=models.CASCADE)
    label = models.CharField(
        max_length=25)
    name = models.CharField(
        max_length=80)
    position = models.IntegerField()

    def __str__(self):
        return self.label


class ParameterGroup(models.Model):
    OPERATION_CHOICES = (
        ('AND', 'All'),
        ('OR', 'Any'),
    )
    query = models.ForeignKey(
        Query,
        on_delete=models.CASCADE)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        related_name='nested_pg')
    operation = models.CharField(
        max_length=3,
        choices=OPERATION_CHOICES,
        default='AND')

    def group_level(self):
        level = 0
        if self.parent is not None:
            level = self.parent.group_level() + 1
        return level

    def __str__(self):
        level_description = ''
        level = self.group_level() + 1
        if level > 3:
            level_description = "%sth level" % level
        elif level == 3:
            level_description = "3rd level"
        elif level == 2:
            level_description = "2nd level"
        elif level == 1:
            level_description = "Main"
        param_names = [str(x) for x in self.parameter_set.all()]
        param_names = "(" + ",".join(param_names) + ")"
        rtn = [
            self.query.name,
            level_description,
            "Parameters",
            param_names]
        return " ".join(rtn)


class Parameter(models.Model):
    query = models.ForeignKey(
        Query,
        on_delete=models.CASCADE)
    parametergroup = models.ForeignKey(
        ParameterGroup,
        on_delete=models.CASCADE,
        null=True)
    field_name = models.CharField(
        max_length=80)
    label = models.CharField(
        max_length=80,
        null=True,
        blank=True)
    apply_quotes = models.BooleanField(
        default=False)

    def __str__(self):
        if self.label is None:
            return self.field_name
        else:
            return self.label

    def set_parameter(self, operator, value):
        rtn = [self.field_name, operator]
        if operator in ['IN', 'NOT IN']:
            if self.apply_quotes:
                value = value.split(",")
                value = "'%s'" % "','".join(value)
            rtn.append("(%s)" % value)
        else:
            rtn.append(value)
        return " ".join(rtn)


class Report(models.Model):
    name = models.CharField(
        max_length=80)

    def __str__(self):
        return self.name

    def result_union(self):
        rslt = []
        for rq in self.reportquery_set.all():
            rqrslt = rq.query.make_result()
            rslt.extend(rqrslt)
        return rslt

    def json_result(self):
        jr = {'data': self.result_union()}
        return json.dumps(jr)

    def display_rules(self):
        fq = self.reportquery_set.all()[0]
        return fq.query.display_rules()

    def parameter_count(self):
        pcount = 0
        for rq in self.reportquery_set.all():
            pcount += rq.params_count()
        return pcount

    def params_required(self):
        return self.parameter_count > 0


class ReportQuery(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE)
    query = models.ForeignKey(
        Query,
        on_delete=models.CASCADE)

    def __str__(self):
        return "%s.%s" % (self.report, self.query)

    def params_count(self):
        return self.query.parameter_set.count()
