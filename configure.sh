#!/bin/bash

if [ $# -eq 1 ]
then
    sf_user=$1
fi

# checking Python version
PYV=`python -c 'import sys; print(hex(sys.hexversion))'`
if (( "$PYV" <= "0x2070000" ))
then
  if type "python2.7" > /dev/null
  then
    shopt -s expand_aliases
    alias python="python2.7"
  else
    echo you are using python version:
    python --version
    echo "this MolProbity configure script requires Python 2.7 or newer";
    exit
  fi
fi

echo ++++++++++ getting MolProbity base ...
if [ ! -f base.tar.gz ]; then curl http://kinemage.biochem.duke.edu/molprobity/base.tar.gz -o base.tar.gz; echo got.;
else echo already got.; fi
echo unpacking ...
if [ ! -d base ]; then tar zxf base.tar.gz; echo unpacked.;
else echo already unpacked.; fi

echo ++++++++++ creating build directories ...
if [ ! -d sources ]; then mkdir sources; fi
if [ ! -d build ]; then mkdir build; fi
cd sources

echo ++++++++++ getting sources ...
if [ -n "$sf_user" ]
then
    if [ ! -d cctbx_project ]
    then
        svn --quiet --non-interactive --trust-server-cert co https://$sf_user@svn.code.sf.net/p/cctbx/code/trunk cctbx_project
    fi
    if [ ! -d cbflib ]
    then
        svn --quiet --non-interactive --trust-server-cert co https://$sf_user@svn.code.sf.net/p/cbflib/code-0/trunk/CBFlib_bleeding_edge cbflib
    fi
else
    if [ ! -d cctbx_project ]
    then
        svn --quiet --non-interactive --trust-server-cert co https://svn.code.sf.net/p/cctbx/code/trunk cctbx_project
    fi
    if [ ! -d cbflib ]
    then
        svn --quiet --non-interactive --trust-server-cert co https://svn.code.sf.net/p/cbflib/code-0/trunk/CBFlib_bleeding_edge cbflib
    fi
fi

#svn --non-interactive --trust-server-cert co https://quiddity.biochem.duke.edu/svn/reduce/trunk reduce
#svn --non-interactive --trust-server-cert co https://quiddity.biochem.duke.edu/svn/probe/trunk probe
#svn --non-interactive --trust-server-cert co https://quiddity.biochem.duke.edu/svn/suitename

if [ ! -d probe ]; 
then 
    svn --quiet --non-interactive --trust-server-cert co https://github.com/rlabduke/probe.git/trunk probe
fi
if [ ! -d reduce ]; 
then 
    svn --quiet --non-interactive --trust-server-cert co https://github.com/rlabduke/reduce.git/trunk reduce
fi
if [ ! -d suitename ];
then 
   svn --quiet --non-interactive --trust-server-cert co https://github.com/rlabduke/suitename.git/trunk suitename
fi

if [ ! -f boost.gz ]; then curl http://cci.lbl.gov/repositories/boost.gz -o boost.gz; fi
if [ ! -f scons.gz ]; then curl http://cci.lbl.gov/repositories/scons.gz -o scons.gz; fi
if [ ! -f annlib.gz ]; then curl http://cci.lbl.gov/repositories/annlib.gz -o annlib.gz; fi
if [ ! -f annlib_adaptbx.gz ]; then curl http://cci.lbl.gov/repositories/annlib_adaptbx.gz -o annlib_adaptbx.gz; fi
if [ ! -f ccp4io.gz ]; then curl http://cci.lbl.gov/repositories/ccp4io.gz -o ccp4io.gz; fi
if [ ! -f ccp4io_adaptbx.gz ]; then curl http://cci.lbl.gov/repositories/ccp4io_adaptbx.gz -o ccp4io_adaptbx.gz; fi
if [ ! -f chem_data.tar.gz ]; then curl http://kinemage.biochem.duke.edu/molprobity/chem_data.tar.gz -o chem_data.tar.gz; fi
if [ ! -f tntbx.gz ]; then curl http://cci.lbl.gov/repositories/tntbx.gz -o tntbx.gz; fi

echo ++++++++++ unpacking sources ...
tar zxf boost.gz
tar zxf scons.gz
tar zxf annlib.gz
tar zxf annlib_adaptbx.gz
tar zxf ccp4io.gz
tar zxf ccp4io_adaptbx.gz
tar zxf chem_data.tar.gz
tar zxf tntbx.gz

echo ++++++++++ creating Makefile ...
cd ../build

#this script, at minimum, creates the Makefile for the make operation that follows
python ../sources/cctbx_project/libtbx/configure.py mmtbx

echo ++++++++++ making ...
#As of this writing, the default make command below evaluates to:
#./bin/libtbx.scons -j "`./bin/libtbx.show_number_of_processors`"
#comment in the similar line below to build with a manually chosen number of processors,
#otherwise "make" will use all processors on the machine (which may be ok)
#Compilation has at least one memory-heavy step such that <= 1GB memory / processor
#will cause compilation to delve into virtual memory (ultrabad)

#slow but safe, (command is fragile b/c copied from an autogenerated make file, check build/Makefile if broken
#./bin/libtbx.scons -j 1
#fast but may be memory intensive
make

echo ++++++++++ setting paths ...
source ../build/setpaths.sh

echo ++++++++++ pickling rotarama ...
#this configures all the rotamer and ramachandran contour files so rotalyze and ramalyze work. 
#They are downloaded as giant text files, this line of code creates them as python pickles
mmtbx.rebuild_rotarama_cache

#echo ++++++++++ creating directories ...
# git doesn't store empty directories so we're adding the the required empty directory here.
cd ..
#mkdir -p public_html/data
#mkdir -p public_html/data/tmp
#mkdir -p feedback
#mkdir -p tmp

echo ++++++++++ MolProbity configure.sh finished.
