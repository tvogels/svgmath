from bs4 import BeautifulSoup
import re
import tempfile
import sys, os
import shutil
import string
import random
import subprocess
from util import which

DEVNULL = open(os.devnull, 'wb')

INLINE  = 'mode-inline'
DISPLAY = 'mode-display'
MARKER_STYLE = 'fill:rgb(72.898865%,85.499573%,33.299255%);fill-opacity:1;'

_keep_numbers_regex = re.compile("[^\d\.]")


# Check dependencies
if not which("pdf2svg"):
  print("Please install pdf2svg (apt-get/yum/brew install pdf2svg)")
  sys.exit()

if not which("xelatex"):
  print("Please install xelatex and the stanalone style (apt-get install texlive-xelatex & texlive-latex-extra)")
  sys.exit()

if not which("pdfcrop"):
  print("Could not find the pdfcrop binary.")
  sys.exit()



def render(equation, mode=INLINE, font_family="Helvetica Neue",
           preamble=[], font_size=12, x_height=None):

  assert mode in [INLINE, DISPLAY], \
         "Invalid mode, choose INLINE or DISPLAY."

  tex = _latex_input(equation, mode, font_family, \
                     preamble, font_size)

  svg = _generate_svg(tex, mode)

  return _parse_svg(svg, mode, x_height)


def _parse_svg(svg, mode, x_height):

  # Generate a unique ID to prefix glyph id's with
  uid_list = [random.choice(string.letters) for i in range(20)]
  uid = ''.join(uid_list)

  # Parse the SVG
  soup = BeautifulSoup(svg, 'xml')
  surface = soup.find(id="surface1")
  characters = list(surface.select('use'))
  # Add a class to all characters uniquify ID
  for char in characters:
    href = char['xlink:href']
    if (href.startswith("#glyph")):
      char['class'] = "svgmath-symbol";
      char['xlink:href'] = href[0] + uid + href[1:]
  # Uniquify symbol IDs
  for symb in soup.find_all("symbol"):
    symb['id'] = uid + symb['id']

  # Locate markers
  markers  = surface.find_all('g', style=MARKER_STYLE, recursive=False)
  nmarkers = len(markers)
  assert nmarkers%2==0, "there should be an even number of markers"
  assert nmarkers>0, "no marker found"

  # Compute baselines and x-height
  xheight_sum = 0
  baselines = []
  for i in xrange(0,nmarkers,2):
    xheight_sum += float(markers[i].use['y']) - float(markers[i+1].use['y'])
    baselines.append(float(markers[i].use['y']))
  if x_height is None:
    x_height = xheight_sum*2/nmarkers

  # Only use the left markers (not the ones on the right) for INLINE
  if mode is INLINE:
    baselines = [baselines[0]]

  # Convert baselines to ex
  baselines = [b/x_height for b in baselines]

  h = float(_keep_numbers_regex.sub('', soup.svg['height'])) / x_height
  w = float(_keep_numbers_regex.sub('', soup.svg['width'])) / x_height
  soup.svg['height'] = "%fex" % h
  soup.svg['width']  = "%fex" % w

  if mode is DISPLAY:
    crop_factor = 0.666
    soup.svg['style'] = """display:inline-block;
                           margin-top:%fex;
                           margin-bottom:%fex;""" % \
                           ((1-baselines[0])*crop_factor, (baselines[-1]-h)*crop_factor)
  elif mode is INLINE:
    below = h - baselines[0]
    soup.svg['style'] = """display:inline-block;
                           margin-bottom:%fex;
                           margin-left:%fex;
                           margin-right:%fex""" % \
                           (-below, -1/x_height, -1/x_height)

  # Add class to the SVG
  soup.svg['class'] = {DISPLAY: 'svgmath-display',
                       INLINE: 'svgmath-inline'}[mode]

  # Remove markers
  for marker in markers:
    marker.extract()

  return {
    'svg': soup.svg.prettify(),
    'baselines': baselines,
    'width': w,
    'height': h,
    'x_height': x_height
  }


def _generate_svg(input, mode):
  """Run latex, crop it, and convert to SVG"""
  try:
    tmpdir   = tempfile.mkdtemp()
    tex_file = os.path.join(tmpdir, "equation.tex")
    pdf_file = os.path.join(tmpdir, "equation.pdf")
    svg_file = os.path.join(tmpdir, "equation.svg")

    # Write tex file
    with open(tex_file,'w') as f:
      f.write(input)


    # Run XeLaTeX
    subprocess.check_call(["xelatex",
                           "-output-directory", tmpdir,
                           "-halt-on-error",
                           tex_file], stdout=DEVNULL)


    # Crop if necessary
    if mode is DISPLAY:
      subprocess.check_call(["pdfcrop",
                             "-margins", "1",
                             pdf_file,
                             pdf_file], stdout=DEVNULL)

    # Convert to SVG
    subprocess.check_call(["pdf2svg", pdf_file, svg_file], stdout=DEVNULL)

    # Return file contents
    with open(svg_file,'r') as svg:
      return svg.read()
  finally:
    # print(tmpdir)
    shutil.rmtree(tmpdir)


def _latex_input(equation, mode=INLINE, font_family="Helvetica Neue",
                  preamble=[], font_size=12):
  if mode is INLINE:
    doctype = ['\documentclass[%dpt, border=1pt]{standalone}' % font_size]
  else:
    doctype = ['\documentclass[%dpt, preview]{standalone}' % font_size]

  packages = [
    '\\usepackage{amsmath}',
    '\\usepackage{amssymb}',
    '\\usepackage{mathspec}',
    '\\usepackage{xunicode}',
    '\\usepackage{xltxtra}',
    '\\usepackage{xcolor}',
    '\\usepackage{color}',
  ]

  font_settings = [
    '\setmainfont{%s}' % font_family,
    '\setmathsfont(Greek,Latin,Digits)[Scale=MatchLowercase]{%s}' % font_family,
    '\setmathrm[Scale=MatchLowercase]{%s}' % font_family,
  ]

  marker_config = [
    '\definecolor{bada55}{RGB}{186,218,85}',
    '\\newcommand{\markers}{\scalebox{0.01}{\color{bada55}.}\\raisebox{1ex}{\scalebox{0.01}{\color{bada55}.}}}'
  ]

  if mode is INLINE:
    content = ['\markers$%s$\markers' % equation]
  else:
    content = [
      '\\begin{align*}',
      '\\\\\n'.join([('\markers '+l.strip()) for l in equation.split('\\\\')]),
      '\end{align*}',
    ]

  return '\n'.join(
    doctype + \
    packages + \
    preamble + \
    font_settings + \
    marker_config + \
    ['\\begin{document}'] + \
    content + \
    ['\end{document}']
  )

