#------------------------------------------------------------------------------
# Copyright (c) 2010, Dag Sverre Seljebotn
# All rights reserved. See LICENSE.txt.
#------------------------------------------------------------------------------
import re
from fwrap import constants
from fwrap.pyf_iface import _py_kw_mangler, py_kw_mangle_expression
from fwrap.cy_wrap import _CyArg, CythonExpression
import pyparsing as prs
from warnings import warn

TODO_PLACEHOLDER = '##TODO (watch any dependencies that may be further down!) %s'
prs.ParserElement.enablePackrat()

class CouldNotMergeError(Exception):
    pass

def mergepyf_ast(cython_ast, cython_ast_from_pyf):
    # Primarily just copy ast, but merge in select detected manual
    # modifications to the pyf file present in pyf_ast

    pyf_procs = dict((proc.name, proc) for proc in cython_ast_from_pyf)
    result = []
    for proc in cython_ast:
        try:
            pyf_proc = pyf_procs.get(proc.name, None)
            if pyf_proc is None:
                continue # treat as manually excluded
            result.append(mergepyf_proc(proc, pyf_proc))
        except CouldNotMergeError, e:
            warn('Could not import procedure "%s" from .pyf, '
                 'please modify manually' % proc.name)
            result.append(proc.copy())
    return result

def mergepyf_proc(f_proc, pyf_proc):
    #merge_comments = []
    # There are three argument lists to merge:
    # call_args: "proc" definitely has the right one, however we
    #            may want to rename arguments
    # in_args: pyf_proc has the right one
    # out_args: pyf_proc has the right one
    #
    # Try to parse call_statement to figure out as much as
    # possible, and leave the rest to the user.
    func_name = f_proc.name
    callstat = pyf_proc.pyf_callstatement

    if callstat is None:
        # We can simply use the pyf argument list and be satisfied
        if len(f_proc.call_args) != len(pyf_proc.call_args):
            raise CouldNotMergeError('pyf and f description of function is different')
        # TODO: Verify that types match as well
        call_args = [arg.copy() for arg in pyf_proc.call_args]
    else:
        # Do NOT trust the name or order in pyf_proc.call_args,
        # but match arguments by their position in the callstatement
        pyf_args = pyf_proc.call_args + pyf_proc.aux_args
        call_args = []
        m = callstatement_re.match(callstat)
        if m is None:
            raise CouldNotMergeError('Unable to parse callstatement! Have a look at '
                                     'callstatement_re:' + callstat)
        arg_exprs = m.group(1).split(',')

        # Strip off error arguments (but leave return value)
        assert f_proc.call_args[-2].name == constants.ERR_NAME
        assert f_proc.call_args[-1].name == constants.ERRSTR_NAME
        fortran_args = f_proc.call_args[:-2]
        if len(fortran_args) != len(arg_exprs):
            raise CouldNotMergeError('"%s": pyf and f disagrees, '
                             'len(fortran_args) != len(arg_exprs)' % pyf_proc.name)
        # Build call_args from the strings present in the callstatement
        for idx, (f_arg, expr) in enumerate(zip(fortran_args, arg_exprs)):
            if idx == 0 and pyf_proc.kind == 'function':
                # NOT the same as f_proc.kind == 'function'
                
                # We can't resolve by name for the return arg, but it will
                # always be first. This case does not hit for functions
                # declared as subprocs in pyf, where the return arg *can*
                # be reorderd, but also carries a user-given name for matching.
                arg = pyf_proc.call_args[0].copy()
            else:
                arg = parse_callstatement_arg(expr, f_arg, pyf_args)
            call_args.append(arg)
            
        # Reinsert the extra error-handling and function return arguments
        call_args.append(f_proc.call_args[-2].copy())
        call_args.append(f_proc.call_args[-1].copy())


    # Make sure our three lists (in/out/callargs) contain the same
    # argument objects
    arg_by_name = dict((arg.name, arg) for arg in call_args)
    def copy_or_get(arg):
        # Also translate default values
        result = arg_by_name.get(arg.name, None)
        if result is None:
            result = arg.copy()
        return result

    in_args = [copy_or_get(arg) for arg in pyf_proc.in_args]
    out_args = [copy_or_get(arg) for arg in pyf_proc.out_args]
    in_args = process_in_args(in_args)
    aux_args = ([copy_or_get(arg) for arg in pyf_proc.aux_args])

    # Translate C expressions to Cython.
    # The check directives on arguments are moved to the procedure
    # (they often contain more than one argument...)
    checks = []
    visited = [] # since arguments cannot be hashed
    for arg in in_args + out_args + aux_args + call_args:
        if arg in visited:
            continue
        visited.append(arg)
        if arg.pyf_check is not None:
            checks.extend([c_to_cython_warn(c, func_name)
                           for c in arg.pyf_check])
            arg.update(pyf_check=[])

        if arg.pyf_default_value is None and not arg.is_array:
            for dep in arg.pyf_depend:
                # If one lists an *explicit* depends on a 1-dim array,
                # set default value to len(arr). TODO: Implicit depends.
                dep_arg = arg_by_name[dep]
                if dep_arg.is_array and len(dep_arg.dimension.dims) == 1:
                    if arg.pyf_default_value is not None:
                        raise RuntimeError('depends on multiple array')
                    arg.pyf_default_value = 'len(%s)' % dep

        if arg.is_array and arg.is_explicit_shape:
            dimexprs = [c_to_cython_warn(dim.sizeexpr, func_name)
                        for dim in arg.dimension]
            arg.update(cy_explicit_shape_expressions=dimexprs)

        if arg.is_array:
            # f2py semantics oddity: If one *explicitly* depends the array
            # on the shape scalar, disable truncation
            last_dim_deps = arg.dimension.dims[-1].depnames
            if len(last_dim_deps.intersection(arg.pyf_depend)) > 0:
                arg.update(truncation_allowed=False)

        if arg.pyf_default_value is not None:
            defval = arg.pyf_default_value
            cy_default_value = c_to_cython_warn(defval, func_name)
            defer = not cy_default_value.is_literal()
            arg.update(cy_default_value=cy_default_value,
                       pyf_default_value=None,
                       defer_init_to_body=defer)

    result = f_proc.copy_and_set(call_args=call_args,
                                 in_args=in_args,
                                 out_args=out_args,
                                 aux_args=aux_args,
                                 checks=checks,
                                 language='pyf')
    return result

