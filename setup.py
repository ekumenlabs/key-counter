from setuptools import setup

setup(
    name="key-counter",
    version="0.1.0",
    packages=['key_counter', 'key_counter.tests', 'key_counter.scripts'],

    description="Client-server architecture to collect keys-per-minute",
    long_description=open('README.txt').read(),

    license="",

    test_suite='key_counter.tests',

    # Metadata for upload to PyPI.
    author="Elvio Toccalino",
    author_email="elvio.toccalino@gmail.com",
    keywords="key count counter client server service",
    url="https://github.com/creativa77/key-counter",
)
