#!/usr/bin/python
# (jEdit options) :folding=explicit:collapseFolds=1:
import sys, os, getopt, re, subprocess, shutil
from optparse import OptionParser
import time
import gzip
# THIS FILE MUST BE IN THE MOLPROBITY CMDLINE DIRECTORY!!!

#number_to_run = 50

#{{{ parse_cmdline
#parse the command line--------------------------------------------------------------------------
def parse_cmdline():
  parser = OptionParser()
  parser.add_option("-l", "--limit", action="store", type="int",
    dest="total_file_size_limit", default=10000000,
    help="change total file size in each separate job")
  parser.add_option("-t", "--type", action="store", type="string",
    dest="bond_type", default="nuclear",
    help="specify hydrogen bond length for clashes (nuclear or ecloud)")
  parser.add_option("-r", "--reduce", action="store", type="boolean",
    dest="run_reduce", default="false",
    help="run reduce to add hydrogens first (use -t to specify length)")
  opts, args = parser.parse_args()
  if opts.total_file_size_limit < 5000000:
    sys.stderr.write("\n**ERROR: -limit cannot be less than 5000000 (5M)\n")
    sys.exit(parser.print_help())
  if not (opts.bond_type == "nuclear" or opts.bond_type == "ecloud"):
    sys.stderr.write("\n**ERROR: -type must be ecloud or nuclear\n")
    sys.exit(parser.print_help())
  if len(args) < 1:
    sys.stderr.write("\n**ERROR: User must specify input directory\n")
    sys.exit(help())
  else:
    indir = args[0]
    if (os.path.isdir(indir)):
      return opts, indir
    else:
      sys.stderr.write("\n**ERROR: First argument must be a directory!\n")
      sys.exit(help())
#------------------------------------------------------------------------------------------------
#}}}

#{{{ help
def help():
  print """USAGE:   python make_condor_files.py [input_directory_of_pdbs]

  Takes as input a directory containing pdbs, and generates a directory 'condor_sub_files'
  within that directory containing all the scripts needed to run molprobity analysis on a
  HTCondor cluster.

FLAGS:
  -h     Print this help message
"""
#}}}

#{{{ split_pdbs_to_models
def split_pdbs_to_models(mp_home, indir, outdir):
  #print "indir: "+indir
  if (os.path.isdir(indir)):
    files = os.listdir(indir)
    files.sort()
    #print files
    for f in files:
      #arg_file = os.path.join(arg, f)
      full_file = os.path.join(indir,f)
      #print "full_file: "+full_file
      if (not os.path.isdir(full_file)):
        root, ext = os.path.splitext(f)
        if (ext == ".pdb"):
          #print full_file
          #print os.path.join(mp_home, "cmdline", "split-models")
          #s_time = time.time()
          #subprocess.call([os.path.join(mp_home, "cmdline", "split-models"), "-q", full_file, outdir])
          split_pdb(full_file, outdir)
          #e_time = time.time()
          #print repr(e_time - s_time) + " seconds?"
        if (ext == ".gz"):
          split_pdb(full_file, outdir, True)
#}}}

#{{{ split_pdb
def split_pdb(pdb_file, outdir, gzip_file = False):
  model_files = []
  keep_lines = False
  pdb_name, ext = os.path.splitext(os.path.basename(pdb_file))
  if gzip_file:
    pdb_in = gzip.open(pdb_file)
  else:
    pdb_in=open(pdb_file)
  mod_num = 0
  for line in pdb_in:
    start = line[0:6]
    if start == "MODEL ":
      keep_lines = True
      mod_num = int(line[5:25].strip())
      model_name = os.path.join(outdir, pdb_name+("_%03d.pdb" % (mod_num)))
      model_out = open(model_name, 'wr')
    elif start == "ENDMDL":
      keep_lines = False
      model_out.close()
    elif keep_lines:
      model_out.write(line)
  pdb_in.close()
  if mod_num == 0: # takes care of the case where there's only one model, so no MODEL or ENDMDL
    shutil.copyfile(pdb_file, os.path.join(outdir, pdb_name+"_001.pdb"))
