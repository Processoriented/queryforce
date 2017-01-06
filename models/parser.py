import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where
from sqlparse.sql import Token, TokenList, Comparison
from sqlparse.tokens import Keyword, DML


AFTER_WHERE_TYPES = (
    'ORDER',
    'GROUP',
    'LIMIT',
    'UNION',
    'EXCEPT',
    'HAVING',
    'RETURNING')

def is_comp_with_placeholder(token):
    if isinstance(token, Comparison):
        flattend = [str(s.ttype) for s in token.flatten()]
        types = [x.split('.')[-1] for x in flattend]
        if 'Placeholder' in types:
            return True
    return False

class QF_Statement(sqlparse.sql.Statement):
    """Inherits Statement from sqlparse"""
    others = []
    where_clauses = []
    main_where = None

    def __init__(self, sql):
        init_stmts = sqlparse.split(sql)
        stmt = sqlparse.parse(init_stmts.pop(0))[0]
        self.others = [QF_Statement(s) for s in init_stmts]
        super(QF_Statement, self).__init__(stmt)
        self.find_where_clauses()

    def make_wc_dict(self, tokenlist=None, level='0'):
        if tokenlist is None:
            tokenlist = self.tokens
        rtn = None
        for token in tokenlist:
            if isinstance(token, Where):
                if rtn:
                    if level in rtn:
                        rtn[level].append(Where_Clause(token))
                    else:
                        rtn[level] = [Where_Clause(token)]
                else:
                    rtn = {level: [Where_Clause(token)]}
            elif token.is_group:
                gwcs = self.make_wc_dict(token.tokens, str(int(level)+1))
                if gwcs:
                    for lvl in gwcs.keys():
                        if lvl in rtn:
                            rtn[lvl].extend(gwcs[lvl])
                        else:
                            rtn[lvl] = gwcs[lvl]
        return rtn

    def find_where_clauses(self):
        rtn = self.make_wc_dict()
        if not rtn:
            return
        self.set_main_where(rtn)
        for k in rtn.keys():
            self.where_clauses.extend(rtn[k])

    def set_main_where(self, wc=None):
        if wc is None:
            return None
        lvls = [int(x) for x in wc.keys()]
        lvls.sort()
        hl = lvls.pop(0)
        self.main_where = wc[str(hl)][0]

    def ph_comps(self):
        rtn = []
        for wc in self.where_clauses:
            rtn.extend(wc.ph_comps())
        return rtn

    def sql_sans_placeholders(self):
        osql = str(self)
        for wc in self.where_clauses:
            osql = osql.replace(str(wc), wc.strip_placeholders())
        return osql

    def apply_limit(self, limit, sql=None):
        als = self if sql is None else QF_Statement(sql)
        top_level_limit = []
        beg_lim = 0
        for idx, token in enumerate(als.tokens):
            if 'Keyword' in str(token.ttype).split('.'):
                if beg_lim > 0:
                    top_level_limit.append((beg_lim, idx))
                    beg_lim = 0
                elif str(token).upper() == 'LIMIT':
                    beg_lim = idx
        if beg_lim > 0:
            top_level_limit.append((beg_lim, None))
        if len(top_level_limit) > 0:
            tll = top_level_limit[-1]
            rtn = [str(x) for x in als.tokens[0:tll[0]]]
            rtn.append("LIMIT %s" % limit)
            if tll[1]:
                rtn.append(" ")
                rtn.extend([str(x) for x in als.tokens[tll[1]:]])
            return "".join(rtn)
        else:
            return "%s LIMIT %s" % (str(als), limit)

    def apply_param(self, param):
        for comp in self.ph_comps():
            if comp.comp_name == param:
                param_str = comp.set_value(param)
                new_sql = str(self).replace(str(comp), param_str)
                return QF_Statement(new_sql)
        return self

    def append_comp(self, sql_fragment):
        if self.main_where is None:
            self.find_where_clauses()
            if self.main_where is None:
                tok_l = []
                seen_aw = False
                for idx, token in enumerate(self.tokens):
                    if not seen_aw:
                        if 'Keyword' in str(token.ttype).split('.'):
                            if str(token) in AFTER_WHERE_TYPES:
                                tok_l.append(' WHERE %s ' % sql_fragment)
                                seen_aw = True
                    tok_l.append(str(token))
                if not seen_aw:
                    tok_l.append(' WHERE %s ' % sql_fragment)
                nsql = "".join(tok_l)
                nsql = nsql.replace("  ", " ")
                return QF_Statement(nsql)
        else:
            mw = self.main_where
            lcg = mw.clause_groups[-1]
            nw = "%s %s %s " % (
                str(mw),
                lcg.group_boolean,
                sql_fragment)
            nsql = str(self).replace(str(mw), nw)
            return QF_Statement(nsql)

    def remove_ph_comp(self, ph_comp):
        if not isinstance(ph_comp, Placeholder_Comp):
            ph_comp = self.get_ph_comp(ph_comp)
        new_sql = str(self)
        if ph_comp is None:
            return new_sql
        for wc in self.where_clauses:
            nwc = wc.remove_ph_comp(ph_comp) or ""
            new_sql = new_sql.replace(str(wc), nwc)
            new_sql = new_sql.replace("  ", " ")
        return new_sql

    def get_ph_comp(self, tokentext):
        for wc in self.where_clauses:
            ph_comp = wc.get_ph_comp(tokentext)
            if ph_comp:
                return ph_comp
        return None


