import io
import re
from setuptools import setup

setup (
    name='uploader', 
    version='0.1.1',
    description='For download and upload files by tcp',
    author='dusc',
    author_email='575678405@qq.com',
    url='', 
    packages=['uploader'],
    install_requires=['zipfile36','setuptools>=16.0'],
    python_requires='>=3',
    zip_safe=False
)