#}}}

#{{{ divide_pdbs
def divide_pdbs(in_dir, size_limit):
  #print os.path.realpath(in_dir)
  if (os.path.isdir(in_dir)):
    files = os.listdir(os.path.realpath(in_dir))
    #print files
    files.sort()
    #print arg
    list_of_lists = []
    pdb_list = []
    list_size = 0
    list_of_lists.append(pdb_list)
    #print files
    for f in files:
      #print f
      #arg_file = os.path.join(arg, f)
      full_file = os.path.abspath(os.path.join(in_dir, f))
      #print full_file
      if (not os.path.isdir(full_file)):
        root, ext = os.path.splitext(f)
        if (ext == ".pdb"):
          #print f
          if (list_size <= size_limit):
            pdb_list.append(full_file)
            #print pdb_list
            list_size = list_size + os.path.getsize(full_file)
          else:
            pdb_list = []
            pdb_list.append(full_file)
            list_of_lists.append(pdb_list)
            list_size = os.path.getsize(full_file)
    if len(list_of_lists) > 10000:
      sys.stderr.write("\n**ERROR: More than 10000 jobs needed, try choosing a larger -limit\n")
      sys.exit()
    return list_of_lists
    #print list_of_lists
#}}}

#{{{ write_super_dag
def write_super_dag(outdir, list_of_pdblists):
  config_name = "supermol.config"
  config_file = os.path.join(os.path.realpath(outdir), config_name)
  config = open(config_file, 'wr')
  config.write("DAGMAN_MAX_JOBS_SUBMITTED = 5\n")
  config.write("DAGMAN_SUBMIT_DELAY = 60")
  config.close()
  out_name = "supermol.dag"
  outfile = os.path.join(os.path.realpath(outdir), out_name)
  out=open(outfile, 'wr')
  out.write("CONFIG "+ config_file+"\n\n")
  for indx, pdbs in enumerate(list_of_pdblists):
    num = '{0:0>4}'.format(indx)
    out.write("SUBDAG EXTERNAL "+num+" moldag"+num+".dag\n")
    write_mol_dag(outdir, num, pdbs)
  out.close()
#}}}

#{{{ write_mol_dag
def write_mol_dag(outdir, num, pdbs):
  out_name = "moldag"+num+".dag"
  outfile = os.path.join(os.path.realpath(outdir), out_name)
  out=open(outfile, 'wr')

  out.write("Jobstate_log logs/mol"+num+".jobstate.log\n")
  out.write("NODE_STATUS_FILE mol"+num+".status 3600\n")
  out.write("\n")

  parent_childs = "" # create parent_childs part of dag file now so only have to loop once thru pdbs
  #pdb_list = []
  #for pdb_file in pdbs:
  #  #pdb_list.append(os.path.basename(pdb_file))
  #  pdb, ext = os.path.splitext(os.path.basename(pdb_file))
  #  out.write("Job clash"+pdb+" clashlist.sub\n")
  #  out.write("VARS clash"+pdb+" PDB=\""+pdb_file+"\" PDBNAME=\""+pdb+"\"\n")
  #  out.write("\n")
  #  parent_childs = parent_childs+"PARENT clash"+pdb+" CHILD local"+num+"\n"
  base_pdbs = []
  pdb_remaps = []
  #relative_pdbs = []
  for pdb_file in pdbs:
    base_pdbs.append(os.path.basename(pdb_file))
    base_pdb, ext = os.path.splitext(os.path.basename(pdb_file))
    pdb_remaps.append(base_pdb+"-clashlist=results/"+base_pdb+"-clashlist") # for transferring clashlist output to results folder
    #relative_pdbs.append(os.path.join("..", os.path.basename(pdb_file)))
  out.write("Job clash"+num+" clashlist.sub\n")
  out.write("VARS clash"+num+" PDBS=\""+" ".join(base_pdbs)+"\"\n") #space separated list of PDBS for commandline input
  out.write("VARS clash"+num+" PDBSINPUT=\""+",".join(pdbs)+"\"\n") #comma separated list of PDBS for condor transfering
  out.write("VARS clash"+num+" PDBREMAPS=\""+";".join(pdb_remaps)+"\"\n")
  out.write("VARS clash"+num+" NUMBER=\""+num+"\"\n")
  #out.write(parent_childs)

  out.write("Job local"+num+" local.sub\n")
  out.write("VARS local"+num+" PDBS=\""+" ".join(pdbs)+"\"\n")
  out.write("VARS local"+num+" NUMBER=\""+num+"\"\n")
  out.write("PARENT clash"+num+" CHILD local"+num+"\n")

  out.close()