callstatement_re = re.compile(r'^.*\(\*f2py_func\)\s*\((.*)\).*$')
callstatement_arg_re = re.compile(r'^\s*(&)?\s*([a-zA-Z0-9_]+)(\s*\+\s*([a-zA-Z0-9_]+))?\s*$')
nested_ternary_re = re.compile(r'^\(?(\s*\(\) .*)\?(.*):(.*)\)?$')

def parse_callstatement_arg(arg_expr, f_arg, pyf_args):
    # Parse arg_expr, and return a suitable new argument based on pyf_args
    # Returns None for unparseable/too complex expression
    m = callstatement_arg_re.match(arg_expr)
    if m is not None:
        ampersand, var_name, offset = m.group(1), m.group(2), m.group(4)
        if offset is not None and ampersand is not None:
            raise CouldNotMergeError('Arithmetic on scalar pointer?')
        pyf_arg = [arg for arg in pyf_args if arg.name == var_name]
        if len(pyf_arg) >= 1:
            result = pyf_arg[0].copy()
            if offset is not None:
                if not result.is_array:
                    raise CouldNotMergeError('Passing scalar without taking address?')
                result.update(mem_offset_code=_py_kw_mangler(offset))
            return result
        else:
            return manual_arg(f_arg, arg_expr)
    else:
        try:
            cy_expr = c_to_cython(arg_expr)
        except ValueError:
            return manual_arg(f_arg, arg_expr)
        else:
            return auxiliary_arg(f_arg, cy_expr)

def manual_arg(f_arg, expr):
    # OK, we do not understand the C code in the callstatement in this
    # argument position, but at least introduce a temporary variable
    # and put in a placeholder for user intervention
    return auxiliary_arg(f_arg, CythonExpression(TODO_PLACEHOLDER % expr, ()))

def auxiliary_arg(f_arg, expr):
    assert isinstance(expr, CythonExpression)
    arg = f_arg.copy_and_set(
        cy_name='%s_f' % f_arg.name,
        name='%s_f' % f_arg.name,
        intent=None,
        pyf_hide=True,
        cy_default_value=expr)
    return arg

def process_in_args(in_args):
    # Arguments must be changed as follows:
    # a) Reorder so that arguments with defaults come last
    # b) Parse the default_value into something usable by Cython.
    mandatory = [arg for arg in in_args if not arg.is_optional()]
    optional = [arg for arg in in_args if arg.is_optional()]
    in_args = mandatory + optional
    
    # Process intent(copy) and intent(overwrite). f2py behaviour is to
    # add overwrite_X to the very end of the argument list, so insert
    # new argument nodes.
    overwrite_args = []
    for arg in in_args:
        if arg.pyf_overwrite_flag:
            flagname = 'overwrite_%s' % arg.cy_name
            arg.overwrite_flag_cy_name = flagname
            overwrite_args.append(
                _CyArg(name=flagname,
                       cy_name=flagname,
                       ktp='bint',
                       intent='in',
                       dtype=None,
                       cy_default_value=CythonExpression(
                           repr(arg.pyf_overwrite_flag_default), ())))
    in_args.extend(overwrite_args)

    # Return new set of in_args
    return in_args


