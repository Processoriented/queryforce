from django.db import models
from .auth import ForceAPI


class Report_Def(models.Model):
    name = models.CharField(
        max_length=80)

    def __str__(self):
        return self.name


class Query_Def(models.Model):
    pass


class Report_Query(models.Model):
    report = models.ForeignKey(
        Report_Def,
        on_delete=models.CASCASE)


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
        

class ParsedSQL():
    baseline = ''
    stmt = None
    others = []

    def __init__(self, sql):
        self.baseline = sql
        self.stmt = sqlparse.parse(sql)[0]
        self.others = [
            ParsedSQL(s) for s in sqlparse.split(sql)[1:]]

    def __str__(self):
        return str(self.stmt)

    def get_type(self):
        return self.stmt.get_type()

    def is_subselect(self, parsed):
        if not parsed.is_group:
            return False
        for item in parsed.tokens:
            if item.ttype is DML and item.value.upper() == 'SELECT':
                return True
        return False

    def extract_part(self, parsed, part_name):
        part_seen = False
        for item in parsed.tokens:
            if part_seen:
                if self.is_subselect(item):
                    for x in extract_part(item, part_name):
                        yield x
                elif item.ttype is Keyword:
                    raise StopIteration
                else:
                    yield item
            elif (item.ttype is Keyword and 
                item.value.upper() == part_name.upper()):
                part_seen = True
            elif (item.ttype is DML and 
                item.value.upper() == part_name.upper()):
                part_seen = True

    def extract_identifiers(self, token_stream):
        for item in token_stream:
            if isinstance(item, IdentifierList):
                for identifier in item.get_identifiers():
                    yield identifier.get_name()
            elif isinstance(item, Identifier):
                yield item.get_name()

    def get_columns(self):
        stream = self.extract_part(self.stmt, 'SELECT')
        return list(self.extract_identifiers(stream))

    def get_tables(self):
        stream = self.extract_part(self.stmt, 'FROM')
        return list(self.extract_identifiers(stream))

    def get_where(self):
        for item in self.stmt.tokens:
            if isinstance(item, Where):
                yield item

    def has_where(self):
        return len(list(self.get_where())) > 0

    def tokens_thru_where(self):
        before_where = True
        for item in self.stmt.tokens:
            if before_where:
                if isinstance(item, Where):
                    before_where = False
                elif not self.has_where():
                    if (item.ttype is Keyword and
                        item.value.upper() != 'FROM'):
                        before_where = False
                yield item

    def tokens_past_where(self):
        before_where = True
        for item in self.stmt.tokens:
            if before_where:
                if isinstance(item, Where):
                    before_where = False
                elif not self.has_where():
                    if (item.ttype is Keyword and
                        item.value.upper() != 'FROM'):
                        before_where = False
                        yield item
            else:
                yield item

    def split_at_where(self):
        before_split = "".join([
            x.value for x in self.tokens_thru_where()])
        after_split = "".join([
            x.value for x in self.tokens_past_where()])
        return [before_split, after_split]

    def add_filter(self, filter_text, bool_operator='AND'):
        before_split = "".join([
            x.value for x in self.tokens_thru_where()]).strip()
        after_split = "".join([
            x.value for x in self.tokens_past_where()]).strip()
        if not self.has_where():
            text_to_insert = "WHERE %s" % filter_text
        else:
            text_to_insert = "%s %s" % (bool_operator, filter_text)
        new_sql = " ".join([
            before_split,
            text_to_insert,
            after_split])
        self.stmt = sqlparse.parse(new_sql)[0]
        return str(self.stmt)


class SelectStatement(ParsedSQL):
    parts = []

    def __init__(self, sql):
        super(SelectStatement, self).__init__(sql)
        if self.get_type().upper() != 'SELECT':
            self = None
        else:
            self.make_parts()

    def make_parts(self):
        cur_part = None
        part_kw = ''
        part_tokens = []
        for item in self.stmt.tokens:
            if item.ttype in (DML, Keyword):
                if len(part_tokens) > 0:
                    self.make_part(part_kw, part_tokens)
                    part_tokens = []
                part_kw = str(item).upper()
            if isinstance(item, Where):
                self.make_part(part_kw, part_tokens)
                self.make_part('WHERE', item.tokens)
                part_tokens = []
            else:
                part_tokens.append(item)
        if len(part_tokens) > 0:
            self.make_part(part_kw, part_tokens)

    def make_part(self, part_kw, tokens):
        sp = StatementPart(part_kw, tokens, self)
        self.parts.append(sp)
        setattr(self, part_kw.lower(), sp)

    def __str__(self):
        rtn = []
        for part in self.parts:
            rtn.append(str(part))
        return "".join(rtn)

    def parts_used(self):
        return [p.name for p in self.parts]

    def replace_part(self, part, text):
        new_sql = []
        if part in self.parts_used():
            for cur_part in self.parts:
                if part.upper() == cur_part.name:
                    new_sql.append(text)
                else:
                    new_sql.append(str(cur_part))
        else:
            new_sql.extend([str(p) for p in self.parts])
            new_sql.append(text)
        return "".join(new_sql)

    def param_comparisons(self):
        if 'WHERE' not in self.parts_used():
            return None
        rtn = {}
        seen_pc = False
        for token in self.parts['WHERE']:
            valid = isinstance(token, sqlparse.sql.Comparison)
            valid = valid and '=' in str(token)
            valid = valid and '?' in str(token)
            if valid:
                idx = self.parts['WHERE'].token_index(token)
                comp_txt = str(token).strip().split('=')
                comp_txt = [x.strip() for x in comp_txt]
                repl_txt = sqlparse.sql.Token(None, "1=1")
                if len(comp_txt) == 2:
                    repl_txt = comp_txt[0] + "=" + comp_txt[0]
                    repl_txt = Token(None, repl_txt)
                rtn[idx] = [token, repl_txt]
                seen_pc = True
        return rtn if seen_pc else None

    def non_param_sql(self):
        param_cps = self.param_comparisons()
        if param_cps is None:
            return str(self)
        else:
            return self.param_sql(param_cps)

    def param_sql(self, param_cps=None):
        if param_cps is None:
            return str(self)
        new_sql = []
        for part in self.parts:
            if part.name == 'WHERE':
                for idx, token in enumerate(part.tokens):
                    if idx in param_cps:
                        new_tok = param_cps[idx][1]
                        if not isinstance(new_tok, Token):
                            new_tok = Token(None, new_tok)
                        new_sql.append(new_tok)
                    else:
                        new_sql.append(token)
            else:
                for token in part.tokens:
                    new_sql.append(token)
        rtn = sqlparse.sql.TokenList(new_sql)
        return str(rtn)


class StatementPart(sqlparse.sql.TokenList):
    name = ''
    parent = None

    def __init__(self, name, tokens, parent=None):
        self.name = name
        self.parent = parent
        super(StatementPart, self).__init__(tokens)