#}}}

#{{{ write_oneline_dag
def write_oneline_dag(outdir, list_of_pdblists):
  config_name = "onelinedag.config"
  config_file = os.path.join(os.path.realpath(outdir), config_name)
  config = open(config_file, 'wr')
  #config.write("DAGMAN_MAX_JOBS_SUBMITTED = 5\n")
  config.write("DAGMAN_SUBMIT_DELAY = 5")
  config.close()
  out_name = "onelinedag.dag"
  outfile = os.path.join(os.path.realpath(outdir), out_name)
  out=open(outfile, 'wr')
  out.write("CONFIG "+ config_file+"\n\n")
  out.write("NODE_STATUS_FILE onelinedag.status 3600\n")
  out.write("\n")
  postjobs = "PARENT "
  for indx, pdbs in enumerate(list_of_pdblists):
    num = '{0:0>4}'.format(indx)
    #out.write("SUBDAG EXTERNAL "+num+" moldag"+num+".dag\n")
    #out.write("Jobstate_log logs/mol"+num+".jobstate.log\n")

    parent_childs = "" # create parent_childs part of dag file now so only have to loop once thru pdbs
    #pdb_list = []
    #for pdb_file in pdbs:
    #  #pdb_list.append(os.path.basename(pdb_file))
    #  pdb, ext = os.path.splitext(os.path.basename(pdb_file))
    #  out.write("Job clash"+pdb+" clashlist.sub\n")
    #  out.write("VARS clash"+pdb+" PDB=\""+pdb_file+"\" PDBNAME=\""+pdb+"\"\n")
    #  out.write("\n")
    #  parent_childs = parent_childs+"PARENT clash"+pdb+" CHILD local"+num+"\n"
    base_pdbs = []
    #pdb_remaps = []
    #relative_pdbs = []
    for pdb_file in pdbs:
      base_pdbs.append(os.path.basename(pdb_file))
      base_pdb, ext = os.path.splitext(os.path.basename(pdb_file))
      #pdb_remaps.append(base_pdb+"-clashlist=results/"+base_pdb+"-clashlist") # for transferring clashlist output to results folder
      #relative_pdbs.append(os.path.join("..", os.path.basename(pdb_file)))
      #out.write("Job clash"+num+" clashlist.sub\n")
      #out.write("VARS clash"+num+" PDBS=\""+" ".join(base_pdbs)+"\"\n") #space separated list of PDBS for commandline input
      #out.write("VARS clash"+num+" PDBSINPUT=\""+",".join(pdbs)+"\"\n") #comma separated list of PDBS for condor transfering
      #out.write("VARS clash"+num+" PDBREMAPS=\""+";".join(pdb_remaps)+"\"\n")
      #out.write("VARS clash"+num+" NUMBER=\""+num+"\"\n")
      #out.write(parent_childs)
      
    out.write("Job oneline"+num+" oneline.sub\n")
    out.write("VARS oneline"+num+" PDBS=\""+" ".join(pdbs)+"\"\n")
    out.write("VARS oneline"+num+" NUMBER=\""+num+"\"\n\n")
    #out.write("PARENT clash"+num+" CHILD local"+num+"\n")
    postjobs = postjobs+"oneline"+num + " "
    
  out.write("JOB post post_process.sub\n")
  out.write(postjobs+"CHILD post\n")
  out.close()