class CToCython(object):
    def __init__(self, doc=False):

        def handle_var(s, loc, tok):
            v = tok[0]
            if v.endswith('_capi'):
                raise prs.ParseException('References f2py-specific variable "%s"' % v)
            self.encountered.add(v)
            return '%%(%s)s' % v

        # FollowedBy(NotAny): make sure variables and
        # function calls are not confused
        variables = prs.Regex(r'[a-zA-Z_][a-zA-Z0-9_]*') + prs.FollowedBy(prs.NotAny('('))
        variables.setParseAction(handle_var)

        var_or_literal = variables | prs.Regex('-?[0-9.e\-]+') | prs.dblQuotedString

        def handle_ternary(s, loc, tok):
            tok = tok[0]
            return '(%s if %s else %s)' % (tok[2], tok[0], tok[4])

        def passthrough_op(s, loc, tok):
            return '(%s)' % ' '.join(tok[0])

        _c_to_cython_bool = {'&&' : 'and', '||' : 'or', '/' : '//', '*' : '*'}
        def translate_op(s, loc, tok):
            tok = tok[0]
            translated = [x if idx % 2 == 0 else _c_to_cython_bool[x]
                          for idx, x in enumerate(tok)]
            return '(%s)' % (' '.join(translated))

        def handle_not(s, loc, tok):
            return 'not %s' % tok[0][1]

        def handle_cast(s, loc, tok):
            return '<%s>%s' % (tok[0][0], tok[0][1])

        def handle_func(s, loc, tok):
            func, args = tok[0], tok[1:]
            if func == 'len':
                if doc:
                    return '%s.shape[0]' % args[0]
                else:
                    return 'np.PyArray_DIMS(%s)[0]' % args[0]
            elif func == 'shape':
                if doc:
                    return '%s.shape[%s]' % (args[0], args[1])
                else:
                    return 'np.PyArray_DIMS(%s)[%s]' % (args[0], args[1])
            elif func in ('abs',):
                return '%s(%s)' % (func, ', '.join(args))

        expr = prs.Forward()

        func_call = (prs.oneOf('len shape abs') + prs.Suppress('(') + expr +
                     prs.ZeroOrMore(prs.Suppress(',') + expr) + prs.Suppress(')'))
        func_call.setParseAction(handle_func)
        cast = prs.Suppress('(') + prs.oneOf('int float') + prs.Suppress(')')

        expr << prs.operatorPrecedence(var_or_literal | func_call, [
            ('!', 1, prs.opAssoc.RIGHT, handle_not),
            (cast, 1, prs.opAssoc.RIGHT, handle_cast),
            (prs.oneOf('* /'), 2, prs.opAssoc.LEFT, translate_op),
            (prs.oneOf('+ -'), 2, prs.opAssoc.LEFT, passthrough_op),
            (prs.oneOf('== != <= >= < >'), 2, prs.opAssoc.LEFT, passthrough_op),
            (prs.oneOf('|| &&'), 2, prs.opAssoc.LEFT, translate_op),
            (('?', ':'), 3, prs.opAssoc.RIGHT, handle_ternary),
            ]) 

        self.translator = expr + prs.StringEnd()


    zero_re = re.compile(r'^[()0.,\s]+$') # variations of zero...
    literal_re = re.compile(r'^-?[()0-9.,\se\-]+$') # close enough; also matches e.g. (0, 0.)
    complex_literal_re = re.compile(r'^\s*\((-?[0-9.,\s]+),(-?[0-9.,\s]+)\)\s*$')

    def translate(self, s):
        self.encountered = set()
        m = self.complex_literal_re.match(s)
        if m is not None:
            real, imag = m.group(1), m.group(2)
            if self.zero_re.match(imag):
                r = real
            else:
                r = '%s + %s*1j' % (real, imag)
        else:
            try:
                r = self.translator.parseString(s)[0]
            except prs.ParseException, e:
                raise ValueError('Could not auto-translate: %s (%s)' % (s, e))            
            if r[0] == '(' and r[-1] == ')':
                r = r[1:-1]
        return r, self.encountered

_translator_cython = CToCython(doc=False)
_translator_doc = CToCython(doc=True)

def c_to_cython(s):
    r, encountered = _translator_cython.translate(s)
    r_doc, _ = _translator_doc.translate(s)
    return CythonExpression(r, encountered, r_doc)

def c_to_cython_warn(s, func_name):
    try:
        return c_to_cython(s)
    except ValueError, e:
        warn('Problem in %s: %s' % (func_name, e))
        return CythonExpression(TODO_PLACEHOLDER % s, [], s)
