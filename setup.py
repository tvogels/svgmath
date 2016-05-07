from setuptools import setup
setup(name='svgmath',
      version='0.1',
      description='LaTeX to SVG with baseline detection',
      author='Thijs Vogels',
      author_email='t.vogels@me.com',
      url='https://github.com/tvogels/svgmath',
      license='MIT',
      install_requires=[
        'bs4'
      ],
      packages=['svgmath'])