#}}}

#{{{ write_file
def write_file(outdir, out_name, file_text, permissions=0644):
  outfile = os.path.join(os.path.realpath(outdir), out_name)
  out=open(outfile, 'wr')
  out.write(file_text)
  out.close()
  os.chmod(outfile, permissions)
#}}}

#{{{ write_local_run
local_run = """#!/bin/sh

# Get the pdb file location from args
#pdb=$1

for pdb in "$@"
do
pdbbase=`basename $pdb .pdb` #should be just the name of the pdb without the .pdb extension
#echo $pdbbase
# Chiropraxis
java -cp {0}/lib/chiropraxis.jar chiropraxis.rotarama.Ramalyze -raw $pdb > results/${pdbbase}-ramalyze

# Rotalyze
java -cp {0}/lib/chiropraxis.jar chiropraxis.rotarama.Rotalyze $pdb > results/${pdbbase}-rotalyze

# Prekin -pperp
{0}/bin/linux/prekin -pperptoline -pperpdump $pdb > results/${pdbbase}-prekin_pperp

# Dangle rna
java -cp {0}/lib/dangle.jar dangle.Dangle -rna -validate -outliers -sigma=0.0 $pdb > results/${pdbbase}-dangle_rna

# c-beta dev
{0}/bin/linux/prekin -cbdevdump $pdb > results/${pdbbase}-cbdev

# Dangle protein
java -cp {0}/lib/dangle.jar dangle.Dangle -protein -validate -outliers -sigma=0.0 $pdb > results/${pdbbase}-dangle_protein

# Suitename
java -Xmx512m -cp {0}/lib/dangle.jar dangle.Dangle rnabb $pdb | {0}/bin/linux/suitename  -report > results/${pdbbase}-suitename

# Analyze the results
{0}/cmdline/molparser.py -q $pdb 1 results/${pdbbase}-clashlist results/${pdbbase}-cbdev results/${pdbbase}-rotalyze results/${pdbbase}-ramalyze results/${pdbbase}-dangle_protein results/${pdbbase}-dangle_rna results/${pdbbase}-dangle_dna results/${pdbbase}-prekin_pperp results/${pdbbase}-suitename
done
"""
#}}}

