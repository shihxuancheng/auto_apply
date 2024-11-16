from setuptools import setup, find_packages

setup(
    name='auto-apply',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'selenium==4.26.1',
        'tqdm==4.67.0'
    ],
    entry_points={
        'console_scripts': [
            'auto-apply=src.auto_apply:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3.11',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.11',
)