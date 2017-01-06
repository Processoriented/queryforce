from django.db import models
from .auth import ForceAPI
from django.conf import settings
import json
import psycopg2
from psycopg2 import extras
from decimal import Decimal
from .parser import QF_Statement


def data_type_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return int(obj)
    else:
        return obj


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
    parse_on_save = models.BooleanField(
        default=True)
    conn = None

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Query, self).save(*args, **kwargs)
        if self.parse_on_save:
            self.auto_cols()
        else:
            self.parse_on_save = True

    def scarchive_conn(self):
        dbname = "hc_ms_scarchival"
        host = "VDCALP03640.ics.cloud.ge.com"
        user = "Global_Report"
        connection = psycopg2.connect(
            "dbname='%s' user='%s' host='%s' password='%s'" %
            (dbname, user, host, user),
            cursor_factory=psycopg2.extras.RealDictCursor)
        self.conn = connection

    def parsed_stmt(self, sql=None):
        sql = sql if sql is not None else self.soql
        return QF_Statement(sql)

    def auto_params(self, pcs=None):
        if pcs is None:
            stmt = QF_Statement(self.soql)
            pcs = stmt.ph_comps()
        for comp in pcs:
            pname = comp.comp_name
            skipit = self.parameter_set.filter(
                field_name=pname,query=self).exists()
            if not skipit:
                param = Parameter(
                    query=self,
                    field_name=pname,
                    token_text=str(comp))
                param.save()

    def auto_cols(self):
        stmt = QF_Statement(self.soql)
        pcs = stmt.ph_comps()
        if len(pcs) > 0:
            self.auto_params(pcs)
            stmt = QF_Statement(stmt.sql_sans_placeholders())
        acq = stmt.apply_limit(20)
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
        if qs[:6] == 'query/':
            return qs
        txt = '+'.join(qs.split(' '))
        return 'query?q=' + txt

    def apply_params(self, sql=None, params={}):
        sql = sql or self.soql
        for key in params.keys():
            param = params[key]
            param_qs = self.parameter_set.filter(label=key)
            if param_qs.count() != 0:
                use_quotes = param_qs[0].apply_quotes
                val_str = param['value']
                if param['operator'] in ['IN', 'NOT IN']:
                    val_str = "(%s)" % val_str
                elif use_quotes:
                    val_str = "'%s'" % val_str
                param_str = "%s%s%s" % (
                    param_qs[0].field_name,
                    param['operator'],
                    val_str)
                nsql = sql.replace(param_qs[0].token_text, param_str)
                sql = nsql
            else:
                fns = [x.field_name for x in self.parameter_set.all()]
                print("can't find %s among %s." % (
                    key,
                    ", ".join(fns)))
        return sql

    def make_result(self, qs=None, params={}):
        qs = qs or self.soql
        qs = self.apply_params(qs, params)
        rslt = None
        if self.api is None:
            # handle archive query
            if self.conn is None:
                self.scarchive_conn()
            cur = self.conn.cursor()
            cur.execute(qs)
            recs = cur.fetchall()
            jrecs = json.dumps(recs, default=data_type_handler)
            rslt = json.loads(jrecs)
        else:
            # handle api call
            qs = self.apiqs(qs)
            print(qs)
            req = self.api.get_data(qs)
            if type(req) is dict:
                if 'records' in req.keys():
                    rslt = req['records']
                    if not(req['done']):
                        nqs = req['nextRecordsUrl'][21:]
                        rslt.append(self.make_result(nqs))
            else:
                rslt = req
                rslt.append({'qs': qs})
                rslt.append({'oq': self.soql})
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


class Parameter(models.Model):
    query = models.ForeignKey(
        Query,
        on_delete=models.CASCADE)
    field_name = models.CharField(
        max_length=80)
    label = models.CharField(
        max_length=80,
        null=True,
        blank=True)
    apply_quotes = models.BooleanField(
        default=False)
    token_text = models.CharField(
        max_length=80,
        null=True,
        blank=True)

    def __str__(self):
        if self.label is None:
            return self.field_name
        else:
            return self.label

    def make_token_text(self):
        return self.token_text or ("%s=?" % self.field_name)

    def token_in_sql(self):
        tt = self.make_token_text()
        rtn = tt in self.query.soql
        if rtn and tt != self.token_text:
            self.token_text = tt
        return rtn

    def append_param(self):
        if not self.token_in_sql():
            tt = self.make_token_text()
            stmt = QF_Statement(self.query.soql)
            nsql = str(stmt.append_comp(tt))
            self.query.soql = nsql
            self.query.parse_on_save = False
            self.query.save()

    def save(self, *args, **kwargs):
        tt = self.make_token_text()
        if self.token_text != tt:
            self.token_text = tt
        super(Parameter, self).save(*args, **kwargs)
        self.append_param()

    def delete(self, *args, **kwargs):
        tt = self.make_token_text()
        stmt = QF_Statement(self.query.soql)
        self.query.soql = stmt.remove_ph_comp(tt)
        self.query.parse_on_save = False
        self.query.save()
        super(Parameter, self).delete(keep_parents=True)


class Report(models.Model):
    name = models.CharField(
        max_length=80)

    def __str__(self):
        return self.name

    def result_union(self, params=None):
        rslt = []
        for rq in self.reportquery_set.all():
            rqrslt = rq.query.make_result(rq.query.soql, params)
            rslt.extend(rqrslt)
        return rslt

    def json_result(self, params=None):
        jr = {'data': self.result_union(params)}
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
        return self.parameter_count() > 0

    def report_params(self):
        params = []
        for rq in self.reportquery_set.all():
            if rq.params_count() > 0:
                params.extend(rq.rq_params())
        return params


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

    def rq_params(self):
        return self.query.parameter_set.all()


class SavedReportParams(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE)
    name = models.CharField(
        max_length=80)
    user_visible = models.BooleanField(
        default=False)

    def __str__(self):
        return self.name

    def make_queries(self):
        sps = self.savedreportparam_set.all()
        sqls = []
        queries = [
            rq.query for rq in self.report.reportquery_set.all()]
        for query in queries:
            sql = query.soql
            to_insert = []
            for sp in sps:
                if sp.parameter in query.parameter_set.all():
                    to_insert.append(sp.sql_fragment())
                    sps.pop(sp)
            if 'WHERE' in sql:
                pass


class SavedReportParam(models.Model):
    saved_report = models.ForeignKey(
        SavedReportParams,
        on_delete=models.CASCADE)
    parameter = models.ForeignKey(
        Parameter,
        on_delete=models.CASCADE)
    operator = models.CharField(
        max_length=20)
    value = models.CharField(
        max_length=255)

    def sql_fragment(self):
        frag = self.parameter.set_parameter(
            self.operator,
            self.value)
        return frag

    def __str__(self):
        return "%s: %s" % (
            self.saved_report.name,
            self.sql_fragment())