#{{{ write_oneline_py
#From Jon Wedell
oneline_py = """#!/usr/bin/python

import sys
import subprocess
import os
import time

# Run a command without blocking
def syscmd(outfile, *commands):
    if outfile != subprocess.PIPE:
        outfile = open(outfile, "w")
    return subprocess.Popen(list(commands),stdout=outfile,stderr=subprocess.PIPE, stdin=subprocess.PIPE)

# Wait for a subprocess to finish and print it's stderr if it exists
def reap(the_cmd, pdb):
    the_cmd.wait()
    err = the_cmd.stderr.read()
    if err != "":
        sys.stderr.write(pdb+" had the following error\\n"+err)
        
os.makedirs("results")

for pdb in sys.argv[1:]:
    s_time = time.time()
    pdbbase = os.path.basename(pdb)[:-4]
    model_num = pdbbase[-3:]
    pdb_code = pdbbase[:4]
    
    if not os.path.exists("results/"+pdb_code):
        os.makedirs("results/"+pdb_code)

    reap(syscmd("results/"+pdb_code+"/"+pdbbase+"-clashlist", "./clashlist", pdb, '40', '10', 'nuclear'), pdbbase)
    reap(syscmd("results/"+pdb_code+"/"+pdbbase+"-ramalyze","java","-cp","{0}/lib/chiropraxis.jar", "chiropraxis.rotarama.Ramalyze", "-raw", "-quiet", pdb), pdbbase)
    reap(syscmd("results/"+pdb_code+"/"+pdbbase+"-rotalyze","java","-cp","{0}/lib/chiropraxis.jar", "chiropraxis.rotarama.Rotalyze", pdb), pdbbase)
    reap(syscmd("results/"+pdb_code+"/"+pdbbase+"-dangle_rna","java","-cp","{0}/lib/dangle.jar", "dangle.Dangle", "-rna", "-validate", "-outliers", "-sigma=0.0", pdb), pdbbase)
    reap(syscmd("results/"+pdb_code+"/"+pdbbase+"-dangle_protein","java","-cp","{0}/lib/dangle.jar", "dangle.Dangle", "-protein", "-validate", "-outliers", "-sigma=0.0", pdb), pdbbase)
    reap(syscmd("results/"+pdb_code+"/"+pdbbase+"-dangle_dna","java","-cp","{0}/lib/dangle.jar", "dangle.Dangle", "-dna", "-validate", "-outliers", "-sigma=0.0", pdb), pdbbase)
    reap(syscmd("results/"+pdb_code+"/"+pdbbase+"-prekin_pperp","{0}/bin/linux/prekin", "-pperptoline", "-pperpdump", pdb), pdbbase)
    reap(syscmd("results/"+pdb_code+"/"+pdbbase+"-cbdev", "{0}/bin/linux/prekin", "-cbdevdump", pdb), pdbbase)

    cmd1 = syscmd(subprocess.PIPE, "java","-Xmx512m", "-cp","{0}/lib/dangle.jar", "dangle.Dangle", "rnabb", pdb)
    cmd1_out = cmd1.stdout.read()
    cmd1.wait()
    cmd2 = syscmd("results/"+pdb_code+"/"+pdbbase+"-suitename", "{0}/bin/linux/suitename", "-report")
    cmd2.stdin.write(cmd1_out)
    cmd2.stdin.flush()
    cmd2.stdin.close()

    reap(cmd1, pdbbase)
    reap(cmd2, pdbbase)

    cmd9 = syscmd(subprocess.PIPE, "{0}/cmdline/molparser.py", "-q", pdb, model_num, "results/"+pdb_code+"/"+pdbbase+"-clashlist", "results/"+pdb_code+"/"+pdbbase+"-cbdev", "results/"+pdb_code+"/"+pdbbase+"-rotalyze", "results/"+pdb_code+"/"+pdbbase+"-ramalyze", "results/"+pdb_code+"/"+pdbbase+"-dangle_protein", "results/"+pdb_code+"/"+pdbbase+"-dangle_rna", "results/"+pdb_code+"/"+pdbbase+"-dangle_dna", "results/"+pdb_code+"/"+pdbbase+"-prekin_pperp", "results/"+pdb_code+"/"+pdbbase+"-suitename")
    reap(cmd9, pdbbase)
    print cmd9.stdout.read().strip()
    e_time = time.time()
    sys.stderr.write(repr(e_time - s_time) + " seconds(?) for local of "+pdbbase+"\\n")
"""
#}}}

#{{{ write_localsub
local_sub = """universe = local

Notify_user  = vbchen@bmrb.wisc.edu
notification = Error

Executable  = post_process.sh

log     = logs/post.log
error       = logs/post.err
copy_to_spool   = False
priority    = 0

queue
"""
#}}}

#{{{ write_clashlistsh
clash_sh = """#!/bin/sh

mkdir results

for pdb in "$@"
do
pdbbase=`basename $pdb .pdb` #should be just the name of the pdb without the .pdb extension
./clashlist $pdb 40 10 {bondtype} > ${pdbbase}-clashlist

done
"""
#}}}

