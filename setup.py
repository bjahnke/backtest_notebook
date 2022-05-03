from setuptools import setup

setup(
    name='backtest_notebook',
    version='',
    packages=['scripts'],
    url='',
    license='',
    author='bjahnke',
    author_email='',
    description='',
    install_requires=[
        'numpy',
        'pandas',
        'data_manager @ git+https://github.com/bjahnke/data_manager.git#egg=data_manager',
        'pandas_accessors @ git+https://github.com/bjahnke/pandas_accessors.git#egg=pandas_accessors',
        'regime @ git+https://github.com/bjahnke/regime.git#egg=regime',
        'blue_bird_pms @ git+https://github.com/bjahnke/blue_bird_pms.git#egg=blue_bird_pms',
        'tda_access @ git+https://github.com/bjahnke/tda_access.git#egg=tda_access',
        'cbpro_access @ git+https://github.com/bjahnke/cbpro_access.git#egg=cbpro_access',
    ]
)
