from django.db import models
from .auth import ForceAPI
from django.core.files.base import ContentFile
from django.conf import settings
import os.path as path
import json
import psycopg2
from psycopg2 import extras


class Query(models.Model):
    name = models.CharField(
        max_length=80)
    soql = models.TextField(
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
        rslt = None
        if self.api is None:
            # handle archive query
            if self.conn is None:
                self.scarchive_conn()
            cur = self.conn.cursor()
            if qs is None:
                qs = self.soql
            cur.execute(qs)

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


class ReportQuery(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE)
    query = models.ForeignKey(
        Query,
        on_delete=models.CASCADE)

    def __str__(self):
        return "%s.%s" % (self.report, self.query)