#{{{ write_clashlistsub
clash_sub = """universe = vanilla

Notify_user  = vbchen@bmrb.wisc.edu
notification = Error

#requirements = ((TARGET.FileSystemDomain == "bmrb.wisc.edu") || (TARGET.FileSystemDomain == ".bmrb.wisc.edu"))

Executable  = clashlist.sh
Arguments   = $(PDBS)

should_transfer_files = YES
when_to_transfer_output = ON_EXIT
transfer_input_files = $(PDBSINPUT),{0}/bin/linux/probe,{0}/bin/linux/cluster,{0}/bin/clashlist
#transfer_output_files = results/
transfer_output_remaps = "$(PDBREMAPS)"

log         = logs/clashlist$(NUMBER).log
#output = logs/clashlist$(NUMBER).out
error       = logs/clashlist$(NUMBER).err
copy_to_spool   = False
priority    = 0

queue
"""
#}}}

#{{{ write_oneline_sub
oneline_sub = """universe = vanilla

Notify_user  = vbchen@bmrb.wisc.edu
notification = Error

#requirements = ((TARGET.FileSystemDomain == "bmrb.wisc.edu") || (TARGET.FileSystemDomain == ".bmrb.wisc.edu"))

Executable  = oneline.py
Arguments   = $(PDBS)

should_transfer_files = YES
when_to_transfer_output = ON_EXIT
#transfer_input_files = $(PDBSINPUT),{0}/bin/linux/probe,{0}/bin/linux/cluster,{0}/bin/clashlist
transfer_input_files = {0}/bin/linux/probe,{0}/bin/linux/cluster,{0}/bin/clashlist
transfer_output_files = results
#transfer_output_remaps = "$(PDBREMAPS)"

log         = logs/oneline$(NUMBER).log
output      = logs/oneline$(NUMBER).out
error       = logs/oneline$(NUMBER).err
copy_to_spool   = False
priority    = 0

queue
"""
#}}}

#{{{ write_post_sh
post_sh = """#!/bin/sh

cat logs/oneline*.out > logs/alloneline.out.csv
cat logs/oneline*.err > logs/alloneline.err
"""
#}}}

#{{{ make_files
def make_files(indir, file_size_limit, bond_type):
  molprobity_home = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
  #print "mp home: " + molprobity_home
  #print "indir: " + indir

  if os.path.exists(indir):
    indir_base = os.path.basename(os.path.realpath(indir))
    outdir = os.path.join(indir, "condor_sub_files_"+indir_base)
    if not os.path.exists(outdir):
      os.makedirs(outdir)
      os.makedirs(os.path.join(outdir,"logs"))
      os.makedirs(os.path.join(outdir,"results"))
      os.makedirs(os.path.join(outdir,"pdbs"))
    else:
      sys.stderr.write("\"condor_sub_files\" directory detected in \""+indir+"\", please delete it before running this script\n")
      sys.exit()
    split_pdbs_to_models(molprobity_home, indir, os.path.join(outdir, "pdbs"))
    #print opts.total_file_size_limit
    list_of_lists = divide_pdbs(os.path.join(outdir, "pdbs"), file_size_limit)
    #write_super_dag(outdir, list_of_lists)
    write_oneline_dag(outdir, list_of_lists)
    write_file(outdir, "oneline.py", oneline_py.format(molprobity_home), 0755)
    write_file(outdir, "oneline.sub", oneline_sub.format(molprobity_home))
    write_file(outdir, "post_process.sh", post_sh, 0755)
    #write_file(outdir, "local_run.sh", local_run.format(molprobity_home, pdbbase="{pdbbase}"), 0755)
    #write_file(outdir, "local_run.py", local_run_py.format(molprobity_home), 0755)
    write_file(outdir, "post_process.sub", local_sub)
    #write_file(outdir, "clashlist.sh", clash_sh.format(bondtype=opts.bond_type, pdb="{pdb}", pdbbase="{pdbbase}"), 0755)
    #write_file(outdir, "clashlist.sub", clash_sub.format(molprobity_home))
    
  else:
    sys.stderr.write(indir + " does not seem to exist!\n")
#}}}

if __name__ == "__main__":

  opts, indir = parse_cmdline()
  make_files(indir, opts.total_file_size_limit, opts.bond_type)
