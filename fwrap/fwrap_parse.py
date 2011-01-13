#------------------------------------------------------------------------------
# Copyright (c) 2010, Kurt W. Smith
# All rights reserved. See LICENSE.txt.
#------------------------------------------------------------------------------

from fwrap import pyf_iface as pyf
from fparser import api

def generate_ast(fsrcs):
    ast = []
    for src in fsrcs:
        language = 'pyf' if src.endswith('.pyf') else 'fortran'
        block = api.parse(src, analyze=True)
        tree = block.content
        for proc in tree:
            if not is_proc(proc):
                # we ignore non-top-level procedures until modules are supported.
                continue
        _process_node(block, ast, language)
    return ast

def _process_node(node, ast, language):
    # ast: Output list of function/subroutine nodes
    if not hasattr(node, 'content'):
        return
    children = node.content
    if len(children) == 0:
        return
    for child in children:
        # For processing .pyf files, simply skip the initial
        # wrapping pythonmodule and interface nodes
        # TODO: Multiple pythonmodule in one .pyf?
        if child.blocktype in ('pythonmodule', 'interface'):
            _process_node(child, ast, language)
        elif not is_proc(child):
            # we ignore non-top-level procedures until modules are supported.
            pass
        else:
            args = _get_args(child, language)
            params = _get_params(child, language)
            kw = dict(
                name=child.name,
                args=args,
                params=params,
                language=language)
            if language == 'pyf':
                kw.update(_get_pyf_proc_annotations(child))
            if child.blocktype == 'subroutine':
                ast.append(pyf.Subroutine(**kw))
            elif child.blocktype == 'function':
                ast.append(pyf.Function(return_arg=_get_ret_arg(child, language),
                                        **kw))
    return ast

def is_proc(proc):
    return proc.blocktype in ('subroutine', 'function')

def _get_ret_arg(proc, language):
    ret_var = proc.get_variable(proc.result)
    ret_arg = _get_arg(ret_var, language)
    ret_arg.intent = None
    return ret_arg

def _get_param(p_param, language):
    if not p_param.is_parameter():
        raise ValueError("argument %r is not a parameter" % p_param)
    if not p_param.init:
        raise ValueError("parameter %r does not have an initialization "
                         "expression." % p_param)
    p_typedecl = p_param.get_typedecl()
    dtype = _get_dtype(p_typedecl, language)
    name = p_param.name
    intent = _get_intent(p_param, language)
    if not p_param.is_scalar():
        raise RuntimeError("do not support array or derived-type "
                           "parameters at the moment...")
    return pyf.Parameter(name=name, dtype=dtype, expr=p_param.init)

def _get_arg(p_arg, language):
    
    if not p_arg.is_scalar() and not p_arg.is_array():
        raise RuntimeError(
                "argument %s is neither "
                    "a scalar or an array (derived type?)" % p_arg)

    p_typedecl = p_arg.get_typedecl()
    dtype = _get_dtype(p_typedecl, language)
    name = p_arg.name
    if language == 'pyf':
        intent, pyf_annotations = _get_pyf_arg_annotations(p_arg)
    else:
        intent = _get_intent(p_arg, language)
        pyf_annotations = {}

    if p_arg.is_array():
        p_dims = p_arg.get_array_spec()
        dimspec = pyf.Dimension(p_dims)
    else:
        dimspec = None

    return pyf.Argument(name=name,
                        dtype=dtype,
                        intent=intent,
                        dimension=dimspec,
                        **pyf_annotations)

def _get_args(proc, language):
    args = []
    for argname in proc.args:
        p_arg = proc.get_variable(argname)
        args.append(_get_arg(p_arg, language))
    return args

def _get_params(proc, language):
    params = []
    for varname in proc.a.variables:
        var = proc.a.variables[varname]
        if var.is_parameter():
            params.append(_get_param(var, language))
    return params

def _get_intent(arg, language):
    assert language != 'pyf'
    intents = []
    if not arg.intent:
        intents.append("inout")
    else:
        if arg.is_intent_in():
            intents.append("in")
        if arg.is_intent_inout():
            intents.append("inout")
        if arg.is_intent_out():
            intents.append("out")
    if not intents:
        raise RuntimeError("argument has no intent specified, '%s'" % arg)
    if len(intents) > 1:
        raise RuntimeError(
                "argument has multiple "
                    "intents specified, '%s', %s" % (arg, intents))
    return intents[0]

