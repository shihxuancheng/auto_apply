from setuptools import setup, find_packages

setup(
    name='auto-apply',
    version='0.0.4',
    packages=find_packages(),
    install_requires=[
        'selenium==4.26.1',
        'tqdm==4.67.0',
        'ntplib==0.4.0',
        'apscheduler==3.11.0'
    ],
    entry_points={
        'console_scripts': [
            'auto-apply=src.auto_apply:main',
        ],
    },
    author='Richard hih',
    author_email='shihxuancheng@gmail.com',
    classifiers=[
        'Programming Language :: Python :: 3.11',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.11',
)