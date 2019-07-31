import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="aio_tiny_healthcheck",
    version="1.1.2",
    author="Nikolai Abrosimov",
    author_email="nikolay.abrosimoff@gmail.com",
    description="Tiny asynchronous implementation of healthcheck provider and http-server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nabrosimoff/aio_tiny_healthcheck",
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)