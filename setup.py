import os
import platform
from setuptools import setup, find_packages, Command
from setuptools.command.build_py import build_py
from setuptools.command.egg_info import egg_info
from setuptools.command.sdist import sdist
from subprocess import check_call
from distutils import log
import sys


here = os.path.dirname(os.path.abspath(__file__))
node_root = os.path.join(here, 'js')
is_repo = os.path.exists(os.path.join(here, '.git'))

npm_path = os.pathsep.join([
    os.path.join(node_root, 'node_modules', '.bin'),
    os.environ.get('PATH', os.defpath),
])

log.set_verbosity(log.DEBUG)
log.info('setup.py entered')
log.info('PATH=%s' % os.environ['PATH'])

with open(os.path.join(here, "README.md")) as f:
    LONG_DESCRIPTION = f.read()


def js_prerelease(command, strict=False):
    """decorator for building minified js/css prior to another command"""
    class DecoratedCommand(command):
        def run(self):
            jsdeps = self.distribution.get_command_obj('jsdeps')
            if not is_repo and all(os.path.exists(t) for t in jsdeps.targets):
                # sdist, nothing to do
                command.run(self)
                return

            try:
                self.distribution.run_command('jsdeps')
            except Exception as e:
                missing = [t for t in jsdeps.targets if not os.path.exists(t)]
                if strict or missing:
                    log.warn('rebuilding js and css failed')
                    if missing:
                        log.error('missing files: %s' % missing)
                    raise e
                else:
                    log.warn('rebuilding js and css failed (not a problem)')
                    log.warn(str(e))
            command.run(self)
            update_package_data(self.distribution)
    return DecoratedCommand


def update_package_data(distribution):
    """update package_data to catch changes during setup"""
    build_py = distribution.get_command_obj('build_py')
    # distribution.package_data = find_package_data()
    # re-init build_py options which load package_data
    build_py.finalize_options()


class NPM(Command):
    description = 'install package.json dependencies using npm'
    user_options = []
    node_modules = os.path.join(node_root, 'node_modules')
    targets = [
        os.path.join(here, 'jupyter_widget_hwt', 'static', f)
        for f in ['extension.js', 'index.js']
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def get_npm_name(self):
        npmName = 'npm'
        if platform.system() == 'Windows':
            npmName = 'npm.cmd'

        return npmName

    def has_npm(self):
        npmName = self.get_npm_name()
        try:
            check_call([npmName, '--version'])
            return True
        except Exception:
            return False

    def should_run_npm_install(self):
        package_json = os.path.join(node_root, 'package.json')
        node_modules_exists = os.path.exists(self.node_modules)
        return self.has_npm()

    def run(self):
        has_npm = self.has_npm()
        if not has_npm:
            log.error(
                "`npm` unavailable.  If you're running this command using sudo, make sure `npm` is available to sudo")

        env = os.environ.copy()
        env['PATH'] = npm_path

        if self.should_run_npm_install():
            log.info(
                "Installing build dependencies with npm.  This may take a while...")
            npmName = self.get_npm_name()
            check_call([npmName, 'install', '--debug'], cwd=node_root,
                       stdout=sys.stdout, stderr=sys.stderr)
            os.utime(self.node_modules, None)
            log.info(
                "running npm build")
            check_call([npmName, 'run-script', 'build', '--debug'], cwd=node_root,
                       stdout=sys.stdout, stderr=sys.stderr)

        for t in self.targets:
            if not os.path.exists(t):
                msg = 'Missing file: %s' % t
                if not has_npm:
                    msg += '\nnpm is required to build a development version of a widget extension'
                raise ValueError(msg)

        # update package data in case this created new files
        update_package_data(self.distribution)


version_ns = {}
with open(os.path.join(here, 'jupyter_widget_hwt', '_version.py')) as f:
    exec(f.read(), {}, version_ns)

setup(
    name='jupyter_widget_hwt',
    version=version_ns['__version__'],
    description='Jupyter widgets for visualization of hwt based circuits and simulations.',
    long_description=LONG_DESCRIPTION,
    include_package_data=True,
    data_files=[
        ('share/jupyter/nbextensions/jupyter_widget_hwt', [
            'jupyter_widget_hwt/static/' + f
            for f in ['extension.js', 'index.js', 'index.js.map',
                      'jupyter_widget_hwt.yaml']
        ],),
        ('etc/jupyter/nbconfig/notebook.d', ['jupyter_widget_hwt.json'])
    ],
    install_requires=[
        'ipywidgets>=7.5.1',
        'hwtGraph>=1.9',
    ],
    tests_require=[
        "pytest", "pebble", "xmltodict", # test deps of nbconvert
        "nbconvert>=6.0.7", "nbclient",
        "hwtLib",
    ],
    test_suite="tests",
    packages=find_packages(),
    zip_safe=False,
    cmdclass={
        'build_py': js_prerelease(build_py),
        'egg_info': js_prerelease(egg_info),
        'sdist': js_prerelease(sdist, strict=True),
        'jsdeps': NPM,
    },
    author='Michal Orsak',
    author_email='Nic30original@gmail.com',
    url='https://github.com/Nic30/jupyter_widget_hwt',
    keywords=[
        'ipython',
        'jupyter',
        'widget',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: IPython',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Multimedia :: Graphics',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
