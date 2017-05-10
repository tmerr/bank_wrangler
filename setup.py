from setuptools import setup

setup(name='bank_wrangler',
      version='0.1',
      description='Aggregate and categorize bank transactions',
      url='http://github.com/tmerr/bank_wrangler',
      author='Trevor Merrifield'
      author_email='trevorm42@gmail.com'
      license='GPLv3',
      packages=['bank_wrangler'],
      install_requires=[
          'tabulate',
          'rncryptor',
          'atomicwrites',
          'selenium',
      ],
      scripts=['bin/bank-wrangler'],
      zip_safe=False)
