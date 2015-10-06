"""
WHAT THIS FILE DOES:
    converts an RST file to a .ipynb file
HOW THIS FILE WORKS:
    1. calls pandoc to convert between .rst and .md
    2. calls notedown to convert between .md and .ipynb
TODO:
    * properly parse command line args (escape chars etc)
    * Features notedown needs:
        * figure emedding
        * unicode
DEPS:
    * [notedown], [pandoc]

[notedown]:https://github.com/aaren/notedown
[pandoc]:http://pandoc.org
"""

import io
import os
pjoin = os.path.join
import re
import sys
from subprocess import Popen, PIPE
import argparse


parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("input", nargs='?', help="the input .rst file. Include the .rst")
parser.add_argument("-o", "--output", help="the .ipynb output file. Include .ipynb")
parser.add_argument("-v", "--verbose", action="store_true", help="be verbose")
parser.add_argument("-d", "--debug", action="store_true", help="write debug information and keep temporary .md file")
args = parser.parse_args()

if args.verbose:
    print(args.input, args.output)

here = os.path.dirname(__file__)

if args.input:
    input_text = io.open(args.input).read()
else:
    input_text = sys.stdin.read()
input_text = '\n'.join([
    # add default-role: math for sage rst
    '.. default-role:: math',
    input_text])
# pandoc doesn't properly handle : immediately-following close-`
input_text = input_text.replace('`:', '` :')

# convert rst->markdown with pandoc
if args.verbose:
    sys.stderr.write("Calling pandoc to convert from rst to markdown\n")
p = Popen([
        'pandoc',
        '--filter', pjoin(here, 'sageblockfilter.py'),
        '--atx-headers',
        '--from', 'rst',
        '--to', 'markdown',
    ], stdout=PIPE, stdin=PIPE)

intermediate_md, _ = p.communicate(input_text.encode('utf8'))

if p.returncode:
    sys.exit("pandoc failed: %s" % p.returncode)

intermediate_md = intermediate_md.decode('utf8', 'replace')

# define some math macros for mathjax
intermediate_md = '\n'.join([
    # add some sage-defined macros:
    '$$',
    r'\def\CC{\bf C}',
    r'\def\QQ{\bf Q}',
    r'\def\RR{\bf R}',
    r'\def\ZZ{\bf Z}',
    '$$',
    intermediate_md])

# Workaround:
# notedown does not handle nicely indented fenced code blocks
# This at least deindents the starting and trailing ```.

regexp = re.compile("^\s*```", flags=re.M)
intermediate_md = regexp.sub("```", intermediate_md)
intermediate_md = intermediate_md.replace("``` {", "```{") # Temporary workaround for older versions of notedown; see: https://github.com/aaren/notedown/issues/29.

# write intermediate markdown for debugging:
if args.debug:
    sys.stderr.write("Writing intermediate markdown in tmp.md\n")
    with open('tmp.md', 'w') as f:
        f.write(intermediate_md)

# md->ipynb via notedown
if args.verbose:
    sys.stderr.write("Calling notedown to convert from markdown to ipynb\n")
command = ['notedown', '--match=fenced']
if args.output:
    command.extend(['-o', args.output])
p = Popen(command, stdin=PIPE)
p.communicate(intermediate_md.encode('utf8'))
if p.returncode:
    sys.exit("notedown failed: %s" % p.returncode)