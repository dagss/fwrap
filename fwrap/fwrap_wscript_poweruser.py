#------------------------------------------------------------------------------
# Copyright (c) 2010, Kurt W. Smith
# All rights reserved. See LICENSE.txt.
#------------------------------------------------------------------------------

top = '.'
out = 'build'

def options(opt):
    opt.load('compiler_c')
    opt.load('compiler_fc')
    opt.load('python')
    opt.load('inplace', tooldir='tools')

def configure(conf):
    cfg = conf.path.find_resource('fwrap.config.py')
    if cfg:
        conf.env.load(cfg.abspath())

    conf.load('compiler_c')
    conf.load('compiler_fc')
    conf.check_fortran()
    conf.check_fortran_verbose_flag()
    conf.check_fortran_clib()

    conf.load('python')
    conf.check_python_version((2,5))
    conf.check_python_headers()

    conf.check_tool('numpy', tooldir='tools')
    conf.check_numpy_version(minver=(1,3))
    conf.check_tool('cython', tooldir='tools')
    conf.check_cython_version(minver=(0,11,1))
    conf.check_tool('fwrapktp', tooldir='tools')
    conf.check_tool('inplace', tooldir='tools')

    conf.add_os_flags('INCLUDES')
    conf.add_os_flags('LIB')
    conf.add_os_flags('LIBPATH')
    conf.add_os_flags('STLIB')
    conf.add_os_flags('STLIBPATH')

def build(bld):

    bld(features='fwrapktp',
        type_spec='fwrap_type_specs.in',
        includes=['.']
        )
    

    bld(
        features = 'fc fcshlib',
        source = bld.srcnode.ant_glob(incl=['src/*.f', 'src/*.F', 'src/*.f90', 'src/*.F90']),
        target = 'myfortranlib',
        includes = ['.', 'basic_package_fwrap'],
    )

    bld(
        features = 'c fc pyext cshlib fcshlib',
        source = ['basic_package_fwrap/barmod.pyx', 'basic_package_fwrap/barmod_fc.f90'],
        target = 'basic_package_fwrap/barmod',
        use = 'CLIB NUMPY myfortranlib',
        includes = ['.', 'basic_package_fwrap'],
    )

    bld(
        features = 'c fc pyext cshlib fcshlib',
        source = ['basic_package_fwrap/foomod.pyx', 'basic_package_fwrap/foomod_fc.f90'],
        target = 'basic_package_fwrap/foomod',
        use = 'CLIB NUMPY myfortranlib',
        includes = ['.', 'basic_package_fwrap'],
    )

#    1/0
# vim:ft=python
