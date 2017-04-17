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
          'rncryptor',
          'atomicwrites',
          'selenium',
          'PyQt5',
      ],
      scripts=['bin/bank-wrangler'],
      #data_files=[('/etc/bank_wrangler', 'etc/bank_wrangler/rules.conf')],
      zip_safe=False)