def _get_pyf_proc_annotations(proc):
    from fparser.statements import Intent, CallStatement, FortranName
    pyf_wraps_c = False
    pyf_callstatement = None
    pyf_fortranname = None
    for line in proc.content:
        if isinstance(line, Intent) and 'C' in line.specs:
            pyf_wraps_c = True
        elif isinstance(line, CallStatement):
            pyf_callstatement = line.expr
        elif isinstance(line, FortranName):
            pyf_fortranname = line.value

    return dict(pyf_wraps_c=pyf_wraps_c,
                pyf_callstatement=pyf_callstatement,
                pyf_fortranname=pyf_fortranname)

def _get_pyf_arg_annotations(arg):
    # Parse Fwrap-compatible intents
    pyf_no_return = False
    if arg.is_intent_inout():
        intent = "inout"
        pyf_no_return = True
    elif arg.is_intent_in() and arg.is_intent_out():
        # The "in,out" feature of f2py corresponds to fwrap's inout
        intent = "inout"
    elif arg.is_intent_in():
        intent = "in"
    elif arg.is_intent_out():
        intent = "out"
    elif arg.is_intent_hide():
        intent = None
    else:
        intent = "inout"

    # Parse intents that are not in Fortran (custom annotations)
    hide = arg.is_intent_hide() and not arg.is_intent_out()

    if arg.is_intent_copy() and arg.is_intent_overwrite():
        raise RuntimeError('intent(copy) conflicts with intent(overwrite)')
    elif arg.is_intent_copy():
        overwrite_flag = True
        overwrite_flag_default = False
    elif arg.is_intent_overwrite():
        overwrite_flag = True
        overwrite_flag_default = True
    else:
        overwrite_flag = False
        overwrite_flag_default = None

    align = None
    if arg.intent is not None:
        if 'ALIGNED4' in arg.intent:
            align = 4
        elif 'ALIGNED8' in arg.intent:
            align = 8
        elif 'ALIGNED16' in arg.intent:
            align = 16

    pyf_by_value = (arg.intent is not None) and ('C' in arg.intent)
        
    annotations = dict(pyf_hide=hide,
                       pyf_default_value=arg.init,
                       pyf_check=arg.check,
                       pyf_overwrite_flag=overwrite_flag,
                       pyf_overwrite_flag_default=overwrite_flag_default,
                       # optional fills a rather different role in pyf files
                       # compared to in F90 files, so we use a seperate flag
                       pyf_optional=arg.is_optional(),
                       pyf_depend=arg.depend,
                       pyf_align=align,
                       pyf_by_value=pyf_by_value,
                       pyf_no_return=pyf_no_return
                       )

    return intent, annotations

name2default = {
        'integer' : pyf.default_integer,
        'real'    : pyf.default_real,
        'doubleprecision' : pyf.default_dbl,
        'complex' : pyf.default_complex,
        'doublecomplex' : pyf.default_double_complex,
        'character' : pyf.default_character,
        'logical' : pyf.default_logical,
        }

name2type = {
        'integer' : pyf.IntegerType,
        'real' : pyf.RealType,
        'complex' : pyf.ComplexType,
        'character' : pyf.CharacterType,
        'logical' : pyf.LogicalType,
        }

def _get_dtype(typedecl, language):
    if not typedecl.is_intrinsic():
        raise RuntimeError(
                "only intrinsic types supported ATM... [%s]" % str(typedecl))
    length, kind = typedecl.selector
    return create_dtype(typedecl.name, length, kind)

def create_dtype(name, length, kind):
    if not kind and not length:
        return name2default[name]
    if length and kind and name != 'character':
        raise RuntimeError("both length and kind specified for "
                               "non-character intrinsic type: "
                               "length: %s kind: %s" % (length, kind))
    if name == 'character':
        if length == '*':
            fw_ktp = '%s_xX' % (name)
        else:
            fw_ktp = '%s_x%s' % (name, length)
        return pyf.CharacterType(fw_ktp=fw_ktp,
                        len=length, kind=kind)
    if length and not kind:
        return name2type[name](fw_ktp="%s_x%s" %
                (name, length),
                length=length)
    try:
        int(kind)
    except ValueError:
        raise RuntimeError(
                "only integer constant kind "
                    "parameters supported ATM, given '%s'" % kind)
    if name == 'doubleprecision':
        return pyf.default_dbl
    return name2type[name](fw_ktp="%s_%s" %
            (name, kind), kind=kind)
