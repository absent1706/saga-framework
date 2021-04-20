from setuptools import setup


def requirements():
    import os
    filename = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    return [line.rstrip('\n') for line in open(filename).readlines()]


setup(name='saga_framework',
      version='0.1',
      description='Mini-framework that helps implementing Saga pattern in microservices',
      url='https://github.com/absent1706/saga-framework',
      download_url='https://github.com/absent1706/saga-framework/archive/master.tar.gz',
      author='Alexander Litvinenko',
      author_email='litvinenko1706@gmail.com',
      license='MIT',
      packages=['saga_framework'],
      install_requires=requirements(),
      keywords=['microservices', 'saga'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Web Environment',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
      ]
)
