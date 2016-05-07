import svgmath

str = """
x &= \int_0^\infty f(u)\exp(x-u)\,du, \\\\
  &= 4.3524 \\approx 0
"""

inline_str = """x^2+6x+8=0"""

data = svgmath.render(inline_str, mode=svgmath.INLINE)
data_display = svgmath.render(str, mode=svgmath.DISPLAY)
str = [
  "<html>",
  "<head><style>body { font-size:30px; font-family: Helvetica Neue; }</style></head>",
  "<body>",
  "<p>Wanne mooie %s vergelijking he!</p>" % data['svg'],
  "<div style='background-color:orange;padding:1.5ex 0;text-align:center;'>%s</div>" % data_display['svg'],
  "</body",
  "</html>",
]
with open('view.html','w') as f:
  f.write("\n".join(str))