class Where_Clause(Where):
    clause_groups = []

    def __init__(self, token):
        super(Where_Clause, self).__init__(token)
        self.clause_groups.append(Where_Group(token.tokens, self))

    def has_placeholders(self):
        phcount = 0
        for grp in self.clause_groups:
            if grp.has_placeholders():
                phcount += 1
        return len(phcount) > 0

    def strip_placeholders(self):
        rtn = []
        for sp in self.clause_groups:
            sptext = sp.strip_placeholders().strip()
            if len(sptext) > 0:
                rtn.append(sptext)
        return "" if len(rtn) == 0 else "WHERE %s" % "".join(rtn)

    def ph_comps(self):
        phcs = []
        for wg in self.clause_groups:
            phcs.extend(wg.all_ph_comps())
        return phcs

    def remove_ph_comp(self, ph_comp):
        cgs = []
        for cg in self.clause_groups:
            cgtext = cg.remove_ph_comp(ph_comp)
            if cgtext:
                cgs.append(cgtext)
        return "" if len(cgs) == 0 else "WHERE %s" % "".join(cgs)

    def get_ph_comp(self, tokentext):
        for cg in self.clause_groups:
            ph_comp = cg.get_ph_comp(tokentext)
            if ph_comp:
                return ph_comp
        return None

class Where_Group(TokenList):
    group_boolean = 'AND'
    group_parent = None
    group_punct = None
    sub_groups = []
    ph_comps = []
    nph_comps = []

    def __init__(self, tokenlist, parent):
        super(Where_Group, self).__init__(tokenlist)
        self.group_parent = parent
        frst = self.tokens[0]
        lst = self.tokens[-1]
        if 'Punctuation' in str(frst.ttype).split('.') and \
                'Punctuation' in str(lst.ttype).split('.'):
            self.group_punct = (str(frst), str(lst))
        self.analyze_comps()

    def analyze_comps(self, tokenlist=None):
        tokenlist = tokenlist or self.tokens
        for token in tokenlist:
            if is_comp_with_placeholder(token):
                self.ph_comps.append(Placeholder_Comp(token, self))
            elif isinstance(token, Comparison):
                self.nph_comps.append(token)
            elif token.is_group:
                self.sub_groups.append(Where_Group(token.tokens, self))
            elif 'Keyword' in str(token.ttype).split('.'):
                if str(token) == 'OR':
                    self.group_boolean = 'OR'

    def placeholder_count(self):
        phcount = len(self.ph_comps)
        for grp in self.sub_groups:
            phcount += grp.placeholder_count()
        return phcount

    def has_placeholders(self):
        return self.placeholder_count > 0

    def strip_placeholders(self):
        rtn = []
        for nph in self.nph_comps:
            rtn.append(str(nph))
        for sg in self.sub_groups:
            sptext = sg.strip_placeholders()
            if len(sptext) > 0:
                rtn.append(sptext)
        sep = " %s " % self.group_boolean
        rtn = sep.join(rtn)
        if self.group_punct and len(rtn) > 0:
            rtn = "%s%s%s" % (
                self.group_punct[0],
                rtn,
                self.group_punct[1])
        return rtn

    def all_ph_comps(self):
        aphcs = self.ph_comps
        for sg in self.sub_groups:
            aphcs.extend(sg.all_ph_comps())
        return aphcs

    def remove_ph_comp(self, ph_comp):
        """ returns group text to re-parse """
        elements = []
        elements.extend(self.nph_comps)
        for sg in self.sub_groups:
            sgtext = sg.remove_ph_comp(ph_comp)
            if sgtext:
                elements.append(sgtext)
        for comp in self.ph_comps:
            if comp != ph_comp:
                elements.append(comp)

        if len(elements) > 0:
            booltext = " %s " % self.group_boolean
            grtext = booltext.join(str(x) for x in elements)
            if self.group_punct:
                return "%s%s%s" % (
                    self.group_punct[0],
                    grtext,
                    self.group_punct[1])
        else:
            return None

    def get_ph_comp(self, tokentext):
        for phc in self.ph_comps:
            if str(phc) == tokentext:
                return phc
        for sg in self.sub_groups:
            ph_comp = sg.get_ph_comp(tokentext)
            if ph_comp:
                return ph_comp
        return None


class Placeholder_Comp(Comparison):
    comp_name = ''
    parent_group = None

    def __init__(self, token, parent_group):
        self.parent_group = parent_group
        super(Placeholder_Comp, self).__init__(token)
        self.comp_name = self.get_real_name()
        
    def set_value(self, param):
        new_tokenlist = []
        for token in self.tokens:
            if 'Comparison' in str(token.ttype):
                new_tokenlist.append(param['operator'])
            elif 'Placeholder' in str(token.ttype):
                val_str = param['value']
                if param['use_quotes']:
                    val_str = "'%s'" % param['value'] 
                new_tokenlist.append(val_str)
            else:
                new_tokenlist.append(str(token))
        return "".join(new_tokenlist)
